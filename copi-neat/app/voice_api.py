"""Copi's voice: a LiveKit room per seat, joined by the browser and by the Copi voice agent (voice/agent.py).

The browser asks for a token here. The token names a fresh room and dispatches the agent into it, so each
seat gets its own Copi that hears only that seat. Copi's brain stays in the drill engine: the agent only
turns speech into /api/drill/copi/voice calls and speaks the radio lines addressed to its seat.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import APIRouter, Body, HTTPException

from .copilot import _load_dotenv

router = APIRouter()
AGENT_NAME = os.environ.get("COPI_AGENT", "copi")
# One radio channel per server run: the pilot and the tower talk on it, Copi listens without speaking.
RADIO_ROOM = f"radio-{secrets.token_hex(3)}"
# One private Copi line per seat per server run. A reload or a second tab joins the same room with the same
# identity, which replaces the old seat, so there is never a second Copi agent talking over the first.
COPI_ROOMS = {r: f"copi-{r}-{secrets.token_hex(3)}" for r in ("driver", "control")}


def _creds() -> tuple[str, str, str] | None:
    _load_dotenv()
    url, key, secret = (os.environ.get(k, "") for k in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"))
    return (url, key, secret) if url and key and secret else None


def _b64(b: bytes) -> bytes:
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def mint_token(key: str, secret: str, identity: str, room: str, agent_metadata: dict, ttl_s: int = 3 * 3600) -> str:
    now = int(time.time())
    claims = {
        "iss": key, "sub": identity, "name": identity, "nbf": now - 5, "exp": now + ttl_s,
        "video": {"roomJoin": True, "room": room, "canPublish": True, "canSubscribe": True, "canPublishData": True},
        # Dispatch the Copi agent into this room as soon as the browser joins it.
        "roomConfig": {"agents": [{"agentName": AGENT_NAME, "metadata": json.dumps(agent_metadata)}]},
    }
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), head + b"." + body, hashlib.sha256).digest())
    return (head + b"." + body + b"." + sig).decode()


@router.get("/api/voice/config")
async def config() -> dict:
    return {"enabled": _creds() is not None, "agent": AGENT_NAME}


@router.post("/api/voice/token")
async def token(p: dict = Body(default={})) -> dict:
    """channel "radio": the shared pilot-tower radio (Copi listens). channel "copi": the tower's private line to Copi."""
    role, channel = str(p.get("role", "")), str(p.get("channel", "copi"))
    if role not in ("driver", "control"):
        raise HTTPException(400, "role must be driver or control")
    if channel not in ("radio", "copi"):
        raise HTTPException(400, "channel must be radio or copi")
    if channel == "copi" and role != "control":
        raise HTTPException(403, "only the tower talks to Copi; the pilot talks to the tower")
    creds = _creds()
    if creds is None:
        raise HTTPException(503, "LiveKit is not configured (LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET)")
    url, key, secret = creds
    seat = "pilot" if role == "driver" else "tower"
    if channel == "radio":
        room, identity, meta = RADIO_ROOM, seat, {"role": "radio"}  # a fixed identity: a reload replaces the old seat
    else:
        room, identity, meta = COPI_ROOMS[role], seat, {"role": role}
    return {"url": url, "room": room, "identity": identity, "channel": channel,
            "token": mint_token(key, secret, identity, room, meta)}
