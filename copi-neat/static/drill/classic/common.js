// Shared by the pilot's cab and the control tower: server link, Copi's voice, Copi's ears.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

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
function connect(role, onState, onLink) {
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
        onLink && onLink(true);
        onState(s);
      } catch (e) {
        onLink && onLink(false);
        await new Promise((res) => setTimeout(res, 800));
      }
    }
  };
  if (/trycloudflare\.com$/.test(location.hostname)) return poll();
  const open = () => {
    if (polling) return;
    es = new EventSource("/api/drill/stream?role=" + role);
    es.onmessage = (e) => { gotOne = true; onLink && onLink(true); onState(JSON.parse(e.data)); };
    es.onerror = () => { onLink && onLink(false); if (es) es.close(); if (!polling) setTimeout(open, 1000); };
  };
  open();
  setTimeout(() => { if (!gotOne) poll(); }, 2500); // nothing came down the stream: the link is buffering it
}

// ---------------------------------------------------------------- sound
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
  chime() { this.tone(880, 0.12); this.tone(1320, 0.16, "sine", 0.08, 0.13); },
  // One sound per urgency, so the tower knows how urgent a line is before Copi has said a word.
  // urgent: three sharp beeps. important: two soft notes. info: nothing (it is on screen only).
  level(lvl) {
    if (lvl === "urgent") for (let i = 0; i < 3; i++) this.tone(988, 0.09, "square", 0.05, i * 0.13);
    else if (lvl === "important") { this.tone(587, 0.12, "sine", 0.06); this.tone(784, 0.16, "sine", 0.06, 0.13); }
  },
  alarm() { for (let i = 0; i < 3; i++) this.tone(620, 0.16, "square", 0.05, i * 0.22); },
  thump(strength = 1) {
    this.tone(55, 0.35, "sine", 0.35 * Math.min(strength, 2));
    this.tone(90, 0.18, "triangle", 0.2, 0.02);
  },
};

// ---------------------------------------------------------------- Copi's voice
const Voice = {
  on: true,
  speaking: false,
  quietUntil: 0, // Copi's ears ignore the room until this time, so Copi does not hear itself
  voice: null,
  pick() {
    const vs = speechSynthesis.getVoices();
    const want = ["Daniel", "Google UK English Male", "Arthur", "Google UK English Female", "Samantha"];
    this.voice = want.map((n) => vs.find((v) => v.name === n)).find(Boolean) || vs.find((v) => v.lang.startsWith("en")) || null;
  },
  say(text, level) {
    if (!this.on || !("speechSynthesis" in window)) return;
    if (!this.voice) this.pick();
    if (level === "urgent") speechSynthesis.cancel(); // an urgent line cuts in; everything else waits its turn
    const u = new SpeechSynthesisUtterance(text.replace(/\bPK\b/g, "P K").replace(/km\/h/g, "kilometres per hour"));
    if (this.voice) u.voice = this.voice;
    u.lang = (this.voice && this.voice.lang) || "en-GB";
    u.rate = level === "urgent" ? 1.2 : 1.08;
    u.onstart = () => { this.speaking = true; };
    const done = () => { this.speaking = speechSynthesis.speaking || speechSynthesis.pending; this.quietUntil = performance.now() + 700; };
    u.onend = done; u.onerror = done;
    if (typeof voiceBus !== "undefined" && voiceBus) voiceBus.postMessage("speak");
    speechSynthesis.speak(u);
  },
  hush() { if ("speechSynthesis" in window) speechSynthesis.cancel(); this.speaking = false; },
};
if ("speechSynthesis" in window) speechSynthesis.onvoiceschanged = () => Voice.pick();
// One voice at a time on this computer: when any tab starts speaking, the others stop.
const voiceBus = "BroadcastChannel" in window ? new BroadcastChannel("capi-voice") : null;
if (voiceBus) voiceBus.onmessage = () => Voice.hush();

// Speak every new line Copi addresses to this seat. Lines already on screen at page load stay silent.
function makeSpeaker(role) {
  let last = null;
  return (radio, toneOnly = false) => { // toneOnly: Copi's voice comes from somewhere else, play just the tone
    const mine = (radio || []).filter((m) => m.speak && m.to === role);
    const top = (radio || []).reduce((a, m) => Math.max(a, m.id), 0);
    if (last === null) { last = top; return; }
    if (top < last) last = 0; // a new drill started
    for (const m of mine) {
      if (m.id <= last) continue;
      Sound.level(m.level);
      if (!toneOnly) Voice.say(m.text, m.level);
    }
    last = top;
  };
}

// ---------------------------------------------------------------- Copi's ears
// Chrome speech-to-text. Two uses of one recogniser:
//   open microphone – every sentence heard goes to Copi as something said in the room
//   talk to Copi    – hold the button (or T), speak, release: Copi answers this seat
// Browsers open the microphone only on https or localhost, so on a plain LAN address
// the button falls back to typing.
class Ears {
  constructor(role, onStatus) {
    this.role = role;
    this.onStatus = onStatus || (() => {});
    this.SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.available = Boolean(this.SR) && window.isSecureContext;
    this.lang = localStorage.getItem("copi_lang") || "en-GB";
    this.open = false;
    this.ptt = false;
    this.buffer = "";
    this.interim = "";
    this.rec = null;
    this.running = false;
    this.denied = false;
  }
  status() {
    this.onStatus({ available: this.available, open: this.open, ptt: this.ptt, running: this.running, denied: this.denied,
                    interim: this.interim, lang: this.lang });
  }
  setLang(lang) { this.lang = lang; localStorage.setItem("copi_lang", lang); if (this.running) this.rec.stop(); this.status(); }
  setOpen(on) {
    this.open = on && this.available;
    localStorage.setItem("copi_open_" + this.role, this.open ? "1" : "0");
    this.sync();
  }
  sync() {
    const want = this.open || this.ptt;
    if (want && !this.running) this.start();
    else if (!want && this.running) this.rec.stop();
    this.status();
  }
  start() {
    if (!this.available || this.running) return;
    const rec = (this.rec = new this.SR());
    rec.continuous = true; rec.interimResults = true; rec.lang = this.lang;
    rec.onstart = () => {
      this.running = true;
      if (!this.open && !this.ptt) { this.closing = true; rec.stop(); } // the button was released before the microphone opened
      this.status();
    };
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i], text = res[0].transcript.trim();
        if (!res.isFinal) { interim += text + " "; continue; }
        if (!text) continue;
        if (this.ptt || this.closing) this.buffer += text + " ";
        else if (this.open && !Voice.speaking && performance.now() > Voice.quietUntil) api("copi/heard", { role: this.role, text });
      }
      this.interim = interim.trim();
      this.status();
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") { this.denied = true; this.open = false; this.ptt = false; }
    };
    rec.onend = () => {
      this.running = false; this.interim = "";
      if (this.closing) { this.closing = false; this.flush(); }
      if ((this.open || this.ptt) && !this.denied) setTimeout(() => this.start(), 150);
      this.status();
    };
    try { rec.start(); } catch (e) { /* already starting */ }
  }
  talkStart() {
    if (!this.available || this.ptt) return;
    Voice.hush();
    this.ptt = true; this.buffer = "";
    Sound.tone(660, 0.07);
    this.sync();
  }
  talkEnd() {
    if (!this.ptt) return;
    this.ptt = false;
    Sound.tone(440, 0.07);
    if (this.running) { this.closing = true; this.rec.stop(); } // stop forces the last words out as a final result
    else this.flush();
    this.status();
  }
  flush() {
    const text = (this.buffer + " " + this.interim).trim();
    this.buffer = "";
    if (text) askCopi(this.role, text);
  }
}

let onCopiBusy = () => {};
async function askCopi(role, text) {
  text = (text || "").trim();
  if (!text) return;
  onCopiBusy(true);
  await api("copi/ask", { role, text }); // the answer arrives over the stream and is spoken from there
  onCopiBusy(false);
}

// Wire a talk-to-Copi button: hold to speak where the microphone works, otherwise type.
function wireTalk(btn, ears, typeBox) {
  const down = (e) => { e.preventDefault(); Sound.unlock(); if (ears.available && !ears.denied) ears.talkStart(); else typeBox(); };
  const up = (e) => { e.preventDefault(); ears.talkEnd(); };
  btn.addEventListener("pointerdown", down);
  btn.addEventListener("pointerup", up);
  btn.addEventListener("pointerleave", up);
  let held = false;
  document.addEventListener("keydown", (e) => {
    if (e.key.toLowerCase() !== "t" || e.repeat || typing(e) || e.metaKey || e.ctrlKey) return;
    held = true; down(e);
  });
  document.addEventListener("keyup", (e) => { if (e.key.toLowerCase() === "t" && held) { held = false; up(e); } });
}

const typing = (e) => ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName);

function fmtFrom(m) {
  if (m.from === "copi") return "Copi";
  if (m.from === "driver") return "Pilot";
  if (m.from === "control") return "Tower";
  if (m.from === "voice") return m.heard_on === "driver" ? "Heard · cab" : "Heard · tower";
  if (m.from.startsWith("train:")) return m.from.slice(6);
  return "System";
}

function radioHtml(list, role) {
  return list.slice().reverse().map((m) => {
    const cls = m.from.startsWith("train:") ? "train" : m.from;
    const to = m.to === "copi" ? " → Copi" : (m.from === "copi" ? (m.to === "driver" ? " → pilot" : " → tower") : "");
    return `<div class="rmsg ${cls} k-${m.kind}${m.level ? " lv-" + m.level : ""}"><span class="rt">${m.clock}</span><span class="rf">${esc(fmtFrom(m))}${to}</span>` +
      `<span class="rx">${esc(m.text)}</span></div>`;
  }).join("") || '<div class="empty">Nothing said yet.</div>';
}

function debriefHtml(o, role) {
  const cls = o.result === "success" ? "ok" : (o.result === "failed" ? "bad" : "mid");
  return `<div class="modal-card debrief ${cls}">
    <div class="deb-tag">${o.result === "success" ? "Protocol complete" : (o.result === "failed" ? "Drill failed" : "Drill stopped")}</div>
    <h3>${esc(o.title)}</h3>
    <p>${esc(o.detail)}</p>
    <table class="cmp">${o.metrics.map((m) => `<tr><td>${esc(m.label)}</td><td class="t">${esc(m.value)}</td></tr>`).join("")}</table>
    ${o.violations.length ? `<div class="subhead">Protocol breaches</div><ul class="breaches">${o.violations.map((v) =>
      `<li><span class="mono">${v.clock}</span> ${esc(v.who === "driver" ? "pilot" : "tower")}: ${esc(v.text)}</li>`).join("")}</ul>` : ""}
    ${(o.reality || []).length ? `<div class="subhead">What really happened</div><ol class="reality">${o.reality.map((r) => `<li>${esc(r)}</li>`).join("")}</ol>` : ""}
    <p class="teach"><b>${esc(o.case)}</b> · ${esc(o.protocol || "no protocol opened")}<br>${esc(o.teaches)}</p>
    ${o.reconstruction ? `<p class="hint">${esc(o.reconstruction)}</p>` : ""}
    ${role === "control" ? '<button class="primary" id="deb-close">Back to the cases</button>' : '<p class="hint">The tower picks the next case.</p>'}
  </div>`;
}
