// Pilot's cab: the view down the track and the driving desk. The pilot sees no protocol and no other screen:
// what to do comes from the tower, by voice.
"use strict";

const ROLE = "driver";
let S = null;
let seated = false;
let got = 0; // performance.now() when the last state arrived
const sig = {};
const changed = (key, data) => {
  const j = JSON.stringify(data);
  if (sig[key] === j) return false;
  sig[key] = j;
  return true;
};

// ---------------------------------------------------------------- voice: the pilot talks to the tower, hold T
const radio = new Comms.Channel(ROLE, "radio");
const tuneIn = () => { Sound.unlock(); radio.connect(); };
document.addEventListener("pointerdown", tuneIn, { once: true });
document.addEventListener("keydown", tuneIn, { once: true });
Comms.holdToTalk(radio, "t", $("#btn-radio"));
radio.on((ch) => {
  $("#radio-state").textContent = ch.state === "live" ? (ch.talking ? "On air" : (ch.peers().includes("tower") ? "" : "Tower not on the radio yet"))
    : ch.state === "connecting" ? "Connecting…" : ch.state === "error" ? "No radio: " + ch.error : "";
  $("#btn-radio").classList.toggle("on", ch.talking);
});

// ================================================================= the view down the track
const cv = $("#cab"), g = cv.getContext("2d");
let W = 0, H = 0, F = 0, HY = 0;
const CAM_H = 2.9, GAUGE = 0.7175, OTHER = -4.7; // metres: eye height, half gauge, centre of the other track
function resize() {
  const r = cv.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
  W = cv.width; H = cv.height; F = W * 0.82; HY = H * 0.44;
}
window.addEventListener("resize", resize);
const px = (X, Y, Z) => [W / 2 + (F * X) / Z, HY + (F * (CAM_H - Y)) / Z];
const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// Where the train is right now, between two states from the server.
let renderS = null; // metres travelled along the direction of travel
function nowPos() {
  const me = S.me, dt = Math.min(0.6, (performance.now() - got) / 1000) * (S.state === "running" ? S.speed : 0);
  const v = Math.max(0, me.v + me.a * dt);
  const moved = Math.max(0, ((me.v + v) / 2) * dt);
  const target = me.pk * 1000 * me.dir + moved;
  renderS = renderS === null || Math.abs(target - renderS) > 60 ? target : renderS + (target - renderS) * 0.35;
  return { s: renderS, v, dt };
}

function quad(pts, fill) {
  g.beginPath();
  g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.closePath(); g.fillStyle = fill; g.fill();
}
function strip(x0, x1, zn, zf, fill, y = 0) { quad([px(x0, y, zn), px(x1, y, zn), px(x1, y, zf), px(x0, y, zf)], fill); }

function drawTrack(cx, s, v) {
  strip(cx - 2.2, cx + 2.2, 3, 4000, "#dcdcd8"); // ballast
  const blur = Math.min(1, v / 22);
  if (blur < 1) { // sleepers, until speed smears them
    g.globalAlpha = 1 - blur * 0.85;
    const off = ((s % 0.6) + 0.6) % 0.6;
    for (let z = 3 + (0.6 - off); z < 70; z += 0.6) strip(cx - 1.25, cx + 1.25, z, z + 0.24, "#c2c2bc");
    g.globalAlpha = 1;
  }
  for (const sgn of [-1, 1]) strip(cx + sgn * GAUGE - 0.045, cx + sgn * GAUGE + 0.045, 3, 4000, "#1c1c1c", 0.17);
}

function drawMast(X, z, arm) {
  const [bx, by] = px(X, 0, z), [tx, ty] = px(X, 7.6, z), w = Math.max(1, (F * 0.2) / z);
  g.strokeStyle = "#8d8d8d"; g.lineWidth = w; g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty); g.stroke();
  const [ax, ay] = px(X + arm, 6.4, z);
  g.lineWidth = Math.max(1, w * 0.5); g.beginPath(); g.moveTo(tx, ty + (by - ty) * 0.1); g.lineTo(ax, ay); g.stroke();
}

function drawPost(z, label, km) {
  const [x, y] = px(2.0, 0, z), sc = F / z, h = (km ? 1.5 : 0.9) * sc, w = Math.max(2, (km ? 0.55 : 0.3) * sc);
  g.fillStyle = "#111"; g.fillRect(x - w / 2, y - h, w, h);
  if (z < (km ? 160 : 70)) { g.fillStyle = "#fff"; g.font = `700 ${Math.max(8, w * 0.42)}px ui-monospace, Menlo, monospace`; g.textAlign = "center"; g.fillText(label, x, y - h * 0.45); }
}

function drawTrain(o, dNose, dTail) {
  const cx = o.where === "own" ? 0 : OTHER, zn = Math.max(4, Math.min(dNose, dTail)), zf = Math.max(dNose, dTail);
  if (zf < 4) return;
  const facing = Math.min(dNose, dTail) === dNose; // true: its nose is towards us
  const side = cx < 0 ? cx + 1.45 : cx - 1.45; // the flank we can see
  quad([px(side, 0.4, zn), px(side, 3.9, zn), px(side, 3.9, zf), px(side, 0.4, zf)], "#c9c9c9");
  quad([px(side, 1.9, zn), px(side, 2.7, zn), px(side, 2.7, zf), px(side, 1.9, zf)], "#111");
  if (Math.min(dNose, dTail) > 4) {
    const [l, b] = px(cx - 1.45, 0.4, zn), [r, t] = px(cx + 1.45, 3.9, zn);
    g.fillStyle = "#efefef"; g.strokeStyle = "#111"; g.lineWidth = Math.max(1, (r - l) * 0.02);
    g.beginPath(); g.roundRect(l, t, r - l, b - t, (r - l) * 0.16); g.fill(); g.stroke();
    g.fillStyle = "#111"; g.fillRect(l + (r - l) * 0.14, t + (b - t) * 0.16, (r - l) * 0.72, (b - t) * 0.3);
    const rad = Math.max(2.2, (F * 0.17) / zn);
    g.fillStyle = facing ? "#f2c200" : "#d42a1c"; // headlights towards us, tail lights away
    for (const dx of [-0.95, 0.95]) { const [x, y] = px(cx + dx, 1.25, zn); g.beginPath(); g.arc(x, y, rad, 0, 7); g.fill(); }
  }
}

function frame() {
  requestAnimationFrame(frame);
  if (!W) resize();
  g.setTransform(1, 0, 0, 1, 0, 0);
  const sky = g.createLinearGradient(0, 0, 0, HY);
  sky.addColorStop(0, "#eef2f5"); sky.addColorStop(1, "#ffffff");
  g.fillStyle = sky; g.fillRect(0, 0, W, HY + 1);
  g.fillStyle = "#f4f4f1"; g.fillRect(0, HY, W, H - HY);
  if (!S || !S.me) return;

  const { s, v, dt } = nowPos();
  const me = S.me;
  g.fillStyle = "#e6ebef"; g.beginPath(); g.moveTo(0, HY); // far hills
  for (let i = 0; i <= 24; i++) g.lineTo((i / 24) * W, HY - (14 + 22 * hash(i + 5) + 10 * Math.sin(i * 0.9)) * (H / 700));
  g.lineTo(W, HY); g.closePath(); g.fill();

  drawTrack(OTHER, s, v);
  drawTrack(0, s, v);

  const items = []; // everything that stands along the line, drawn far to near
  const slot = (every, fn, reach) => { const base = Math.floor(s / every); for (let i = Math.ceil(reach / every); i >= 0; i--) { const z = (base + i + 1) * every - s; if (z > 3 && z < reach) fn(z, base + i + 1); } };
  slot(60, (z) => items.push([z, () => { drawMast(3.4, z, -3.0); drawMast(OTHER - 3.4, z, 3.0); }]), 1500);
  slot(100, (z, n) => {
    const pk = ((n * 100) / 1000) * me.dir, km = Math.abs(Math.round(pk * 10) % 10) === 0;
    items.push([z, () => drawPost(z, km ? Math.abs(pk).toFixed(0) : (Math.abs(pk * 10) % 10).toFixed(0), km)]);
  }, 500);
  for (const o of S.ahead) {
    if (o.kind !== "train") continue;
    const d = o.pk * 1000 * me.dir - s, move = o.dir * me.dir * o.v * dt, dn = d + move, dtail = o.rear_pk * 1000 * me.dir - s + move;
    items.push([Math.min(Math.max(dn, 4), Math.max(dtail, 4)), () => drawTrain(o, dn, dtail)]);
  }
  items.sort((a, b) => b[0] - a[0]);
  for (const [, draw] of items) draw();

  g.fillStyle = "#fff"; g.strokeStyle = "#111"; g.lineWidth = 2; // the edge of the desk
  g.beginPath(); g.moveTo(0, H); g.lineTo(0, H * 0.93); g.quadraticCurveTo(W / 2, H * 0.87, W, H * 0.93); g.lineTo(W, H); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(0, H * 0.93); g.quadraticCurveTo(W / 2, H * 0.87, W, H * 0.93); g.stroke();
  if (me.status === "collided") { g.fillStyle = "rgba(212,42,28,0.18)"; g.fillRect(0, 0, W, H); }
}

// ================================================================= desk
function renderDesk(s) {
  const me = s.me;
  $("#h-train").textContent = me.label;
  $("#h-route").textContent = [me.name, me.route].filter(Boolean).join(" · ");
  $("#h-clock").textContent = s.clock;
  $("#h-pk").textContent = s.state === "ready" ? "Waiting for the tower to start" : `PK ${me.pk.toFixed(1)}`;
  $("#v").textContent = Math.round(me.kmh);
  $("#cruise").textContent = me.cruise_kmh != null ? `· holding ${me.cruise_kmh}` : "";
  if (changed("lever", [me.notch, me.eb, me.cruise_kmh != null])) {
    let h = "";
    for (let i = -4; i <= 4; i++) {
      if (i === 0) { h += '<i class="n"></i>'; continue; }
      const on = me.eb ? i < 0 : (i < 0 ? me.notch <= i : me.notch >= i);
      h += `<i class="${i < 0 ? "b" : "p"} ${on ? "on" : ""}"></i>`;
    }
    $("#lever").innerHTML = h;
    const eb = $("#b-eb");
    eb.classList.toggle("on", me.eb);
    eb.firstChild.textContent = me.eb ? (me.kmh < 0.5 ? "Release brake " : "Emergency brake on ") : "Emergency brake ";
  }
  const top = s.alarms.find((a) => !a.text.startsWith("EMERGENCY BRAKE applied")); // the brake button already shows that one
  if (changed("alarm", top)) {
    $("#alarm").innerHTML = top ? `<div class="cab-alarm ${top.level === "red" ? "" : "amber"}" role="alert">${esc(top.text)}</div>` : "";
    $("#view").classList.toggle("alarmed", Boolean(top));
    if (top && top.level === "red") Sound.alarm();
  }
}

function renderSheet(s) {
  const o = s.outcome, hasCase = Boolean(s.me);
  if (!changed("sheet", [o && o.title, hasCase, seated, hasCase && s.case.brief])) return;
  const el = $("#sheet");
  if (o) {
    const [cls, tag] = RESULT[o.result] || RESULT.stopped;
    el.className = "sheet " + cls;
    el.innerHTML = `<div><div class="tag">${tag}</div><h2>${esc(o.title)}</h2><p>${esc(o.detail)}</p><p class="label">The tower starts the next run.</p></div>`;
    o.result === "success" ? Sound.done() : Sound.alarm();
  } else if (!hasCase || !seated) {
    el.className = "sheet";
    el.innerHTML = `<div><div class="tag">Pilot</div><h2>Train A</h2>` +
      `<p>${esc(hasCase ? s.case.brief : "Waiting for the tower.")}</p><button class="solid" id="btn-seat">Take the seat</button></div>`;
  } else el.className = "sheet hidden";
}

function render(s) {
  const first = !S;
  S = s; got = performance.now();
  if (first) resize();
  if (!s.me) renderS = null;
  else renderDesk(s);
  renderSheet(s);
}

// ================================================================= inputs
const input = (body) => api("driver/input", body);
const notch = (d) => { if (S && S.me) input({ notch: Math.max(-4, Math.min(4, (S.me.cruise_kmh != null ? 0 : S.me.notch) + d)) }); };
const eb = () => { if (S && S.me) input({ eb: !(S.me.eb && S.me.kmh < 0.5) }); };
$("#b-eb").onclick = eb;
$("#sheet").addEventListener("click", (e) => { if (e.target.id === "btn-seat") { seated = true; tuneIn(); if (S) renderSheet(S); } });
document.addEventListener("keydown", (e) => {
  if (typing(e) || e.metaKey || e.ctrlKey || e.altKey || !S || !S.me) return;
  const k = e.key.toLowerCase();
  if (k === "arrowup" || k === "w") { e.preventDefault(); notch(1); }
  else if (k === "arrowdown" || k === "s") { e.preventDefault(); notch(-1); }
  else if (k === "n" || k === "0") input({ notch: 0 });
  else if (k === "c") input({ cruise: !(S.me.cruise_kmh != null) });
  else if (k === " ") { e.preventDefault(); if (!e.repeat) eb(); }
});

connect(ROLE, render);
requestAnimationFrame(frame);
