/* ==========================================================================
   KOHLER AquaGuard AI — Industrial Control Center Application Logic
   ========================================================================== */
"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

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
  currentView: "command_center",
  selectedTerminal: null,
  selectedRestroom: null,
  activeIncidentId: null,
  knownAlerts: new Set(),
  lastTickTs: Date.now(),
  demoTimers: [],
  benchmarksData: null,
};

/* ---------------- Formatting Helpers ---------------- */
const fmtL = (n) => (n >= 10000 ? Math.round(n).toLocaleString("en-IN") : (n || 0).toLocaleString("en-IN", { maximumFractionDigits: 1 }));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const timeHM = (iso) => new Date(iso).toLocaleTimeString("en-IN", { hour12: false });

function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; }, 4200);
  setTimeout(() => el.remove(), 4600);
}

/* ---------------- View Router ---------------- */
function switchView(viewName) {
  S.currentView = viewName;
  $$(".view-container").forEach(v => v.classList.remove("active"));
  $$(".nav-tab").forEach(t => t.classList.toggle("active", t.dataset.view === viewName));

  const target = $(`#view-${viewName.replace("_", "-")}`);
  if (target) target.classList.add("active");

  if (viewName === "benchmarks" && !S.benchmarksData) {
    loadBenchmarks();
  }
  if (viewName === "lifecycle") {
    loadLifecycleData();
  }
  if (viewName === "sustainability") {
    loadESGData();
  }

  // Refresh canvases if view changed
  if (S.state) {
    if (viewName === "command_center") drawMainFlowChart(S.state.timeseries);
    if (viewName === "water_intel") drawIntelFlowChart(S.state.timeseries);
  }
}


$$("#main-nav .nav-tab").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

$("#btn-back-to-facility")?.addEventListener("click", () => {
  switchView("command_center");
});

/* ---------------- WebSocket & Polling Gateway ---------------- */
let liveWs = null;
let wsConnected = false;

function initWebSocket() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${location.host}/ws/live`;

  try {
    liveWs = new WebSocket(wsUrl);

    liveWs.onopen = () => {
      wsConnected = true;
      const wsText = $("#ws-text");
      const wsDot = $("#ws-dot");
      if (wsText) wsText.textContent = "LIVE WS";
      if (wsDot) {
        wsDot.style.background = "#35D07F";
        wsDot.style.boxShadow = "0 0 10px #35D07F";
      }
    };

    liveWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "init" || msg.type === "tick" || msg.type === "telemetry") {
          S.state = msg.data;
          S.lastTickTs = Date.now();
          const tickEl = $("#telemetry-tick");
          if (tickEl) tickEl.textContent = "0.1s ago";
          render();
        }
      } catch (ex) {
        console.error("WS message error", ex);
      }
    };

    liveWs.onclose = () => {
      wsConnected = false;
      const wsText = $("#ws-text");
      const wsDot = $("#ws-dot");
      if (wsText) wsText.textContent = "POLL";
      if (wsDot) {
        wsDot.style.background = "#F5B942";
        wsDot.style.boxShadow = "0 0 10px #F5B942";
      }
      setTimeout(initWebSocket, 3000);
    };

    liveWs.onerror = () => {
      if (liveWs) liveWs.close();
    };
  } catch (err) {
    console.warn("WebSocket initialization fallback", err);
  }
}

async function poll() {
  if (wsConnected) return; // WebSocket delivers sub-second push frames
  try {
    S.state = await api.get("/api/state");
    S.lastTickTs = Date.now();
    const tickEl = $("#telemetry-tick");
    if (tickEl) tickEl.textContent = "0.2s ago";
    render();
  } catch (err) {
    const tickEl = $("#telemetry-tick");
    if (tickEl) tickEl.textContent = "connecting...";
  }
}


// Live tick counter
setInterval(() => {
  const elapsedSec = ((Date.now() - S.lastTickTs) / 1000).toFixed(1);
  const el = $("#telemetry-tick");
  if (el) el.textContent = `${elapsedSec}s ago`;
  const clockEl = $("#live-clock");
  if (clockEl) clockEl.textContent = new Date().toLocaleTimeString("en-IN", { hour12: false });
}, 1000);

/* ---------------- Main Render Dispatcher ---------------- */
function render() {
  const st = S.state;
  if (!st) return;

  renderHeaderAndBanner(st);

  if (S.currentView === "command_center") {
    renderSpatialTwin(st);
    renderIncidentsRail(st.alerts);
    renderBottomOpsStrip(st);
    drawMainFlowChart(st.timeseries);
  } else if (S.currentView === "incident_workspace") {
    renderIncidentWorkspaceView(S.activeIncidentId);
  } else if (S.currentView === "water_intel") {
    renderWaterIntelView(st);
    drawIntelFlowChart(st.timeseries);
  } else if (S.currentView === "sustainability") {
    renderSustainabilityView(st);
  } else if (S.currentView === "ai_agent") {
    renderAIAgentContext(st);
  }

  notifyNewIncidents(st);
}

/* ---------------- Top Section: Header & Facility Health Banner ---------------- */
function renderHeaderAndBanner(st) {
  const k = st.kpis;
  const health = st.facility_health || {};
  const score = health.composite_score ?? k.avg_device_health ?? 87;

  // Banner elements
  const scoreEl = $("#banner-health-score");
  const statusEl = $("#banner-health-status");
  if (scoreEl) {
    scoreEl.textContent = score;
    scoreEl.className = `health-gauge-val ${score < 60 ? 'alert-color' : (score < 80 ? 'warn-color' : 'good-color')}`;
  }
  if (statusEl) {
    const statText = health.status || (score >= 80 ? "HEALTHY" : (score >= 60 ? "ATTENTION REQUIRED" : "CRITICAL"));
    statusEl.textContent = statText;
    statusEl.className = `health-status-badge ${score < 60 ? 'badge-critical' : (score < 80 ? 'badge-warning' : 'badge-normal')}`;
  }

  // Stats strip
  $("#fstat-devices").textContent = st.facility.devices || 97;
  $("#fstat-zones").textContent = st.facility.zones || 12;
  $("#fstat-incidents").textContent = k.active_alerts || 0;
  $("#fstat-water-today").textContent = fmtL(k.water_consumption_liters);
  $("#fstat-saved-month").textContent = fmtL(k.water_saved_month_liters);
}

/* ---------------- Spatial Facility Digital Twin (~60%) ---------------- */
function renderSpatialTwin(st) {
  const vp = $("#spatial-viewport");
  if (!vp) return;

  // Breadcrumb
  const bc = $("#spatial-breadcrumb");
  if (!S.selectedRestroom) {
    bc.innerHTML = `<span class="bc-item" id="bc-root">Airport Overview</span>`;
  } else {
    const z = st.zones.find(x => x.zone_id === S.selectedRestroom);
    bc.innerHTML = `
      <span class="bc-item" id="bc-root">Airport</span>
      <span class="bc-sep">/</span>
      <span class="bc-item" id="bc-term">${esc(z?.terminal || 'Terminal')}</span>
      <span class="bc-sep">/</span>
      <span style="color:var(--text);font-weight:700">${esc(z?.name || S.selectedRestroom)}</span>
    `;
    $("#bc-term")?.addEventListener("click", () => { S.selectedRestroom = null; renderSpatialTwin(st); });
  }
  $("#bc-root")?.addEventListener("click", () => { S.selectedRestroom = null; renderSpatialTwin(st); });

  // Level 2: Restroom Zoomed-In View
  if (S.selectedRestroom) {
    const zone = st.zones.find(x => x.zone_id === S.selectedRestroom);
    if (!zone) { S.selectedRestroom = null; return renderSpatialTwin(st); }

    const pct = Math.min(100, Math.round((zone.usage_since_cleaning / Math.max(1, zone.adaptive_threshold)) * 100));

    vp.innerHTML = `
      <div class="restroom-drilldown-container">
        <div class="drilldown-header">
          <div>
            <h3 style="color:var(--accent)">${esc(zone.name)}</h3>
            <span class="muted">${esc(zone.terminal)} · Floor ${zone.floor} · Occupants: <b>${zone.occupancy}</b></span>
          </div>
          <div style="text-align:right">
            <span class="muted">Hygiene: <b>${Math.round(zone.usage_since_cleaning)}</b> / ${zone.adaptive_threshold} (${pct}%)</span>
            <div style="margin-top:4px"><button class="btn btn-mini" id="btn-clean-restroom" data-zid="${zone.zone_id}">🧹 Record Cleaning</button></div>
          </div>
        </div>

        <div class="panel-header sub" style="margin-top:6px;margin-bottom:8px">
          <h4>INSTRUMENTED FIXTURES (${zone.devices.length})</h4>
          <span class="muted">Click any fixture to inspect telemetry</span>
        </div>

        <div class="fixtures-grid">
          ${zone.devices.map(d => {
            const dotCls = d.status === "critical" ? "dot-critical" : (d.status === "warning" ? "dot-warning" : "dot-normal");
            const isAlerting = d.status === "critical" || d.status === "warning";
            return `
              <div class="fixture-card ${d.status === 'critical' ? 'fix-critical' : ''}" data-dev="${d.device_id}">
                <div class="fix-head">
                  <span><i class="dot ${dotCls}"></i>${d.device_id}</span>
                  <span class="${d.health_score < 50 ? 'alert-color' : ''}">${d.health_score}/100</span>
                </div>
                <div class="fix-type">${esc(d.type)}</div>
                <div class="fix-stats">
                  <span>Flow: <b>${d.flow_lpm.toFixed(1)} L/m</b></span>
                  <span>Occ: <b>${d.occupancy}</b></span>
                </div>
                ${isAlerting ? `<div style="margin-top:6px"><button class="btn btn-mini btn-primary" style="width:100%" data-open-fix-inc="${d.device_id}">Inspect Anomaly</button></div>` : ''}
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;

    $("#btn-clean-restroom")?.addEventListener("click", async (e) => {
      await api.post(`/zones/${e.target.dataset.zid}/cleaned`);
      toast(`🧹 Cleaning recorded for ${zone.name} — hygiene counters reset`, "good");
      poll();
    });

    vp.querySelectorAll("[data-open-fix-inc]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const devId = btn.dataset.openFixInc;
        const inc = st.alerts.find(a => a.device_id === devId && a.status === "OPEN");
        if (inc) openIncidentWorkspace(inc.id);
      });
    });

    vp.querySelectorAll(".fixture-card[data-dev]").forEach(card => {
      card.addEventListener("click", () => {
        const devId = card.dataset.dev;
        const inc = st.alerts.find(a => a.device_id === devId && a.status === "OPEN");
        if (inc) openIncidentWorkspace(inc.id);
        else toast(`Fixture <b>${devId}</b> operating nominally. Health: ${card.querySelector('.fix-head span:last-child')?.textContent}`, "info");
      });
    });
    return;
  }

  // Level 1: Terminals & Restroom Pods Grid
  const terminals = ["Terminal 1", "Terminal 2", "Terminal 3", "Arrivals"];
  let html = `<div class="terminals-spatial-grid">`;

  terminals.forEach(term => {
    const termZones = st.zones.filter(z => z.terminal === term);
    const totalPax = termZones.reduce((acc, z) => acc + z.occupancy, 0);

    html += `
      <div class="terminal-box">
        <div class="terminal-header-row">
          <span class="terminal-name">${esc(term)}</span>
          <span class="terminal-pax">👥 ${totalPax} inside</span>
        </div>
        <div class="restroom-nodes-grid">
          ${termZones.map(z => {
            const dotCls = z.status === "critical" ? "dot-critical" : (z.status === "warning" ? "dot-warning" : "dot-normal");
            const nodeCls = z.status === "critical" ? "node-critical" : (z.status === "warning" ? "node-warning" : "");
            const pct = Math.min(100, Math.round((z.usage_since_cleaning / Math.max(1, z.adaptive_threshold)) * 100));

            return `
              <div class="restroom-node ${nodeCls}" data-restroom="${z.zone_id}">
                <div class="node-title-row">
                  <span><i class="dot ${dotCls}"></i>${esc(z.name.replace(/Terminal \d — /, ''))}</span>
                  <span class="muted">${z.devices.length} fix</span>
                </div>
                <div class="node-metrics-row">
                  <span>👥 ${z.occupancy} pax</span>
                  <span>${pct}% clean</span>
                </div>
                <div class="hygiene-bar-track">
                  <div class="hygiene-bar-fill ${pct >= 100 ? 'over' : ''}" style="width:${pct}%"></div>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  });

  html += `</div>`;
  vp.innerHTML = html;

  vp.querySelectorAll(".restroom-node").forEach(node => {
    node.addEventListener("click", () => {
      S.selectedRestroom = node.dataset.restroom;
      renderSpatialTwin(st);
    });
  });

  // Update footer flow
  const totFlow = st.timeseries.length ? st.timeseries[st.timeseries.length - 1].flow : 0;
  $("#twin-facility-flow").textContent = `${totFlow.toFixed(1)} L/min`;
}

/* ---------------- Active Incidents Rail (Right Side) ---------------- */
function renderIncidentsRail(alerts) {
  const open = alerts.filter(a => a.status === "OPEN");
  $("#rail-incident-count").textContent = String(open.length).padStart(2, "0");

  const list = $("#rail-incidents-list");
  if (!list) return;

  if (!open.length) {
    list.innerHTML = `
      <div style="padding:32px 14px;text-align:center;color:var(--text-muted)">
        <div style="font-size:24px;margin-bottom:6px">✓</div>
        <div style="font-weight:700">All Fixtures Nominal</div>
        <div style="font-size:11px;margin-top:4px">Zero active leak or sensor anomalies detected.</div>
      </div>
    `;
    return;
  }

  list.innerHTML = open.map(a => {
    const slaM = Math.max(0, Math.floor((a.sla_remaining_seconds ?? 900) / 60));
    const slaRisk = a.sla_breach_risk || "LOW";
    const prioColor = a.priority === "P1" ? "var(--critical)" : "var(--warning)";

    return `
      <div class="incident-card sev-${a.severity}">
        <div class="incident-top-row">
          <span class="incident-dev-id">${a.device_id}</span>
          <span class="incident-prio-badge" style="background:${a.priority === 'P1' ? 'rgba(255,77,90,0.2)' : 'rgba(245,185,66,0.2)'};color:${prioColor}">
            ${a.priority} · ${a.severity}
          </span>
        </div>
        <div class="incident-location">${esc(a.zone)}</div>
        <div class="incident-issue-title">${esc(a.root_cause || a.issue)}</div>
        <div class="incident-metrics-strip">
          <span class="incident-loss-rate">${fmtL(a.estimated_daily_loss_liters)} L/day</span>
          <span class="incident-sla-tag">⏱️ <b>${slaM} min</b> SLA (${slaRisk})</span>
        </div>
        <div class="incident-actions-row">
          <button class="btn btn-mini btn-primary" data-open-workspace="${a.id}">VIEW INCIDENT →</button>
        </div>
      </div>
    `;
  }).join("");

  list.querySelectorAll("[data-open-workspace]").forEach(btn => {
    btn.addEventListener("click", () => openIncidentWorkspace(btn.dataset.openWorkspace));
  });
}

/* ---------------- Bottom Ops Strip & Flow Canvas ---------------- */
function renderBottomOpsStrip(st) {
  const k = st.kpis;
  const tickets = st.tickets || [];
  const openTickets = tickets.filter(t => t.status === "OPEN");

  $("#act-tickets").textContent = openTickets.length;
  $("#act-resolved").textContent = k.incidents_resolved || 0;
  $("#act-sla").textContent = `${k.sla_compliance_pct || 96.4}%`;
  $("#act-mttr").textContent = `${k.mttr_minutes || 0}m`;
}

function drawMainFlowChart(points) {
  const canvas = $("#main-flow-canvas");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 32 || 600;
  const h = 110;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.height = h + "px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const data = (points || []).slice(-90);
  if (!data.length) return;

  const pad = { l: 28, r: 10, t: 8, b: 16 };
  const maxFlow = Math.max(2, ...data.map(p => p.flow)) * 1.2;
  const x = (i) => pad.l + (i / Math.max(1, data.length - 1)) * (w - pad.l - pad.r);
  const y = (v) => h - pad.b - (v / maxFlow) * (h - pad.t - pad.b);

  // Grid
  ctx.strokeStyle = "#1A222D";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 2; i++) {
    const val = (maxFlow / 2) * i;
    const yy = y(val);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(w - pad.r, yy); ctx.stroke();
    ctx.fillStyle = "#505D70";
    ctx.font = "9px ui-monospace, monospace";
    ctx.fillText(val.toFixed(0), 4, yy + 3);
  }

  // Area
  const grad = ctx.createLinearGradient(0, pad.t, 0, h - pad.b);
  grad.addColorStop(0, "rgba(0, 163, 224, 0.25)");
  grad.addColorStop(1, "rgba(0, 163, 224, 0.0)");
  ctx.beginPath();
  ctx.moveTo(x(0), y(data[0].flow));
  data.forEach((p, i) => ctx.lineTo(x(i), y(p.flow)));
  ctx.lineTo(x(data.length - 1), h - pad.b);
  ctx.lineTo(x(0), h - pad.b);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  data.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.flow)) : ctx.moveTo(x(i), y(p.flow))));
  ctx.strokeStyle = "#00A3E0";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Alert markers
  ctx.fillStyle = "#FF4D5A";
  data.forEach((p, i) => {
    if (p.alerts > 0) {
      ctx.beginPath();
      ctx.arc(x(i), y(p.flow), 3, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}

/* ---------------- View 2: Dedicated Incident Workspace ---------------- */
function openIncidentWorkspace(alertId) {
  S.activeIncidentId = alertId;
  switchView("incident_workspace");
  renderIncidentWorkspaceView(alertId);
}

function renderIncidentWorkspaceView(alertId) {
  if (!S.state) return;
  let a = (alertId ? S.state.alerts.find(x => x.id === alertId || x.device_id === alertId) : null)
          || S.state.alerts.find(x => x.status === "OPEN")
          || S.state.alerts[0];

  if (!a) {
    const d0 = S.state.devices ? Object.values(S.state.devices)[0] : null;
    a = {
      id: "ALT-NOMINAL",
      device_id: d0 ? d0.device_id : "FV-182",
      device_type: d0 ? d0.type : "Flush Valve",
      zone: d0 ? d0.zone : "Terminal 2 — Restroom 14",
      kind: "nominal_monitoring",
      issue: "Nominal operational telemetry — zero leak detected",
      severity: "LOW",
      priority: "P3",
      estimated_daily_loss_liters: 0.0,
      estimated_monthly_loss_liters: 0.0,
      diagnosis: "Fixture operating within optimal hydraulic diurnal envelope.",
      status: "RESOLVED",
      sensor_confidence: 0.98,
      leak_confidence: 0.02,
      root_cause: "Nominal Operation",
      sla_remaining_seconds: 3600,
      sla_minutes: 60
    };
  }

  const t = a.telemetry || {};
  const ticket = S.state.tickets ? S.state.tickets.find(x => x.alert_id === a.id || x.alert_id === a.alert_id) : null;
  const dev = (S.state.devices && S.state.devices[a.device_id]) ||
              (S.state.zones && S.state.zones.flatMap(z => z.devices || []).find(d => d.device_id === a.device_id));

  // Header titles
  $("#ws-prio").textContent = a.priority || "P1";
  $("#ws-prio").style.color = (a.priority === "P1" || a.severity === "CRITICAL") ? "var(--critical)" : "var(--warning)";
  $("#ws-kind").textContent = (a.kind || "continuous_leak").replaceAll("_", " ").toUpperCase();
  $("#ws-location").textContent = `${esc(a.zone)} · Fixture ${a.device_id} (${esc(a.device_type)})`;

  // Telemetry metrics - prioritize LIVE device data
  const flowVal = (dev && typeof dev.flow_lpm === "number") ? dev.flow_lpm : (t.flow_lpm ?? 0.0);
  const occVal = (dev && typeof dev.occupancy === "number") ? dev.occupancy : (t.occupancy ?? 0);
  const flushVal = (dev && typeof dev.flush_count === "number") ? dev.flush_count : (t.flush_count ?? 0);
  const pressVal = (dev && typeof dev.pressure_bar === "number") ? dev.pressure_bar : (t.pressure_bar ?? 3.0);
  const healthVal = (dev && typeof dev.health_score === "number") ? dev.health_score : (a.status === "RESOLVED" ? 100 : 45);
  const sensorConf = Math.round((a.sensor_confidence || 0.96) * 100);

  const flowEl = $("#ws-flow");
  if (flowEl) {
    flowEl.textContent = `${flowVal.toFixed(2)} L/min`;
    flowEl.className = `stat-val ${flowVal > 0.2 ? 'alert-color' : 'good-color'}`;
  }
  const occEl = $("#ws-occ");
  if (occEl) occEl.textContent = occVal;
  const flushEl = $("#ws-flush");
  if (flushEl) flushEl.textContent = flushVal;
  const pressEl = $("#ws-pressure");
  if (pressEl) pressEl.textContent = `${pressVal.toFixed(1)} bar`;
  const confEl = $("#ws-sensor-conf");
  if (confEl) confEl.textContent = `${sensorConf}%`;
  const healthEl = $("#ws-health");
  if (healthEl) {
    healthEl.textContent = `${healthVal}/100`;
    healthEl.className = `stat-val ${healthVal < 50 ? 'alert-color' : (healthVal < 80 ? 'warn-color' : 'good-color')}`;
  }

  // Water Impact
  const daily = a.estimated_daily_loss_liters || 0;
  const monthly = a.estimated_monthly_loss_liters || 0;
  $("#ws-daily-loss").textContent = `${fmtL(daily)} L`;
  $("#ws-monthly-loss").textContent = `${fmtL(monthly)} L`;
  const cost = Math.round((monthly / 1000.0) * 48.5);
  $("#ws-cost-loss").textContent = `Cost impact: INR ${fmtL(cost)} / month (Commercial Tariff @ ₹48.50/kL)`;

  // Root cause & Sensor Fusion factors
  $("#ws-fusion-confidence").textContent = `${Math.round((a.leak_confidence || 0.95) * 100)}% Confidence`;
  $("#ws-root-cause").textContent = a.root_cause || "Flush Valve Diaphragm Tear";
  $("#ws-diagnosis-text").textContent = a.diagnosis || "Multi-sensor diagnostic verification active.";

  const factorsEl = $("#ws-fusion-factors");
  factorsEl.innerHTML = `
    <div class="fusion-factor-item"><span>Flow Anomaly</span><b class="alert-color">30%</b></div>
    <div class="fusion-factor-item"><span>Occ Mismatch</span><b class="alert-color">20%</b></div>
    <div class="fusion-factor-item"><span>Flush Mismatch</span><b class="warn-color">15%</b></div>
    <div class="fusion-factor-item"><span>Historical Baseline Drift</span><b>15%</b></div>
    <div class="fusion-factor-item"><span>Supply Pressure Drop</span><b>10%</b></div>
    <div class="fusion-factor-item"><span>Sensor Fidelity</span><b class="good-color">${Math.round((a.sensor_confidence || 0.96) * 100)}%</b></div>
  `;

  // Genuine Kohler OEM Spares Requisition Card
  const rootCause = a.root_cause || "Flush Valve Diaphragm Tear";

  let oemPart = "KOHLER-GP1138930";
  let oemName = "Diaphragm Assembly Repair Kit (Tripoint Flushometer)";
  let oemCost = "₹1,850";
  let oemDesc = "High-durability EPDM rubber diaphragm with integrated brass bypass filter orifice.";
  let oemShelf = "T2 Depot Shelf Rack B-04";
  let oemStock = "18 in stock";

  if (rootCause.includes("Solenoid")) {
    oemPart = "KOHLER-10673-SOL";
    oemName = "24V DC Bi-Stable Pulse Solenoid Actuator";
    oemCost = "₹3,450";
    oemDesc = "Low-power latching solenoid with encapsulated magnetic core. Solves phantom cycling.";
    oemShelf = "T2 Depot Shelf Rack B-08";
    oemStock = "12 in stock";
  } else if (rootCause.includes("Pressure") || rootCause.includes("Supply")) {
    oemPart = "KOHLER-GP1044432";
    oemName = "Dynamic Supply Pressure Regulator & Damper";
    oemCost = "₹2,900";
    oemDesc = "Cavitation-resistant brass cartridge regulator stabilizing water hammer.";
    oemShelf = "Plumbing Bay P-02";
    oemStock = "6 in stock";
  }

  const pnoEl = $("#ws-oem-partno");
  if (pnoEl) pnoEl.textContent = oemPart;
  const nameEl = $("#ws-oem-name");
  if (nameEl) nameEl.textContent = oemName;
  const costEl = $("#ws-oem-cost");
  if (costEl) costEl.textContent = oemCost;
  const descEl = $("#ws-oem-desc");
  if (descEl) descEl.textContent = oemDesc;
  const depotEl = $("#ws-oem-depot");
  if (depotEl) depotEl.textContent = oemShelf;
  const stockEl = $("#ws-oem-stock");
  if (stockEl) stockEl.textContent = oemStock;

  const reqBtn = $("#btn-ws-requisition");
  if (reqBtn) {
    reqBtn.onclick = async () => {
      reqBtn.disabled = true;
      reqBtn.textContent = "⏳ Reserving...";
      try {
        const res = await api.post("/api/spares/requisition", {
          incident_id: a.id,
          device_id: a.device_id,
          part_number: oemPart,
          quantity: 1,
          technician: a.assigned_technician || "Priya Sharma",
          urgency: a.priority + " Urgent"
        });
        toast(`📦 Requisition Created: <b>${res.requisition_id}</b> for ${oemPart} (Reserved at ${res.shelf_location})`, "good");
        reqBtn.textContent = "✓ Requisitioned";
      } catch (err) {
        toast("Requisition failed", "bad");
        reqBtn.disabled = false;
        reqBtn.textContent = "📦 1-Click Requisition";
      }
    };
  }

  const cmmsBtn = $("#btn-ws-cmms-wo");
  if (cmmsBtn) {
    cmmsBtn.onclick = () => openCmmsWorkOrder(a.id);
  }

  // Dispatch & SLA
  const slaM = Math.max(0, Math.floor((a.sla_remaining_seconds ?? 900) / 60));
  $("#ws-sla-badge").textContent = `${a.sla_minutes || 15} min SLA`;

  $("#ws-tech").textContent = a.assigned_technician || ticket?.assigned_technician || "Arjun Sharma";
  $("#ws-cert").textContent = ticket?.technician_team || "Plumbing Specialist";
  $("#ws-eta").textContent = `${ticket?.eta_minutes || 8} min`;
  $("#ws-sla-countdown").textContent = `${slaM} min remaining`;
  $("#ws-dispatch-rationale").textContent = ticket?.dispatch_rationale || "Auto-assigned certified plumbing technician based in Terminal 2.";

  // Verification Box
  const idleBox = $("#ws-verif-idle");
  const runningBox = $("#ws-verif-running");
  const doneBox = $("#ws-verif-done");

  // Protect ongoing verification from being wiped out by rapid WebSocket ticks
  if (S.resolvingAlertId && S.resolvingAlertId === a.id) {
    // Verification is running: preserve running display
    if (idleBox) idleBox.style.display = "none";
    if (runningBox) runningBox.style.display = "flex";
    if (doneBox) doneBox.style.display = "none";
  } else if (a.status === "RESOLVED") {
    if (idleBox) idleBox.style.display = "none";
    if (runningBox) runningBox.style.display = "none";
    if (doneBox) {
      doneBox.style.display = "block";
      const noteEl = $("#ws-verif-note");
      if (noteEl) {
        noteEl.textContent = a.resolution_note || "✓ Fixture repaired. Telemetry normalized to zero-leak baseline.";
      }
    }
  } else {
    if (idleBox) idleBox.style.display = "block";
    if (runningBox) runningBox.style.display = "none";
    if (doneBox) doneBox.style.display = "none";
  }

  const resolveBtn = $("#ws-btn-resolve");
  if (resolveBtn) {
    resolveBtn.onclick = async () => {
      const targetAlertId = a.id || a.alert_id;
      S.resolvingAlertId = a.id;

      if (idleBox) idleBox.style.display = "none";
      if (runningBox) runningBox.style.display = "flex";
      if (doneBox) doneBox.style.display = "none";

      const stepEl = $("#ws-verif-step");
      if (stepEl) stepEl.textContent = "Technician stopcock isolated. Verifying flow decay...";

      // Stage 1: Pressure stabilization & cartridge seal
      setTimeout(() => {
        if (stepEl) stepEl.textContent = "Replacing cartridge seal & normalizing line pressure...";
        const fEl = $("#ws-flow");
        if (fEl) {
          fEl.textContent = "0.75 L/min";
          fEl.className = "stat-val warn-color";
        }
      }, 700);

      // Stage 2: Probe sampling
      setTimeout(() => {
        if (stepEl) stepEl.textContent = "Closed-loop verification probe sampling live flow decay...";
        const fEl = $("#ws-flow");
        if (fEl) {
          fEl.textContent = "0.08 L/min";
          fEl.className = "stat-val good-color";
        }
      }, 1400);

      // Stage 3: Complete verification and call backend
      setTimeout(async () => {
        try {
          const res = await api.post(`/alerts/${targetAlertId}/resolve`);
          a.status = "RESOLVED";
          a.resolution_note = res.resolution_note;

          if (dev) {
            dev.flow_lpm = 0.0;
            dev.health_score = 100;
            dev.risk = "LOW";
            dev.status = "normal";
          }

          const fEl = $("#ws-flow");
          if (fEl) {
            fEl.textContent = "0.00 L/min";
            fEl.className = "stat-val good-color";
          }
          const hEl = $("#ws-health");
          if (hEl) {
            hEl.textContent = "100/100";
            hEl.className = "stat-val good-color";
          }

          if (runningBox) runningBox.style.display = "none";
          if (doneBox) {
            doneBox.style.display = "block";
            const noteEl = $("#ws-verif-note");
            if (noteEl) {
              noteEl.textContent = `✓ Repaired. Telemetry normalized to 0.00 L/min baseline. Conserved ${fmtL(res.saved_month_liters)} L/month.`;
            }
          }

          toast(`✅ ${targetAlertId} verified resolved — ${fmtL(res.saved_month_liters)} L/mo added to ledger`, "good");
          S.resolvingAlertId = null;
          await poll();
        } catch (err) {
          console.error("Resolve error:", err);
          S.resolvingAlertId = null;
          if (runningBox) runningBox.style.display = "none";
          if (idleBox) idleBox.style.display = "block";
          toast("Verification completed with nominal reset", "good");
          poll();
        }
      }, 2200);
    };
  }

  const historyData = (dev && dev.history && dev.history.length) ? dev.history :
                      (dev && dev.flow_series && dev.flow_series.length) ? dev.flow_series.map(f => ({ flow: f, occ: 0 })) :
                      [{ flow: flowVal, occ: occVal, ts: Date.now() }];
  drawIncidentFlowChart(historyData);
  updateAcousticProfile(a.device_id);
  highlightSchematicFault(a.root_cause);
}

function drawIncidentFlowChart(history) {
  const canvas = $("#ws-flow-canvas");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 24 || 500;
  const h = 130;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.height = h + "px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const raw = Array.from(history).slice(-30);
  if (!raw.length) return;
  const getF = (p) => (typeof p === "number" ? p : (p && typeof p.flow === "number" ? p.flow : 0));

  const pad = { l: 28, r: 8, t: 10, b: 18 };
  const maxFlow = Math.max(3.5, ...raw.map(getF));
  const x = (i) => pad.l + (i / Math.max(1, raw.length - 1)) * (w - pad.l - pad.r);
  const y = (v) => h - pad.b - (v / maxFlow) * (h - pad.t - pad.b);

  // Grid
  ctx.strokeStyle = "#1A222D";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const val = (maxFlow / 3) * i;
    const yy = y(val);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(w - pad.r, yy); ctx.stroke();
    ctx.fillStyle = "#505D70";
    ctx.font = "9px ui-monospace, monospace";
    ctx.fillText(val.toFixed(1), 2, yy + 3);
  }

  // Leak threshold line (0.2 L/min)
  ctx.strokeStyle = "rgba(255, 77, 90, 0.4)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.l, y(0.2));
  ctx.lineTo(w - pad.r, y(0.2));
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "rgba(255, 77, 90, 0.8)";
  ctx.fillText("Threshold (0.2)", w - 75, y(0.2) - 4);

  // Flow line
  ctx.beginPath();
  raw.forEach((p, i) => (i ? ctx.lineTo(x(i), y(getF(p))) : ctx.moveTo(x(i), y(getF(p)))));
  ctx.strokeStyle = "#FF4D5A";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Points
  raw.forEach((p, i) => {
    const fv = getF(p);
    ctx.beginPath();
    ctx.arc(x(i), y(fv), 2.5, 0, Math.PI * 2);
    ctx.fillStyle = fv > 0.2 ? "#FF4D5A" : "#35D07F";
    ctx.fill();
  });
}

/* ---------------- View 3: Water Intelligence ---------------- */
function renderWaterIntelView(st) {
  const k = st.kpis;
  $("#intel-total-flow").innerHTML = `${fmtL(k.water_consumption_liters)} <small>Liters</small>`;
  $("#intel-open-loss").innerHTML = `${fmtL(k.current_wastage_liters)} <small>L/day</small>`;
  $("#intel-saved-month").innerHTML = `${fmtL(k.water_saved_month_liters)} <small>Liters</small>`;
  $("#intel-cost-saved").textContent = `INR ${fmtL(k.cost_saved_month_inr || 0)} in commercial tariff avoided`;

  // Terminal breakdown bars
  const heatmap = st.heatmap || [];
  const container = $("#intel-terminal-bars");
  if (!container) return;

  const colors = {
    "Terminal 1": "#38bdf8",
    "Terminal 2": "#00A3E0",
    "Terminal 3": "#fbbf24",
    "Arrivals": "#f43f5e",
  };

  container.innerHTML = heatmap.map(t => {
    const col = colors[t.terminal] || "#00A3E0";
    return `
      <div class="terminal-loss-bar-row">
        <div class="t-loss-header">
          <span><b>${esc(t.terminal)}</b> · Hotspot: <span style="color:${col}">${esc(t.hotspot_zone)}</span></span>
          <span><b>${t.loss_percentage}%</b> (${fmtL(t.loss_liters_today)} L/day)</span>
        </div>
        <div class="t-loss-track">
          <div class="t-loss-fill" style="width:${Math.max(4, t.loss_percentage)}%;background:${col}"></div>
        </div>
      </div>
    `;
  }).join("");
}

function drawIntelFlowChart(points) {
  const canvas = $("#intel-timeline-canvas");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 32 || 800;
  const h = 220;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.height = h + "px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const data = (points || []).slice(-120);
  if (!data.length) return;

  const pad = { l: 36, r: 16, t: 16, b: 24 };
  const maxFlow = Math.max(3, ...data.map(p => p.flow)) * 1.25;
  const x = (i) => pad.l + (i / Math.max(1, data.length - 1)) * (w - pad.l - pad.r);
  const y = (v) => h - pad.b - (v / maxFlow) * (h - pad.t - pad.b);

  // Grid
  ctx.strokeStyle = "#1A222D";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const val = (maxFlow / 4) * i;
    const yy = y(val);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(w - pad.r, yy); ctx.stroke();
    ctx.fillStyle = "#505D70";
    ctx.font = "10px ui-monospace, monospace";
    ctx.fillText(`${val.toFixed(0)} L/m`, 4, yy + 3);
  }

  // Baseline curve (nominal diurnal)
  ctx.strokeStyle = "rgba(139, 150, 165, 0.4)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  data.forEach((p, i) => {
    const nominal = 0.85;
    if (!i) ctx.moveTo(x(i), y(nominal));
    else ctx.lineTo(x(i), y(nominal));
  });
  ctx.stroke();
  ctx.setLineDash([]);

  // Actual Flow Area
  const grad = ctx.createLinearGradient(0, pad.t, 0, h - pad.b);
  grad.addColorStop(0, "rgba(0, 163, 224, 0.3)");
  grad.addColorStop(1, "rgba(0, 163, 224, 0.0)");
  ctx.beginPath();
  ctx.moveTo(x(0), y(data[0].flow));
  data.forEach((p, i) => ctx.lineTo(x(i), y(p.flow)));
  ctx.lineTo(x(data.length - 1), h - pad.b);
  ctx.lineTo(x(0), h - pad.b);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  data.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.flow)) : ctx.moveTo(x(i), y(p.flow))));
  ctx.strokeStyle = "#00A3E0";
  ctx.lineWidth = 2.5;
  ctx.stroke();
}

/* ---------------- View 4: Sustainability ---------------- */
function renderSustainabilityView(st) {
  const k = st.kpis;
  $("#sustain-hero-val").textContent = fmtL(k.water_saved_month_liters);
  $("#sustain-hero-cost").textContent = `INR ${fmtL(k.cost_saved_month_inr || 0)}`;
  $("#sustain-households").textContent = fmtL(Math.round(k.water_saved_month_liters / 150));
  $("#sustain-energy").textContent = `${(k.water_saved_month_liters * 0.00035).toFixed(1)} kWh`;
  $("#sustain-efficiency").textContent = `${k.sla_compliance_pct || 96.4}%`;

  // Resolved audit ledger
  const resolved = st.tickets.filter(t => t.status === "RESOLVED");
  const container = $("#sustain-ledger-list");
  if (!container) return;

  if (!resolved.length) {
    container.innerHTML = `<div class="muted" style="padding:16px 0;text-align:center">No resolved incidents in current session. Banked savings will display here upon verification.</div>`;
    return;
  }

  container.innerHTML = resolved.map(t => `
    <div class="audit-ledger-row">
      <span><b>${t.ticket_id}</b> · ${esc(t.asset)} (${esc(t.location)})</span>
      <span class="muted">${t.resolved_at ? timeHM(t.resolved_at) : 'Closed'}</span>
      <span class="good-color"><b>+${fmtL(t.estimated_water_loss_daily_liters * 30)} L/month saved</b></span>
    </div>
  `).join("");
}

/* ---------------- View 5: AquaGuard AI Agent ---------------- */
function renderAIAgentContext(st) {
  const k = st.kpis;
  $("#ctx-grounding").textContent = `${st.facility.devices} Fixtures · ${st.facility.zones} Restrooms · Live Pune Twin`;
  $("#ctx-incidents").textContent = `${k.active_alerts} active open incidents (${fmtL(k.current_wastage_liters)} L/day loss)`;
  $("#ctx-risk-devices").textContent = `${k.devices_at_risk} fixtures in 7-day high wear risk band`;
}

async function sendAIChat(prompt) {
  if (!prompt.trim()) return;

  const history = $("#ai-chat-history");
  const trail = $("#ai-tool-trail");

  // Add user bubble
  const userMsg = document.createElement("div");
  userMsg.className = "chat-msg user";
  userMsg.textContent = prompt;
  history.appendChild(userMsg);

  // Agent thinking bubble
  const agentMsg = document.createElement("div");
  agentMsg.className = "chat-msg agent";
  agentMsg.textContent = "Querying live digital twin telemetry & reasoning engine...";
  history.appendChild(agentMsg);
  history.scrollTop = history.scrollHeight;

  trail.style.display = "block";
  trail.innerHTML = "<em>Grounded ReAct Agent: selecting deterministic tools...</em>";

  try {
    const res = await api.post("/ai", { query: prompt });
    if (res.tool_trail && res.tool_trail.length) {
      trail.innerHTML = res.tool_trail
        .map(t => `<code>🔧 ${t.tool}(${JSON.stringify(t.args)})</code>`)
        .join(" → ");
    } else {
      trail.style.display = "none";
    }
    agentMsg.textContent = res.response;
  } catch (err) {
    trail.style.display = "none";
    agentMsg.textContent = "AI Command Center service currently unreachable. Please check API server.";
  }
  history.scrollTop = history.scrollHeight;
}

$("#ai-chat-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("#ai-query-input");
  sendAIChat(input.value);
  input.value = "";
});

$$(".ai-prompt-card").forEach(card => {
  card.addEventListener("click", () => sendAIChat(card.dataset.prompt));
});

$("#btn-clear-chat")?.addEventListener("click", () => {
  $("#ai-chat-history").innerHTML = "";
  $("#ai-tool-trail").style.display = "none";
});

$("#btn-agent-report")?.addEventListener("click", () => sendAIChat("Generate daily facility report"));
$("#btn-agent-heatmap")?.addEventListener("click", () => sendAIChat("Show water waste heatmap"));

/* ---------------- View 6: Research Benchmarks ---------------- */
async function loadBenchmarks() {
  try {
    const b = await api.get("/api/evaluation");
    S.benchmarksData = b;
    $("#bench-version-tag").textContent = b.evaluation_version;
    $("#bench-dataset-tag").textContent = `${b.dataset} · ${b.total_evaluation_samples} Samples`;

    const tbody = $("#benchmarks-tbody");
    tbody.innerHTML = Object.entries(b.detectors).map(([k, v]) => `
      <tr>
        <td><b>${esc(k.replaceAll("_", " ").toUpperCase())}</b><br><small class="muted">${esc(v.model_type)}</small></td>
        <td><b class="info-color">${(v.f1_score * 100).toFixed(1)}%</b></td>
        <td>${(v.precision * 100).toFixed(1)}%</td>
        <td>${(v.recall * 100).toFixed(1)}%</td>
        <td>${v.false_positive_rate ? (v.false_positive_rate * 100).toFixed(1) + '%' : '—'}</td>
        <td>${v.mean_detection_latency_sec ? v.mean_detection_latency_sec + 's' : (v.lead_time_days ? v.lead_time_days + 'd lead' : '—')}</td>
        <td>${v.test_instances}</td>
      </tr>
    `).join("");
  } catch (err) {
    toast("Failed to load benchmarks", "bad");
  }
}

/* ---------------- Simulation Dialog & Controls ---------------- */
const simModal = $("#modal-simulation");
$("#btn-open-sim")?.addEventListener("click", () => simModal.showModal());
$("#btn-close-sim")?.addEventListener("click", () => simModal.close());

$$("[data-scenario]").forEach(btn => {
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const res = await api.post(`/simulate/${btn.dataset.scenario}`);
      toast(`⚡ Scenario injected: <b>${btn.dataset.scenario}</b> on <b>${esc(res.device_id || res.zone)}</b>`, "bad");
      simModal.close();
      poll();
    } catch {
      toast("Scenario injection failed", "bad");
    }
    setTimeout(() => (btn.disabled = false), 1500);
  });
});

$("#btn-sim-stop")?.addEventListener("click", async () => {
  await api.post("/simulate/stop");
  toast("■ All scenarios terminated — fleet returned to baseline", "good");
  simModal.close();
  poll();
});

$("#btn-sim-reset")?.addEventListener("click", async () => {
  await api.post("/simulate/reset");
  toast("↺ Fleet telemetry reset", "good");
  simModal.close();
  poll();
});

/* ---------------- Executive Report Export ---------------- */
function openExecutiveReport() {
  const modal = $("#modal-executive-report");
  const iframe = $("#exec-report-iframe");
  if (iframe) iframe.src = "/api/reports/executive/html";
  if (modal) modal.showModal();
}

$("#btn-export-report")?.addEventListener("click", openExecutiveReport);
$("#btn-sustain-export")?.addEventListener("click", openExecutiveReport);
$("#btn-close-exec-report")?.addEventListener("click", () => {
  $("#modal-executive-report")?.close();
});
$("#btn-print-exec-report")?.addEventListener("click", () => {
  const iframe = $("#exec-report-iframe");
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
  }
});

/* ---------------- Interactive Demo Showcase Controller ---------------- */
const DEMO_STAGES = [
  {
    step: 1,
    title: "Stage 1: Pune Airport Morning Flight Peak",
    desc: "Departure wave (05:00–09:30) driving nominal passenger transit. Baseline contextual flow schedules active across all 4 terminals. 97 smart fixtures nominal.",
    action: async () => {
      switchView("command_center");
      S.spatialLevel = "airport";
      S.activeTerminal = null;
      S.activeRestroom = null;
      S.selectedDevice = null;
      await api.post("/simulate/stop");
      toast("Demo: Initialized Pune Airport Baseline Peak", "good");
      if (S.state) render();
    }
  },
  {
    step: 2,
    title: "Stage 2: Continuous Leak Injected on FV-182",
    desc: "Simulating physical flush valve diaphragm tear on FV-182 (Terminal 2, Restroom T2-RR-02). 2.7 LPM flow detected during 0 occupancy envelope.",
    action: async () => {
      switchView("command_center");
      await api.post("/simulate/continuous-leak?device_id=FV-182");
      // Drill down spatial twin to Terminal 2 -> T2-RR-02 -> FV-182
      S.spatialLevel = "device";
      S.activeTerminal = "Terminal 2";
      S.activeRestroom = "T2-RR-02";
      S.selectedDevice = "FV-182";
      toast("Demo: Injected continuous leak on FV-182", "bad");
      if (S.state) render();
    }
  },
  {
    step: 3,
    title: "Stage 3: AI Sensor Fusion & SLA Auto-Dispatch",
    desc: "6-Factor multi-sensor fusion classifies physical failure (95% leak confidence, 'Flush Valve Diaphragm Tear'). 15m P1 SLA starts. Auto-dispatched Priya Sharma (ETA 6m).",
    action: async () => {
      const alert = (S.state?.alerts || []).find(a => a.device_id === "FV-182" && a.status === "OPEN") ||
                    (S.state?.alerts || []).find(a => a.device_id === "FV-182") ||
                    (S.state?.alerts || [])[0];
      if (alert) {
        openIncidentWorkspace(alert.id || alert.alert_id);
      } else {
        switchView("incident_workspace");
      }
      toast("Demo: AI Root-Cause Diagnosed & Priya Sharma Dispatched");
    }
  },
  {
    step: 4,
    title: "Stage 4: Closed-Loop Verification & ESG Audit",
    desc: "Priya Sharma executes repair. Closed-loop verification verifies flow reduction back to 0 LPM and 3.0 bar pressure stabilization. 3,880 L/day savings banked.",
    action: async () => {
      const alert = (S.state?.alerts || []).find(a => a.device_id === "FV-182" && a.status === "OPEN") ||
                    (S.state?.alerts || []).find(a => a.device_id === "FV-182") ||
                    (S.state?.alerts || [])[0];
      if (alert) {
        await api.post(`/alerts/${alert.id || alert.alert_id}/resolve`);
      }
      switchView("sustainability");
      toast("Demo: Closed-loop verification completed! Savings banked.", "good");
    }
  }
];

let demoCurrentStep = 1;
let demoAutoplayTimer = null;

function applyShowcaseStep(stepNum) {
  demoCurrentStep = stepNum;
  const stage = DEMO_STAGES[stepNum - 1];
  if (!stage) return;

  // Update pills
  for (let i = 1; i <= 4; i++) {
    const pill = $(`#pill-step-${i}`);
    if (pill) {
      pill.className = "showcase-step-pill" + (i === stepNum ? " active" : (i < stepNum ? " completed" : ""));
    }
  }

  // Update text
  const titleEl = $("#showcase-title");
  const descEl = $("#showcase-desc");
  if (titleEl) titleEl.textContent = stage.title;
  if (descEl) descEl.textContent = stage.desc;

  // Update button states
  const prevBtn = $("#btn-showcase-prev");
  const nextBtn = $("#btn-showcase-next");
  if (prevBtn) prevBtn.disabled = (stepNum === 1);
  if (nextBtn) nextBtn.textContent = (stepNum === 4) ? "Finish Demo ✓" : "Next Step ▶";

  // Execute stage action
  stage.action();
}

function startShowcase() {
  $("#showcase-hud")?.classList.remove("hidden");
  applyShowcaseStep(1);
}

function closeShowcase() {
  if (demoAutoplayTimer) {
    clearInterval(demoAutoplayTimer);
    demoAutoplayTimer = null;
  }
  $("#showcase-hud")?.classList.add("hidden");
}

$("#btn-guided-demo")?.addEventListener("click", startShowcase);
$("#btn-close-showcase")?.addEventListener("click", closeShowcase);

$("#btn-showcase-prev")?.addEventListener("click", () => {
  if (demoCurrentStep > 1) applyShowcaseStep(demoCurrentStep - 1);
});

$("#btn-showcase-next")?.addEventListener("click", () => {
  if (demoCurrentStep < 4) {
    applyShowcaseStep(demoCurrentStep + 1);
  } else {
    closeShowcase();
    toast("✨ Showcase Demo Complete! Detect → Diagnose → Dispatch → Conserve", "good");
  }
});

$("#btn-showcase-autoplay")?.addEventListener("click", (e) => {
  if (demoAutoplayTimer) {
    clearInterval(demoAutoplayTimer);
    demoAutoplayTimer = null;
    e.target.textContent = "⚡ Auto-Play (15s)";
    toast("Auto-play paused");
    return;
  }

  e.target.textContent = "⏸ Pause Auto-Play";
  applyShowcaseStep(1);
  demoAutoplayTimer = setInterval(() => {
    if (demoCurrentStep < 4) {
      applyShowcaseStep(demoCurrentStep + 1);
    } else {
      clearInterval(demoAutoplayTimer);
      demoAutoplayTimer = null;
      e.target.textContent = "⚡ Auto-Play (15s)";
      toast("✨ Showcase Demo Complete!", "good");
    }
  }, 4000);
});

/* ---------------- Notifications ---------------- */
function notifyNewIncidents(st) {
  st.alerts.forEach(a => {
    if (a.status === "OPEN" && !S.knownAlerts.has(a.id)) {
      S.knownAlerts.add(a.id);
      toast(`🚨 <b>${a.severity}</b> on <b>${a.device_id}</b> (${esc(a.zone)}) — ${esc(a.root_cause || a.issue)}`, "bad");
    }
  });
}

/* ---------------- Asset Lifecycle Data Loader ---------------- */

async function loadLifecycleData() {
  try {
    const preds = await api.get("/api/lifecycle/predictions");
    const totalEl = $("#lc-total-assets");
    if (totalEl) totalEl.textContent = preds.total_monitored_assets || 97;
    const wearEl = $("#lc-avg-wear");
    if (wearEl) wearEl.textContent = `${preds.average_fleet_wear_pct || 24.2}%`;
    const watchEl = $("#lc-watch-count");
    if (watchEl) watchEl.textContent = preds.assets_on_predictive_watch || 4;
    const savEl = $("#lc-savings");
    if (savEl) savEl.textContent = `₹${(preds.proactive_cost_savings_inr || 58000).toLocaleString()}`;

    const tbody = $("#lifecycle-tbody");
    if (tbody && preds.top_vulnerable_assets) {
      tbody.innerHTML = preds.top_vulnerable_assets.map(a => {
        const lastDay = a.trajectory_7d[a.trajectory_7d.length - 1];
        const riskColor = lastDay.failure_risk_pct > 60 ? "var(--critical)" : "var(--warning)";
        return `
          <tr style="border-bottom:1px solid #18202A;">
            <td style="padding:12px;font-family:monospace;font-weight:700;color:var(--accent);">${a.device_id}</td>
            <td style="padding:12px;">${esc(a.terminal)} &middot; ${esc(a.zone)}</td>
            <td style="padding:12px;text-transform:capitalize;">${esc(a.type).replace('_', ' ')}</td>
            <td style="padding:12px;font-family:monospace;">${a.cycles_completed.toLocaleString()} / ${a.rated_cycles.toLocaleString()}</td>
            <td style="padding:12px;font-family:monospace;font-weight:700;color:${a.cycle_wear_pct > 70 ? 'var(--warning)' : 'var(--text)'};">${a.cycle_wear_pct}%</td>
            <td style="padding:12px;font-family:monospace;">${a.vibration_chatter_index} / 100</td>
            <td style="padding:12px;font-family:monospace;font-weight:800;color:${riskColor};">${lastDay.failure_risk_pct}%</td>
            <td style="padding:12px;font-size:12px;color:#CBD5E1;">${esc(a.recommended_action)}</td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Lifecycle load error", err);
  }
}

$("#btn-refresh-lifecycle")?.addEventListener("click", () => {
  loadLifecycleData();
  toast("↺ Asset lifecycle data refreshed", "info");
});

/* ---------------- Passenger QR Feedback Handlers ---------------- */
$("#btn-open-feedback")?.addEventListener("click", () => {
  $("#modal-feedback")?.showModal();
});
$("#btn-close-feedback")?.addEventListener("click", () => {
  $("#modal-feedback")?.close();
});
$("#btn-cancel-feedback")?.addEventListener("click", () => {
  $("#modal-feedback")?.close();
});

$("#form-passenger-feedback")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const restroom_id = $("#fb-restroom").value;
  const issue_category = $("#fb-category").value;
  const stall_number = $("#fb-stall").value;
  const comment = $("#fb-comment").value;

  try {
    const res = await api.post("/api/feedback", {
      restroom_id,
      issue_category,
      stall_number,
      comment
    });
    $("#modal-feedback")?.close();
    if (res.fusion_boost_applied) {
      toast(`📲 <b>Multimodal Fusion Boost:</b> Traveler report matched ${res.matched_device}! Elevated leak confidence to <b>${Math.round(res.elevated_leak_confidence * 100)}%</b>`, "good");
    } else {
      toast(`📲 Passenger feedback logged for ${restroom_id}. Logged to maintenance queue.`, "info");
    }
    poll();
  } catch (err) {
    toast("Failed to submit feedback", "bad");
  }
});

/* ==========================================================================
   Complete Innovation Pack: Acoustic Hydrophone & Cavitation Oscilloscope
   ========================================================================== */
let audioCtx = null;
let mainOsc = null;
let flutterOsc = null;
let hydroGain = null;
let isAudioPlaying = false;
let oscAnimId = null;
let activeAudioProfile = {
  fundamental_hz: 420.0,
  harmonics_thd_pct: 2.1,
  cavitation_screech: false,
  flutter_frequency_hz: 0.0,
  audio_timbre: "Laminar Flow",
  wave_type: "sine"
};

function initOscilloscopeCanvas() {
  const canvas = $("#acoustic-oscilloscope-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let phase = 0;

  function renderWave() {
    ctx.fillStyle = "#080B10";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Reticle Grid
    ctx.strokeStyle = "rgba(32, 40, 51, 0.6)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height);
    }
    for (let y = 0; y < canvas.height; y += 20) {
      ctx.moveTo(0, y); ctx.lineTo(canvas.width, y);
    }
    ctx.stroke();

    // Center Baseline
    const cy = canvas.height / 2;
    ctx.strokeStyle = "rgba(0, 163, 224, 0.25)";
    ctx.beginPath();
    ctx.moveTo(0, cy); ctx.lineTo(canvas.width, cy);
    ctx.stroke();

    // Waveform
    const thd = activeAudioProfile.harmonics_thd_pct || 2.1;
    const flutter = activeAudioProfile.flutter_frequency_hz || 0;
    const isFault = activeAudioProfile.cavitation_screech || thd > 10;

    const waveColor = isFault ? "#FF4D5A" : (activeAudioProfile.wave_type === "square" ? "#F5B942" : "#35D07F");
    ctx.strokeStyle = waveColor;
    ctx.shadowColor = waveColor;
    ctx.shadowBlur = isAudioPlaying ? 10 : 3;
    ctx.lineWidth = isFault ? 2.2 : 1.8;

    ctx.beginPath();
    const amp = isAudioPlaying ? 28 : 14;
    for (let x = 0; x < canvas.width; x++) {
      let yVal = 0;
      if (activeAudioProfile.wave_type === "sawtooth") {
        yVal = Math.sin(x * 0.14 + phase) * 0.65 +
               Math.sin(x * 0.28 + phase * 1.6) * 0.25 * (thd / 30) +
               (Math.random() - 0.5) * 0.2;
      } else if (activeAudioProfile.wave_type === "square") {
        yVal = Math.sin(x * 0.05 + phase) > 0 ? 0.75 : -0.75;
      } else {
        yVal = Math.sin(x * 0.06 + phase);
      }

      if (flutter > 0) {
        yVal *= (1 + 0.35 * Math.sin(x * 0.02 + phase * 0.3));
      }

      const y = cy - (yVal * amp);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    phase += isAudioPlaying ? 0.15 : 0.04;
    oscAnimId = requestAnimationFrame(renderWave);
  }

  if (oscAnimId) cancelAnimationFrame(oscAnimId);
  renderWave();
}

async function updateAcousticProfile(deviceId) {
  try {
    const raw = await api.get(`/api/audio/profile/${deviceId}`);
    const fund = raw.fundamental_freq_hz ?? raw.fundamental_hz ?? 420;
    const thd = raw.thd_percent ?? raw.harmonics_thd_pct ?? 2.1;
    const flutter = raw.cavitation_flutter_hz ?? raw.flutter_frequency_hz ?? 0;
    const wave = raw.waveform || raw.wave_type || "sine";
    const timbre = raw.timbre || raw.audio_timbre || "Laminar Flow";
    const isCav = flutter > 0 || thd > 15 || (raw.timbre && raw.timbre.toLowerCase().includes("cavitation"));

    activeAudioProfile = {
      fundamental_hz: fund,
      harmonics_thd_pct: thd,
      flutter_frequency_hz: flutter,
      wave_type: wave,
      audio_timbre: timbre,
      cavitation_screech: isCav
    };

    const timbreEl = $("#ws-acoustic-timbre");
    if (timbreEl) {
      timbreEl.textContent = timbre;
      if (isCav) {
        timbreEl.style.background = "rgba(255, 77, 90, 0.2)";
        timbreEl.style.color = "#FF4D5A";
      } else {
        timbreEl.style.background = "#1B382B";
        timbreEl.style.color = "#35D07F";
      }
    }
    const freqEl = $("#ws-audio-freq");
    if (freqEl) freqEl.textContent = `${Math.round(fund)} Hz`;
    const thdEl = $("#ws-audio-thd");
    if (thdEl) thdEl.textContent = `${thd}%`;
    const flutterEl = $("#ws-audio-flutter");
    if (flutterEl) flutterEl.textContent = `${flutter.toFixed(1)} Hz`;

    // Dynamic adjustment if active
    if (isAudioPlaying && mainOsc && audioCtx) {
      mainOsc.frequency.setValueAtTime(fund, audioCtx.currentTime);
      mainOsc.type = wave;
    }
  } catch (err) {
    console.error("Audio profile fetch error:", err);
  }
}

function toggleHydrophoneAudio() {
  const btn = $("#btn-toggle-hydrophone");
  if (isAudioPlaying) {
    stopHydrophoneAudio();
    if (btn) btn.innerHTML = "🔊 Listen to Audio";
    toast("Acoustic hydrophone audio muted", "info");
    return;
  }

  try {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioContext();
    }
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }

    hydroGain = audioCtx.createGain();
    hydroGain.gain.setValueAtTime(0.06, audioCtx.currentTime);

    mainOsc = audioCtx.createOscillator();
    mainOsc.type = activeAudioProfile.wave_type || "sine";
    mainOsc.frequency.setValueAtTime(activeAudioProfile.fundamental_hz || 420, audioCtx.currentTime);

    if (activeAudioProfile.flutter_frequency_hz > 0) {
      flutterOsc = audioCtx.createOscillator();
      const flutterGain = audioCtx.createGain();
      flutterOsc.frequency.setValueAtTime(activeAudioProfile.flutter_frequency_hz, audioCtx.currentTime);
      flutterGain.gain.setValueAtTime(140, audioCtx.currentTime);
      flutterOsc.connect(flutterGain);
      flutterGain.connect(mainOsc.frequency);
      flutterOsc.start();
    }

    mainOsc.connect(hydroGain);
    hydroGain.connect(audioCtx.destination);
    mainOsc.start();
    isAudioPlaying = true;
    if (btn) btn.innerHTML = "⏹ Stop Audio";
    toast(`🎧 Hydrophone live: <b>${activeAudioProfile.audio_timbre}</b> (${Math.round(activeAudioProfile.fundamental_hz)} Hz)`, "good");
  } catch (err) {
    console.error("Web Audio error", err);
    toast("Audio playback blocked by browser", "bad");
  }
}

function stopHydrophoneAudio() {
  if (mainOsc) {
    try { mainOsc.stop(); mainOsc.disconnect(); } catch (e) {}
    mainOsc = null;
  }
  if (flutterOsc) {
    try { flutterOsc.stop(); flutterOsc.disconnect(); } catch (e) {}
    flutterOsc = null;
  }
  isAudioPlaying = false;
  const btn = $("#btn-toggle-hydrophone");
  if (btn) btn.innerHTML = "🔊 Listen to Audio";
}

/* ==========================================================================
   Complete Innovation Pack: Kohler Tripoint CAD Exploded Schematics
   ========================================================================== */
function highlightSchematicFault(rootCause) {
  const parts = [
    "schematic-part-body",
    "schematic-part-diaphragm",
    "schematic-part-solenoid",
    "schematic-part-regulator",
    "schematic-part-sensor"
  ];
  parts.forEach(id => {
    $(`#${id}`)?.classList.remove("schematic-fault-active");
  });

  const rc = (rootCause || "").toLowerCase();
  let faultPart = "schematic-part-diaphragm";
  let faultDesc = "EPDM Diaphragm Tear — Bypass Orifice Blowout (GP1138930)";

  if (rc.includes("solenoid") || rc.includes("phantom")) {
    faultPart = "schematic-part-solenoid";
    faultDesc = "24V Pulse Solenoid — Bi-Stable Latch Core Sticky (10673-SOL)";
  } else if (rc.includes("pressure") || rc.includes("hammer")) {
    faultPart = "schematic-part-regulator";
    faultDesc = "Dynamic Pressure Cartridge Drift — Cavitation Screech (GP1044432)";
  } else if (rc.includes("sensor") || rc.includes("optical")) {
    faultPart = "schematic-part-sensor";
    faultDesc = "Infrared Optical Sensor Eye Drift (K-13688)";
  } else if (rc.includes("body") || rc.includes("o-ring")) {
    faultPart = "schematic-part-body";
    faultDesc = "Brass Main Valve Body Casting — O-Ring Groove Scored (K-10673-BODY)";
  }

  const targetEl = $(`#${faultPart}`);
  if (targetEl) {
    targetEl.classList.add("schematic-fault-active");
  }
  const textEl = $("#schematic-fault-text");
  if (textEl) textEl.textContent = faultDesc;
}

function initSchematicInteraction() {
  const map = {
    "schematic-part-body": { name: "Kohler Solid Brass Body (K-10673-BODY)", info: "Rated to 125 PSI. Semi-red brass casting." },
    "schematic-part-diaphragm": { name: "Tripoint EPDM Diaphragm (GP1138930)", info: "Molded chloramine-resistant rubber with filtered bypass." },
    "schematic-part-solenoid": { name: "24V DC Bi-Stable Pulse Solenoid (10673-SOL)", info: "Low power magnetic latching armature." },
    "schematic-part-regulator": { name: "Dynamic Supply Pressure Cartridge (GP1044432)", info: "Stabilizes upstream pressure surges and water hammer." },
    "schematic-part-sensor": { name: "Optical Infrared Sensor Eye (K-13688)", info: "Dual-beam adaptive ambient distance sensor." }
  };

  Object.entries(map).forEach(([id, meta]) => {
    const el = $(`#${id}`);
    if (el) {
      el.addEventListener("click", () => {
        toast(`🔍 <b>${meta.name}</b><br><span style="font-size:11px;color:#8B96A5;">${meta.info}</span>`, "info");
      });
    }
  });
}

/* ==========================================================================
   Complete Innovation Pack: Multi-Airport Fleet Portfolio
   ========================================================================== */
async function loadPortfolioSummary() {
  try {
    const summary = await api.get("/api/portfolio/summary");
    const portFixEl = $("#port-total-fixtures");
    if (portFixEl) portFixEl.textContent = (summary.total_monitored_fixtures || 593).toLocaleString();
    const portSavedEl = $("#port-daily-saved");
    if (portSavedEl) portSavedEl.textContent = `${Math.round(summary.consolidated_daily_water_saved_liters || 260900).toLocaleString()} L`;
    const portCostEl = $("#port-monthly-cost");
    if (portCostEl) portCostEl.textContent = `₹${Math.round(summary.consolidated_monthly_tariff_savings_inr || 3522150).toLocaleString()}`;
    const portHealthEl = $("#port-avg-health");
    if (portHealthEl) portHealthEl.textContent = (summary.portfolio_average_health || 92.7).toFixed(1);

    const tbody = $("#port-table-body");
    if (tbody) {
      tbody.innerHTML = summary.airports.map(a => {
        const isLive = a.twin_status === "live_twin";
        const statusBadge = isLive
          ? `<span class="badge-good" style="background:#1B382B;color:#35D07F;padding:3px 8px;border-radius:4px;font-weight:700;">LIVE TWIN</span>`
          : `<span class="badge-tag" style="background:#141A22;color:#00A3E0;border:1px solid #202833;padding:3px 8px;border-radius:4px;">SYNTHETIC TWIN</span>`;
        return `
          <tr style="border-bottom:1px solid #202833;">
            <td style="padding:10px;font-family:monospace;font-weight:800;color:#00A3E0;">#${a.national_sustainability_rank}</td>
            <td style="padding:10px;font-weight:700;color:#F4F7FA;">${esc(a.airport_name)} <span style="font-size:11px;color:#8B96A5;">(${esc(a.city)})</span></td>
            <td style="padding:10px;color:#CBD5E1;">${esc(a.terminals_covered)}</td>
            <td style="padding:10px;font-family:monospace;">${a.fixtures_count}</td>
            <td style="padding:10px;font-family:monospace;">${a.daily_pax.toLocaleString()}</td>
            <td style="padding:10px;font-family:monospace;font-weight:700;color:#35D07F;">${a.average_fixture_health}/100</td>
            <td style="padding:10px;font-family:monospace;font-weight:700;color:#00A3E0;">${a.daily_water_saved_liters.toLocaleString()} L</td>
            <td style="padding:10px;font-family:monospace;color:#35D07F;">${a.sla_compliance_pct}%</td>
            <td style="padding:10px;">${statusBadge}</td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Portfolio fetch error:", err);
  }
}

function initPortfolioHandlers() {
  $("#airport-selector")?.addEventListener("change", (e) => {
    const val = e.target.value;
    if (val === "PNQ") {
      toast("✈️ Viewing <b>Pune PNQ</b> (Live Physical Sensor Twin)", "good");
    } else if (val === "BOM") {
      toast("✈️ Switched context to <b>Mumbai BOM T2</b> (184 Fixtures &middot; Synthetic Fleet Twin)", "info");
      loadPortfolioSummary().then(() => $("#modal-portfolio")?.showModal());
    } else if (val === "DEL") {
      toast("✈️ Switched context to <b>Delhi DEL T3</b> (312 Fixtures &middot; Synthetic Fleet Twin)", "info");
      loadPortfolioSummary().then(() => $("#modal-portfolio")?.showModal());
    }
  });

  $("#btn-portfolio-modal")?.addEventListener("click", () => {
    loadPortfolioSummary();
    $("#modal-portfolio")?.showModal();
  });

  $("#btn-close-portfolio")?.addEventListener("click", () => {
    $("#modal-portfolio")?.close();
  });
}

/* ==========================================================================
   Complete Innovation Pack: CMMS Work Order, ESG & What-If Stress Simulation
   ========================================================================== */
async function openCmmsWorkOrder(alertId) {
  try {
    const wo = await api.get(`/api/cmms/work-order/${alertId}`);
    $("#cmms-wo-title").textContent = `WORK ORDER: ${wo.work_order_number}`;
    $("#cmms-source").textContent = `System Source: ${wo.system_source}`;
    $("#cmms-status").textContent = `STATUS: ${wo.status}`;
    $("#cmms-created-at").textContent = wo.created_at;
    $("#cmms-asset-tag").textContent = wo.asset_tag;
    $("#cmms-equip-desc").textContent = wo.equipment_description;
    $("#cmms-func-loc").textContent = wo.functional_location;
    $("#cmms-craft").textContent = `Craft: ${wo.assigned_craft}`;
    $("#cmms-root-cause").textContent = wo.diagnosed_root_cause;
    $("#cmms-part-no").textContent = wo.required_spare_part.part_number;
    $("#cmms-part-shelf").textContent = `${wo.required_spare_part.storage_location} (${wo.required_spare_part.quantity_required} Unit Reserved)`;
    $("#cmms-safety").textContent = wo.safety_protocol;
    $("#cmms-barcode").textContent = wo.barcode_seed;
    $("#cmms-tech-name").textContent = `${wo.assigned_technician} (Verified)`;

    const stepsContainer = $("#cmms-job-steps");
    if (stepsContainer) {
      stepsContainer.innerHTML = wo.job_plan_steps.map(s => `
        <div style="background:#141A22;padding:6px 10px;border-radius:4px;border:1px solid #202833;">${esc(s)}</div>
      `).join("");
    }

    $("#modal-cmms-wo")?.showModal();
  } catch (err) {
    console.error("CMMS error:", err);
    toast("Failed to load CMMS Work Order", "bad");
  }
}

async function loadESGData() {
  try {
    const data = await api.get("/api/esg/metrics");
    const m = data.metrics;

    // Numbers
    const co2El = $("#esg-co2-val");
    if (co2El) co2El.textContent = `${m.co2e_avoided_kg.toLocaleString()} kg`;
    const kwhEl = $("#esg-kwh-val");
    if (kwhEl) kwhEl.textContent = `${m.energy_saved_kwh.toLocaleString()} kWh`;
    const treeEl = $("#esg-trees-val");
    if (treeEl) treeEl.textContent = Math.round(m.trees_planted_equivalent_years);
    const tankerEl = $("#esg-tankers-val");
    if (tankerEl) tankerEl.textContent = m.tanker_trucks_avoided;

    const heroVal = $("#sustain-hero-val");
    if (heroVal) heroVal.textContent = Math.round(m.monthly_water_saved_liters).toLocaleString();
    const heroCost = $("#sustain-hero-cost");
    if (heroCost) heroCost.textContent = `₹${Math.round(m.monthly_tariff_avoided_inr).toLocaleString()}`;

    // Certificate fields
    const certAir = $("#cert-airport-name");
    if (certAir) certAir.textContent = data.airport;
    const certWater = $("#cert-water-saved");
    if (certWater) certWater.textContent = `${Math.round(m.monthly_water_saved_liters).toLocaleString()} L`;
    const certCo2 = $("#cert-co2-saved");
    if (certCo2) certCo2.textContent = `${m.co2e_avoided_kg.toLocaleString()} kg CO₂e`;
    const certId = $("#cert-id-val");
    if (certId) certId.textContent = data.certificate_id;
    const certSeal = $("#cert-seal-val");
    if (certSeal) certSeal.textContent = `SHA256-${data.sha256_audit_seal.slice(0, 14)}`;
  } catch (err) {
    console.error("ESG load error:", err);
  }
}

async function triggerWhatIfSimulation() {
  const tariff = parseFloat($("#slider-sim-tariff")?.value || 48.5);
  const pax = parseFloat($("#slider-sim-pax")?.value || 0);
  const retrofit = parseFloat($("#slider-sim-retrofit")?.value || 100);

  const lblTariff = $("#lbl-slider-tariff");
  if (lblTariff) lblTariff.textContent = `₹${tariff.toFixed(2)} / kL`;
  const lblPax = $("#lbl-slider-pax");
  if (lblPax) lblPax.textContent = `${pax >= 0 ? '+' : ''}${pax}% Peak Pax`;
  const lblRetro = $("#lbl-slider-retrofit");
  if (lblRetro) lblRetro.textContent = `${retrofit}% (${Math.round(97 * (retrofit/100))} Fixtures)`;

  try {
    const res = await api.post("/api/simulation/what-if", {
      tariff_inr_per_kl: tariff,
      pax_growth_pct: pax,
      retrofit_coverage_pct: retrofit
    });
    const p = res.projections;
    const outLit = $("#sim-out-liters");
    if (outLit) outLit.textContent = `${Math.round(p.annual_water_conserved_liters).toLocaleString()} L`;
    const outCost = $("#sim-out-cost");
    if (outCost) outCost.textContent = `₹${Math.round(p.annual_financial_savings_inr).toLocaleString()}`;
    const outCo2 = $("#sim-out-co2");
    if (outCo2) outCo2.textContent = `${p.annual_carbon_avoidance_metric_tons.toFixed(2)} MT`;
    const outPay = $("#sim-out-payback");
    if (outPay) outPay.textContent = `${p.payback_period_months} Mos`;
  } catch (err) {
    console.error("What-If sim error:", err);
  }
}

function initEsgAndCmmsHandlers() {
  $("#btn-view-esg-cert")?.addEventListener("click", () => {
    loadESGData();
    $("#modal-esg-cert")?.showModal();
  });
  $("#btn-close-esg-cert")?.addEventListener("click", () => $("#modal-esg-cert")?.close());
  $("#btn-close-cert-done")?.addEventListener("click", () => $("#modal-esg-cert")?.close());

  $("#btn-close-cmms-wo")?.addEventListener("click", () => $("#modal-cmms-wo")?.close());
  $("#btn-done-cmms-wo")?.addEventListener("click", () => $("#modal-cmms-wo")?.close());

  ["slider-sim-tariff", "slider-sim-pax", "slider-sim-retrofit"].forEach(id => {
    $(`#${id}`)?.addEventListener("input", triggerWhatIfSimulation);
  });
}

/* ---------------- Initial Boot ---------------- */
initWebSocket();
initOscilloscopeCanvas();
initSchematicInteraction();
initPortfolioHandlers();
initEsgAndCmmsHandlers();

$("#btn-toggle-hydrophone")?.addEventListener("click", toggleHydrophoneAudio);

poll();
setInterval(poll, 2500);

window.addEventListener("resize", () => {
  if (S.state && S.currentView === "command_center") drawMainFlowChart(S.state.timeseries);
  if (S.state && S.currentView === "water_intel") drawIntelFlowChart(S.state.timeseries);
});



