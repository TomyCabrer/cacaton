"use strict";

const $ = (id) => document.getElementById(id);
let S = null; // latest state snapshot from the server
let SC = null; // static scenario info
const ui = { rejecting: null, reasons: {}, memo: {} };

// ---------- helpers ---------------------------------------------------
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tOf = (iso) => (iso ? iso.slice(11, 19) : "--:--:--");
const dOf = (iso) =>
  iso ? new Date(iso + "Z").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "";
const secs = (a, b) => (new Date(b + "Z") - new Date(a + "Z")) / 1000;
function dur(s) {
  s = Math.max(0, Math.round(s));
  if (s >= 86400) return `${Math.floor(s / 86400)} d ${Math.floor((s % 86400) / 3600)} h`;
  if (s >= 3600) return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} m`;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
const chips = (ids) => (ids || []).map((i) => `<span class="chip" data-ev="${esc(i)}">${esc(i)}</span>`).join("");
const changed = (key, data) => {
  const s = JSON.stringify(data);
  if (ui.memo[key] === s) return false;
  ui.memo[key] = s;
  return true;
};
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
const control = (action, extra = {}) => post("/api/control", { action, ...extra }).catch(console.error);

// ---------- boot ------------------------------------------------------
async function boot() {
  SC = await (await fetch("/api/scenario")).json();
  $("acts").innerHTML = SC.acts
    .map((a, i) => `<button data-act="${a.id}">${esc(a.title.split("·")[1] || a.title)}<small>Act ${i + 1}</small></button>`)
    .join("");
  const es = new EventSource("/api/stream");
  es.onmessage = (m) => {
    S = JSON.parse(m.data);
    render();
  };
  es.onerror = () => {
    $("copilot-chip").textContent = "disconnected — retrying…";
  };
}

// ---------- render ----------------------------------------------------
function render() {
  renderTop();
  renderBanner();
  renderLine();
  if (changed("briefing", [S.briefing, S.copilot.busy])) renderBriefing();
  if (changed("qa", S.qa)) renderQA();
  renderMemory();
  if (changed("decisions", [S.memory.recommendations, ui.rejecting, ui.showAll])) renderDecisions();
  if (changed("feed", [S.events.length, $("show-notes").checked])) renderFeed();
  if (changed("driver", S.driver)) renderDriver();
  if (changed("audit", S.memory.log.length)) renderAudit();
}

function renderTop() {
  $("clock-date").textContent = dOf(S.sim_time);
  $("clock-time").textContent = tOf(S.sim_time);
  $("btn-play").textContent = S.playing ? "⏸" : "▶";
  $("btn-play").disabled = S.finished;
  $("speed").value = String(S.speed);
  $("sw-integrations").checked = S.integrations;
  $("sw-autopause").checked = S.auto_pause;
  document.querySelectorAll("#acts button").forEach((b) => b.classList.toggle("active", b.dataset.act === S.act));
  const c = S.copilot;
  const chip = $("copilot-chip");
  chip.className = `copilot-chip ${c.mode}${c.busy ? " busy" : ""}`;
  const label = {
    live: `Claude live · ${c.model} · effort ${c.effort}`,
    recorded: "Claude · recorded outputs (offline demo)",
    offline: "Rules only · no Claude key",
  }[c.mode];
  chip.innerHTML = `<span class="dot"></span>${esc(label)}${c.busy ? " · thinking…" : ""}`;
  const note = $("pause-note");
  note.classList.toggle("hidden", S.playing || !S.paused_reason);
  note.textContent = S.paused_reason || "";
}

function renderBanner() {
  const b = $("banner");
  if (!S.banner) return b.classList.add("hidden");
  b.className = `banner ${S.banner.kind}`;
  b.innerHTML = `${esc(S.banner.text)} <span class="hint">since ${tOf(S.banner.since)}</span>`;
}

// ---------- line schematic -------------------------------------------
const TRAIN_COLORS = { "IRYO 6189": "#b06cff", "ALVIA 2384": "#5ea0ff", "AVLO 2181": "#3ecf8e" };
const TRAIN_LEN_KM = { "IRYO 6189": 0.2, "ALVIA 2384": 0.107, "AVLO 2181": 0.2 };

function renderLine() {
  drawLine($("line-overview"), 300, 345, 1000, false);
  drawLine($("line-detail"), 317.8, 319.6, 600, true);
}

function drawLine(svg, pk0, pk1, W, detail) {
  const x = (pk) => 20 + ((pk - pk0) / (pk1 - pk0)) * (W - 40);
  const y = { 1: 50, 2: 88 };
  const items = S.memory.items;
  const has = (kind, key) => items[kind].find((i) => i.key === key || i.key.startsWith(key));
  const out = [];

  // power section band
  const powerDown = has("fact", "power:");
  for (const p of SC.infrastructure.power_sections) {
    const a = Math.max(x(p.pk_from), 20), b = Math.min(x(p.pk_to), W - 20);
    if (b > a) {
      out.push(`<rect x="${a}" y="16" width="${b - a}" height="6" rx="3" fill="${powerDown ? "#ff4d4f" : "#2a3242"}"/>`);
      out.push(`<text class="svg-label" x="${a + 4}" y="12">catenary · ${esc(p.id)}${powerDown ? " · VOLTAGE DROP" : ""}</text>`);
    }
  }
  // tracks
  for (const tk of [1, 2]) {
    out.push(`<line class="svg-track" x1="20" x2="${W - 20}" y1="${y[tk]}" y2="${y[tk]}"/>`);
    out.push(`<text class="svg-label" x="22" y="${y[tk] - 6}">vía ${tk} ${tk === 1 ? "← Madrid" : "→ Córdoba"}</text>`);
  }
  // suspect zone (track circuit) coloured by defect hypothesis confidence
  const defect = items.hypothesis.find((i) => i.key.startsWith("defect:") && i.status === "open");
  for (const tc of SC.infrastructure.track_circuits) {
    const col = defect ? { high: "#ff4d4f", medium: "#f5a524", low: "#5ea0ff" }[defect.confidence] : "#2a3242";
    const a = x(tc.pk_from), b = x(tc.pk_to);
    if (b > 20 && a < W - 20) {
      out.push(`<rect x="${a}" y="${y[tc.track] - 5}" width="${Math.max(b - a, 3)}" height="10" rx="2" fill="${col}" opacity="${defect ? 0.45 : 0.6}"/>`);
      if (detail) out.push(`<text class="svg-label" x="${a}" y="${y[tc.track] + 20}">${esc(tc.id)}</text>`);
    }
  }
  // anomaly markers from fed precursor events
  for (const e of S.events) {
    if (!e.fed || !e.anomaly || e.location.track == null) continue;
    const ex = x(e.location.pk);
    if (ex < 20 || ex > W - 20) continue;
    out.push(`<circle cx="${ex}" cy="${y[e.location.track] - 14}" r="${detail ? 5 : 3}" fill="#f5a524"><title>${esc(e.id + " " + e.text)}</title></circle>`);
  }
  // fouled adjacent track
  if (has("hypothesis", "fouled:adjacent")) {
    const fx = x(318.62);
    out.push(`<rect x="${fx - (detail ? 25 : 4)}" y="${y[1]}" width="${detail ? 50 : 8}" height="${y[2] - y[1]}" fill="#ff4d4f" opacity="0.35"/>`);
    if (detail) out.push(`<text class="svg-label" x="${fx + 28}" y="${(y[1] + y[2]) / 2 + 3}" fill="#ff8a8b">fouled</text>`);
  }
  // signals
  for (const s of SC.infrastructure.signals) {
    const red = has("fact", `signal:${s.id}`);
    const sx = x(s.pk);
    if (sx < 20 || sx > W - 20) continue;
    out.push(`<circle cx="${sx}" cy="${y[s.track] + 12}" r="${detail ? 5 : 3.5}" fill="${red ? "#ff4d4f" : "#3ecf8e"}"/>`);
    if (detail) out.push(`<text class="svg-label" x="${sx + 8}" y="${y[s.track] + 16}">${esc(s.id)}</text>`);
  }
  // incident ring
  if (S.banner && S.banner.kind === "incident") {
    const ix = x(318.6);
    out.push(`<circle class="svg-ring" cx="${ix}" cy="${(y[1] + y[2]) / 2}" r="6"/>`);
  }
  // trains
  for (const tr of S.trains) {
    const hx = x(tr.pk);
    if (hx < 0 || hx > W) continue;
    const dir = tr.track === 1 ? -1 : 1;
    const len = detail ? Math.max(14, (TRAIN_LEN_KM[tr.id] / (pk1 - pk0)) * (W - 40)) : 16;
    const tx = dir === 1 ? hx - len : hx;
    const col = TRAIN_COLORS[tr.id] || "#ccc";
    const stopped = tr.status === "stopped";
    const ty = y[tr.track] - 5;
    const label = `${tr.id}${tr.speed_kmh ? ` · ${tr.speed_kmh} km/h` : stopped ? " · stopped" : ""}`;
    const ly = tr.track === 1 ? ty - 8 : ty + 26;
    out.push(
      `<g class="svg-train"><rect x="${tx}" y="${ty}" width="${len}" height="10" fill="${stopped ? "none" : col}" stroke="${col}" stroke-width="2"/>` +
        `<text x="${Math.min(Math.max(tx, 22), W - 150)}" y="${ly}">${esc(label)}</text></g>`
    );
  }
  // places
  if (!detail) {
    for (const p of SC.infrastructure.places) {
      const px = x(p.pk);
      out.push(`<line x1="${px}" x2="${px}" y1="100" y2="106" stroke="#3a4456"/>`);
      out.push(`<text class="svg-place" x="${Math.min(px - 10, W - 110)}" y="122">${esc(p.name)} <tspan class="svg-label">PK ${p.pk}</tspan></text>`);
    }
  } else {
    for (let pk = Math.ceil(pk0 * 5) / 5; pk <= pk1; pk += 0.2) {
      const px = x(pk);
      out.push(`<text class="svg-label" x="${px - 12}" y="122">${pk.toFixed(1)}</text>`);
    }
  }
  svg.innerHTML = out.join("");
}

// ---------- briefing --------------------------------------------------
function renderBriefing() {
  const b = S.briefing;
  const meta = $("briefing-meta");
  if (!b) {
    $("briefing").innerHTML = `<div class="empty">No briefing yet.</div>`;
    meta.textContent = "";
    return;
  }
  const m = b.meta || {};
  const src = { live: "Claude", recorded: "Claude (recorded)", offline: "rules only" }[m.mode] || m.mode;
  meta.textContent =
    `${src} · based on ${tOf(m.based_on)}` + (m.latency_ms ? ` · ${(m.latency_ms / 1000).toFixed(1)} s` : "") + (S.copilot.busy ? " · updating…" : "");
  const hyps = (b.hypotheses || [])
    .map((h) => `<div class="hyp">${esc(h.statement)}<span class="conf ${h.confidence}">${h.confidence}</span><div>${chips(h.evidence_ids)}</div></div>`)
    .join("");
  const unk = (b.unknowns || []).map((u) => `<li>${esc(u)}</li>`).join("");
  $("briefing").innerHTML = `
    <div class="headline">${esc(b.headline)}</div>
    <div class="situation">${esc(b.situation)}</div>
    ${unk ? `<div class="subhead">Not known yet</div><ul class="unknowns">${unk}</ul>` : ""}
    ${hyps ? `<div class="subhead">Hypotheses</div>${hyps}` : ""}
    ${m.error ? `<div class="briefing-error">Claude unavailable (${esc(m.error)}). Showing the rule-based briefing.</div>` : ""}`;
}

function renderQA() {
  $("qa").innerHTML = S.qa
    .slice()
    .reverse()
    .map(
      (q) => `<div class="qa-item"><div class="qa-q">${tOf(q.asked_at)} · ${esc(q.q)}</div>
      <div>${q.pending ? "<span class='empty'>thinking…</span>" : esc(q.answer)}</div>
      <div>${chips(q.evidence_ids)}${q.confidence && !q.pending ? `<span class="conf ${q.confidence}">${q.confidence}</span>` : ""}</div></div>`
    )
    .join("");
}

// ---------- memory ----------------------------------------------------
const GROUPS = [
  ["contradiction", "Contradictions"],
  ["open_loop", "Open loops"],
  ["hypothesis", "Hypotheses"],
  ["fact", "Facts"],
  ["watch", "Watching"],
];

function renderMemory() {
  const items = S.memory.items;
  const openCount = (k) => items[k].filter((i) => i.status === "open").length;
  $("memory-count").textContent = `${openCount("open_loop")} open loops · ${openCount("contradiction")} contradictions`;
  const html = GROUPS.map(([kind, title]) => {
    const list = items[kind].slice().sort((a, b) => (a.status === b.status ? (a.updated < b.updated ? 1 : -1) : a.status === "open" ? -1 : 1));
    if (!list.length) return "";
    const rows = list
      .map((i) => {
        const open = i.status === "open";
        const timer = open ? `open ${dur(secs(i.created, S.sim_time))}` : `closed after ${dur(secs(i.created, i.resolved_at))}`;
        const showTimer = kind === "open_loop" || kind === "contradiction" || (!open && kind !== "fact");
        return `<div class="mem-item ${kind} ${open ? "" : "resolved"}">
          <div>${esc(i.text)}${i.confidence ? `<span class="conf ${i.confidence}">${i.confidence}</span>` : ""}</div>
          ${i.detail && kind !== "fact" ? `<div class="detail">${esc(i.detail)}</div>` : ""}
          ${!open && i.resolution ? `<div class="detail">→ ${esc(i.resolution)}</div>` : ""}
          <div class="meta"><div>${chips(i.evidence)}</div>${showTimer ? `<span class="timer">${timer}</span>` : ""}</div>
        </div>`;
      })
      .join("");
    return `<div class="mem-group"><div class="mem-title"><span>${title}</span><span>${list.filter((i) => i.status === "open").length}</span></div>${rows}</div>`;
  }).join("");
  if (changed("memory", html)) $("memory").innerHTML = html || `<div class="empty">Memory is empty. Nothing has been fed yet.</div>`;
}

// ---------- decisions -------------------------------------------------
const URG = { critical: 0, high: 1, medium: 2 };

function renderDecisions() {
  const active = document.activeElement;
  const refocus = active && active.dataset && active.dataset.reason;
  const recs = S.memory.recommendations;
  const pending = recs.filter((r) => r.status === "pending").sort((a, b) => URG[a.urgency] - URG[b.urgency] || (a.created < b.created ? 1 : -1));
  const decided = recs.filter((r) => r.status !== "pending").reverse();
  $("decision-count").textContent = `${pending.length} pending · ${decided.length} decided`;
  const cards = pending
    .map((r, idx) => {
      const rejecting = ui.rejecting === r.id;
      if (idx >= 3 && !rejecting && !ui.showAll) {
        return `<div class="rec compact ${r.urgency}"><div class="rec-top"><span><span class="urg ${r.urgency}">${r.urgency}</span>
          ${esc(r.title)}</span><span class="rec-actions"><button class="approve" data-do="approved" data-rec="${r.id}">Approve</button>
          <button data-do="expand" data-rec="${r.id}">…</button></span></div></div>`;
      }
      return `<div class="rec ${r.urgency}">
        <div class="rec-top"><span><span class="urg ${r.urgency}">${r.urgency}</span> ${esc(r.action.replace(/_/g, " "))}
          ${r.escalated_from ? ` · escalated from ${r.escalated_from}` : ""}</span>
          <span><span class="badge ${r.source}">${r.source === "claude" ? "Claude" : "rules"}</span> ${r.id} · ${tOf(r.created)}</span></div>
        <div class="rec-title">${esc(r.title)}</div>
        <div class="rec-why">${esc(r.rationale)}</div>
        <div class="rec-cost">If wrong: ${esc(r.cost_if_wrong)}</div>
        <div>${chips(r.evidence)}</div>
        <div class="rec-actions">
          ${
            rejecting
              ? `<div class="reason"><input data-reason="${r.id}" placeholder="Why not? (logged for the investigation)" value="${esc(ui.reasons[r.id] || "")}">
                 <button class="reject" data-do="rejected" data-rec="${r.id}">Confirm reject</button>
                 <button data-do="cancel" data-rec="${r.id}">Cancel</button></div>`
              : `<button class="approve" data-do="approved" data-rec="${r.id}">Approve</button>
                 <button class="reject" data-do="reject-start" data-rec="${r.id}">Reject…</button>
                 <button data-do="deferred" data-rec="${r.id}">Defer</button>`
          }
        </div>
      </div>`;
    })
    .join("");
  const done = decided
    .map(
      (r) => `<div class="decided-item"><span class="st ${r.status}">${r.status}</span>
      <div><div>${esc(r.title)}</div><div class="why">${r.id} · ${tOf(r.decided_at)}${r.reason ? ` · “${esc(r.reason)}”` : ""}</div></div></div>`
    )
    .join("");
  $("decisions").innerHTML =
    (cards || `<div class="empty">No recommendation waiting. Copi stays quiet until the evidence justifies interrupting you.</div>`) +
    (done ? `<div class="decided"><div class="subhead">Decided by the operator</div>${done}</div>` : "");
  if (refocus) {
    const el = document.querySelector(`[data-reason="${refocus}"]`);
    if (el) {
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length);
    }
  }
}

$("decisions").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-do]");
  if (!btn) return;
  const id = btn.dataset.rec, act = btn.dataset.do;
  if (act === "reject-start") {
    ui.rejecting = id;
    renderDecisions();
    document.querySelector(`[data-reason="${id}"]`)?.focus();
    return;
  }
  if (act === "cancel") {
    ui.rejecting = null;
    return renderDecisions();
  }
  if (act === "expand") {
    ui.showAll = true;
    return renderDecisions();
  }
  if (act === "rejected" && !(ui.reasons[id] || "").trim()) {
    document.querySelector(`[data-reason="${id}"]`)?.focus();
    return;
  }
  ui.rejecting = null;
  try {
    await post("/api/decide", { rec_id: id, decision: act, reason: ui.reasons[id] || null });
  } catch (err) {
    console.error(err);
  }
});
$("decisions").addEventListener("input", (e) => {
  if (e.target.dataset.reason) ui.reasons[e.target.dataset.reason] = e.target.value;
});
$("decisions").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.dataset.reason) document.querySelector(`button[data-do="rejected"][data-rec="${e.target.dataset.reason}"]`)?.click();
});

// ---------- feed ------------------------------------------------------
const FEED_LABEL = { ctc: "CTC today", proposed: "proposed integration", hindsight: "hindsight · not fed" };

function renderFeed() {
  const notes = $("show-notes").checked;
  $("feed").innerHTML =
    S.events
      .slice()
      .reverse()
      .map(
        (e) => `<div class="ev ${e.fed ? "" : "unfed"}" id="ev-${esc(e.id)}">
        <div class="ev-top"><span class="ev-id">${esc(e.id)}</span>
          <span class="ev-t">${e.t.slice(0, 10) !== "2026-01-18" ? esc(dOf(e.t)) + " " : ""}${tOf(e.t)}</span>
          <span>${esc(e.channel)}</span>
          <span class="badge ${e.provenance}">${e.provenance}</span>
          <span class="badge ${e.feed}">${FEED_LABEL[e.feed]}</span></div>
        <div class="ev-text">${esc(e.text)}</div>
        ${e.original ? `<div class="ev-orig">«${esc(e.original)}»</div>` : ""}
        ${notes && (e.note || e.time_note) ? `<div class="ev-note">${esc([e.time_note, e.note].filter(Boolean).join(" "))}</div>` : ""}
      </div>`
      )
      .join("") || `<div class="empty">Nothing received yet.</div>`;
}
$("show-notes").addEventListener("change", () => S && renderFeed());

// ---------- driver ----------------------------------------------------
function renderDriver() {
  const d = S.driver;
  if (!d) {
    $("driver").innerHTML = `<div class="quiet">No advisory.<br>The cab tablet stays silent unless it matters.</div>`;
    return;
  }
  $("driver").innerHTML = `
    <div class="train">${esc(d.train)} · ${tOf(d.t)} · <span class="badge ${d.source}">${d.source === "claude" ? "Claude" : "rules"}</span></div>
    ${d.headline ? `<div class="adv-head">${esc(d.headline)}</div>` : ""}
    <div>${esc(d.text)}</div>
    ${d.say ? `<div class="say">${esc(d.say)}</div>` : ""}
    <div>${chips(d.evidence)}</div>`;
}

// ---------- audit -----------------------------------------------------
function renderAudit() {
  $("audit").innerHTML = S.memory.log
    .slice(-120)
    .reverse()
    .map((l) => {
      const cls = l.what.startsWith("human.") ? "human" : l.source === "claude" ? "claude" : l.what.startsWith("rec.") ? "rec" : "";
      return `<div class="log-row ${cls}"><span>${tOf(l.sim)}</span><span class="w">${esc(l.what)}</span><span>${esc(l.text)}</span></div>`;
    })
    .join("");
}

// ---------- modals ----------------------------------------------------
function openModal(html) {
  $("modal-body").innerHTML = html;
  $("modal").classList.remove("hidden");
}
$("modal-close").onclick = () => $("modal").classList.add("hidden");
$("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") $("modal").classList.add("hidden");
});

function realityHTML() {
  const rows = S.comparison
    .map((r) => {
      const mem = r.memoria
        ? `<span class="t">${r.memoria.slice(0, 10) !== "2026-01-18" ? dOf(r.memoria) + " " : ""}${tOf(r.memoria)}</span><br><span class="hint">${
            r.vs_collision_min < 0 ? `${dur(-r.vs_collision_min * 60)} before the collision` : `${dur(r.vs_collision_min * 60)} after the collision`
          }</span>`
        : `<span class="hint">not reached in this run</span>`;
      const real = r.real ? `<span class="t">${tOf(r.real)}</span><br><span class="hint">${esc(r.real_text)}</span>` : `<span class="hint">${esc(r.real_text)}</span>`;
      const gain = r.gain_min != null ? `<span class="gain">${r.gain_min} min earlier</span>` : r.memoria && !r.real ? `<span class="gain">only Copi</span>` : "";
      return `<tr><td>${esc(r.label)}</td><td>${mem}</td><td>${real}</td><td>${gain}</td></tr>`;
    })
    .join("");
  const decided = S.memory.recommendations.filter((r) => r.status !== "pending");
  return `<h3>Reality check · ${S.integrations ? "with proposed integrations" : "CTC data only"}</h3>
    <p>When Copi raised each flag in this replay, against when the real control room knew.</p>
    <table class="cmp"><tr><th>Moment</th><th>Copi (this replay)</th><th>Reality</th><th></th></tr>${rows}</table>
    <p>Your decisions in this run: ${decided.filter((r) => r.status === "approved").length} approved,
       ${decided.filter((r) => r.status === "rejected").length} rejected, ${decided.filter((r) => r.status === "deferred").length} deferred.
       The replay follows the real timeline whatever you decide; your decisions are logged against it.</p>
    <div class="caveat">What this does not show. The collision came about 8 seconds after the derailment: no operator and no advisory
      system could have stopped the Alvia in that window; that is the job of automatic protection, and signal S613 did drop.
      Autopsies found 45 of the 46 victims died on impact, so a faster response mainly helps the injured.
      The lives are in Act 1: the defect signals existed (or could have been captured) hours before. Act 1 only works with the
      proposed integrations, because today those signals live in separate systems, or are never recorded.
      Timings here come from a reconstruction with simulated train-describer data; they are an argument, not a finding.</div>`;
}

function aboutHTML() {
  const src = SC.sources.map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a></li>`).join("");
  return `<h3>${esc(SC.title)}</h3>
    <p>${esc(SC.disclaimer)}</p>
    <div class="subhead">Badges</div>
    <p><span class="badge real">real</span> from the public timeline ·
       <span class="badge simulated">simulated</span> plausible control-room data, not published ·
       <span class="badge counterfactual">counterfactual</span> something that did not happen but could have been captured<br>
       <span class="badge ctc">CTC today</span> a control room receives it now ·
       <span class="badge proposed">proposed integration</span> needs a new data link ·
       <span class="badge hindsight">hindsight</span> known only after the investigation; never fed to Copi</p>
    <div class="subhead">Sources</div><ul class="sources">${src}</ul>`;
}

function handoverHTML(h) {
  const list = (title, xs) => (xs && xs.length ? `<div class="subhead">${title}</div><ul class="unknowns">${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  return `<h3>Shift handover · ${tOf(h.at)} <span class="badge ${h.mode === "offline" ? "rules" : "claude"}">${h.mode}</span></h3>
    <p>${esc(h.summary)}</p>${list("Unresolved", h.unresolved)}${list("Decisions pending", h.decisions_pending)}${list("Watch next", h.watch_next)}`;
}

$("btn-reality").onclick = () => openModal(realityHTML());
$("btn-about").onclick = () => openModal(aboutHTML());
$("btn-handover").onclick = async () => {
  openModal(`<h3>Shift handover</h3><p class="empty">Writing handover…</p>`);
  try {
    openModal(handoverHTML(await post("/api/handover")));
  } catch (err) {
    openModal(`<h3>Shift handover</h3><p>Failed: ${esc(err.message)}</p>`);
  }
};

// ---------- evidence chips -------------------------------------------
document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip[data-ev]");
  if (!chip) return;
  const el = $(`ev-${chip.dataset.ev}`);
  if (!el) return;
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.classList.remove("flash");
  void el.offsetWidth;
  el.classList.add("flash");
});

// ---------- controls --------------------------------------------------
$("btn-play").onclick = () => control(S && S.playing ? "pause" : "play");
$("btn-step").onclick = () => control("step");
$("btn-reset").onclick = () => {
  ui.rejecting = null;
  ui.reasons = {};
  control("reset");
};
$("speed").onchange = (e) => control("speed", { speed: parseFloat(e.target.value) });
$("sw-integrations").onchange = (e) => control("integrations", { value: e.target.checked });
$("sw-autopause").onchange = (e) => control("auto_pause", { value: e.target.checked });
$("acts").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-act]");
  if (b) control("jump", { act: b.dataset.act });
});
$("ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("ask-input").value.trim();
  if (!q) return;
  $("ask-input").value = "";
  try {
    await post("/api/ask", { question: q });
  } catch (err) {
    console.error(err);
  }
});
document.addEventListener("keydown", (e) => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  if (e.code === "Space") {
    e.preventDefault();
    $("btn-play").click();
  } else if (e.key === "n") {
    $("btn-step").click();
  } else if (e.key === "Escape") {
    $("modal").classList.add("hidden");
  }
});

boot();
