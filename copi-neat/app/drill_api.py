"""HTTP API and pages for the two-seat drill. One Drill per server, two roles: driver (pilot) and control (tower)."""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from .drill import Drill
from .protocols import CASES

DEFAULT_CASE = "urda"  # the drill starts here: the tower page opens on it, ready for Start

STATIC = Path(__file__).resolve().parent.parent / "static" / "drill"
TUNNEL_FILE = Path(__file__).resolve().parent.parent / ".drill_tunnel"

router = APIRouter()
_drill: Drill | None = None


def get_drill() -> Drill:
    global _drill
    if _drill is None:
        _drill = Drill()
        _drill.load(DEFAULT_CASE)
    return _drill


def _role(role: str) -> str:
    if role not in ("driver", "control"):
        raise HTTPException(400, "role must be driver or control")
    return role


def _lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent; this only picks the outgoing interface
            return s.getsockname()[0]
    except OSError:
        return None


@router.get("/drill")
async def page_lobby() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@router.get("/drill/driver")
async def page_driver() -> FileResponse:
    return FileResponse(STATIC / "driver.html")


@router.get("/drill/control")
async def page_control() -> FileResponse:
    return FileResponse(STATIC / "control.html")


# The earlier pages (five cases, protocol buttons, radio log), kept as they were.
@router.get("/drill/classic")
async def page_classic_lobby() -> FileResponse:
    return FileResponse(STATIC / "classic" / "index.html")


@router.get("/drill/classic/driver")
async def page_classic_driver() -> FileResponse:
    return FileResponse(STATIC / "classic" / "driver.html")


@router.get("/drill/classic/control")
async def page_classic_control() -> FileResponse:
    return FileResponse(STATIC / "classic" / "control.html")


@router.get("/api/drill/join")
async def join(request: Request) -> dict:
    """Links for the second laptop. The tunnel link is https, which the browser needs before it opens the microphone."""
    key = request.app.state.access_key
    port = request.url.port or 8000
    ip = _lan_ip()
    tunnel = None
    try:
        tunnel = TUNNEL_FILE.read_text().strip() or None
    except FileNotFoundError:
        pass
    return {
        "key": key,
        "lan": f"http://{ip}:{port}/drill/driver?k={key}" if ip and os.environ.get("MEMORIA_LAN") == "1" else None,
        "tunnel": f"{tunnel}/drill/driver?k={key}" if tunnel else None,
    }


@router.get("/api/drill/state")
async def state(role: str = "control") -> dict:
    return get_drill().view(_role(role))


@router.get("/api/drill/stream")
async def stream(request: Request, role: str = "control") -> StreamingResponse:
    d = get_drill()
    role = _role(role)

    async def gen():
        d.online[role] += 1
        d.hub.bump()
        seen = -1
        try:
            while True:
                if await request.is_disconnected():
                    break
                await d.hub.wait(seen, 10.0)
                if d.hub.version != seen:
                    seen = d.hub.version
                    yield f"data: {json.dumps(d.view(role), ensure_ascii=False)}\n\n"
                else:
                    yield ": keepalive\n\n"
        finally:
            d.online[role] = max(0, d.online[role] - 1)
            d.hub.bump()

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/api/drill/poll")
async def poll(role: str = "control", v: int = -1, agent: int = 0) -> dict:
    """Long poll: answers as soon as the state is newer than version v. For links that cannot carry an
    event stream (Cloudflare quick tunnels buffer them), this gives the same updates one request at a time.
    agent=1 is Copi's voice agent: it reads a seat's view but is not that seat, so it does not count as online."""
    d = get_drill()
    role = _role(role)
    if not agent:
        d.polled[role] = time.monotonic()
    await d.hub.wait(v, 8.0)
    if not agent:
        d.polled[role] = time.monotonic()
    return d.view(role)


@router.post("/api/drill/load")
async def load(p: dict = Body(default={})) -> dict:
    case = p.get("case")
    if case is not None and case not in CASES:
        raise HTTPException(400, "unknown case")
    get_drill().load(case, hidden=bool(p.get("hidden")))
    return {"ok": True}


@router.post("/api/drill/start")
async def start() -> dict:
    get_drill().start()
    return {"ok": True}


@router.post("/api/drill/driver/input")
async def driver_input(p: dict = Body(default={})) -> dict:
    get_drill().driver_input(notch=p.get("notch"), eb=p.get("eb"), cruise=p.get("cruise"))
    return {"ok": True}


@router.post("/api/drill/driver/report")
async def driver_report(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.driver_report(str(p.get("category", "")), p.get("where"), str(p.get("text") or ""))
    d.hub.bump()
    return res


@router.post("/api/drill/driver/say")
async def driver_say(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.driver_say(str(p.get("text") or ""))
    d.hub.bump()
    return res


@router.post("/api/drill/driver/act")
async def driver_act(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.driver_act(str(p.get("kind", "")))
    d.hub.bump()
    return res


@router.post("/api/drill/control/step")
async def control_step(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.control_step(str(p.get("step", "")), str(p.get("op", "")))
    d.hub.bump()
    return res


@router.post("/api/drill/control/action")
async def control_action(p: dict = Body(default={})) -> dict:
    d = get_drill()
    p = dict(p)
    res = d.control_action(str(p.pop("kind", "")), **p)
    d.hub.bump()
    return res


@router.post("/api/drill/control/say")
async def control_say(p: dict = Body(default={})) -> dict:
    d = get_drill()
    if d.state == "running":
        d.say_to_driver(str(p.get("text") or ""))
    d.hub.bump()
    return {"ok": True}


# ----- Copi: the R key, the open microphone, and the talk-to-Copi button -----------------
@router.post("/api/drill/copi/ack")
async def copi_ack(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.copi_ack(_role(str(p.get("role", ""))))
    d.hub.bump()
    return res


@router.post("/api/drill/copi/heard")
async def copi_heard(p: dict = Body(default={})) -> dict:
    d = get_drill()
    res = d.heard(_role(str(p.get("role", ""))), str(p.get("text") or ""))
    d.hub.bump()
    return res


@router.post("/api/drill/copi/ask")
async def copi_ask(p: dict = Body(default={})) -> dict:
    return await get_drill().ask(_role(str(p.get("role", ""))), str(p.get("text") or ""))


@router.post("/api/drill/copi/voice")
async def copi_voice(p: dict = Body(default={})) -> dict:
    """A finished spoken turn from a seat's voice room: talking to Copi, with Copi's own voice filtered out."""
    return await get_drill().voice(_role(str(p.get("role", ""))), str(p.get("text") or ""))
