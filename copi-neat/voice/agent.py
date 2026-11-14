"""Copi's ears and mouth for the Copi drill.

One LiveKit room per seat (pilot or tower). The browser joins it with a token from /api/voice/token, and that
token dispatches this agent into the room. The agent:

  ears   speech -> text (LiveKit Inference STT) -> POST /api/drill/copi/voice   (Copi's brain is the drill engine)
  mouth  long-polls the seat's view and speaks every radio line Copi addresses to that seat (LiveKit Inference TTS)
  face   optional Synthesia interactive avatar that lip-syncs the same audio (SYNTHESIA_API_KEY + SYNTHESIA_AVATAR_IDS)

No LLM runs here: what Copi says is decided by the engine, which already picks the Claude model per protocol.

Rooms:  radio-*        pilot + tower talk to each other; Copi only listens (ears -> /api/drill/copi/heard)
        copi-control-* the tower's private line: Copi listens and speaks (only the tower hears Copi)

Run (drill.sh does this):  uv run --project voice voice/agent.py start
Env (.env next to drill.sh):        LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET; optional COPI_SERVER, COPI_AGENT,
                           COPI_LANG (en|es), COPI_VOICE, SYNTHESIA_API_KEY, SYNTHESIA_AVATAR_IDS, COPI_AVATAR_SEAT
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentServer, AgentSession, StopResponse, TurnHandlingOptions, inference, stt

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

log = logging.getLogger("copi-voice")

SERVER = os.environ.get("COPI_SERVER", f"http://127.0.0.1:{os.environ.get('PORT', '8000')}").rstrip("/")
AGENT_NAME = os.environ.get("COPI_AGENT", "copi")
LANG = os.environ.get("COPI_LANG", "en")
VOICES = {  # LiveKit Inference voices: calm, neutral, easy to hear over a noisy room
    "en": "cartesia/sonic-3:f31cc6a7-c1e8-4764-980c-60a361443dd1",  # Robyn, neutral mature female
    "es": "cartesia/sonic-3:5c5ad5e7-1020-476b-8b91-fdcbe9cc313c",  # Daniela, calm female
}
TTS_MODEL = os.environ.get("COPI_VOICE") or VOICES.get(LANG, VOICES["en"])
STT_MODEL = "assemblyai/universal-3-6-pro" if LANG == "en" else "deepgram/nova-3"

# Saying one of these on Copi's line means "heard": Copi stops talking at once (urgent lines and the queue
# included) and the engine logs it like the R key. Short utterances only, so "did you hear the pilot?" stays
# a question for the engine.
ACK = re.compile(r"\b(heard|hear|copy|copied|roger|recibido|entendido|o[ií]do)\b", re.I)
QUESTION = re.compile(r"^\W*(did|do|does|can|could|what|where|when|who|why|how|is|are|have|has)\b", re.I)


def is_ack(text: str) -> bool:
    words = re.findall(r"\w+", text)
    return 0 < len(words) <= 4 and "?" not in text and bool(ACK.search(text)) and not QUESTION.match(text)


def hush(session: AgentSession) -> None:
    """Stop Copi mid-sentence, urgent lines and anything queued included."""
    try:
        session.interrupt(force=True)
    except RuntimeError:  # the session is not running
        pass


def spoken(text: str) -> str:
    """Radio text written for the eye, made right for the ear."""
    text = re.sub(r"\bPK\s*(\d+)\.(\d)\b", r"P K \1 point \2", text)
    text = re.sub(r"\bPK\b", "P K", text)
    text = text.replace("km/h", " kilometres per hour").replace("→", "to")
    return re.sub(r"\s+", " ", text).strip()


class Copi(Agent):
    """Hears one seat. Every finished turn goes to the drill engine; the reply comes back over the radio."""

    def __init__(self, role: str, http: aiohttp.ClientSession, on_thinking) -> None:
        super().__init__(instructions="Copi's voice. Replies are decided by the drill engine, not here.")
        self.role, self.http, self.on_thinking = role, http, on_thinking

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = (new_message.text_content or "").strip()
        if text and is_ack(text):
            hush(self.session)
            asyncio.create_task(self._ack(text))
        elif text:
            asyncio.create_task(self._send(text))
        raise StopResponse()  # nothing to generate locally; the answer arrives as a radio line

    async def _ack(self, text: str) -> None:
        log.info("[%s] heard (ack): %s", self.role, text)
        try:
            async with self.http.post(f"{SERVER}/api/drill/copi/ack", json={"role": self.role},
                                      timeout=aiohttp.ClientTimeout(total=10)) as r:
                await r.read()
        except Exception as e:  # Copi already stopped talking; the R key still works
            log.warning("[%s] copi/ack failed: %s", self.role, e)

    async def _send(self, text: str) -> None:
        log.info("[%s] heard: %s", self.role, text)
        self.on_thinking(True)
        try:
            async with self.http.post(f"{SERVER}/api/drill/copi/voice", json={"role": self.role, "text": text},
                                      timeout=aiohttp.ClientTimeout(total=90)) as r:
                res = await r.json()
            if res.get("lobby"):
                self.session.say("No drill is loaded yet. The tower picks a case first.", add_to_chat_ctx=False)
            elif res.get("dropped"):
                log.info("[%s] dropped (%s)", self.role, res["dropped"])
        except Exception as e:  # keep listening whatever the server does
            log.warning("[%s] copi/voice failed: %s", self.role, e)
            self.session.say("I lost the link to the drill. Say that again in a moment.", add_to_chat_ctx=False)
        finally:
            self.on_thinking(False)


async def speak_radio(session: AgentSession, http: aiohttp.ClientSession, role: str) -> None:
    """Long-poll the seat's view; say every new line Copi addresses to this seat. Lines from before we joined stay silent."""
    v, last = -1, None
    while True:
        try:
            async with http.get(f"{SERVER}/api/drill/poll", params={"role": role, "v": v, "agent": 1},
                                timeout=aiohttp.ClientTimeout(total=20)) as r:
                s = await r.json()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("[%s] poll failed: %s", role, e)
            await asyncio.sleep(1.0)
            continue
        v = s.get("version", v)
        radio = s.get("radio") or []
        top = max((m["id"] for m in radio), default=0)
        if last is None or top < last:  # first look, or a new drill started
            last = top
            continue
        for m in radio:
            if m["id"] <= last:
                continue
            if m.get("kind") == "ack" and m.get("from") == role:  # the R key, the Heard button or a spoken "heard"
                hush(session)
            elif m.get("speak") and m.get("to") == role:
                urgent = bool(m.get("urgent")) or m.get("kind") in ("emergency", "alert")
                if urgent:
                    hush(session)  # force: a plain interrupt() raises on an urgent line and killed this loop
                try:
                    session.say(spoken(m["text"]), allow_interruptions=not urgent, add_to_chat_ctx=False)
                except RuntimeError as e:
                    log.warning("[%s] say failed: %s", role, e)
        last = top


async def radio_ears(ctx: agents.JobContext, http: aiohttp.ClientSession) -> None:
    """The pilot-tower radio. Copi never speaks here: it transcribes each seat and hands the words to the engine
    (/api/drill/copi/heard), which opens protocols from the pilot's reports and credits the tower's spoken orders."""
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    recognizer = inference.STT(model=STT_MODEL, language=LANG)
    busy: set[str] = set()

    async def post(seat: str, text: str) -> None:
        log.info("[radio] %s: %s", seat, text)
        try:
            async with http.post(f"{SERVER}/api/drill/copi/heard", json={"role": seat, "text": text},
                                 timeout=aiohttp.ClientTimeout(total=15)) as r:
                await r.read()
        except Exception as e:
            log.warning("[radio] heard failed: %s", e)

    async def listen(track: rtc.RemoteAudioTrack, participant: rtc.RemoteParticipant) -> None:
        seat = "driver" if participant.identity.startswith("pilot") else "control"
        key = f"{participant.identity}:{track.sid}"
        if key in busy:
            return
        busy.add(key)
        stream = recognizer.stream()

        async def feed() -> None:
            async for ev in rtc.AudioStream(track, sample_rate=16000, num_channels=1):
                stream.push_frame(ev.frame)
            stream.end_input()

        feeder = asyncio.create_task(feed())
        try:
            async for ev in stream:
                if ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT and ev.alternatives:
                    text = ev.alternatives[0].text.strip()
                    if len(text) > 2:
                        asyncio.create_task(post(seat, text))
        finally:
            feeder.cancel()
            busy.discard(key)

    @ctx.room.on("track_subscribed")
    def on_track(track, publication, participant) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.create_task(listen(track, participant))

    for p in ctx.room.remote_participants.values():
        for pub in p.track_publications.values():
            if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                asyncio.create_task(listen(pub.track, p))
    log.info("listening on the radio %s", ctx.room.name)


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: agents.JobContext):
    try:
        role = json.loads(ctx.job.metadata or "{}").get("role")
    except json.JSONDecodeError:
        role = None
    if role not in ("driver", "control", "radio"):
        role = "radio" if ctx.room.name.startswith("radio") else ("driver" if ctx.room.name.startswith("copi-driver") else "control")
    log.info("joining %s as Copi (%s)", ctx.room.name, role)

    http = aiohttp.ClientSession()
    ctx.add_shutdown_callback(http.close)
    if role == "radio":
        await radio_ears(ctx, http)
        return

    session = AgentSession(
        stt=inference.STT(model=STT_MODEL, language=LANG),
        tts=TTS_MODEL,
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )

    @session.on("user_input_transcribed")
    def _on_words(ev) -> None:
        # Act on "heard" as soon as the words appear, before the end of the turn: Copi stops mid-word.
        if is_ack(ev.transcript):
            hush(session)

    def on_thinking(busy: bool) -> None:
        # The page shows Copi thinking while the engine (and Claude) works on an answer.
        asyncio.create_task(ctx.room.local_participant.set_attributes({"copi.thinking": "1" if busy else "0"}))

    avatar_ids = [a.strip() for a in os.environ.get("SYNTHESIA_AVATAR_IDS", "").split(",") if a.strip()]
    if os.environ.get("SYNTHESIA_API_KEY") and avatar_ids and role == os.environ.get("COPI_AVATAR_SEAT", "control"):
        from livekit.plugins import synthesia

        avatar = synthesia.AvatarSession(synthesia.AvatarConfig(avatar_ids=avatar_ids[:5]))
        try:
            await avatar.start(session, room=ctx.room)
        except synthesia.SynthesiaError as e:
            log.error("Synthesia avatar failed (%s): %s. Copi stays voice-only.", e.type, e)

    await session.start(room=ctx.room, agent=Copi(role, http, on_thinking))
    task = asyncio.create_task(speak_radio(session, http, role))

    async def stop_radio() -> None:
        task.cancel()

    ctx.add_shutdown_callback(stop_radio)
    session.say(spoken("Copi here. I'm listening." if role == "control" else "Copi here. Talk to me any time."),
                add_to_chat_ctx=False)


if __name__ == "__main__":
    agents.cli.run_app(server)
