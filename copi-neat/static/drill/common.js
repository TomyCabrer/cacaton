// Shared by the pilot's cab and the control tower: the link to the server, a few tones, result labels.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const typing = (e) => ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName);

async function api(path, body = {}) {
  try {
    const r = await fetch("/api/drill/" + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// Live state. An event stream where the link carries one; otherwise a long poll, which every link carries.
// (Cloudflare quick tunnels buffer event streams, so the pilot's laptop usually ends up on the long poll.)
function connect(role, onState) {
  let es = null, polling = false, gotOne = false;
  const poll = async () => {
    if (polling) return;
    polling = true;
    if (es) { es.close(); es = null; }
    let v = -1;
    for (;;) {
      try {
        const r = await fetch(`/api/drill/poll?role=${role}&v=${v}`);
        if (!r.ok) throw new Error(r.status);
        const s = await r.json();
        v = s.version;
        onState(s);
      } catch (e) {
        await new Promise((res) => setTimeout(res, 800));
      }
    }
  };
  if (/trycloudflare\.com$/.test(location.hostname)) return poll();
  const open = () => {
    if (polling) return;
    es = new EventSource("/api/drill/stream?role=" + role);
    es.onmessage = (e) => { gotOne = true; onState(JSON.parse(e.data)); };
    es.onerror = () => { if (es) es.close(); if (!polling) setTimeout(open, 1000); };
  };
  open();
  setTimeout(() => { if (!gotOne) poll(); }, 2500); // nothing came down the stream: the link is buffering it
}

// Sounds are tones only. Copi does not talk: what it has to say is written on the tower's screen.
const Sound = {
  ctx: null,
  unlock() {
    if (!this.ctx) {
      try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { /* no audio */ }
    }
    if (this.ctx && this.ctx.state === "suspended") this.ctx.resume();
  },
  tone(freq, dur = 0.12, type = "sine", gain = 0.08, when = 0) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when;
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.ctx.destination);
    o.start(t); o.stop(t + dur + 0.02);
  },
  alarm() { for (let i = 0; i < 3; i++) this.tone(620, 0.16, "square", 0.05, i * 0.22); }, // the LZB failure
  flag() { this.tone(587, 0.12, "sine", 0.07); this.tone(784, 0.18, "sine", 0.07, 0.13); }, // Copi wrote something
  done() { this.tone(880, 0.12); this.tone(1320, 0.16, "sine", 0.08, 0.13); },
};

// outcome.result -> [css class, word shown above the title]
const RESULT = { success: ["ok", "Done"], failed: ["bad", "Failed"], near_miss: ["mid", "Near miss"], stopped: ["mid", "Stopped"] };
