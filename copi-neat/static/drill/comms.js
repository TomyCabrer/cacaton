// Real voice for the drill, over LiveKit. Two channels:
//   radio  pilot and tower hear each other (hold T). Copi listens on it and never speaks there.
//   copi   the tower's private line: Copi speaks in the tower's ear; hold C to ask it something.
// Talking is push-to-talk: the microphone track stays published and is switched on only while the key or
// button is held, so the listener gets clean silence (and Copi a clean end of sentence) the moment it is let go.
"use strict";

const Comms = (() => {
  const LK = window.LivekitClient;
  let ctx = null;
  const audioCtx = () => (ctx ||= new (window.AudioContext || window.webkitAudioContext)());

  // Loudness of a MediaStreamTrack, 0..1, for the orb and the radio meter.
  function meter(mediaTrack) {
    try {
      const ac = audioCtx();
      const src = ac.createMediaStreamSource(new MediaStream([mediaTrack]));
      const an = ac.createAnalyser();
      an.fftSize = 512;
      src.connect(an);
      const buf = new Uint8Array(an.fftSize);
      return () => {
        an.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
        return Math.min(1, Math.sqrt(sum / buf.length) * 4.5);
      };
    } catch (e) {
      return () => 0;
    }
  }

  class Channel {
    constructor(role, channel) {
      this.role = role;
      this.channel = channel;
      this.state = "off"; // off | connecting | live | error
      this.error = "";
      this.talking = false;
      this.thinking = false;
      this.agentState = "";
      this.room = null;
      this.mic = null;
      this.levels = {}; // participant identity -> () => level
      this.listeners = new Set();
      this.video = null; // a remote video track (Copi's avatar), if one arrives
    }
    on(fn) { this.listeners.add(fn); fn(this); return this; }
    emit() { for (const fn of this.listeners) fn(this); }

    level(who) { // who: "me", "remote" (anyone else), or an identity prefix
      if (who === "me") return this.talking && this.levels.__me ? this.levels.__me() : 0;
      let best = 0;
      for (const [id, f] of Object.entries(this.levels)) {
        if (id === "__me") continue;
        if (who === "remote" || id.startsWith(who)) best = Math.max(best, f());
      }
      return best;
    }

    async connect() {
      if (!LK) { this.fail("voice library did not load (offline?)"); return; }
      if (!window.isSecureContext) { this.fail("the microphone needs https or localhost"); return; }
      if (this.state === "connecting" || this.state === "live") return;
      this.state = "connecting"; this.error = ""; this.emit();
      try {
        const r = await fetch("/api/voice/token", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: this.role, channel: this.channel }),
        });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `token ${r.status}`);
        const { url, token } = await r.json();
        const room = (this.room = new LK.Room({ adaptiveStream: true, dynacast: true }));
        room.on(LK.RoomEvent.TrackSubscribed, (track, pub, p) => {
          if (track.kind === "audio") {
            const el = track.attach();
            el.dataset.comms = this.channel;
            el.hidden = true;
            document.body.appendChild(el);
            this.levels[p.identity] = meter(track.mediaStreamTrack);
          } else if (track.kind === "video") {
            this.video = track;
          }
          this.emit();
        });
        room.on(LK.RoomEvent.TrackUnsubscribed, (track, pub, p) => {
          track.detach().forEach((el) => el.remove());
          if (track.kind === "audio") delete this.levels[p.identity];
          if (track === this.video) this.video = null;
          this.emit();
        });
        room.on(LK.RoomEvent.ParticipantAttributesChanged, (changed, p) => {
          if ("copi.thinking" in changed) this.thinking = changed["copi.thinking"] === "1";
          if ("lk.agent.state" in changed) this.agentState = changed["lk.agent.state"];
          this.emit();
        });
        room.on(LK.RoomEvent.ParticipantConnected, () => this.emit());
        room.on(LK.RoomEvent.ParticipantDisconnected, () => this.emit());
        room.on(LK.RoomEvent.Disconnected, () => { this.state = "off"; this.emit(); });
        await room.connect(url, token);
        await room.startAudio();
        this.mic = await LK.createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true, autoGainControl: true });
        this.mic.mediaStreamTrack.enabled = false;
        await room.localParticipant.publishTrack(this.mic);
        this.levels.__me = meter(this.mic.mediaStreamTrack);
        this.state = "live";
        this.emit();
      } catch (e) {
        this.fail(/Permission|NotAllowed/i.test(String(e)) ? "microphone blocked: allow it in the address bar" : String(e.message || e));
      }
    }

    fail(msg) { this.state = "error"; this.error = msg; this.emit(); }

    peers() { // remote humans and agents in the room
      return this.room ? Array.from(this.room.remoteParticipants.values()).map((p) => p.identity) : [];
    }

    talk(on) {
      if (this.state !== "live" || !this.mic) return;
      if (this.talking === on) return;
      this.talking = on;
      this.mic.mediaStreamTrack.enabled = on;
      if (ctx && ctx.state === "suspended") ctx.resume();
      this.emit();
    }
  }

  // Hold a key or a button to talk on a channel. Keys are ignored while typing in a field.
  function holdToTalk(channel, key, button, onDown) {
    let held = false;
    const down = (e) => {
      if (e) e.preventDefault();
      if (held) return;
      held = true;
      if (onDown) onDown();
      if (channel.state === "off" || channel.state === "error") channel.connect();
      channel.talk(true);
    };
    const up = (e) => {
      if (e) e.preventDefault();
      if (!held) return;
      held = false;
      setTimeout(() => channel.talk(false), 250); // keep the tail of the last word
    };
    if (button) {
      button.addEventListener("pointerdown", down);
      button.addEventListener("pointerup", up);
      button.addEventListener("pointerleave", up);
      button.addEventListener("pointercancel", up);
    }
    document.addEventListener("keydown", (e) => {
      if (e.key.toLowerCase() !== key || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
      down(e);
    });
    document.addEventListener("keyup", (e) => { if (e.key.toLowerCase() === key) up(e); });
    window.addEventListener("blur", () => up());
  }

  return { Channel, holdToTalk, available: Boolean(LK) };
})();
