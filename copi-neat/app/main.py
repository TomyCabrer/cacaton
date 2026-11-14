"""Copi: FastAPI server, scenario replay and the operator console API."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import scenario as S
from .copilot import EFFORT, MODEL, Copilot, offline_briefing
from .drill_api import router as drill_router
from .voice_api import router as voice_router
from .memory import WorkingMemory
from .rules import RuleEngine

STATIC = Path(__file__).resolve().parent.parent / "static"
GAP_CAP_S = 3.0  # at 1x, any gap between events longer than this plays in 3 s
TICK_S = 0.2


class Hub:
    """Version counter + wake-up for SSE subscribers."""

    def __init__(self) -> None:
        self.version = 0
        self._event = asyncio.Event()

    def bump(self) -> None:
        self.version += 1
        self._event.set()
        self._event = asyncio.Event()

    async def wait(self, seen: int, timeout: float) -> None:
        if self.version != seen:
            return
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except asyncio.TimeoutError:
            pass


class Session:
    def __init__(self, scenario_name: str = "adamuz") -> None:
        self.sc = S.load(scenario_name)
        self.events = self.sc["events"]
        self.acts = {a["id"]: a for a in self.sc["acts"]}
        self.copilot = Copilot(self.sc["id"])
        self.hub = Hub()
        self.speed = 1.0
        self.auto_pause = True
        self.task: asyncio.Task | None = None
        self.generation = 0
        self.reset(integrations=True)

    # ----- lifecycle ----------------------------------------------------
    def reset(self, integrations: bool, act_id: str | None = None) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
        self.generation += 1
        self.mem = WorkingMemory()
        self.rules = RuleEngine(self.sc, self.mem)
        self.integrations = integrations
        self.idx = 0
        self.seen: list[dict] = []
        self.playing = False
        self.finished = False
        self.paused_reason: str | None = "Press play to start the replay."
        self.briefing: dict | None = None
        self.claude_driver: dict | None = None
        self.llm_busy = False
        self.llm_dirty = False
        self.qa: list[dict] = []
        self.handover: dict | None = None
        first_act = self.sc["acts"][0]
        self.act = first_act["id"]
        self.sim = S.parse_t(first_act["start"]) - timedelta(days=1)
        if act_id and act_id != first_act["id"]:
            act = self.acts[act_id]
            while self.idx < len(self.events) and self.events[self.idx]["t"] < act["start"]:
                self._process(self.events[self.idx], silent=True)
                self.idx += 1
            self.act = act_id
            self.sim = S.parse_t(act["start"])
            self.paused_reason = f"{act['title']} — {act['subtitle']}. Press play."
            self.request_brief()
        else:
            self.briefing = self._offline()
        self.hub.bump()

    @property
    def now(self) -> str:
        return S.fmt_t(self.sim)

    def play(self) -> None:
        if self.finished:
            return
        self.playing = True
        self.paused_reason = None
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._run(self.generation))
        self.hub.bump()

    def pause(self, reason: str | None = None) -> None:
        self.playing = False
        self.paused_reason = reason
        self.hub.bump()

    def step(self) -> None:
        if self.idx >= len(self.events):
            return
        nxt = self.events[self.idx]
        if nxt["act"] != self.act:
            self.act = nxt["act"]
        self.sim = max(self.sim, S.parse_t(nxt["t"]))
        self._process(nxt)
        self.idx += 1
        self._check_finished()
        self.hub.bump()

    async def _run(self, gen: int) -> None:
        try:
            while self.playing and gen == self.generation:
                if self.idx >= len(self.events):
                    self._check_finished()
                    break
                nxt = self.events[self.idx]
                if nxt["act"] != self.act:
                    act = self.acts[nxt["act"]]
                    self.act = act["id"]
                    self.sim = max(self.sim, S.parse_t(act["start"]))
                    if self.auto_pause:
                        self.pause(f"{act['title']} — {act['subtitle']}. Press play.")
                        break
                target = S.parse_t(nxt["t"])
                gap = (target - self.sim).total_seconds()
                if gap > 0:
                    start = self.sim
                    duration = min(gap, GAP_CAP_S) / self.speed
                    steps = max(1, round(duration / TICK_S))
                    for i in range(steps):
                        await asyncio.sleep(duration / steps)
                        if not self.playing or gen != self.generation:
                            return
                        self.sim = start + timedelta(seconds=gap * (i + 1) / steps)
                        self.hub.bump()
                self.sim = target
                new_critical = self._process(nxt)
                self.idx += 1
                self._check_finished()
                self.hub.bump()
                if new_critical and self.auto_pause:
                    self.pause("Critical recommendation raised. Decide, or press play to let time run.")
                    break
        except asyncio.CancelledError:
            pass

    def _check_finished(self) -> None:
        if self.idx >= len(self.events) and not self.finished:
            self.finished = True
            self.playing = False
            self.paused_reason = "Replay finished. See the comparison with what really happened."
            self.mem.note(self.now, "replay.end", "Replay finished")

    # ----- event processing ---------------------------------------------
    def _process(self, ev: dict, silent: bool = False) -> bool:
        """Feed one event. Returns True if a new critical recommendation appeared."""
        t = ev["t"]
        is_fed = S.fed(ev, self.integrations)
        self.seen.append({**ev, "fed": is_fed})
        if not is_fed:
            reason = "only known after the investigation" if ev.get("feed") == "hindsight" else "needs a proposed integration"
            self.mem.note(t, "event.unfed", f"{ev['id']} not available to Copi live ({reason})", evidence=[ev["id"]])
            return False
        before = {r.id for r in self.mem.recs if r.status == "pending" and r.urgency == "critical"}
        changed = self.rules.on_event(ev, t)
        after = {r.id for r in self.mem.recs if r.status == "pending" and r.urgency == "critical"}
        if changed and not silent:
            self.request_brief()
        return bool(after - before)

    # ----- Claude layer ---------------------------------------------------
    def _offline(self) -> dict:
        return {
            **offline_briefing(self.mem.snapshot(), self.rules.banner),
            "meta": {"mode": "offline", "based_on": self.now, "events": len(self.seen), "latency_ms": None, "error": None},
        }

    def _keys(self) -> list[str]:
        fed_ids = [e["id"] for e in self.seen if e["fed"]]
        return [f"{int(self.integrations)}|{i}" for i in reversed(fed_ids)] or [f"{int(self.integrations)}|start"]

    def request_brief(self) -> None:
        if self.copilot.mode == "offline":
            self.briefing = self._offline()
            return
        if self.llm_busy:
            self.llm_dirty = True
            return
        self.llm_busy = True
        asyncio.get_running_loop().create_task(self._brief_task(self.generation))

    async def _brief_task(self, gen: int) -> None:
        try:
            while gen == self.generation:
                self.llm_dirty = False
                based_on, n = self.now, len(self.seen)
                keys = self._keys()
                data, meta = await self.copilot.brief(self.llm_snapshot(), keys)
                if gen != self.generation:
                    return
                if data is None:
                    self.briefing = self._offline()
                    self.briefing["meta"]["error"] = meta.get("error") or (
                        "no recorded Claude briefing for this moment" if meta["mode"] == "recorded" else None
                    )
                else:
                    self._apply_briefing(data, meta, based_on, n)
                self.hub.bump()
                if not self.llm_dirty:
                    break
        finally:
            if gen == self.generation:
                self.llm_busy = False
                self.hub.bump()

    def _apply_briefing(self, data: dict, meta: dict, based_on: str, n: int) -> None:
        valid = {e["id"] for e in self.seen if e["fed"]}
        for h in data.get("hypotheses", []):
            h["evidence_ids"] = [i for i in h["evidence_ids"] if i in valid]
        for r in data.get("recommendations", []):
            ev = [i for i in r["evidence_ids"] if i in valid]
            if not ev or not r["target"].strip():
                self.mem.note(self.now, "validator.drop", f"Claude recommendation dropped (no valid evidence): {r['title']}")
                continue
            if len(ev) < len(r["evidence_ids"]):
                self.mem.note(self.now, "validator.trim", f"Removed unknown evidence ids from: {r['title']}")
            self.mem.recommend(
                r["action"], r["target"], r["title"], r["rationale"], ev, r["urgency"], r["cost_if_wrong"],
                self.now, source="claude",
            )
        if data.get("driver_train") and data.get("driver_message"):
            if any(tr["id"] == data["driver_train"] for tr in self.sc["trains"]):
                self.claude_driver = {"train": data["driver_train"], "text": data["driver_message"], "t": based_on}
        self.briefing = {
            **data,
            "meta": {
                "mode": meta["mode"], "model": meta.get("model"), "based_on": based_on, "events": n,
                "latency_ms": meta.get("latency_ms"), "error": None,
            },
        }

    def llm_snapshot(self) -> dict:
        """What Claude sees: only fed events, no hindsight notes, no train statuses."""
        mem = self.mem.snapshot()
        strip = lambda i: {k: i[k] for k in ("key", "text", "confidence", "evidence", "status", "detail", "resolution")}  # noqa: E731
        return {
            "sim_time": self.now,
            "phase": self.acts[self.act]["title"],
            "events": [
                {k: e[k] for k in ("id", "t", "channel", "text", "original") if k in e}
                for e in self.seen
                if e["fed"]
            ],
            "memory": {kind: [strip(i) for i in items] for kind, items in mem["items"].items()},
            "recommendations": [
                {k: r[k] for k in ("id", "action", "target", "title", "urgency", "status", "reason", "created", "decided_at", "source")}
                for r in mem["recommendations"]
            ],
            "train_describer": [
                {k: tr[k] for k in ("id", "track", "pk", "speed_kmh", "on_board")}
                for tr in S.train_positions(self.sc, self.now)
            ],
        }

    # ----- views --------------------------------------------------------
    def comparison(self) -> list[dict]:
        f, real = self.rules.firsts, self.sc["reality"]
        collision = real["collision"]

        def row(label, memoria, real_t, real_text):
            out = {"label": label, "memoria": memoria, "real": real_t, "real_text": real_text}
            if memoria and real_t:
                out["gain_min"] = round(S.seconds_between(memoria, real_t) / 60, 1)
            if memoria:
                out["vs_collision_min"] = round(S.seconds_between(collision, memoria) / 60, 1)
            return out

        return [
            row("Rail defect near PK 318.7 flagged", f.get("defect:flagged"), None, "Never flagged; found after the crash"),
            row("Defect escalated to close / restrict", f.get("defect:critical"), None, "Line open at line speed"),
            row("Alvia flagged as possibly involved", f.get("involved:ALVIA 2384"), real["alvia_involvement_known"],
                "First mention to the CTC: Iryo driver, 20:06:16"),
            row("Emergency response proposed for the Alvia", f.get("dispatch:ALVIA 2384"), real["alvia_confirmed_derailed"],
                "Second derailed train confirmed 20:16:29; first medics at the Alvia 20:35"),
        ]

    def snapshot(self) -> dict:
        nxt = self.events[self.idx] if self.idx < len(self.events) else None
        driver = self.rules.driver
        if self.claude_driver and (driver is None or self.claude_driver["t"] >= driver["t"]):
            driver = {**self.claude_driver, "source": "claude"}
        elif driver:
            driver = {**driver, "source": "rules"}
        return {
            "version": self.hub.version,
            "sim_time": self.now,
            "playing": self.playing,
            "finished": self.finished,
            "paused_reason": self.paused_reason,
            "speed": self.speed,
            "auto_pause": self.auto_pause,
            "integrations": self.integrations,
            "act": self.act,
            "next_event": nxt and {"id": nxt["id"], "t": nxt["t"], "act": nxt["act"]},
            "copilot": {"mode": self.copilot.mode, "busy": self.llm_busy, "model": MODEL, "effort": EFFORT},
            "events": self.seen,
            "memory": self.mem.snapshot(),
            "banner": self.rules.banner,
            "driver": driver,
            "trains": S.train_positions(self.sc, self.now),
            "briefing": self.briefing,
            "qa": self.qa[-8:],
            "handover": self.handover,
            "comparison": self.comparison(),
        }


class RemoteKey:
    """Anything that is not this laptop needs the join key.

    The drill is served to a second laptop over the LAN or a tunnel, and this server holds an
    API key that its endpoints spend. A request counts as local only if it comes from loopback,
    asks for localhost and was not forwarded by a tunnel. Everyone else must carry the key
    (the ?k= of the join link, which is then kept in a cookie).
    """

    def __init__(self, app, key: str) -> None:
        self.app, self.key = app, key

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        client = (scope.get("client") or ("", 0))[0]
        host = headers.get("host", "")
        host = host[: host.rindex(":")] if ":" in host and not host.endswith("]") else host
        forwarded = any(h in headers for h in ("cf-connecting-ip", "x-forwarded-for", "cf-ray"))
        if client in ("127.0.0.1", "::1", "testclient") and host in ("localhost", "127.0.0.1", "[::1]", "testserver") and not forwarded:
            return await self.app(scope, receive, send)
        in_query = parse_qs(scope.get("query_string", b"").decode("latin-1")).get("k", [""])[0]
        cookie = SimpleCookie(headers.get("cookie", ""))
        in_cookie = cookie["memoria_key"].value if "memoria_key" in cookie else ""
        given = in_query or in_cookie or headers.get("x-memoria-key", "")
        if not secrets.compare_digest(given.encode(), self.key.encode()):
            await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": b"Ask the control tower for the join link."})
            return

        async def send_with_cookie(message):
            if message["type"] == "http.response.start" and in_query:
                message = dict(message)
                message["headers"] = list(message.get("headers", [])) + [
                    (b"set-cookie", f"memoria_key={self.key}; Path=/; HttpOnly; SameSite=Lax".encode())
                ]
            await send(message)

        await self.app(scope, receive, send_with_cookie)


app = FastAPI(title="Copi")
app.state.access_key = os.environ.get("MEMORIA_KEY") or secrets.token_hex(4)
app.add_middleware(RemoteKey, key=app.state.access_key)
app.include_router(drill_router)
app.include_router(voice_router)
session: Session | None = None


def get_session() -> Session:
    global session
    if session is None:
        session = Session()
    return session


class Control(BaseModel):
    action: str
    act: str | None = None
    speed: float | None = None
    value: bool | None = None


class Decide(BaseModel):
    rec_id: str
    decision: str
    reason: str | None = None


class Ask(BaseModel):
    question: str


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/scenario")
async def scenario_info() -> dict:
    sc = get_session().sc
    return {k: sc[k] for k in ("id", "title", "line", "disclaimer", "sources", "acts", "infrastructure", "reality")}


@app.get("/api/state")
async def state() -> dict:
    return get_session().snapshot()


@app.get("/api/stream")
async def stream(request: Request) -> StreamingResponse:
    s = get_session()

    async def gen():
        seen = -1
        while True:
            if await request.is_disconnected():
                break
            await s.hub.wait(seen, 15.0)
            if s.hub.version != seen:
                seen = s.hub.version
                yield f"data: {json.dumps(s.snapshot(), ensure_ascii=False)}\n\n"
            else:
                yield ": keepalive\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/control")
async def control(c: Control) -> dict:
    s = get_session()
    if c.action == "play":
        s.play()
    elif c.action == "pause":
        s.pause("Paused.")
    elif c.action == "step":
        s.pause("Stepping one event at a time.")
        s.step()
    elif c.action == "reset":
        s.reset(s.integrations)
    elif c.action == "jump":
        if c.act not in s.acts:
            raise HTTPException(400, "unknown act")
        s.reset(s.integrations, c.act)
    elif c.action == "speed" and c.speed:
        s.speed = max(0.25, min(8.0, c.speed))
        s.hub.bump()
    elif c.action == "integrations" and c.value is not None:
        s.reset(c.value, s.act)
    elif c.action == "auto_pause" and c.value is not None:
        s.auto_pause = c.value
        s.hub.bump()
    else:
        raise HTTPException(400, "unknown action")
    return {"ok": True}


@app.post("/api/decide")
async def decide(d: Decide) -> dict:
    s = get_session()
    try:
        rec = s.mem.decide(d.rec_id, d.decision, (d.reason or "").strip() or None, s.now)
    except KeyError:
        raise HTTPException(404, "no such recommendation")
    except ValueError as e:
        raise HTTPException(409, str(e))
    s.request_brief()
    s.hub.bump()
    return {"ok": True, "status": rec.status}


@app.post("/api/ask")
async def ask(a: Ask) -> dict:
    s = get_session()
    q = a.question.strip()[:500]
    if not q:
        raise HTTPException(400, "empty question")
    entry = {"q": q, "asked_at": s.now, "pending": True}
    s.qa.append(entry)
    s.hub.bump()
    result = await s.copilot.ask(s.llm_snapshot(), q)
    valid = {e["id"] for e in s.seen if e["fed"]}
    result["evidence_ids"] = [i for i in result.get("evidence_ids", []) if i in valid]
    entry.update(result, pending=False)
    s.hub.bump()
    return entry


@app.post("/api/handover")
async def handover() -> dict:
    s = get_session()
    key = s._keys()[0]
    result = await s.copilot.handover(s.llm_snapshot(), key)
    if result is None:
        snap = s.mem.snapshot()
        items = snap["items"]
        result = {
            "summary": offline_briefing(snap, s.rules.banner)["headline"],
            "unresolved": [i["text"] for k in ("open_loop", "contradiction") for i in items[k] if i["status"] == "open"],
            "decisions_pending": [r["title"] for r in snap["recommendations"] if r["status"] == "pending"],
            "watch_next": [i["text"] for i in items["hypothesis"] if i["status"] == "open"][:3],
            "mode": "offline",
        }
    result["at"] = s.now
    s.handover = result
    s.hub.bump()
    return result


app.mount("/static", StaticFiles(directory=STATIC), name="static")
