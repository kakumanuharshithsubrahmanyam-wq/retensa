/* ============================================================
   RETENSA — App Logic
   ============================================================ */

const state = {
  currentPage: "overview",
  selectedCustomerId: CUSTOMERS[0].id,
  explorer: { page: 1, pageSize: 10, search: "", risk: "", value: "", minProb: "", sort: "prob-desc" },
  actionStatuses: {}, // id -> status override
  simulator: null,
};

/* ---------- Utility: icons ---------- */
const ICONS = {
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>',
  flame: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z"/></svg>',
  percent: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M19 5L5 19M6.5 6.5a2.5 2.5 0 105 0 2.5 2.5 0 00-5 0zM12.5 17.5a2.5 2.5 0 105 0 2.5 2.5 0 00-5 0z"/></svg>',
  target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>',
};

/* ============================================================
   Router
   ============================================================ */

const PAGE_IDS = ["overview", "customers", "risk-intelligence", "customer-intelligence", "action-center", "simulator", "ai-assistant", "reports"];

function navigateTo(pageId, opts = {}) {
  if (!PAGE_IDS.includes(pageId)) pageId = "overview";
  state.currentPage = pageId;

  PAGE_IDS.forEach((id) => {
    const el = document.getElementById("page-" + id);
    if (el) el.hidden = id !== pageId;
  });

  document.querySelectorAll(".nav-item[data-page]").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === pageId);
  });

  closeMobileSidebar();
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });

  if (pageId === "overview") renderOverview();
  if (pageId === "customers") renderExplorer();
  if (pageId === "risk-intelligence") renderRiskIntelligence();
  if (pageId === "customer-intelligence") renderCustomerIntelligence(opts.customerId || state.selectedCustomerId);
  if (pageId === "action-center") renderActionCenter();
  if (pageId === "simulator") renderSimulatorPage(opts.customerId || state.selectedCustomerId);
  if (pageId === "ai-assistant") renderAssistantIfEmpty();
}

function handleHashRoute() {
  const hash = (location.hash || "#overview").replace("#", "");
  navigateTo(hash);
}

window.addEventListener("hashchange", handleHashRoute);

document.addEventListener("click", (e) => {
  const navTarget = e.target.closest("[data-nav]");
  if (navTarget) {
    e.preventDefault();
    location.hash = navTarget.dataset.nav;
  }
});

/* ============================================================
   Sidebar / mobile
   ============================================================ */

const appShell = document.getElementById("appShell");
const sidebar = document.getElementById("sidebar");
const sidebarScrim = document.getElementById("sidebarScrim");

document.getElementById("sidebarToggle").addEventListener("click", () => {
  appShell.classList.toggle("sidebar-collapsed");
});

document.getElementById("mobileMenuBtn").addEventListener("click", () => {
  sidebar.classList.add("mobile-open");
  sidebarScrim.style.display = "block";
});
sidebarScrim.addEventListener("click", closeMobileSidebar);

function closeMobileSidebar() {
  sidebar.classList.remove("mobile-open");
  sidebarScrim.style.display = "none";
}

/* ============================================================
   Toasts
   ============================================================ */

function showToast(message) {
  const stack = document.getElementById("toastStack");
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `${ICONS.check}<span>${message}</span>`;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.25s ease";
    setTimeout(() => el.remove(), 260);
  }, 3200);
}

/* ============================================================
   Animated counters
   ============================================================ */

function animateCounter(el, target, opts = {}) {
  const duration = 900;
  const start = performance.now();
  const decimals = opts.decimals || 0;
  const suffix = opts.suffix || "";
  const prefix = opts.prefix || "";
  function tick(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = target * eased;
    el.textContent = prefix + value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* ============================================================
   Shared render helpers
   ============================================================ */

function riskBadge(risk) {
  return `<span class="badge badge-${risk.toLowerCase()}">${risk}</span>`;
}

function customerStatus(c) {
  return state.actionStatuses[c.id] || c.status;
}

/* ============================================================
   PAGE: Overview
   ============================================================ */

function renderOverview() {
  const kpiGrid = document.getElementById("kpiGrid");
  const kpis = [
    { label: "TOTAL CUSTOMERS", value: KPI_DATA.totalCustomers, icon: ICONS.users, trend: KPI_DATA.totalCustomersTrend, up: true },
    { label: "HIGH RISK", value: KPI_DATA.highRisk, icon: ICONS.alert, trend: KPI_DATA.highRiskTrend, up: false },
    { label: "CRITICAL RISK", value: KPI_DATA.criticalRisk, icon: ICONS.flame, trend: KPI_DATA.criticalRiskTrend, up: false },
    { label: "AVG CHURN PROBABILITY", value: KPI_DATA.avgChurnProbability, suffix: "%", icon: ICONS.percent, trend: KPI_DATA.avgChurnTrend, up: true, decimals: 1 },
    { label: "RETENTION OPPORTUNITIES", value: KPI_DATA.retentionOpportunities, icon: ICONS.target, trend: KPI_DATA.retentionOpportunitiesTrend, up: true },
  ];
  kpiGrid.innerHTML = kpis.map((k, i) => `
    <div class="card kpi-card">
      <div class="kpi-top">
        <div class="kpi-icon">${k.icon}</div>
        <span class="kpi-trend ${k.up ? "trend-up" : "trend-down"}">${k.trend}</span>
      </div>
      <div class="kpi-value" id="kpiVal${i}">0</div>
      <div class="kpi-label">${k.label}</div>
    </div>
  `).join("");
  kpis.forEach((k, i) => {
    animateCounter(document.getElementById("kpiVal" + i), k.value, { suffix: k.suffix || "", decimals: k.decimals || 0 });
  });

  renderDonut("riskDonutChart");

  const total = Object.values(RISK_SUMMARY).reduce((a, b) => a + b, 0);
  document.getElementById("riskSummaryList").innerHTML = ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((r) => `
    <div class="risk-row">
      <span class="risk-dot dot-${r.toLowerCase()}"></span>
      <span class="risk-name">${r.charAt(0) + r.slice(1).toLowerCase()}</span>
      <span class="risk-count">${RISK_SUMMARY[r].toLocaleString()}</span>
    </div>
  `).join("");

  renderTrendLine("overviewTrendChart", "30D");
  setupChipToggle("trendToggle", (range) => renderTrendLine("overviewTrendChart", range));

  document.getElementById("driverList").innerHTML = CHURN_DRIVERS.map((d) => `
    <div class="driver-row">
      <div class="driver-row-top"><span class="name">${d.name}</span><span class="pct">${d.value}%</span></div>
      <div class="driver-track"><div class="driver-fill" style="width:${d.value * 2.6}%"></div></div>
    </div>
  `).join("");

  const topOpportunities = [...CUSTOMERS].sort((a, b) => b.opportunityScore - a.opportunityScore).slice(0, 4);
  document.getElementById("opportunityMini").innerHTML = topOpportunities.map((c) => `
    <div class="risk-row">
      <span class="risk-dot dot-${c.risk.toLowerCase()}"></span>
      <span class="risk-name">${c.id} · ${c.primaryCause}</span>
      <span class="risk-count">${c.opportunityScore}/100</span>
    </div>
  `).join("");

  const priority = CUSTOMERS.slice(0, 8);
  document.getElementById("priorityTableBody").innerHTML = priority.map((c) => `
    <tr data-nav="customer-intelligence" data-customer="${c.id}">
      <td class="cust-id">${c.id}</td>
      <td class="mono">${c.probability.toFixed(1)}%</td>
      <td>${riskBadge(c.risk)}</td>
      <td>${c.primaryCause}</td>
      <td><span class="value-tag">${c.customerValue}</span></td>
      <td class="mono">${c.opportunityScore}/100</td>
      <td><button class="btn btn-sm" data-nav="customer-intelligence" data-customer="${c.id}">View</button></td>
    </tr>
  `).join("");
  bindTableRowNav("priorityTableBody");
}

function setupChipToggle(containerId, onSelect) {
  const container = document.getElementById(containerId);
  container.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => {
      container.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onSelect(btn.dataset.range);
    };
  });
}

function bindTableRowNav(tbodyId) {
  const tbody = document.getElementById(tbodyId);
  tbody.querySelectorAll("tr[data-customer]").forEach((row) => {
    row.addEventListener("click", (e) => {
      const id = row.dataset.customer;
      state.selectedCustomerId = id;
      location.hash = "customer-intelligence";
      if (state.currentPage === "customer-intelligence") renderCustomerIntelligence(id);
    });
  });
}

/* ============================================================
   PAGE: Customer Risk Explorer
   ============================================================ */

function getFilteredCustomers() {
  let list = [...CUSTOMERS];
  const { search, risk, value, minProb, sort } = state.explorer;
  if (search) list = list.filter((c) => c.id.toLowerCase().includes(search.toLowerCase()));
  if (risk) list = list.filter((c) => c.risk === risk);
  if (value) list = list.filter((c) => c.customerValue === value);
  if (minProb) list = list.filter((c) => c.probability >= Number(minProb));

  switch (sort) {
    case "prob-asc": list.sort((a, b) => a.probability - b.probability); break;
    case "opp-desc": list.sort((a, b) => b.opportunityScore - a.opportunityScore); break;
    case "tenure-asc": list.sort((a, b) => a.tenure - b.tenure); break;
    default: list.sort((a, b) => b.probability - a.probability);
  }
  return list;
}

function renderExplorer() {
  const list = getFilteredCustomers();
  const { page, pageSize } = state.explorer;
  const totalPages = Math.max(1, Math.ceil(list.length / pageSize));
  const clampedPage = Math.min(page, totalPages);
  state.explorer.page = clampedPage;
  const pageItems = list.slice((clampedPage - 1) * pageSize, clampedPage * pageSize);

  document.getElementById("explorerTableBody").innerHTML = pageItems.map((c) => `
    <tr data-nav="customer-intelligence" data-customer="${c.id}">
      <td class="cust-id">${c.id}</td>
      <td class="mono">${c.probability.toFixed(1)}%</td>
      <td>${riskBadge(c.risk)}</td>
      <td class="mono">${c.tenure} mo</td>
      <td class="mono">$${c.monthlyCharges}</td>
      <td>${c.contract}</td>
      <td>${c.primaryCause}</td>
      <td class="mono">${c.opportunityScore}/100</td>
      <td><button class="btn btn-sm" data-nav="customer-intelligence" data-customer="${c.id}">View</button></td>
    </tr>
  `).join("") || `<tr><td colspan="9" style="text-align:center;color:var(--text-tertiary);padding:26px;">No customers match these filters.</td></tr>`;
  bindTableRowNav("explorerTableBody");

  document.getElementById("explorerPagination").innerHTML = `
    <span>Page ${clampedPage} of ${totalPages} · ${list.length} customers</span>
    <button class="page-btn" id="prevPageBtn" ${clampedPage <= 1 ? "disabled" : ""} aria-label="Previous page">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
    </button>
    <button class="page-btn" id="nextPageBtn" ${clampedPage >= totalPages ? "disabled" : ""} aria-label="Next page">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
    </button>
  `;
  const prevBtn = document.getElementById("prevPageBtn");
  const nextBtn = document.getElementById("nextPageBtn");
  if (prevBtn) prevBtn.onclick = () => { state.explorer.page--; renderExplorer(); };
  if (nextBtn) nextBtn.onclick = () => { state.explorer.page++; renderExplorer(); };
}

document.getElementById("explorerSearch").addEventListener("input", (e) => {
  state.explorer.search = e.target.value; state.explorer.page = 1; renderExplorer();
});
document.getElementById("riskFilter").addEventListener("change", (e) => {
  state.explorer.risk = e.target.value; state.explorer.page = 1; renderExplorer();
});
document.getElementById("valueFilter").addEventListener("change", (e) => {
  state.explorer.value = e.target.value; state.explorer.page = 1; renderExplorer();
});
document.getElementById("probFilter").addEventListener("change", (e) => {
  state.explorer.minProb = e.target.value; state.explorer.page = 1; renderExplorer();
});
document.getElementById("sortFilter").addEventListener("change", (e) => {
  state.explorer.sort = e.target.value; renderExplorer();
});

/* Global top-bar search filters the explorer too */
document.getElementById("globalSearch").addEventListener("input", (e) => {
  const val = e.target.value.trim();
  if (val && state.currentPage !== "customers") {
    location.hash = "customers";
  }
  state.explorer.search = val;
  state.explorer.page = 1;
  document.getElementById("explorerSearch").value = val;
  if (state.currentPage === "customers") renderExplorer();
});

/* ============================================================
   PAGE: Risk Intelligence
   ============================================================ */

function renderRiskIntelligence() {
  renderRiskDistBar("ri_riskDist");
  renderProbDistribution("ri_probDist");
  renderHorizontalBar("ri_drivers", CHURN_DRIVERS.map((d) => d.name), CHURN_DRIVERS.map((d) => d.value), CHART_COLORS.accent);
  renderHorizontalBar("ri_contract", RISK_BY_CONTRACT.map((d) => d.label), RISK_BY_CONTRACT.map((d) => d.value), CHART_COLORS.high);
  renderHorizontalBar("ri_tenure", RISK_BY_TENURE.map((d) => d.label), RISK_BY_TENURE.map((d) => d.value), CHART_COLORS.medium);
  renderHorizontalBar("ri_value", RISK_BY_VALUE.map((d) => d.label), RISK_BY_VALUE.map((d) => d.value), CHART_COLORS.accent);
  renderHorizontalBar("ri_charges", RISK_BY_CHARGES.map((d) => d.label), RISK_BY_CHARGES.map((d) => d.value), CHART_COLORS.critical);
  setupChipToggle("riskIntelToggle", () => { /* visual only — data is portfolio level */ });
}

/* ============================================================
   PAGE: Customer Intelligence
   ============================================================ */

function findCustomer(id) {
  return CUSTOMERS.find((c) => c.id === id) || CUSTOMERS[0];
}

function renderCustomerIntelligence(id) {
  const c = findCustomer(id);
  state.selectedCustomerId = c.id;

  document.getElementById("ciCustomerId").textContent = "Customer " + c.id;
  const badge = document.getElementById("ciRiskBadge");
  badge.className = "badge badge-" + c.risk.toLowerCase();
  badge.textContent = c.risk + " RISK";

  document.getElementById("ciProbNum").textContent = c.probability.toFixed(1) + "%";
  document.getElementById("ciConfidence").textContent = c.confidence;
  const circumference = 452;
  const offset = circumference - (circumference * c.probability) / 100;
  const ring = document.getElementById("ciRingFill");
  ring.style.stroke = riskColor(c.risk);
  requestAnimationFrame(() => {
    ring.style.transition = "stroke-dashoffset 0.8s cubic-bezier(.2,.7,.3,1)";
    ring.style.strokeDashoffset = offset;
  });

  const cards = [
    { lbl: "Tenure", val: c.tenure + " months" },
    { lbl: "Monthly Charges", val: "$" + c.monthlyCharges },
    { lbl: "Contract", val: c.contract },
    { lbl: "Support Requests", val: c.supportRequests },
    { lbl: "Usage Trend", val: "↓ " + Math.abs(c.engagementTrend) + "%", neg: true },
    { lbl: "Customer Value", val: c.customerValue },
    { lbl: "Retention Opportunity", val: c.opportunityScore + "/100" },
    { lbl: "Primary Cause", val: c.primaryCause },
  ];
  document.getElementById("ciProfileCards").innerHTML = cards.map((k) => `
    <div class="card profile-mini">
      <div class="lbl">${k.lbl}</div>
      <div class="val ${k.neg ? "neg" : ""}">${k.val}</div>
    </div>
  `).join("");

  document.getElementById("ciPositiveContrib").innerHTML = c.contributions.positive.map((f) => `
    <div class="contrib-row">
      <span class="contrib-name">${f.name}</span>
      <div class="contrib-bar-track"><div class="contrib-bar-fill pos" style="width:${Math.min(100, f.value * 2.6)}%"></div></div>
      <span class="contrib-val">+${f.value}%</span>
    </div>
  `).join("");
  document.getElementById("ciNegativeContrib").innerHTML = c.contributions.negative.map((f) => `
    <div class="contrib-row">
      <span class="contrib-name">${f.name}</span>
      <div class="contrib-bar-track"><div class="contrib-bar-fill neg" style="width:${Math.min(100, Math.abs(f.value) * 2.6)}%"></div></div>
      <span class="contrib-val">${f.value}%</span>
    </div>
  `).join("");

  const topFactor = c.contributions.positive[0];
  document.getElementById("ciExplanationText").innerHTML =
    `This customer has a <mark>${c.risk.toLowerCase()} predicted churn risk</mark> primarily because of ` +
    `<mark>${topFactor.name.toLowerCase()}</mark>, a ${c.contract.toLowerCase()} contract, and ${c.tenure} months of tenure. ` +
    (c.supportRequests > 3 ? `Repeated support interactions (${c.supportRequests} requests) further increase the predicted risk.` : `Engagement patterns and billing history further shape the predicted risk.`);

  // Root cause diagram
  document.getElementById("rcMid").textContent = causeToLabel(c.primaryCause);
  document.getElementById("rcFactorA").textContent = c.primaryCause === "Support" ? `${c.supportRequests} Support Requests` : `$${c.monthlyCharges} Monthly Charges`;
  document.getElementById("rcFactorB").textContent = `${c.contract} Contract`;
  document.getElementById("rcSecondary").textContent = "Secondary cause: " + secondaryCause(c.primaryCause);

  const diagram = document.getElementById("rootCauseDiagram");
  diagram.classList.remove("in-view");
  observeRootCause(diagram);

  // Strategy panel
  const strat = strategyFor(c);
  document.getElementById("stratPriority").textContent = strat.priority;
  document.getElementById("stratPrimary").textContent = strat.primary;
  document.getElementById("stratSecondary").textContent = strat.secondary;
  document.getElementById("stratTiming").textContent = strat.timing;

  document.getElementById("campaignArea").innerHTML = "";
}

function riskColor(risk) {
  return { LOW: CHART_COLORS.low, MEDIUM: CHART_COLORS.medium, HIGH: CHART_COLORS.high, CRITICAL: CHART_COLORS.critical }[risk];
}

function causeToLabel(cause) {
  const map = {
    Pricing: "PRICE SENSITIVITY", Support: "SUPPORT FRICTION", Engagement: "DISENGAGEMENT",
    Contract: "CONTRACT FLEXIBILITY", "Usage Drop": "DECLINING USAGE", Onboarding: "EARLY LIFECYCLE RISK",
  };
  return map[cause] || "PRICE SENSITIVITY";
}
function secondaryCause(cause) {
  return cause === "Support" ? "Pricing Sensitivity" : "Support Friction";
}
function strategyFor(c) {
  const primaryMap = {
    Pricing: "Annual Plan Incentive", Support: "Priority Support Escalation", Engagement: "Personalized Re-engagement Offer",
    Contract: "Contract Flexibility Review", "Usage Drop": "Usage Coaching Session", Onboarding: "Guided Onboarding Check-in",
  };
  return {
    priority: c.risk === "CRITICAL" ? "CRITICAL" : c.risk === "HIGH" ? "HIGH" : "MEDIUM",
    primary: primaryMap[c.primaryCause] || "Annual Plan Incentive",
    secondary: c.supportRequests > 3 ? "Priority Support" : "Loyalty Discount",
    timing: c.risk === "CRITICAL" ? "Within 48 Hours" : c.risk === "HIGH" ? "Within 7 Days" : "Within 14 Days",
  };
}

function observeRootCause(el) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        el.classList.add("in-view");
        io.disconnect();
      }
    });
  }, { threshold: 0.3 });
  io.observe(el);
}

/* ---------- Generate AI Action Plan modal ---------- */

document.getElementById("generatePlanBtn").addEventListener("click", () => {
  const c = findCustomer(state.selectedCustomerId);
  const strat = strategyFor(c);
  document.getElementById("modalBody").innerHTML = `
    <div class="modal-section"><div class="lbl">Customer summary</div>
      <div class="val">${c.id} — ${c.probability.toFixed(1)}% predicted churn probability, ${c.risk} risk, ${c.customerValue} customer value.</div></div>
    <div class="modal-section"><div class="lbl">Risk</div>
      <div class="val">${c.risk} — primarily driven by ${c.primaryCause.toLowerCase()}.</div></div>
    <div class="modal-section"><div class="lbl">Root causes</div>
      <ul>${c.contributions.positive.map((f) => `<li>${f.name} (+${f.value}%)</li>`).join("")}</ul></div>
    <div class="modal-section"><div class="lbl">Recommended actions</div>
      <ul><li>${strat.primary}</li><li>${strat.secondary}</li><li>Schedule a check-in ${strat.timing.toLowerCase()}</li></ul></div>
    <div class="modal-section"><div class="lbl">Communication strategy</div>
      <div class="val">Lead with the ${strat.primary.toLowerCase()}, referencing tenure and loyalty. Keep tone consultative rather than transactional.</div></div>
    <div class="modal-section"><div class="lbl">Priority</div><div class="val">${strat.priority}</div></div>
  `;
  openModal();
});

function openModal() { document.getElementById("planModal").classList.add("open"); }
function closeModal() { document.getElementById("planModal").classList.remove("open"); }
document.getElementById("closeModalBtn").addEventListener("click", closeModal);
document.getElementById("planModal").addEventListener("click", (e) => {
  if (e.target.id === "planModal") closeModal();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

/* ---------- Campaign generator (on Customer Intelligence page) ---------- */

document.getElementById("generateCampaignBtn").addEventListener("click", () => {
  const c = findCustomer(state.selectedCustomerId);
  const area = document.getElementById("campaignArea");
  area.innerHTML = `<div class="loading-strip"><span class="spinner"></span> Generating retention campaign for ${c.id}…</div>`;
  setTimeout(() => renderCampaign(area, c), 900);
});

function renderCampaign(area, c) {
  const strat = strategyFor(c);
  area.innerHTML = `
    <div class="campaign-output mt-12">
      <div class="card campaign-block">
        <div class="block-label">Email</div>
        <div class="subject">Subject: A plan built around how you use your account</div>
        <div class="body-text">Hi there,

We noticed your usage patterns have shifted recently, and we want to make sure your plan still fits. Based on your account, switching to ${strat.primary.toLowerCase()} could reduce your monthly cost while keeping the features you rely on.

Reply here or book 10 minutes with our team this week — we'll walk through the numbers together.

— The Retensa Customer Success Team</div>
        <div class="campaign-block-actions">
          <button class="btn btn-sm copy-btn" data-copy="email">Copy</button>
          <button class="btn btn-sm regen-btn">Regenerate</button>
        </div>
      </div>

      <div class="card campaign-block">
        <div class="block-label">SMS</div>
        <div class="body-text">Hi — this is Retensa Support. We'd like to offer you a better plan based on your usage. Reply YES for a callback, or STOP to opt out.</div>
        <div class="campaign-block-actions">
          <button class="btn btn-sm copy-btn" data-copy="sms">Copy</button>
          <button class="btn btn-sm regen-btn">Regenerate</button>
        </div>
      </div>

      <div class="card campaign-block">
        <div class="block-label">Support call script</div>
        <ul class="step-list">
          <li><span class="step-num">1</span>Understand the customer's current concern and confirm account details.</li>
          <li><span class="step-num">2</span>Walk through their current plan usage and monthly cost.</li>
          <li><span class="step-num">3</span>Present ${strat.primary.toLowerCase()} as a tailored alternative.</li>
          <li><span class="step-num">4</span>Confirm next action and timeline (${strat.timing.toLowerCase()}).</li>
        </ul>
        <div class="campaign-block-actions">
          <button class="btn btn-sm copy-btn" data-copy="script">Copy</button>
          <button class="btn btn-sm regen-btn">Regenerate</button>
        </div>
      </div>
    </div>
  `;
  area.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", () => showToast("Copied to clipboard"));
  });
  area.querySelectorAll(".regen-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      area.innerHTML = `<div class="loading-strip"><span class="spinner"></span> Regenerating…</div>`;
      setTimeout(() => renderCampaign(area, c), 800);
    });
  });
}

/* ============================================================
   PAGE: What-If Simulator
   ============================================================ */

function contractRiskFactor(contract) {
  return { "Month-to-month": 1, "One year": 0.55, "Two year": 0.32 }[contract];
}
function supportRiskFactor(level) {
  return { Basic: 1.08, Standard: 1, Priority: 0.72 }[level];
}
function engagementRiskFactor(level) {
  return { Low: 1.15, Medium: 1, High: 0.78 }[level];
}

function computeSimProbability(profile) {
  let base = 28;
  base += (profile.charges - 19) * 0.42;
  base += Math.max(0, 30 - profile.tenure) * 1.05;
  base *= contractRiskFactor(profile.contract);
  base *= supportRiskFactor(profile.support);
  base *= engagementRiskFactor(profile.engagement);
  return Math.max(3, Math.min(98, Math.round(base * 10) / 10));
}

function renderSimulatorPage(customerId) {
  const select = document.getElementById("simCustomerSelect");
  if (!select.dataset.bound) {
    select.innerHTML = CUSTOMERS.map((c) => `<option value="${c.id}">${c.id} — ${c.risk}</option>`).join("");
    select.dataset.bound = "1";
    select.addEventListener("change", () => renderSimulatorPage(select.value));
  }
  select.value = customerId;

  const c = findCustomer(customerId);
  state.simulator = {
    base: { charges: c.monthlyCharges, tenure: c.tenure, contract: c.contract, support: "Standard", engagement: "Low" },
    current: { charges: c.monthlyCharges, tenure: c.tenure, contract: c.contract, support: "Standard", engagement: "Low" },
    currentProb: c.probability,
  };

  setToggleGroup("simContractToggle", c.contract);
  setToggleGroup("simSupportToggle", "Standard");
  setToggleGroup("simEngagementToggle", "Low");
  document.getElementById("simCharges").value = c.monthlyCharges;
  document.getElementById("simTenure").value = c.tenure;
  updateSimLabels();

  document.getElementById("simInsightBox").innerHTML = `<b>Intervention insight —</b> Adjust the controls and press Simulate to see how the model's simulated prediction responds.`;
  renderSimRings(c.probability, c.probability);
}

function setToggleGroup(containerId, value) {
  const container = document.getElementById(containerId);
  container.querySelectorAll(".toggle-pill").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.value === value);
  });
}

["simContractToggle", "simSupportToggle", "simEngagementToggle"].forEach((id) => {
  document.getElementById(id).addEventListener("click", (e) => {
    const btn = e.target.closest(".toggle-pill");
    if (!btn) return;
    setToggleGroup(id, btn.dataset.value);
    updateSimLabels();
  });
});
document.getElementById("simCharges").addEventListener("input", updateSimLabels);
document.getElementById("simTenure").addEventListener("input", updateSimLabels);

function currentSimProfile() {
  return {
    contract: document.querySelector("#simContractToggle .toggle-pill.active").dataset.value,
    charges: Number(document.getElementById("simCharges").value),
    tenure: Number(document.getElementById("simTenure").value),
    support: document.querySelector("#simSupportToggle .toggle-pill.active").dataset.value,
    engagement: document.querySelector("#simEngagementToggle .toggle-pill.active").dataset.value,
  };
}

function updateSimLabels() {
  document.getElementById("simContractLabel").textContent = document.querySelector("#simContractToggle .toggle-pill.active").dataset.value;
  document.getElementById("simChargesLabel").textContent = "$" + document.getElementById("simCharges").value;
  document.getElementById("simTenureLabel").textContent = document.getElementById("simTenure").value;
  document.getElementById("simSupportLabel").textContent = document.querySelector("#simSupportToggle .toggle-pill.active").dataset.value;
  document.getElementById("simEngagementLabel").textContent = document.querySelector("#simEngagementToggle .toggle-pill.active").dataset.value;
}

function renderSimRings(currentPct, simPct) {
  const circumference = 314;
  const curRing = document.getElementById("simCurrentRing");
  const simRing = document.getElementById("simSimulatedRing");
  curRing.style.transition = "stroke-dashoffset 0.6s ease";
  simRing.style.transition = "stroke-dashoffset 0.6s ease";
  curRing.style.strokeDashoffset = circumference - (circumference * currentPct) / 100;
  simRing.style.strokeDashoffset = circumference - (circumference * simPct) / 100;
  simRing.style.stroke = simPct <= currentPct ? CHART_COLORS.low : CHART_COLORS.critical;
  document.getElementById("simCurrentNum").textContent = currentPct.toFixed(0) + "%";
  document.getElementById("simSimulatedNum").textContent = simPct.toFixed(0) + "%";
}

document.getElementById("simulateBtn").addEventListener("click", () => {
  const c = findCustomer(state.selectedCustomerId);
  const profile = currentSimProfile();
  const simProb = computeSimProbability(profile);
  const delta = Math.round(simProb - c.probability);

  renderSimRings(c.probability, simProb);

  const banner = document.getElementById("simRiskChangeBanner");
  banner.textContent = `Risk change: ${delta > 0 ? "+" : ""}${delta} percentage points`;
  banner.classList.toggle("negative", delta > 0);

  const changedParts = [];
  if (profile.contract !== c.contract) changedParts.push(`the simulated contract from ${c.contract.toLowerCase()} to ${profile.contract.toLowerCase()}`);
  if (profile.support !== "Standard") changedParts.push(`support level to ${profile.support.toLowerCase()}`);
  if (profile.engagement !== "Low") changedParts.push(`engagement to ${profile.engagement.toLowerCase()}`);
  if (profile.charges !== c.monthlyCharges) changedParts.push(`monthly charges to $${profile.charges}`);
  const changeText = changedParts.length ? changedParts.join(", ") : "the simulated profile";

  document.getElementById("simInsightBox").innerHTML =
    `<b>Intervention insight —</b> Changing ${changeText} moves the model's simulated prediction ${delta <= 0 ? "down" : "up"} by ${Math.abs(delta)} percentage points under this scenario. This is a simulated model prediction, not a proof of causal effect.`;
});

document.getElementById("resetSimBtn").addEventListener("click", () => {
  renderSimulatorPage(state.selectedCustomerId);
});

/* ============================================================
   PAGE: Retention Action Center
   ============================================================ */

function actionForCause(cause) {
  const map = {
    Pricing: "Offer annual plan incentive", Support: "Escalate to priority support", Engagement: "Send re-engagement offer",
    Contract: "Propose flexible contract terms", "Usage Drop": "Schedule usage coaching call", Onboarding: "Trigger onboarding check-in",
  };
  return map[cause] || "Offer annual plan incentive";
}

function renderActionCenter() {
  const list = [...CUSTOMERS].filter((c) => c.risk === "CRITICAL" || c.risk === "HIGH").slice(0, 12);
  const tbody = document.getElementById("actionTableBody");
  tbody.innerHTML = list.map((c) => {
    const status = customerStatus(c);
    return `
      <tr>
        <td class="cust-id">${c.id}</td>
        <td>${riskBadge(c.risk)}</td>
        <td>${c.primaryCause}</td>
        <td>${actionForCause(c.primaryCause)}</td>
        <td><span class="value-tag">${c.risk === "CRITICAL" ? "HIGH" : "MEDIUM"}</span></td>
        <td><span class="status-pill status-${status.replace(" ", "")}" data-status-cell="${c.id}">${status}</span></td>
        <td>
          <div class="row-actions">
            <button class="btn btn-sm" data-nav="customer-intelligence" data-customer="${c.id}">View</button>
            <button class="btn btn-sm" data-plan="${c.id}">Plan</button>
            ${status === "New" ? `<button class="btn btn-sm" data-progress="${c.id}">In Progress</button>` : ""}
            ${status !== "Completed" ? `<button class="btn btn-sm" data-complete="${c.id}">Complete</button>` : ""}
          </div>
        </td>
      </tr>`;
  }).join("");

  tbody.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      state.selectedCustomerId = btn.dataset.customer;
      location.hash = "customer-intelligence";
    });
  });
  tbody.querySelectorAll("[data-plan]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const c = findCustomer(btn.dataset.plan);
      const strat = strategyFor(c);
      document.getElementById("modalBody").innerHTML = `
        <div class="modal-section"><div class="lbl">Customer summary</div><div class="val">${c.id} — ${c.probability.toFixed(1)}% predicted churn probability, ${c.risk} risk.</div></div>
        <div class="modal-section"><div class="lbl">Root cause</div><div class="val">${c.primaryCause}</div></div>
        <div class="modal-section"><div class="lbl">Recommended actions</div><ul><li>${strat.primary}</li><li>${strat.secondary}</li></ul></div>
        <div class="modal-section"><div class="lbl">Priority</div><div class="val">${strat.priority}</div></div>`;
      openModal();
    });
  });
  tbody.querySelectorAll("[data-progress]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.actionStatuses[btn.dataset.progress] = "In Progress";
      showToast(`${btn.dataset.progress} marked in progress`);
      renderActionCenter();
    });
  });
  tbody.querySelectorAll("[data-complete]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.actionStatuses[btn.dataset.complete] = "Completed";
      showToast(`${btn.dataset.complete} marked complete`);
      renderActionCenter();
    });
  });
}

/* ============================================================
   PAGE: AI Assistant
   ============================================================ */

let assistantRendered = false;

function renderAssistantIfEmpty() {
  if (assistantRendered) return;
  assistantRendered = true;
  appendChatMessage("ai", AI_RESPONSES.default.text);
}

function appendChatMessage(role, text, recommendation) {
  const scroll = document.getElementById("chatScroll");
  const el = document.createElement("div");
  el.className = "chat-msg " + role;
  el.innerHTML = `
    <div class="chat-avatar ${role}">${role === "ai" ? "AI" : "You"}</div>
    <div>
      <div class="chat-bubble">${text}</div>
      ${recommendation ? `<div class="chat-rec"><div class="lbl">${recommendation.title}</div><div class="txt">${recommendation.body}</div></div>` : ""}
    </div>
  `;
  scroll.appendChild(el);
  scroll.scrollTop = scroll.scrollHeight;
}

function handleUserPrompt(text) {
  appendChatMessage("user", escapeHtml(text));
  const key = text.trim().toLowerCase().replace(/[?.!]+$/, "");
  const match = AI_RESPONSES[key] || matchLooseKey(key) || AI_RESPONSES.default;
  setTimeout(() => appendChatMessage("ai", match.text, match.recommendation), 400);
}

function matchLooseKey(key) {
  const found = Object.keys(AI_RESPONSES).find((k) => k !== "default" && (key.includes(k) || k.includes(key)));
  return found ? AI_RESPONSES[found] : null;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

document.getElementById("promptChips").addEventListener("click", (e) => {
  const chip = e.target.closest(".prompt-chip");
  if (chip) handleUserPrompt(chip.dataset.prompt);
});
document.getElementById("chatSendBtn").addEventListener("click", sendChatInput);
document.getElementById("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChatInput();
});
function sendChatInput() {
  const input = document.getElementById("chatInput");
  const val = input.value.trim();
  if (!val) return;
  handleUserPrompt(val);
  input.value = "";
}

/* ============================================================
   PAGE: Reports
   ============================================================ */

document.getElementById("generateReportBtn").addEventListener("click", (e) => {
  const btn = e.target;
  btn.disabled = true;
  btn.textContent = "Generating…";
  document.getElementById("reportReadyBanner").classList.add("hidden-el");
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = "Generate report";
    document.getElementById("reportReadyBanner").classList.remove("hidden-el");
    showToast("Retention intelligence report generated");
  }, 1300);
});
document.getElementById("viewReportBtn").addEventListener("click", () => {
  showToast("Opening report preview");
});

/* ============================================================
   Init
   ============================================================ */

handleHashRoute();
if (!location.hash) navigateTo("overview");
