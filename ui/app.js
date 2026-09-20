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

/* ---------------- Polling Loop ---------------- */
async function poll() {
  try {
    S.state = await api.get("/api/state");
    S.lastTickTs = Date.now();
    $("#telemetry-tick").textContent = "0.2s ago";
    render();
  } catch (err) {
    $("#telemetry-tick").textContent = "connecting...";
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
  const a = S.state.alerts.find(x => x.id === alertId) || S.state.alerts[0];
  if (!a) return;

  const t = a.telemetry || {};
  const ticket = S.state.tickets.find(x => x.alert_id === a.id);
  const dev = S.state.devices[a.device_id];

  // Header titles
  $("#ws-prio").textContent = a.priority;
  $("#ws-prio").style.color = a.priority === "P1" ? "var(--critical)" : "var(--warning)";
  $("#ws-kind").textContent = a.kind.replaceAll("_", " ").toUpperCase();
  $("#ws-location").textContent = `${esc(a.zone)} · Fixture ${a.device_id} (${esc(a.device_type)})`;

  // Telemetry metrics
  $("#ws-flow").textContent = `${(t.flow_lpm ?? dev?.flow_lpm ?? 0).toFixed(2)} L/min`;
  $("#ws-occ").textContent = t.occupancy ?? dev?.occupancy ?? 0;
  $("#ws-flush").textContent = t.flush_count ?? dev?.flush_count ?? 0;
  $("#ws-pressure").textContent = `${(dev?.pressure_bar ?? 3.0).toFixed(1)} bar`;
  $("#ws-sensor-conf").textContent = `${Math.round((a.sensor_confidence || 0.96) * 100)}%`;
  $("#ws-health").textContent = `${dev?.health_score || 45}/100`;

  // Water Impact
  const daily = a.estimated_daily_loss_liters;
  const monthly = a.estimated_monthly_loss_liters;
  $("#ws-daily-loss").textContent = `${fmtL(daily)} L`;
  $("#ws-monthly-loss").textContent = `${fmtL(monthly)} L`;
  const cost = Math.round((monthly / 1000.0) * 48.5);
  $("#ws-cost-loss").textContent = `Cost impact: INR ${fmtL(cost)} / month (Commercial Tariff @ ₹48.50/kL)`;

  // Root cause & Sensor Fusion factors
  $("#ws-fusion-confidence").textContent = `${Math.round((a.leak_confidence || 0.95) * 100)}% Confidence`;
  $("#ws-root-cause").textContent = a.root_cause || "Flush Valve Diaphragm Tear";
  $("#ws-diagnosis-text").textContent = a.diagnosis;

  const factorsEl = $("#ws-fusion-factors");
  factorsEl.innerHTML = `
    <div class="fusion-factor-item"><span>Flow Anomaly</span><b class="alert-color">30%</b></div>
    <div class="fusion-factor-item"><span>Occ Mismatch</span><b class="alert-color">20%</b></div>
    <div class="fusion-factor-item"><span>Flush Mismatch</span><b class="warn-color">15%</b></div>
    <div class="fusion-factor-item"><span>Historical Baseline Drift</span><b>15%</b></div>
    <div class="fusion-factor-item"><span>Supply Pressure Drop</span><b>10%</b></div>
    <div class="fusion-factor-item"><span>Sensor Fidelity</span><b class="good-color">${Math.round((a.sensor_confidence || 0.96) * 100)}%</b></div>
  `;

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

  if (a.status === "RESOLVED") {
    idleBox.style.display = "none";
    runningBox.style.display = "none";
    doneBox.style.display = "block";
    $("#ws-verif-note").textContent = a.resolution_note || "Fixture repaired. Telemetry normalized to zero-leak baseline.";
  } else {
    idleBox.style.display = "block";
    runningBox.style.display = "none";
    doneBox.style.display = "none";
  }

  const resolveBtn = $("#ws-btn-resolve");
  if (resolveBtn) {
    resolveBtn.onclick = async () => {
      idleBox.style.display = "none";
      runningBox.style.display = "flex";
      $("#ws-verif-step").textContent = "Technician stopcock isolated. Verifying flow decay...";

      setTimeout(async () => {
        $("#ws-verif-step").textContent = "Replacing cartridge seal & normalizing line pressure...";
      }, 1200);

      setTimeout(async () => {
        try {
          const res = await api.post(`/alerts/${a.id}/resolve`);
          runningBox.style.display = "none";
          doneBox.style.display = "block";
          $("#ws-verif-note").textContent = `✓ Repaired. Telemetry back to baseline. Conserved ${fmtL(res.saved_month_liters)} L/month.`;
          toast(`✅ ${a.id} verified resolved — ${fmtL(res.saved_month_liters)} L/mo added to ledger`, "good");
          poll();
        } catch (err) {
          runningBox.style.display = "none";
          idleBox.style.display = "block";
          toast("Verification failed", "bad");
        }
      }, 2400);
    };
  }

  drawIncidentFlowChart(dev?.history || []);
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

  const pad = { l: 28, r: 8, t: 10, b: 18 };
  const maxFlow = Math.max(3.5, ...raw.map(p => p.flow || 0));
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
  raw.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.flow || 0)) : ctx.moveTo(x(i), y(p.flow || 0))));
  ctx.strokeStyle = "#FF4D5A";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Points
  raw.forEach((p, i) => {
    ctx.beginPath();
    ctx.arc(x(i), y(p.flow || 0), 2.5, 0, Math.PI * 2);
    ctx.fillStyle = p.flow > 0.2 ? "#FF4D5A" : "#35D07F";
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

/* ---------------- Guided Demo Walkthrough ---------------- */
$("#btn-guided-demo")?.addEventListener("click", () => {
  S.demoTimers.forEach(clearTimeout);
  S.demoTimers = [];
  const t = (ms, fn) => S.demoTimers.push(setTimeout(fn, ms));

  toast("🎬 Guided demo started — switching to Command Center overview", "info");
  switchView("command_center");

  t(1200, async () => {
    await api.post("/simulate/continuous-leak");
    toast("⚡ <b>FV-182</b> in Terminal 2 / Restroom 14: Flush valve diaphragm tear injected!", "bad");
    poll();
  });

  t(6500, () => {
    toast("🔍 Anomaly confirmed by Multi-Sensor Fusion! Inspecting incident...", "info");
    const leak = (S.state?.alerts || []).find(a => a.device_id === "FV-182" && a.status === "OPEN");
    if (leak) openIncidentWorkspace(leak.id);
  });

  t(14000, () => {
    toast("🔧 Technician Arjun Sharma dispatched. Initiating resolution verification...", "info");
    const resBtn = $("#ws-btn-resolve");
    if (resBtn) resBtn.click();
  });

  t(19000, () => {
    toast("🌱 Resolution verified! Viewing Sustainability Ledger...", "good");
    switchView("sustainability");
  });

  t(24000, () => {
    toast("🎬 Demo complete! Detect → Diagnose → Dispatch → Conserve", "good");
  });
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

/* ---------------- Initial Boot ---------------- */
poll();
setInterval(poll, 2500);
window.addEventListener("resize", () => {
  if (S.state && S.currentView === "command_center") drawMainFlowChart(S.state.timeseries);
  if (S.state && S.currentView === "water_intel") drawIntelFlowChart(S.state.timeseries);
});
