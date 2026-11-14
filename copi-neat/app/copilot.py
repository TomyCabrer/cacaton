"""Claude layer: turns the working memory into a briefing a stressed operator can read in five seconds.

Three modes, picked at startup:
  live      – credentials found; calls Claude and records every output to demo_cache/
  recorded  – no credentials, but a recording exists; replays recorded Claude outputs
  offline   – neither; builds a plain briefing from the rule engine's memory

Claude never acts. Its recommendations go into the same queue as the rules', must cite
event ids that exist, and wait for a human decision like everything else.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from .memory import ACTIONS

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("MEMORIA_CACHE_DIR", ROOT / "demo_cache"))
MODEL = os.environ.get("MEMORIA_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("MEMORIA_EFFORT", "low")  # live ops: latency matters more than depth

Action = Literal[ACTIONS]  # type: ignore[valid-type]

SYSTEM = """You are Copi, the working-memory assistant of a railway traffic control centre (CTC) on a Spanish high-speed line. You support a human operator during normal running and during incidents. The human decides. You never act on the railway.

Each request gives you a JSON snapshot: the simulated time, the events received so far (each with an id), the deterministic rule engine's memory (facts, hypotheses, open loops, contradictions), and the recommendations already raised with their status (pending, approved, rejected or deferred by the operator, with the operator's reason).

Write a briefing for an operator under stress:
- headline: one line, at most 15 words: the single most important thing right now.
- situation: at most 3 short sentences. What is known, and how sure.
- unknowns: the most important things not yet known (at most 4).
- hypotheses: at most 3, each with a confidence and the event ids that support it.
- recommendations: only actions that are NOT already in the recommendation list under any status. Usually zero or one. Each must cite event ids from the snapshot. Respect operator decisions: do not re-propose a rejected action unless evidence arrived after the rejection, and if you do, say what changed.
- driver_train and driver_message: if one train crew needs one short instruction now, name the train and write it in at most 25 words. Otherwise leave both empty.

Rules:
- Cite only event ids present in the snapshot. Never invent events, positions, numbers or names.
- Separate evidence from inference. Say "unconfirmed" when it is.
- When the cost of being wrong is lopsided (stopping trains against a collision; dispatching ambulances against injured people waiting), prefer the safe action and state the cost.
- If the situation is seconds-critical, say plainly that automatic protection is the relevant layer, not the operator.
- Plain English. Keep Spanish railway terms the operator uses (PK, vía, maquinista, interventor) where natural."""

ASK_SYSTEM = """You are Copi, the working-memory assistant of a railway control centre. Answer the operator's question from the JSON snapshot only. Be brief (at most 4 sentences), cite the event ids you rely on, and say plainly when the record does not contain the answer. Never invent facts. You advise; the operator decides."""

HANDOVER_SYSTEM = """You are Copi, the working-memory assistant of a railway control centre. Write a shift handover from the JSON snapshot for the incoming operator, who has no context. Lead with anything unresolved that could hurt someone. Cite event ids in brackets. Never invent facts."""


class Hypothesis(BaseModel):
    statement: str
    confidence: Literal["low", "medium", "high"]
    evidence_ids: list[str]


class Recommendation(BaseModel):
    action: Action
    target: str
    title: str
    rationale: str
    evidence_ids: list[str]
    urgency: Literal["medium", "high", "critical"]
    cost_if_wrong: str


class Briefing(BaseModel):
    headline: str
    situation: str
    unknowns: list[str]
    hypotheses: list[Hypothesis]
    recommendations: list[Recommendation]
    driver_train: str
    driver_message: str


class Answer(BaseModel):
    answer: str
    evidence_ids: list[str]
    confidence: Literal["low", "medium", "high"]


class Handover(BaseModel):
    summary: str
    unresolved: list[str]
    decisions_pending: list[str]
    watch_next: list[str]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Copilot:
    def __init__(self, scenario_id: str):
        _load_dotenv()
        self.cache_path = CACHE_DIR / f"{scenario_id}.json"
        self.cache = self._read_cache()
        has_creds = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        if os.environ.get("MEMORIA_OFFLINE") == "1":
            has_creds = False
        if has_creds:
            self.mode = "live"
            self.client = anthropic.AsyncAnthropic(timeout=60.0, max_retries=1)
        elif self.cache["briefings"]:
            self.mode, self.client = "recorded", None
        else:
            self.mode, self.client = "offline", None

    # ----- cache --------------------------------------------------------
    def _read_cache(self) -> dict:
        try:
            data = json.loads(self.cache_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data.setdefault("briefings", {})
        data.setdefault("asks", {})
        data.setdefault("handovers", {})
        return data

    def _write_cache(self) -> None:
        CACHE_DIR.mkdir(exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True))

    # ----- calls --------------------------------------------------------
    async def _parse(self, system: str, snapshot: dict, out, extra: str | None = None):
        content = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        if extra:
            content += "\n\n" + extra
        resp = await self.client.beta.messages.parse(
            model=MODEL,
            max_tokens=8000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": EFFORT},
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": content}],
            output_format=out,
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("model declined the request")
        if resp.parsed_output is None:
            raise RuntimeError(f"no structured output (stop_reason={resp.stop_reason})")
        return resp.parsed_output, resp.model

    async def brief(self, snapshot: dict, keys: list[str]) -> tuple[dict | None, dict]:
        """keys: cache keys for this moment, most specific first (live writes keys[0];
        recorded mode replays the first key that has a recording)."""
        key = keys[0]
        meta = {"mode": self.mode, "key": key, "model": None, "latency_ms": None, "error": None}
        if self.mode == "live":
            t0 = time.perf_counter()
            try:
                out, model = await self._parse(SYSTEM, snapshot, Briefing)
            except (anthropic.APIError, RuntimeError) as e:  # keep the console running on any API failure
                meta["error"] = f"{type(e).__name__}: {e}"[:300]
                return None, meta
            meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            meta["model"] = model
            data = out.model_dump()
            self.cache["briefings"][key] = data
            self._write_cache()
            return data, meta
        if self.mode == "recorded":
            for k in keys:
                if k in self.cache["briefings"]:
                    meta["model"], meta["key"] = "recorded", k
                    return json.loads(json.dumps(self.cache["briefings"][k])), meta
        return None, meta

    async def ask(self, snapshot: dict, question: str) -> dict:
        if self.mode != "live":
            hit = self.cache["asks"].get(question.strip().lower())
            if hit:
                return {**hit, "mode": "recorded"}
            return {
                "answer": "Live questions need an Anthropic API key (set ANTHROPIC_API_KEY in memoria/.env). "
                "The rule-based memory on screen is still current.",
                "evidence_ids": [],
                "confidence": "low",
                "mode": self.mode,
            }
        t0 = time.perf_counter()
        try:
            out, _ = await self._parse(ASK_SYSTEM, snapshot, Answer, extra=f"Operator question: {question}")
        except (anthropic.APIError, RuntimeError) as e:
            return {"answer": f"Claude unavailable: {type(e).__name__}", "evidence_ids": [], "confidence": "low", "mode": "error"}
        data = out.model_dump()
        self.cache["asks"][question.strip().lower()] = data
        self._write_cache()
        return {**data, "mode": "live", "latency_ms": round((time.perf_counter() - t0) * 1000)}

    async def handover(self, snapshot: dict, key: str) -> dict | None:
        if self.mode != "live":
            hit = self.cache["handovers"].get(key)
            return {**hit, "mode": "recorded"} if hit else None
        try:
            out, _ = await self._parse(HANDOVER_SYSTEM, snapshot, Handover)
        except (anthropic.APIError, RuntimeError):
            return None
        data = out.model_dump()
        self.cache["handovers"][key] = data
        self._write_cache()
        return {**data, "mode": "live"}


def offline_briefing(mem_snapshot: dict, banner: dict | None) -> dict:
    """Plain briefing built from the rule engine's memory when Claude is not available."""
    items = mem_snapshot["items"]
    open_ = lambda kind: [i for i in items[kind] if i["status"] == "open"]  # noqa: E731
    pending = [r for r in mem_snapshot["recommendations"] if r["status"] == "pending"]
    pending.sort(key=lambda r: {"critical": 0, "high": 1, "medium": 2}[r["urgency"]])
    hyps = sorted(open_("hypothesis"), key=lambda i: {"high": 0, "medium": 1, "low": 2}.get(i["confidence"] or "low", 3))
    if banner:
        headline = banner["text"].split(" — ")[0].split(". ")[0]
    elif pending:
        headline = pending[0]["title"]
    elif hyps:
        headline = hyps[0]["text"]
    else:
        headline = "Nothing unusual in the record."
    facts = sorted(open_("fact"), key=lambda i: i["updated"], reverse=True)[:3]
    if facts:
        situation = " ".join(f["text"] for f in facts)
    elif hyps:
        situation = f"No confirmed facts yet. {hyps[0]['text']} {hyps[0].get('detail') or ''}".strip()
    else:
        situation = "No confirmed facts yet."
    return {
        "headline": headline,
        "situation": situation,
        "unknowns": [i["text"] for i in open_("open_loop")][:4] + [i["text"] for i in open_("contradiction")][:2],
        "hypotheses": [
            {"statement": h["text"], "confidence": h["confidence"] or "low", "evidence_ids": h["evidence"]} for h in hyps[:3]
        ],
        "recommendations": [],
        "driver_train": "",
        "driver_message": "",
    }
