/* AquaGuard AI dashboard — vanilla JS, no build step. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const api = {
  get: (url) => fetch(url).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
  post: (url, body) => fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
};

const S = {
  state: null,
  selectedZone: null,
  knownAlerts: new Set(),
  knownTickets: new Set(),
  firstLoad: true,
  demoTimers: [],
};

/* ---------------- helpers ---------------- */
const fmtL = (n) => (n >= 10000 ? Math.round(n).toLocaleString("en-IN") : n.toLocaleString("en-IN", { maximumFractionDigits: 1 }));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sevDot = (sev) => (sev === "CRITICAL" || sev === "HIGH" ? "dot-red" : sev === "MEDIUM" ? "dot-amber" : "dot-green");
const sevColor = (sev) => (sev === "CRITICAL" || sev === "HIGH" ? "var(--red)" : sev === "MEDIUM" ? "var(--amber)" : "var(--green)");
const timeHM = (iso) => new Date(iso).toLocaleTimeString("en-IN", { hour12: false });

function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .4s"; }, 4600);
  setTimeout(() => el.remove(), 5100);
}

/* ---------------- polling ---------------- */
async function poll() {
  try {
    S.state = await api.get("/api/state");
    document.querySelector(".live-badge").style.opacity = 1;
    render();
  } catch {
    document.querySelector(".live-badge").style.opacity = 0.35;
  }
}

/* ---------------- render ---------------- */
function render() {
  const st = S.state;
  if (!st) return;
  $("#clock").textContent = new Date().toLocaleTimeString("en-IN", { hour12: false });
  $("#fleet-meta").textContent = `${st.facility.devices} devices · ${st.facility.zones} zones · sim ${st.facility.sim_minutes_elapsed} min`;
  renderKpis(st.kpis);
  renderZones(st.zones);
  renderAlerts(st.alerts);
  renderTickets(st.tickets);
  renderRisk(st.risk_devices);
  renderSustain(st.kpis);
  drawChart(st.timeseries);
  notifyNew(st);
  S.firstLoad = false;
}

function renderKpis(k) {
  const cards = [
    ["Water consumption", `${fmtL(k.water_consumption_liters)}`, "L today (tracked)", "var(--blue)"],
    ["Active alerts", `${k.active_alerts}`, `${k.critical_alerts} high/critical`, k.active_alerts ? "var(--red)" : "var(--green)", k.active_alerts ? "alerting" : ""],
    ["Devices at risk", `${k.devices_at_risk}`, `avg health ${k.avg_device_health}/100`, k.devices_at_risk ? "var(--amber)" : "var(--green)"],
    ["Water saved", `${fmtL(k.water_saved_month_liters)}`, "L / month avoided", "var(--green)"],
    ["Current wastage", `${fmtL(k.current_wastage_liters)}`, "L (open incidents)", k.current_wastage_liters > 0 ? "var(--red)" : "var(--green)"],
    ["Tickets", `${k.open_tickets}`, `${k.incidents_resolved} resolved · MTTR ${k.mttr_minutes}m`, "var(--cyan)"],
  ];
  $("#kpi-row").innerHTML = cards.map(([label, val, sub, accent, cls]) => `
    <div class="kpi ${cls || ""}" style="--accent:${accent}">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${val}</div>
      <div class="kpi-sub">${sub}</div>
    </div>`).join("");
}

function renderZones(zones) {
  const groups = {};
  zones.forEach((z) => (groups[z.terminal] ||= []).push(z));
  let html = "";
  for (const [terminal, zs] of Object.entries(groups)) {
    html += `<div class="terminal-title">${esc(terminal)}</div><div class="zone-grid">`;
    for (const z of zs) {
      const pct = Math.min(100, Math.round((z.usage_since_cleaning / Math.max(1, z.adaptive_threshold)) * 100));
      const cls = z.status === "critical" ? "st-critical" : z.status === "warning" ? "st-warning" : "";
      html += `
      <div class="zone-card st-${z.status} ${S.selectedZone === z.zone_id ? "open sel" : ""}" data-zone="${z.zone_id}">
        <div class="zone-name">${esc(z.name)}${z.cleaning_required ? ' <span class="badge sev-MEDIUM">clean</span>' : ""}</div>
        <div class="zone-meta"><span>👥 <b>${z.occupancy}</b> inside</span><span>${z.devices.length} devices</span></div>
        <div class="zone-meta"><span>hygiene <b>${Math.round(z.usage_since_cleaning)}</b>/${z.adaptive_threshold}</span><span>cleaned ${z.last_cleaned_min_ago}m ago</span></div>
        <div class="usage-bar"><i class="${pct >= 100 ? "over" : ""}" style="width:${pct}%"></i></div>
        <div class="zone-devices">${z.devices.map(devRow).join("")}
          <div style="margin-top:8px"><button class="btn btn-mini" data-clean="${z.zone_id}">🧹 Mark cleaned</button></div>
        </div>
      </div>`;
    }
    html += "</div>";
  }
  $("#zones").innerHTML = html;
  $("#zones").querySelectorAll(".zone-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest("[data-clean]") || e.target.closest(".dev-row")) return;
      const id = card.dataset.zone;
      S.selectedZone = S.selectedZone === id ? null : id;
      renderZones(S.state.zones);
    });
  });
  $("#zones").querySelectorAll("[data-clean]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api.post(`/zones/${btn.dataset.clean}/cleaned`);
      toast(`🧹 Cleaning recorded for zone — hygiene counter reset`, "good");
      poll();
    }));
  $("#zones").querySelectorAll(".dev-row[data-dev]").forEach((row) =>
    row.addEventListener("click", () => openDeviceModal(row.dataset.dev)));
}

function devRow(d) {
  const dot = d.status === "critical" ? "dot-red" : d.status === "warning" ? "dot-amber" : d.status === "offline" ? "dot-blue" : "dot-green";
  const hcls = d.health_score < 45 ? "bad" : d.health_score < 75 ? "warn" : "";
  return `<div class="dev-row" data-dev="${d.device_id}">
    <i class="dot ${dot}"></i>
    <span class="dev-id">${d.device_id}</span>
    ${d.scenario ? '<span class="badge sev-CRITICAL">SIM</span>' : ""}
    <span class="health-mini ${hcls}">${d.health_score}</span>
    <span class="dev-type">${esc(d.type)} · ${d.flow_lpm.toFixed(1)} L/m</span>
  </div>`;
}

function renderAlerts(alerts) {
  $("#alert-count").textContent = `${alerts.filter((a) => a.status === "OPEN").length} open`;
  $("#alerts-list").innerHTML = alerts.map((a) => `
    <div class="alert-card" data-alert="${a.id}" style="--sev:${sevColor(a.severity)};${a.status === "RESOLVED" ? "opacity:.55" : ""}">
      <div class="alert-top">
        <i class="dot ${a.status === "OPEN" ? sevDot(a.severity) : "dot-green"}"></i>
        <span class="alert-device">${a.device_id}</span>
        <span class="badge sev-${a.severity}">${a.severity}</span>
        <span class="badge prio">${a.priority}</span>
        ${a.status === "RESOLVED" ? '<span class="resolved-tag">✓ RESOLVED</span>' : `<span class="alert-zone">${esc(a.zone)} · ${timeHM(a.created_at)}</span>`}
      </div>
      <div class="alert-issue">${esc(a.issue)}</div>
      ${a.estimated_daily_loss_liters > 0 ? `<div class="alert-loss">〜 ${fmtL(a.estimated_daily_loss_liters)} L/day · ${fmtL(a.estimated_monthly_loss_liters)} L/month if unresolved</div>` : ""}
      <div class="ai-line">${esc(a.diagnosis)}</div>
    </div>`).join("");
  $("#alerts-list").querySelectorAll(".alert-card").forEach((el) =>
    el.addEventListener("click", () => openAlertModal(el.dataset.alert)));
}

function renderTickets(tickets) {
  const open = tickets.filter((t) => t.status === "OPEN");
  $("#ticket-count").textContent = `${open.length} open`;
  $("#tickets-list").innerHTML = tickets.map((t) => `
    <div class="ticket">
      <div class="ticket-top">
        <i class="dot ${t.status === "OPEN" ? sevDot(t.severity) : "dot-green"}"></i>
        <span class="ticket-id">${t.ticket_id}</span>
        <span class="badge sev-${t.severity}">${t.severity}</span>
        <span class="badge prio">${t.priority}</span>
        ${t.status === "RESOLVED" ? '<span class="resolved-tag">✓ done</span>' : `<span class="ticket-cat">${esc(t.category)}</span>`}
      </div>
      <div class="ticket-issue"><b>${esc(t.asset)}</b> · ${esc(t.location)} — ${esc(t.issue)}</div>
      <div class="ticket-act">${esc(t.action)}</div>
      ${t.estimated_water_loss_daily_liters > 0 ? `<div class="alert-loss">〜 ${fmtL(t.estimated_water_loss_daily_liters)} L/day at risk</div>` : ""}
      ${t.status === "OPEN" ? `<div class="ticket-foot"><button class="btn btn-mini btn-primary" data-resolve-ticket="${t.ticket_id}">✓ Resolve &amp; verify</button></div>` : ""}
    </div>`).join("");
  $("#tickets-list").querySelectorAll("[data-resolve-ticket]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      const res = await api.post(`/tickets/${btn.dataset.resolveTicket}/resolve`);
      toast(`✅ Ticket resolved · ${fmtL(res.saved_month_liters)} L/month now in the sustainability ledger`, "good");
      poll();
    }));
}

function renderRisk(devices) {
  const risky = devices.filter((d) => d.risk !== "LOW");
  $("#risk-list").innerHTML = risky.length === 0
    ? '<div class="muted" style="padding:8px 2px">All devices LOW risk — no degradation patterns detected.</div>'
    : risky.map((d) => `
    <div class="risk-row" data-dev="${d.device_id}">
      <div class="risk-top">
        <i class="dot ${d.risk === "HIGH" ? "dot-red" : "dot-amber"}"></i>
        <span class="dev-id">${d.device_id}</span>
        <span class="badge ${d.risk === "HIGH" ? "sev-HIGH" : "sev-MEDIUM"}">${d.risk} RISK</span>
        <span class="health-mini ${d.health_score < 45 ? "bad" : "warn"}">health ${d.health_score}/100</span>
        <span class="dev-type">${esc(d.type)}</span>
      </div>
      <div class="risk-bars">
        ${rbar("Anomaly freq", d.anomaly_frequency / 30)}
        ${rbar("Flow variance", d.flow_variance_pct / 100)}
        ${rbar("Flush irregular", d.flush_irregularity / 15)}
        ${rbar("Sensor errors", d.sensor_errors / 12)}
      </div>
      <div class="risk-proj">Failure probability (7d): <b>${Math.round((d.failure_probability_7d || 0) * 100)}%</b> · variance +${(d.flow_variance_pct || 0).toFixed(0)}% · ${esc(d.zone)}</div>
    </div>`).join("");
  $("#risk-list").querySelectorAll(".risk-row").forEach((el) =>
    el.addEventListener("click", () => openDeviceModal(el.dataset.dev)));
}

const rbar = (label, frac) => {
  const pct = Math.max(4, Math.min(100, Math.round((frac || 0) * 100)));
  const color = pct > 66 ? "var(--red)" : pct > 33 ? "var(--amber)" : "var(--green)";
  return `<div class="rbar">${label}<div class="track"><i style="width:${pct}%;background:${color}"></i></div></div>`;
};

function renderSustain(k) {
  const household = k.water_saved_month_liters / 150;
  $("#sustainability").innerHTML = `
    <div class="sustain-big">${fmtL(k.water_saved_month_liters)} <small>L / month loss avoided</small></div>
    <div class="sustain-row"><span>Equivalent household-days (150 L/day)</span><b>~${fmtL(household)}</b></div>
    <div class="sustain-row"><span>Incidents resolved</span><b>${k.incidents_resolved}</b></div>
    <div class="sustain-row"><span>Mean time to resolve</span><b>${k.mttr_minutes} min</b></div>
    <div class="sustain-row"><span>Average device health</span><b>${k.avg_device_health}/100</b></div>
    <div class="sustain-note">Savings are computed from verified resolutions: each resolved water-loss incident adds its
    projected monthly loss (daily rate × 30) to the ledger. Baseline = flow that would have continued without intervention.</div>`;
}

/* ---------------- chart ---------------- */
function drawChart(points) {
  const canvas = $("#flow-chart");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 600;
  const h = 150;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.height = h + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const data = points.slice(-90);
  const pad = { l: 34, r: 8, t: 10, b: 18 };
  const maxFlow = Math.max(2, ...data.map((p) => p.flow)) * 1.15;
  const x = (i) => pad.l + (i / Math.max(1, data.length - 1)) * (w - pad.l - pad.r);
  const y = (v) => h - pad.b - (v / maxFlow) * (h - pad.t - pad.b);

  // grid
  ctx.strokeStyle = "rgba(148,163,184,.12)"; ctx.fillStyle = "#64748b";
  ctx.font = "10px Consolas"; ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const v = (maxFlow / 3) * i, yy = y(v);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(w - pad.r, yy); ctx.stroke();
    ctx.fillText(v.toFixed(0), 4, yy + 3);
  }

  if (data.length > 1) {
    // area
    const grad = ctx.createLinearGradient(0, pad.t, 0, h - pad.b);
    grad.addColorStop(0, "rgba(34,211,238,.35)"); grad.addColorStop(1, "rgba(34,211,238,0)");
    ctx.beginPath();
    ctx.moveTo(x(0), y(data[0].flow));
    data.forEach((p, i) => ctx.lineTo(x(i), y(p.flow)));
    ctx.lineTo(x(data.length - 1), h - pad.b); ctx.lineTo(x(0), h - pad.b); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    // line
    ctx.beginPath();
    data.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.flow)) : ctx.moveTo(x(i), y(p.flow))));
    ctx.strokeStyle = "#22d3ee"; ctx.lineWidth = 2; ctx.stroke();
    // alert markers
    ctx.fillStyle = "#fb7185";
    data.forEach((p, i) => { if (p.alerts > 0) { ctx.beginPath(); ctx.arc(x(i), y(p.flow), 3, 0, 7); ctx.fill(); } });
    // last value
    const last = data[data.length - 1];
    ctx.fillStyle = "#cffafe"; ctx.font = "bold 11px Consolas";
    ctx.fillText(`${last.flow.toFixed(1)} L/min`, Math.min(x(data.length - 1) + 4, w - 70), y(last.flow) - 6);
  }
  if (data.length) $("#flow-now").textContent = `${data[data.length - 1].flow.toFixed(1)} L/min facility-wide`;
}

/* ---------------- notifications ---------------- */
function notifyNew(st) {
  st.alerts.forEach((a) => {
    if (a.status === "OPEN" && !S.knownAlerts.has(a.id)) {
      S.knownAlerts.add(a.id);
      if (!S.firstLoad) {
        const loss = a.estimated_daily_loss_liters > 0 ? ` · ${fmtL(a.estimated_daily_loss_liters)} L/day` : "";
        toast(`🚨 <b>${a.severity}</b> ${a.device_id} — ${esc(a.issue)}${loss}`, a.severity === "HIGH" || a.severity === "CRITICAL" ? "bad" : "");
      }
    }
  });
  st.tickets.forEach((t) => {
    if (t.status === "OPEN" && !S.knownTickets.has(t.ticket_id)) {
      S.knownTickets.add(t.ticket_id);
      if (!S.firstLoad) toast(`🎫 Dispatch ticket <b>${t.ticket_id}</b> auto-generated (${t.priority}) — ${esc(t.asset)}`, "bad");
    }
  });
}

/* ---------------- modals ---------------- */
function openModal(html) {
  $("#modal-content").innerHTML = html;
  $("#modal").showModal();
}

function openAlertModal(alertId) {
  const a = S.state.alerts.find((x) => x.id === alertId);
  if (!a) return;
  const t = a.telemetry || {};
  const isLoss = a.kind === "continuous_leak" || a.kind === "phantom_flush";
  const ticket = S.state.tickets.find((x) => x.alert_id === a.id);
  const math = a.kind === "continuous_leak"
    ? `flow ${(t.flow_lpm ?? 0).toFixed(1)} L/min × 1,440 min/day = <b>${fmtL(a.estimated_daily_loss_liters)} L/day</b><br>` +
      `${fmtL(a.estimated_daily_loss_liters)} × 30 days = <b>${fmtL(a.estimated_monthly_loss_liters)} L/month</b><br>` +
      `lost so far: ${fmtL(a.estimated_loss_liters)} L over ${t.duration_min ?? "?"} min`
    : a.kind === "phantom_flush"
      ? `${t.flush_events_zero_occupancy ?? "?"} phantom flushes × 6 L, rate ${(t.estimated_flush_rate_per_min ?? 0).toFixed(1)}/min<br>` +
        `→ <b>${fmtL(a.estimated_daily_loss_liters)} L/day</b> · ${fmtL(a.estimated_monthly_loss_liters)} L/month if unresolved`
      : "No direct water-loss signature for this incident type.";
  openModal(`
    <div class="modal-body">
      <div class="modal-title"><i class="dot ${a.status === "OPEN" ? sevDot(a.severity) : "dot-green"}"></i><h3>${a.id}</h3>
        <span class="badge sev-${a.severity}">${a.severity}</span><span class="badge prio">${a.priority}</span>
        ${a.status === "RESOLVED" ? '<span class="resolved-tag">✓ RESOLVED</span>' : ""}</div>
      <div class="modal-zone">${esc(a.zone)} · ${esc(a.device_type)} <b>${a.device_id}</b> · ${esc(a.issue)}</div>
      ${isLoss ? `<div class="modal-section"><h4>Water-loss estimation</h4><div class="loss-math">${math}</div></div>` : ""}
      <div class="modal-grid">
        ${Object.entries(t).slice(0, 6).map(([k, v]) => `<div class="stat"><div class="k">${esc(k.replaceAll("_", " "))}</div><div class="v">${esc(typeof v === "number" ? Math.round(v * 100) / 100 : v)}</div></div>`).join("")}
      </div>
      <div class="modal-section"><h4>AI diagnosis</h4><div class="modal-text">${esc(a.diagnosis)}</div></div>
      <div class="modal-section"><h4>Recommended action</h4><div class="modal-text">${esc(a.recommended_action)}</div>
        ${ticket ? `<div class="muted" style="margin-top:6px">Dispatched as ticket <b class="dev-id">${ticket.ticket_id}</b> (${ticket.status})</div>` : ""}</div>
      ${a.status === "RESOLVED" && a.resolution_note ? `<div class="modal-section"><h4>Resolution verification</h4><div class="modal-text">${esc(a.resolution_note)}</div></div>` : ""}
      <div class="modal-actions">
        <button class="btn" onclick="document.getElementById('modal').close()">Close</button>
        ${a.status === "OPEN" ? `<button class="btn btn-primary" id="modal-resolve">✓ Resolve &amp; verify</button>` : ""}
      </div>
    </div>`);
  const btn = $("#modal-resolve");
  if (btn) btn.addEventListener("click", async () => {
    btn.disabled = true;
    const res = await api.post(`/alerts/${a.id}/resolve`);
    $("#modal").close();
    toast(`✅ ${a.id} resolved · <b>${fmtL(res.saved_month_liters)} L/month</b> loss avoided`, "good");
    poll();
  });
}

function openDeviceModal(deviceId) {
  let dev = null, zoneName = "";
  for (const z of S.state.zones) {
    const d = z.devices.find((x) => x.device_id === deviceId);
    if (d) { dev = d; zoneName = z.name; break; }
  }
  if (!dev) return;
  const risk = S.state.risk_devices.find((r) => r.device_id === deviceId) || {};
  openModal(`
    <div class="modal-body">
      <div class="modal-title"><h3>${dev.device_id}</h3><span class="muted">${esc(dev.type)} · ${esc(zoneName)}</span></div>
      <div class="modal-grid">
        <div class="stat"><div class="k">Flow</div><div class="v">${dev.flow_lpm.toFixed(2)} L/min</div></div>
        <div class="stat"><div class="k">Occupancy</div><div class="v">${dev.occupancy}</div></div>
        <div class="stat"><div class="k">Flushes (tick)</div><div class="v">${dev.flush_count}</div></div>
        <div class="stat"><div class="k">Health score</div><div class="v">${dev.health_score}/100</div></div>
        <div class="stat"><div class="k">7-day risk</div><div class="v">${dev.risk}</div></div>
        <div class="stat"><div class="k">Failure prob.</div><div class="v">${Math.round((risk.failure_probability_7d || 0) * 100)}%</div></div>
      </div>
      <div class="modal-section"><h4>Live flow — last 24 ticks</h4>
        <svg class="spark" viewBox="0 0 300 64" preserveAspectRatio="none">
          ${spark(dev.flow_series || [])}
        </svg>
      </div>
      <div class="modal-section"><h4>Health drivers</h4>
        <div class="risk-bars" style="grid-template-columns:repeat(4,1fr)">
          ${rbar("Anomaly freq", (risk.anomaly_frequency || 0) / 30)}
          ${rbar("Flow variance", (risk.flow_variance_pct || 0) / 100)}
          ${rbar("Flush irregular", (risk.flush_irregularity || 0) / 15)}
          ${rbar("Sensor errors", (risk.sensor_errors || 0) / 12)}
        </div>
      </div>
      <div class="modal-actions"><button class="btn" onclick="document.getElementById('modal').close()">Close</button></div>
    </div>`);
}

function spark(series) {
  if (!series.length) return "";
  const max = Math.max(0.5, ...series);
  const pts = series.map((v, i) =>
    `${(i / Math.max(1, series.length - 1)) * 300},${60 - (v / max) * 54}`).join(" ");
  return `<polyline points="${pts}" fill="none" stroke="#22d3ee" stroke-width="2" />
    <line x1="0" y1="60" x2="300" y2="60" stroke="rgba(148,163,184,.25)" stroke-width="1" />`;
}

/* ---------------- AI chat ---------------- */
function addMsg(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  const log = $("#chat-log");
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

async function sendChat(text) {
  if (!text.trim()) return;
  addMsg("user", text);
  const thinking = addMsg("ai", "Analyzing live facility telemetry…");
  try {
    const res = await api.post("/ai", { query: text });
    thinking.textContent = res.response;
  } catch {
    thinking.textContent = "AI engine unreachable — check the API server.";
  }
  const log = $("#chat-log");
  log.scrollTop = log.scrollHeight;
}

/* ---------------- scenario wiring ---------------- */
$("#toolbar").querySelectorAll("[data-scenario]").forEach((btn) =>
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const res = await api.post(`/simulate/${btn.dataset.scenario}`);
      const target = res.zone || res.device_id;
      toast(`🧪 Scenario injected: <b>${btn.dataset.scenario}</b> on <b>${esc(target)}</b>`, "bad");
    } catch { toast("Scenario injection failed", "bad"); }
    setTimeout(() => (btn.disabled = false), 1500);
  }));

$("#btn-stop").addEventListener("click", async () => {
  await api.post("/simulate/stop");
  toast("■ All scenarios stopped — devices return to normal telemetry");
  poll();
});

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("#chat-input");
  sendChat(input.value);
  input.value = "";
});
document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => sendChat(chip.dataset.q)));

/* ---------------- guided demo ---------------- */
$("#btn-demo").addEventListener("click", () => {
  S.demoTimers.forEach(clearTimeout);
  S.demoTimers = [];
  const t = (ms, fn) => S.demoTimers.push(setTimeout(fn, ms));
  toast("🎬 Guided demo started — leak → detection → diagnosis → dispatch → savings");
  sendChat("Give me a facility status overview");

  t(1500, async () => {
    await api.post("/simulate/continuous-leak");
    toast("🧪 <b>FV-182</b> (Terminal 2 — Restroom 14): flush valve now leaking — watch the incident feed", "bad");
  });

  // detection needs 5 simulated minutes of sustained idle flow (~12s)
  // plus one poll cycle, then the modal shows the live loss math

  t(15500, () => sendChat("Where are we wasting the most water today?"));
  t(20500, () => sendChat("What should I fix first?"));

  t(26000, () => {
    const leak = (S.state?.alerts || []).find((a) => a.kind === "continuous_leak" && a.status === "OPEN");
    if (leak) openAlertModal(leak.id);
    else toast("⏳ Detection still converging — reopen the modal from the incident feed");
  });

  t(34000, async () => {
    const ticket = (S.state?.tickets || []).find((x) => x.status === "OPEN");
    if (ticket) {
      await api.post(`/tickets/${ticket.ticket_id}/resolve`);
      $("#modal").close();
      toast(`✅ Demo: ticket <b>${ticket.ticket_id}</b> resolved — savings added to the ledger`, "good");
    }
  });

  t(39000, () => sendChat("What is our sustainability impact?"));
  t(44000, () => toast("🎬 Demo complete — Detect → Diagnose → Dispatch → Conserve", "good"));
});

/* ---------------- boot ---------------- */
poll();
setInterval(poll, 2000);
window.addEventListener("resize", () => S.state && drawChart(S.state.timeseries));
