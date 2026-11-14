// Control tower: the line, the protocol, and what Copi writes. The tower never sees the track, and after an
// LZB failure it does not see the trains either.
"use strict";

const ROLE = "control";
const CASE = "urda";
let S = null;
const sig = {}; // last rendered data per section, so the page only changes when its data does
const changed = (key, data) => {
  const j = JSON.stringify(data);
  if (sig[key] === j) return false;
  sig[key] = j;
  return true;
};

// ---------------------------------------------------------------- voice: the tower talks to the pilot, hold T
const radio = new Comms.Channel(ROLE, "radio");
const tuneIn = () => { Sound.unlock(); radio.connect(); };
document.addEventListener("pointerdown", tuneIn, { once: true });
document.addEventListener("keydown", tuneIn, { once: true });
Comms.holdToTalk(radio, "t", $("#btn-radio"));
radio.on((ch) => {
  $("#radio-state").textContent = ch.state === "live" ? (ch.talking ? "On air" : (ch.peers().includes("pilot") ? "" : "Pilot not on the radio yet"))
    : ch.state === "connecting" ? "Connecting…" : ch.state === "error" ? "No radio: " + ch.error : "";
  $("#btn-radio").classList.toggle("on", ch.talking);
});

// ---------------------------------------------------------------- top bar, banner, result
function renderTop(s) {
  $("#clock").textContent = s.case ? s.clock : "--:--:--";
  $("#case").textContent = s.case ? s.case.title : "Control tower";
  const b = $("#btn-main");
  b.textContent = s.state === "running" ? "End drill" : s.state === "ended" ? "Run again" : "Start";
  b.className = s.state === "running" ? "" : "solid";
}

let lzbWasDown = false;
function renderBanner(s) {
  const down = Boolean(s.lzb && s.lzb.down && s.state === "running");
  if (down && !lzbWasDown) Sound.alarm();
  lzbWasDown = down;
  if (!changed("banner", [down, s.outcome, s.state])) return;
  const el = $("#banner");
  if (s.outcome) {
    const o = s.outcome, [cls, tag] = RESULT[o.result] || RESULT.stopped;
    el.innerHTML = `<div class="result ${cls}">
      <div>
        <div class="tag">${tag}</div>
        <h2>${esc(o.title)}</h2>
        <p>${esc(o.detail)}</p>
        ${o.violations.length ? `<ul>${o.violations.map((v) => `<li class="breach">${esc(v.who === "driver" ? "Pilot" : "Tower")}: ${esc(v.text)}</li>`).join("")}</ul>` : ""}
        ${(o.reality || []).length ? `<div class="label">What happened at Urda</div><ol>${o.reality.map((r) => `<li>${esc(r)}</li>`).join("")}</ol>` : ""}
      </div>
      <table>${o.metrics.map((m) => `<tr><td>${esc(m.label)}</td><td>${esc(m.value)}</td></tr>`).join("")}</table>
    </div>`;
    o.result === "success" ? Sound.done() : Sound.alarm();
  } else if (down) {
    el.innerHTML = `<div class="alarm-bar" role="alert"><b>LZB FAILED</b><span>${esc(s.lzb.at || "")} · No cab signal. Train positions lost.</span></div>`;
  } else el.innerHTML = "";
}

// ---------------------------------------------------------------- line diagram
const W = 1200, PAD = 70, Y = { 1: 62, 2: 118 };
function renderLine(s) {
  if (!s.case) return;
  if (!changed("line", [s.trains, s.blind, s.case.view, s.state])) return;
  const [v0, v1] = s.case.view;
  const x = (pk) => PAD + ((pk - v0) / (v1 - v0)) * (W - 2 * PAD);
  let h = "";
  for (const p of s.line.places) if (p.pk >= v0 && p.pk <= v1) {
    const end = p.pk - v0 < 1 ? "start" : (v1 - p.pk < 1 ? "end" : "middle");
    h += `<text x="${x(p.pk)}" y="16" text-anchor="${end}" class="d-place">${esc(p.name)}</text>`;
  }
  for (const tr of [1, 2]) {
    h += `<text x="${PAD - 14}" y="${Y[tr] + 4}" text-anchor="end" class="d-track">T${tr}</text>` +
      `<line x1="${PAD}" y1="${Y[tr]}" x2="${W - PAD}" y2="${Y[tr]}" class="d-rail"/>`;
  }
  for (let pk = Math.ceil(v0); pk <= v1; pk++) {
    h += `<line x1="${x(pk)}" y1="158" x2="${x(pk)}" y2="${pk % 2 ? 162 : 166}" class="d-tick"/>`;
    if (pk % 2 === 0) h += `<text x="${x(pk)}" y="182" text-anchor="middle" class="d-pk">PK ${pk}</text>`;
  }
  const lastLabel = { 1: -1e9, 2: -1e9 }, below = { 1: false, 2: false }; // labels of two trains close together: one above, one below
  for (const t of (s.trains || []).slice().sort((p, q) => p.pk - q.pk)) {
    const a = x(Math.min(t.pk, t.rear_pk)), b = x(Math.max(t.pk, t.rear_pk));
    if (b < PAD - 40 || a > W - PAD + 40) continue;
    const y = Y[t.track], w = Math.max(b - a, 24), left = (a + b) / 2 - w / 2;
    below[t.track] = left - lastLabel[t.track] < 150 ? !below[t.track] : false;
    lastLabel[t.track] = left;
    const ny = below[t.track] ? y + 24 : y - 30, sy = below[t.track] ? y + 39 : y - 15;
    const dir = t.track === 2 ? 1 : -1, nose = dir === 1 ? left + w : left;
    const bad = t.status === "derailed" || t.status === "collided";
    const sub = t.lost ? `last seen ${t.seen}` : bad ? t.status : (t.stopped === true ? "stopped" : (t.human ? "pilot" : ""));
    h += `<g class="d-train${t.lost ? " lost" : ""}${bad ? " bad" : ""}">` +
      `<rect x="${left}" y="${y - 7}" width="${w}" height="14"/>` +
      `<path d="M${nose} ${y - 7} L${nose + dir * 8} ${y} L${nose} ${y + 7} Z"/>` +
      `<text x="${left}" y="${ny}" class="d-name">${esc(t.label)}</text>` +
      `<text x="${left}" y="${sy}" class="d-sub">${esc(sub)}</text></g>`;
  }
  $("#line").innerHTML = h;
  $("#diagram").classList.toggle("blind", Boolean(s.blind));
}

// ---------------------------------------------------------------- protocol
function renderProtocol(s) {
  const p = s.protocol;
  if (!changed("proto", [p && p.steps.map((x) => [x.status, x.note]), s.state])) return;
  const el = $("#protocol");
  if (!p) {
    el.innerHTML = `<div class="empty">${s.state === "ready" ? "None open. Press Start when the pilot is seated." : "None open."}</div>`;
    return;
  }
  const next = p.steps.find((x) => x.status !== "done");
  el.innerHTML = `<ol class="steps">${p.steps.map((st) => `
    <li class="${st.status === "done" ? "done" : (st === next ? "next" : "")}">
      <span class="n">${st.status === "done" ? "✓" : st.n}</span>
      <div><div class="t">${esc(st.title)}</div>${st.status === "done" && st.note ? `<div class="note">${esc(st.note)}</div>` : ""}</div>
    </li>`).join("")}</ol>`;
}

// ---------------------------------------------------------------- Copi: written flags, only when something is going wrong
let lastFlag = null;
function renderCopi(s) {
  const a = s.advisory, log = s.copi_log || [];
  const top = log.reduce((m, e) => Math.max(m, e.id), 0);
  if (lastFlag !== null && top > lastFlag) Sound.flag();
  lastFlag = top;
  if (!changed("copi", [a && [a.id, a.stage, a.text], log.map((e) => [e.id, e.heard, e.cleared]), s.state])) return;
  let h = "";
  if (a) {
    const acked = a.stage !== "tower";
    h += `<div class="flag${acked ? " acked" : ""}" role="alert"><div class="f-text">${esc(a.text)}</div>` +
      `<div class="f-foot">${acked ? "Heard" : '<button id="btn-heard">Heard <kbd>R</kbd></button>'}</div></div>`;
  } else {
    h += `<div class="empty">${s.state === "running" ? "Nothing to flag." : "Writes here only when something is going wrong."}</div>`;
  }
  const past = log.filter((e) => !a || e.id !== a.id).reverse();
  if (past.length) {
    h += `<ul class="flaglog">${past.map((e) => `<li><span class="mono">${esc(e.clock)}</span><span>${esc(e.text)}</span>` +
      `<span>${e.cleared ? "cleared" : (e.heard ? "heard" : "open")}</span></li>`).join("")}</ul>`;
  }
  $("#copi").innerHTML = h;
}
const heard = () => api("copi/ack", { role: ROLE });
$("#copi").addEventListener("click", (e) => { if (e.target.closest("#btn-heard")) heard(); });

// ---------------------------------------------------------------- the pilot's laptop
let join = null;
async function loadJoin() {
  try { join = await (await fetch("/api/drill/join")).json(); } catch (e) { join = null; }
  renderFoot();
}
function renderFoot() {
  if (!S) return;
  const on = S.online.driver > 0;
  $("#dot").classList.toggle("on", on);
  $("#pilot-text").textContent = on ? "Pilot connected" : "Pilot not connected";
  const link = join && (join.tunnel || join.lan);
  if (!changed("link", [on, link])) return;
  $("#link").innerHTML = on ? "" : (link ? `Pilot's link: <code>${esc(link)}</code>` : `Pilot's link: run <code>./drill.sh --tunnel</code>`);
}

// ---------------------------------------------------------------- frame
function render(s) {
  S = s;
  if (s.state === "lobby") { api("load", { case: CASE }); return; }
  renderTop(s);
  renderBanner(s);
  renderLine(s);
  renderProtocol(s);
  renderCopi(s);
  renderFoot();
}

$("#btn-main").onclick = () => {
  Sound.unlock();
  if (!S) return;
  if (S.state === "running") api("control/action", { kind: "end" });
  else if (S.state === "ended") api("load", { case: CASE });
  else api("start");
};
document.addEventListener("keydown", (e) => {
  if (typing(e) || e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;
  if (e.key.toLowerCase() === "r" && S && S.advisory && S.advisory.stage === "tower") heard();
});

loadJoin();
setInterval(loadJoin, 5000);
connect(ROLE, render);
