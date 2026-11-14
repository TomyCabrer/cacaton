// Control tower: line diagram, protocol, Copi, radio. The tower never sees the track.
"use strict";

const ROLE = "control";
let S = null;
const sig = {}; // last rendered signature per section, so the DOM only changes when its data does
const speak = makeSpeaker(ROLE);
const changed = (key, data) => {
  const j = JSON.stringify(data);
  if (sig[key] === j) return false;
  sig[key] = j;
  return true;
};

// Two voice channels: the radio to the pilot (hold T) and Copi's private line to the tower (hold C).
const radio = new Comms.Channel(ROLE, "radio");
const copiLine = new Comms.Channel(ROLE, "copi");
const connectVoice = () => { Sound.unlock(); radio.connect(); copiLine.connect(); };
document.addEventListener("pointerdown", connectVoice, { once: true });
document.addEventListener("keydown", connectVoice, { once: true });
Comms.holdToTalk(radio, "t", $("#btn-radio"), () => copiLine.talk(false));
Comms.holdToTalk(copiLine, "c", $("#orb"), () => radio.talk(false));

radio.on((ch) => {
  const st = $("#radio-state");
  st.textContent = ch.state === "live" ? (ch.talking ? "on air: the pilot hears you" : (ch.peers().includes("pilot") ? "pilot on the radio" : "radio on, no pilot yet"))
    : ch.state === "connecting" ? "tuning in…" : ch.state === "error" ? ch.error : "press to tune in";
  $("#btn-radio").classList.toggle("on", ch.talking);
  $("#btn-radio").classList.toggle("err", ch.state === "error");
  $("#peer-pilot").classList.toggle("here", ch.peers().includes("pilot"));
});
copiLine.on((ch) => {
  const agent = ch.peers().some((id) => id.startsWith("agent"));
  const state = ch.state !== "live" ? (ch.state === "connecting" ? "Copi is connecting" : ch.state === "error" ? "Copi's voice is off" : "Copi is off")
    : ch.talking ? "Listening to you" : ch.thinking ? "Thinking" : ch.agentState === "speaking" ? "Speaking" : agent ? "Listening" : "Waiting for Copi";
  $("#copi-state").textContent = state;
  $("#copi-hint").innerHTML = ch.state === "error" ? esc(ch.error) + " · Copi still writes below"
    : ch.state === "live" ? "Hold <kbd>C</kbd> or the circle to ask Copi" : "Press <kbd>C</kbd> or the circle to turn Copi's voice on";
  const orb = $("#orb");
  orb.dataset.state = ch.state !== "live" ? "off" : ch.talking ? "you" : ch.thinking ? "thinking" : ch.agentState === "speaking" ? "speaking" : "idle";
  const v = $("#copi-video");
  if (ch.video && v.dataset.sid !== ch.video.sid) { ch.video.attach(v); v.dataset.sid = ch.video.sid; v.hidden = false; orb.classList.add("face"); }
  if (!ch.video && !v.hidden) { v.hidden = true; v.dataset.sid = ""; orb.classList.remove("face"); }
});
(function meters() { // orb and radio meter follow the actual audio
  const orb = $("#orb");
  const copiLvl = copiLine.talking ? copiLine.level("me") : copiLine.level("remote");
  orb.style.setProperty("--lvl", copiLvl.toFixed(3));
  $("#btn-radio").style.setProperty("--lvl", radio.level("me").toFixed(3));
  $("#peer-pilot").style.setProperty("--lvl", radio.level("pilot").toFixed(3));
  requestAnimationFrame(meters);
})();

// ---------------------------------------------------------------- top bar
function renderTop(s) {
  $("#clock").textContent = s.state === "lobby" ? "--:--:--" : s.clock;
  $("#case-name").textContent = s.case ? `Case ${s.case.n} · ${s.case.title}` : "No case loaded";
  $("#dot-control").classList.toggle("on", s.online.control > 0);
  $("#dot-driver").classList.toggle("on", s.online.driver > 0);
  const start = $("#btn-start");
  start.disabled = s.state !== "ready";
  start.textContent = s.state === "ready" ? (s.online.driver > 0 ? "Start" : "Start (no pilot yet)") : (s.state === "running" ? "Running" : "Start");
  start.classList.toggle("running", s.state === "running");
  $("#btn-end").disabled = s.state !== "running";
  if (document.activeElement !== $("#speed")) $("#speed").value = String(s.speed);
}

let join = null;
async function loadJoin() {
  try { join = await (await fetch("/api/drill/join")).json(); } catch (e) { join = null; }
  renderJoin();
}
function renderJoin() {
  const el = $("#joinbar");
  if (!S || !join) return;
  if (S.online.driver > 0) { el.classList.add("hidden"); return; }
  el.classList.remove("hidden");
  const link = join.tunnel || join.lan;
  el.innerHTML = link
    ? `<b>Pilot's laptop:</b> open <code>${esc(link)}</code>` +
      (join.tunnel ? '<span>https link: the pilot gets the radio.</span>' : '<span>LAN link: no microphone on that laptop, so no radio. Run <code>./drill.sh --tunnel</code> for an https link.</span>')
    : `<b>Pilot's laptop:</b> this server only listens on this laptop. Start it with <code>./drill.sh</code> (same Wi-Fi) or <code>./drill.sh --tunnel</code> (any network, with microphone). ` +
      `Or open <a href="/drill/classic/driver" target="_blank">the pilot's seat</a> in a second window here.`;
}

// ---------------------------------------------------------------- line diagram
const W = 1400, Y1 = 62, Y2 = 118, PAD = 70;
const ASPECT = { clear: "oklch(0.78 0.16 152)", caution: "oklch(0.85 0.15 88)", stop: "oklch(0.66 0.21 25)" };
function renderLine(s) {
  const svg = $("#line");
  if (!s.case) { svg.innerHTML = `<text x="${W / 2}" y="92" text-anchor="middle" class="t-empty">Load a case to see the line.</text>`; return; }
  const [v0, v1] = s.case.view;
  const x = (pk) => PAD + ((pk - v0) / (v1 - v0)) * (W - 2 * PAD);
  const yOf = (track) => (track === 1 ? Y1 : Y2);
  const inView = (pk) => pk >= v0 - 0.01 && pk <= v1 + 0.01;
  let h = "";
  h += `<text x="8" y="${Y1 + 4}" class="t-lab">T1 ←</text><text x="8" y="${Y2 + 4}" class="t-lab">T2 →</text>`;
  h += `<line x1="${PAD}" y1="${Y1}" x2="${W - PAD}" y2="${Y1}" class="t-rail"/><line x1="${PAD}" y1="${Y2}" x2="${W - PAD}" y2="${Y2}" class="t-rail"/>`;
  for (let pk = Math.ceil(v0); pk <= v1; pk++) {
    h += `<line x1="${x(pk)}" y1="${Y2 + 26}" x2="${x(pk)}" y2="${Y2 + (pk % 2 ? 30 : 34)}" class="t-tick"/>`;
    if (pk % 2 === 0) h += `<text x="${x(pk)}" y="${Y2 + 46}" text-anchor="middle" class="t-lab">PK ${pk}</text>`;
  }
  if (s.lzb && s.lzb.down) {
    const a = x(Math.max(s.lzb.from_pk, v0)), b = x(Math.min(s.lzb.to_pk, v1));
    if (b > a) h += `<rect x="${a}" y="${Y1 - 30}" width="${b - a}" height="${Y2 - Y1 + 60}" class="t-lzb"/>` +
      `<text x="${a + 8}" y="${Y1 - 34}" class="t-lzb-lab">LZB down since ${esc(s.lzb.since)}: no cab signal</text>`;
  }
  for (const p of s.line.places) if (inView(p.pk)) h += `<text x="${x(p.pk)}" y="14" text-anchor="middle" class="t-place">${esc(p.name)}</text>`;
  for (const z of s.zones || []) {
    const a = x(Math.max(z.from, v0)), b = x(Math.min(z.to, v1));
    if (b > a) h += `<rect x="${a}" y="${yOf(z.track) - 7}" width="${b - a}" height="14" class="t-perm"/>` +
      `<text x="${a + 4}" y="${yOf(z.track) + (z.track === 1 ? 22 : -12)}" class="t-lab">limit ${z.kmh}</text>`;
  }
  for (const z of s.tsrs || []) {
    const a = x(Math.max(z.from, v0)), b = x(Math.min(z.to, v1));
    if (b > a) h += `<rect x="${a}" y="${yOf(z.track) - 8}" width="${Math.max(b - a, 6)}" height="16" class="t-zone"/>` +
      `<text x="${(a + b) / 2}" y="${yOf(z.track) + (z.track === 1 ? 22 : -12)}" text-anchor="middle" class="t-lab" fill="#ffd27a">${z.kmh} km/h</text>`;
  }
  if (s.site && inView(s.site.pk)) {
    const sx = x(s.site.pk), sy = yOf(s.site.track);
    h += `<circle cx="${sx}" cy="${sy}" class="svg-ring"/><path d="M${sx - 7} ${sy + 6} L${sx + 7} ${sy + 6} L${sx} ${sy - 8} Z" fill="oklch(0.66 0.21 25)"/>`;
  }
  for (const c of s.clips || []) if (inView(c.pk)) {
    const cx = x(c.pk), cy = yOf(c.track);
    h += `<path d="M${cx - 5} ${cy - 5} L${cx + 5} ${cy + 5} M${cx + 5} ${cy - 5} L${cx - 5} ${cy + 5}" stroke="#ffd27a" stroke-width="2.5"/>`;
  }
  for (const g of s.signals || []) {
    if (!inView(g.pk)) continue;
    const gx = x(g.pk), up = g.track === 1, gy = up ? Y1 - 18 : Y2 + 18;
    h += `<g class="t-sig" data-sig="${g.id}"><title>${g.id} · ${g.aspect}${g.held ? " · held by the tower" : ""}${g.occupied_by ? " · section occupied by " + esc(g.occupied_by) : ""}</title>` +
      `<line x1="${gx}" y1="${up ? Y1 - 2 : Y2 + 2}" x2="${gx}" y2="${gy}" stroke="oklch(0.55 0.012 75)" stroke-width="1.5"/>` +
      `<circle cx="${gx}" cy="${gy}" r="11" fill="transparent"/>` +
      (g.held ? `<circle cx="${gx}" cy="${gy}" r="8.5" fill="none" stroke="oklch(0.95 0.02 88)" stroke-width="2"/>` : "") +
      `<circle cx="${gx}" cy="${gy}" r="5.5" fill="${ASPECT[g.aspect]}"/>` +
      `<text x="${gx}" y="${up ? gy - 11 : gy + 17}" text-anchor="middle">${g.id}${g.fault ? " ⚠" : ""}${g.held ? " held" : ""}</text></g>`;
  }
  const lastLabel = { 1: -1e9, 2: -1e9 }, row = { 1: 0, 2: 0 }; // labels of trains close together step outwards
  for (const t of (s.trains || []).slice().sort((p, q) => p.pk - q.pk)) {
    const a = x(Math.min(t.pk, t.rear_pk)), b = x(Math.max(t.pk, t.rear_pk));
    if (b < PAD - 30 || a > W - PAD + 30) continue;
    const y = yOf(t.track), w = Math.max(b - a, 16), cx = (a + b) / 2, left = cx - w / 2;
    row[t.track] = cx - lastLabel[t.track] < 230 ? (row[t.track] + 1) % 2 : 0;
    lastLabel[t.track] = cx;
    const ly = t.track === 1 ? y + 22 + row[1] * 13 : y - 13 - row[2] * 13;
    const bad = t.status === "derailed" || t.status === "collided";
    const fill = bad ? "oklch(0.66 0.21 25)" : (t.human ? "oklch(0.82 0.08 228)" : (t.stopped ? "oklch(0.6 0.01 75)" : "oklch(0.88 0.01 80)"));
    const nose = t.track === 2 ? left + w : left, dir = t.track === 2 ? 1 : -1;
    h += `<g class="t-train"><rect x="${left}" y="${y - 6}" width="${w}" height="12" rx="3" fill="${fill}" ${t.human ? 'stroke="oklch(0.95 0.01 80)" stroke-width="1.5"' : ""}/>` +
      `<path d="M${nose} ${y - 6} L${nose + dir * 7} ${y} L${nose} ${y + 6} Z" fill="${fill}"/>` +
      `<text x="${cx}" y="${ly}" text-anchor="middle">${esc(trainLabel(t))}${t.human ? " · pilot" : ""} · ` +
      `${bad ? t.status.toUpperCase() : (t.stopped ? "stopped" : t.kmh + " km/h")}${t.called && !t.stopped ? " · braking" : ""}</text></g>`;
  }
  svg.innerHTML = h;
}
function trainLabel(t) { return (t.label || (String(t.id).length <= 2 ? `Train ${t.id}` : t.id)) + (t.name ? ` (${t.name})` : ""); }
$("#line").addEventListener("pointerdown", (e) => {
  const g = e.target.closest("[data-sig]");
  if (g && S && S.state === "running") api("control/action", { kind: "toggle_signal", signal: g.dataset.sig });
});

// ---------------------------------------------------------------- protocol
function renderProtocol(s) {
  const head = $("#proto-head"), body = $("#proto");
  if (!s.case || s.state === "lobby") {
    if (!changed("proto", ["cases", s.cases])) return;
    $("#proto-progress").textContent = "pick a case";
    head.innerHTML = "";
    body.innerHTML = s.cases.map((c) => `
      <div class="case-card">
        <div>
          <h4>${c.n}. ${esc(c.title)}</h4>
          <p>${esc(c.summary)}</p>
          <div class="meta"><span>${esc(c.protocol)} · ${esc(c.protocol_title)}</span><span class="chipm">${esc(c.model)}</span><span>${esc(c.train)}</span></div>
        </div>
        <button class="primary" data-load="${c.id}">Load</button>
      </div>`).join("") +
      `<div class="case-card"><div><h4>Surprise me</h4><p>A random case. The tower is not told which until the pilot reports.</p></div><button data-load="?">Load</button></div>`;
    return;
  }
  const p = s.protocol;
  if (!p) {
    if (!changed("proto", ["lib", s.library, s.state, s.case])) return;
    $("#proto-progress").textContent = "none open";
    head.innerHTML = `<div class="proto-head"><div class="proto-title">No protocol open</div>
      <div class="proto-src">${s.state === "ready" ? "Press Start when the pilot is seated." : "Copi opens one when the pilot reports something. You can also open one by hand."}</div></div>`;
    body.innerHTML = `<div class="subhead">Protocol library</div>` + s.library.map((l) => `
      <div class="lib-item"><div><span class="mono">${l.id}</span> · ${esc(l.title)} <span class="chipm">${esc(l.model)}</span></div>
      <button data-open="${l.id}" ${s.state === "running" ? "" : "disabled"}>Open</button></div>`).join("");
    return;
  }
  const done = p.steps.filter((x) => x.status === "done").length;
  $("#proto-progress").textContent = `${done} of ${p.steps.length} done`;
  if (!changed("proto", [p, s.next_step, s.suggest, s.state])) return;
  head.innerHTML = `<div class="proto-head">
    <div class="proto-id">${p.id} · opened ${p.clock} <span class="chipm">${esc(p.model)}</span></div>
    <div class="proto-title">${esc(p.title)}</div>
    <div class="proto-src">Matched from the ${esc(p.source)}. ${esc(p.why_model)}</div>
    ${s.suggest ? `<div class="alert high">A new report points to ${s.suggest.protocol} · ${esc(s.suggest.title)}. <button data-open="${s.suggest.protocol}">Switch</button></div>` : ""}
  </div>`;
  const doneIds = new Set(p.steps.filter((x) => x.status === "done").map((x) => x.id));
  body.innerHTML = p.steps.map((st) => {
    const locked = (st.after || []).some((a) => !doneIds.has(a));
    const cls = st.status === "done" ? "done" : (locked ? "locked" : (st.id === s.next_step ? "next" : ""));
    const who = st.who === "driver" ? "tell the pilot" : "you do";
    let row = "";
    if (st.status !== "done" && s.state === "running") {
      if (st.say) {
        const label = st.action ? st.action.label : (st.status === "sent" ? "Send again" : "Send to the pilot");
        row += `<button class="${st.id === s.next_step ? "primary" : ""}" data-step="${st.id}" data-op="send">${esc(label)}</button>`;
      } else if (st.action) {
        row += `<button class="${st.id === s.next_step ? "primary" : ""}" data-step="${st.id}" data-op="act">${esc(st.action.label)}</button>`;
      }
      if (st.status === "sent") {
        const by = st.sent_by === "copi" ? "Copi told the pilot" : (st.sent_by === "voice" ? "you said it on the radio" : "sent");
        row += `<span class="st-state wait">${by} · waiting for the pilot</span>`;
      } else if (!st.say && !st.action) row += `<span class="st-state wait">waiting · ticks itself</span>`;
      else if (locked) row += `<span class="st-state">after step ${p.steps.find((x) => x.id === st.after[0]).n}</span>`;
      if (st.who === "driver") row += `<button class="link" data-step="${st.id}" data-op="done">tick by hand</button>`;
    }
    return `<div class="step ${cls}">
      <div class="num">${st.status === "done" ? "✓" : st.n}</div>
      <div>
        <div class="who ${st.who}">${who}</div>
        <div class="st-title">${esc(st.title)}</div>
        <div class="st-detail">${esc(st.detail)}</div>
        ${st.say && st.status !== "done" ? `<div class="st-say">“${esc(st.say)}”</div>` : ""}
        ${row ? `<div class="st-row">${row}</div>` : ""}
        ${st.status === "done" ? `<div class="st-note">done ${fmtT(st.done_t)}${st.note ? " · " + esc(st.note) : ""}</div>` : ""}
      </div>
    </div>`;
  }).join("");
}
const fmtT = (t) => (t == null ? "" : `+${Math.round(t)} s`);

$("#proto").addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  Sound.unlock();
  if (b.dataset.load) {
    const ids = S.cases.map((c) => c.id);
    const hidden = b.dataset.load === "?";
    await api("load", { case: hidden ? ids[Math.floor(Math.random() * ids.length)] : b.dataset.load, hidden });
  } else if (b.dataset.open) await api("control/action", { kind: "protocol", id: b.dataset.open });
  else if (b.dataset.step) await api("control/step", { step: b.dataset.step, op: b.dataset.op });
});
$("#proto-head").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-open]");
  if (b) api("control/action", { kind: "protocol", id: b.dataset.open });
});

// ---------------------------------------------------------------- Copi
function renderCopi(s) {
  const co = s.copilot, a = s.advisory;
  const chip = $("#copi-chip");
  chip.textContent = co.mode === "live" ? `${co.model}${co.busy ? " · writing" : ""}` : (co.mode === "recorded" ? "recorded" : "rules only");

  const now = $("#copi-now");
  if (changed("adv", [a && [a.id, a.stage, a.pilot_text], s.state, !!s.protocol])) {
    if (!a) {
      now.innerHTML = `<div class="copi-now calm"><div class="cn-text">` +
        (s.state === "running" ? (s.protocol ? "Every step is covered." : "I am listening to the radio. If the pilot reports something, I tell you first.")
          : "I listen to the radio and tell you what matters. You give the orders.") + `</div></div>`;
    } else {
      // Three urgencies: urgent (red, act now), important (amber), info (on screen only, needs no R).
      // R is final: once heard, Copi says nothing more about this step.
      const toPilot = a.stage === "pilot" || a.stage === "pilot_acked";
      const lvlName = { urgent: "Urgent · act now", important: "Important", info: "For information" }[a.level] || "Copi suggests";
      now.innerHTML = `<div class="copi-now ${toPilot ? "pilot" : a.stage}${a.level ? " lv-" + a.level : ""}">
        <div class="cn-top"><span>${toPilot ? "Copi told the pilot" : lvlName}</span><span id="cn-count"></span></div>
        <div class="cn-text">${esc(toPilot ? a.pilot_text : a.text)}</div>
        <div class="cn-foot">${
          a.stage === "tower" ? `<button id="btn-heard" class="copi">Heard <kbd>R</kbd></button><div class="cn-bar"><i id="cn-fill"></i></div>`
          : a.stage === "silent" ? `<button id="btn-heard" class="copi">Heard <kbd>R</kbd></button><span>Still open. I will not say it again.</span>`
          : a.stage === "acked" ? "<span>Heard. Your call from here.</span>"
          : a.stage === "quiet" ? "<span>Nothing for you to do yet.</span>"
          : `<span>No answer from the tower, so I told the pilot${a.stage === "pilot_acked" ? ". The pilot heard." : "."}</span>`
        }</div></div>`;
    }
  }
  if (a && a.stage === "tower") {
    const left = Math.max(0, a.deadline - s.t), total = Math.max(1, a.deadline - a.t);
    const fill = $("#cn-fill"), cnt = $("#cn-count");
    if (fill) fill.style.width = `${Math.min(100, (left / total) * 100)}%`;
    if (cnt) cnt.textContent = left > 0 ? `${Math.ceil(left)} s` : "now";
  }

  const b = co.brief, rb = s.rules_brief, meta = co.meta;
  if (!changed("copi", [b, rb, meta, s.alerts, s.memory, co.busy, !!s.protocol])) return;
  let h = "";
  if (s.protocol) {
    const show = b || rb;
    h += `<div class="subhead">Copi's read of the situation <span class="chipm">${b && meta && meta.model ? `${esc(meta.model)} · ${meta.latency_ms ? (meta.latency_ms / 1000).toFixed(1) + " s" : "recorded"}` : `rules${co.busy ? " · Claude is writing" : ""}`}</span></div>`;
    if (show) {
      h += `<div class="brief-head">${esc(show.headline)}</div>`;
      if (show.say_to_pilot) h += `<div class="sayline"><span class="sl-tag">You could say</span><span>“${esc(show.say_to_pilot)}”</span></div>`;
      for (const c of show.cautions || []) h += `<div class="alert high">${esc(c)}</div>`;
      if ((show.ask || []).length) h += `<div class="subhead">Ask the pilot</div><ul class="unknowns">${show.ask.slice(0, 2).map((q) => `<li>${esc(q)}</li>`).join("")}</ul>`;
    }
    if (meta && meta.error) h += `<div class="briefing-error">Claude: ${esc(meta.error)}</div>`;
    if ((s.alerts || []).length) h += `<div class="subhead">Right now</div>` + s.alerts.map((x) => `<div class="alert ${x.level}">${esc(x.text)}</div>`).join("");
  }
  if ((s.memory || []).length && (s.protocol || s.state !== "lobby")) {
    h += `<details class="more"><summary>What Copi remembers about this stretch</summary>` + s.memory.map((m) =>
      `<div class="mem"><b>${esc(m.when)} · ${esc(m.source)}</b><br>${esc(m.text)}</div>`).join("") + `</details>`;
  }
  if (!s.protocol) {
    h += `<details class="more"><summary>Which Claude model Copi uses</summary><table class="route-table">` +
      s.routing.map((r) => `<tr><td class="mono">${r.protocol}</td><td>${esc(r.title)}<br><span class="hint">${esc(r.why)}</span></td><td><span class="chipm">${esc(r.model)}</span></td></tr>`).join("") +
      `<tr><td class="mono">ears</td><td>Reading what is said<br><span class="hint">Is this sentence a report, and of what?</span></td><td><span class="chipm">${esc(s.triage_model)}</span></td></tr></table></details>`;
  }
  $("#copi-body").innerHTML = h;
}
$("#copi-body").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-say]");
  if (b) api("control/say", { text: b.dataset.say });
});
$("#copi-now").addEventListener("click", (e) => { if (e.target.closest("#btn-heard")) heard(); });
// "Heard": Copi stops talking at once and drops the subject.
function heard() { Voice.hush(); api("copi/ack", { role: ROLE }); }

// ---------------------------------------------------------------- Urda-type cases: release, incoming calls, what Copi tracks
const minsSince = (since, clock) => {
  if (!since || !clock) return null;
  const [h1, m1] = since.split(":").map(Number), [h2, m2, s2] = clock.split(":").map(Number);
  return Math.max(0, Math.floor((h2 * 60 + m2 + (s2 || 0) / 60) - (h1 * 60 + m1)));
};
function renderRelease(s) {
  const el = $("#release"), z = s.lzb;
  const me = (s.trains || []).find((t) => t.human);
  if (!changed("release", [z && z.release, s.state, me && me.id])) return;
  if (!z || !me || s.state !== "running") { el.innerHTML = ""; return; }
  const mode = z.release || "none";
  const opt = (m, label, sub, cls = "") => `<button class="seg ${cls} ${mode === m ? "on" : ""}" data-release="${m}"><b>${label}</b><small>${sub}</small></button>`;
  el.innerHTML = `<div class="release"><div class="rel-head">${esc(me.label || "Train A")} <span>${esc(me.name || "")}</span>` +
    `<span class="rel-now">${mode === "none" ? "at a stand, waiting for you" : mode === "hold" ? "held" : mode === "on_sight" ? "released on sight" : "released, normal running"}</span></div>` +
    `<div class="segs">${opt("hold", "Hold", "stay at a stand")}${opt("on_sight", "On sight", "40 km/h max")}${opt("normal", "Normal running", "line speed", "risky")}</div></div>`;
}
$("#release").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-release]");
  if (b) { Sound.unlock(); api("control/action", { kind: "release", mode: b.dataset.release }); }
});

// Calls to the tower that are not Copi: other trains and the regulator. They ring, and are read out in a
// plain radio voice (not Copi's), so the tower hears who is calling without reading.
let lastCall = null;
function renderIncoming(s) {
  const calls = (s.radio || []).filter((m) => (m.from.startsWith("train:") || m.kind === "pressure") && (m.to === "control" || m.to === "all"));
  const top = calls.length ? calls[calls.length - 1] : null;
  if (lastCall === null) lastCall = top ? top.id : 0;
  else if (top && top.id > lastCall) {
    lastCall = top.id;
    Sound.chime();
    const caller = top.from.startsWith("train:") ? top.from.slice(6) : "Regulator";
    // Read aloud only when Copi's own line is down: a second voice next to Copi sounds like two Copis.
    if (copiLine.state !== "live" && Voice.on) Voice.say(top.text.toLowerCase().includes(caller.toLowerCase()) ? top.text : `${caller}: ${top.text}`);
  }
  const fresh = top && s.t - top.t < 40 ? top : null;
  if (!changed("incoming", [fresh && fresh.id, s.lzb && s.lzb.stopped && s.lzb.stopped.answered])) return;
  const el = $("#incoming");
  if (!fresh) { el.innerHTML = ""; return; }
  const isTrain = fresh.from.startsWith("train:");
  const who = isTrain ? fresh.from.slice(6) : "Regulator";
  const tid = isTrain ? (((s.trains || []).find((t) => t.label === who || `Train ${t.id}` === who)) || {}).id : null;
  el.innerHTML = `<div class="incoming ${isTrain ? "train" : "pressure"}"><span class="in-ring"></span><div><div class="in-who">${esc(who)} is calling · ${esc(fresh.clock)}</div>` +
    `<div class="in-text">“${esc(fresh.text)}”</div></div>` +
    (tid ? `<button data-answer="${esc(tid)}">Answer</button>` : "") + `</div>`;
}
$("#incoming").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-answer]");
  if (b) api("control/action", { kind: "radio_train", train: b.dataset.answer, ask: "status" });
});

// The open loops Copi holds so the tower does not have to: the Urda chain in one card.
function renderTracking(s) {
  const z = s.lzb, st = z && z.stopped, el = $("#tracking");
  const mins = st ? minsSince(z.since, s.clock) : null;
  if (!changed("tracking", [st, z && z.release, z && z.gap_km, mins])) return;
  if (!st) { el.innerHTML = ""; return; }
  const row = (bad, text) => `<li class="${bad ? "bad" : "ok"}"><i></i>${text}</li>`;
  el.innerHTML = `<div class="tracking"><div class="tr-head">Copi is keeping track of</div><ul>` +
    row(true, `<b>${esc(st.label)}</b> (${esc(st.name)}) stopped at ${esc(st.signal)}, PK ${st.pk.toFixed(1)}${mins != null ? `, for ${mins} min` : ""}`) +
    row(!st.answered, st.calls ? `${st.calls} call${st.calls > 1 ? "s" : ""} from ${esc(st.label)}: ${st.answered ? "answered" : "<b>not answered</b>"}` : `${esc(st.label)} has not called yet`) +
    (st.cannot_restart ? row(true, `${esc(st.label)} says it <b>cannot restart</b>`) : "") +
    row(true, `LZB down since ${esc(z.since)}: nothing in the cab stops Train A`) +
    (z.gap_km != null ? row(z.release === "normal", `Gap Train A to ${esc(st.label)}: <b>${z.gap_km.toFixed(1)} km</b>${z.release === "normal" ? ", closing at line speed" : ""}`) : "") +
    `</ul></div>`;
}

// ---------------------------------------------------------------- radio + manual controls
function renderRadio(s) {
  if (changed("radio", (s.radio || []).length ? s.radio[s.radio.length - 1].id : 0)) $("#radio").innerHTML = radioHtml(s.radio || [], ROLE);
  const ai = (s.trains || []).filter((t) => !t.human).map((t) => t.id);
  if (!changed("manual", [s.state, ai, s.tsrs])) return;
  const on = s.state === "running" ? "" : "disabled";
  $("#manual").innerHTML = `
    <button class="danger" data-act='{"kind":"emergency_call","track":"all"}' ${on}>Emergency call · all</button>
    <button data-act='{"kind":"emergency_call","track":"1"}' ${on}>Call T1</button>
    <button data-act='{"kind":"emergency_call","track":"2"}' ${on}>Call T2</button>
    ${ai.map((id) => `<button data-act='{"kind":"radio_train","train":"${id}","ask":"status"}' ${on}>Status ${esc(id)}</button>` +
      `<button data-act='{"kind":"radio_train","train":"${id}","ask":"resume"}' ${on}>Release ${esc(id)}</button>`).join("")}
    <span class="lab">Speed restriction</span>
    track <input id="tsr-track" value="1" style="width:34px"> PK <input id="tsr-from" placeholder="from"> – <input id="tsr-to" placeholder="to">
    <input id="tsr-kmh" value="30" style="width:44px"> km/h <button id="tsr-set" ${on}>Set</button>
    ${(s.tsrs || []).map((z) => `<button data-act='{"kind":"clear_tsr","id":"${z.id}"}' ${on}>Lift ${z.id}</button>`).join("")}`;
}
$("#manual").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.act) api("control/action", JSON.parse(b.dataset.act));
  else if (b.id === "tsr-set") api("control/action", { kind: "tsr", track: $("#tsr-track").value, from: $("#tsr-from").value, to: $("#tsr-to").value, kmh: $("#tsr-kmh").value });
});

// ---------------------------------------------------------------- frame
let shownOutcome = null;
function render(s) {
  S = s;
  renderTop(s);
  renderJoin();
  renderLine(s);
  renderProtocol(s);
  renderCopi(s);
  renderRelease(s);
  renderIncoming(s);
  renderTracking(s);
  renderRadio(s);
  speak(s.radio, copiLine.state === "live"); // Copi's own voice comes over its line when that is up: then only the tone
  const modal = $("#modal");
  if (s.outcome && shownOutcome !== s.outcome.title + s.t) {
    shownOutcome = s.outcome.title + s.t;
    modal.innerHTML = debriefHtml(s.outcome, ROLE);
    modal.classList.remove("hidden");
    s.outcome.result === "success" ? Sound.chime() : Sound.alarm();
  } else if (!s.outcome && !modal.classList.contains("hidden")) modal.classList.add("hidden");
}
$("#modal").addEventListener("click", (e) => {
  if (e.target.id === "deb-close") { $("#modal").classList.add("hidden"); api("load", { case: null }); }
  else if (e.target.id === "modal") $("#modal").classList.add("hidden");
});

$("#btn-start").onclick = () => { Sound.unlock(); api("start"); };
$("#btn-end").onclick = () => api("control/action", { kind: "end" });
$("#btn-cases").onclick = () => api("load", { case: null });
$("#speed").onchange = (e) => api("control/action", { kind: "speed", x: Number(e.target.value) });
const sendSay = () => { const i = $("#say"); if (i.value.trim()) api("control/say", { text: i.value }); i.value = ""; };
$("#btn-say").onclick = sendSay;
$("#say").addEventListener("keydown", (e) => { if (e.key === "Enter") sendSay(); });
document.addEventListener("keydown", (e) => {
  if (typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key.toLowerCase() === "r") { Sound.unlock(); heard(); }
});
document.addEventListener("pointerdown", () => Sound.unlock(), { once: true });

loadJoin();
setInterval(loadJoin, 5000);
connect(ROLE, render);
