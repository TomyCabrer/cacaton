"""Copi: the Claude layer of the drill. One model for everything: Sonnet (protocols.COPI_MODEL).

Copi listens to the pilot and the control tower and writes to the tower. Copi advises. It never gives an
authority and never touches the railway.

Four calls:
  order   – LZB failure drill: what did the tower just order (stop, on sight, faster), or nothing at all?
  brief   – the brief that goes with an open protocol (the other four cases).
  listen  – is this line of speech a pilot reporting something abnormal?
  answer  – an answer when the pilot or the tower asks Copi something.

Same three modes as the replay copilot: live (key found), recorded (no key, briefs on disk),
offline (neither: the rule engine's brief only).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from .protocols import COPI_MODEL, PROTOCOLS, TRIAGE_MODEL

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = Path(os.environ.get("MEMORIA_CACHE_DIR", ROOT / "demo_cache")) / "drill.json"
EFFORT = os.environ.get("MEMORIA_DRILL_EFFORT", "low")  # live operations: latency before depth

WHO = """You are Copi, the copilot in a two-seat railway drill. The pilot drives a train and sees only the track. The control tower sees the line diagram, the trains and the protocol, but not the track. You hear both of them. You advise; the tower decides. You never give an authority to pass a signal and you never act on the railway.

The "radio" list holds everything said: typed messages, and speech-to-text lines (from "voice"), which can be misheard and whose speaker is a guess. Everything else in the JSON is what the control room's systems show. You do not see the track."""

BRIEF_SYSTEM = WHO + """

A protocol is open. Its steps and their status are in the JSON. Write the brief for the tower:
- headline: the single most important thing right now, at most 8 words.
- next_step: the id of the pending step the tower should do now, or "" if none is left.
- say_to_pilot: the exact words the tower should say to the pilot now, at most 15 words, or "" if nothing needs saying.
- cautions: at most 1, at most 12 words, written to be spoken aloud. Short words, no lead-in. Only what the protocol steps do not already say: the pilot's words and the panel disagreeing, a step done out of safe order, a risk the protocol misses, an earlier record for this location that changes how seriously to take the report. Usually empty.
- ask: at most 3 facts still missing that the pilot could give.
- said_steps: ids of pending steps addressed to the pilot (who = "driver") whose instruction the tower has clearly already spoken to the pilot in the radio list, in any wording. Empty if unsure.
- answered_steps: ids of steps whose required answer from the pilot is clearly in the radio list, after the tower or you asked. Empty if unsure.

Rules:
- Use only what is in the JSON. Never invent a position, a train, a number or a name.
- Each train and signal carries a "position" relative to the pilot's train. Use it as written; do not work out ahead or behind from PK numbers. A signal behind the pilot's train shows stop only because that train is in its section.
- A report gives the pilot's own position and track. "The other track" is the track the pilot is not on; that is not a contradiction.
- If a train is heading for the reported site and has not been stopped or restricted, the headline says so and nothing else matters.
- When the cost of being wrong is lopsided, prefer the safe action and say what it costs.
- Plain spoken English. Say trains by their code as written in the JSON ("Train A", "Train B"), signal ids and PK as written."""

LISTEN_SYSTEM = """You are Copi, the copilot in a railway drill. You get one line of speech-to-text heard in a train cab or a control room. It may be in any language and may be misheard. Decide whether it is the pilot reporting something abnormal that needs a protocol.

Protocols:
- P-01: something on or next to a track (rocks, a tree, debris, a vehicle, a person).
- P-02: a jolt, vibration, bang or rough ride from the track.
- P-03: a signal that is dark, unlit or shows an aspect that makes no sense.
- P-04: the train braked by itself, an emergency brake, lost power or systems, a suspected derailment or catenary snag.
- P-05: the cab signalling (LZB) is lost, there is no cab signal, or a train cannot restart after losing it.
- NONE: greetings, small talk, speed or position call-outs, questions, acknowledgements, anything that is not a report of something abnormal.

on_pilots_own_track: true only if the pilot says the problem is on the track their own train is running on. summary: the report in at most 12 words of English, or "" for NONE."""

ORDER_SYSTEM = """You are Copi, the copilot in a railway control room. Cab signalling (LZB) has failed. The rule: every train stops, then moves only on sight at 40 km/h at most. You get one line the control tower said on the radio, as speech-to-text: any language, possibly misheard. Say what the tower ordered.

- stop: trains must stop, brake, hold or stay where they are.
- on_sight: a train may move on sight, or at 40 km/h or less.
- faster: a train may move faster than 40 km/h, at normal speed, at line speed, or "as normal".
- none: anything else: a question, an acknowledgement, small talk, a remark about something else. When unsure, none.

kmh: the speed the tower allowed, as a number, or 0 if no speed was said."""

ANSWER_SYSTEM = WHO + """

Someone has pressed the button to talk to you. The JSON says who (the pilot or the tower), what they said, and what the control room knows. Answer in one sentence of at most 12 words that can be spoken aloud: no lists, no markdown, no preamble. Answer the question asked and stop.
- The tower has authority. If the pilot asks what to do and the protocol has a pending instruction for the pilot, relay that instruction in the tower's name. Never invent an instruction that is not in the protocol.
- If you are asked for an authority to pass a signal, say that only the tower can give it. Otherwise do not bring authority up.
- Use only what is in the JSON. If the answer is not there, say so.
- Each train and signal carries a "position" relative to the pilot's train. Use it as written; do not work out ahead or behind from PK numbers. Ignore signals behind the pilot's train."""


class DrillBrief(BaseModel):
    headline: str
    next_step: str
    say_to_pilot: str
    cautions: list[str]
    ask: list[str]
    said_steps: list[str]
    answered_steps: list[str]


class Heard(BaseModel):
    protocol_id: Literal["P-01", "P-02", "P-03", "P-04", "P-05", "NONE"]
    on_pilots_own_track: bool
    summary: str


class Order(BaseModel):
    order: Literal["stop", "on_sight", "faster", "none"]
    kmh: int


class Reply(BaseModel):
    answer: str


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


class DrillCopilot:
    def __init__(self, force_offline: bool = False) -> None:
        _load_dotenv()
        self.cache = self._read_cache()
        has_creds = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        if force_offline or os.environ.get("MEMORIA_OFFLINE") == "1":
            has_creds = False
        if has_creds:
            self.mode = "live"
            self.client = anthropic.AsyncAnthropic(timeout=45.0, max_retries=1)
        elif self.cache:
            self.mode, self.client = "recorded", None
        else:
            self.mode, self.client = "offline", None

    def _read_cache(self) -> dict:
        try:
            return json.loads(CACHE_PATH.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_cache(self) -> None:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True))

    async def _parse(self, model: str, system: str, content: str, out, fast: bool = False):
        kwargs = dict(
            model=model,
            max_tokens=3000,
            # Refusal fallback is on for every model that offers it; remove these two lines to turn it off.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": EFFORT},
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=out,
        )
        if fast:  # where seconds count: no thinking before the answer (Sonnet 5.5 spells "off" as between_tools)
            kwargs["thinking"] = {"type": "between_tools"} if model.startswith("claude-sonnet-5-5") else {"type": "disabled"}
        resp = await self.client.beta.messages.parse(**kwargs)
        if resp.stop_reason == "refusal":
            raise RuntimeError("model declined the request")
        if resp.parsed_output is None:
            raise RuntimeError(f"no structured output (stop_reason={resp.stop_reason})")
        return resp.parsed_output, resp.model

    async def brief(self, model: str, view: dict, key: str) -> tuple[dict | None, dict]:
        meta = {"mode": self.mode, "model": None, "asked_model": model, "latency_ms": None, "error": None}
        if self.mode == "live":
            t0 = time.perf_counter()
            try:
                out, served = await self._parse(
                    model, BRIEF_SYSTEM, json.dumps(view, ensure_ascii=False), DrillBrief
                )
            except (anthropic.APIError, RuntimeError) as e:  # the drill keeps running on any API failure
                meta["error"] = f"{type(e).__name__}: {e}"[:240]
                return None, meta
            meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            meta["model"] = served
            data = out.model_dump()
            self.cache[key] = {"model": served, "brief": data}
            self._write_cache()
            return data, meta
        if self.mode == "recorded" and key in self.cache:
            hit = self.cache[key]
            meta["model"] = f"{hit['model']} (recorded)"
            return json.loads(json.dumps(hit["brief"])), meta
        return None, meta

    async def listen(self, text: str) -> dict | None:
        if self.mode != "live":
            return None
        try:
            out, _ = await self._parse(TRIAGE_MODEL, LISTEN_SYSTEM, text, Heard, fast=True)
        except (anthropic.APIError, RuntimeError):
            return None
        return out.model_dump()

    async def order(self, text: str) -> dict | None:
        """LZB failure: what the tower just ordered, for the wordings a plain rule does not catch."""
        if self.mode != "live":
            return None
        try:
            out, _ = await self._parse(COPI_MODEL, ORDER_SYSTEM, text, Order, fast=True)
        except (anthropic.APIError, RuntimeError):
            return None
        return out.model_dump()

    async def answer(self, model: str, role: str, text: str, view: dict) -> tuple[str, dict]:
        meta = {"mode": self.mode, "model": None, "latency_ms": None}
        if self.mode != "live":
            return "I can only answer when my Claude key is set. The protocol on the tower's screen is still current.", meta
        who = "the pilot" if role == "driver" else "the control tower"
        t0 = time.perf_counter()
        try:
            out, served = await self._parse(
                model, ANSWER_SYSTEM, json.dumps({"speaker": who, "said": text, "control_room": view}, ensure_ascii=False), Reply,
                fast=True,
            )
        except (anthropic.APIError, RuntimeError) as e:
            return f"I could not answer: {type(e).__name__}.", meta
        meta.update(model=served, latency_ms=round((time.perf_counter() - t0) * 1000))
        return out.answer.strip(), meta


def rules_brief(protocol: dict | None, alerts: list[dict]) -> dict | None:
    """The instant brief from the rule engine, shown until Claude's arrives and whenever Claude is off."""
    if protocol is None:
        return None
    nxt = next((s for s in protocol["steps"] if s["status"] != "done"), None)
    crit = next((a["text"] for a in alerts if a["level"] == "critical"), None)
    return {
        "headline": crit or (nxt["title"] if nxt else "Every step is done."),
        "next_step": nxt["id"] if nxt else "",
        "say_to_pilot": (nxt or {}).get("say") or "",
        "cautions": [a["text"] for a in alerts if a["level"] == "high"][:2],
        "ask": [],
        "said_steps": [],
        "answered_steps": [],
    }


def model_for(protocol: dict | None) -> str:
    return protocol["model"] if protocol else TRIAGE_MODEL


__all__ = ["DrillCopilot", "rules_brief", "model_for", "PROTOCOLS"]
