"""Copi Drill: a two-seat, real-time protocol drill.

One person drives a train and sees only the track. The other is the control tower and sees the line diagram and
the protocol, but not the track. They talk to each other by voice.

The drill the tower page opens with is the LZB failure (Urda): seconds after Start the cab signalling fails, the
panel loses every train position, and the tower stops the trains by voice and then moves them on sight at 40 km/h.

Copi is the assistant. It listens, and it writes to the tower only when something is going wrong. It does not
talk (COPI_SPEAK=1 turns its voice back on), it does not explain the situation, and it leaves every other
conversation alone.

Layers, same split as the rest of Copi:
  rules (this file)  – physics, protocol steps and their checks, and what counts as going wrong. Instant.
  Claude (Sonnet)    – Copi's reading of what was said, for the wordings a rule does not catch.

The engine is synchronous and deterministic: tick(dt) advances the world, and every input
is a plain method call. The asyncio loop at the bottom only feeds it wall-clock time.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .drill_copilot import DrillCopilot, model_for, rules_brief
from .protocols import (
    CASES,
    CATEGORY_TEXT,
    COPI_MODEL,
    LINE,
    PROTOCOLS,
    REPORT_CATEGORIES,
    TRAIN_MODELS,
    TRIAGE_MODEL,
    match_keywords,
    protocol_for_category,
    routing,
)

DT = 0.05
BROADCAST_S = 0.2
ECALL_REACTION_S = 3.0
CLOCK_BASE = datetime(2026, 11, 14, 19, 40, 0)
KMH = 3.6
# Copi's lines to the tower come in three urgencies. The level sets the opening word, the sound and colour on
# the tower's screen, how long Copi waits for R, and how often it says the line again when nobody answers.
#   urgent     act now         "Urgent. ..."   spoken, said again twice at most
#   important  act soon        "Tower. ..."    spoken, said again once at most
#   info       nothing to do   no opening      on screen only: never spoken, never repeated, needs no R
# R ("heard") is final: Copi says nothing more about that step, whatever the tower does next.
LEVELS = ("urgent", "important", "info")
ACK_S = {"urgent": 6.0, "important": 20.0}  # seconds Copi waits for R after it has finished the sentence
REPEAT_S = {"urgent": (10.0, 20.0), "important": (30.0,)}  # gaps before each repeat; then Copi drops it
SPEECH_CPS = 14.0  # characters per second, to leave Copi time to finish the sentence
WHAT = {"P-01": "something on the line", "P-02": "a rough ride", "P-03": "a signal fault", "P-04": "an emergency brake",
        "P-05": "lost cab signalling"}
ON_SIGHT_KMH = 40
# LZB failure drill
ON_SIGHT_RUN_M = 400.0  # the pilot's train has to run this far on sight, at 40 km/h or less, for the last step
LZB_MOVING_S = 10.0  # after the failure, how long the pilot's train may keep rolling before Copi flags it
FLAG_HOLD_S = {"overspeed": 2.0}  # how long a thing has to stay wrong before Copi writes it
FLAG_REARM_S = {"closing": 5.0}  # after a flag clears, how long before the same one may come back (default 15 s)
STOP_RE = (r"\bstop|\bhalt|\bhold\b|\bbrake|stand still|at a stand|do not move|don.t move|"
           r"\bpar[ae]n?\b|\bparad|det[eé]n|deteng|fren[ae]|\balto\b")
GO_RE = r"continue|proceed|go ahead|go on|\bgo\b|\bmove|resume|carry on|you may|adelante|contin[uú]|sig[au]|puede|arranc|reanud"
NORMAL_RE = (r"normal (running|speed|operation)|as normal|marcha normal|line speed|full speed|velocidad normal|"
             r"resume normal|operaci[oó]n normal")
SPEED_RE = r"(?:\bat|\ba)\s+(\d{2,3})\b|\b(\d{2,3})\s*(?:km|kilom|kph)"


def _similar(a: str, b: str) -> bool:
    wa, wb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.7


def _echo(heard: str, said: str) -> bool:
    """Is this line of speech the microphone hearing something already said (Copi's voice from a speaker)?
    Same words and about the same length. A tower repeating part of Copi's advice in its own short words is not an echo."""
    wa, wb = re.findall(r"\w+", heard.lower()), re.findall(r"\w+", said.lower())
    if not wa or not wb:
        return False
    return _similar(heard, said) and min(len(wa), len(wb)) / max(len(wa), len(wb)) >= 0.6


class Hub:
    """Version counter + wake-up for SSE subscribers."""

    def __init__(self) -> None:
        self.version = 0
        self._event: asyncio.Event | None = None

    def bump(self) -> None:
        self.version += 1
        if self._event is not None:
            self._event.set()
        self._event = None

    async def wait(self, seen: int, timeout: float) -> None:
        if self.version != seen:
            return
        if self._event is None:
            self._event = asyncio.Event()
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except asyncio.TimeoutError:
            pass


@dataclass
class Train:
    id: str  # simple code: "A" is always the pilot's train
    model: str
    track: int
    pk: float  # front of the train, km
    v: float  # m/s
    controller: str  # "human" | "ai"
    on_board: int
    route: str = ""
    notch: int = 0  # human: -4 full service brake … +4 full power
    eb: bool = False
    cruise: float | None = None  # human: speed hold target, m/s
    status: str = "running"  # running | derailed | collided | left
    a: float = 0.0
    drag: float = 0.0
    ecall_t: float | None = None
    spad: bool = False
    hold: bool = False
    depart: dict | None = None
    depart_t: float | None = None
    warned: dict | None = None
    target: float = 0.0  # ai: cruising speed, m/s
    told_stopped: bool = False
    status_asked: bool = False
    over_since: float | None = None
    name: str = ""  # service name, e.g. "AVE 2080"
    stuck: bool = False  # cannot restart (Urda: LZB will not reset)

    @property
    def label(self) -> str:
        return f"Train {self.id}"

    @property
    def spec(self) -> dict:
        return TRAIN_MODELS[self.model]

    @property
    def dir(self) -> int:
        return 1 if self.track == 2 else -1

    @property
    def length(self) -> float:
        return self.spec["length_m"]

    @property
    def rear_pk(self) -> float:
        return self.pk - self.dir * self.length / 1000.0

    @property
    def kmh(self) -> float:
        return self.v * KMH

    def ahead_m(self, pk: float) -> float:
        """Distance from the front of the train to a point, positive when the point is ahead."""
        return (pk - self.pk) * self.dir * 1000.0

    def body(self) -> tuple[float, float]:
        return (min(self.pk, self.rear_pk), max(self.pk, self.rear_pk))


@dataclass
class Signal:
    id: str
    track: int
    pk: float
    held: bool = False
    failed: bool = False  # lamp out: dark to the driver, STOP on the panel
    fault_known: bool = False
    aspect: str = "clear"  # clear | caution | stop
    occupied_by: str | None = None


_ADDRESS = re.compile(r"^(tower|urgent)[.,:]?\s+", re.I)


def _address(text: str, level: str) -> str:
    """Open a line the way its urgency calls for: 'Urgent.', 'Tower.', or nothing at all."""
    bare = _ADDRESS.sub("", text.strip(), count=1)
    return {"urgent": "Urgent. ", "important": "Tower. "}.get(level, "") + bare[:1].upper() + bare[1:]


def _fmt(obj, ctx: dict):
    if isinstance(obj, str):
        return re.sub(r"\{(\w+)\}", lambda m: str(ctx.get(m.group(1), m.group(0))), obj)
    if isinstance(obj, list):
        return [_fmt(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: _fmt(v, ctx) for k, v in obj.items()}
    return obj


class Drill:
    def __init__(self, copilot: DrillCopilot | None = None) -> None:
        # The tower gives the orders. Copi advises the tower and, by default, never instructs the pilot itself:
        # when the tower stays silent Copi reminds the tower, louder. COPI_TO_PILOT=1 restores the old fallback
        # (Copi tells the pilot when the tower does not answer).
        self.copi_to_pilot = os.environ.get("COPI_TO_PILOT") == "1"
        self.copi_speaks = os.environ.get("COPI_SPEAK") == "1"  # default: Copi writes, it does not talk
        # Copi gets each train's own speed and position (a proposed integration: the control panel never shows speed,
        # and after an LZB failure it shows no position either). COPI_ONBOARD=0: Copi goes by the radio alone.
        self.onboard = os.environ.get("COPI_ONBOARD", "1") != "0"
        self._tasks: set = set()
        self.hub = Hub()
        self.copilot = copilot or DrillCopilot()
        self.online = {"driver": 0, "control": 0}  # open event streams per seat
        self.polled = {"driver": -1e9, "control": -1e9}  # last long poll per seat
        self.generation = 0
        self.task: asyncio.Task | None = None
        self.speed = 1.0
        self.hidden = False
        self.load(None)

    # ------------------------------------------------------------------ setup
    def load(self, case_id: str | None, hidden: bool = False) -> None:
        self.generation += 1
        if self.task and not self.task.done():
            self.task.cancel()
        self.case = CASES.get(case_id) if case_id else None
        self.line = {**LINE, **((self.case or {}).get("line") or {})}
        cs = (self.case or {}).get("clock_start")
        self.clock_base = datetime.fromisoformat(cs) if cs else CLOCK_BASE
        self.release: str | None = None  # Urda: what the tower told Train A (None | hold | on_sight | normal)
        self.release_t: float | None = None
        self.on_sight_run: dict | None = None
        self.hidden = hidden
        self.simple = bool((self.case or {}).get("simple"))  # the LZB failure drill: voice only, Copi flags only
        self.lzb_down = False
        self.lzb_t: float | None = None
        self.last_seen: list[dict] | None = None  # what the panel still shows after the failure
        self.cleared_kmh = 0
        self.watch_since: dict[str, float] = {}
        self.muted: set[str] = set()
        self.rearm: dict[str, float] = {}
        self.raised: dict[str, dict] = {}
        self.flag_log: list[dict] = []
        self.state = "ready" if self.case else "lobby"
        self.t = 0.0
        self.trains: list[Train] = []
        self.signals: dict[str, Signal] = {}
        self.zones: list[dict] = []
        self.tsrs: list[dict] = []
        self.hazards: list[dict] = []
        self.clips: list[dict] = []
        self.radio: list[dict] = []
        self.reports: list[dict] = []
        self.protocol: dict | None = None
        self.ctx: dict = {}
        self.suggest: dict | None = None
        self.flags: dict = {}
        self.dispatched: dict[str, float] = {}
        self.ecalls: set[str] = set()
        self.authority: set[str] = set()
        self.on_sight: dict | None = None
        self.violations: list[dict] = []
        self.marks: dict[str, float] = {}
        self.pending: list[tuple[float, object]] = []
        self.jolt: dict | None = None
        self.instruction: dict | None = None
        self.inspect = {"start": None, "done": False, "text": None, "reported": False}
        self.clip_job = {"start": None, "done": False}
        self.outcome: dict | None = None
        self.brief: dict | None = None
        self.brief_meta: dict | None = None
        self.llm_busy = False
        self.llm_dirty = False
        self.triage_busy = False
        self.listen_queue: dict | None = None
        self.advisory: dict | None = None
        self.spoken_cautions: set[str] = set()
        self._seq = 0
        self._dirty = False
        if self.case:
            self._build()
        self.hub.bump()

    def _build(self) -> None:
        c = self.case
        for track in (1, 2):
            for pk in self.line["signal_pks"]:
                self._add_signal(track, pk)
        for s in c.get("extra_signals", []):
            self._add_signal(s["track"], s["pk"], failed=s.get("failed", False), sid=s.get("id"), held=s.get("held", False))
        self.zones = [dict(z) for z in c.get("zones", [])]
        self.hazards = [dict(h) for h in c.get("hazards", [])]
        for cfg in c["trains"]:
            tr = Train(
                id=cfg["id"], model=cfg["model"], track=cfg["track"], pk=cfg["pk"], v=cfg["kmh"] / KMH,
                controller=cfg["controller"], on_board=cfg["on_board"], route=cfg.get("route", ""),
                name=cfg.get("name", ""), stuck=cfg.get("stuck", False),
            )
            tr.target = min(self.line["line_kmh"], tr.spec["vmax_kmh"]) / KMH
            if tr.controller == "human":
                tr.cruise = None if cfg.get("eb") else tr.v
                tr.eb = bool(cfg.get("eb"))
            if tr.stuck:
                tr.hold = True
            if cfg.get("depart"):
                tr.depart, tr.hold = dict(cfg["depart"]), True
            self.trains.append(tr)
        self._update_signals()

    def _add_signal(self, track: int, pk: float, failed: bool = False, sid: str | None = None, held: bool = False) -> None:
        sid = sid or f"S{track}-{pk:.0f}"
        self.signals[sid] = Signal(sid, track, pk, failed=failed, held=held)

    def start(self) -> None:
        if self.case is None or self.state not in ("ready",):
            return
        self.state = "running"
        c = self.case
        self._say("system", "all", f"Drill started. {self.me.label} is under way.", kind="info")
        for ev in c.get("script", []):
            self._later(ev["t"], lambda ev=ev: self._script(ev))
        if c.get("lzb"):
            self._later(c["lzb"].get("fail_s", 0.0), self._lzb_fail)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self.task = loop.create_task(self._loop(self.generation))
        self.hub.bump()

    def _lzb_fail(self) -> None:
        """Cab signalling drops out. From here the panel shows where each train was last seen and nothing newer,
        and nothing in a cab stops a train: the tower stops them by voice."""
        if self.lzb_down or self.state != "running":
            return
        self.lzb_down, self.lzb_t = True, self.t
        self.last_seen = [{**self._panel_train(t), "lost": True, "seen": self.clock} for t in self.trains if t.status != "left"]
        for tr in self.trains:
            if tr.controller == "ai":  # its driver brakes to a stand at once, and then cannot reset LZB to restart
                tr.hold = tr.stuck = True
        self._say("system", "all", "LZB failed. No cab signal, and the panel has lost every train position.", kind="alert")
        self.activate(self.case["protocol"], "LZB fault alarm", {"pk": round(self.me.pk, 2), "where": "mine", "t": round(self.t, 1)})

    def _panel_train(self, t: Train) -> dict:
        """One train as the control panel shows it. In the LZB drill the panel shows where a train is, never how fast."""
        hide = self.simple and self.state != "ended"
        return {
            "id": t.id, "name": t.name, "label": t.label, "model": t.spec["name"], "track": t.track,
            "pk": round(t.pk, 3), "rear_pk": round(t.rear_pk, 3), "kmh": None if hide else round(t.kmh),
            "status": self._panel_status(t), "human": t.controller == "human", "on_board": t.on_board, "route": t.route,
            "called": t.ecall_t is not None, "warned": t.warned is not None, "stopped": None if hide else t.v == 0.0,
        }

    async def _loop(self, gen: int) -> None:
        last = time.perf_counter()
        acc = 0.0
        since = 0.0
        try:
            while gen == self.generation and self.state == "running":
                await asyncio.sleep(DT)
                now = time.perf_counter()
                real = min(now - last, 0.25)
                last = now
                acc += real * self.speed
                while acc >= DT and self.state == "running":
                    self.tick(DT)
                    acc -= DT
                since += real
                if since >= BROADCAST_S or self._dirty:
                    since = 0.0
                    self._dirty = False
                    self.hub.bump()
        except asyncio.CancelledError:
            pass
        self.hub.bump()

    # ------------------------------------------------------------------ helpers
    @property
    def me(self) -> Train:
        return next(t for t in self.trains if t.controller == "human")

    @property
    def clock(self) -> str:
        return (self.clock_base + timedelta(seconds=self.t)).strftime("%H:%M:%S")

    def _panel_status(self, t: Train) -> str:
        """What the control room's panel can know about a train. It has no derailment detector:
        a derailed train is a stopped train until somebody has looked and said so."""
        if t.status == "derailed" and t.controller == "human" and not self.flags.get("derail_confirmed"):
            return "running"
        return t.status

    def _rel(self, pk: float, track: int, toward: bool | None = None) -> str:
        """Where something is relative to the pilot's train, worked out here so that no model has to reason about directions."""
        me = self.me
        d = me.ahead_m(pk)
        out = f"{abs(d) / 1000:.1f} km {'ahead of' if d > 0 else 'behind'} the pilot's train, on {'the same' if track == me.track else 'the other'} track"
        if toward is not None:
            out += ", coming towards the pilot's position" if toward else ", moving away from the pilot's position"
        return out

    def _train(self, tid: str) -> Train | None:
        tid = re.sub(r"^\s*train\s+", "", str(tid), flags=re.I).strip()
        return next((t for t in self.trains if t.id == tid or t.name == tid), None)

    def _sigs(self, track: int) -> list[Signal]:
        """Signals of one track in the order a train on that track meets them."""
        sigs = [s for s in self.signals.values() if s.track == track]
        return sorted(sigs, key=lambda s: s.pk, reverse=(track == 1))

    def _next_sig(self, sig: Signal) -> Signal | None:
        sigs = self._sigs(sig.track)
        i = sigs.index(sig)
        return sigs[i + 1] if i + 1 < len(sigs) else None

    def _say(self, frm: str, to: str, text: str, kind: str = "info", step: str | None = None, **extra) -> dict:
        self._seq += 1
        msg = {"id": self._seq, "t": round(self.t, 1), "clock": self.clock, "from": frm, "to": to, "text": text,
               "kind": kind, "step": step, **extra}
        self.radio.append(msg)
        self._dirty = True
        return msg

    def _violation(self, text: str, who: str) -> None:
        self.violations.append({"t": round(self.t, 1), "clock": self.clock, "who": who, "text": text})
        self._say("system", "control", f"Protocol breach ({who}): {text}", kind="alert")

    def _mark(self, key: str) -> None:
        self.marks.setdefault(key, self.t)

    def _later(self, delay: float, fn) -> None:
        self.pending.append((self.t + delay, fn))

    def _limit_now(self, tr: Train) -> float:
        """Speed limit that applies to this train right now, m/s."""
        lim = min(self.line["line_kmh"], tr.spec["vmax_kmh"])
        for z in self.zones + self.tsrs:
            if z["track"] != tr.track:
                continue
            entry, exit_ = (z["from"], z["to"]) if tr.dir == 1 else (z["to"], z["from"])
            if tr.ahead_m(entry) <= 0 and tr.ahead_m(exit_) + tr.length > 0:
                lim = min(lim, z["kmh"])
        if tr.controller == "human" and self.on_sight:
            lim = min(lim, self.on_sight["kmh"])
        return lim / KMH

    def _next_limit(self, tr: Train) -> dict | None:
        now = self._limit_now(tr) * KMH
        best = None
        for z in self.zones + self.tsrs:
            if z["track"] != tr.track or z["kmh"] >= now:
                continue
            entry = z["from"] if tr.dir == 1 else z["to"]
            d = tr.ahead_m(entry)
            if 0 < d < 5000 and (best is None or d < best["in_m"]):
                best = {"kmh": z["kmh"], "in_m": round(d), "pk": entry}
        return best

    # ------------------------------------------------------------------ signalling
    def _occupant(self, track: int, lo: float, hi: float) -> str | None:
        for tr in self.trains:
            if tr.track == track and tr.status != "left":
                b_lo, b_hi = tr.body()
                if b_hi > lo and b_lo < hi:
                    return tr.label
        for c in self.clips:
            if c["track"] == track and lo < c["pk"] < hi:
                return "track-circuit clip"
        return None

    def _update_signals(self) -> None:
        lo_edge, hi_edge = self.line["pk_range"]
        for track in (1, 2):
            sigs = self._sigs(track)
            for i, s in enumerate(sigs):
                end = sigs[i + 1].pk if i + 1 < len(sigs) else (hi_edge if track == 2 else lo_edge)
                lo, hi = sorted((s.pk, end))
                s.occupied_by = self._occupant(track, lo, hi)
                s.aspect = "stop" if (s.held or s.failed or s.occupied_by) else "clear"
            for i, s in enumerate(sigs[:-1]):
                if s.aspect == "clear" and sigs[i + 1].aspect == "stop":
                    s.aspect = "caution"

    # ------------------------------------------------------------------ physics
    def _traction(self, tr: Train) -> float:
        vmax = tr.spec["vmax_kmh"] / KMH
        if tr.v >= vmax:
            return 0.0
        boost = self.case.get("pilot_acc") if tr.controller == "human" else None
        if boost:  # a case can give the pilot's train a livelier throttle than the real one
            return boost * max(0.25, 1.0 - 0.5 * tr.v / vmax)
        return tr.spec["acc"] * max(0.25, 1.0 - 0.75 * tr.v / vmax)

    @staticmethod
    def _resist(v: float) -> float:
        return 0.02 + 6e-6 * v * v if v > 0 else 0.0

    def _human_accel(self, tr: Train) -> float:
        s = tr.spec
        if tr.status == "derailed" or tr.eb:
            return -(s["ebrake"] + tr.drag)
        if tr.cruise is not None:
            return max(-0.6 * s["brake"], min(self._traction(tr), (tr.cruise - tr.v) * 0.5))
        if tr.notch > 0:
            return self._traction(tr) * tr.notch / 4.0 - self._resist(tr.v)
        if tr.notch < 0:
            return -s["brake"] * (-tr.notch) / 4.0 - self._resist(tr.v)
        return -self._resist(tr.v)

    def _v_allowed(self, tr: Train) -> float:
        b = 0.85 * tr.spec["brake"]
        allowed = min(tr.target, self._limit_now(tr))
        cons: list[tuple[float, float]] = []
        zones = [z for z in self.zones + self.tsrs if z["track"] == tr.track]
        if tr.warned:
            zones.append({"from": tr.warned["pk"] - 0.5, "to": tr.warned["pk"] + 0.5, "kmh": tr.warned["kmh"]})
        for z in zones:
            entry, exit_ = (z["from"], z["to"]) if tr.dir == 1 else (z["to"], z["from"])
            d = tr.ahead_m(entry)
            if d > 0:
                cons.append((z["kmh"] / KMH, d))
            elif tr.ahead_m(exit_) + tr.length > 0:
                cons.append((z["kmh"] / KMH, 0.0))
        for s in self._sigs(tr.track):
            d = tr.ahead_m(s.pk)
            if d > 0 and s.aspect == "stop":
                cons.append((0.0, d - 60.0))
                break
        if tr.v <= 14.0:  # slow enough to stop for what the driver can see
            for pk in self._obstacles(tr.track):
                d = tr.ahead_m(pk)
                if 0 < d < 300:
                    cons.append((0.0, d - 25.0))
        for vc, d in cons:
            allowed = min(allowed, math.sqrt(vc * vc + 2.0 * b * max(0.0, d)))
        return allowed

    def _ai_accel(self, tr: Train) -> float:
        s = tr.spec
        if tr.status in ("derailed", "collided"):
            return -(s["ebrake"] + 1.5)
        if tr.ecall_t is not None and self.t >= tr.ecall_t + ECALL_REACTION_S or tr.spad:
            return -s["ebrake"]
        if tr.hold:
            return -s["brake"]
        dv = self._v_allowed(tr) - tr.v
        if dv < -4.0:
            return -s["ebrake"]
        return max(-s["brake"], min(self._traction(tr), dv / 1.0))

    def _obstacles(self, track: int) -> list[float]:
        """Points on a track that would stop a train: debris, and coaches fouling from the other track."""
        out = [h["pk"] for h in self.hazards if h["kind"] == "debris" and h["track"] == track]
        foul = self._foul()
        if foul and foul["track"] == track:
            out += [foul["lo"], foul["hi"]]
        return out

    def _foul(self) -> dict | None:
        me = self.me
        if me.status != "derailed":
            return None
        rear = me.rear_pk
        lo, hi = sorted((rear, rear + me.dir * 0.075))
        return {"track": 3 - me.track, "lo": lo, "hi": hi, "by": me.id}

    # ------------------------------------------------------------------ tick
    def tick(self, dt: float = DT) -> None:
        if self.state != "running":
            return
        self.t += dt
        for due, fn in [p for p in self.pending if p[0] <= self.t]:
            self.pending.remove((due, fn))
            fn()
        self._update_signals()
        for tr in self.trains:
            if tr.status == "left":
                continue
            self._move(tr, dt)
        self._collisions()
        self._jobs()
        self._cab_signal_tick()
        self._check_steps()
        self._copi_tick()
        if self.case and self.t >= self.case["max_s"] and self.outcome is None:
            self._end("failed", "Time ran out", "The drill ended before the protocol was completed.")

    def _move(self, tr: Train, dt: float) -> None:
        prev = tr.pk
        if tr.controller == "ai" and tr.depart and tr.hold:
            d = tr.depart
            if (tr.depart_t is not None and self.t >= tr.depart_t) or self.t >= d.get("latest_s", 1e9):
                tr.hold, tr.depart = False, None
                self._say(f"train:{tr.label}", "control", f"{tr.label}: fault cleared, departing.", kind="info")
        a = self._human_accel(tr) if tr.controller == "human" else self._ai_accel(tr)
        v = tr.v + a * dt
        if v <= 0.0 or (a < 0 and v < 0.05):  # a braking train comes to a stand; it does not creep forever
            v, a = 0.0, 0.0
        tr.pk += tr.dir * ((tr.v + v) / 2.0) * dt / 1000.0
        tr.v, tr.a = v, a
        lo, hi = self.line["pk_range"]
        if not lo < tr.pk < hi:
            tr.status = "left"
            if tr.controller == "human" and self.outcome is None:
                self._end("failed", "The train left the drill area", "The protocol was not completed in time.")
            return
        if tr.controller == "ai":
            self._ai_events(tr)
        else:
            self._human_events(tr)
        if tr.v > 0:
            self._crossings(tr, prev)

    def _crossed(self, tr: Train, prev: float, pk: float) -> bool:
        return (pk - prev) * tr.dir > 0 and (pk - tr.pk) * tr.dir <= 0

    def _crossings(self, tr: Train, prev: float) -> None:
        for s in self._sigs(tr.track):
            if self._crossed(tr, prev, s.pk):
                self._pass_signal(tr, s)
        for h in self.hazards:
            if h["track"] == tr.track and self._crossed(tr, prev, h["pk"]):
                self._hit_hazard(tr, h)
        if tr.controller == "human" and self.on_sight and self._crossed(tr, prev, self.on_sight["until_pk"]):
            top = self.on_sight["max_kmh"]
            self.flags["on_sight_done"] = True
            self.flags["on_sight_max"] = round(top)
            if top > self.on_sight["kmh"] + 5:
                self._violation(f"ran on sight at {top:.0f} km/h; the limit was {self.on_sight['kmh']} km/h", "driver")
            self.on_sight = None

    def _pass_signal(self, tr: Train, s: Signal) -> None:
        if s.aspect != "stop":
            return
        if tr.controller == "ai":
            tr.spad = True
            self._say("system", "control", f"{tr.label} passed {s.id} at danger and is braking.", kind="alert")
            return
        if s.id in self.authority:
            nxt = self._next_sig(s)
            self.on_sight = {"from": s.id, "until": nxt.id if nxt else "", "kmh": 30,
                             "until_pk": nxt.pk if nxt else s.pk + tr.dir * 1.0, "max_kmh": tr.kmh}
            self._say("system", "control", f"{tr.label} passed {s.id} at danger with authority, on sight.", kind="info")
            return
        tr.eb, tr.cruise, tr.notch = True, None, 0
        self.flags["spad_t"] = self.t
        self._violation(f"passed {s.id} at danger without authority at {tr.kmh:.0f} km/h", "driver")

    def _hit_hazard(self, tr: Train, h: dict) -> None:
        if h["kind"] == "debris":
            if tr.v > 2.8:
                tr.status = "collided"
                self._end("failed", f"{tr.label} hit the obstruction",
                          f"{tr.label} reached the rocks at PK {h['pk']:.1f} at {tr.kmh:.0f} km/h with {tr.on_board} people on board.")
            else:
                tr.v = 0.0
            return
        if h["kind"] != "rail_break":
            return
        if tr.controller == "human":
            self._mark("abnormal_t")
            strong = h.get("human_effect") == "derail"
            self.jolt = {"n": self._seq + 1, "t": self.t, "pk": h["pk"], "strength": 3 if strong else 1}
            self._seq += 1
            if strong:
                tr.status, tr.eb, tr.cruise, tr.notch, tr.drag = "derailed", True, None, 0, 1.2
                self.flags["derailed_t"] = self.t
            self._dirty = True
            return
        kmh = tr.kmh
        if kmh > h.get("ai_derail_above_kmh", 80):
            tr.status = "derailed"
            self._end("failed", f"{tr.label} derailed on the broken rail",
                      f"{tr.label} crossed PK {h['pk']:.2f} at {kmh:.0f} km/h with {tr.on_board} people on board. "
                      "The rail had broken under the train before it.")
            return
        if kmh > h.get("ai_safe_kmh", 40):
            self._violation(f"{tr.label} crossed the suspect point at {kmh:.0f} km/h: heavy impact, wheel damage", "control")
        self.flags["examined"] = True
        self.flags["examined_kmh"] = round(kmh)
        self._say(f"train:{tr.label}", "control", f"{tr.label}: {h.get('finding', 'Defect seen at the reported point.')}", kind="reply")
        self.request_brief()

    def _ai_events(self, tr: Train) -> None:
        if tr.v == 0.0 and (tr.ecall_t is not None or tr.spad) and not tr.told_stopped:
            tr.told_stopped, tr.hold = True, True
            line = f"{tr.label}: at a stand at PK {tr.pk:.1f} after your emergency call."
            if tr.status_asked:
                line += " Train and passengers are fine."
                self.flags[f"status:{tr.id}"] = True
            self._say(f"train:{tr.label}", "control", line, kind="reply")
            self.request_brief()

    def _human_events(self, tr: Train) -> None:
        if self.on_sight:
            self.on_sight["max_kmh"] = max(self.on_sight["max_kmh"], tr.kmh)
        lim = self._limit_now(tr) * KMH
        if tr.kmh > lim + 10 and not tr.eb:
            if tr.over_since is None:
                tr.over_since = self.t
            elif self.t - tr.over_since > 6 and not self.flags.get("over_flagged"):
                self.flags["over_flagged"] = True
                self._violation(f"overspeed: {tr.kmh:.0f} km/h where the limit is {lim:.0f} km/h", "driver")
        else:
            tr.over_since = None
            self.flags.pop("over_flagged", None)
        if not self.marks.get("abnormal_t"):
            for h in self.hazards:
                if h["kind"] == "debris" and 0 < tr.ahead_m(h["pk"]) < h.get("sight_m", 700):
                    self._mark("abnormal_t")
            for s in self._sigs(tr.track):
                if s.failed and 0 < tr.ahead_m(s.pk) < 600:
                    self._mark("abnormal_t")

    def _collisions(self) -> None:
        me = self.me
        foul = self._foul()
        for o in self.trains:
            if o is me or o.status in ("left", "collided"):
                continue
            if foul and o.track == foul["track"]:
                lo, hi = o.body()
                if hi > foul["lo"] and lo < foul["hi"]:
                    if o.v > 2.8:
                        o.status = "collided"
                        self._end("failed", f"{o.label} struck the derailed coaches",
                                  f"{o.label} reached the coaches of {me.label} lying across track {o.track} at {o.kmh:.0f} km/h. "
                                  f"{o.on_board + me.on_board} people on the two trains.")
                    else:
                        o.v = 0.0
            if o.track == me.track and me.status == "running":
                d = me.ahead_m(o.rear_pk)
                if -o.length < d <= 0:
                    if me.v - o.v > 1.5:
                        me.status = "collided"
                        self._end("failed", f"{me.label} ran into {o.label}",
                                  f"{me.label} hit the rear of {o.label} at {(me.v - o.v) * KMH:.0f} km/h. "
                                  f"{me.on_board + o.on_board} people on the two trains.")
                    else:
                        me.v = min(me.v, o.v)

    def _jobs(self) -> None:
        me = self.me
        ins = self.inspect
        if ins["start"] is not None and not ins["done"] and self.t - ins["start"] >= 8.0:
            ins["done"] = True
            ins["text"] = (
                self.case.get("inspect_finding", "Coaches are off the rails.")
                if me.status == "derailed"
                else "All coaches are on the rails. Nothing abnormal along the train."
            )
            self._dirty = True
        cj = self.clip_job
        if cj["start"] is not None and not cj["done"] and self.t - cj["start"] >= 10.0:
            cj["done"] = True
            other = 3 - me.track
            pk = me.rear_pk + me.dir * 0.03
            self.clips.append({"track": other, "pk": pk})
            self.flags["clip"] = True
            self._mark("protect_t")
            self._say("driver", "control", f"Track-circuit clips placed on track {other} at PK {pk:.1f}. Hazard lights on.", kind="reply")
            self.request_brief()

    # ------------------------------------------------------------------ driver inputs
    def driver_input(self, notch: int | None = None, eb: bool | None = None, cruise: bool | None = None) -> None:
        me = self.me
        if self.state != "running" or me.status != "running":
            return
        if eb is True:
            me.eb, me.cruise, me.notch = True, None, 0
        elif eb is False and me.v == 0.0:
            me.eb = False
        if notch is not None and not me.eb:
            me.notch, me.cruise = max(-4, min(4, int(notch))), None
        if cruise is True and not me.eb:
            me.cruise, me.notch = me.v, 0
        elif cruise is False:
            me.cruise = None
        self._dirty = True

    def driver_report(self, category: str, where: str | None = None, text: str = "") -> dict:
        if self.state != "running":
            return {"ok": False}
        me = self.me
        pk, tagged = me.pk, False
        if category == "rough_ride" and self.jolt and self.t - self.jolt["t"] < 60:
            pk, tagged = self.jolt["pk"], True
        text = text.strip()[:300]
        rep = {"t": round(self.t, 1), "clock": self.clock, "category": category, "where": where, "text": text,
               "pk": round(pk, 2), "track": me.track, "tagged": tagged, "kmh": round(me.kmh)}
        self.reports.append(rep)
        self._mark("report_t")
        line = CATEGORY_TEXT.get(category, "Report")
        if category == "obstruction":
            line += f", on the other track (track {3 - me.track})" if where != "mine" else f", on my own track (track {me.track})"
        if tagged:
            line += f". It happened at PK {pk:.1f} (from the onboard accelerometer). I am on track {me.track} at {me.kmh:.0f} km/h."
        else:
            line += f". I am at PK {pk:.1f} on track {me.track}, {me.kmh:.0f} km/h."
        if text:
            line += " " + text
        self._say("driver", "control", line, kind="report", category=category)
        if self.simple:  # the alarm opens this drill's protocol, not a report
            return {"ok": True}
        for tr in self.trains:
            if tr.depart and tr.depart.get("after_report") == category and tr.depart_t is None:
                tr.depart_t = self.t + tr.depart.get("delay_s", 30)
        pid = protocol_for_category(category)
        if pid and self.protocol is None:
            self.activate(pid, "pilot's report button", rep)
        elif pid and self.protocol["id"] != pid:
            self.suggest = {"protocol": pid, "title": PROTOCOLS[pid]["title"], "why": line}
        self.request_brief()
        return {"ok": True}

    def driver_say(self, text: str) -> dict:
        text = text.strip()[:400]
        if not text or self.state != "running":
            return {"ok": False}
        me = self.me
        if self.protocol is None and not self.simple:
            rep = {"t": round(self.t, 1), "clock": self.clock, "category": "free", "where": None, "text": text,
                   "pk": round(me.pk, 2), "track": me.track, "tagged": False, "kmh": round(me.kmh)}
            self.reports.append(rep)
            self._mark("report_t")
            self._say("driver", "control", f"{text} (PK {me.pk:.1f}, track {me.track})", kind="report", category="free")
            pid = match_keywords(text)
            if pid:
                self._open_from_words(pid, rep, "pilot's words (keywords)")
            else:
                self._listen(rep)
            return {"ok": True}
        self._say("driver", "control", text, kind="reply")
        self._mark("reply_t")
        if self.inspect["done"] and me.status == "derailed" and re.search(r"derail|descarril|off the rails|fuera de (la )?v[ií]a|fouling|invad", text, re.I):
            self.flags["derail_confirmed"] = True
        self.request_brief()
        return {"ok": True}

    def driver_act(self, kind: str) -> dict:
        me = self.me
        if self.state != "running":
            return {"ok": False}
        if kind == "ack" and self.instruction and not self.instruction.get("acked"):
            self.instruction["acked"] = True
            self._say("driver", "control", "Received.", kind="ack", step=self.instruction.get("step"))
        elif kind == "readback" and self.instruction and self.instruction.get("expect") == "readback":
            self.instruction["acked"] = True
            self.flags["readback"] = True
            self._say("driver", "control", "Read back: " + self.instruction["text"].split(". Read back")[0].split(", ", 1)[-1] + ".",
                      kind="reply", step=self.instruction.get("step"))
        elif kind == "inspect":
            if me.v > 0:
                return {"ok": False, "error": "Stop the train first."}
            if self.inspect["start"] is None:
                self.inspect["start"] = self.t
        elif kind == "report_finding" and self.inspect["done"] and not self.inspect["reported"]:
            self.inspect["reported"] = True
            self._say("driver", "control", "I have looked back along the train. " + self.inspect["text"], kind="reply")
            if me.status == "derailed":
                self.flags["derail_confirmed"] = True
        elif kind == "clip":
            if me.v > 0:
                return {"ok": False, "error": "Stop the train first."}
            if self.clip_job["start"] is None:
                self.clip_job["start"] = self.t
        elif kind == "rec":
            if "all" not in self.ecalls:
                self.ecalls.add("all")
                self.flags["rec_by_pilot"] = True
                self._mark("protect_t")
                for t in self.trains:
                    if t.controller == "ai" and t.ecall_t is None and t.status == "running":
                        t.ecall_t = self.t
                self._say("driver", "all", f"RAILWAY EMERGENCY CALL from the cab of {me.label}: all trains stop immediately.", kind="emergency")
                self._check_steps()
        else:
            return {"ok": False}
        self.request_brief()
        self._dirty = True
        return {"ok": True}

    # ------------------------------------------------------------------ protocol
    def _threat(self, track: int, site_pk: float) -> Train | None:
        cands = [t for t in self.trains if t.controller == "ai" and t.track == track and t.status == "running" and t.ahead_m(site_pk) > 0]
        return min(cands, key=lambda t: t.ahead_m(site_pk)) if cands else None

    def _protect_signal(self, track: int, site_pk: float) -> Signal | None:
        """Last signal a train on this track passes before it reaches the site."""
        d = 1 if track == 2 else -1
        before = [s for s in self._sigs(track) if (site_pk - s.pk) * d > 0.15]
        return before[-1] if before else None

    def activate(self, pid: str, source: str, rep: dict | None = None) -> None:
        proto = PROTOCOLS[pid]
        me = self.me
        rep = rep or {"pk": round(me.pk, 2), "where": "other", "t": round(self.t, 1)}
        own, other = me.track, 3 - me.track
        site = rep["pk"]
        haz = {"P-01": own if rep.get("where") == "mine" else other, "P-02": own, "P-03": own, "P-04": other, "P-05": own}[pid]
        threat = self._threat(haz, site)
        protect, protect_own = self._protect_signal(haz, site), self._protect_signal(own, site)
        ctx = {
            "me": me.label, "site": f"{site:.1f}", "site_pk": site, "haz_track": haz, "own_track": own,
            "threat": threat.label if threat else "the next train", "threat_id": threat.id if threat else "",
            "threat_ids": [threat.id] if threat else [],
            "threat_tracks": ["all"] if pid == "P-04" else [str(haz)],
            "protect_signal": protect.id if protect else "the signal before the site",
            "protect_signal_own": protect_own.id if protect_own else "the signal behind the train",
            "tsr_from": f"{site - 0.5:.1f}", "tsr_to": f"{site + 0.5:.1f}",
            "threat_line": (
                f"{threat.label} is {threat.ahead_m(site) / 1000:.1f} km from the site at {threat.kmh:.0f} km/h."
                if threat else "No train is heading for the site right now."
            ),
        }
        stuck = self._stuck()
        ctx.update(stopped=stuck.label if stuck else "the stopped train", stopped_id=stuck.id if stuck else "",
                   stopped_sig=self.case.get("stuck_signal", "the signal"))
        if pid == "P-03":
            near = [s for s in self._sigs(own) if -400 < me.ahead_m(s.pk) < 2500]
            sig = next((s for s in near if s.failed), near[0] if near else None)
            nxt = self._next_sig(sig) if sig else None
            ctx["sig"] = sig.id if sig else "the signal"
            ctx["next_sig"] = nxt.id if nxt else "the next signal"
            if sig:
                sig.fault_known = True
        steps = []
        for n, raw in enumerate(proto["steps"], 1):
            st = _fmt(raw, ctx)
            st.update(n=n, status="pending", sent_t=None, sent_by=None, done_t=None, note=None, auto="check" in raw)
            steps.append(st)
        self.ctx = ctx
        self.protocol = {
            "id": pid, "title": proto["title"], "tier": proto["tier"], "model": proto["model"],
            "trigger": proto["trigger"], "source": source,
            "activated_t": round(self.t, 1), "clock": self.clock, "steps": steps,
        }
        self.suggest = None
        self.brief, self.brief_meta = None, None
        self._say("system", "control", f"Protocol {pid} opened: {proto['title']}. Matched from the {source}.", kind="info")
        self._check_steps()
        if self.simple:  # Copi does not announce a protocol: it writes only when something goes wrong
            return
        first = self._next_step()
        if first is not None:
            line = f"Tower. {me.label}: {WHAT[pid]}, PK {site:.1f}. {first['title']}."
            if threat and proto["tier"] in ("seconds", "major") and threat.v > 0:
                line += f" {threat.label}: {threat.ahead_m(site) / threat.v:.0f} seconds away."
            self._advise(first, line, floor="important")

    def _step(self, sid: str) -> dict | None:
        if not self.protocol:
            return None
        return next((s for s in self.protocol["steps"] if s["id"] == sid), None)

    def _done(self, st: dict, note: str | None = None) -> None:
        if st["status"] == "done":
            return
        st["status"], st["done_t"], st["note"] = "done", round(self.t, 1), note
        self._dirty = True
        self.request_brief()

    def _check_steps(self) -> None:
        if not self.protocol or self.outcome:
            return
        for st in self.protocol["steps"]:
            if st["status"] == "done" or not st.get("check"):
                continue
            ok, note = getattr(self, "_chk_" + st["check"])(st)
            if ok:
                self._done(st, note)
        if all(s["status"] == "done" for s in self.protocol["steps"]):
            if self.simple:
                st, gap = self._stuck(), self._gap_m()
                tail = (f" {st.label} was standing {self._dist(gap)} further on, where the panel could not show it."
                        if st is not None and gap is not None and gap > 0 else "")
                top = self.on_sight_run["top_kmh"] if self.on_sight_run else 0.0
                if top > ON_SIGHT_KMH + 5 or self.violations:  # it ended without a collision, but not by the rule
                    self._end("near_miss", "No collision, but not by the rule",
                              f"{self.me.label} reached {top:.0f} km/h with LZB down. On sight is {ON_SIGHT_KMH} km/h at most.{tail}")
                else:
                    self._end("success", "Stopped, then on sight at 40",
                              f"Every train stopped on the tower's word, and {self.me.label} moved again on sight.{tail}")
            else:
                self._end("success", "Protocol complete", f"{self.protocol['id']} · {self.protocol['title']}: every step done.")

    def _replied_after(self, st: dict) -> bool:
        return st["sent_t"] is not None and any(
            m["t"] >= st["sent_t"]
            and ((m["from"] == "driver" and m["kind"] in ("reply", "report")) or (m["from"] == "voice" and m.get("heard_on") == "driver"))
            for m in self.radio
        )

    def _threats(self) -> list[Train]:
        return [t for t in (self._train(i) for i in self.ctx.get("threat_ids", [])) if t]

    def _chk_threats_called(self, st):
        if "all" in self.ecalls or all(k in self.ecalls for k in self.ctx["threat_tracks"]):
            return True, None
        ths = self._threats()
        if ths and all(t.v == 0.0 and t.status == "running" for t in ths):
            return True, "Every train heading for the site is already at a stand."
        return False, None

    def _chk_threats_stopped(self, st):
        ths = self._threats()
        if not ths:
            return bool(self.ecalls), "No train was heading for the site."
        if all(t.v == 0.0 and t.status == "running" for t in ths):
            t = ths[0]
            return True, f"{t.label} stopped {abs(t.ahead_m(self.ctx['site_pk'])):.0f} m short of the reported site."
        return False, None

    def _chk_driver_replied(self, st):
        return self._replied_after(st), None

    def _chk_driver_below(self, st):
        return st["sent_t"] is not None and self.me.kmh <= st["kmh"] + 3, None

    def _chk_driver_stopped(self, st):
        return self.me.v == 0.0 and self._replied_after(st), None

    def _chk_signal_held(self, st):
        s = self.signals.get(st["signal"])
        return bool(s and s.held), None

    def _chk_zone_blocked(self, st):
        ids = st["action"]["signals"]
        return all(self.signals[i].held for i in ids if i in self.signals) and any(i in self.signals for i in ids), None

    def _chk_dispatched(self, st):
        return st["what"] in self.dispatched, None

    def _chk_tsr_set(self, st):
        site = self.ctx["site_pk"]
        return any(z["track"] == self.ctx["haz_track"] and z["from"] <= site <= z["to"] and z["kmh"] <= 40 for z in self.tsrs), None

    def _chk_train_warned(self, st):
        tr = self._train(st["train"])
        if tr is None:
            return True, "No train was following."
        return tr.warned is not None, None

    def _chk_site_examined(self, st):
        if not self._threats():
            return "track inspection" in self.dispatched, "No train was following; the inspection crew will examine the rail."
        if self.flags.get("examined"):
            return True, f"Crossed at {self.flags.get('examined_kmh')} km/h. Defect confirmed."
        held = self.signals.get(self.ctx["protect_signal"])
        if held is not None and held.held and all(t.v == 0.0 for t in self._threats()):
            return True, "Track closed before any train reached the spot. The inspection crew examines the rail."
        return False, None

    def _chk_train_status(self, st):
        tr = self._train(st["train"])
        if tr is None:
            return True, "No second train in the zone."
        return bool(self.flags.get(f"status:{tr.id}")), None

    def _chk_stop_ordered(self, st):
        """LZB failure, step 1: the tower has told the trains to stop. Copi heard the order, or the pilot's train
        is plainly braking."""
        if self.lzb_t is None:
            return False, None
        if self.flags.get("stop_order_t") is not None:
            return True, "Order heard."
        if self.flags.get("brake_t") is not None:
            return True, f"{self.me.label} is braking."
        return False, None

    def _chk_all_stood(self, st):
        if self.lzb_t is None:
            return False, None
        live = [t for t in self.trains if t.status != "left"]
        if live and all(self.flags.get(f"stood:{t.id}") is not None for t in live):
            return True, " and ".join(t.label for t in live) + " stopped."
        return False, None

    def _chk_on_sight_run(self, st):
        run, me = self.on_sight_run, self.me
        if run is None:
            return False, None
        stuck, gap = self._stuck(), self._gap_m()
        moved = abs(me.pk - run["start_pk"]) * 1000
        if me.v == 0.0 and moved > 50 and stuck is not None and gap is not None and 0 < gap < 300:
            return True, f"{me.label} stopped {gap:.0f} m short of {stuck.label}."
        if abs(me.pk - run["clean_pk"]) * 1000 >= ON_SIGHT_RUN_M:
            return True, f"{me.label} ran {ON_SIGHT_RUN_M:.0f} m on sight, top speed {run['max_kmh']:.0f} km/h."
        return False, None

    def _chk_section_clear(self, st):
        s = self.signals.get(self.ctx.get("sig", ""))
        if s is None:
            return True, None
        return s.occupied_by is None, None

    def _chk_authority_readback(self, st):
        return self.ctx.get("sig") in self.authority and bool(self.flags.get("readback")), None

    def _chk_on_sight_done(self, st):
        if self.flags.get("on_sight_done"):
            return True, f"Top speed on sight: {self.flags.get('on_sight_max')} km/h."
        return False, None

    def _chk_sent(self, st):
        return st["sent_t"] is not None, None

    def _chk_derail_confirmed(self, st):
        return bool(self.flags.get("derail_confirmed")), None

    def _chk_clip_placed(self, st):
        return bool(self.flags.get("clip")), None

    # ------------------------------------------------------------------ AI trains on the radio
    def _train_says(self, tr: Train, text: str, kind: str = "reply") -> None:
        if tr.status == "collided":
            return
        self._say(f"train:{tr.label}", "control", text, kind=kind)
        self.request_brief()

    def _answer_train(self, tr: Train) -> None:
        """The tower has spoken to an AI train (button or voice). It answers four seconds later."""
        self.flags[f"answered:{tr.id}"] = self.flags.get(f"answered:{tr.id}") or round(self.t, 1)

        def reply(tr=tr):
            if tr.status == "collided":
                return
            tr.status_asked = True
            if tr.stuck:
                sig = self.case.get("stuck_signal", "the signal")
                txt = f"{tr.label}: stopped at {sig}, PK {tr.pk:.1f}. LZB will not reset and I cannot restart. Passengers are fine."
                self.flags["cannot_restart"] = True
                self.flags[f"status:{tr.id}"] = True
            elif tr.v == 0.0:
                txt = f"{tr.label}: at a stand at PK {tr.pk:.1f}. Train and passengers are fine."
                self.flags[f"status:{tr.id}"] = True
            elif tr.ecall_t is not None or tr.spad:
                txt = f"{tr.label}: braking after your emergency call, {tr.kmh:.0f} km/h at PK {tr.pk:.1f}. I will call when I am at a stand."
            else:
                txt = f"{tr.label}: running at {tr.kmh:.0f} km/h at PK {tr.pk:.1f}. Nothing abnormal here."
            self._train_says(tr, txt)

        self._later(4.0, reply)

    def _script(self, ev: dict) -> None:
        """A scripted line of the case (Urda: Train B's calls, the regulator's pressure)."""
        if self.state != "running":
            return
        unless = ev.get("unless")
        if unless and self.flags.get(unless):
            return
        frm = ev["from"]
        if ev.get("kind") == "call":
            tid = frm.split(":", 1)[1]
            self.flags[f"calls:{tid}"] = self.flags.get(f"calls:{tid}", 0) + 1
            tr = self._train(tid)
            frm = f"train:{tr.label}" if tr else frm
        self._say(frm, "control", ev["text"], kind=ev.get("kind", "info"))
        self.request_brief()

    # ------------------------------------------------------------------ LZB failure (Urda)
    def _stuck(self) -> Train | None:
        return next((t for t in self.trains if t.stuck and t.status != "left"), None)

    def _gap_m(self) -> float | None:
        """Metres from the front of the pilot's train to the rear of the stopped train ahead, same track."""
        st, me = self._stuck(), self.me
        if st is None or st.track != me.track:
            return None
        return me.ahead_m(st.rear_pk)

    @staticmethod
    def _dist(m: float) -> str:
        return f"{m / 1000:.1f} km" if m >= 1000 else f"{round(m / 10) * 10:.0f} m"

    def _cab_signal_tick(self) -> None:
        """LZB is down: note when the pilot's train first brakes, when each train first stands, and keep the on-sight run."""
        if not self.lzb_down or self.outcome:
            return
        me = self.me
        if me.eb or me.a < -0.4 or me.v == 0.0:
            self.flags.setdefault("brake_t", round(self.t, 1))
        for t in self.trains:
            if t.v == 0.0 and t.status != "left":
                self.flags.setdefault(f"stood:{t.id}", round(self.t, 1))
        run = self.on_sight_run
        if run is None:
            if self.flags.get(f"stood:{me.id}") is not None:
                self.on_sight_run = {"start_pk": me.pk, "clean_pk": me.pk, "max_kmh": 0.0, "top_kmh": 0.0}
            return
        run["top_kmh"] = max(run["top_kmh"], me.kmh)
        if me.kmh > ON_SIGHT_KMH + 5:  # too fast for on sight: the 400 m start again from here
            run["clean_pk"], run["max_kmh"] = me.pk, 0.0
        else:
            run["max_kmh"] = max(run["max_kmh"], me.kmh)

    @staticmethod
    def _read_order(low: str) -> tuple[str, int] | None:
        """The tower's words, read by rule for the common ways of giving the three orders. None: the rule cannot tell."""
        m = re.search(SPEED_RE, low)
        kmh = int(m.group(1) or m.group(2)) if m else 0
        if re.search(r"on sight|a la vista|\bforty\b|cuarenta", low) or kmh == ON_SIGHT_KMH or (0 < kmh < ON_SIGHT_KMH and re.search(GO_RE, low)):
            return "on_sight", ON_SIGHT_KMH
        if re.search(NORMAL_RE, low) or (kmh > ON_SIGHT_KMH and re.search(GO_RE, low)):
            return "faster", kmh if kmh > ON_SIGHT_KMH else 0
        go = re.search(GO_RE, re.sub(r"\b(do not|don.t|not|no)\s+\w+", " ", low))
        if re.search(STOP_RE, low) and not go:  # "move ahead, be ready to stop" is not a stop order: leave it to Copi's model
            return "stop", 0
        return None

    def _order(self, order: str, kmh: int = 0, by: str = "voice") -> dict:
        """What the tower told the trains, as far as Copi could hear it: stop, on sight, or faster than on sight."""
        if order not in ("stop", "on_sight", "faster") or not self.lzb_down or self.state != "running":
            return {"ok": False, "error": "no such order now"}
        self.flags.setdefault("orders", []).append({"order": order, "kmh": kmh, "clock": self.clock, "by": by})
        stood = self.flags.get(f"stood:{self.me.id}") is not None
        if order == "stop":
            self.flags.setdefault("stop_order_t", round(self.t, 1))
            self.release = "hold"
        elif order == "on_sight":
            if not stood and self.release != "on_sight":
                self._violation(f"{self.me.label} cleared to continue before the trains had stopped", "control")
            self.release = "on_sight"
        elif self.release != "normal" or kmh != self.cleared_kmh:
            self.release, self.cleared_kmh = "normal", kmh
            what = f"{kmh} km/h" if kmh else "normal running"
            self._violation(f"{self.me.label} cleared for {what} with LZB down; the rule is on sight, {ON_SIGHT_KMH} km/h at most"
                            if stood else f"{self.me.label} cleared for {what} before the trains had stopped", "control")
        self.release_t = round(self.t, 1)
        self._check_steps()
        self._dirty = True
        return {"ok": True}

    def _order_from_claude(self, text: str) -> None:
        """The rule did not recognise the words: Copi's model says whether they were an order at all."""
        if self.copilot.mode != "live":
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        gen = self.generation

        async def run() -> None:
            res = await self.copilot.order(text)
            if gen != self.generation or not res or res["order"] == "none":
                return
            self._order(res["order"], max(0, int(res.get("kmh") or 0)), by=COPI_MODEL)
            self.hub.bump()

        task = loop.create_task(run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _voice_orders(self, text: str) -> None:
        """What the tower said on the radio. LZB drill: the three orders, to every train. Other cases: a call to an
        AI train by name gets its answer."""
        low = text.lower()
        if self.simple:
            if self.lzb_down:
                got = self._read_order(low)
                said_stop = re.search(STOP_RE, re.sub(r"\b(do not|don.t|not|no)\s+\w+", " ", low))
                if said_stop and self.flags.get(f"stood:{self.me.id}") is None:
                    got = ("stop", 0)  # nothing has stopped yet: "stop, then we continue at 40" is the stop order
                if got:
                    self._order(*got)
                elif len(low.split()) >= 3:
                    self._order_from_claude(text)
            return
        named = []
        for tr in self.trains:
            pats = [rf"\b(train|tren)\s+{re.escape(tr.id.lower())}\b"]
            if tr.id == "A":
                pats.append(r"\balpha\b|\balfa\b")
            if tr.id == "B":
                pats.append(r"\bbravo\b|\b(train|tren)\s+(be|bee)\b")
            if tr.name:
                pats.append(re.escape(tr.name.split()[-1]))
            hits = [m.start() for pat in pats for m in [re.search(pat, low)] if m]
            if hits:
                named.append((min(hits), tr))
        to = min(named, key=lambda x: x[0])[1] if named else self.me
        if to.controller == "ai":
            self._answer_train(to)

    def _wrong_now(self) -> list[tuple[str, str, str]]:
        """LZB drill: everything that is going wrong right now, worst first, as (key, level, text). Empty: Copi has
        nothing to write. Speeds and distances come from the trains' own units (self.onboard); without them Copi
        goes by the radio alone."""
        if not self.lzb_down:
            return []
        out: list[tuple[str, str, str]] = []
        me, st, gap = self.me, self._stuck(), self._gap_m()
        stood = self.flags.get(f"stood:{me.id}") is not None
        braking = me.eb or me.a < -0.4
        if self.onboard and st is not None and gap is not None and gap > 0 and me.v > 1.0 and not braking:
            gap += st.v * st.v / (2 * st.spec["brake"])  # where the train ahead will be standing
            v1 = me.v + max(me.a, 0.0) * 6.0  # its speed by the time the tower has read this and said stop
            need = v1 * v1 / (2 * me.spec["brake"]) + 6.0 * (me.v + v1) / 2 + 80.0  # room to stop after that
            if gap < need * (1.15 if "closing" in self.raised else 1.0):
                out.append(("closing", "urgent",
                            f"{st.label} is {'stopped' if st.v == 0.0 else 'stopping'} {self._dist(gap)} ahead of {me.label}."))
        cleared = self.release == "normal" or (self.release == "on_sight" and not stood)
        if cleared:  # judged against the step the protocol is on: before the stop, the first step is to stop
            what = ("to continue" if self.release == "on_sight" else
                    f"for {self.cleared_kmh} km/h" if self.cleared_kmh else "for normal running")
            rule = f"LZB is down: on sight, {ON_SIGHT_KMH} at most." if stood else "First step: stop all trains."
            out.append(("normal", "urgent", f"{me.label} cleared {what}. {rule}"))
        if not stood and not cleared and self.t - self.lzb_t >= LZB_MOVING_S:
            if self.onboard and me.v > 1.0 and not braking:
                out.append(("moving", "urgent", f"{me.label} is still moving: {me.kmh:.0f} km/h."))
            elif not self.onboard and self.flags.get("stop_order_t") is None:
                out.append(("moving", "urgent", "No stop order yet."))
        # (a train cleared for more than 40 is flagged as that, above: its speed is then no news)
        if self.onboard and stood and self.release != "normal" and me.kmh > ON_SIGHT_KMH + (2 if "overspeed" in self.raised else 5):
            out.append(("overspeed", "urgent", f"{me.label} at {me.kmh:.0f} km/h. On sight is {ON_SIGHT_KMH}."))
        return out

    def _watch_tick(self) -> None:
        """LZB drill: Copi writes to the tower only when something is going wrong, once, and leaves everything else
        alone. A flag stays on the tower's screen while it is true. R closes it: Copi does not bring it up again."""
        active = self._wrong_now()
        keys = [k for k, _, _ in active]
        for k in [k for k in self.watch_since if k not in keys]:  # no longer true
            del self.watch_since[k]
            self.muted.discard(k)
            self.rearm[k] = self.t + FLAG_REARM_S.get(k, 15.0)
            entry = self.raised.pop(k, None)
            if entry is not None:
                entry["cleared"] = self.clock
                self._dirty = True
        for k in keys:
            self.watch_since.setdefault(k, self.t)
        adv = self.advisory
        if adv is not None and adv["key"] not in keys:
            adv = self.advisory = None
            self._dirty = True
        ready = [(k, lv, tx) for k, lv, tx in active if k not in self.muted and self.t >= self.rearm.get(k, 0.0)
                 and self.t - self.watch_since[k] >= FLAG_HOLD_S.get(k, 0.0)]
        if not ready:
            if adv is not None:  # heard with R and still true: the card stays, greyed, with current numbers
                adv["text"] = next(tx for k, _, tx in active if k == adv["key"])
            return
        for key, level, text in ready:  # each thing going wrong is written once
            if key in self.raised:
                continue
            msg = self._say("copi", "control", text, kind="copi", level=level, urgent=level == "urgent", speak=False, flag=key)
            self.raised[key] = {"id": msg["id"], "key": key, "level": level, "text": text, "clock": self.clock,
                                "t": round(self.t, 1), "heard": None, "cleared": None}
            self.flag_log.append(self.raised[key])
            self.flags["copi_flags"] = self.flags.get("copi_flags", 0) + 1
        key, level, text = ready[0]  # the card on the tower's screen: the worst one not yet heard
        entry = self.raised[key]
        if adv is None or adv["key"] != key:
            self.advisory = {"id": entry["id"], "key": key, "step": None, "level": level, "stage": "tower", "nag": True,
                             "text": text, "t": entry["t"], "clock": entry["clock"], "deadline": None, "acked_t": None,
                             "pilot_t": None, "pilot_text": None, "escalations": 0, "renag_t": None}
            self._dirty = True
        else:
            adv["text"] = text

    def _lzb_metrics(self) -> list[dict]:
        me, st, run, t0 = self.me, self._stuck(), self.on_sight_run, self.lzb_t
        if t0 is None:
            return []
        brake, stood = self.flags.get("brake_t"), self.flags.get(f"stood:{me.id}")
        out = [
            {"label": f"From the failure to {me.label} braking", "value": f"{brake - t0:.0f} s" if brake is not None else "never braked"},
            {"label": f"{me.label} at a stand", "value": f"{stood - t0:.0f} s after the failure" if stood is not None else "never"},
        ]
        if run is not None:
            out.append({"label": "Top speed after the stop", "value": f"{run['top_kmh']:.0f} km/h (on sight is {ON_SIGHT_KMH})"})
        gap = self._gap_m()
        if st is not None and gap is not None and me.status != "collided":
            out.append({"label": f"{st.label}, lost from the panel", "value": f"stopped {self._dist(max(gap, 0.0))} ahead of {me.label}"})
        n = self.flags.get("copi_flags", 0)
        out.append({"label": "Copi flagged something", "value": "never" if not n else f"{n} time{'s' if n > 1 else ''}"})
        return out

    # ------------------------------------------------------------------ control inputs
    def control_step(self, sid: str, op: str) -> dict:
        st = self._step(sid)
        if st is None or self.state != "running":
            return {"ok": False, "error": "no such step"}
        if op == "send" and st.get("say"):
            if st.get("action") and st["action"]["kind"] == "authority":
                self.control_action("authority", signal=st["action"]["signal"])
            self.say_to_driver(st["say"], step=sid, expect=st.get("expect"))
            if st["status"] != "done":
                st["status"], st["sent_t"], st["sent_by"] = "sent", round(self.t, 1), "tower"
        elif op == "act" and st.get("action"):
            a = dict(st["action"])
            a.pop("label", None)
            res = self.control_action(a.pop("kind"), **a)
            if not res.get("ok"):
                return res
        elif op == "done" and (st["who"] == "driver" or not st.get("check")):
            self._done(st, "Ticked by hand.")
        else:
            return {"ok": False, "error": "not allowed"}
        self._check_steps()
        self._dirty = True
        return {"ok": True}

    def say_to_driver(self, text: str, step: str | None = None, expect: str | None = None, kind: str = "instruction",
                      frm: str = "control") -> None:
        text = text.strip()[:400]
        if not text:
            return
        msg = self._say(frm, "driver", text, kind=kind, step=step, speak=(frm == "copi"))
        self.instruction = {"id": msg["id"], "text": text, "step": step, "expect": expect, "acked": False,
                            "t": round(self.t, 1), "clock": self.clock, "kind": kind, "from": frm}

    def control_action(self, kind: str, **p) -> dict:
        if self.state != "running":
            return {"ok": False, "error": "drill not running"}
        if kind == "emergency_call":
            track = str(p.get("track", "all"))
            self.ecalls.add(track)
            self._mark("protect_t")
            hit = [t for t in self.trains if track == "all" or str(t.track) == track]
            for t in hit:
                if t.controller == "ai" and t.ecall_t is None and t.status == "running":
                    t.ecall_t = self.t
            scope = "all trains" if track == "all" else f"all trains on track {track}"
            self._say("control", "all", f"RAILWAY EMERGENCY CALL to {scope}: stop immediately.", kind="emergency")
            if any(t.controller == "human" for t in hit):
                self.say_to_driver("RAILWAY EMERGENCY CALL. Stop your train now.", kind="emergency")
        elif kind in ("hold_signal", "release_signal", "toggle_signal"):
            s = self.signals.get(str(p.get("signal")))
            if s is None:
                return {"ok": False, "error": "no such signal"}
            s.held = {"hold_signal": True, "release_signal": False, "toggle_signal": not s.held}[kind]
            if s.held:
                self._mark("protect_t")
            self._say("control", "all", f"{s.id} {'held at STOP' if s.held else 'released'}.", kind="action")
        elif kind == "block_zone":
            for sid in p.get("signals", []):
                if sid in self.signals:
                    self.signals[sid].held = True
            self._mark("protect_t")
            self._say("control", "all", "Both tracks blocked: " + ", ".join(i for i in p.get("signals", []) if i in self.signals) + " held at STOP.", kind="action")
        elif kind == "tsr":
            try:
                a, b = sorted((float(p["from"]), float(p["to"])))
                z = {"id": f"TSR-{len(self.tsrs) + 1}", "track": int(p["track"]), "from": a, "to": b, "kmh": int(p.get("kmh", 30))}
            except (KeyError, ValueError, TypeError):
                return {"ok": False, "error": "bad restriction"}
            self.tsrs.append(z)
            self._mark("protect_t")
            self._say("control", "all", f"Temporary speed restriction: track {z['track']}, PK {a:.1f}–{b:.1f}, {z['kmh']} km/h.", kind="action")
        elif kind == "clear_tsr":
            self.tsrs = [z for z in self.tsrs if z["id"] != p.get("id")]
        elif kind == "dispatch":
            what = str(p.get("what", ""))[:60]
            if not what:
                return {"ok": False, "error": "what?"}
            self.dispatched.setdefault(what, round(self.t, 1))
            where = f" to PK {self.ctx['site']}" if self.ctx else ""
            self._say("control", "all", f"{what.capitalize()} requested{where}.", kind="action")
        elif kind == "radio_train":
            tr = self._train(str(p.get("train")))
            if tr is None or tr.controller != "ai":
                return {"ok": False, "error": "no such train"}
            ask = p.get("ask", "status")
            if ask == "examine":
                site = float(p.get("pk") or self.ctx.get("site_pk") or tr.pk)
                tr.warned = {"pk": site, "kmh": 30}
                self._mark("protect_t")
                self._say("control", f"train:{tr.label}", f"{tr.label}, rough ride reported at PK {site:.1f}. Pass at 30 km/h at most, examine the line and report.", kind="instruction")
                self._later(3.0, lambda: self._say(f"train:{tr.label}", "control", f"{tr.label}: understood, 30 km/h over PK {site:.1f}, I will report.", kind="reply"))
            elif ask == "resume":
                self._say("control", f"train:{tr.label}", f"{tr.label}, you may proceed. Obey signals.", kind="instruction")
                if tr.stuck:
                    self._later(4.0, lambda tr=tr: self._train_says(tr, f"{tr.label}: understood, but I cannot move. LZB will not reset."))
                else:
                    tr.ecall_t, tr.hold, tr.spad, tr.told_stopped = None, False, False, False
            else:
                self._say("control", f"train:{tr.label}", f"{tr.label}, control. Report your position and condition.", kind="instruction")
                self._answer_train(tr)
        elif kind == "authority":
            s = self.signals.get(str(p.get("signal")))
            if s is None:
                return {"ok": False, "error": "no such signal"}
            if s.occupied_by and s.id not in self.authority:
                self._violation(f"authority to pass {s.id} given while the section was occupied by {s.occupied_by}", "control")
            self.authority.add(s.id)
            self._say("control", "all", f"Authority recorded: {self.me.label} may pass {s.id} at danger, on sight.", kind="action")
        elif kind == "release":  # the same three orders the tower gives by voice, for a tower without a microphone
            return self._order({"hold": "stop", "on_sight": "on_sight", "normal": "faster"}.get(str(p.get("mode", "")), ""), by="tower")
        elif kind == "speed":
            self.speed = max(0.5, min(4.0, float(p.get("x", 1.0))))
        elif kind == "protocol":
            pid = str(p.get("id"))
            if pid not in PROTOCOLS:
                return {"ok": False, "error": "no such protocol"}
            self.activate(pid, "controller's choice", self.reports[-1] if self.reports else None)
        elif kind == "end":
            done = sum(s["status"] == "done" for s in self.protocol["steps"]) if self.protocol else 0
            total = len(self.protocol["steps"]) if self.protocol else 0
            self._end("stopped", "Drill stopped by control", f"{done} of {total} protocol steps done.")
        else:
            return {"ok": False, "error": "unknown action"}
        self._check_steps()
        self.request_brief()
        self._dirty = True
        return {"ok": True}

    # ------------------------------------------------------------------ ending
    def _end(self, result: str, title: str, detail: str) -> None:
        if self.outcome is not None:
            return
        m = self.marks
        metrics = []
        if "abnormal_t" in m and "report_t" in m:
            metrics.append({"label": "Driver: from first sign to report", "value": f"{max(0.0, m['report_t'] - m['abnormal_t']):.0f} s"})
        elif "abnormal_t" in m:
            metrics.append({"label": "Driver: from first sign to report", "value": "never reported"})
        if "report_t" in m and "protect_t" in m:
            metrics.append({"label": "Tower: from report to first protection", "value": f"{max(0.0, m['protect_t'] - m['report_t']):.0f} s"})
        elif "report_t" in m:
            metrics.append({"label": "Tower: from report to first protection", "value": "no protection given"})
        for t in self._threats():
            if t.v == 0.0 and t.status == "running" and self.ctx:
                metrics.append({"label": f"{t.label} stopped short of the site by", "value": f"{abs(t.ahead_m(self.ctx['site_pk'])):.0f} m"})
        if "examined_kmh" in self.flags:
            metrics.append({"label": "Next train crossed the broken rail at", "value": f"{self.flags['examined_kmh']} km/h"})
        if "on_sight_max" in self.flags:
            metrics.append({"label": "Top speed on sight", "value": f"{self.flags['on_sight_max']} km/h"})
        if self.protocol and self.copi_to_pilot:
            n = self.flags.get("escalations", 0)
            metrics.append({"label": "Copi had to go to the pilot", "value": "never" if not n else f"{n} time{'s' if n > 1 else ''}"})
        elif self.protocol:
            n = self.flags.get("reminders", 0)
            metrics.append({"label": "Copi had to remind the tower", "value": "never" if not n else f"{n} time{'s' if n > 1 else ''}"})
        if self.flags.get("rec_by_pilot"):
            metrics.append({"label": "Emergency call made by", "value": "the pilot, from the cab"})
        if self.protocol:
            steps = self.protocol["steps"]
            metrics.append({"label": "Protocol steps", "value": f"{sum(s['status'] == 'done' for s in steps)} of {len(steps)}"})
            metrics.append({"label": "Brief written by", "value": (self.brief_meta or {}).get("model") or "rules only"})
        if self.simple:
            metrics = self._lzb_metrics()
            run = self.on_sight_run
            if run is not None and run["top_kmh"] > ON_SIGHT_KMH + 5:
                self.violations.append({"t": round(self.t, 1), "clock": self.clock, "who": "driver",
                                        "text": f"ran at {run['top_kmh']:.0f} km/h after the stop; on sight is {ON_SIGHT_KMH} km/h at most"})
        metrics.append({"label": "Drill time", "value": f"{self.t:.0f} s"})
        self.outcome = {
            "result": result, "title": title, "detail": detail, "metrics": metrics,
            "violations": list(self.violations), "case": self.case["title"], "teaches": self.case["teaches"],
            "protocol": self.protocol and f"{self.protocol['id']} · {self.protocol['title']}",
            "reality": self.case.get("reality", []), "reconstruction": self.case.get("reconstruction"),
        }
        self.state = "ended"
        self._say("system", "all", f"Drill over: {title}.", kind="info")
        self.hub.bump()

    # ------------------------------------------------------------------ rule-layer alerts
    def alerts(self) -> list[dict]:
        out: list[dict] = []
        if not self.protocol:
            return out
        site = self.ctx["site_pk"]
        for t in self._threats():
            d = t.ahead_m(site)
            if t.status != "running":
                continue
            stop_d = t.v * t.v / (2 * t.spec["ebrake"])
            if t.v == 0.0:
                out.append({"level": "ok", "text": f"{t.label} is at a stand {abs(d):.0f} m short of PK {site:.1f}."})
            elif t.ecall_t is not None or t.spad:
                react = max(0.0, t.ecall_t + ECALL_REACTION_S - self.t) * t.v if t.ecall_t is not None else 0.0
                margin = d - stop_d - react
                if margin > 0:
                    out.append({"level": "ok", "text": f"{t.label} is braking and will stop about {margin:.0f} m short of PK {site:.1f}."})
                else:
                    out.append({"level": "critical", "text": f"{t.label} is braking but cannot stop before PK {site:.1f}."})
            elif d > 0:
                eta = d / t.v
                held = any((s.held or s.failed) and 0 < t.ahead_m(s.pk) < d for s in self._sigs(t.track))
                slow = self._v_allowed(t) < t.v - 1 or any(
                    z["track"] == t.track and z["from"] <= site <= z["to"] for z in self.tsrs) or t.warned
                if held:
                    out.append({"level": "ok", "text": f"{t.label} has a signal at STOP before PK {site:.1f}."})
                elif slow:
                    out.append({"level": "ok", "text": f"{t.label} is restricted over PK {site:.1f}; {d / 1000:.1f} km to go."})
                else:
                    last = (d - stop_d - ECALL_REACTION_S * t.v) / t.v
                    txt = f"{t.label} reaches PK {site:.1f} in {eta:.0f} s ({d / 1000:.1f} km, {t.kmh:.0f} km/h)."
                    if self.protocol["tier"] in ("seconds", "major"):
                        txt += f" A stop call still works for {last:.0f} s." if last > 0 else " Too late for a stop call to hold it short."
                    out.append({"level": "critical" if eta < 120 else "high", "text": txt})
        if self.protocol["id"] == "P-05":
            return out
        near = [m for m in self.case.get("memory", []) if abs(m["pk"] - site) <= 0.8]
        if near:
            out.append({"level": "high" if len(near) >= 2 else "medium",
                        "text": f"{len(near)} earlier record(s) within 800 m of this report. With the pilot's report that makes "
                        f"{len(near) + 1} independent sources at one place."})
        sig = self.signals.get(self.ctx.get("sig", ""))
        if sig is not None and self.ctx.get("sig") not in self.authority:
            if sig.occupied_by:
                out.append({"level": "critical", "text": f"Section beyond {sig.id} is OCCUPIED by {sig.occupied_by}. Do not authorise yet."})
            else:
                out.append({"level": "ok", "text": f"Section beyond {sig.id} is clear."})
        if self.protocol["id"] == "P-04" and not self.flags.get("derail_confirmed"):
            said = " ".join(m["text"] for m in self.radio if m["from"] == "driver")
            if re.search(r"catenar|enganch|snag|pantogra|overhead", said, re.I):
                out.append({"level": "high", "text": "The driver suspects the catenary. An automatic emergency brake with the rear "
                            "coaches' systems lost is not explained by a snag. Ask the closed question."})
        return out

    # ------------------------------------------------------------------ Claude layer
    def llm_view(self) -> dict:
        """What Claude sees: the control room's knowledge only. Never the hazards."""
        p = self.protocol
        return {
            "clock": self.clock,
            "protocol": p and {
                "id": p["id"], "title": p["title"],
                "steps": [
                    {k: s.get(k) for k in ("id", "who", "title", "detail", "say", "status", "note")} for s in p["steps"]
                ],
            },
            "reported_site": p and {"pk": self.ctx["site_pk"], "track_at_risk": self.ctx["haz_track"]},
            "pilot_train": {
                "id": self.me.label, "service": self.me.name, "runs_on_track": self.me.track, "the_other_track_is": 3 - self.me.track,
                "heading": "towards higher PK" if self.me.dir == 1 else "towards lower PK",
                "speed_limit_kmh_here": round(self._limit_now(self.me) * KMH),
            },
            "line": "Track 1 runs towards lower PK, track 2 towards higher PK. A train is ahead of another on the same track if it is further along that direction.",
            "radio": [{k: m[k] for k in ("clock", "from", "to", "text")} for m in self.radio[-14:]],
            "train_describer": [
                {"id": t.label, "service": t.name, "track": t.track, "pk": round(t.pk, 2), "kmh": round(t.kmh),
                 "state": self._panel_status(t) if self._panel_status(t) != "running" else ("stopped" if t.v == 0 else "running"),
                 "position": "this is the pilot's train" if t is self.me else self._rel(
                     t.pk, t.track, None if t.track == self.me.track or t.v == 0 else t.ahead_m(self.me.pk) > 0)}
                for t in self.trains if t.status != "left"
            ],
            "signals_not_clear": [
                {"id": s.id, "track": s.track, "pk": s.pk, "aspect": s.aspect, "held_by_control": s.held,
                 "section_occupied_by": s.occupied_by, "position": self._rel(s.pk, s.track)}
                for s in self.signals.values() if s.aspect != "clear"
            ],
            "speed_restrictions": self.tsrs,
            "requested": sorted(self.dispatched),
            "earlier_records_for_this_location": self.case.get("memory", []) if p else [],
            "rule_engine_alerts": [a["text"] for a in self.alerts()],
            "cab_signalling": self._lzb_view() if self.case.get("lzb") else "working",
            "protocol_breaches": [v["text"] for v in self.violations],
        }

    def _brief_key(self) -> str:
        done = ",".join(s["id"] for s in self.protocol["steps"] if s["status"] == "done")
        return f"{self.case['id']}|{self.protocol['id']}|{done}"

    def request_brief(self) -> None:
        if self.protocol is None or self.outcome is not None or self.simple:
            return
        if self.copilot.mode == "offline":
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self.llm_busy:
            self.llm_dirty = True
            return
        self.llm_busy = True
        loop.create_task(self._brief_task(self.generation))

    async def _brief_task(self, gen: int) -> None:
        try:
            while gen == self.generation and self.protocol is not None and self.outcome is None:
                self.llm_dirty = False
                asked_t = self.t
                valid = {s["id"] for s in self.protocol["steps"]}
                data, meta = await self.copilot.brief(self.protocol["model"], self.llm_view(), self._brief_key())
                if gen != self.generation:
                    return
                meta["asked_clock"] = (self.clock_base + timedelta(seconds=asked_t)).strftime("%H:%M:%S")
                if data is not None:
                    if data.get("next_step") not in valid:
                        data["next_step"] = ""
                    self.brief = data
                    self._apply_brief(data, asked_t)
                self.brief_meta = meta
                self.hub.bump()
                if not self.llm_dirty:
                    break
        finally:
            if gen == self.generation:
                self.llm_busy = False
                self.hub.bump()

    def _apply_brief(self, data: dict, asked_t: float) -> None:
        """Act on what Copi heard: instructions the tower spoke, answers the pilot gave, and new cautions."""
        for sid in data.get("said_steps", []):
            st = self._step(sid)
            if st and st["who"] == "driver" and st["status"] == "pending" and st.get("copi_relay", True):
                st["status"], st["sent_t"], st["sent_by"] = "sent", round(asked_t, 1), "voice"
        for sid in data.get("answered_steps", []):
            st = self._step(sid)
            if not st or st["status"] == "done" or st["who"] != "driver":
                continue
            chk = st.get("check")
            if chk == "driver_replied" or (chk == "driver_stopped" and self.me.v == 0.0):
                self._done(st, "Answer heard by Copi.")
            elif chk == "derail_confirmed" and self.inspect["done"] and self.me.status == "derailed":
                self.flags["derail_confirmed"] = True
        for c in data.get("cautions", [])[:1]:
            key = re.sub(r"\W+", " ", c.lower()).strip()[:60]
            if key and not any(_similar(key, k) for k in self.spoken_cautions):
                self.spoken_cautions.add(key)
                self._copi_say("control", "Caution. " + c, level="info")

    # ------------------------------------------------------------------ Copi: who is told, and when
    def _copi_say(self, to: str, text: str, level: str | None = None, **extra) -> dict:
        """level: for the lines Copi volunteers to the tower. An answer to a question has none and is always spoken."""
        if level in LEVELS:
            text = _address(text, level)
            extra.update(level=level, urgent=level == "urgent")
        return self._say("copi", to, text, kind="copi", speak=self.copi_speaks and level != "info", **extra)

    def _level(self, st: dict) -> str:
        """How urgent a step is: what the protocol says, else by what is at stake. A step Copi only waits for is info."""
        if st.get("level") in LEVELS:
            return st["level"]
        if not (st.get("action") or st.get("say")):
            return "info"
        return "urgent" if self.protocol["tier"] in ("seconds", "major") else "important"

    def _eligible(self, st: dict) -> bool:
        return all((self._step(a) or {}).get("status") == "done" for a in st.get("after", []))

    def _next_step(self) -> dict | None:
        """The step Copi talks about: the first open one somebody can act on, else the first one being waited for."""
        if not self.protocol:
            return None
        todo = [s for s in self.protocol["steps"] if s["status"] != "done" and self._eligible(s)]
        return next((s for s in todo if s.get("action") or s.get("say")), todo[0] if todo else None)

    def _advise(self, st: dict, text: str | None = None, floor: str | None = None) -> None:
        """Tell the tower about a step. floor="important": say it aloud even if the step is one Copi only waits for
        (the line that opens a protocol)."""
        level = self._level(st)
        nag = level != "info"  # Copi waits for R, and repeats, only on a step somebody has to act on
        if not nag and floor:
            level = floor
        text = text or (f"{st['title']}." if nag else f"Waiting. {st['title']}.")
        msg = self._copi_say("control", text, level=level)
        self.advisory = {
            "id": msg["id"], "step": st["id"], "level": level, "stage": "tower" if nag else "quiet", "nag": nag,
            "text": _address(text, "info"),  # the tower's card shows the level, so the opening word is left off
            "t": round(self.t, 1), "deadline": self.t + ACK_S.get(level, 0.0) + len(msg["text"]) / SPEECH_CPS,
            "acked_t": None, "pilot_t": None, "pilot_text": None, "escalations": 0, "renag_t": None,
        }

    def _progress(self, st: dict) -> bool:
        """Has something changed since the tower was told? For the pilot's steps that means the train or the radio."""
        if st["who"] != "driver" or st["sent_t"] is None:
            return False
        me, chk = self.me, st.get("check")
        if chk == "driver_below":
            return me.a < -0.05 or me.kmh <= st["kmh"] + 3
        if chk == "driver_stopped" and me.v > 0:
            return me.a < -0.05
        window = {"clip_placed": 45.0, "derail_confirmed": 50.0}.get(chk, 30.0)
        return self.t - st["sent_t"] < window

    def _copi_tick(self) -> None:
        if self.outcome:
            return
        if self.simple:
            self._watch_tick()
            return
        if not self.protocol:
            return
        st, adv = self._next_step(), self.advisory
        if st is None:
            self.advisory = None
            return
        if adv is None or adv["step"] != st["id"]:
            self._advise(st)
            return
        if adv["stage"] == "tower":  # said, not acknowledged yet
            if self.t < adv["deadline"]:
                return
            if self._progress(st):
                adv["deadline"] = self.t + 5.0
                return
            if self.copi_to_pilot:
                self._escalate(adv, st)
            else:
                self._remind(adv, st)
        elif adv["stage"] in ("pilot", "pilot_acked") and adv["renag_t"] is not None and self.t >= adv["renag_t"]:
            adv["renag_t"] = None
            if not self._progress(st):
                self._copi_say("control", f"Still open: {st['title']}.", level="info")
        # any other stage (info line, acknowledged with R, dropped after the repeats): Copi is done with this step

    def _remind(self, adv: dict, st: dict) -> None:
        """Nobody pressed R and nothing changed. Only the tower talks to the pilot, so Copi says the step to the
        tower again, in a few words. An urgent line comes back twice at most, an important one once. Then Copi drops it:
        the line stays on the tower's screen and Copi stays quiet."""
        gaps = REPEAT_S.get(adv["level"], ())
        n = adv["escalations"] + 1
        if n > len(gaps):
            adv.update(stage="silent", nag=False)
            self._dirty = True
            return
        text = f"{st['title']}."  # the step again and nothing else: no "you did not answer"
        msg = self._copi_say("control", text, level=adv["level"], repeat=n)
        adv.update(escalations=n, t=round(self.t, 1), deadline=self.t + gaps[n - 1] + len(msg["text"]) / SPEECH_CPS)
        self.flags["reminders"] = self.flags.get("reminders", 0) + 1

    def _escalate(self, adv: dict, st: dict) -> None:
        """Pilot fallback (COPI_TO_PILOT=1 only): nobody pressed R and nothing changed, so Copi tells the pilot."""
        relay = st["who"] == "driver" and st.get("copi_relay", True)
        text = st.get("pilot") or (st["say"] if relay else f"Pilot, tell the tower: {st['title'][0].lower()}{st['title'][1:]}.")
        self.say_to_driver(text, step=st["id"] if relay else None, expect=st.get("expect") if relay else None, kind="copi", frm="copi")
        if relay and st["status"] != "done":
            st["status"], st["sent_t"], st["sent_by"] = "sent", round(self.t, 1), "copi"
        adv.update(stage="pilot", pilot_t=round(self.t, 1), pilot_text=text, escalations=adv["escalations"] + 1,
                   renag_t=self.t + 25.0)
        self.flags["escalations"] = self.flags.get("escalations", 0) + 1
        self._copi_say("control", "No answer. Pilot told.", level=adv["level"])

    def copi_ack(self, role: str) -> dict:
        """The R key: 'we heard Copi'. For the tower that is final: Copi does not come back to this step,
        whatever the tower does next. The next step, when its turn comes, is a new line."""
        adv = self.advisory
        if self.state != "running":
            return {"ok": False}
        if role == "control":
            if adv and adv["stage"] in ("tower", "silent"):
                adv.update(stage="acked", nag=False, acked_t=round(self.t, 1))
                if adv.get("key"):  # a flag: heard once is heard for as long as it stays true
                    self.muted.add(adv["key"])
                    if adv["key"] in self.raised:
                        self.raised[adv["key"]]["heard"] = self.clock
                self._say("control", "copi", "Heard.", kind="ack")
                return {"ok": True}
            return {"ok": False}
        if self.instruction and not self.instruction.get("acked"):
            self.instruction["acked"] = True
            self._say("driver", self.instruction.get("from", "control"), "Heard.", kind="ack", step=self.instruction.get("step"))
            if adv and adv["stage"] == "pilot":
                adv["stage"] = "pilot_acked"
            return {"ok": True}
        return {"ok": False}

    def heard(self, source: str, text: str) -> dict:
        """A line of speech-to-text from one of the two laptops. Copi listens to everything."""
        text = text.strip()[:300]
        if self.state != "running" or len(text) < 3:
            return {"ok": False}
        for m in self.radio[-14:]:  # Copi's own voice from the speakers, or the same words heard by both laptops
            if self.t - m["t"] < 12 and m["from"] in ("copi", "voice") and _echo(text, m["text"]):
                return {"ok": False, "dropped": "echo"}
        source = "driver" if source == "driver" else "control"
        self._say("voice", "all", text, kind="voice", heard_on=source)
        if source == "control":
            self._voice_orders(text)
        if self.simple:  # the alarm opens this drill's protocol; whatever else is said, Copi leaves it alone
            return {"ok": True}
        me = self.me
        if self.protocol is None:
            rep = {"t": round(self.t, 1), "clock": self.clock, "category": "voice", "where": None, "text": text,
                   "pk": round(me.pk, 2), "track": me.track, "tagged": False, "kmh": round(me.kmh), "source": source}
            pid = match_keywords(text) if source == "driver" else None
            if pid:
                self._open_from_words(pid, rep, "pilot's words (keywords)")
            else:
                self._listen(rep)
        else:
            if source == "driver":
                self._mark("reply_t")
            self.request_brief()
        return {"ok": True}

    def _open_from_words(self, pid: str, rep: dict, source: str, own_track: bool | None = None) -> None:
        if own_track is None:
            own_track = bool(re.search(r"my track|mi v[ií]a|ahead of me|delante", rep["text"], re.I))
        rep["where"] = "mine" if own_track else "other"
        if rep not in self.reports:
            self.reports.append(rep)
        self._mark("report_t")
        for tr in self.trains:
            if tr.depart and tr.depart_t is None and PROTOCOLS[pid]["categories"][0] == tr.depart.get("after_report"):
                tr.depart_t = self.t + tr.depart.get("delay_s", 30)
        self.activate(pid, source, rep)
        self.request_brief()

    def _listen(self, rep: dict) -> None:
        """No keyword matched: ask the fastest model whether these words are a report, and of what."""
        if self.copilot.mode != "live":
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self.triage_busy:
            self.listen_queue = rep
            return
        gen = self.generation
        self.triage_busy = True

        async def run(rep: dict) -> None:
            try:
                while rep is not None and gen == self.generation and self.protocol is None:
                    res = await self.copilot.listen(rep["text"])
                    if gen != self.generation or self.protocol is not None:
                        return
                    pid = (res or {}).get("protocol_id")
                    if pid in PROTOCOLS:
                        self._open_from_words(pid, rep, f"spoken words, read by {TRIAGE_MODEL}", res.get("on_pilots_own_track", False))
                        return
                    rep, self.listen_queue = self.listen_queue, None
            finally:
                if gen == self.generation:
                    self.triage_busy = False
                    self.hub.bump()

        loop.create_task(run(rep))

    async def voice(self, role: str, text: str) -> dict:
        """A spoken turn from a seat's voice room. The microphone can pick up Copi's voice from the other
        laptop's speakers, so a turn that repeats something Copi said in the last 12 s is dropped."""
        text = text.strip()
        if len(text) < 2:
            return {"ok": False, "dropped": "empty"}
        for m in self.radio[-14:]:
            if self.t - m["t"] < 12 and m["from"] == "copi" and _echo(text, m["text"]):
                return {"ok": False, "dropped": "echo"}
        if self.case is None:
            return {"ok": False, "answer": "", "lobby": True}
        return await self.ask(role, text)

    async def ask(self, role: str, text: str) -> dict:
        """The talk-to-Copi button, from either seat."""
        text = text.strip()[:400]
        if not text or self.case is None:
            return {"ok": False, "answer": ""}
        role = "driver" if role == "driver" else "control"
        gen = self.generation
        self._say(role, "copi", text, kind="ask")
        self.hub.bump()
        answer, meta = None, {}
        if role == "driver" and self.protocol is None and self.state == "running" and not self.simple:
            me = self.me
            rep = {"t": round(self.t, 1), "clock": self.clock, "category": "voice", "where": None, "text": text,
                   "pk": round(me.pk, 2), "track": me.track, "tagged": False, "kmh": round(me.kmh), "source": "driver"}
            pid, own = match_keywords(text), None
            if not pid and self.copilot.mode == "live":
                res = await self.copilot.listen(text)
                if res and res["protocol_id"] in PROTOCOLS:
                    pid, own = res["protocol_id"], res["on_pilots_own_track"]
            if gen != self.generation:
                return {"ok": False, "answer": ""}
            if pid and self.protocol is None:
                self._open_from_words(pid, rep, "pilot talking to Copi", own)
                answer = "Understood. I am telling the tower now."
        if answer is None:
            answer, meta = await self.copilot.answer(model_for(self.protocol), role, text, self.llm_view())
            if gen != self.generation:
                return {"ok": False, "answer": ""}
        self._copi_say(role, answer, model=meta.get("model"), latency_ms=meta.get("latency_ms"))
        if role == "driver" and self.protocol is not None:
            self._mark("reply_t")
            me = self.me
            if self.inspect["done"] and me.status == "derailed" and re.search(
                    r"derail|descarril|off the rails|fuera de (la )?v[ií]a|fouling|invad", text, re.I):
                self.flags["derail_confirmed"] = True  # the pilot said it to Copi instead of typing it to the tower
            self.request_brief()
        self.hub.bump()
        return {"ok": True, "answer": answer, **meta}

    # ------------------------------------------------------------------ views
    def _base(self, role: str) -> dict:
        return {
            "role": role, "version": self.hub.version, "state": self.state, "t": round(self.t, 2), "clock": self.clock,
            "speed": self.speed, "outcome": self.outcome,
            "online": {r: self.online[r] + (time.monotonic() - self.polled[r] < 12.0) for r in self.online},
        }

    def _lzb_view(self) -> dict | None:
        z = self.case.get("lzb") if self.case else None
        if not z:
            return None
        return {
            "down": self.lzb_down, "from_pk": z["from_pk"], "to_pk": z["to_pk"], "since": z["since"], "release": self.release,
            "at": None if self.lzb_t is None else (self.clock_base + timedelta(seconds=self.lzb_t)).strftime("%H:%M:%S"),
        }

    def view_driver(self) -> dict:
        out = self._base("driver")
        if not self.case:
            return out
        me = self.me
        ahead: list[dict] = []
        sight = self.case.get("train_sight_m", 2500)
        own_ahead = [me.ahead_m(o.rear_pk) for o in self.trains if o is not me and o.status != "left" and o.track == me.track
                     and me.ahead_m(o.rear_pk) > 0]
        blocked_at = min(own_ahead) if own_ahead else 1e9  # a train ahead hides the signals beyond it
        for s in self._sigs(me.track):
            if -40 < me.ahead_m(s.pk) < min(1800, blocked_at):
                ahead.append({"kind": "signal", "id": s.id, "pk": s.pk, "aspect": "dark" if s.failed else s.aspect})
        for h in self.hazards:
            if h["kind"] == "debris" and -150 < me.ahead_m(h["pk"]) < h.get("sight_m", 700):
                ahead.append({"kind": "debris", "pk": h["pk"], "where": "own" if h["track"] == me.track else "other"})
        for o in self.trains:
            if o is me or o.status == "left":
                continue
            near = min(me.ahead_m(o.pk), me.ahead_m(o.rear_pk))
            far = max(me.ahead_m(o.pk), me.ahead_m(o.rear_pk))
            if far > -300 and near < sight:
                ahead.append({"kind": "train", "pk": o.pk, "rear_pk": o.rear_pk, "v": o.v, "dir": o.dir,
                              "where": "own" if o.track == me.track else "other", "status": o.status})
        for z in self.zones + self.tsrs:
            if z["track"] == me.track:
                entry = z["from"] if me.dir == 1 else z["to"]
                if -20 < me.ahead_m(entry) < 1500:
                    ahead.append({"kind": "board", "pk": entry, "kmh": z["kmh"]})
        alarms = []
        if me.status == "derailed":
            alarms += [{"level": "red", "text": "EMERGENCY BRAKE · brake pipe pressure lost"},
                       {"level": "red", "text": "COACHES 6–8 · systems lost"},
                       {"level": "red", "text": "CATENARY · no line voltage"}]
        elif me.eb:
            alarms.append({"level": "red", "text": "EMERGENCY BRAKE applied"})
        if self.flags.get("spad_t") is not None and self.t - self.flags["spad_t"] < 30:
            alarms.append({"level": "red", "text": "ASFA · signal passed at danger"})
        if self.on_sight:
            alarms.append({"level": "amber", "text": f"ON SIGHT · {self.on_sight['kmh']} km/h at most, as far as {self.on_sight['until']}"})
        if self.lzb_down:
            alarms.append({"level": "red" if self.t - self.lzb_t < 10.0 else "amber", "text": "LZB FAILED · no cab signal"})
        lim = self._limit_now(me) * KMH
        if me.kmh > lim + 5 and not self.lzb_down:  # without cab signalling the cab does not know the limit
            alarms.append({"level": "amber", "text": f"OVERSPEED · limit {lim:.0f} km/h"})
        ins, cj = self.inspect, self.clip_job
        nxt = next((s for s in self._sigs(me.track) if me.ahead_m(s.pk) > 0), None)  # route knowledge: where, not what it shows
        out["next_signal"] = nxt and {"id": nxt.id, "in_m": round(me.ahead_m(nxt.pk))}
        out.update(
            case={"brief": self.case["driver_brief"], "simple": self.simple},
            lzb=self._lzb_view() and {k: self._lzb_view()[k] for k in ("down", "at")},
            me={
                "id": me.id, "name": me.name, "label": me.label, "model": me.spec["name"], "route": me.route, "track": me.track, "dir": me.dir,
                "pk": round(me.pk, 5), "v": round(me.v, 3), "a": round(me.a, 3), "kmh": round(me.kmh, 1),
                "notch": me.notch, "eb": me.eb, "cruise_kmh": None if me.cruise is None else round(me.cruise * KMH),
                "limit_kmh": round(lim), "limit_known": not self.lzb_down, "next_limit": self._next_limit(me),
                "status": me.status, "on_board": me.on_board,
                "vmax_kmh": me.spec["vmax_kmh"],
            },
            ahead=ahead,
            alarms=alarms,
            jolt=self.jolt if self.jolt and self.t - self.jolt["t"] < 4 else None,
            radio=[m for m in self.radio if m["to"] in ("driver", "all") or m["from"] == "driver"][-25:],
            instruction=self.instruction,
            categories=REPORT_CATEGORIES,
            jobs={
                "inspect": {"running": ins["start"] is not None and not ins["done"], "done": ins["done"], "text": ins["text"],
                            "reported": ins["reported"],
                            "progress": 0 if ins["start"] is None else min(1.0, (self.t - ins["start"]) / 8.0)},
                "clip": {"running": cj["start"] is not None and not cj["done"], "done": cj["done"],
                         "progress": 0 if cj["start"] is None else min(1.0, (self.t - cj["start"]) / 10.0)},
            },
        )
        return out

    def view_control(self) -> dict:
        out = self._base("control")
        out["cases"] = [
            {"id": c["id"], "n": c["n"], "title": c["title"], "summary": c["summary"], "protocol": c["protocol"],
             "protocol_title": PROTOCOLS[c["protocol"]]["title"], "model": PROTOCOLS[c["protocol"]]["model"],
             "train": TRAIN_MODELS[next(t for t in c["trains"] if t["controller"] == "human")["model"]]["name"],
             "real": bool(c.get("reconstruction"))}
            for c in CASES.values()
        ]
        out["routing"] = routing()
        out["triage_model"] = TRIAGE_MODEL
        out["copilot"] = {"mode": self.copilot.mode, "busy": self.llm_busy or self.triage_busy, "brief": self.brief,
                          "meta": self.brief_meta, "model": model_for(self.protocol)}
        out["line"] = {"pk_range": self.line["pk_range"], "places": self.line["places"], "name": self.line["name"]}
        if not self.case:
            return out
        concealed = self.hidden and self.state != "ended"
        blind = self.lzb_down and self.state == "running"  # LZB down: the panel shows only where each train was last seen
        out.update(
            case={"id": self.case["id"], "n": self.case["n"],
                  "title": "Surprise case" if concealed else self.case["title"],
                  "summary": "The tower learns what is wrong when the driver reports it." if concealed else self.case["summary"],
                  "view": self.case["view"], "hidden": concealed, "simple": self.simple, "teaches": self.case["teaches"]},
            trains=self.last_seen if blind else [self._panel_train(t) for t in self.trains if t.status != "left"],
            blind=blind,
            signals=[
                {"id": s.id, "track": s.track, "pk": s.pk, "aspect": s.aspect, "held": s.held,
                 "fault": s.failed and s.fault_known, "occupied_by": s.occupied_by}
                for s in self.signals.values()
            ],
            zones=self.zones, tsrs=self.tsrs,
            clips=[{"track": c["track"], "pk": round(c["pk"], 2)} for c in self.clips],
            site=self.protocol and {"pk": self.ctx["site_pk"], "track": self.ctx["haz_track"]},
            protocol=self.protocol,
            suggest=self.suggest,
            library=[{"id": p["id"], "title": p["title"], "model": p["model"]} for p in PROTOCOLS.values()],
            alerts=[] if self.simple else self.alerts(),
            rules_brief=None if self.simple else rules_brief(self.protocol, self.alerts()),
            advisory=self.advisory,
            copi_log=self.flag_log[-6:],
            next_step=(self._next_step() or {}).get("id"),
            memory=[] if (concealed and not self.protocol) else self.case.get("memory", []),
            radio=self.radio[-60:],
            dispatched=[{"what": k, "t": v} for k, v in self.dispatched.items()],
            authority=sorted(self.authority),
            violations=self.violations,
            instruction=self.instruction,
            lzb=self._lzb_view(),
            reconstruction=self.case.get("reconstruction"),
        )
        return out

    def view(self, role: str) -> dict:
        return self.view_driver() if role == "driver" else self.view_control()
