// Pilot's cab: the view down the track, the driving desk, the radio. The pilot never sees the protocol.
"use strict";

const ROLE = "driver";
let S = null;
let seated = false;
let got = 0; // performance.now() when the last state arrived
const speak = makeSpeaker(ROLE);
const sig = {};
const changed = (key, data) => {
  const j = JSON.stringify(data);
  if (sig[key] === j) return false;
  sig[key] = j;
  return true;
};

// The radio to the tower: hold T. Copi listens on it but only ever speaks to the tower.
const radio = new Comms.Channel(ROLE, "radio");
const tuneIn = () => { Sound.unlock(); radio.connect(); };
document.addEventListener("pointerdown", tuneIn, { once: true });
document.addEventListener("keydown", tuneIn, { once: true });
Comms.holdToTalk(radio, "t", $("#btn-radio"));
radio.on((ch) => {
  $("#radio-state").textContent = ch.state === "live" ? (ch.talking ? "on air: the tower hears you" : (ch.peers().includes("tower") ? "tower on the radio" : "radio on, no tower yet"))
    : ch.state === "connecting" ? "tuning in…" : ch.state === "error" ? ch.error : "press to tune in";
  $("#btn-radio").classList.toggle("on", ch.talking);
  $("#btn-radio").classList.toggle("err", ch.state === "error");
  $("#peer-tower").classList.toggle("here", ch.peers().includes("tower"));
  $("#say-row").classList.toggle("hidden", ch.state !== "error");
});
(function meters() {
  $("#btn-radio").style.setProperty("--lvl", radio.level("me").toFixed(3));
  $("#peer-tower").style.setProperty("--lvl", radio.level("tower").toFixed(3));
  requestAnimationFrame(meters);
})();

// ================================================================= the view down the track
const cv = $("#cab"), g = cv.getContext("2d");
let W = 0, H = 0, F = 0, HY = 0;
const CAM_H = 2.9, GAUGE = 0.7175, OTHER = -4.7; // metres: eye height, half gauge, centre of the other track
function resize() {
  const r = cv.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
  W = cv.width; H = cv.height; F = W * 0.82; HY = H * 0.42;
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
function glow(x, y, r, color) {
  const gr = g.createRadialGradient(x, y, 0, x, y, r * 4);
  gr.addColorStop(0, color); gr.addColorStop(0.25, color); gr.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = gr; g.beginPath(); g.arc(x, y, r * 4, 0, 7); g.fill();
  g.fillStyle = "#fff"; g.globalAlpha = 0.85; g.beginPath(); g.arc(x, y, Math.max(1, r * 0.5), 0, 7); g.fill(); g.globalAlpha = 1;
}

function drawTrack(cx, s, v) {
  strip(cx - 2.2, cx + 2.2, 3, 4000, "#3b3f47"); // ballast
  const blur = Math.min(1, v / 22);
  if (blur < 1) { // sleepers, until speed smears them
    g.globalAlpha = 1 - blur * 0.85;
    const off = ((s % 0.6) + 0.6) % 0.6;
    for (let z = 3 + (0.6 - off); z < 70; z += 0.6) strip(cx - 1.25, cx + 1.25, z, z + 0.24, "#262a31");
    g.globalAlpha = 1;
  }
  strip(cx - 1.3, cx + 1.3, 3, 4000, `rgba(30,33,39,${0.35 + 0.4 * blur})`);
  for (const sgn of [-1, 1]) strip(cx + sgn * GAUGE - 0.045, cx + sgn * GAUGE + 0.045, 3, 4000, "#aeb7c6", 0.17);
}

function drawMast(X, z, arm) {
  const [bx, by] = px(X, 0, z), [tx, ty] = px(X, 7.6, z), w = Math.max(1, (F * 0.22) / z);
  g.strokeStyle = "#1a1e25"; g.lineWidth = w; g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty); g.stroke();
  const [ax, ay] = px(X + arm, 6.4, z);
  g.lineWidth = Math.max(1, w * 0.5); g.beginPath(); g.moveTo(tx, ty + (by - ty) * 0.1); g.lineTo(ax, ay); g.stroke();
}

function drawTree(X, z, h, seed) {
  const [bx, by] = px(X, 0, z), [, ty] = px(X, h, z), r = ((F * h * 0.42) / z);
  g.fillStyle = seed > 0.5 ? "#0e1a17" : "#0b1513";
  g.beginPath(); g.ellipse(bx, (by + ty) / 2 - r * 0.2, r, (by - ty) * 0.62, 0, 0, 7); g.fill();
  g.fillRect(bx - Math.max(1, r * 0.08), by - (by - ty) * 0.3, Math.max(1, r * 0.16), (by - ty) * 0.3);
}

function drawSignal(o, z) {
  if (z < 4) return;
  const X = 2.7, [bx, by] = px(X, 0, z), [hx, hy] = px(X, 5.2, z), sc = F / z;
  g.strokeStyle = "#20252e"; g.lineWidth = Math.max(1, sc * 0.16); g.beginPath(); g.moveTo(bx, by); g.lineTo(hx, hy); g.stroke();
  const hw = Math.max(4, sc * 0.8), hh = Math.max(10, sc * 2.1);
  g.fillStyle = "#07090c"; g.fillRect(hx - hw / 2, hy - hh, hw, hh);
  g.strokeStyle = "#d9dee8"; g.lineWidth = Math.max(0.7, sc * 0.05); g.strokeRect(hx - hw / 2, hy - hh, hw, hh); // white border: readable even unlit
  const lamps = [["clear", "#31e58b"], ["caution", "#ffcf3a"], ["stop", "#ff3b3b"]];
  lamps.forEach(([a, col], i) => {
    const ly = hy - hh + hh * (0.2 + i * 0.3), r = Math.max(1.8, sc * 0.24);
    if (o.aspect === a) glow(hx, ly, r, col);
    else { g.fillStyle = "#1a1d22"; g.beginPath(); g.arc(hx, ly, r, 0, 7); g.fill(); }
  });
  if (z < 220) {
    g.fillStyle = "#e9edf3"; g.font = `${Math.max(9, sc * 0.42)}px ui-monospace, Menlo, monospace`; g.textAlign = "center";
    g.fillText(o.id, hx, hy + Math.max(10, sc * 0.6));
  }
}

function drawBoard(o, z) {
  if (z < 4) return;
  const [x, y] = px(2.3, 2.4, z), [bx, by] = px(2.3, 0, z), r = Math.max(4, (F * 0.55) / z);
  g.strokeStyle = "#20252e"; g.lineWidth = Math.max(1, r * 0.12); g.beginPath(); g.moveTo(bx, by); g.lineTo(x, y); g.stroke();
  g.fillStyle = "#f4d03f"; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
  g.strokeStyle = "#111"; g.lineWidth = Math.max(1, r * 0.1); g.stroke();
  if (r > 7) { g.fillStyle = "#111"; g.font = `700 ${r * 0.85}px ui-monospace, Menlo, monospace`; g.textAlign = "center"; g.fillText(o.kmh, x, y + r * 0.3); }
}

function drawPost(z, label, km) {
  const [x, y] = px(2.0, 0, z), sc = F / z, h = (km ? 1.5 : 0.9) * sc, w = Math.max(2, (km ? 0.55 : 0.3) * sc);
  g.fillStyle = "#e6e9ef"; g.fillRect(x - w / 2, y - h, w, h);
  if (z < (km ? 160 : 70)) { g.fillStyle = "#0b0e13"; g.font = `700 ${Math.max(8, w * 0.42)}px ui-monospace, Menlo, monospace`; g.textAlign = "center"; g.fillText(label, x, y - h * 0.45); }
}

function drawDebris(o, z) {
  if (z < 3) return;
  const cx = o.where === "own" ? 0 : OTHER;
  // scar on the cutting above the track, then the pile across the rails
  const side = cx < 0 ? -1 : 1; // the slide comes off the bank on the outer side of that track
  quad([px(cx + side * 16, 12, z + 10), px(cx + side * 7, 10, z + 6), px(cx + side * 1.0, 0, z), px(cx + side * 9, 0, z + 4)], "#9a8e78");
  quad([px(cx + side * 13, 9, z + 9), px(cx + side * 8, 8, z + 6), px(cx + side * 2.4, 0.4, z + 1), px(cx + side * 7, 0.2, z + 3)], "#c2b59a");
  const [hx, hy] = px(cx, 1.6, z), hr = (F * 6) / z; // dust still hanging over it
  const haze = g.createRadialGradient(hx, hy, 0, hx, hy, hr);
  haze.addColorStop(0, "rgba(214,200,172,0.42)"); haze.addColorStop(1, "rgba(214,200,172,0)");
  g.fillStyle = haze; g.beginPath(); g.arc(hx, hy, hr, 0, 7); g.fill();
  for (let i = 0; i < 16; i++) {
    const X = cx - 2.8 + hash(i + 3) * 5.6, r = 0.8 + hash(i + 11) * 1.5, zz = z + (hash(i + 21) - 0.5) * 7;
    if (zz < 3) continue;
    const [x, y] = px(X, 0, zz), R = (F * r) / zz;
    g.fillStyle = i % 3 === 0 ? "#d6cab0" : (i % 2 ? "#b0a48d" : "#93886f");
    g.beginPath(); g.moveTo(x - R, y); g.lineTo(x - R * 0.5, y - R * 1.1); g.lineTo(x + R * 0.4, y - R * 1.3); g.lineTo(x + R, y - R * 0.3); g.lineTo(x + R * 0.8, y); g.closePath(); g.fill();
  }
}

function drawTrain(o, dNose, dTail) {
  const cx = o.where === "own" ? 0 : OTHER, zn = Math.max(4, Math.min(dNose, dTail)), zf = Math.max(dNose, dTail);
  if (zf < 4) return;
  const facing = Math.min(dNose, dTail) === dNose; // true: its nose is towards us
  const bad = o.status === "derailed" || o.status === "collided";
  const side = cx < 0 ? cx + 1.45 : cx - 1.45; // the flank we can see
  if (zn < 900) {
    quad([px(side, 0.4, zn), px(side, 3.9, zn), px(side, 3.9, zf), px(side, 0.4, zf)], bad ? "#5a2022" : "#c9ced8");
    quad([px(side, 1.9, zn), px(side, 2.7, zn), px(side, 2.7, zf), px(side, 1.9, zf)], "#1b2a44");
    if (Math.min(dNose, dTail) > 4) {
      const [l, b] = px(cx - 1.45, 0.4, zn), [r, t] = px(cx + 1.45, 3.9, zn);
      g.fillStyle = bad ? "#6b2326" : "#dfe3ea"; g.beginPath(); g.roundRect(l, t, r - l, b - t, (r - l) * 0.18); g.fill();
      g.fillStyle = "#0d1420"; g.fillRect(l + (r - l) * 0.14, t + (b - t) * 0.16, (r - l) * 0.72, (b - t) * 0.3);
    }
  }
  if (Math.min(dNose, dTail) > 4) {
    const r = Math.max(1.8, (F * 0.16) / zn), col = facing ? "rgba(255,250,225,0.95)" : "rgba(255,40,40,0.95)";
    for (const dx of [-0.95, 0.95]) { const [x, y] = px(cx + dx, 1.25, zn); glow(x, y, facing ? r * 1.3 : r, col); }
    if (facing) { const [x, y] = px(cx, 3.5, zn); glow(x, y, r, col); }
  }
}

let shake = { n: 0, until: 0, power: 0 };
function frame() {
  requestAnimationFrame(frame);
  if (!W) resize();
  g.setTransform(1, 0, 0, 1, 0, 0);
  // dusk sky
  const sky = g.createLinearGradient(0, 0, 0, HY);
  sky.addColorStop(0, "#0a1024"); sky.addColorStop(0.6, "#2b2c4d"); sky.addColorStop(0.92, "#a8563c"); sky.addColorStop(1, "#e08a4a");
  g.fillStyle = sky; g.fillRect(0, 0, W, HY + 1);
  const gnd = g.createLinearGradient(0, HY, 0, H);
  gnd.addColorStop(0, "#1a1d1b"); gnd.addColorStop(1, "#0c0f0d");
  g.fillStyle = gnd; g.fillRect(0, HY, W, H - HY);
  if (!S || !S.me) return;

  const { s, v, dt } = nowPos();
  const me = S.me, t = performance.now();
  // jolt: the cab shakes; a derailed train keeps shaking and leans
  let ox = 0, oy = 0, tilt = 0;
  if (t < shake.until) { const k = (shake.until - t) / 900; ox = (Math.random() - 0.5) * 22 * shake.power * k; oy = (Math.random() - 0.5) * 30 * shake.power * k; }
  if (me.status === "derailed") { tilt = -0.022; if (v > 0.5) { ox += (Math.random() - 0.5) * 9; oy += (Math.random() - 0.5) * 12; } }
  g.translate(W / 2 + ox, H / 2 + oy); g.rotate(tilt); g.translate(-W / 2, -H / 2);

  // far hills
  g.fillStyle = "#141a26"; g.beginPath(); g.moveTo(0, HY);
  for (let i = 0; i <= 24; i++) g.lineTo((i / 24) * W, HY - (18 + 26 * hash(i + 5) + 12 * Math.sin(i * 0.9)) * (H / 700));
  g.lineTo(W, HY); g.closePath(); g.fill();

  drawTrack(OTHER, s, v);
  drawTrack(0, s, v);
  // catenary wires
  g.strokeStyle = "rgba(15,18,24,0.9)"; g.lineWidth = 1.2;
  for (const cx of [0, OTHER]) { const [a, b] = px(cx, 5.3, 6), [c, d] = px(cx, 5.3, 4000); g.beginPath(); g.moveTo(a, b); g.lineTo(c, d); g.stroke(); }

  // everything that stands along the line, far to near
  const items = [];
  const slot = (every, fn, reach) => { const base = Math.floor(s / every); for (let i = Math.ceil(reach / every); i >= 0; i--) { const z = (base + i + 1) * every - s; if (z > 3 && z < reach) fn(z, base + i + 1); } };
  slot(60, (z) => items.push([z, () => { drawMast(3.4, z, -3.0); drawMast(OTHER - 3.4, z, 3.0); }]), 1500);
  slot(35, (z, n) => {
    const a = hash(n), b = hash(n + 0.5);
    if (a > 0.35) items.push([z, () => drawTree(9 + a * 26, z, 4 + b * 6, b)]);
    if (b > 0.4) items.push([z, () => drawTree(OTHER - 9 - b * 30, z, 4 + a * 7, a)]);
  }, 900);
  slot(100, (z, n) => {
    const pk = ((n * 100) / 1000) * me.dir, km = Math.abs(Math.round(pk * 10) % 10) === 0;
    items.push([z, () => drawPost(z, km ? Math.abs(pk).toFixed(0) : (Math.abs(pk * 10) % 10).toFixed(0), km)]);
  }, 500);
  for (const o of S.ahead) {
    const d = (o.pk * 1000 * me.dir - s);
    if (o.kind === "signal") items.push([d, () => drawSignal(o, d)]);
    else if (o.kind === "board") items.push([d, () => drawBoard(o, d)]);
    else if (o.kind === "debris") items.push([d, () => drawDebris(o, d)]);
    else if (o.kind === "train") {
      const move = o.dir * me.dir * o.v * dt, dn = d + move, dtail = o.rear_pk * 1000 * me.dir - s + move;
      items.push([Math.min(Math.max(dn, 4), Math.max(dtail, 4)), () => drawTrain(o, dn, dtail)]);
    }
  }
  items.sort((a, b) => b[0] - a[0]);
  for (const [, draw] of items) draw();

  // headlight pool and the cab itself
  g.setTransform(1, 0, 0, 1, 0, 0);
  const pool = g.createRadialGradient(W / 2, H * 0.98, 10, W / 2, H * 0.98, W * 0.5);
  pool.addColorStop(0, "rgba(255,240,200,0.10)"); pool.addColorStop(1, "rgba(255,240,200,0)");
  g.fillStyle = pool; g.fillRect(0, HY, W, H - HY);
  g.fillStyle = "#07090c";
  g.beginPath(); g.moveTo(0, H); g.lineTo(0, H * 0.9); g.quadraticCurveTo(W / 2, H * 0.83, W, H * 0.9); g.lineTo(W, H); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(0, 0); g.lineTo(W * 0.035, 0); g.lineTo(W * 0.012, H); g.lineTo(0, H); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(W, 0); g.lineTo(W * 0.965, 0); g.lineTo(W * 0.988, H); g.lineTo(W, H); g.closePath(); g.fill();
  if (me.eb || me.status === "derailed") { g.fillStyle = `rgba(255,40,40,${0.06 + 0.05 * Math.sin(t / 130)})`; g.fillRect(0, 0, W, H); }
}

// ================================================================= desk
function renderDesk(s) {
  const me = s.me;
  $("#h-train").textContent = String(me.id).length <= 2 ? `Train ${me.id}` : me.id;
  $("#h-route").textContent = [me.name || me.model, me.route, `track ${me.track}`].filter(Boolean).join(" · ");
  $("#h-pk").textContent = `PK ${me.pk.toFixed(1)}`;
  $("#h-clock").textContent = s.clock + (s.speed !== 1 ? ` · ${s.speed}×` : "");
  const ns = s.next_signal;
  $("#h-sig").textContent = ns ? `next signal ${ns.id} · ${ns.in_m >= 1000 ? (ns.in_m / 1000).toFixed(1) + " km" : Math.round(ns.in_m / 10) * 10 + " m"}` : "";
  const v = $("#v");
  v.textContent = Math.round(me.kmh);
  v.classList.toggle("over", me.kmh > me.limit_kmh + 5);
  $("#lim").textContent = me.limit_kmh;
  $("#next-lim").innerHTML = me.next_limit ? `then <b>${me.next_limit.kmh}</b> in ${(me.next_limit.in_m / 1000).toFixed(1)} km` : "";
  $("#cruise").innerHTML = me.cruise_kmh != null ? `holding <b>${me.cruise_kmh}</b>` : "";
  if (changed("lever", [me.notch, me.eb, me.cruise_kmh != null])) {
    let h = "";
    for (let i = -4; i <= 4; i++) {
      if (i === 0) { h += '<i class="n"></i>'; continue; }
      const on = me.eb ? i < 0 : (i < 0 ? me.notch <= i : me.notch >= i);
      h += `<i class="${i < 0 ? "b" : "p"} ${on ? "on" : ""}"></i>`;
    }
    $("#lever").innerHTML = h;
    $("#b-eb").textContent = me.eb ? (me.kmh < 0.5 ? "Release emergency brake" : "EMERGENCY BRAKE ON") : "EMERGENCY BRAKE";
    $("#b-cruise").classList.toggle("primary", me.cruise_kmh != null);
  }
  if (changed("alarms", s.alarms)) {
    $("#alarms").innerHTML = s.alarms.map((a) => `<div class="alarm ${a.level}">${esc(a.text)}</div>`).join("");
    if (s.alarms.some((a) => a.level === "red")) Sound.alarm();
  }
  if (changed("cats", s.categories)) {
    $("#reports").innerHTML = s.categories.map((c, i) => c.options
      ? c.options.map((o, j) => `<button data-cat="${c.id}" data-where="${o.id}">${esc(c.label)}: ${esc(o.label.toLowerCase())}${j === 0 ? ` <kbd>${i + 1}</kbd>` : ""}</button>`).join("")
      : `<button data-cat="${c.id}">${esc(c.label)} <kbd>${i + 1}</kbd></button>`).join("");
  }
  // jobs: look back, clip
  const ins = s.jobs.inspect, cl = s.jobs.clip, stopped = me.kmh < 0.5;
  $("#b-inspect").disabled = !stopped || ins.running || ins.done;
  $("#b-inspect").textContent = ins.running ? "Looking back…" : (ins.done ? "Looked back" : "Look back along the train");
  $("#b-clip").disabled = !stopped || cl.running || cl.done;
  $("#b-clip").textContent = cl.running ? "Placing clips…" : (cl.done ? "Other track clipped" : "Clip the other track");
  const prog = $("#job-prog"), run = ins.running ? ins : (cl.running ? cl : null);
  prog.classList.toggle("hidden", !run);
  if (run) prog.firstChild.style.width = `${run.progress * 100}%`;
  if (changed("finding", [ins.done, ins.text, ins.reported])) {
    const f = $("#finding");
    f.classList.toggle("hidden", !ins.done);
    f.innerHTML = ins.done ? `You look back: <b>${esc(ins.text)}</b> ${ins.reported ? "<span class='hint'>· reported</span>" : '<button id="b-find" class="primary">Tell the tower</button>'}` : "";
  }
}

function renderInstr(s) {
  const i = s.instruction, el = $("#instr");
  if (!changed("instr", i)) return;
  if (!i) { el.classList.add("hidden"); return; }
  el.className = "instr " + (i.kind === "emergency" ? "emergency" : (i.from === "copi" ? "copi" : "")) + (i.acked ? " acked" : "");
  $("#i-from").textContent = `${i.from === "copi" ? "Copi" : "Control tower"} · ${i.clock}${i.acked ? " · heard" : ""}`;
  $("#i-text").textContent = i.text;
  $("#i-btns").innerHTML = i.acked ? "" : (i.expect === "readback"
    ? '<button class="primary big" id="b-readback">Read back <kbd>R</kbd></button>'
    : '<button class="primary big" id="b-ack">Heard <kbd>R</kbd></button>');
}

let lastJolt = 0, lastInstr = 0, shownOutcome = null;
function render(s) {
  const first = !S;
  S = s; got = performance.now();
  if (first) resize();
  const hasCase = Boolean(s.me);
  $("#start-brief").textContent = hasCase ? s.case.brief : "Waiting for the control tower to load a case.";
  $("#start-state").textContent = !hasCase ? "" : (s.state === "ready" ? " The tower starts the drill." : (s.state === "running" ? " The drill is running." : ""));
  if (!hasCase) { seated = false; renderS = null; }
  $("#start").classList.toggle("hidden", seated && hasCase);
  if (hasCase) {
    renderDesk(s);
    renderInstr(s);
    if (changed("radio", s.radio.length ? s.radio[s.radio.length - 1].id : 0)) $("#radio").innerHTML = radioHtml(s.radio, ROLE);
    if (s.jolt && s.jolt.n !== lastJolt) {
      lastJolt = s.jolt.n;
      shake = { until: performance.now() + (s.jolt.strength > 1 ? 2200 : 900), power: s.jolt.strength > 1 ? 1.6 : 1 };
      Sound.thump(s.jolt.strength);
    }
    if (s.instruction && s.instruction.id !== lastInstr) { lastInstr = s.instruction.id; s.instruction.kind === "emergency" ? Sound.alarm() : Sound.chime(); }
    speak(s.radio);
  }
  const modal = $("#modal");
  if (s.outcome && shownOutcome !== s.outcome.title + s.t) {
    shownOutcome = s.outcome.title + s.t;
    modal.innerHTML = debriefHtml(s.outcome, ROLE);
    modal.classList.remove("hidden");
    s.outcome.result === "success" ? Sound.chime() : Sound.alarm();
  } else if (!s.outcome && !modal.classList.contains("hidden")) modal.classList.add("hidden");
}

// ================================================================= inputs
const input = (body) => api("driver/input", body);
const notch = (d) => { if (S && S.me) input({ notch: Math.max(-4, Math.min(4, (S.me.cruise_kmh != null ? 0 : S.me.notch) + d)) }); };
const eb = () => { if (S && S.me) input({ eb: !(S.me.eb && S.me.kmh < 0.5) }); };
const ack = () => {
  const i = S && S.instruction;
  if (!i || i.acked) return;
  if (i.expect === "readback") api("driver/act", { kind: "readback" });
  else api("copi/ack", { role: ROLE });
};
const report = (cat, where) => api("driver/report", { category: cat, where: where || null });

$("#b-power").onclick = () => notch(1);
$("#b-brake").onclick = () => notch(-1);
$("#b-neutral").onclick = () => input({ notch: 0 });
$("#b-cruise").onclick = () => input({ cruise: !(S && S.me && S.me.cruise_kmh != null) });
$("#b-eb").onclick = eb;
$("#b-rec").onclick = () => api("driver/act", { kind: "rec" });
$("#b-inspect").onclick = () => api("driver/act", { kind: "inspect" });
$("#b-clip").onclick = () => api("driver/act", { kind: "clip" });
$("#finding").addEventListener("click", (e) => { if (e.target.id === "b-find") api("driver/act", { kind: "report_finding" }); });
$("#instr").addEventListener("click", (e) => { if (e.target.closest("button")) ack(); });
$("#reports").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) report(b.dataset.cat, b.dataset.where); });
const sendSay = () => { const i = $("#say"); if (i.value.trim()) api("driver/say", { text: i.value }); i.value = ""; };
$("#btn-say").onclick = sendSay;
$("#say").addEventListener("keydown", (e) => { if (e.key === "Enter") sendSay(); });
$("#btn-seat").onclick = () => { seated = true; tuneIn(); $("#start").classList.toggle("hidden", Boolean(S && S.me)); };

document.addEventListener("keydown", (e) => {
  if (typing(e) || e.metaKey || e.ctrlKey || e.altKey || !S || !S.me) return;
  const k = e.key;
  if (k === "ArrowUp" || k === "w") { e.preventDefault(); notch(1); }
  else if (k === "ArrowDown" || k === "s") { e.preventDefault(); notch(-1); }
  else if (k === "n" || k === "0") input({ notch: 0 });
  else if (k === "c") input({ cruise: !(S.me.cruise_kmh != null) });
  else if (k === " ") { e.preventDefault(); if (!e.repeat) eb(); }
  else if (k === "r") ack();
  else if (/^[1-9]$/.test(k) && !e.repeat) { // one key per quick report, however many there are
    const c = S.categories[Number(k) - 1];
    if (c) report(c.id, c.options ? c.options[0].id : null);
  }
});

connect(ROLE, render);
requestAnimationFrame(frame);
