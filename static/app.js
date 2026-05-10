"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const VIEW_TITLES = {
  dashboard: { title: "Today", subtitle: "Your watched companies, recent runs, and what to do next." },
  companies: { title: "Companies", subtitle: "Add companies, find their career pages, and check for new roles." },
  jobs: { title: "Discovered jobs", subtitle: "Roles found on company sites. Review before importing." },
  brief: { title: "AI Brief", subtitle: "Prepare a provider-neutral brief and analyze fit with your own AI." },
  settings: { title: "Settings", subtitle: "AI provider, account security, backup, and scan history." },
  admin: { title: "Admin", subtitle: "Tester accounts. Visible to admins only." },
};

const ERROR_COPY = {
  unauthorized: "Please sign in again.",
  csrf_failed: "Session expired — refresh and try again.",
  admin_required: "That action is admin-only.",
  rate_limited: "Too many failed sign-ins. Wait a few minutes and retry.",
  invalid_login: "Email or password is incorrect.",
  invalid_email: "That doesn't look like a valid email.",
  password_too_short: "Password must be at least 12 characters.",
  invalid_role: "Role must be tester or admin.",
  email_already_exists: "An account with that email already exists.",
  last_admin_required: "You can't deactivate or demote the only admin.",
  invalid_current_password: "Current password is incorrect.",
  registration_closed: "Registration is closed. Ask an admin to create your account.",
  unsupported_export_schema: "That backup file is from a different version.",
  self_modify_forbidden: "Admins can't change their own role or active status.",
  raw_secret_not_allowed: "Use the env var name (e.g. OPENAI_API_KEY), not the secret value.",
  unknown_provider: "Pick a provider from the list.",
  unsupported_invocation_mode: "That mode isn't available for this provider.",
};

const SCAN_STATUS_COPY = {
  queued: "Queued",
  running: "Checking now…",
  completed: "Roles found",
  completed_with_errors: "Checked with notes",
  blocked_or_unavailable: "Could not check this page safely",
  blocked_or_captcha: "Page is behind a CAPTCHA / bot block",
  blocked_by_robots: "Page is disallowed by robots.txt",
  restricted_platform: "We don't scan that platform — paste jobs manually instead",
  missing_career_page: "Add the career page URL first",
  failed: "Scan failed",
  already_running: "A scan is already in progress",
  nothing_to_scan: "Nothing to check yet",
};

/* ---------- i18n lookup helper ---------- */

function t(key, fallback) {
  const dict = (typeof state !== "undefined" && state && state.translations) || {};
  return dict[key] || fallback || key;
}

function translateError(code) {
  if (!code) return null;
  const translated = t("errors." + code, null);
  if (translated && translated !== "errors." + code) return translated;
  return ERROR_COPY[code] || null;
}

function translateScanStatus(code) {
  if (!code) return null;
  const translated = t("scanStatus." + code, null);
  if (translated && translated !== "scanStatus." + code) return translated;
  return SCAN_STATUS_COPY[code] || null;
}

const state = {
  view: "jobs",
  companies: [],
  discoveredJobs: [],
  importedJobs: [],
  scans: [],
  discoveryRuns: [],
  summary: {},
  aiProvider: {},
  aiProviderOptions: [],
  watchlistSchedule: {},
  auth: { authenticated: false, user: null, registrationOpen: false },
  adminUsers: [],
  analysisBrief: null,
  selectedCompanyId: null,
  selectedImportedJobId: null,
  queueFilter: "all",
  queueSort: "discovered",
  queueSourceFilter: {},
  queueSelected: new Set(),
  companyFilter: "",
  locale: "en",
  translations: {},
  theme: "dark",
  pollTimer: null,
};

const companyTemplate = $("#companyTemplate");
const jobTemplate = $("#jobTemplate");
const historyTemplate = $("#historyTemplate");
const activityTemplate = $("#activityTemplate");

/* ---------- Status / toast / confirm ---------- */

function setStatus(text, mode = "") {
  const el = $("#networkState");
  if (!el) return;
  el.textContent = text;
  el.className = `status-pill ${mode}`.trim();
}

function showToast(message, kind = "info", timeout = 4500) {
  const root = $("#toastRoot");
  if (!root) return;
  const node = document.createElement("div");
  node.className = `toast ${kind}`.trim();
  node.textContent = message;
  root.appendChild(node);
  setTimeout(() => node.remove(), timeout);
}

function friendlyError(rawMessage, code) {
  const byCode = translateError(code);
  if (byCode) return byCode;
  const byMessage = translateError(rawMessage);
  if (byMessage) return byMessage;
  return rawMessage || t("errors.generic", "Something went wrong.");
}

function confirmDialog({ title = "Confirm", body = "", confirmLabel = "Confirm", danger = false } = {}) {
  return new Promise((resolve) => {
    const root = $("#confirmDialog");
    $("#confirmTitle").textContent = title;
    $("#confirmBody").textContent = body;
    const okBtn = $("#confirmOk");
    okBtn.textContent = confirmLabel;
    okBtn.classList.toggle("btn-danger", danger);
    okBtn.classList.toggle("btn-primary", !danger);
    root.hidden = false;
    okBtn.focus();
    const cleanup = (result) => {
      root.hidden = true;
      okBtn.removeEventListener("click", onOk);
      $("#confirmCancel").removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onKey);
      resolve(result);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onKey = (event) => {
      if (event.key === "Escape") cleanup(false);
      if (event.key === "Enter") cleanup(true);
    };
    okBtn.addEventListener("click", onOk);
    $("#confirmCancel").addEventListener("click", onCancel);
    document.addEventListener("keydown", onKey);
  });
}

/* ---------- API ---------- */

async function api(path, options = {}) {
  setStatus("Working", "busy");
  const method = options.method || "GET";
  let response;
  try {
    response = await fetch(path, {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(method !== "GET" && state.auth.user?.csrfToken ? { "X-CSRF-Token": state.auth.user.csrfToken } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (networkError) {
    setStatus("Offline", "error");
    throw new Error(friendlyError(networkError.message));
  }
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthenticatedState();
      renderAuth();
    }
    const code = payload.error?.code;
    const message = friendlyError(payload.error?.message, code);
    setStatus("Error", "error");
    const error = new Error(message);
    error.code = code;
    throw error;
  }
  setStatus("Ready");
  return payload;
}

/* ---------- State ---------- */

function isAdmin() {
  return Boolean(state.auth.user?.isAdmin || state.auth.user?.role === "admin");
}

function selectedCompany() {
  return state.companies.find((c) => c.id === state.selectedCompanyId) || null;
}

function absorbBootstrap(bootstrap) {
  if (!bootstrap) return;
  state.companies = bootstrap.companies || [];
  state.discoveredJobs = bootstrap.discoveredJobs || [];
  state.importedJobs = bootstrap.importedJobs || [];
  state.scans = bootstrap.scans || [];
  state.discoveryRuns = bootstrap.discoveryRuns || [];
  state.summary = bootstrap.summary || {};
  state.aiProvider = bootstrap.aiProvider || {};
  state.aiProviderOptions = bootstrap.aiProviderOptions || [];
  state.watchlistSchedule = bootstrap.watchlistSchedule || {};
  state.bootstrapQuotas = bootstrap.quotas || null;
  state.savedSearches = bootstrap.savedSearches || [];
  state.watchlistTemplates = bootstrap.watchlistTemplates || [];
  state.billingPlans = bootstrap.billingPlans || [];
  state.personas = bootstrap.personas || [];
  state.workspaces = bootstrap.workspaces || state.workspaces || [];
  state.activeWorkspaceId = bootstrap.activeWorkspaceId || null;
  state.profile = bootstrap.profile || { personaId: "healthcare-management", targetRoles: [], languages: [], cvText: "", locale: "en", theme: "dark" };
  if (state.profile.locale && state.profile.locale !== state.locale) {
    loadLocale(state.profile.locale);
  }
  applyTheme(state.profile.theme || "dark");
  state.applicationStatuses = bootstrap.applicationStatuses || ["saved", "interested", "applied", "interview", "rejected", "archived"];
  state.onboarding = bootstrap.onboarding || { steps: [], progress: { completed: 0, total: 0 }, firstRunWizard: false };
  // Open the first-run wizard when the server says we should AND it
  // isn't already on screen. After the user dismisses or finishes, the
  // server flips firstRunWizard to false and we won't reopen it.
  if (state.onboarding?.firstRunWizard) {
    queueMicrotask(() => openFirstRunWizard());
  }
  if (!state.selectedCompanyId && state.companies.length) {
    state.selectedCompanyId = state.companies[0].id;
  }
  if (state.selectedCompanyId && !state.companies.some((c) => c.id === state.selectedCompanyId)) {
    state.selectedCompanyId = state.companies[0]?.id || null;
  }
  if (state.selectedImportedJobId && !state.importedJobs.some((j) => j.id === state.selectedImportedJobId)) {
    state.selectedImportedJobId = state.importedJobs[0]?.id || null;
  }
  if (!state.selectedImportedJobId && state.importedJobs.length) {
    state.selectedImportedJobId = state.importedJobs[0].id;
  }
}

function clearAuthenticatedState() {
  state.auth = { authenticated: false, user: null, registrationOpen: state.auth.registrationOpen };
  state.companies = [];
  state.discoveredJobs = [];
  state.importedJobs = [];
  state.scans = [];
  state.discoveryRuns = [];
  state.summary = {};
  state.aiProvider = {};
  state.aiProviderOptions = [];
  state.watchlistSchedule = {};
  state.adminUsers = [];
  state.analysisBrief = null;
  state.selectedCompanyId = null;
  state.selectedImportedJobId = null;
  state.queueFilter = "all";
  state.companyFilter = "";
  state.savedSearches = [];
  state.watchlistTemplates = [];
  state.billingPlans = [];
  state.personas = [];
  state.profile = { personaId: "healthcare-management", targetRoles: [], languages: [], cvText: "" };
  state.onboarding = { steps: [], progress: { completed: 0, total: 0 } };
  if (state.pollTimer) {
    clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }
}

/* ---------- Init ---------- */

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || "";
}

function showOnly(viewId) {
  const ids = ["authGate", "appShell", "forgotPasswordView", "resetPasswordView", "acceptInviteView"];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.hidden = id !== viewId;
  }
}

async function init() {
  const path = window.location.pathname || "/";
  if (path === "/accept-invite") {
    await initAcceptInvite();
    return;
  }
  if (path === "/reset-password") {
    await initResetPassword();
    return;
  }
  if (path === "/forgot-password") {
    showOnly("forgotPasswordView");
    return;
  }
  try {
    const payload = await api("/api/auth/status");
    state.auth = {
      authenticated: Boolean(payload.authenticated),
      user: payload.user,
      registrationOpen: Boolean(payload.registrationOpen),
    };
    renderAuth();
    if (state.auth.authenticated) {
      await load();
    }
  } catch (error) {
    setStatus("Error", "error");
    showToast(error.message, "error");
  }
}

async function initAcceptInvite() {
  showOnly("acceptInviteView");
  const token = getQueryParam("token");
  const target = $("#acceptInviteTarget");
  const form = $("#acceptInviteForm");
  const message = $("#acceptInviteMessage");
  message.textContent = "";
  if (!token) {
    target.textContent = "This invitation link is missing a token.";
    return;
  }
  try {
    const payload = await api(`/api/auth/accept-invite/${encodeURIComponent(token)}`);
    target.textContent = `Invitation for ${payload.invitation.email} (${payload.invitation.role}). Expires ${new Date(payload.invitation.expiresAt).toLocaleString()}.`;
    form.hidden = false;
    form.dataset.token = token;
  } catch (error) {
    target.textContent = error.message;
  }
}

async function initResetPassword() {
  showOnly("resetPasswordView");
  const token = getQueryParam("token");
  const target = $("#resetPasswordTarget");
  const form = $("#resetPasswordForm");
  const message = $("#resetPasswordMessage");
  message.textContent = "";
  if (!token) {
    target.textContent = "This reset link is missing a token.";
    return;
  }
  try {
    const payload = await api(`/api/auth/reset-password/${encodeURIComponent(token)}`);
    target.textContent = `Reset for ${payload.reset.email}. Link expires ${new Date(payload.reset.expiresAt).toLocaleString()}.`;
    form.hidden = false;
    form.dataset.token = token;
  } catch (error) {
    target.textContent = error.message;
  }
}

async function load() {
  const payload = await api("/api/bootstrap");
  absorbBootstrap(payload);
  render();
  if (isAdmin()) {
    try {
      await loadAdminUsers();
    } catch (error) {
      showToast(error.message, "error");
    }
  }
}

/* ---------- Routing ---------- */

function navigate(view) {
  if (!VIEW_TITLES[view]) view = "jobs";
  if (view === "admin" && !isAdmin()) view = "jobs";
  state.view = view;
  $$(".view").forEach((el) => {
    el.hidden = el.dataset.view !== view;
  });
  $$(".nav-item").forEach((btn) => {
    const active = btn.dataset.view === view;
    btn.setAttribute("aria-current", active ? "page" : "false");
  });
  const meta = VIEW_TITLES[view];
  $("#viewTitle").textContent = meta.title;
  $("#viewSubtitle").textContent = meta.subtitle;
  if (view === "brief") renderBrief();
  if (view === "settings") loadBilling();
  if (view === "admin" && isAdmin()) {
    loadAdminUsers().catch((error) => showToast(error.message, "error"));
    loadAdminTickets().catch(() => {});
    loadReadiness().catch(() => {});
    loadEmailStatus().catch(() => {});
  }
  logUiEvent("ui_nav", { view });
}

/* ---------- Render ---------- */

function render() {
  renderDashboard();
  renderOnboarding();
  renderTemplates();
  renderSavedSearches();
  renderCompanies();
  renderDetail();
  renderJobs();
  renderProvider();
  renderProfile();
  renderTotpCard();
  renderNotifySettings();
  renderPrivacyAudit();
  renderWorkspacePicker();
  renderHistory();
  renderImportedJobs();
  renderBriefSummary();
  renderApplicationForm();
  renderQuotaSummary();
  renderAdminUsers();
  renderBilling();
  $("#navCompanyCount").textContent = state.companies.length;
  const newCount = state.discoveredJobs.filter((j) => !j.imported_job_id).length;
  $("#navJobCount").textContent = newCount;
  scheduleRunPolling();
}

function renderAuth() {
  if (state.auth.authenticated) {
    showOnly("appShell");
  } else {
    showOnly("authGate");
  }
  $("#sidebarUser").hidden = !state.auth.authenticated;
  $("#sidebarUserEmail").textContent = state.auth.user?.email || "";
  $("#sidebarUserRole").textContent = isAdmin() ? "Admin" : "Tester";
  $$(".admin-only").forEach((el) => {
    el.hidden = !isAdmin();
  });
  $("#registerForm").hidden = !state.auth.registrationOpen;
  $("#authMessage").textContent = "";
  setStatus(state.auth.authenticated ? "Ready" : "Sign in");
  if (state.auth.authenticated) navigate(state.view);
}

function renderDashboard() {
  const watched = state.summary.companiesWatched ?? 0;
  const newJobs = state.summary.newDirectCompanyJobs ?? state.discoveredJobs.filter((j) => !j.imported_job_id).length;
  const setup = state.summary.companiesNeedingCareerPageSetup ?? state.companies.filter((c) => !c.career_page_url).length;
  const lastRun = state.summary.lastDiscoveryRunStatus || "—";
  $("#metricWatched").textContent = watched;
  $("#metricJobs").textContent = newJobs;
  $("#metricSetup").textContent = setup;
  $("#metricRun").textContent = translateScanStatus(lastRun) || (lastRun === "—" ? "—" : lastRun);

  $("#metricWatchedHint").textContent = watched ? `${watched} on your watchlist` : "Add a company to start";
  $("#metricJobsHint").textContent = newJobs ? `${newJobs} need review` : "Awaiting first scan";
  $("#metricSetupHint").textContent = setup ? `${setup} need career page URL` : "All set up";
  $("#metricRunHint").textContent = state.watchlistSchedule.lastRunAt
    ? `at ${new Date(state.watchlistSchedule.lastRunAt).toLocaleString()}`
    : "No scan recorded";

  let nextStep;
  if (state.companies.length === 0) {
    nextStep = "Add your first company. Use Suggestions if you'd like a curated list.";
  } else if (setup > 0) {
    nextStep = "A few companies still need a career page URL — open Companies to fix that.";
  } else if (newJobs > 0) {
    nextStep = `${newJobs} new role${newJobs === 1 ? "" : "s"} found. Review them in Discovered Jobs.`;
  } else if (state.companies.length && !state.summary.lastDiscoveryRunAt && !state.watchlistSchedule.lastRunAt) {
    nextStep = "Run your first scan with Check for new roles.";
  } else {
    nextStep = "All caught up. Add more companies or wait for the next scan.";
  }
  $("#nextStepText").textContent = nextStep;

  $("#scheduleEnabled").checked = Boolean(state.watchlistSchedule.enabled);
  $("#scheduleInterval").value = state.watchlistSchedule.intervalMinutes || 360;
  const lastRunAt = state.watchlistSchedule.lastRunAt
    ? new Date(state.watchlistSchedule.lastRunAt).toLocaleString()
    : "Never";
  $("#scheduleStatus").textContent = state.watchlistSchedule.enabled
    ? `Scheduled every ${state.watchlistSchedule.intervalMinutes || 360} minutes · last run ${lastRunAt}`
    : `Manual scans only · last run ${lastRunAt}`;

  const list = $("#recentActivity");
  list.replaceChildren();
  const items = [...state.discoveryRuns]
    .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))
    .slice(0, 5);
  if (!items.length) {
    list.append(emptyNode(t("dashboard.activity.empty", "No activity yet."), { icon: "list" }));
    return;
  }
  for (const run of items) {
    const company = state.companies.find((c) => c.id === run.company_id);
    const node = activityTemplate.content.firstElementChild.cloneNode(true);
    const status = translateScanStatus(run.status) || run.status;
    const isError = ["failed", "blocked_or_unavailable", "blocked_by_robots", "blocked_or_captcha", "restricted_platform", "missing_career_page"].includes(run.status);
    const isWarn = run.status === "completed_with_errors";
    if (isError) node.classList.add("error");
    else if (isWarn) node.classList.add("warn");
    node.querySelector(".activity-text").textContent = `${company?.name || "Unknown company"} — ${status}`;
    const ts = run.finished_at || run.created_at;
    node.querySelector(".activity-time").textContent = ts ? new Date(ts).toLocaleString() : "";
    list.append(node);
  }
}

function renderCompanies() {
  const list = $("#companyList");
  list.replaceChildren();
  const filtered = state.companies.filter((c) => {
    if (!state.companyFilter) return true;
    const haystack = `${c.name} ${c.sector || ""} ${c.website_url || ""}`.toLowerCase();
    return haystack.includes(state.companyFilter.toLowerCase());
  });
  if (!filtered.length) {
    if (state.companyFilter) {
      list.append(emptyNode(t("companies.empty.filtered", "No companies match your filter."), { icon: "search" }));
    } else {
      list.append(emptyNode(
        t("companies.empty.none", "Build a watchlist of employers you'd love to work for."),
        {
          icon: "company",
          ctaText: t("companies.empty.cta", "Add your first company"),
          onCta: () => document.getElementById("newCompanyBtn")?.click(),
        },
      ));
    }
    return;
  }
  for (const company of filtered) {
    const node = companyTemplate.content.firstElementChild.cloneNode(true);
    node.classList.toggle("active", company.id === state.selectedCompanyId);
    const status = node.querySelector(".company-status");
    if (!company.career_page_url) status.classList.add("needs-setup");
    else if (company.watch_enabled) status.classList.add("watching");
    node.querySelector(".company-title").textContent = company.name;
    const jobs = state.discoveredJobs.filter((j) => j.company_id === company.id).length;
    const watch = company.watch_enabled ? "Watching" : "Paused";
    const careerStatus = company.career_page_url ? "" : " · Needs career page";
    node.querySelector(".company-meta").textContent = `${company.sector || "Uncategorized"} · ${watch} · ${jobs} role${jobs === 1 ? "" : "s"}${careerStatus}`;
    node.addEventListener("click", () => {
      state.selectedCompanyId = company.id;
      render();
    });
    list.append(node);
  }
}

function renderDetail() {
  const company = selectedCompany();
  const empty = $("#companyEmptyState");
  const form = $("#detailForm");
  $("#findCareerBtn").disabled = !company;
  $("#scanBtn").disabled = !company;
  $("#extractHtmlBtn").disabled = !company;
  if (!company) {
    empty.hidden = false;
    form.hidden = true;
    $("#detailName").textContent = "Select a company";
    $("#detailMeta").textContent = "Pick a company on the left to see details.";
    $("#scanResult").textContent = "";
    return;
  }
  empty.hidden = true;
  form.hidden = false;
  $("#detailName").textContent = company.name;
  const careerStatus = company.career_page_url ? "Career page on file" : "Needs career page";
  $("#detailMeta").textContent = `${company.sector || "Uncategorized"} · ${careerStatus}`;
  $("#detailWebsite").value = company.website_url || "";
  $("#detailCareer").value = company.career_page_url || "";
  $("#detailSector").value = company.sector || "";
  $("#detailWatch").checked = Boolean(company.watch_enabled);
  $("#detailNotes").value = company.notes || "";
  $("#manualPageUrl").value = company.career_page_url || company.website_url || "";

  const lastScan = state.scans.find((s) => s.company_id === company.id);
  const activeRun = state.discoveryRuns.find(
    (r) => r.company_id === company.id && ["queued", "running"].includes(r.status),
  );
  if (activeRun) {
    $("#scanResult").textContent = `${translateScanStatus(activeRun.status) || activeRun.status}…`;
    return;
  }
  if (!lastScan) {
    $("#scanResult").textContent = "No scan recorded yet.";
    return;
  }
  const status = translateScanStatus(lastScan.status) || lastScan.status;
  const mergedTotal = (lastScan.errors || []).find((e) => e.code === "merged_sources_total");
  const mergedCount = mergedTotal ? mergedTotal.count : 0;
  const otherErrors = (lastScan.errors || []).filter(
    (e) => e.code !== "source_merged" && e.code !== "merged_sources_total",
  ).length;
  const parts = [
    status,
    `${lastScan.pages_checked} ${t("scanResult.pages", "page" + (lastScan.pages_checked === 1 ? "" : "s"))}`,
    `${lastScan.jobs_found} ${t("scanResult.newRoles", "new role" + (lastScan.jobs_found === 1 ? "" : "s"))}`,
  ];
  if (mergedCount > 0) {
    parts.push(`${mergedCount} ${t("scanResult.mergedSources", "source" + (mergedCount === 1 ? "" : "s") + " merged")}`);
  }
  if (otherErrors > 0) {
    parts.push(`${otherErrors} ${t("scanResult.notes", "note" + (otherErrors === 1 ? "" : "s"))}`);
  }
  $("#scanResult").textContent = parts.join(" · ");
}

function jobPrimarySource(job) {
  // bookmarklet-captured jobs carry their platform tag in structured_data.
  const captured = job.structured_data && job.structured_data.captured_via;
  if (typeof captured === "string" && captured) return captured;
  // career-page-scan jobs have a company and confidence > 0.
  if (job.company_id) return "direct";
  return "aggregator";
}

function jobMatchesSourceFilter(job) {
  const enabled = state.queueSourceFilter || {};
  // If the user hasn't toggled anything, all sources are enabled.
  if (Object.keys(enabled).length === 0) return true;
  const source = jobPrimarySource(job);
  // Group bookmarklet:* under one toggle each, allow generic toggle for "direct".
  if (source.startsWith("bookmarklet:")) return enabled[source] !== false;
  return enabled[source] !== false;
}

function renderQueueSourceFilters() {
  const wrap = document.getElementById("queueSourceFilters");
  if (!wrap) return;
  // Compute the full source set across the user's jobs.
  const sources = new Set();
  for (const job of state.discoveredJobs || []) {
    sources.add(jobPrimarySource(job));
  }
  // Strip non-label children (keep the leading "Sources:" span)
  while (wrap.children.length > 1) wrap.removeChild(wrap.lastChild);
  // Honor server-persisted hidden_sources if present.
  const hidden = new Set((state.profile?.hiddenSources) || []);
  for (const s of [...sources].sort()) {
    if (state.queueSourceFilter[s] === undefined) {
      state.queueSourceFilter[s] = !hidden.has(s);
    }
    const label = t(`queue.source.${s}`, s);
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip${state.queueSourceFilter[s] ? " active" : ""}`;
    chip.textContent = label;
    chip.title = s;
    chip.addEventListener("click", () => {
      state.queueSourceFilter[s] = !state.queueSourceFilter[s];
      try { localStorage.setItem("dj_queue_sources", JSON.stringify(state.queueSourceFilter)); } catch (_) {}
      // Persist server-side via UserProfile.hidden_sources.
      const hiddenList = Object.entries(state.queueSourceFilter)
        .filter(([, on]) => !on)
        .map(([k]) => k);
      api("/api/profile", { method: "POST", body: JSON.stringify({ hiddenSources: hiddenList }) }).catch(() => {});
      renderQueueSourceFilters();
      renderJobs();
    });
    wrap.append(chip);
  }
}

function renderQueueBulkBar() {
  const host = document.getElementById("queueBulkBar");
  if (!host) return;
  const n = state.queueSelected.size;
  if (n === 0) {
    host.hidden = true;
    return;
  }
  host.hidden = false;
  host.replaceChildren();
  const label = document.createElement("span");
  label.textContent = t("queue.bulk.count", "{n} selected").replace("{n}", String(n));
  const importBtn = document.createElement("button");
  importBtn.type = "button";
  importBtn.className = "btn btn-primary";
  importBtn.textContent = t("queue.bulk.import", "Import selected");
  importBtn.addEventListener("click", bulkImportSelected);
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "btn";
  dismiss.textContent = t("queue.bulk.dismiss", "Dismiss selected");
  dismiss.addEventListener("click", bulkDismissSelected);
  const clear = document.createElement("button");
  clear.type = "button";
  clear.className = "btn btn-ghost";
  clear.textContent = t("queue.bulk.clear", "Clear");
  clear.addEventListener("click", () => {
    state.queueSelected.clear();
    renderJobs();
  });
  host.append(label, importBtn, dismiss, clear);
}

async function bulkImportSelected() {
  const ids = Array.from(state.queueSelected);
  if (!ids.length) return;
  // Skip jobs already imported in the current state — server would error
  // anyway, and we want a tighter "imported N of M" count.
  const eligible = ids.filter((id) => {
    const job = state.discoveredJobs.find((j) => j.id === id);
    return job && !job.imported_job_id;
  });
  if (!eligible.length) {
    showToast(t("queue.bulk.nothingToImport", "Nothing new to import — all selected rows are already imported."), "info");
    return;
  }
  try {
    const payload = await api("/api/discovered-jobs/bulk-import", {
      method: "POST",
      body: JSON.stringify({ ids: eligible }),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    state.queueSelected.clear();
    const errors = (payload.outcomes || []).filter((o) => o.status !== "imported").length;
    const tpl = errors
      ? t("queue.bulk.imported.partial", "Imported {ok} of {total}. {err} skipped.")
        .replace("{ok}", String(payload.imported || 0))
        .replace("{total}", String(eligible.length))
        .replace("{err}", String(errors))
      : t("queue.bulk.imported", "Imported {n}.").replace("{n}", String(payload.imported || 0));
    showToast(tpl, errors ? "info" : "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function bulkDismissSelected() {
  const ids = Array.from(state.queueSelected);
  if (!ids.length) return;
  const terms = [];
  for (const id of ids) {
    const job = state.discoveredJobs.find((j) => j.id === id);
    if (!job) continue;
    if (job.title) terms.push(job.title);
    const company = (state.companies || []).find((c) => c.id === job.company_id);
    if (company?.name) terms.push(company.name);
  }
  if (!terms.length) return;
  try {
    const payload = await api("/api/profile", {
      method: "POST",
      body: JSON.stringify({ addDismissedTerms: terms }),
    });
    if (payload.profile) state.profile = payload.profile;
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    state.discoveredJobs = state.discoveredJobs.filter((j) => !state.queueSelected.has(j.id));
    state.queueSelected.clear();
    showToast(t("queue.bulk.dismissed", "{n} dismissed.").replace("{n}", String(ids.length)), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderJobs() {
  const list = $("#jobsQueue");
  list.replaceChildren();
  renderQueueSourceFilters();
  renderQueueBulkBar();
  let jobs = [...state.discoveredJobs];
  if (state.queueFilter === "new") jobs = jobs.filter((j) => !j.imported_job_id);
  if (state.queueFilter === "imported") jobs = jobs.filter((j) => j.imported_job_id);
  jobs = jobs.filter(jobMatchesSourceFilter);
  if (!jobs.length) {
    const wrap = document.createElement("div");
    wrap.className = "empty queue-empty";
    const icon = document.createElement("div");
    icon.className = "queue-empty-icon";
    icon.innerHTML = '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="22" cy="22" r="12"/><path d="M31 31 L40 40"/><circle cx="22" cy="22" r="3.5" fill="currentColor" stroke="none" opacity="0.6"/></svg>';
    const title = document.createElement("p");
    title.className = "queue-empty-title";
    title.textContent =
      state.queueFilter === "new"
        ? t("queue.empty.new", "Nothing new yet. Want us to look further?")
        : state.queueFilter === "imported"
        ? t("queue.empty.imported", "No saved roles yet — pick one from the queue.")
        : t("queue.empty.all", "Your queue is empty. Tell us what you want.");
    const sub = document.createElement("p");
    sub.className = "muted";
    sub.textContent = t("queue.empty.sub", "We watch Indeed, StepStone, Arbeitnow, Muse, Bundesagentur and more. Set up a saved search and we'll keep checking daily.");
    wrap.append(icon, title, sub);
    if (state.queueFilter !== "imported") {
      const cta = document.createElement("button");
      cta.type = "button";
      cta.className = "btn btn-primary";
      cta.textContent = t("queue.empty.cta", "Find me jobs");
      cta.addEventListener("click", () => {
        navigate("dashboard");
        // Auto-focus the search input + scroll it into view so the
        // user lands ready to type, not hunting for the field.
        setTimeout(() => {
          const input = document.getElementById("findJobsQuery");
          if (input) {
            input.scrollIntoView({ block: "center", behavior: "smooth" });
            input.focus();
          }
        }, 60);
      });
      wrap.append(cta);
    }
    list.append(wrap);
    return;
  }
  if (state.queueSort === "fit") {
    jobs.sort((a, b) => (b.auto_fit_score || -1) - (a.auto_fit_score || -1));
  } else {
    jobs.sort((a, b) => (b.discovered_at || "").localeCompare(a.discovered_at || ""));
  }
  for (const job of jobs) {
    const company = state.companies.find((c) => c.id === job.company_id);
    const node = jobTemplate.content.firstElementChild.cloneNode(true);
    node.classList.toggle("imported", Boolean(job.imported_job_id));
    node.classList.toggle("highlighted", Boolean(job.__highlight));
    // Bulk-select checkbox. Goes on the left of the title.
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "queue-select";
    checkbox.checked = state.queueSelected.has(job.id);
    checkbox.title = t("queue.bulk.checkboxTitle", "Select for bulk action");
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.queueSelected.add(job.id);
      else state.queueSelected.delete(job.id);
      renderQueueBulkBar();
    });
    const main = node.querySelector(".job-main");
    if (main) main.prepend(checkbox);
    node.querySelector("h3").textContent = job.title;
    const subParts = [company?.name, job.location].filter(Boolean);
    const freshIso = jobEffectiveFreshness(job);
    const freshRel = relativeTimeFromIso(freshIso);
    if (freshRel) subParts.push(freshRel);
    node.querySelector(".job-sub").textContent = subParts.join(" · ") || "Direct company source";
    // "New" dot if the freshness is within the last 24 hours.
    if (freshIso) {
      const ms = Date.now() - new Date(freshIso).getTime();
      if (ms < 24 * 3600 * 1000 && ms >= 0) {
        const titleEl = node.querySelector("h3");
        const dot = document.createElement("span");
        dot.className = "fresh-dot";
        dot.title = t("queue.freshTooltip", "New since yesterday");
        dot.setAttribute("aria-label", "New");
        titleEl.prepend(dot);
      }
    }
    node.querySelector(".job-source").textContent = `${t("queue.from", "From")} ${shortUrl(job.source_url)}`;
    const score = Math.round((job.confidence_score || 0) * 100);
    const conf = node.querySelector(".confidence");
    conf.textContent = `${score}% confidence`;
    if (score < 40) conf.classList.add("bad");
    else if (score < 65) conf.classList.add("low");

    if (job.auto_fit_score != null) {
      const fit = Math.round(job.auto_fit_score * 100);
      const fitTag = document.createElement("span");
      fitTag.className = `tag ${fit >= 70 ? "success" : fit >= 45 ? "warn" : ""}`.trim();
      fitTag.textContent = `Fit ${fit}`;
      if (job.auto_fit_reason) fitTag.title = job.auto_fit_reason;
      conf.after(fitTag);
    }

    // Source badge — primary source + "found in N more places" expansion.
    const primarySource = jobPrimarySource(job);
    const sourceTag = document.createElement("span");
    sourceTag.className = "tag source-tag";
    sourceTag.textContent = primarySource;
    conf.after(sourceTag);
    const alsoSeen = job.also_seen_at || {};
    const extraHosts = Object.keys(alsoSeen).filter((h) => h);
    if (extraHosts.length > 0) {
      const moreTag = document.createElement("button");
      moreTag.type = "button";
      moreTag.className = "tag muted source-also";
      const labelTpl = t("queue.foundInN", "Found in {count} more");
      moreTag.textContent = labelTpl.replace("{count}", String(extraHosts.length));
      moreTag.setAttribute("aria-expanded", "false");
      sourceTag.after(moreTag);
      const panel = buildAlsoSeenPanel(alsoSeen);
      moreTag.after(panel);
      moreTag.addEventListener("click", (event) => {
        event.preventDefault();
        const open = panel.hidden === false;
        panel.hidden = open;
        moreTag.setAttribute("aria-expanded", String(!open));
      });
    }

    const importBtn = node.querySelector(".import-btn");
    const briefBtn = node.querySelector(".brief-btn");
    const analyzeBtn = node.querySelector(".analyze-btn");
    importBtn.textContent = job.imported_job_id ? "Imported" : "Import";
    importBtn.disabled = Boolean(job.imported_job_id);
    importBtn.addEventListener("click", () => importJob(job.id));
    briefBtn.addEventListener("click", () => {
      state.selectedImportedJobId = job.imported_job_id;
      navigate("brief");
      prepareBrief(job.imported_job_id);
    });
    analyzeBtn.addEventListener("click", () => {
      state.selectedImportedJobId = job.imported_job_id;
      runAnalysis(job.imported_job_id);
    });

    const fitBtn = document.createElement("button");
    fitBtn.type = "button";
    fitBtn.className = "btn btn-ghost";
    fitBtn.textContent = job.auto_fit_score == null ? "Auto-fit" : "Re-score";
    fitBtn.addEventListener("click", () => autoFitOne(job.id));
    analyzeBtn.after(fitBtn);

    const dismissBtn = document.createElement("button");
    dismissBtn.type = "button";
    dismissBtn.className = "btn btn-ghost";
    dismissBtn.textContent = t("queue.notRelevant", "Not relevant");
    dismissBtn.title = t("queue.notRelevant.hint", "Hide this job and downweight similar future results");
    dismissBtn.addEventListener("click", () => dismissJob(job));
    fitBtn.after(dismissBtn);
    list.append(node);
  }
}

function buildAlsoSeenPanel(alsoSeen) {
  // Hidden-by-default expansion under a queue row. Lists every host
  // we've seen this job at, with a clickable URL + a "found N days ago"
  // hint, so the operator can sanity-check the dedup decision.
  const panel = document.createElement("div");
  panel.className = "also-seen-panel";
  panel.hidden = true;
  const ul = document.createElement("ul");
  for (const [host, entry] of Object.entries(alsoSeen)) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = entry?.url || `https://${host}`;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = host;
    li.append(a);
    const meta = document.createElement("span");
    meta.className = "muted";
    const label = entry?.source_label ? ` · ${entry.source_label}` : "";
    const seenIso = entry?.found_at || entry?.seen_at || entry?.at;
    let when = "";
    if (seenIso) {
      try {
        const seen = new Date(seenIso);
        const days = Math.max(0, Math.floor((Date.now() - seen.getTime()) / 86400000));
        const tpl = days === 0
          ? t("queue.alsoSeenToday", "today")
          : t("queue.alsoSeenDaysAgo", "{days}d ago").replace("{days}", String(days));
        when = ` · ${tpl}`;
      } catch (_) {}
    }
    meta.textContent = `${label}${when}`;
    li.append(meta);
    ul.append(li);
  }
  panel.append(ul);
  return panel;
}

async function dismissJob(job) {
  // Build the term we'll downweight — title + company. Send to server so
  // the persisted profile.dismissed_terms grows; the downweight applies
  // to future find-me-jobs and saved-search runs automatically.
  const company = (state.companies || []).find((c) => c.id === job.company_id);
  const title = (job.title || "").trim();
  const companyName = (company?.name || "").trim();
  const terms = [title, companyName].filter((s) => s && s.length >= 3);
  if (!terms.length) {
    showToast(t("queue.notRelevant.noTerms", "Nothing to learn from this row."), "info");
    return;
  }
  try {
    const payload = await api("/api/profile", {
      method: "POST",
      body: JSON.stringify({ addDismissedTerms: terms }),
    });
    if (payload.profile) state.profile = payload.profile;
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    // Hide the row immediately for snappy feedback.
    state.discoveredJobs = state.discoveredJobs.filter((j) => j.id !== job.id);
    showToast(t("queue.notRelevant.toast", `Dismissed. ${terms[0]} won't surface as prominently.`), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function autoFitOne(discoveredJobId) {
  const credentialValue = $("#providerRuntimeKey")?.value || "";
  try {
    const payload = await api(`/api/discovered-jobs/${encodeURIComponent(discoveredJobId)}/auto-fit`, {
      method: "POST",
      body: JSON.stringify({ credentialValue }),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    const status = payload.result?.status;
    const score = payload.discoveredJob?.auto_fit_score;
    if (status === "completed" && score != null) {
      showToast(`Fit ${Math.round(score * 100)} — ${payload.discoveredJob.auto_fit_reason || "scored"}.`, "success");
    } else if (status === "handoff_required") {
      showToast("Auto-fit needs an API-mode AI provider. Set one in Settings.", "info");
    } else {
      showToast(`Auto-fit ${status}: ${payload.result?.error || "no score"}.`, "info");
    }
    if ($("#providerRuntimeKey")) $("#providerRuntimeKey").value = "";
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function autoFitAll() {
  const credentialValue = $("#providerRuntimeKey")?.value || "";
  const limit = Number($("#autoFitLimit")?.value) || 10;
  try {
    const payload = await api("/api/discovered-jobs/auto-fit-all", {
      method: "POST",
      body: JSON.stringify({ credentialValue, limit }),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    const completed = (payload.outcomes || []).filter((o) => o.status === "completed").length;
    showToast(`Scored ${completed} job${completed === 1 ? "" : "s"}.`, completed > 0 ? "success" : "info");
    if ($("#providerRuntimeKey")) $("#providerRuntimeKey").value = "";
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function tailorCv(importedJobId) {
  if (!importedJobId) return;
  const credentialValue = $("#providerRuntimeKey")?.value || "";
  const status = $("#tailorCvStatus");
  if (status) status.textContent = "Tailoring…";
  try {
    const payload = await api(`/api/imported-jobs/${encodeURIComponent(importedJobId)}/tailor-cv`, {
      method: "POST",
      body: JSON.stringify({ credentialValue }),
    });
    const tailored = payload.tailored || {};
    state.analysisBrief = { title: "Tailored CV", prompt: tailored.output || tailored.error || tailored.prompt || "", providerLabel: tailored.provider_id, invocationMode: tailored.invocation_mode };
    $("#briefMeta").textContent = `Tailored CV · ${tailored.provider_id} (${tailored.invocation_mode})`;
    $("#briefPrompt").value = tailored.output || tailored.error || tailored.prompt || "";
    if (tailored.status === "completed") {
      showToast("Tailored CV ready in the AI Brief view.", "success");
    } else if (tailored.status === "handoff_required") {
      showToast("Configure an API-mode AI provider, or copy the prompt manually.", "info");
    } else {
      showToast(`CV tailoring ${tailored.status}: ${tailored.error || ""}`, "info");
    }
    if ($("#providerRuntimeKey")) $("#providerRuntimeKey").value = "";
    if (status) status.textContent = `Status: ${tailored.status}`;
    navigate("brief");
  } catch (error) {
    if (status) status.textContent = `Error: ${error.message}`;
    showToast(error.message, "error");
  }
}

function renderImportedJobs() {
  const list = $("#importedJobsList");
  if (!list) return;
  list.replaceChildren();
  if (!state.importedJobs.length) {
    list.append(emptyNode(
      t("imported.empty.text", "No imported jobs yet. Open the queue, find one you like, hit Import."),
      {
        icon: "briefcase",
        ctaText: t("imported.empty.cta", "Open queue"),
        onCta: () => navigate("jobs"),
      },
    ));
    return;
  }
  for (const job of state.importedJobs.slice(0, 12)) {
    const row = document.createElement("div");
    row.className = "imported-row";
    const left = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = job.title;
    const meta = document.createElement("span");
    meta.className = "muted";
    const status = job.analysis_status && job.analysis_status !== "pending" ? ` · ${job.analysis_status}` : "";
    meta.textContent = `${job.company_name || ""}${job.location ? ` · ${job.location}` : ""}${status}`;
    left.append(title, meta);
    const right = document.createElement("div");
    right.className = "action-group";
    const briefBtn = document.createElement("button");
    briefBtn.type = "button";
    briefBtn.className = "btn";
    briefBtn.textContent = "Open brief";
    briefBtn.addEventListener("click", () => {
      state.selectedImportedJobId = job.id;
      prepareBrief(job.id);
    });
    right.append(briefBtn);
    if (job.source_url) {
      const applyBtn = document.createElement("button");
      applyBtn.type = "button";
      applyBtn.className = "btn btn-primary";
      const isApplied = job.application_status === "applied"
        || job.application_status === "interviewing"
        || job.application_status === "offer"
        || job.application_status === "rejected"
        || job.application_status === "accepted";
      applyBtn.textContent = isApplied
        ? t("imported.applyAgain", "Re-open posting")
        : t("imported.applyNow", "Apply now");
      applyBtn.addEventListener("click", () => applyToJob(job));
      right.append(applyBtn);
    }
    row.append(left, right);
    list.append(row);
  }
}

async function applyToJob(job) {
  // Opening the source URL is the side-effect the user actually cares about.
  // Marking applied is bookkeeping — we still record it but tolerate failures.
  try {
    if (job.source_url) {
      window.open(job.source_url, "_blank", "noopener,noreferrer");
    }
  } catch (_) {
    // popup blocked → user can still copy the URL from the brief
  }
  if (job.application_status === "applied") {
    showToast(t("imported.alreadyApplied", "Already marked applied — opened posting in a new tab."), "info");
    return;
  }
  try {
    const payload = await api(`/api/imported-jobs/${encodeURIComponent(job.id)}/application`, {
      method: "POST",
      body: JSON.stringify({ applicationStatus: "applied", historyNote: "Apply-now button" }),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    showToast(t("imported.applyMarked", "Marked as applied — good luck."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderBriefSummary() {
  const summary = $("#briefProviderSummary");
  if (!summary) return;
  const id = state.aiProvider.provider_id || "manual";
  const opt = state.aiProviderOptions.find((o) => o.id === id);
  const mode = state.aiProvider.invocation_mode || opt?.invocation_modes?.[0] || "manual";
  const label = opt?.label || "Manual / no AI";
  const cred = state.aiProvider.credential_reference ? ` · key from ${state.aiProvider.credential_reference}` : "";
  summary.textContent = `${label} — mode: ${mode}${cred}. Session keys are sent only with Run AI.`;
}

function renderBrief() {
  if (!state.analysisBrief) {
    $("#briefMeta").textContent = state.selectedImportedJobId ? "Click an imported job to prepare its brief" : "No brief prepared yet";
    $("#briefPrompt").value = "";
  }
}

function renderHistory() {
  const list = $("#scanHistory");
  list.replaceChildren();
  const scans = [...state.scans]
    .sort((a, b) => (b.last_checked_at || "").localeCompare(a.last_checked_at || ""))
    .slice(0, 10);
  if (!scans.length) {
    list.append(emptyNode(t("history.empty", "No scan history yet."), { icon: "list" }));
    return;
  }
  for (const scan of scans) {
    const company = state.companies.find((c) => c.id === scan.company_id);
    const node = historyTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("strong").textContent = `${company?.name || "Unknown company"} — ${SCAN_STATUS_COPY[scan.status] || scan.status}`;
    const ts = scan.last_checked_at ? new Date(scan.last_checked_at).toLocaleString() : "";
    node.querySelector("p").textContent = `${scan.jobs_found} role${scan.jobs_found === 1 ? "" : "s"} · ${scan.pages_checked} page${scan.pages_checked === 1 ? "" : "s"} · ${ts}`;
    const pre = node.querySelector("pre");
    if (scan.errors?.length) pre.textContent = JSON.stringify(scan.errors, null, 2);
    else pre.hidden = true;
    list.append(node);
  }
}

function renderOnboarding() {
  const list = $("#onboardingList");
  if (!list) return;
  list.replaceChildren();
  const steps = state.onboarding?.steps || [];
  const progress = state.onboarding?.progress || { completed: 0, total: steps.length };
  $("#onboardingProgress").textContent = `${progress.completed} of ${progress.total} complete`;
  for (const step of steps) {
    const li = document.createElement("li");
    li.className = step.complete ? "complete" : "";
    const label = document.createElement("strong");
    label.textContent = step.label;
    const hint = document.createElement("span");
    hint.className = "muted";
    hint.textContent = step.hint;
    const wrap = document.createElement("span");
    wrap.append(label, document.createTextNode(" — "), hint);
    li.append(wrap);
    list.append(li);
  }
}

function renderTemplates() {
  const list = $("#templateList");
  if (!list) return;
  list.replaceChildren();
  for (const template of state.watchlistTemplates || []) {
    const node = document.createElement("div");
    node.className = "suggestion";
    const title = document.createElement("strong");
    title.textContent = template.label;
    const desc = document.createElement("span");
    desc.textContent = template.description;
    const meta = document.createElement("span");
    meta.textContent = `${template.companies.length} companies`;
    const apply = document.createElement("button");
    apply.type = "button";
    apply.className = "btn btn-small";
    apply.textContent = "Apply template";
    apply.addEventListener("click", () => applyWatchlistTemplate(template.id));
    node.append(title, desc, meta, apply);
    list.append(node);
  }
}

function renderSavedSearches() {
  const list = $("#savedSearchList");
  if (!list) return;
  list.replaceChildren();
  if (!(state.savedSearches || []).length) {
    list.append(emptyNode(
      t("savedSearches.empty.text", "No saved searches yet. Save a query and we'll watch it daily."),
      { icon: "saved" },
    ));
    return;
  }
  for (const search of state.savedSearches || []) {
    const row = document.createElement("div");
    row.className = "saved-search-row";
    const left = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = search.name;
    const meta = document.createElement("span");
    meta.className = "muted small";
    const roles = (search.target_roles || []).join(", ");
    meta.textContent = `${roles || "(no roles)"} · ${search.industry} · ${search.location || "anywhere"}`;
    left.append(title, meta);
    const apply = document.createElement("button");
    apply.type = "button";
    apply.className = "btn";
    apply.textContent = "Apply";
    apply.addEventListener("click", () => {
      $("#targetRoles").value = (search.target_roles || []).join(", ");
      $("#targetIndustry").value = search.industry || "Healthcare";
      $("#targetLocation").value = search.location || "";
      suggestCompanies();
    });
    const alerts = search.alerts || {};
    const unseen = Number(alerts.unseenCount || 0);
    if (unseen > 0) {
      const badge = document.createElement("span");
      badge.className = "tag warn";
      badge.textContent = `${unseen} new`;
      badge.title = "New matching jobs since you last checked";
      meta.append(" · ");
      meta.append(badge);
    }
    const matchesBtn = document.createElement("button");
    matchesBtn.type = "button";
    matchesBtn.className = "btn";
    matchesBtn.textContent = unseen > 0 ? `Show ${unseen} new` : `Show matches (${alerts.matchCount || 0})`;
    matchesBtn.addEventListener("click", () => showSavedSearchMatches(search.id, unseen > 0));
    const runNowBtn = document.createElement("button");
    runNowBtn.type = "button";
    runNowBtn.className = "btn";
    runNowBtn.textContent = t("savedSearch.runNow", "Run now");
    runNowBtn.title = t("savedSearch.runNow.hint", "Search all aggregators with this query and add new results to your queue");
    runNowBtn.addEventListener("click", () => runSavedSearchNow(search.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-danger";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteSavedSearch(search.id));
    const right = document.createElement("div");
    right.className = "action-group";
    right.append(runNowBtn, matchesBtn, apply, remove);
    row.append(left, right);
    list.append(row);
  }
}

function renderApplicationHistory(job) {
  const panel = $("#applicationHistoryPanel");
  const list = $("#applicationHistoryList");
  if (!panel || !list) return;
  const history = Array.isArray(job?.application_history) ? job.application_history : [];
  list.replaceChildren();
  if (!history.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  // Vertical timeline: marker + status pill + stage + relative time + note.
  list.classList.add("timeline");
  for (const entry of history.slice().reverse()) {
    const li = document.createElement("li");
    li.className = "timeline-item";

    const marker = document.createElement("span");
    marker.className = `timeline-marker status-${(entry.status || "").replace(/\W+/g, "_")}`;
    marker.setAttribute("aria-hidden", "true");

    const body = document.createElement("div");
    body.className = "timeline-body";

    const head = document.createElement("div");
    head.className = "timeline-head";
    if (entry.status) {
      const pill = document.createElement("span");
      pill.className = `tag status-pill status-${entry.status}`;
      pill.textContent = entry.status;
      head.append(pill);
    }
    if (entry.stage) {
      const stageEl = document.createElement("span");
      stageEl.className = "muted small";
      stageEl.textContent = `· ${entry.stage}`;
      head.append(stageEl);
    }
    const when = document.createElement("time");
    when.className = "muted small timeline-when";
    if (entry.at) {
      const ts = new Date(entry.at);
      when.dateTime = ts.toISOString();
      when.title = ts.toLocaleString();
      when.textContent = relativeTimeFromIso(entry.at);
    }
    head.append(when);
    body.append(head);

    if (entry.note) {
      const note = document.createElement("p");
      note.className = "timeline-note";
      note.textContent = entry.note;
      body.append(note);
    }

    li.append(marker, body);
    list.append(li);
  }
}

function renderApplicationForm() {
  const form = $("#applicationForm");
  if (!form) return;
  const summary = $("#structuredFitSummary");
  const job = state.importedJobs.find((j) => j.id === state.selectedImportedJobId);
  if (!job) {
    form.hidden = true;
    summary.hidden = true;
    $("#applicationContextLabel").textContent = "Pick an imported job to update its status and notes.";
    return;
  }
  form.hidden = false;
  $("#applicationContextLabel").textContent = `${job.title} — ${job.company_name}`;
  const select = $("#applicationStatus");
  select.replaceChildren();
  for (const status of state.applicationStatuses || []) {
    const opt = document.createElement("option");
    opt.value = status;
    opt.textContent = status;
    select.append(opt);
  }
  select.value = job.application_status || "saved";
  const stageEl = $("#applicationInterviewStage");
  if (stageEl) stageEl.value = job.interview_stage || "";
  const reminderEl = $("#applicationReminderAt");
  if (reminderEl) {
    if (job.reminder_at) {
      // Trim seconds + tz so the datetime-local input accepts the value.
      reminderEl.value = String(job.reminder_at).slice(0, 16);
    } else {
      reminderEl.value = "";
    }
  }
  const noteEl = $("#applicationHistoryNote");
  if (noteEl) noteEl.value = "";
  $("#applicationNextAction").value = job.next_action || "";
  $("#applicationNotes").value = job.application_notes || "";
  $("#applicationCoverLetter").value = job.cover_letter_draft || "";
  const checklistText = (job.documents_checklist || [])
    .map((item) => `${item.complete ? "[x]" : "[ ]"} ${item.label}`)
    .join("\n");
  $("#applicationChecklist").value = checklistText;
  renderApplicationHistory(job);
  if (job.structured_analysis || job.fit_score != null) {
    summary.hidden = false;
    const fit = job.fit_score != null ? `${Math.round(job.fit_score * 100)}%` : "—";
    const rec = job.recommendation || "—";
    summary.textContent = `Fit: ${fit} · Recommendation: ${rec}`;
  } else {
    summary.hidden = true;
  }
}

function renderBilling() {
  const summary = $("#billingSummary");
  const planSelect = $("#adminBillingPlan");
  if (planSelect) {
    planSelect.replaceChildren();
    for (const plan of state.billingPlans || []) {
      const opt = document.createElement("option");
      opt.value = plan.id;
      opt.textContent = `${plan.label} (€${plan.monthlyPriceEur}/mo · ${plan.seatsIncluded} seats)`;
      planSelect.append(opt);
    }
  }
  if (summary && state.subscription) {
    const plan = (state.billingPlans || []).find((p) => p.id === state.subscription.plan_id);
    summary.textContent = `${plan ? plan.label : state.subscription.plan_id} — ${state.subscription.status}, ${state.subscription.seats} seats.`;
  } else if (summary) {
    summary.textContent = "Subscription details load when you open Settings.";
  }
}

function renderQuotaSummary() {
  const el = $("#quotaSummary");
  if (!el) return;
  const usage = state.bootstrapQuotas;
  if (!usage) {
    el.textContent = "No usage yet.";
    return;
  }
  el.textContent =
    `Scans today: ${usage.scansToday}/${usage.scansLimitPerDay} · ` +
    `AI calls today: ${usage.aiToday}/${usage.aiLimitPerDay} · ` +
    `Active scans: ${usage.activeScans}/${usage.activeScanLimit}`;
}

function applyTheme(theme) {
  let resolved = (theme || "dark").toLowerCase();
  if (resolved === "system") {
    resolved = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }
  if (resolved !== "light" && resolved !== "dark") {
    resolved = "dark";
  }
  document.documentElement.dataset.theme = resolved;
  state.theme = theme || "dark";
  const select = document.getElementById("themeSelect");
  if (select) select.value = state.theme;
}

async function loadLocale(locale) {
  const target = (locale || "en").toLowerCase();
  if (target !== "en" && target !== "de") {
    state.locale = "en";
    state.translations = {};
    applyTranslations();
    return;
  }
  if (target === "en") {
    state.locale = "en";
    state.translations = {};
    applyTranslations();
    try { localStorage.setItem("dj_locale", "en"); } catch (_) {}
    return;
  }
  try {
    const response = await fetch(`/i18n/${target}.json`, { cache: "force-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.translations = await response.json();
    state.locale = target;
    document.documentElement.lang = target;
    try { localStorage.setItem("dj_locale", target); } catch (_) {}
  } catch (error) {
    state.locale = "en";
    state.translations = {};
    document.documentElement.lang = "en";
  }
  applyTranslations();
}

// Apply cached locale at boot so the auth gate (and other pre-login views)
// render in the user's last-chosen language.
(function bootLocale() {
  let cached = null;
  try { cached = localStorage.getItem("dj_locale"); } catch (_) {}
  if (!cached && navigator.language && navigator.language.toLowerCase().startsWith("de")) {
    cached = "de";
  }
  if (cached) loadLocale(cached);
})();

// Restore queue source-filter toggles from localStorage so they survive a reload.
(function bootQueueFilters() {
  try {
    const raw = localStorage.getItem("dj_queue_sources");
    if (raw) state.queueSourceFilter = JSON.parse(raw) || {};
  } catch (_) { state.queueSourceFilter = {}; }
})();

// First-run wizard controller. Opened by absorbBootstrap when the
// server reports firstRunWizard=true. Three steps; each Next persists
// what the user typed so far so a refresh mid-wizard doesn't lose data.
const wizardState = { step: 1, suggestedPersonaId: null };

function openFirstRunWizard() {
  const dialog = document.getElementById("firstRunWizard");
  if (!dialog || typeof dialog.showModal !== "function") return;
  if (dialog.open) return;
  wizardState.step = 1;
  setWizardStep(1);
  // Pre-populate persona dropdown with the same list as Settings.
  const select = document.getElementById("wizardPersona");
  if (select) {
    select.replaceChildren();
    for (const p of state.personas || []) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.label;
      select.append(opt);
    }
    select.value = state.profile?.personaId || "healthcare-management";
  }
  dialog.showModal();
}

function setWizardStep(step) {
  for (let i = 1; i <= 3; i += 1) {
    const el = document.getElementById(`wizardStep${i}`);
    if (el) el.classList.toggle("active", i === step);
  }
  wizardState.step = step;
}

async function wizardSaveCv() {
  const text = (document.getElementById("wizardCvText")?.value || "").trim();
  if (!text) return;
  try {
    await api("/api/profile", { method: "POST", body: JSON.stringify({ cvText: text }) });
    // Ask the server for a persona suggestion based on the saved CV.
    const sug = await api("/api/profile/persona-suggest", { method: "POST", body: JSON.stringify({}) });
    const top = (sug.personaSuggestions || [])[0];
    if (top && top.personaId) {
      wizardState.suggestedPersonaId = top.personaId;
      const hint = document.getElementById("wizardPersonaHint");
      if (hint) {
        const tpl = t("wizard.step2.suggested", "From your CV we picked: {label}");
        hint.textContent = tpl.replace("{label}", top.label);
      }
      const select = document.getElementById("wizardPersona");
      if (select) select.value = top.personaId;
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function wizardFinish() {
  const role = (document.getElementById("wizardRole")?.value || "").trim();
  const location = (document.getElementById("wizardLocation")?.value || "").trim();
  const personaId = document.getElementById("wizardPersona")?.value;
  if (!role) {
    showToast(t("wizard.step3.roleRequired", "Add a role keyword to save."), "info");
    return;
  }
  try {
    if (personaId) {
      await api("/api/profile", { method: "POST", body: JSON.stringify({ personaId }) });
    }
    const search = await api("/api/saved-searches", {
      method: "POST",
      body: JSON.stringify({
        label: role + (location ? ` in ${location}` : ""),
        role,
        location,
      }),
    });
    if (search.savedSearch?.id) {
      // Run the search immediately so the user lands on real results.
      await api(`/api/saved-searches/${encodeURIComponent(search.savedSearch.id)}/run-now`, { method: "POST" });
    }
    await api("/api/profile", { method: "POST", body: JSON.stringify({ onboardingDismissed: true }) });
    const dialog = document.getElementById("firstRunWizard");
    if (dialog?.open) dialog.close();
    showToast(t("wizard.done", "Set up. We'll watch this search daily."), "success");
    // Re-fetch bootstrap so the new saved search + ranked results show up.
    const bs = await api("/api/bootstrap");
    absorbBootstrap(bs);
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function wizardDismiss() {
  try {
    await api("/api/profile", { method: "POST", body: JSON.stringify({ onboardingDismissed: true }) });
  } catch (_) {}
  const dialog = document.getElementById("firstRunWizard");
  if (dialog?.open) dialog.close();
}

// Command palette (cmd-K on Mac, ctrl-K on Windows/Linux). Single
// search bar that lets you switch view, jump to a job, or open a
// company without lifting your hands off the keyboard.
const cmdK = {
  open() {
    const dialog = document.getElementById("cmdkDialog");
    if (!dialog || dialog.open) return;
    document.getElementById("cmdkKbdHint").textContent = "Esc";
    document.getElementById("cmdkInput").value = "";
    cmdK.activeIndex = 0;
    cmdK.render("");
    dialog.showModal();
    setTimeout(() => document.getElementById("cmdkInput")?.focus(), 0);
  },
  close() {
    const dialog = document.getElementById("cmdkDialog");
    if (dialog?.open) dialog.close();
  },
  activeIndex: 0,
  visibleItems: [],
  buildItems(query) {
    const q = query.trim().toLowerCase();
    const matches = (text) => !q || (text || "").toLowerCase().includes(q);
    const items = [];
    // Views
    const views = [
      { view: "jobs", label: t("nav.queue", "Jobs") },
      { view: "dashboard", label: t("nav.dashboard", "Today") },
      { view: "brief", label: t("nav.brief", "Briefcase") },
      { view: "companies", label: t("nav.companies", "Companies") },
      { view: "settings", label: t("nav.settings", "Settings") },
    ];
    if (isAdmin()) views.push({ view: "admin", label: t("nav.admin", "Admin") });
    views.forEach((v) => {
      if (matches(v.label)) items.push({ kind: "view", label: v.label, meta: t("cmdk.go", "Go to view"), action: () => navigate(v.view) });
    });
    // Common actions
    const actions = [
      { label: t("cmdk.action.toggleTheme", "Toggle theme"), action: () => {
          const next = (state.theme === "dark") ? "light" : "dark";
          state.theme = next; applyTheme(next);
          api("/api/profile", { method: "POST", body: JSON.stringify({ theme: next }) }).catch(() => {});
        } },
      { label: t("cmdk.action.toggleLocale", "Switch language"), action: () => {
          const next = (state.locale === "de") ? "en" : "de";
          loadLocale(next);
          api("/api/profile", { method: "POST", body: JSON.stringify({ locale: next }) }).catch(() => {});
        } },
      { label: t("cmdk.action.signOut", "Sign out"), action: () => document.getElementById("logoutBtn")?.click() },
    ];
    actions.forEach((a) => { if (matches(a.label)) items.push({ kind: "action", label: a.label, meta: t("cmdk.do", "Action"), action: a.action }); });
    // Open jobs (top 30 matches)
    let jobMatches = 0;
    for (const job of state.discoveredJobs || []) {
      if (jobMatches >= 30) break;
      const company = (state.companies || []).find((c) => c.id === job.company_id);
      const label = `${job.title}${company ? " · " + company.name : ""}`;
      if (!matches(label)) continue;
      items.push({
        kind: "job", label, meta: t("cmdk.openJob", "Open job"),
        action: () => {
          if (job.source_url) window.open(job.source_url, "_blank", "noopener,noreferrer");
        },
      });
      jobMatches += 1;
    }
    // Companies (top 20 matches)
    let companyMatches = 0;
    for (const co of state.companies || []) {
      if (companyMatches >= 20) break;
      if (!matches(co.name)) continue;
      items.push({
        kind: "company", label: co.name, meta: t("cmdk.openCompany", "Watchlist"),
        action: () => { state.selectedCompanyId = co.id; navigate("companies"); },
      });
      companyMatches += 1;
    }
    // Saved searches: Run-now action for each.
    for (const search of state.savedSearches || []) {
      const label = search.label || `${search.role || ""} ${search.location ? "@ " + search.location : ""}`.trim();
      if (!matches(label)) continue;
      items.push({
        kind: "savedSearch", label: `▶ ${label}`, meta: t("cmdk.runSearch", "Run saved search"),
        action: () => runSavedSearchNow(search.id),
      });
    }
    return items;
  },
  render(query) {
    const list = document.getElementById("cmdkResults");
    if (!list) return;
    list.replaceChildren();
    cmdK.visibleItems = cmdK.buildItems(query);
    if (!cmdK.visibleItems.length) {
      const empty = document.createElement("li");
      empty.className = "cmdk-section";
      empty.textContent = t("cmdk.noResults", "No matches");
      list.append(empty);
      return;
    }
    cmdK.activeIndex = Math.min(cmdK.activeIndex, cmdK.visibleItems.length - 1);
    cmdK.visibleItems.forEach((item, idx) => {
      const li = document.createElement("li");
      li.className = "cmdk-item" + (idx === cmdK.activeIndex ? " active" : "");
      li.setAttribute("role", "option");
      const label = document.createElement("span");
      label.textContent = item.label;
      const meta = document.createElement("span");
      meta.className = "cmdk-item-meta";
      meta.textContent = item.meta;
      li.append(label, meta);
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        cmdK.activeIndex = idx;
        cmdK.execute();
      });
      list.append(li);
    });
  },
  execute() {
    const item = cmdK.visibleItems[cmdK.activeIndex];
    if (!item) return;
    cmdK.close();
    try { item.action(); } catch (_) {}
  },
};

document.addEventListener("keydown", (event) => {
  // Open cmd-K on Cmd+K (mac) or Ctrl+K (win/linux). Escape closes.
  if ((event.metaKey || event.ctrlKey) && !event.shiftKey && !event.altKey && event.key.toLowerCase() === "k") {
    event.preventDefault();
    cmdK.open();
    return;
  }
  const dialog = document.getElementById("cmdkDialog");
  if (!dialog || !dialog.open) return;
  if (event.key === "Escape") {
    event.preventDefault();
    cmdK.close();
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    cmdK.activeIndex = (cmdK.activeIndex + 1) % Math.max(1, cmdK.visibleItems.length);
    cmdK.render(document.getElementById("cmdkInput").value);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    cmdK.activeIndex = (cmdK.activeIndex - 1 + cmdK.visibleItems.length) % Math.max(1, cmdK.visibleItems.length);
    cmdK.render(document.getElementById("cmdkInput").value);
  } else if (event.key === "Enter") {
    event.preventDefault();
    cmdK.execute();
  }
});

(function bootCmdKInputHandler() {
  const input = document.getElementById("cmdkInput");
  input?.addEventListener("input", (e) => {
    cmdK.activeIndex = 0;
    cmdK.render(e.target.value);
  });
  // Topbar launcher button — also opens the palette.
  document.getElementById("cmdkLauncher")?.addEventListener("click", () => cmdK.open());
  // Adapt the kbd hint on Windows/Linux (Ctrl) vs Mac (Cmd).
  const isMac = /Mac|iPad|iPhone|iPod/.test(navigator.userAgent || "");
  const kbd = document.getElementById("cmdkLauncherKbd");
  const hintKbd = document.getElementById("cmdkKbdHint");
  if (kbd) kbd.textContent = isMac ? "⌘K" : "Ctrl+K";
  if (hintKbd) hintKbd.textContent = "Esc";
})();

// Settings tabs — show only cards with data-tab matching the active tab.
// Cards without a data-tab attr stay always-visible (e.g. workspace
// section header inside #view-settings if added later).
function setSettingsTab(tabId) {
  const tabs = document.querySelectorAll("#settingsTabs .settings-tab");
  if (!tabs.length) return;
  const known = new Set(Array.from(tabs).map((t) => t.dataset.tab));
  if (!known.has(tabId)) tabId = "profile";
  tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.tab === tabId)));
  const view = document.getElementById("view-settings");
  if (!view) return;
  view.querySelectorAll(":scope > .card").forEach((card) => {
    const cardTab = card.dataset.tab;
    card.hidden = Boolean(cardTab) && cardTab !== tabId;
  });
  try { localStorage.setItem("dj_settings_tab", tabId); } catch (_) {}
}

(function bootSettingsTabs() {
  document.addEventListener("click", (event) => {
    const tab = event.target.closest("#settingsTabs .settings-tab");
    if (!tab) return;
    setSettingsTab(tab.dataset.tab);
  });
  // Restore last-selected tab on load.
  let saved = "profile";
  try { saved = localStorage.getItem("dj_settings_tab") || "profile"; } catch (_) {}
  // Defer until DOM ready so the cards exist.
  queueMicrotask(() => setSettingsTab(saved));
})();

// Keyboard shortcuts for the queue. Vim-style j/k to move focus,
// a to apply (opens source URL), e to import, x to dismiss, i to mark imported.
// Disabled while typing in inputs/textareas/contenteditable.
(function bootKeyboardShortcuts() {
  let focusedIndex = -1;

  function visibleQueueRows() {
    return Array.from(document.querySelectorAll("#jobsQueue .job-item"));
  }

  function setFocusedIndex(i) {
    const rows = visibleQueueRows();
    if (!rows.length) return;
    focusedIndex = (i + rows.length) % rows.length;
    rows.forEach((row, idx) => row.classList.toggle("kbd-focused", idx === focusedIndex));
    rows[focusedIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function getJobAt(idx) {
    const rows = visibleQueueRows();
    if (idx < 0 || idx >= rows.length) return null;
    const titleEl = rows[idx].querySelector("h3");
    if (!titleEl) return null;
    const title = titleEl.textContent;
    return (state.discoveredJobs || []).find((j) => j.title === title) || null;
  }

  document.addEventListener("keydown", (event) => {
    if (state.view !== "jobs") return;
    const target = event.target;
    if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable)) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === "j") {
      event.preventDefault();
      setFocusedIndex(focusedIndex < 0 ? 0 : focusedIndex + 1);
    } else if (key === "k") {
      event.preventDefault();
      setFocusedIndex(focusedIndex < 0 ? 0 : focusedIndex - 1);
    } else if (key === "x") {
      const job = getJobAt(focusedIndex);
      if (job) { event.preventDefault(); dismissJob(job); }
    } else if (key === "a") {
      const job = getJobAt(focusedIndex);
      if (job?.source_url) {
        event.preventDefault();
        window.open(job.source_url, "_blank", "noopener,noreferrer");
      }
    } else if (key === "e") {
      const job = getJobAt(focusedIndex);
      if (job && !job.imported_job_id) {
        event.preventDefault();
        importJob(job.id);
      }
    } else if (key === "?") {
      event.preventDefault();
      showToast(t("kbd.help", "j/k = move · a = open · e = import · x = dismiss"), "info", 6000);
    }
  });
})();

(function bootWizardHandlers() {
  document.getElementById("wizardCvUploadBtn")?.addEventListener("click", () => {
    document.getElementById("wizardCvFile")?.click();
  });
  document.getElementById("wizardCvFile")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const status = document.getElementById("wizardCvStatus");
    if (status) status.textContent = `Uploading ${file.name}…`;
    try {
      const arrayBuffer = await file.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
      const contentBase64 = btoa(binary);
      const payload = await api("/api/profile/cv-upload", {
        method: "POST",
        body: JSON.stringify({ filename: file.name, contentBase64 }),
      });
      if (status) status.textContent = `Imported ${payload.extractedChars || 0} chars.`;
      const text = payload.profile?.cvText || "";
      const ta = document.getElementById("wizardCvText");
      if (ta) ta.value = text;
      const top = (payload.personaSuggestions || [])[0];
      if (top) {
        wizardState.suggestedPersonaId = top.personaId;
      }
    } catch (error) {
      if (status) status.textContent = `Error: ${error.message}`;
    } finally {
      event.target.value = "";
    }
  });
  document.getElementById("wizardSkipCv")?.addEventListener("click", () => setWizardStep(2));
  document.getElementById("wizardCvNext")?.addEventListener("click", async () => {
    await wizardSaveCv();
    setWizardStep(2);
  });
  document.getElementById("wizardBackPersona")?.addEventListener("click", () => setWizardStep(1));
  document.getElementById("wizardPersonaNext")?.addEventListener("click", () => setWizardStep(3));
  document.getElementById("wizardBackSearch")?.addEventListener("click", () => setWizardStep(2));
  document.getElementById("wizardFinish")?.addEventListener("click", wizardFinish);
  document.getElementById("wizardDismiss")?.addEventListener("click", wizardDismiss);
})();

function applyTranslations() {
  const dict = state.translations || {};
  for (const node of document.querySelectorAll("[data-i18n]")) {
    const key = node.getAttribute("data-i18n");
    if (key && dict[key]) {
      node.textContent = dict[key];
    }
  }
  const localeSelect = document.getElementById("localeSelect");
  if (localeSelect) localeSelect.value = state.locale || "en";
}

function renderWorkspacePicker() {
  const wrap = document.getElementById("workspacePickerWrap");
  const select = document.getElementById("workspaceSelect");
  if (!wrap || !select) return;
  const workspaces = Array.isArray(state.workspaces) ? state.workspaces : [];
  if (!workspaces.length || !state.auth?.authenticated) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  select.replaceChildren();
  for (const ws of workspaces) {
    const opt = document.createElement("option");
    opt.value = ws.id;
    const ownTag = ws.role === "owner" ? "" : " · member";
    opt.textContent = `${ws.label || ws.id}${ownTag}`;
    select.append(opt);
  }
  const active = state.profile?.activeWorkspaceId || state.activeWorkspaceId || workspaces[0].id;
  select.value = active;
  // Show invite button only when current user is owner/admin of selected workspace.
  const inviteBtn = document.getElementById("inviteWorkspaceBtn");
  if (inviteBtn) {
    const current = workspaces.find((w) => w.id === active);
    inviteBtn.hidden = !current || (current.role !== "owner" && current.role !== "admin");
  }
}

async function switchWorkspace(workspaceId) {
  try {
    const payload = await api("/api/workspaces/active", {
      method: "POST",
      body: JSON.stringify({ workspaceId }),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    state.profile = payload.profile || state.profile;
    showToast(t("toast.workspaceSwitched", "Workspace switched."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function inviteWorkspaceMember() {
  const select = document.getElementById("workspaceSelect");
  const workspaceId = select?.value;
  if (!workspaceId) return;
  const email = window.prompt(
    state.translations?.["workspaces.invite.prompt"] || "Email of the user to add to this workspace:"
  );
  if (!email) return;
  try {
    const resp = await api(`/api/workspaces/${encodeURIComponent(workspaceId)}/invite`, {
      method: "POST",
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    });
    if (resp.status === "added") {
      showToast(state.translations?.["workspaces.invite.added"] || "Member added.", "success");
    } else if (resp.status === "already_member") {
      showToast(t("toast.alreadyMember", "Already a member."), "info");
    }
  } catch (error) {
    if (error.message?.includes("user_not_found")) {
      showToast(state.translations?.["workspaces.invite.notFound"] || "User not found. They must already have an account.", "error");
    } else {
      showToast(error.message, "error");
    }
  }
}

function renderNotifySettings() {
  const urlInput = document.getElementById("slackWebhookUrl");
  const thresholdInput = document.getElementById("slackFitThreshold");
  const saveBtn = document.getElementById("saveNotifyBtn");
  const testBtn = document.getElementById("slackTestBtn");
  if (!urlInput || !thresholdInput || !saveBtn) return;
  // We never round-trip the actual webhook URL to the client (treat it
  // as a credential). Show "configured" placeholder if set, else empty.
  if (state.profile?.slackWebhookConfigured && !urlInput.dataset.touched) {
    urlInput.placeholder = t("settings.notify.configuredPlaceholder", "(configured — paste new URL to replace)");
    urlInput.value = "";
  }
  thresholdInput.value = String(Math.round((state.profile?.slackFitThreshold ?? 0.7) * 100));
  if (!saveBtn.dataset.bound) {
    saveBtn.dataset.bound = "1";
    saveBtn.addEventListener("click", async () => {
      const body = {};
      const raw = urlInput.value.trim();
      if (raw) body.slackWebhookUrl = raw;
      const pct = Number(thresholdInput.value);
      if (Number.isFinite(pct)) body.slackFitThreshold = Math.max(0, Math.min(1, pct / 100));
      try {
        const payload = await api("/api/profile", { method: "POST", body: JSON.stringify(body) });
        if (payload.profile) state.profile = payload.profile;
        showToast(t("settings.notify.saved", "Notification settings saved."), "success");
        urlInput.value = "";
        urlInput.dataset.touched = "";
        renderNotifySettings();
      } catch (error) {
        showToast(error.message, "error");
      }
    });
    urlInput.addEventListener("input", () => { urlInput.dataset.touched = "1"; });
  }
  if (testBtn && !testBtn.dataset.bound) {
    testBtn.dataset.bound = "1";
    testBtn.addEventListener("click", async () => {
      try {
        const data = await api("/api/profile/slack-test", { method: "POST", body: "{}" });
        const status = data.result?.status || "?";
        if (status === "ok") {
          showToast(t("settings.notify.testOk", "Test sent. Check Slack."), "success");
        } else {
          showToast(t("settings.notify.testFailed", "Test failed: {status}").replace("{status}", status), "error");
        }
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  }
}

function renderPrivacyAudit() {
  const banner = document.getElementById("aiConsentBanner");
  if (banner) {
    const provider = state.aiProvider || {};
    const providerLabel = (state.aiProviderOptions || []).find((p) => p.id === provider.provider_id)?.label || provider.provider_id || "manual";
    const consentNeeded =
      provider.provider_id &&
      provider.provider_id !== "manual" &&
      provider.invocation_mode !== "local_http" &&
      (!state.profile?.aiConsentAt || state.profile?.aiConsentProviderId !== provider.provider_id);
    if (!consentNeeded) {
      banner.hidden = true;
    } else {
      banner.hidden = false;
      banner.replaceChildren();
      const text = document.createElement("p");
      const tpl = t("settings.privacy.consentNeeded", "AI on your CV will be sent to {provider}. Confirm to enable.");
      text.textContent = tpl.replace("{provider}", providerLabel);
      const grant = document.createElement("button");
      grant.type = "button";
      grant.className = "btn btn-primary";
      grant.textContent = t("settings.privacy.grant", "I consent — enable AI");
      grant.addEventListener("click", async () => {
        try {
          await api("/api/profile", {
            method: "POST",
            body: JSON.stringify({ aiConsent: { granted: true, providerId: provider.provider_id } }),
          });
          if (state.profile) {
            state.profile.aiConsentAt = new Date().toISOString();
            state.profile.aiConsentProviderId = provider.provider_id;
          }
          showToast(t("settings.privacy.granted", "Consent recorded."), "success");
          renderPrivacyAudit();
        } catch (error) {
          showToast(error.message, "error");
        }
      });
      banner.append(text, grant);
    }
  }
  const log = document.getElementById("auditLog");
  if (log && log.dataset.loaded !== "1") {
    log.dataset.loaded = "1";
    refreshAuditLog();
  }
  const refreshBtn = document.getElementById("refreshAuditBtn");
  if (refreshBtn && refreshBtn.dataset.bound !== "1") {
    refreshBtn.dataset.bound = "1";
    refreshBtn.addEventListener("click", refreshAuditLog);
  }
}

async function refreshAuditLog() {
  const log = document.getElementById("auditLog");
  if (!log) return;
  try {
    const data = await api("/api/audit-log");
    log.replaceChildren();
    if (!data.events?.length) {
      const empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = t("settings.privacy.empty", "No relevant events yet.");
      log.append(empty);
      return;
    }
    for (const e of data.events) {
      const li = document.createElement("li");
      const when = new Date(e.created_at || e.createdAt || "").toLocaleString();
      li.textContent = `${when} — ${e.kind}`;
      const detail = e.payload && Object.keys(e.payload).length
        ? ` (${Object.entries(e.payload).map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`).join(", ")})`
        : "";
      li.textContent += detail;
      log.append(li);
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderTotpCard() {
  const host = document.getElementById("totpControls");
  const status = document.getElementById("totpStatus");
  if (!host) return;
  const enabled = Boolean(state.auth?.user?.totpEnabled);
  if (status) {
    status.textContent = enabled
      ? t("settings.totp.enabled", "Enabled")
      : t("settings.totp.disabled", "Disabled");
  }
  host.replaceChildren();
  if (enabled) {
    const disableBtn = document.createElement("button");
    disableBtn.type = "button";
    disableBtn.className = "btn";
    disableBtn.textContent = t("settings.totp.disableBtn", "Disable 2FA");
    disableBtn.addEventListener("click", async () => {
      const password = window.prompt(t("settings.totp.disablePrompt", "Enter your password to disable 2FA:"));
      if (!password) return;
      try {
        await api("/api/auth/totp/disable", { method: "POST", body: JSON.stringify({ password }) });
        if (state.auth?.user) state.auth.user.totpEnabled = false;
        showToast(t("settings.totp.disabledToast", "2FA disabled."), "success");
        renderTotpCard();
      } catch (error) {
        showToast(error.message, "error");
      }
    });
    host.append(disableBtn);
    return;
  }
  const enableBtn = document.createElement("button");
  enableBtn.type = "button";
  enableBtn.className = "btn btn-primary";
  enableBtn.textContent = t("settings.totp.enableBtn", "Enable 2FA");
  enableBtn.addEventListener("click", () => beginTotpEnrollment(host));
  host.append(enableBtn);
}

async function beginTotpEnrollment(host) {
  try {
    const enrollment = await api("/api/auth/totp/enroll", { method: "POST", body: "{}" });
    host.replaceChildren();
    const url = enrollment.otpauthUrl || "";
    const secret = enrollment.secret || "";
    const block = document.createElement("div");
    block.className = "totp-enroll";
    const intro = document.createElement("p");
    intro.className = "muted";
    intro.textContent = t("settings.totp.enrollIntro", "Scan this with your authenticator app, then enter the 6-digit code below.");
    const codeEl = document.createElement("code");
    codeEl.textContent = secret;
    const link = document.createElement("a");
    link.href = url;
    link.textContent = t("settings.totp.openInApp", "Open in authenticator app");
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = "numeric";
    input.maxLength = 6;
    input.pattern = "\\d{6}";
    input.placeholder = "123456";
    const submit = document.createElement("button");
    submit.type = "button";
    submit.className = "btn btn-primary";
    submit.textContent = t("settings.totp.confirm", "Confirm code");
    submit.addEventListener("click", async () => {
      try {
        const resp = await api("/api/auth/totp/confirm", {
          method: "POST",
          body: JSON.stringify({ code: input.value.trim() }),
        });
        if (state.auth?.user) state.auth.user.totpEnabled = true;
        showRecoveryCodes(resp.recoveryCodes || []);
        renderTotpCard();
      } catch (error) {
        showToast(error.message, "error");
      }
    });
    block.append(intro, codeEl, document.createElement("br"), link, document.createElement("br"), input, submit);
    host.append(block);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function showRecoveryCodes(codes) {
  if (!codes.length) return;
  const text = codes.join("\n");
  window.alert(t("settings.totp.recoveryAlert", "Save these recovery codes — each works once:") + "\n\n" + text);
}

function renderProfile() {
  // Persona is now a datalist combobox: one input + a <datalist> of
  // human-readable labels. We translate label↔id at save-time so the
  // backend keeps using persona ids.
  const personaInput = $("#profilePersona");
  const datalist = $("#personaDatalist");
  if (!personaInput || !datalist) return;
  const personas = Array.isArray(state.personas) ? state.personas : [];
  const profile = state.profile || {};
  datalist.replaceChildren();
  for (const persona of personas) {
    const opt = document.createElement("option");
    opt.value = persona.label;
    opt.dataset.personaId = persona.id;
    datalist.append(opt);
  }
  // Show the human-readable label for the currently-selected persona.
  const current = personas.find((p) => p.id === profile.personaId);
  personaInput.value = current ? current.label : (personas[0]?.label || "Healthcare management");
  personaInput.dataset.personaId = current ? current.id : (personas[0]?.id || "healthcare-management");
  // Update dataset.personaId on every input so saveProfile knows which id to send.
  if (!personaInput.dataset.bound) {
    personaInput.dataset.bound = "1";
    personaInput.addEventListener("input", () => {
      const match = personas.find((p) => p.label.toLowerCase() === personaInput.value.toLowerCase());
      if (match) personaInput.dataset.personaId = match.id;
    });
  }

  $("#profileIndustry").value = profile.industry || "";
  $("#profileTargetRoles").value = (profile.targetRoles || []).join(", ");
  $("#profileLocation").value = profile.location || "";
  $("#profileSeniority").value = profile.seniority || "";
  $("#profileYearsExperience").value =
    profile.yearsExperience !== null && profile.yearsExperience !== undefined
      ? String(profile.yearsExperience)
      : "";
  $("#profileLanguages").value = (profile.languages || []).join(", ");
  $("#profileCvText").value = profile.cvText || "";
  $("#profileNotes").value = profile.notes || "";
  const hint = $("#profileCvHint");
  if (hint) {
    const length = (profile.cvText || "").length;
    hint.textContent = length
      ? `${length.toLocaleString()} characters of CV stored on this server. Used by AI Brief and cover-letter drafts.`
      : "No CV pasted yet. The AI Brief still works without it but is less personalised.";
  }
}

function renderProvider() {
  const providerSelect = $("#providerId");
  const modeSelect = $("#invocationMode");
  if (!providerSelect) return;
  const selectedId = state.aiProvider.provider_id || "manual";
  const selectedProvider = state.aiProviderOptions.find((o) => o.id === selectedId) || state.aiProviderOptions[0];

  providerSelect.replaceChildren();
  for (const option of state.aiProviderOptions) {
    const node = document.createElement("option");
    node.value = option.id;
    node.textContent = option.label;
    providerSelect.append(node);
  }
  providerSelect.value = selectedId;

  modeSelect.replaceChildren();
  for (const mode of selectedProvider?.invocation_modes || ["manual"]) {
    const node = document.createElement("option");
    node.value = mode;
    node.textContent = mode;
    modeSelect.append(node);
  }
  modeSelect.value = state.aiProvider.invocation_mode || selectedProvider?.invocation_modes?.[0] || "manual";

  $("#providerModel").value = state.aiProvider.model || "";
  $("#credentialReference").value = state.aiProvider.credential_reference || "";
  $("#providerBaseUrl").value = state.aiProvider.base_url || "";
  $("#providerCommand").value = state.aiProvider.command || "";
  $("#providerNotes").value = state.aiProvider.notes || "";
  $("#providerHint").textContent = selectedProvider
    ? `${selectedProvider.secret_hint} ${selectedProvider.notes} Session keys are sent only with Run AI.`
    : "Bring your own AI subscription. Raw secrets are not stored.";

  // Sync the simplified mode-picker to current provider state.
  // Manual = no provider configured. BYOK = provider is set with api/local mode.
  const aiMode = (state.aiProvider.provider_id && state.aiProvider.provider_id !== "manual") ? "byok" : "manual";
  document.querySelectorAll(".ai-mode").forEach((el) => {
    el.setAttribute("aria-checked", String(el.dataset.aiMode === aiMode));
  });
  const byokPane = document.getElementById("aiByokPane");
  if (byokPane) byokPane.hidden = (aiMode !== "byok");
}

// Auto-detect provider id + sensible model from a pasted API key.
function detectProviderFromKey(key) {
  const k = (key || "").trim();
  if (!k) return null;
  if (k.startsWith("sk-ant-")) return { providerId: "anthropic", invocationMode: "api", model: "claude-sonnet-4-5", credRef: "ANTHROPIC_API_KEY" };
  if (k.startsWith("sk-or-")) return { providerId: "openrouter", invocationMode: "api", model: "anthropic/claude-3.5-sonnet", credRef: "OPENROUTER_API_KEY" };
  if (k.startsWith("sk-proj-") || k.startsWith("sk-")) return { providerId: "openai", invocationMode: "api", model: "gpt-4o-mini", credRef: "OPENAI_API_KEY" };
  if (k.startsWith("AIza")) return { providerId: "google_gemini", invocationMode: "api", model: "gemini-2.0-flash-exp", credRef: "GEMINI_API_KEY" };
  return null;
}

(function bootAiModePicker() {
  document.addEventListener("click", async (event) => {
    const modeBtn = event.target.closest(".ai-mode");
    if (modeBtn && !modeBtn.disabled) {
      const mode = modeBtn.dataset.aiMode;
      document.querySelectorAll(".ai-mode").forEach((el) => {
        el.setAttribute("aria-checked", String(el === modeBtn));
      });
      const byokPane = document.getElementById("aiByokPane");
      if (mode === "manual") {
        if (byokPane) byokPane.hidden = true;
        try {
          await api("/api/ai-provider", {
            method: "POST",
            body: JSON.stringify({ providerId: "manual", invocationMode: "manual" }),
          });
          showToast(t("settings.ai.savedManual", "Set to manual mode."), "success");
          state.aiProvider.provider_id = "manual";
          state.aiProvider.invocation_mode = "manual";
          renderProvider();
        } catch (error) {
          showToast(error.message, "error");
        }
      } else if (mode === "byok") {
        if (byokPane) byokPane.hidden = false;
        document.getElementById("aiByokKey")?.focus();
      } else if (mode === "managed") {
        // Real Stripe checkout is operator-pending; we collect waitlist
        // signups via the analytics_events log so we can email when ready.
        try {
          const res = await api("/api/managed-ai/waitlist", { method: "POST", body: "{}" });
          if (res.status === "already_on_waitlist") {
            showToast(t("settings.ai.managed.alreadyJoined", "You're already on the waitlist — we'll email you when it opens."), "info");
          } else {
            showToast(t("settings.ai.managed.joined", "Added to waitlist. Thanks — we'll email you when it opens."), "success");
          }
        } catch (error) {
          showToast(error.message, "error");
        }
        // Re-select the previous mode visually since "managed" isn't actually active yet.
        const currentMode = (state.aiProvider.provider_id && state.aiProvider.provider_id !== "manual") ? "byok" : "manual";
        document.querySelectorAll(".ai-mode").forEach((el) => {
          el.setAttribute("aria-checked", String(el.dataset.aiMode === currentMode));
        });
        if (byokPane) byokPane.hidden = (currentMode !== "byok");
      }
      return;
    }
    if (event.target?.id === "aiByokSaveBtn") {
      event.preventDefault();
      const keyInput = document.getElementById("aiByokKey");
      const key = (keyInput?.value || "").trim();
      const detected = detectProviderFromKey(key);
      if (!detected) {
        showToast(t("settings.ai.byok.unrecognised", "Unrecognised key shape. Use OpenAI (sk-…), Anthropic (sk-ant-…), Google (AIza…) or OpenRouter (sk-or-…)."), "error");
        return;
      }
      try {
        await api("/api/ai-provider", {
          method: "POST",
          body: JSON.stringify({
            providerId: detected.providerId,
            invocationMode: detected.invocationMode,
            model: detected.model,
            credentialReference: detected.credRef,
          }),
        });
        state.aiProvider.provider_id = detected.providerId;
        state.aiProvider.invocation_mode = detected.invocationMode;
        state.aiProvider.model = detected.model;
        state.aiProvider.credential_reference = detected.credRef;
        // Stash the raw key in the in-memory session-credential store
        // so subsequent AI calls in this tab use it without re-prompting.
        state.sessionAiKey = key;
        if (keyInput) keyInput.value = "";
        renderProvider();
        showToast(t("settings.ai.byok.connected", "Connected. Provider: {label}").replace("{label}", detected.providerId), "success");
      } catch (error) {
        showToast(error.message, "error");
      }
    }
  });
})();

function makeTag(text, kind) {
  const span = document.createElement("span");
  span.className = `tag${kind ? " " + kind : ""}`;
  span.textContent = text;
  return span;
}

function renderAdminUsers() {
  const list = $("#adminUsersList");
  if (!list) return;
  list.replaceChildren();
  if (!isAdmin()) return;
  if (!state.adminUsers.length) {
    list.append(emptyNode("No tester accounts loaded yet."));
    return;
  }
  for (const user of state.adminUsers) {
    const row = document.createElement("article");
    row.className = `admin-user${user.active ? "" : " inactive"}`;
    const info = document.createElement("div");
    info.className = "admin-user-info";
    const title = document.createElement("strong");
    title.textContent = user.email;
    const meta = document.createElement("span");
    meta.append(makeTag(user.role === "admin" ? "Admin" : "Tester", user.role === "admin" ? "admin" : ""));
    if (!user.active) {
      meta.append(document.createTextNode(" "));
      meta.append(makeTag("Inactive", "inactive"));
    }
    if (user.id === state.auth.user?.id) {
      meta.append(document.createTextNode(" "));
      meta.append(makeTag("You", "you"));
    }
    meta.append(document.createTextNode(` · created ${new Date(user.createdAt).toLocaleDateString()}`));
    info.append(title, meta);

    const controls = document.createElement("div");
    controls.className = "admin-user-controls";
    const isCurrentUser = user.id === state.auth.user?.id;

    const role = document.createElement("select");
    role.disabled = isCurrentUser;
    role.title = isCurrentUser ? "You can't change your own role" : "Change role";
    const memberOpt = document.createElement("option");
    memberOpt.value = "member";
    memberOpt.textContent = "Tester";
    const adminOpt = document.createElement("option");
    adminOpt.value = "admin";
    adminOpt.textContent = "Admin";
    role.append(memberOpt, adminOpt);
    role.value = user.role;

    const saveRole = document.createElement("button");
    saveRole.type = "button";
    saveRole.className = "btn";
    saveRole.textContent = "Save role";
    saveRole.disabled = isCurrentUser;
    saveRole.addEventListener("click", async () => {
      if (role.value === user.role) return;
      const ok = await confirmDialog({
        title: role.value === "admin" ? "Promote to admin?" : "Demote to tester?",
        body: `${user.email} will ${role.value === "admin" ? "gain" : "lose"} admin access immediately.`,
        confirmLabel: role.value === "admin" ? "Promote" : "Demote",
        danger: role.value !== "admin",
      });
      if (ok) updateAdminUser(user.id, { role: role.value });
    });

    const active = document.createElement("button");
    active.type = "button";
    active.className = `btn ${user.active ? "btn-danger" : "btn-primary"}`;
    active.textContent = user.active ? "Deactivate" : "Activate";
    active.disabled = isCurrentUser;
    active.title = isCurrentUser ? "You can't deactivate yourself" : "";
    active.addEventListener("click", async () => {
      const ok = await confirmDialog({
        title: user.active ? "Deactivate this account?" : "Activate this account?",
        body: user.active
          ? `${user.email} will be signed out and unable to sign in until reactivated.`
          : `${user.email} will be able to sign in again.`,
        confirmLabel: user.active ? "Deactivate" : "Activate",
        danger: user.active,
      });
      if (ok) updateAdminUser(user.id, { active: !user.active });
    });

    const pwWrap = document.createElement("div");
    pwWrap.className = "pw-inline";
    const password = document.createElement("input");
    password.type = "password";
    password.placeholder = "New password";
    password.minLength = 12;
    password.autocomplete = "new-password";
    password.disabled = isCurrentUser;
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "btn";
    reset.textContent = "Reset password";
    reset.disabled = isCurrentUser;
    reset.addEventListener("click", async () => {
      if (!password.value || password.value.length < 12) {
        showToast("New password must be at least 12 characters.", "error");
        return;
      }
      const ok = await confirmDialog({
        title: "Reset this tester's password?",
        body: `${user.email} will be signed out and must use the new password to sign in.`,
        confirmLabel: "Reset",
        danger: true,
      });
      if (!ok) return;
      try {
        await updateAdminUser(user.id, { password: password.value });
        password.value = "";
      } catch (error) {
        showToast(error.message, "error");
      }
    });
    pwWrap.append(password, reset);

    controls.append(role, saveRole, active, pwWrap);
    row.append(info, controls);
    list.append(row);
  }
}

/* ---------- Helpers ---------- */

function setFormStatus(elementOrId, state, text) {
  // state: "saving" | "success" | "error" | "" (clear)
  const el = typeof elementOrId === "string" ? document.getElementById(elementOrId) : elementOrId;
  if (!el) return;
  el.classList.remove("is-saving", "is-success", "is-error");
  if (state) el.classList.add(`is-${state}`, "form-status");
  if (!el.classList.contains("form-status")) el.classList.add("form-status");
  el.textContent = text || "";
}

function emptyNode(text, options) {
  // Options: { icon: "search" | "briefcase" | "company" | "list",
  //           ctaText: string, onCta: fn }
  const opts = options || {};
  const node = document.createElement("div");
  node.className = "empty";
  if (opts.icon) {
    const ic = document.createElement("div");
    ic.className = "empty-icon";
    ic.innerHTML = EMPTY_ICONS[opts.icon] || "";
    if (ic.innerHTML) node.append(ic);
  }
  const p = document.createElement("p");
  p.textContent = text;
  node.append(p);
  if (opts.ctaText && opts.onCta) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-primary";
    btn.textContent = opts.ctaText;
    btn.addEventListener("click", opts.onCta);
    node.append(btn);
  }
  return node;
}

// Reusable empty-state SVG icons. Match the queue-empty visual so the
// app feels consistent across surfaces.
const EMPTY_ICONS = {
  search: '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="22" cy="22" r="12"/><path d="M31 31 L40 40"/></svg>',
  briefcase: '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="14" width="32" height="26" rx="3"/><path d="M18 14 V10 a2 2 0 0 1 2-2 h8 a2 2 0 0 1 2 2 v4"/><path d="M8 24 H40"/></svg>',
  company: '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 40 V14 a2 2 0 0 1 2-2 h14 a2 2 0 0 1 2 2 v26"/><path d="M28 40 V22 a2 2 0 0 1 2-2 h6 a2 2 0 0 1 2 2 v18"/><path d="M16 20 h4 M16 26 h4 M16 32 h4 M32 26 h2 M32 32 h2"/></svg>',
  list: '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14 H38 M14 22 H38 M14 30 H30"/><circle cx="9" cy="14" r="1.5" fill="currentColor"/><circle cx="9" cy="22" r="1.5" fill="currentColor"/><circle cx="9" cy="30" r="1.5" fill="currentColor"/></svg>',
  saved: '<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 8 H34 a2 2 0 0 1 2 2 V40 L24 32 L12 40 V10 a2 2 0 0 1 2-2 z"/></svg>',
};

function relativeTimeFromIso(iso) {
  // Returns short i18n'd relative-time strings like "just now", "5m ago",
  // "2h ago", "3d ago". Empty string when iso is missing/invalid.
  if (!iso) return "";
  let ts;
  try { ts = new Date(iso); } catch (_) { return ""; }
  if (Number.isNaN(ts.getTime())) return "";
  const deltaMs = Date.now() - ts.getTime();
  const minutes = Math.floor(deltaMs / 60_000);
  const hours = Math.floor(deltaMs / 3_600_000);
  const days = Math.floor(deltaMs / 86_400_000);
  if (days >= 1) return t("timeline.daysAgo", "{n}d ago").replace("{n}", String(days));
  if (hours >= 1) return t("timeline.hoursAgo", "{n}h ago").replace("{n}", String(hours));
  if (minutes >= 1) return t("timeline.minutesAgo", "{n}m ago").replace("{n}", String(minutes));
  return t("timeline.justNow", "just now");
}

function jobEffectiveFreshness(job) {
  // Prefer also_seen_at re-sightings (max), else discovered_at.
  const candidates = [];
  if (job?.discovered_at) candidates.push(job.discovered_at);
  for (const entry of Object.values(job?.also_seen_at || {})) {
    if (entry && typeof entry === "object") {
      const seen = entry.seen_at || entry.found_at || entry.at;
      if (seen) candidates.push(seen);
    }
  }
  if (!candidates.length) return null;
  return candidates.sort().slice(-1)[0];
}

function skeletonRows(count = 3) {
  // Vertical stack of placeholder rows that look like real list items
  // while data fetches. Use sparingly — empty-state still wins for "no
  // results", skeletons are only for "loading first time".
  const wrap = document.createDocumentFragment();
  for (let i = 0; i < count; i += 1) {
    const row = document.createElement("div");
    row.className = "skeleton-row";
    const title = document.createElement("span");
    title.className = "skeleton title";
    const sub = document.createElement("span");
    sub.className = "skeleton sub";
    const tagsRow = document.createElement("div");
    tagsRow.style.display = "flex";
    tagsRow.style.gap = "6px";
    for (let j = 0; j < 3; j += 1) {
      const t = document.createElement("span");
      t.className = "skeleton tag";
      tagsRow.append(t);
    }
    row.append(title, sub, tagsRow);
    wrap.append(row);
  }
  return wrap;
}

function shortUrl(value) {
  try {
    const url = new URL(value);
    return `${url.hostname}${url.pathname}`;
  } catch {
    return value || "";
  }
}

/* ---------- Mutations ---------- */

async function createCompany(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  data.watchEnabled = form.watchEnabled.checked;
  try {
    const payload = await api("/api/companies", {
      method: "POST",
      body: JSON.stringify(data),
    });
    absorbBootstrap(payload.bootstrap);
    state.selectedCompanyId = payload.company.id;
    form.reset();
    form.watchEnabled.checked = true;
    showToast(`Added ${payload.company.name}.`, "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function saveDetail() {
  const company = selectedCompany();
  if (!company) return;
  try {
    const payload = await api(`/api/companies/${company.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        websiteUrl: $("#detailWebsite").value,
        careerPageUrl: $("#detailCareer").value,
        sector: $("#detailSector").value,
        notes: $("#detailNotes").value,
        watchEnabled: $("#detailWatch").checked,
      }),
    });
    absorbBootstrap(payload.bootstrap);
    showToast(t("toast.saved", "Saved."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteCompany() {
  const company = selectedCompany();
  if (!company) return;
  const ok = await confirmDialog({
    title: "Delete this company?",
    body: `${company.name} and all of its discovered jobs and scan history will be removed. This can't be undone.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  try {
    const payload = await api(`/api/companies/${company.id}`, { method: "DELETE" });
    absorbBootstrap(payload.bootstrap);
    showToast(t("toast.companyDeleted", "Company deleted."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function findCareerPage() {
  const company = selectedCompany();
  if (!company) return;
  try {
    const payload = await api(`/api/companies/${company.id}/find-career-page`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    const status = payload.result.status;
    const message = status === "found"
      ? `Found career page: ${payload.result.careerPageUrl}`
      : status === "not_found"
      ? "Could not find a career page link. Add it manually."
      : SCAN_STATUS_COPY[status] || status;
    showToast(message, status === "found" ? "success" : "info");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function scanCompany() {
  const company = selectedCompany();
  if (!company) return;
  try {
    const payload = await api(`/api/companies/${company.id}/scan`, {
      method: "POST",
      body: JSON.stringify({ careerPageUrl: $("#detailCareer").value }),
    });
    absorbBootstrap(payload.bootstrap);
    const run = payload.run || {};
    const status = run.status || "completed";
    // Find the matching scan record on the bootstrap so we can quote new + merged counts.
    const scan = (state.scans || []).find((s) => s.company_id === company.id);
    let summary = translateScanStatus(status) || status;
    if (scan) {
      const merged = (scan.errors || []).find((e) => e.code === "merged_sources_total");
      const mergedCount = merged ? merged.count : 0;
      const newCount = scan.jobs_found || 0;
      const newLabel = t("scanResult.newRoles", "new role" + (newCount === 1 ? "" : "s"));
      summary = `${newCount} ${newLabel}`;
      if (mergedCount > 0) {
        const mergedLabel = t("scanResult.mergedSources", "source" + (mergedCount === 1 ? "" : "s") + " merged");
        summary += ` · ${mergedCount} ${mergedLabel}`;
      }
    }
    const toastKind = status === "queued" || status === "running" ? "info" : "success";
    showToast(summary, toastKind);
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function scanWatchlist() {
  try {
    const payload = await api("/api/watchlist/scan", {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    const queued = payload.result.runs?.length || 0;
    const skipped = payload.result.skipped?.length || 0;
    showToast(queued ? `Queued ${queued} scan${queued === 1 ? "" : "s"} · ${skipped} skipped.` : "Nothing to check yet.", "info");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function saveSchedule() {
  try {
    const payload = await api("/api/watchlist/schedule", {
      method: "POST",
      body: JSON.stringify({
        enabled: $("#scheduleEnabled").checked,
        intervalMinutes: Number($("#scheduleInterval").value || 360),
      }),
    });
    absorbBootstrap(payload.bootstrap);
    showToast(t("toast.scheduleSaved", "Schedule saved."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function seedDemo() {
  try {
    const payload = await api("/api/demo/seed", {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    state.selectedCompanyId = payload.demo.company.id;
    showToast(t("toast.demoAdded", "Demo company added."), "success");
    navigate("companies");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function extractManualHtml() {
  const company = selectedCompany();
  if (!company) return;
  try {
    const payload = await api(`/api/companies/${company.id}/extract-html`, {
      method: "POST",
      body: JSON.stringify({
        pageUrl: $("#manualPageUrl").value,
        html: $("#manualHtml").value,
      }),
    });
    absorbBootstrap(payload.bootstrap);
    showToast(`Manual import · ${payload.jobs.length} role${payload.jobs.length === 1 ? "" : "s"} added.`, "success");
    $("#manualHtml").value = "";
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function importJob(id) {
  try {
    const payload = await api(`/api/discovered-jobs/${id}/import`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    state.selectedImportedJobId = payload.job.id;
    showToast(t("toast.imported", "Imported. Open AI Brief to prepare a brief."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function prepareBrief(importedJobId) {
  if (!importedJobId) return;
  try {
    const payload = await api(`/api/imported-jobs/${importedJobId}/prepare-brief`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    state.analysisBrief = payload.brief;
    state.selectedImportedJobId = importedJobId;
    $("#briefMeta").textContent = `${payload.brief.title} · ${payload.brief.providerLabel} (${payload.brief.invocationMode})`;
    $("#briefPrompt").value = payload.brief.prompt;
    navigate("brief");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function prepareCoverLetter(importedJobId) {
  if (!importedJobId) return;
  try {
    const payload = await api(`/api/imported-jobs/${importedJobId}/prepare-cover-letter`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.analysisBrief = payload.brief;
    $("#briefMeta").textContent = `${payload.brief.title} · ${payload.brief.providerLabel} (${payload.brief.invocationMode})`;
    $("#briefPrompt").value = payload.brief.prompt;
    showToast("Cover-letter prompt ready in the AI Brief view.", "info");
    navigate("brief");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function draftCoverLetter(importedJobId) {
  if (!importedJobId) return;
  const credentialValue = $("#providerRuntimeKey")?.value || "";
  const statusEl = $("#coverLetterStatus");
  if (statusEl) statusEl.textContent = "Drafting…";
  try {
    const payload = await api(`/api/imported-jobs/${importedJobId}/draft-cover-letter`, {
      method: "POST",
      body: JSON.stringify({ credentialValue }),
    });
    absorbBootstrap(payload.bootstrap);
    const draft = payload.draft || {};
    if (statusEl) {
      statusEl.textContent = draft.status === "completed"
        ? "Draft ready below — edit before sending."
        : `Status: ${draft.status}${draft.error ? " — " + draft.error : ""}`;
    }
    if (draft.status === "completed" && draft.output) {
      $("#applicationCoverLetter").value = draft.output;
      showToast("Cover letter drafted.", "success");
    } else if (draft.status === "handoff_required") {
      showToast("AI provider not configured — copy the prompt instead (Cover-letter prompt button).", "info");
    } else {
      showToast(`Cover letter ${draft.status}.`, "info");
    }
    if ($("#providerRuntimeKey")) $("#providerRuntimeKey").value = "";
    render();
  } catch (error) {
    if (statusEl) statusEl.textContent = "Error.";
    showToast(error.message, "error");
  }
}

function showPersonaSuggestionPrompt(suggestion, message) {
  // Render a compact banner above the persona dropdown with an Apply button.
  // Auto-clears once applied or after 30s.
  const host = document.querySelector("#personaSuggestionHost");
  if (!host) {
    showToast(message, "info");
    return;
  }
  host.replaceChildren();
  const banner = document.createElement("div");
  banner.className = "persona-suggestion";
  const text = document.createElement("span");
  text.textContent = message;
  banner.append(text);
  const apply = document.createElement("button");
  apply.type = "button";
  apply.className = "btn btn-primary";
  apply.textContent = t("settings.persona.applySuggestion", "Apply");
  apply.addEventListener("click", async () => {
    try {
      // Update the datalist combobox to show the new persona's label.
      const personaInput = $("#profilePersona");
      if (personaInput) {
        const match = (state.personas || []).find((p) => p.id === suggestion.personaId);
        personaInput.value = match?.label || suggestion.personaId;
        personaInput.dataset.personaId = suggestion.personaId;
      }
      await api("/api/profile", {
        method: "POST",
        body: JSON.stringify({ personaId: suggestion.personaId }),
      });
      showToast(t("settings.persona.applied", "Persona updated."), "success");
      host.replaceChildren();
      render();
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "btn btn-ghost";
  dismiss.textContent = t("settings.persona.dismissSuggestion", "Keep current");
  dismiss.addEventListener("click", () => host.replaceChildren());
  banner.append(apply, dismiss);
  host.append(banner);
  setTimeout(() => host.replaceChildren(), 30_000);
}

async function handleCvUpload(event) {
  const input = event.target;
  const file = input?.files?.[0];
  if (!file) return;
  const status = $("#cvUploadStatus");
  if (status) status.textContent = `Uploading ${file.name}…`;
  try {
    const arrayBuffer = await file.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
    const contentBase64 = btoa(binary);
    const payload = await api("/api/profile/cv-upload", {
      method: "POST",
      body: JSON.stringify({ filename: file.name, contentBase64 }),
    });
    state.profile = payload.profile || state.profile;
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    if (status) status.textContent = `Imported ${payload.extractedChars || 0} chars from ${file.name}.`;
    showToast(t("toast.cvUploaded", "CV uploaded."), "success");
    // Surface persona-fit suggestion if the server matched one strongly.
    const suggestions = payload.personaSuggestions || [];
    const top = suggestions[0];
    if (top && top.personaId && top.personaId !== state.profile?.personaId) {
      const tpl = t("settings.persona.suggested", "Best fit from your CV: {label}. Apply?");
      const msg = tpl.replace("{label}", top.label);
      // Use a confirm-style toast: tap-to-apply.
      showPersonaSuggestionPrompt(top, msg);
    }
    render();
  } catch (error) {
    if (status) status.textContent = `Error: ${error.message}`;
    showToast(error.message, "error");
  } finally {
    if (input) input.value = "";
  }
}

async function saveProfile() {
  const personaInput = $("#profilePersona");
  if (!personaInput) return;
  const personaId = personaInput.dataset.personaId
    || (state.personas || []).find((p) => p.label.toLowerCase() === (personaInput.value || "").toLowerCase())?.id
    || "healthcare-management";
  const yearsRaw = $("#profileYearsExperience").value.trim();
  const body = {
    personaId,
    industry: $("#profileIndustry").value.trim(),
    targetRoles: $("#profileTargetRoles").value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    location: $("#profileLocation").value.trim(),
    seniority: $("#profileSeniority").value.trim(),
    yearsExperience: yearsRaw === "" ? null : Number(yearsRaw),
    languages: $("#profileLanguages").value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    cvText: $("#profileCvText").value,
    notes: $("#profileNotes").value.trim(),
  };
  setFormStatus("profileMessage", "saving", t("form.saving", "Saving…"));
  try {
    const payload = await api("/api/profile", {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.profile = payload.profile || state.profile;
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    setFormStatus("profileMessage", "success", t("form.saved", "Saved."));
    render();
  } catch (error) {
    setFormStatus("profileMessage", "error", error.message);
    showToast(error.message, "error");
  }
}

async function runAnalysis(importedJobId) {
  if (!importedJobId) return;
  const credentialValue = $("#providerRuntimeKey")?.value || "";
  try {
    const payload = await api(`/api/imported-jobs/${importedJobId}/analyze`, {
      method: "POST",
      body: JSON.stringify({ credentialValue }),
    });
    absorbBootstrap(payload.bootstrap);
    state.analysisBrief = payload.analysis;
    $("#briefMeta").textContent = `Analysis ${payload.analysis.status} · ${payload.analysis.provider_id} (${payload.analysis.invocation_mode})`;
    $("#briefPrompt").value = payload.analysis.output || payload.analysis.error || payload.analysis.prompt || "";
    if ($("#providerRuntimeKey")) $("#providerRuntimeKey").value = "";
    showToast(payload.analysis.status === "completed" ? "Analysis ready." : `Analysis ${payload.analysis.status}.`, payload.analysis.status === "completed" ? "success" : "info");
    navigate("brief");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function suggestCompanies() {
  try {
    const payload = await api("/api/suggest-companies", {
      method: "POST",
      body: JSON.stringify({
        targetRoles: $("#targetRoles").value.split(",").map((s) => s.trim()).filter(Boolean),
        industry: $("#targetIndustry").value,
        location: $("#targetLocation").value,
      }),
    });
    renderSuggestions(payload.suggestions);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function addSuggestedCompany(item) {
  const existing = state.companies.find((c) => {
    return c.website_url === item.website_url || c.name.toLowerCase() === item.name.toLowerCase();
  });
  if (existing) {
    state.selectedCompanyId = existing.id;
    showToast(`${existing.name} is already on your watchlist.`, "info");
    render();
    return;
  }
  try {
    const payload = await api("/api/companies", {
      method: "POST",
      body: JSON.stringify({
        name: item.name,
        websiteUrl: item.website_url,
        careerPageUrl: item.career_page_url,
        sector: item.sector,
        notes: item.relevanceReason,
        watchEnabled: Boolean(item.watchEnabled),
      }),
    });
    absorbBootstrap(payload.bootstrap);
    state.selectedCompanyId = payload.company.id;
    showToast(`Added ${payload.company.name}.`, "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function saveProvider() {
  try {
    const payload = await api("/api/ai-provider", {
      method: "POST",
      body: JSON.stringify({
        providerId: $("#providerId").value,
        invocationMode: $("#invocationMode").value,
        model: $("#providerModel").value,
        credentialReference: $("#credentialReference").value,
        baseUrl: $("#providerBaseUrl").value,
        command: $("#providerCommand").value,
        notes: $("#providerNotes").value,
      }),
    });
    absorbBootstrap(payload.bootstrap);
    showToast(t("toast.providerSaved", "Provider saved."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadAdminUsers() {
  if (!isAdmin()) return;
  const payload = await api("/api/admin/users");
  state.adminUsers = payload.users || [];
  renderAdminUsers();
  loadInvitations().catch((error) => showToast(error.message, "error"));
}

async function loadInvitations() {
  if (!isAdmin()) return;
  const payload = await api("/api/admin/invitations");
  renderInvitations(payload.invitations || []);
}

function renderInvitations(items) {
  const list = $("#invitationList");
  if (!list) return;
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyNode("No active invitations."));
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "invitation-row";
    const left = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.email;
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = `${item.role} · expires ${new Date(item.expiresAt).toLocaleString()}`;
    left.append(title, meta);
    const pill = document.createElement("span");
    pill.className = "invite-pill";
    pill.textContent = "Pending";
    row.append(left, pill);
    list.append(row);
  }
}

async function refreshAdminMetrics() {
  if (!isAdmin()) return;
  try {
    const payload = await api("/api/admin/metrics");
    const out = $("#metricsResult");
    out.hidden = false;
    out.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function createAdminUser(event) {
  event.preventDefault();
  try {
    const payload = await api("/api/admin/users", {
      method: "POST",
      body: JSON.stringify({
        email: $("#newUserEmail").value,
        password: $("#newUserPassword").value,
        role: $("#newUserRole").value,
      }),
    });
    state.adminUsers = payload.users || [];
    $("#newUserEmail").value = "";
    $("#newUserPassword").value = "";
    $("#newUserRole").value = "member";
    showToast(`Created ${payload.user.email}.`, "success");
    renderAdminUsers();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function updateAdminUser(userId, update) {
  const payload = await api(`/api/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });
  state.adminUsers = payload.users || [];
  renderAdminUsers();
  if (update.password) showToast("Password reset.", "success");
  else if ("active" in update) showToast(update.active ? "Account activated." : "Account deactivated.", "success");
  else if ("role" in update) showToast(`Role updated to ${update.role}.`, "success");
}

async function login(event) {
  event.preventDefault();
  $("#authMessage").textContent = "";
  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("#loginEmail").value,
        password: $("#loginPassword").value,
      }),
    });
    if (payload.requires2fa) {
      $("#loginPassword").value = "";
      const code = window.prompt(t("auth.totp.prompt", "Enter the 6-digit code from your authenticator app (or a recovery code):"));
      if (!code) {
        $("#authMessage").textContent = t("auth.totp.cancelled", "Sign-in cancelled.");
        return;
      }
      const verified = await api("/api/auth/2fa-verify", {
        method: "POST",
        body: JSON.stringify({ challengeToken: payload.challengeToken, code: code.trim() }),
      });
      state.auth = { authenticated: true, user: verified.user, registrationOpen: false };
      absorbBootstrap(verified.bootstrap);
      renderAuth();
      render();
      if (isAdmin()) await loadAdminUsers();
      return;
    }
    state.auth = { authenticated: true, user: payload.user, registrationOpen: false };
    absorbBootstrap(payload.bootstrap);
    $("#loginPassword").value = "";
    renderAuth();
    render();
    if (isAdmin()) await loadAdminUsers();
  } catch (error) {
    $("#authMessage").textContent = error.message;
  }
}

async function register(event) {
  event.preventDefault();
  $("#authMessage").textContent = "";
  try {
    const payload = await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: $("#registerEmail").value,
        password: $("#registerPassword").value,
      }),
    });
    state.auth = { authenticated: true, user: payload.user, registrationOpen: false };
    absorbBootstrap(payload.bootstrap);
    $("#registerPassword").value = "";
    renderAuth();
    render();
  } catch (error) {
    $("#authMessage").textContent = error.message;
  }
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
  } catch {
    /* clear local state regardless */
  }
  clearAuthenticatedState();
  renderAuth();
}

async function changePassword(event) {
  event.preventDefault();
  setFormStatus("accountMessage", "saving", t("form.saving", "Saving…"));
  try {
    await api("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        currentPassword: $("#currentPassword").value,
        newPassword: $("#newPassword").value,
      }),
    });
    $("#currentPassword").value = "";
    $("#newPassword").value = "";
    clearAuthenticatedState();
    renderAuth();
    $("#authMessage").textContent = t("auth.passwordChanged", "Password changed. Sign in with the new password.");
  } catch (error) {
    setFormStatus("accountMessage", "error", error.message);
  }
}

async function exportData() {
  try {
    const payload = await api("/api/data/export");
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `directjob-scout-backup-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    const ops = $("#opsResult");
    ops.hidden = false;
    ops.textContent = JSON.stringify({ status: "exported", companies: payload.companies.length, jobs: payload.discoveredJobs.length }, null, 2);
    showToast("Backup downloaded.", "success");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function importDataFromFile(event) {
  const file = event.currentTarget.files?.[0];
  if (!file) return;
  const text = await file.text();
  try {
    const payload = await api("/api/data/import", { method: "POST", body: text });
    absorbBootstrap(payload.bootstrap);
    const ops = $("#opsResult");
    ops.hidden = false;
    ops.textContent = JSON.stringify(payload.result, null, 2);
    showToast("Backup imported.", "success");
    event.currentTarget.value = "";
    render();
  } catch (error) {
    showToast(error.message, "error");
    event.currentTarget.value = "";
  }
}

async function checkHealth() {
  try {
    const payload = await api("/api/health");
    const ops = $("#opsResult");
    ops.hidden = false;
    ops.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderSuggestions(suggestions) {
  const list = $("#suggestionsList");
  list.replaceChildren();
  for (const item of (suggestions || []).slice(0, 12)) {
    const node = document.createElement("div");
    node.className = "suggestion";
    const title = document.createElement("strong");
    title.textContent = item.name || item.category;
    const meta = document.createElement("span");
    meta.textContent = item.type === "company"
      ? `${item.sector || "Company"} · ${item.location_hint || item.locationHint || "Location flexible"}`
      : "Category suggestion";
    const reason = document.createElement("span");
    reason.textContent = item.relevanceReason;
    const score = document.createElement("span");
    score.className = "suggestion-score";
    score.textContent = `${Math.round(item.relevanceScore * 100)}% match`;
    node.append(title, meta, reason, score);
    if (item.type === "company") {
      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "btn btn-small";
      addBtn.textContent = "Add to watchlist";
      addBtn.addEventListener("click", () => addSuggestedCompany(item));
      node.append(addBtn);
    }
    list.append(node);
  }
}

/* ---------- Polling ---------- */

function scheduleRunPolling() {
  const active = state.discoveryRuns.some((r) => ["queued", "running"].includes(r.status));
  if (!active || state.pollTimer) return;
  state.pollTimer = window.setTimeout(async () => {
    state.pollTimer = null;
    try {
      const payload = await api("/api/bootstrap");
      absorbBootstrap(payload);
      render();
    } catch {
      /* setStatus already covers this */
    }
  }, 1500);
}

/* ---------- Phase 2/3 handlers ---------- */

async function applyWatchlistTemplate(templateId) {
  try {
    const payload = await api(`/api/watchlist-templates/${encodeURIComponent(templateId)}/apply`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    const added = payload.result.added.length;
    const skipped = payload.result.skipped.length;
    showToast(`Template applied · ${added} added, ${skipped} skipped.`, added ? "success" : "info");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function saveCurrentSearch() {
  const name = window.prompt("Name this search?");
  if (!name) return;
  try {
    const payload = await api("/api/saved-searches", {
      method: "POST",
      body: JSON.stringify({
        name,
        targetRoles: $("#targetRoles").value.split(",").map((s) => s.trim()).filter(Boolean),
        industry: $("#targetIndustry").value,
        location: $("#targetLocation").value,
      }),
    });
    state.savedSearches = payload.savedSearches;
    renderSavedSearches();
    showToast("Search saved.", "success");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteSavedSearch(id) {
  const ok = await confirmDialog({
    title: "Delete saved search?",
    body: "This only removes the saved combination, not your watchlist.",
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  try {
    const payload = await api(`/api/saved-searches/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.savedSearches = payload.savedSearches;
    renderSavedSearches();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function findJobs(event) {
  if (event) event.preventDefault();
  const query = ($("#findJobsQuery")?.value || "").trim();
  const location = ($("#findJobsLocation")?.value || "").trim();
  const limit = Number($("#findJobsLimit")?.value || 15);
  const status = $("#findJobsStatus");
  const results = $("#findJobsResults");
  const attributions = $("#findJobsAttributions");
  if (status) status.textContent = t("findJobs.searching", "Searching across providers…");
  if (results) {
    results.replaceChildren();
    // Show 4 skeleton rows so the user feels something is happening
    // even before the first byte lands.
    results.append(skeletonRows(4));
  }
  try {
    const clamped = Math.max(5, Math.min(50, limit));
    const payload = await api("/api/jobs/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        location: location || null,
        limitPerProvider: clamped,
        // Total cap should track what the user asked for, not the
        // server's default of 50 — otherwise raising "Per provider"
        // above ~7 (with 6+ providers) silently hits the cap.
        cap: Math.min(200, clamped * 7),
      }),
    });
    const jobs = payload.jobs || [];
    if (status) {
      const counts = (payload.outcomes || [])
        .filter((o) => o.jobCount > 0)
        .map((o) => `${o.provider} ${o.jobCount}${o.cached ? " ⚡" : ""}`)
        .join(" · ");
      status.textContent = `${jobs.length} ${t("queue.toolbar.sort.discovered", "results")} · ${counts}`;
    }
    if (results) {
      // Clear skeletons before painting the real results.
      results.replaceChildren();
      if (jobs.length === 0) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = t("findJobs.empty", "No results yet. Try a different query or location.");
        results.append(empty);
      } else {
        for (const job of jobs.slice(0, 50)) {
          const row = document.createElement("div");
          row.className = "find-jobs-row";
          const title = document.createElement("a");
          title.href = job.sourceUrl;
          title.target = "_blank";
          title.rel = "noopener";
          title.textContent = job.title || "(untitled)";
          title.className = "find-jobs-title";
          const meta = document.createElement("span");
          meta.className = "muted small";
          const locStr = job.location ? ` · ${job.location}` : "";
          meta.textContent = `${job.companyName || "?"}${locStr}`;
          const sourceTag = document.createElement("span");
          sourceTag.className = "tag";
          sourceTag.textContent = job.source;
          row.append(title, document.createElement("br"), meta, document.createTextNode(" "), sourceTag);
          results.append(row);
        }
      }
    }
    if (attributions) {
      const list = (payload.attributions || []).map((a) => `<a href="${a.url}" target="_blank" rel="noopener">${a.label}</a>`).join(" · ");
      attributions.innerHTML = list ? `${t("findJobs.poweredBy", "Powered by:")} ${list}` : "";
    }
  } catch (error) {
    if (status) status.textContent = `Error: ${error.message}`;
    if (results) results.replaceChildren();
    showToast(error.message, "error");
  }
}

async function runSavedSearchNow(searchId) {
  try {
    const payload = await api(`/api/saved-searches/${encodeURIComponent(searchId)}/run-now`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (payload.bootstrap) absorbBootstrap(payload.bootstrap);
    const result = payload.result || {};
    const newJobs = result.newJobs || 0;
    const merged = result.mergedSources || 0;
    const candidates = result.candidates || 0;
    const summary = `${newJobs} ${t("savedSearch.newJobs", "new")} · ${merged} ${t("savedSearch.merged", "merged")} · ${candidates} ${t("savedSearch.candidates", "candidates")}`;
    showToast(summary, newJobs > 0 ? "success" : "info");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function showSavedSearchMatches(searchId, unseenOnly) {
  try {
    const payload = await api(`/api/saved-searches/${encodeURIComponent(searchId)}/matches`, {
      method: "POST",
      body: JSON.stringify({ unseenOnly }),
    });
    const matchedIds = new Set((payload.matches || []).map((j) => j.id));
    if (matchedIds.size === 0) {
      showToast(unseenOnly ? "No new matches yet." : "No matches found yet.", "info");
      return;
    }
    state.queueFilter = "all";
    state.discoveredJobs = state.discoveredJobs.map((job) => ({
      ...job,
      __highlight: matchedIds.has(job.id),
    }));
    navigate("queue");
    renderJobs();
    showToast(`${matchedIds.size} matching job${matchedIds.size === 1 ? "" : "s"} highlighted in Queue.`, "success");
    // Mark seen so the badge resets next bootstrap.
    try {
      await api(`/api/saved-searches/${encodeURIComponent(searchId)}/mark-seen`, {
        method: "POST",
        body: JSON.stringify({}),
      }).then((res) => {
        if (res.savedSearches) state.savedSearches = res.savedSearches;
        renderSavedSearches();
      });
    } catch {
      // Non-fatal — the badge just stays until the next bootstrap.
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function digestPreview() {
  try {
    const payload = await api("/api/digest/preview");
    const out = $("#digestResult");
    out.hidden = false;
    out.textContent = payload.digest;
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function digestSend() {
  try {
    const payload = await api("/api/digest/send", { method: "POST", body: JSON.stringify({}) });
    const out = $("#digestResult");
    out.hidden = false;
    out.textContent = payload.preview;
    showToast("Digest sent (or written to outbox).", "success");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function handleSupport(event) {
  event.preventDefault();
  const subject = $("#supportSubject").value;
  const body = $("#supportBody").value;
  const contact = $("#supportContactEmail").value;
  if (!subject || !body) {
    $("#supportMessage").textContent = "Subject and body are required.";
    return;
  }
  try {
    await api("/api/support", {
      method: "POST",
      body: JSON.stringify({ subject, body, contactEmail: contact }),
    });
    $("#supportMessage").textContent = "Submitted. The admin will see it in the Admin → Support panel.";
    $("#supportSubject").value = "";
    $("#supportBody").value = "";
    $("#supportContactEmail").value = "";
  } catch (error) {
    $("#supportMessage").textContent = error.message;
  }
}

async function handleApplicationSave(event) {
  event.preventDefault();
  if (!state.selectedImportedJobId) {
    showToast("Pick an imported job first.", "info");
    return;
  }
  const checklistRaw = $("#applicationChecklist").value || "";
  const checklist = checklistRaw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^\[([ xX])\]\s*(.*)$/);
      if (match) {
        return { label: match[2].trim(), complete: match[1].toLowerCase() === "x" };
      }
      return { label: line, complete: false };
    });
  try {
    const reminderRaw = $("#applicationReminderAt")?.value || "";
    const payload = await api(`/api/imported-jobs/${encodeURIComponent(state.selectedImportedJobId)}/application`, {
      method: "POST",
      body: JSON.stringify({
        applicationStatus: $("#applicationStatus").value,
        applicationNotes: $("#applicationNotes").value,
        coverLetterDraft: $("#applicationCoverLetter").value,
        nextAction: $("#applicationNextAction").value,
        interviewStage: $("#applicationInterviewStage")?.value || null,
        reminderAt: reminderRaw ? reminderRaw + ":00" : null,
        historyNote: $("#applicationHistoryNote")?.value || "",
        documentsChecklist: checklist,
      }),
    });
    absorbBootstrap(payload.bootstrap);
    showToast(t("toast.applicationSaved", "Application saved."), "success");
    render();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadBilling() {
  try {
    const payload = await api("/api/billing");
    state.subscription = payload.subscription;
    state.billingPlans = payload.plans;
    renderBilling();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function handleAdminBilling(event) {
  event.preventDefault();
  try {
    const payload = await api("/api/admin/billing", {
      method: "POST",
      body: JSON.stringify({
        planId: $("#adminBillingPlan").value,
        status: $("#adminBillingStatus").value,
        seats: Number($("#adminBillingSeats").value || 1),
      }),
    });
    state.subscription = payload.subscription;
    renderBilling();
    $("#adminBillingNote").textContent = "Saved.";
  } catch (error) {
    $("#adminBillingNote").textContent = error.message;
  }
}

async function loadReadiness() {
  if (!isAdmin()) return;
  // Seed a placeholder row so the panel is visible while the fetch runs.
  const list = $("#readinessList");
  if (list && !list.children.length) {
    const li = document.createElement("li");
    li.textContent = "Loading…";
    list.append(li);
  }
  try {
    const payload = await api("/api/admin/readiness");
    renderReadiness(payload);
  } catch (error) {
    renderReadiness({ signals: [{ id: "error", label: "Readiness", status: "missing", summary: error.message }] });
  }
}

function renderReadiness(report) {
  const list = $("#readinessList");
  if (!list) return;
  list.replaceChildren();
  if (!report || !Array.isArray(report.signals)) {
    const li = document.createElement("li");
    li.textContent = "No readiness data.";
    list.append(li);
    return;
  }
  for (const signal of report.signals) {
    const li = document.createElement("li");
    const badge = document.createElement("span");
    badge.className = `readiness-status ${signal.status}`;
    badge.textContent = signal.status;
    const text = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = signal.label;
    const summary = document.createElement("span");
    summary.className = "muted";
    summary.textContent = " — " + signal.summary;
    text.append(title, summary);
    li.append(badge, text);
    list.append(li);
  }
}

async function loadEmailStatus() {
  if (!isAdmin()) return;
  try {
    const payload = await api("/api/admin/email/status");
    const summary = `${payload.backend.toUpperCase()} backend${payload.host ? ` · ${payload.host}:${payload.port}` : ""} · from ${payload.fromAddress}${payload.outboxEntries ? ` · outbox has ${payload.outboxEntries} entries` : ""}`;
    $("#emailBackendSummary").textContent = summary;
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function handleTestEmail(event) {
  event.preventDefault();
  if (!isAdmin()) return;
  const target = $("#testEmailTarget").value || state.auth.user?.email || "";
  try {
    const payload = await api("/api/admin/email/test", {
      method: "POST",
      body: JSON.stringify({ target }),
    });
    $("#testEmailMessage").textContent = `Status: ${payload.status} (backend: ${payload.backend})`;
    showToast("Test email sent.", "success");
    loadEmailStatus();
  } catch (error) {
    $("#testEmailMessage").textContent = error.message;
  }
}

async function handleDeletionRequest(event) {
  event.preventDefault();
  const ok = await confirmDialog({
    title: "Request account deletion?",
    body: "An admin must confirm before your data is removed. You will see this status under Support tickets in admin.",
    confirmLabel: "Request deletion",
    danger: true,
  });
  if (!ok) return;
  try {
    await api("/api/account/deletion-request", {
      method: "POST",
      body: JSON.stringify({ reason: $("#deletionReason").value }),
    });
    $("#deletionMessage").textContent = "Deletion request submitted. The admin will see it in Support tickets.";
    $("#deletionReason").value = "";
  } catch (error) {
    $("#deletionMessage").textContent = error.message;
  }
}

async function loadAdminTickets() {
  try {
    const payload = await api("/api/admin/support");
    const list = $("#adminTicketList");
    list.replaceChildren();
    if (!payload.tickets.length) {
      list.append(emptyNode("No tickets."));
      return;
    }
    for (const ticket of payload.tickets) {
      const row = document.createElement("div");
      row.className = "ticket-row";
      const subject = document.createElement("strong");
      subject.textContent = ticket.subject;
      const meta = document.createElement("span");
      meta.className = "muted";
      meta.textContent = `${ticket.contact_email} · ${new Date(ticket.created_at).toLocaleString()} · ${ticket.status}`;
      const body = document.createElement("p");
      body.textContent = ticket.body;
      row.append(subject, meta, body);
      list.append(row);
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}

function setAnalyticsEnabled(enabled) {
  try {
    if (enabled) {
      window.localStorage.setItem("djs_analytics_enabled", "1");
    } else {
      window.localStorage.setItem("djs_analytics_enabled", "0");
    }
  } catch {
    /* localStorage unavailable */
  }
}

function isAnalyticsEnabled() {
  try {
    return window.localStorage.getItem("djs_analytics_enabled") !== "0";
  } catch {
    return true;
  }
}

function logUiEvent(kind, detail) {
  if (!state.auth.authenticated || !isAnalyticsEnabled()) return;
  api("/api/analytics/event", {
    method: "POST",
    body: JSON.stringify({ kind, payload: detail || {} }),
  }).catch(() => {});
}

/* ---------- Forgot / reset / invite handlers ---------- */

async function handleForgotPassword(event) {
  event.preventDefault();
  const email = $("#forgotEmail").value.trim();
  const message = $("#forgotPasswordMessage");
  message.textContent = "";
  if (!email) {
    message.textContent = "Please enter your email.";
    return;
  }
  try {
    await api("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    message.textContent = "If a matching account exists, a reset link has been sent.";
  } catch (error) {
    message.textContent = error.message;
  }
}

async function handleResetPassword(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const token = form.dataset.token;
  const newPassword = $("#resetPasswordValue").value;
  const message = $("#resetPasswordMessage");
  message.textContent = "";
  if (!token) {
    message.textContent = "Reset link is missing.";
    return;
  }
  if (newPassword.length < 12) {
    message.textContent = "Password must be at least 12 characters.";
    return;
  }
  try {
    await api(`/api/auth/reset-password/${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ newPassword }),
    });
    message.textContent = "Password reset. Redirecting to sign in…";
    setTimeout(() => {
      window.location.assign("/");
    }, 1200);
  } catch (error) {
    message.textContent = error.message;
  }
}

async function handleAcceptInvite(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const token = form.dataset.token;
  const password = $("#acceptInvitePassword").value;
  const message = $("#acceptInviteMessage");
  message.textContent = "";
  if (!token) {
    message.textContent = "Invitation token is missing.";
    return;
  }
  if (password.length < 12) {
    message.textContent = "Password must be at least 12 characters.";
    return;
  }
  try {
    const payload = await api(`/api/auth/accept-invite/${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ newPassword: password }),
    });
    state.auth = { authenticated: true, user: payload.user, registrationOpen: false };
    absorbBootstrap(payload.bootstrap);
    message.textContent = "Account activated. Redirecting…";
    setTimeout(() => {
      window.location.assign("/");
    }, 800);
  } catch (error) {
    message.textContent = error.message;
  }
}

async function handleAdminInvite(event) {
  event.preventDefault();
  const email = $("#inviteEmail").value.trim();
  const role = $("#inviteRole").value;
  if (!email) {
    showToast("Enter an email address.", "error");
    return;
  }
  try {
    await api("/api/admin/invitations", {
      method: "POST",
      body: JSON.stringify({ email, role }),
    });
    $("#inviteEmail").value = "";
    showToast(`Invitation sent to ${email}.`, "success");
    await loadInvitations();
  } catch (error) {
    showToast(error.message, "error");
  }
}

/* ---------- Wiring ---------- */

$("#companyForm").addEventListener("submit", createCompany);
$("#loginForm").addEventListener("submit", login);
$("#registerForm").addEventListener("submit", register);
$("#logoutBtn").addEventListener("click", logout);
$("#changePasswordForm").addEventListener("submit", changePassword);
$("#saveDetailBtn").addEventListener("click", saveDetail);
$("#deleteCompanyBtn").addEventListener("click", deleteCompany);
$("#findCareerBtn").addEventListener("click", findCareerPage);
$("#scanBtn").addEventListener("click", scanCompany);
$("#quickScanWatchlistBtn").addEventListener("click", scanWatchlist);
$("#saveScheduleBtn").addEventListener("click", saveSchedule);
$("#quickSeedDemoBtn").addEventListener("click", seedDemo);
$("#extractHtmlBtn").addEventListener("click", extractManualHtml);
$("#suggestBtn").addEventListener("click", (event) => {
  // Sits inside <summary> of a collapsible — stop the toggle.
  event.preventDefault();
  event.stopPropagation();
  suggestCompanies();
});
$("#saveProviderBtn").addEventListener("click", saveProvider);
$("#saveProfileBtn")?.addEventListener("click", saveProfile);
$("#cvUploadBtn")?.addEventListener("click", () => $("#cvUploadInput")?.click());
$("#cvUploadInput")?.addEventListener("change", handleCvUpload);
$("#findJobsForm")?.addEventListener("submit", findJobs);

// Bookmarklet — render the draggable javascript: URL.
(function setupBookmarklet() {
  const link = document.getElementById("bookmarkletLink");
  if (!link) return;
  const captureUrl = `${window.location.origin}/capture`;
  // Compact, single-statement bookmarklet payload. Long-form source lives at
  // /bookmarklet.js for transparency. Variable shadowing is intentional —
  // bookmarklets run in the host page's global scope.
  const code = `(function(){var u=window.location.href;function p(s){for(var i=0;i<s.length;i++){var e=document.querySelector(s[i]);if(e&&e.textContent&&e.textContent.trim())return e.textContent.trim();}return"";}var t=p(["h1.jobsearch-JobInfoHeader-title","h1[data-test='job-title']","h1.t-24","h1.top-card-layout__title","h1[data-at='header-job-title']","[data-at='job-title']","h1.job-detail-title","h1"])||document.title||"";window.open(${JSON.stringify(captureUrl)}+"?u="+encodeURIComponent(u)+"&t="+encodeURIComponent(t.slice(0,200)),"_blank","noopener,noreferrer");})();`;
  link.setAttribute("href", "javascript:" + encodeURI(code));
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const status = document.getElementById("bookmarkletStatus");
    if (status) status.textContent = "Drag this link to your bookmark bar — clicking it here doesn't capture anything.";
  });
})();

// Toast on /capture redirect with ?capture=...
(function announceCaptureRedirect() {
  const params = new URLSearchParams(window.location.search);
  const capture = params.get("capture");
  if (!capture) return;
  const message = {
    captured: t("capture.captured", "Job captured."),
    merged: t("capture.merged", "Already in your queue — added this URL as another source."),
    bad_url: t("capture.bad_url", "That URL didn't look like a job page."),
    needs_login: t("capture.needs_login", "Sign in first, then click the bookmarklet again."),
  }[capture];
  if (message) {
    window.setTimeout(() => showToast(message, capture === "bad_url" || capture === "needs_login" ? "error" : "success"), 800);
  }
  // Strip the query param so subsequent reloads don't re-toast.
  history.replaceState({}, "", window.location.pathname);
})();
$("#prepareCoverLetterBtn")?.addEventListener("click", () => {
  if (state.selectedImportedJobId) prepareCoverLetter(state.selectedImportedJobId);
  else showToast("Pick an imported job first.", "info");
});
$("#draftCoverLetterBtn")?.addEventListener("click", () => {
  if (state.selectedImportedJobId) draftCoverLetter(state.selectedImportedJobId);
  else showToast("Pick an imported job first.", "info");
});
$("#tailorCvBtn")?.addEventListener("click", () => {
  if (state.selectedImportedJobId) tailorCv(state.selectedImportedJobId);
  else showToast("Pick an imported job first.", "info");
});
$("#autoFitAllBtn")?.addEventListener("click", autoFitAll);
$("#queueSortSelect")?.addEventListener("change", (event) => {
  state.queueSort = event.target.value;
  renderJobs();
});
$("#localeSelect")?.addEventListener("change", async (event) => {
  const value = event.target.value;
  await loadLocale(value);
  try {
    await api("/api/profile", { method: "POST", body: JSON.stringify({ locale: value }) });
  } catch (error) {
    showToast(error.message, "error");
  }
});
function urlBase64ToUint8Array(base64) {
  const padding = "=".repeat((4 - base64.length % 4) % 4);
  const standard = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(standard);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

async function enablePush() {
  const status = $("#pushStatus");
  const setStatusText = (msg) => { if (status) status.textContent = msg; };
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    setStatusText("This browser does not support push.");
    return;
  }
  try {
    setStatusText("Requesting permission…");
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setStatusText(`Permission ${permission}.`);
      return;
    }
    const keyResp = await api("/api/push/key");
    if (!keyResp.configured || !keyResp.publicKey) {
      setStatusText("Push isn't configured on the server (VAPID keys not set).");
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(keyResp.publicKey),
    });
    const json = subscription.toJSON();
    await api("/api/push/subscribe", {
      method: "POST",
      body: JSON.stringify(json),
    });
    setStatusText("Notifications enabled.");
    showToast("Browser notifications enabled.", "success");
  } catch (error) {
    setStatusText(`Error: ${error.message}`);
    showToast(error.message, "error");
  }
}

async function sendTestPush() {
  const status = $("#pushStatus");
  try {
    if (status) status.textContent = "Sending test…";
    const resp = await api("/api/push/test", { method: "POST", body: JSON.stringify({}) });
    const sent = (resp.outcomes || []).filter((o) => o.status === "sent").length;
    if (status) status.textContent = `Sent ${sent} test notification${sent === 1 ? "" : "s"}.`;
    showToast(sent ? "Test push sent." : "No test push delivered.", sent ? "success" : "info");
  } catch (error) {
    if (status) status.textContent = `Error: ${error.message}`;
    showToast(error.message, "error");
  }
}

$("#enablePushBtn")?.addEventListener("click", enablePush);
$("#testPushBtn")?.addEventListener("click", sendTestPush);
$("#workspaceSelect")?.addEventListener("change", (event) => switchWorkspace(event.target.value));
$("#inviteWorkspaceBtn")?.addEventListener("click", inviteWorkspaceMember);
$("#themeSelect")?.addEventListener("change", async (event) => {
  const value = event.target.value;
  applyTheme(value);
  try {
    await api("/api/profile", { method: "POST", body: JSON.stringify({ theme: value }) });
  } catch (error) {
    showToast(error.message, "error");
  }
});

// React to system theme changes when user picked "system".
if (window.matchMedia) {
  const mql = window.matchMedia("(prefers-color-scheme: light)");
  mql.addEventListener("change", () => {
    if (state.theme === "system") applyTheme("system");
  });
}
$("#adminCreateUserForm").addEventListener("submit", createAdminUser);
$("#refreshUsersBtn").addEventListener("click", () => loadAdminUsers().catch((error) => showToast(error.message, "error")));
$("#exportDataBtn").addEventListener("click", exportData);
$("#importDataBtn").addEventListener("click", () => $("#importFile").click());
$("#importFile").addEventListener("change", importDataFromFile);
$("#healthBtn").addEventListener("click", checkHealth);
$("#providerId").addEventListener("change", () => {
  state.aiProvider = { ...state.aiProvider, provider_id: $("#providerId").value, invocation_mode: "" };
  renderProvider();
});
$("#newCompanyBtn").addEventListener("click", () => {
  navigate("companies");
  document.querySelector("#companyForm input[name='name']")?.focus();
});
$("#emptyAddCompanyBtn").addEventListener("click", () => {
  document.querySelector("#companyForm input[name='name']")?.focus();
});
$("#quickAddCompanyBtn").addEventListener("click", () => {
  navigate("companies");
  document.querySelector("#companyForm input[name='name']")?.focus();
});
$("#briefOpenSettings")?.addEventListener("click", () => navigate("settings"));
$("#runAnalysisBriefBtn").addEventListener("click", () => {
  if (state.selectedImportedJobId) runAnalysis(state.selectedImportedJobId);
  else showToast("Pick an imported job first.", "info");
});
async function copyBriefThen(actionFn) {
  const text = $("#briefPrompt").value;
  if (!text) {
    showToast(t("brief.empty", "No brief to copy yet."), "info");
    return false;
  }
  try {
    await navigator.clipboard.writeText(text);
    if (actionFn) actionFn();
    return true;
  } catch {
    showToast(t("brief.clipboardErr", "Could not access the clipboard."), "error");
    return false;
  }
}

$("#copyBriefBtn").addEventListener("click", async () => {
  const ok = await copyBriefThen();
  if (ok) showToast(t("brief.copied", "Brief copied to clipboard."), "success");
});

// Manual-mode handoff: copy the prompt + open the LLM's web UI in a new tab.
// We can't programmatically prefill the LLM's textarea from a 3rd-party origin
// (CSP / cross-origin restrictions), but copy-then-open removes 80% of the friction.
$("#openInChatGPTBtn")?.addEventListener("click", async () => {
  const ok = await copyBriefThen(() => window.open("https://chat.openai.com/", "_blank", "noopener,noreferrer"));
  if (ok) showToast(t("brief.openHandoff", "Copied. Paste it into the LLM tab."), "success");
});
$("#openInClaudeBtn")?.addEventListener("click", async () => {
  const ok = await copyBriefThen(() => window.open("https://claude.ai/new", "_blank", "noopener,noreferrer"));
  if (ok) showToast(t("brief.openHandoff", "Copied. Paste it into the LLM tab."), "success");
});
$("#companyFilter").addEventListener("input", (event) => {
  state.companyFilter = event.target.value;
  renderCompanies();
});
$$(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.view));
});
$$(".segmented-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".segmented-btn").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    state.queueFilter = btn.dataset.filter;
    renderJobs();
  });
});

$("#saveCurrentSearchBtn")?.addEventListener("click", saveCurrentSearch);
$("#applicationForm")?.addEventListener("submit", handleApplicationSave);
$("#supportForm")?.addEventListener("submit", handleSupport);
$("#digestPreviewBtn")?.addEventListener("click", digestPreview);
$("#digestSendBtn")?.addEventListener("click", digestSend);
$("#refreshSupportBtn")?.addEventListener("click", loadAdminTickets);
$("#adminBillingForm")?.addEventListener("submit", handleAdminBilling);
$("#analyticsToggle")?.addEventListener("change", (event) => {
  setAnalyticsEnabled(event.target.checked);
});

if ($("#analyticsToggle")) {
  $("#analyticsToggle").checked = isAnalyticsEnabled();
}

$("#showForgotPasswordBtn")?.addEventListener("click", () => showOnly("forgotPasswordView"));
$("#forgotPasswordBack")?.addEventListener("click", () => showOnly("authGate"));
$("#forgotPasswordForm")?.addEventListener("submit", handleForgotPassword);
$("#resetPasswordForm")?.addEventListener("submit", handleResetPassword);
$("#resetPasswordBack")?.addEventListener("click", () => window.location.assign("/"));
$("#acceptInviteForm")?.addEventListener("submit", handleAcceptInvite);
$("#adminInviteForm")?.addEventListener("submit", handleAdminInvite);
$("#refreshMetricsBtn")?.addEventListener("click", refreshAdminMetrics);
$("#refreshReadinessBtn")?.addEventListener("click", loadReadiness);
$("#refreshEmailStatusBtn")?.addEventListener("click", loadEmailStatus);
$("#testEmailForm")?.addEventListener("submit", handleTestEmail);
$("#deletionForm")?.addEventListener("submit", handleDeletionRequest);

init().catch((error) => {
  setStatus("Error", "error");
  showToast(error.message, "error");
});

// PWA — register service worker + handle install prompt.
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

let __deferredInstallPrompt = null;
window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  __deferredInstallPrompt = event;
  const btn = document.getElementById("installAppBtn");
  if (btn) btn.hidden = false;
});
document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.id !== "installAppBtn") return;
  if (!__deferredInstallPrompt) return;
  __deferredInstallPrompt.prompt();
  __deferredInstallPrompt.userChoice.finally(() => {
    __deferredInstallPrompt = null;
    target.hidden = true;
  });
});
