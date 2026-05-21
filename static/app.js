"use strict";

const $ = (selector) => document.querySelector(selector);

// Null-safe textContent setter. Use whenever an element might be
// absent (test fixtures, stale-HTML / fresh-JS deploy mismatches,
// view-conditional partials). Replaces the unguarded
// ``$("#x").textContent = y`` pattern that throws "Cannot set
// properties of null" when ``#x`` is missing.
const setText = (selector, text) => {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (el) el.textContent = text == null ? "" : String(text);
};
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const VIEW_TITLES = {
  dashboard: { title: "Today", subtitle: "Your watched companies, recent runs, and what to do next." },
  companies: { title: "Companies", subtitle: "Add companies, find their career pages, and check for new roles." },
  jobs: { title: "Discovered jobs", subtitle: "Roles found on company sites. Review before importing." },
  brief: { title: "AI Brief", subtitle: "Prepare a provider-neutral brief and analyze fit with your own AI." },
  settings: { title: "Settings", subtitle: "AI provider, account security, backup, and scan history." },
  admin: { title: "Admin", subtitle: "Tester accounts. Visible to admins only." },
  cvBuilder: { title: "CV Builder", subtitle: "Walk through guided sections. The AI formats — it does not invent." },
  assistant: { title: "Assistant", subtitle: "One chat for every action. Slash-commands, keyword routing, and confirmation before every write." },
  searchResults: { title: "Search results", subtitle: "Live aggregator hits for your last search, grouped by role family." },
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
  // Loop 16 (2026-05-20): Gate 6.5 — network-drop normalized
  // messages. The browser emits varying jargon for connection
  // issues ("NetworkError when attempting to fetch resource",
  // "Failed to fetch", "Load failed"); these map them all to one
  // user-friendly line. Also covers offline fallback when fetch
  // throws before reaching the server.
  network_error: "Connection issue — please check your network and try again.",
  failed_to_fetch: "Connection issue — please check your network and try again.",
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
// Expose `state` on window so e2e smoke tests can seed it directly.
// Harmless in production — the browser-side app already manages
// this single instance; the alias just lets external scripts read /
// write to it. (Phase 2 #80 in-context-highlight smoke depends on
// being able to set state.profile.cvText + state.activeImportedJob
// without booting through the full bootstrap flow.)
if (typeof window !== "undefined") {
  window.state = state;
}

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
  // Only surface the pill when something is actually wrong or in flight.
  // "Ready" was confusing users — it stayed visible after a Settings
  // fetch landed, then disappeared/changed when navigating to Jobs and
  // looked like the page itself was offline.
  el.hidden = !mode || mode === "" || /^(Ready|Bereit|Sign in|Anmelden)$/i.test(text);
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
  // Loop 16 (2026-05-20): Gate 6.5 — recognise common browser
  // network-drop jargon and surface the friendly normalized
  // message. Browser-specific strings differ across Firefox
  // ("NetworkError when attempting to fetch resource"), Chrome
  // ("Failed to fetch"), Safari ("Load failed"), and offline
  // ("TypeError: Failed to fetch"). Match permissively.
  if (rawMessage && typeof rawMessage === "string") {
    const low = rawMessage.toLowerCase();
    if (
      low.includes("networkerror") ||
      low.includes("failed to fetch") ||
      low.includes("load failed") ||
      low === "typeerror"
    ) {
      return ERROR_COPY.network_error;
    }
  }
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
    const code = payload.error?.code;
    // Loop 16 (2026-05-20): Gate 6.5 — session-expiry recovery.
    // 401 = unauthenticated; 403 csrf_failed = stale session
    // (cookie still present but CSRF rotated). Both require the
    // user to re-authenticate. Triggering renderAuth() puts the
    // login form back in front of the user with the friendly
    // message; without this, a stale-session user just saw an
    // opaque "403" with no recovery path.
    if (
      response.status === 401 ||
      (response.status === 403 && code === "csrf_failed")
    ) {
      clearAuthenticatedState();
      renderAuth();
    }
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
  // localStorage is authoritative for the user's most-recent choice.
  // If it disagrees with the server (e.g., server save was slow), the
  // local pick wins so the user doesn't see their language flip back.
  let storedLocale = "";
  try { storedLocale = localStorage.getItem("dj_locale") || ""; } catch (_) {}
  const targetLocale = storedLocale || state.profile.locale || "en";
  if (targetLocale && targetLocale !== state.locale) {
    loadLocale(targetLocale);
  }
  applyTheme(state.profile.theme || "dark");
  state.applicationStatuses = bootstrap.applicationStatuses || ["saved", "interested", "applied", "interview", "rejected", "archived"];
  state.applicationOutcomes = bootstrap.applicationOutcomes || null;
  state.skillGaps = bootstrap.skillGaps || null;
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

async function loadSiteConfig() {
  // Best-effort, no-auth. Sole responsibility: inject the optional
  // analytics script when the operator has set DIRECTJOB_ANALYTICS_*
  // env vars. Safe to fail silently — analytics is operator-opt-in.
  try {
    const response = await fetch("/api/site-config", { credentials: "same-origin" });
    if (!response.ok) return;
    const cfg = await response.json();
    const scriptUrl = cfg?.analytics?.scriptUrl;
    const domain = cfg?.analytics?.domain;
    if (!scriptUrl) return;
    if (document.querySelector(`script[data-analytics-script="1"]`)) return;
    const script = document.createElement("script");
    script.defer = true;
    script.src = String(scriptUrl);
    script.dataset.analyticsScript = "1";
    if (domain) {
      // Plausible reads the domain from data-domain; Umami uses
      // data-website-id. We surface both — operator includes the
      // attributes their tool needs.
      script.setAttribute("data-domain", String(domain));
    }
    document.head.appendChild(script);
  } catch (_) {
    // network failure on a public endpoint is not user-facing
  }
}

async function init() {
  const path = window.location.pathname || "/";
  loadSiteConfig();
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
      hasUsers: Boolean(payload.hasUsers),
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
  if (payload?.whatsNew) {
    const seenKey = `directjob.whatsNew.${payload.whatsNew.appVersion}`;
    if (!localStorage.getItem(seenKey)) {
      const tpl = t("whatsNew.toast", "Welcome back — see what shipped while you were away.");
      showToast(tpl, "info", 8000);
      localStorage.setItem(seenKey, "1");
    }
  }
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
  // Honour the active locale — VIEW_TITLES carries the English defaults,
  // but ``t(...)`` looks up "view.<id>.title" / ".subtitle" first so a
  // German-locale user sees German titles instead of "Discovered jobs"
  // bleeding through above an otherwise-translated UI.
  $("#viewTitle").textContent = t(`view.${view}.title`, meta.title);
  $("#viewSubtitle").textContent = t(`view.${view}.subtitle`, meta.subtitle);
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
  // Wrap each renderer in try/catch so a single bad selector never
  // poisons the wider save-success path. Before this guard, a missing
  // element in any renderer threw "Cannot set properties of null"
  // up through saveProfile's catch and surfaced as the user's
  // form-status error message — even though the save itself had
  // already succeeded server-side.
  const renderers = [
    renderDashboard, renderSkillGapsCard, renderReplyRateCard,
    renderOnboarding, renderTemplates, renderSavedSearches,
    renderCompanies, renderDetail, renderJobs, renderProvider,
    renderProfile, renderTotpCard, renderNotifySettings,
    renderPrivacyAudit, renderWorkspacePicker, renderHistory,
    renderImportedJobs, renderBriefSummary, renderApplicationForm,
    renderQuotaSummary, renderAdminUsers, renderBilling,
    renderSearchResults,
  ];
  for (const fn of renderers) {
    try {
      fn();
    } catch (err) {
      // Log to console for diagnosis; never bubble. The user's save
      // already succeeded server-side and most renderers are
      // independent — one failure must not break the rest.
      console.error(`render: ${fn.name} failed`, err);
    }
  }
  setText("#navCompanyCount", state.companies.length);
  const newCount = state.discoveredJobs.filter((j) => !j.imported_job_id).length;
  setText("#navJobCount", newCount);
  scheduleRunPolling();
}

function renderAuth() {
  if (state.auth.authenticated) {
    showOnly("appShell");
  } else {
    showOnly("authGate");
  }
  // R18: persistent chat dock follows the auth state. Seed the
  // welcome bubble the first time it becomes visible.
  const dock = $("#chatDock");
  if (dock) {
    dock.hidden = !state.auth.authenticated;
    if (state.auth.authenticated) {
      seedChatWelcomeOnce();
    }
  }
  $("#sidebarUser").hidden = !state.auth.authenticated;
  const email = state.auth.user?.email || "";
  $("#sidebarUserEmail").textContent = email;
  $("#sidebarUserRole").textContent = isAdmin() ? "Admin" : "Tester";
  // First letter of the local-part as the avatar initial.
  const initial = (email.split("@")[0] || "·").trim().charAt(0).toUpperCase() || "·";
  const av = document.getElementById("sidebarUserAvatar");
  if (av) av.textContent = initial;
  $$(".admin-only").forEach((el) => {
    el.hidden = !isAdmin();
  });
  $("#registerForm").hidden = !state.auth.registrationOpen;
  // Public sign-up (users already exist) requires DSGVO consent
  // checkboxes; the bootstrap path (no users yet) hides them and
  // uses the original "Create the first account" copy.
  const isPublicSignup = state.auth.registrationOpen && state.auth.hasUsers;
  const consent = $("#registerConsent");
  if (consent) consent.hidden = !isPublicSignup;
  const heading = $("#registerHeading");
  const lead = $("#registerLead");
  if (heading) {
    heading.textContent = isPublicSignup
      ? t("auth.createPublicHeading", "Create your account")
      : t("auth.createFirstHeading", "Create the first account");
  }
  if (lead) {
    lead.textContent = isPublicSignup
      ? t("auth.createPublicLead", "Free to start. No tracker, no recruiter feed.")
      : t("auth.createFirstLead", "This screen only appears on a new install.");
  }
  $("#authMessage").textContent = "";
  setStatus(state.auth.authenticated ? "Ready" : "Sign in");
  if (state.auth.authenticated) navigate(state.view);
}

function renderSkillGapsCard() {
  const card = $("#skillGapsCard");
  if (!card) return;
  const summary = state.skillGaps;
  if (!summary || !summary.ready || !summary.top || summary.top.length === 0) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const list = $("#skillGapsList");
  if (!list) return;
  list.replaceChildren();
  for (const entry of summary.top) {
    const li = document.createElement("li");
    const headline = document.createElement("p");
    headline.className = "skill-gaps-headline";
    const skill = document.createElement("strong");
    skill.textContent = entry.skill;
    const count = document.createElement("span");
    count.className = "muted small";
    count.textContent = ` · ${t("dashboard.skillGaps.unlocks", "{n} more role(s)").replace("{n}", String(entry.jobs))}`;
    headline.append(skill, count);
    li.append(headline);
    if (entry.examples && entry.examples.length) {
      const ex = document.createElement("p");
      ex.className = "muted small skill-gaps-examples";
      ex.textContent = `${t("dashboard.skillGaps.examples", "e.g.")} ${entry.examples.join(", ")}`;
      li.append(ex);
    }
    list.append(li);
  }
}

function renderReplyRateCard() {
  const card = $("#replyRateCard");
  if (!card) return;
  const summary = state.applicationOutcomes;
  if (!summary || !summary.ready) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const pct = Math.round((summary.replyRate || 0) * 100);
  $("#replyRatePct").textContent = `${pct}%`;
  $("#replyRateDenominator").textContent = t("dashboard.replyRate.denom", "{r} of {n} applications").replace("{r}", String(summary.replied)).replace("{n}", String(summary.totalApplications));
  let insight;
  if (pct >= 25) {
    insight = t("dashboard.replyRate.insightHigh", "Strong rate. The roles + CV combination is landing.");
  } else if (pct >= 10) {
    insight = t("dashboard.replyRate.insightMid", "Solid for outbound. Keep the volume up.");
  } else if (pct > 0) {
    insight = t("dashboard.replyRate.insightLow", "Below typical. Consider tightening fit or rewording the cover letter.");
  } else {
    insight = t("dashboard.replyRate.insightZero", "No replies yet across {n} applications. Try a different angle.").replace("{n}", String(summary.totalApplications));
  }
  $("#replyRateInsight").textContent = insight;
}

function renderDashboard() {
  const watched = state.summary.companiesWatched ?? 0;
  const newJobs = state.summary.newDirectCompanyJobs ?? state.discoveredJobs.filter((j) => !j.imported_job_id).length;
  const setup = state.summary.companiesNeedingCareerPageSetup ?? state.companies.filter((c) => !c.career_page_url).length;
  const lastRun = state.summary.lastDiscoveryRunStatus || "—";
  // Some metric elements are conditionally rendered; null-guard every
  // direct write so a missing hint span never blows up render().
  const setText = (sel, value) => {
    const el = $(sel);
    if (el) el.textContent = value;
  };
  setText("#metricWatched", watched);
  setText("#metricJobs", newJobs);
  setText("#metricSetup", setup);
  setText("#metricRun",
            translateScanStatus(lastRun)
            || (lastRun === "—" ? "—" : lastRun));
  setText("#metricWatchedHint",
            watched ? `${watched} on your watchlist`
                       : "Add a company to start");
  setText("#metricJobsHint",
            newJobs ? `${newJobs} need review` : "Awaiting first scan");
  setText("#metricSetupHint",
            setup ? `${setup} need career page URL` : "All set up");
  setText("#metricRunHint",
            state.watchlistSchedule.lastRunAt
            ? `at ${new Date(state.watchlistSchedule.lastRunAt).toLocaleString()}`
            : "No scan recorded");

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
    const textEl = node.querySelector(".activity-text");
    textEl.replaceChildren();
    const co = document.createElement("strong");
    co.textContent = company?.name || t("history.unknownCompany", "Unknown company");
    const sep = document.createElement("span");
    sep.className = "muted";
    sep.textContent = " · ";
    const statusSpan = document.createElement("span");
    statusSpan.textContent = status;
    textEl.append(co, sep, statusSpan);
    const ts = run.finished_at || run.created_at;
    const timeEl = node.querySelector(".activity-time");
    if (ts) {
      timeEl.textContent = relativeTimeFromIso(ts) || new Date(ts).toLocaleString();
      timeEl.title = new Date(ts).toLocaleString();
    } else {
      timeEl.textContent = "";
    }
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
      const ctaRow = document.createElement("div");
      ctaRow.className = "queue-empty-cta-row";
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
      const demo = document.createElement("button");
      demo.type = "button";
      demo.className = "btn";
      demo.textContent = t("queue.empty.demo", "Try with sample jobs");
      demo.addEventListener("click", async () => {
        demo.disabled = true;
        try {
          const payload = await api("/api/demo-data/seed", { method: "POST", body: JSON.stringify({}) });
          absorbBootstrap(payload.bootstrap);
          render();
          showToast(t("queue.empty.demoSeeded", "Sample jobs added. Triage with j/k/a/x or scroll down."), "success");
        } catch (error) {
          showToast(error.message, "error");
        } finally {
          demo.disabled = false;
        }
      });
      ctaRow.append(cta, demo);
      wrap.append(ctaRow);
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
    // Confidence_score measures how much METADATA the source supplied
    // (title + url + description + location). For aggregator-fetched
    // jobs it's almost always 55% — uninformative. Hide it unless the
    // value crosses a meaningful threshold (≥75 = full structured data).
    const score = Math.round((job.confidence_score || 0) * 100);
    const conf = node.querySelector(".confidence");
    if (score >= 75) {
      conf.textContent = `${score}% data`;
      conf.title = t("queue.confidenceHint", "How complete the source's posting was (title + description + location).");
    } else {
      conf.hidden = true;
    }

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
  syncBriefActionsEnabled();
}

function syncBriefActionsEnabled() {
  const text = ($("#briefPrompt")?.value || "").trim();
  const has = text.length > 0;
  for (const id of ["copyBriefBtn", "openInChatGPTBtn", "openInClaudeBtn"]) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = !has;
    if (!has) {
      btn.dataset.disabledReason = "1";
      btn.title = t("brief.disabledTitle", "Pick an imported job below to prepare a brief first.");
    } else if (btn.dataset.disabledReason) {
      btn.title = btn.dataset.originalTitle || "";
      delete btn.dataset.disabledReason;
    }
  }
}

// Auto-sync the brief buttons when the textarea changes for any reason.
(function bootBriefAutoSync() {
  const ta = document.getElementById("briefPrompt");
  if (!ta) return;
  ta.addEventListener("input", syncBriefActionsEnabled);
  // Stash original tooltips so we can restore after a disabled cycle.
  for (const id of ["copyBriefBtn", "openInChatGPTBtn", "openInClaudeBtn"]) {
    const btn = document.getElementById(id);
    if (btn) btn.dataset.originalTitle = btn.title || "";
  }
  // MutationObserver covers programmatic .value = … assignments which
  // don't trigger the "input" event.
  let last = ta.value;
  setInterval(() => {
    if (ta.value !== last) { last = ta.value; syncBriefActionsEnabled(); }
  }, 400);
  syncBriefActionsEnabled();
})();

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

function renderSharePanel(job) {
  const panel = $("#sharePanel");
  const toggle = $("#shareEnabledToggle");
  const urlRow = $("#shareUrlRow");
  const urlEl = $("#shareUrl");
  if (!panel || !toggle || !urlRow || !urlEl) return;
  panel.hidden = !job;
  if (!job) return;
  toggle.checked = Boolean(job.share_enabled);
  if (job.share_enabled) {
    const url = `${location.origin}/share/job/${job.id}`;
    urlEl.textContent = url;
    urlRow.hidden = false;
  } else {
    urlEl.textContent = "";
    urlRow.hidden = true;
  }
  toggle.dataset.jobId = job.id;
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
  const repliedEl = $("#applicationReplied");
  const repliedHint = $("#applicationRepliedAt");
  if (repliedEl) {
    repliedEl.checked = Boolean(job.replied_at);
    if (repliedHint) {
      if (job.replied_at) {
        repliedHint.textContent = `${t("applications.repliedOn", "Replied on")} ${String(job.replied_at).slice(0, 10)}`;
      } else {
        repliedHint.textContent = t("applications.repliedHint", "Tick when the company first wrote back. Drives reply-rate analytics.");
      }
    }
  }
  const noteEl = $("#applicationHistoryNote");
  if (noteEl) noteEl.value = "";
  $("#applicationNextAction").value = job.next_action || "";
  $("#applicationNotes").value = job.application_notes || "";
  $("#applicationCoverLetter").value = job.cover_letter_draft || "";
  // Phase 2 #80 in-context-highlight: stash the active job on state
  // so renderCoverLetterSections can resolve [JD] citations against
  // the real job description. The reverse (CV) comes from state.profile.
  state.activeImportedJob = job;
  // Phase 2 #80: section-aware re-render whenever the application
  // view loads a job (or switches between jobs).
  renderCoverLetterSections(job.cover_letter_draft || "");
  const checklistText = (job.documents_checklist || [])
    .map((item) => `${item.complete ? "[x]" : "[ ]"} ${item.label}`)
    .join("\n");
  $("#applicationChecklist").value = checklistText;
  renderApplicationHistory(job);
  renderSharePanel(job);
  if (job.structured_analysis || job.fit_score != null) {
    summary.hidden = false;
    summary.replaceChildren();
    const fitN = job.fit_score != null ? Math.round(job.fit_score * 100) : null;
    if (fitN != null) {
      const ring = document.createElement("div");
      ring.className = "fit-ring";
      const tone = fitN >= 70 ? "good" : fitN >= 45 ? "warn" : "low";
      ring.classList.add(`fit-ring-${tone}`);
      ring.style.setProperty("--fit-pct", String(fitN));
      ring.innerHTML = `<svg viewBox="0 0 36 36" aria-hidden="true"><circle class="fit-ring-bg" cx="18" cy="18" r="15" fill="none"/><circle class="fit-ring-fg" cx="18" cy="18" r="15" fill="none" pathLength="100" stroke-dasharray="${fitN} 100" transform="rotate(-90 18 18)"/></svg><span class="fit-ring-num">${fitN}<span>%</span></span>`;
      summary.append(ring);
    }
    const block = document.createElement("div");
    block.className = "fit-meta";
    const fitLabel = document.createElement("p");
    fitLabel.className = "muted small";
    fitLabel.textContent = t("application.fit.label", "AI fit");
    const rec = document.createElement("p");
    rec.className = "fit-rec";
    rec.textContent = job.recommendation || t("application.fit.noRec", "No recommendation yet — Analyze fit on the Brief view to score.");
    block.append(fitLabel, rec);
    if (job.gaps && job.gaps.length) {
      const gapsBlock = document.createElement("ul");
      gapsBlock.className = "fit-gaps";
      const aggregated = state.skillGaps?.top || [];
      const lookup = new Map(aggregated.map((row) => [String(row.skill).toLowerCase(), row.jobs]));
      const tplBefore = t("application.fit.gapBefore", "Add ");
      const tplAfter = t("application.fit.gapAfter", " to your CV → unlocks {n} more role(s) in your queue");
      for (const gap of job.gaps) {
        const li = document.createElement("li");
        const overlap = lookup.get(String(gap).toLowerCase()) || 1;
        const beforeText = document.createTextNode(tplBefore);
        const skillStrong = document.createElement("strong");
        skillStrong.textContent = String(gap);
        const afterText = document.createTextNode(tplAfter.replace("{n}", String(overlap)));
        li.append(beforeText, skillStrong, afterText);
        gapsBlock.append(li);
      }
      block.append(gapsBlock);
    }
    summary.append(block);
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
  // Manage-subscription button: only shows when there's a real
  // Stripe customer to redirect (i.e. the user has completed at
  // least one checkout). Otherwise the portal call would 400.
  const manageBtn = $("#manageSubscriptionBtn");
  if (manageBtn) {
    const customerId = state.subscription?.customer_id;
    manageBtn.hidden = !customerId;
  }
}

async function manageSubscription() {
  const message = $("#subscriptionMessage");
  if (message) message.textContent = t("settings.subscription.opening", "Opening Stripe portal…");
  try {
    const payload = await api("/api/billing/portal", {
      method: "POST", body: JSON.stringify({}),
    });
    const url = payload?.portal?.url;
    if (url) {
      window.location.assign(url);
    } else if (message) {
      message.textContent = t("settings.subscription.noUrl", "Portal session opened but returned no URL. Try again.");
    }
  } catch (error) {
    if (message) message.textContent = error.message;
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
    // Cache-bust so a re-deploy with new copy doesn't get masked by the
    // browser's cached i18n bundle. The version is the running app's
    // /api/health version (refreshed once per session via state.appVersion).
    const cacheBust = state.appVersion ? `?v=${encodeURIComponent(state.appVersion)}` : `?t=${Date.now()}`;
    const response = await fetch(`/i18n/${target}.json${cacheBust}`);
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
      { label: t("cmdk.action.toggleLocale", "Switch language"), action: async () => {
          const next = (state.locale === "de") ? "en" : "de";
          try {
            await api("/api/profile", { method: "POST", body: JSON.stringify({ locale: next }) });
            try { localStorage.setItem("dj_locale", next); } catch (_) {}
            showToast(t("settings.locale.switching", "Switching language…"), "info", 800);
            setTimeout(() => location.reload(), 220);
          } catch (error) {
            showToast(error.message, "error");
          }
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
  // Also translate input / textarea placeholders. Bug #24: the wizard's
  // CV textarea stayed English ("…or paste your CV here") under a German
  // UI because applyTranslations only walked data-i18n, never the
  // -placeholder variant — so the bundle key was loaded but never applied.
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    const key = node.getAttribute("data-i18n-placeholder");
    if (key && dict[key]) {
      node.setAttribute("placeholder", dict[key]);
    }
  }
  // Same for aria-label / title (announces correctly to screen readers).
  for (const node of document.querySelectorAll("[data-i18n-aria-label]")) {
    const key = node.getAttribute("data-i18n-aria-label");
    if (key && dict[key]) {
      node.setAttribute("aria-label", dict[key]);
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
      li.className = "audit-row";
      const when = document.createElement("time");
      when.className = "audit-when muted";
      when.textContent = relativeTimeFromIso(e.created_at || e.createdAt) || (e.created_at || "");
      when.title = new Date(e.created_at || e.createdAt || "").toLocaleString();
      const kind = document.createElement("span");
      kind.className = `tag audit-kind audit-kind-${(e.kind || "").replace(/[^a-z0-9_]/gi, "_")}`;
      kind.textContent = e.kind;
      const detail = document.createElement("span");
      detail.className = "audit-detail muted";
      detail.textContent = e.payload && Object.keys(e.payload).length
        ? Object.entries(e.payload).map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`).join(" · ")
        : "";
      li.append(when, kind, detail);
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
  // Phase 2 #76 sub-piece (d): populate the friction-class display
  // on render so the user sees their classification slug + can
  // re-classify / clear it from the Settings card.
  const frictionInput = $("#frictionClassCurrent");
  if (frictionInput) frictionInput.value = profile.frictionClass || "";
  // Phase 2 #76 sub-piece (b): persona-vs-friction-class reconciliation
  // banner. Show when the server computed a non-empty mismatch hint.
  const mismatchEl = $("#frictionClassMismatchHint");
  if (mismatchEl) {
    const hint = profile.frictionClassMismatchHint || "";
    if (hint) {
      mismatchEl.textContent = hint;
      mismatchEl.hidden = false;
    } else {
      mismatchEl.textContent = "";
      mismatchEl.hidden = true;
    }
  }
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
  if (!providerSelect || !modeSelect) return;
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
        websiteUrl: $("#detailWebsite")?.value ?? "",
        careerPageUrl: $("#detailCareer")?.value ?? "",
        sector: $("#detailSector")?.value ?? "",
        notes: $("#detailNotes")?.value ?? "",
        watchEnabled: Boolean($("#detailWatch")?.checked),
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
        enabled: Boolean($("#scheduleEnabled")?.checked),
        intervalMinutes: Number($("#scheduleInterval")?.value || 360),
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
      // Phase 2 #80: section-aware re-render alongside the
      // canonical textarea value.
      renderCoverLetterSections(draft.output);
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
  // Read every field through optional chaining + ?? "" so a missing
  // input element doesn't throw "Cannot read properties of null".
  // The form is dynamic — i18n / persona variants can hide rows —
  // and saveProfile shouldn't be the place that crashes when a row
  // isn't rendered.
  const fieldValue = (sel) => ($(sel)?.value ?? "");
  const yearsRaw = fieldValue("#profileYearsExperience").trim();
  const body = {
    personaId,
    industry: fieldValue("#profileIndustry").trim(),
    targetRoles: fieldValue("#profileTargetRoles")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    location: fieldValue("#profileLocation").trim(),
    seniority: fieldValue("#profileSeniority").trim(),
    yearsExperience: yearsRaw === "" ? null : Number(yearsRaw),
    languages: fieldValue("#profileLanguages")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    cvText: fieldValue("#profileCvText"),
    notes: fieldValue("#profileNotes").trim(),
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
  // Read every form field via optional chaining + ?? "" so a missing
  // input doesn't throw. Same pattern as saveProfile (#Nasr's render
  // hardening) — form variants can hide rows, the save shouldn't be
  // the place that crashes when one isn't rendered.
  const fieldValue = (sel) => ($(sel)?.value ?? "");
  try {
    const payload = await api("/api/ai-provider", {
      method: "POST",
      body: JSON.stringify({
        providerId: fieldValue("#providerId"),
        invocationMode: fieldValue("#invocationMode"),
        model: fieldValue("#providerModel"),
        credentialReference: fieldValue("#credentialReference"),
        baseUrl: fieldValue("#providerBaseUrl"),
        command: fieldValue("#providerCommand"),
        notes: fieldValue("#providerNotes"),
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
  setText("#authMessage", "");
  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("#loginEmail")?.value ?? "",
        password: $("#loginPassword")?.value ?? "",
      }),
    });
    if (payload.requires2fa) {
      if ($("#loginPassword")) $("#loginPassword").value = "";
      const code = window.prompt(t("auth.totp.prompt", "Enter the 6-digit code from your authenticator app (or a recovery code):"));
      if (!code) {
        setText("#authMessage", t("auth.totp.cancelled", "Sign-in cancelled."));
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
    if ($("#loginPassword")) $("#loginPassword").value = "";
    renderAuth();
    render();
    if (isAdmin()) await loadAdminUsers();
  } catch (error) {
    setText("#authMessage", error.message);
  }
}

async function register(event) {
  event.preventDefault();
  setText("#authMessage", "");
  // Public sign-up requires DSGVO consent. The bootstrap path
  // (no users yet) skips the checkboxes — the operator IS the
  // one writing the policy.
  const consentVisible = !$("#registerConsent")?.hidden;
  const tosAccepted = Boolean($("#registerTos")?.checked);
  const privacyAccepted = Boolean($("#registerPrivacy")?.checked);
  if (consentVisible && (!tosAccepted || !privacyAccepted)) {
    setText("#authMessage", t(
      "auth.consent.required",
      "Tick both boxes to accept the Terms and the Privacy policy.",
    ));
    return;
  }
  try {
    const body = {
      email: $("#registerEmail")?.value ?? "",
      password: $("#registerPassword")?.value ?? "",
    };
    if (consentVisible) {
      body.tosAccepted = true;
      body.privacyAccepted = true;
    }
    const payload = await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.auth = { authenticated: true, user: payload.user, registrationOpen: false };
    absorbBootstrap(payload.bootstrap);
    if ($("#registerPassword")) $("#registerPassword").value = "";
    renderAuth();
    render();
  } catch (error) {
    setText("#authMessage", error.message);
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
    link.download = `helpmefindthejob-backup-${new Date().toISOString().slice(0, 10)}.json`;
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
        targetRoles: ($("#targetRoles")?.value ?? "").split(",").map((s) => s.trim()).filter(Boolean),
        industry: $("#targetIndustry")?.value ?? "",
        location: $("#targetLocation")?.value ?? "",
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
          const row = document.createElement("article");
          row.className = "find-jobs-row";
          const main = document.createElement("div");
          main.className = "find-jobs-main";
          const title = document.createElement("a");
          title.href = job.sourceUrl;
          title.target = "_blank";
          title.rel = "noopener";
          title.textContent = job.title || "(untitled)";
          title.className = "find-jobs-title";
          const subParts = [job.companyName || "?", job.location].filter(Boolean);
          const fresh = relativeTimeFromIso(job.postedAt || job.posted_at);
          if (fresh) subParts.push(fresh);
          const meta = document.createElement("p");
          meta.className = "find-jobs-meta muted small";
          meta.textContent = subParts.join(" · ");
          main.append(title, meta);
          const sourceTag = document.createElement("span");
          sourceTag.className = "tag find-jobs-source";
          sourceTag.textContent = job.source;
          row.append(main, sourceTag);
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
  const subject = $("#supportSubject")?.value ?? "";
  const body = $("#supportBody")?.value ?? "";
  const contact = $("#supportContactEmail")?.value ?? "";
  if (!subject || !body) {
    setText("#supportMessage", "Subject and body are required.");
    return;
  }
  try {
    await api("/api/support", {
      method: "POST",
      body: JSON.stringify({ subject, body, contactEmail: contact }),
    });
    setText("#supportMessage", "Submitted. The admin will see it in the Admin → Support panel.");
    if ($("#supportSubject")) $("#supportSubject").value = "";
    if ($("#supportBody")) $("#supportBody").value = "";
    if ($("#supportContactEmail")) $("#supportContactEmail").value = "";
  } catch (error) {
    setText("#supportMessage", error.message);
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
  setFormStatus("applicationStatusMessage", "saving", t("form.saving", "Saving…"));
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
        replied: $("#applicationReplied")?.checked || false,
        historyNote: $("#applicationHistoryNote")?.value || "",
        documentsChecklist: checklist,
      }),
    });
    absorbBootstrap(payload.bootstrap);
    setFormStatus("applicationStatusMessage", "success", t("toast.applicationSaved", "Application saved."));
    render();
  } catch (error) {
    setFormStatus("applicationStatusMessage", "error", error.message);
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
        planId: $("#adminBillingPlan")?.value ?? "",
        status: $("#adminBillingStatus")?.value ?? "",
        seats: Number($("#adminBillingSeats")?.value || 1),
      }),
    });
    state.subscription = payload.subscription;
    renderBilling();
    setText("#adminBillingNote", "Saved.");
  } catch (error) {
    setText("#adminBillingNote", error.message);
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
  const target = ($("#testEmailTarget")?.value) || state.auth.user?.email || "";
  try {
    const payload = await api("/api/admin/email/test", {
      method: "POST",
      body: JSON.stringify({ target }),
    });
    setText("#testEmailMessage", `Status: ${payload.status} (backend: ${payload.backend})`);
    showToast("Test email sent.", "success");
    loadEmailStatus();
  } catch (error) {
    setText("#testEmailMessage", error.message);
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
      body: JSON.stringify({ reason: $("#deletionReason")?.value ?? "" }),
    });
    setText("#deletionMessage", "Deletion request submitted. The admin will see it in Support tickets.");
    if ($("#deletionReason")) $("#deletionReason").value = "";
  } catch (error) {
    setText("#deletionMessage", error.message);
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
  const email = ($("#forgotEmail")?.value ?? "").trim();
  setText("#forgotPasswordMessage", "");
  if (!email) {
    setText("#forgotPasswordMessage", "Please enter your email.");
    return;
  }
  try {
    await api("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    setText("#forgotPasswordMessage", "If a matching account exists, a reset link has been sent.");
  } catch (error) {
    setText("#forgotPasswordMessage", error.message);
  }
}

async function handleResetPassword(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const token = form.dataset.token;
  const newPassword = $("#resetPasswordValue")?.value ?? "";
  setText("#resetPasswordMessage", "");
  if (!token) {
    setText("#resetPasswordMessage", "Reset link is missing.");
    return;
  }
  if (newPassword.length < 12) {
    setText("#resetPasswordMessage", "Password must be at least 12 characters.");
    return;
  }
  try {
    await api(`/api/auth/reset-password/${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ newPassword }),
    });
    setText("#resetPasswordMessage", "Password reset. Redirecting to sign in…");
    setTimeout(() => {
      window.location.assign("/");
    }, 1200);
  } catch (error) {
    setText("#resetPasswordMessage", error.message);
  }
}

async function handleAcceptInvite(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const token = form.dataset.token;
  const password = $("#acceptInvitePassword")?.value ?? "";
  setText("#acceptInviteMessage", "");
  if (!token) {
    setText("#acceptInviteMessage", "Invitation token is missing.");
    return;
  }
  if (password.length < 12) {
    setText("#acceptInviteMessage", "Password must be at least 12 characters.");
    return;
  }
  try {
    const payload = await api(`/api/auth/accept-invite/${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ newPassword: password }),
    });
    state.auth = { authenticated: true, user: payload.user, registrationOpen: false };
    absorbBootstrap(payload.bootstrap);
    setText("#acceptInviteMessage", "Account activated. Redirecting…");
    setTimeout(() => {
      window.location.assign("/");
    }, 800);
  } catch (error) {
    setText("#acceptInviteMessage", error.message);
  }
}

async function handleAdminInvite(event) {
  event.preventDefault();
  const email = ($("#inviteEmail")?.value ?? "").trim();
  const role = $("#inviteRole")?.value ?? "member";
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

// Phase 2 #76 sub-piece (d): user-visible friction-class actions on
// the Settings page. Re-classify re-runs the deterministic classifier
// against the user's current CV text; Clear sets friction_class="".
// Phase 2 #80: Copy-letter-body button + textarea-input listener so
// the section-aware panel stays in sync when the user edits the
// textarea directly.
$("#coverLetterCopyBodyBtn")?.addEventListener("click", () => {
  const sections = parseCoverLetterSections($("#applicationCoverLetter")?.value || "");
  const body = sections.body || "";
  if (!body) {
    showToast("No letter body parsed — paste a draft first.", "info");
    return;
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(body).then(
      () => showToast("Letter body copied to clipboard.", "success"),
      () => showToast("Clipboard write blocked by browser — select + copy manually.", "info"),
    );
  } else {
    showToast("Clipboard API unavailable in this browser.", "info");
  }
});
$("#applicationCoverLetter")?.addEventListener("input", (event) => {
  renderCoverLetterSections(event.target?.value || "");
});

$("#frictionClassReclassifyBtn")?.addEventListener("click", async () => {
  const statusEl = $("#frictionClassStatus");
  if (statusEl) statusEl.textContent = "";
  try {
    const payload = await api("/api/profile/friction-class/reclassify", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (state.profile) state.profile.frictionClass = payload.frictionClass || "";
    const input = $("#frictionClassCurrent");
    if (input) input.value = payload.frictionClass || "";
    if (statusEl) {
      statusEl.textContent =
        t("settings.frictionClass.reclassified", "Re-classified — current value: ") +
        (payload.frictionClass || "—");
    }
  } catch (err) {
    if (statusEl) {
      if ((err.message || "").includes("no_cv")) {
        statusEl.textContent = t(
          "settings.frictionClass.noCv",
          "No CV to classify — paste or build your CV first.",
        );
      } else {
        statusEl.textContent = `Error: ${err.message}`;
      }
    }
  }
});
$("#frictionClassClearBtn")?.addEventListener("click", async () => {
  const statusEl = $("#frictionClassStatus");
  if (statusEl) statusEl.textContent = "";
  try {
    await api("/api/profile/friction-class/clear", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (state.profile) state.profile.frictionClass = "";
    const input = $("#frictionClassCurrent");
    if (input) input.value = "";
    if (statusEl) {
      statusEl.textContent = t("settings.frictionClass.cleared", "Cleared.");
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Error: ${err.message}`;
  }
});
$("#findJobsForm")?.addEventListener("submit", findJobs);

// ----------------- CV Builder -----------------
//
// Walks the user through deterministic sections. The AI is invoked
// server-side only to FORMAT raw input; the fact-ratio gate prevents
// hallucination. Photo upload lives on /api/profile/photo-upload.

const cvBuilder = {
  currentSection: null,
  state: { sections: {} },
  photoDataUri: null,
};

async function cvBuilderRefresh() {
  try {
    const payload = await api("/api/cv-builder/state");
    cvBuilder.state = payload.state || { sections: {} };
    cvBuilder.currentSection = payload.currentSection || null;
    cvBuilder.sectionOrder = payload.sectionOrder || [];
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderMessage", `Error: ${err.message}`);
  }
}

async function cvBuilderStart() {
  try {
    const payload = await api("/api/cv-builder/start", {
      method: "POST", body: JSON.stringify({}),
    });
    cvBuilder.state = payload.state || { sections: {} };
    cvBuilder.currentSection = payload.currentSection || null;
    cvBuilder.sectionOrder = payload.sectionOrder || [];
    setText("#cvBuilderMessage", "");
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderMessage", `Error: ${err.message}`);
  }
}

function renderCvBuilder() {
  // Clear ONLY stale ERROR statuses on render. Success messages set by
  // cvBuilderUploadPhoto (e.g. "Photo saved (32 KB).") must survive
  // the render that immediately follows the upload, otherwise the
  // user never sees the confirmation.
  const photoStatus = $("#cvBuilderPhotoStatus");
  if (photoStatus && /^error:/i.test(photoStatus.textContent || "")) {
    photoStatus.textContent = "";
  }
  // Sidebar — list every section, mark completion status.
  const sidebar = $("#cvBuilderSidebar");
  if (sidebar) {
    sidebar.innerHTML = "";
    (cvBuilder.sectionOrder || []).forEach((sid) => {
      const filled = (cvBuilder.state.sections?.[sid] || []).length;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-ghost";
      button.style.textAlign = "left";
      const isCurrent = cvBuilder.currentSection?.sectionId === sid;
      button.style.fontWeight = isCurrent ? "600" : "400";
      // Use the CSS color hierarchy instead of opacity so the
      // inactive-section text still clears WCAG 1.4.3 (4.5:1).
      // The earlier opacity-based dimming computed to ~2.7:1
      // (axe-core 4.10 audit 2026-05-19). See ACCESSIBILITY.md.
      button.style.color = isCurrent
        ? "var(--text)"
        : filled
          ? "var(--text-muted)"
          : "var(--text-soft)";
      const marker = filled ? "●" : "○";
      button.textContent = `${marker} ${sid}${filled ? ` (${filled})` : ""}`;
      sidebar.append(button);
    });
  }
  // Photo preview state. Only render when the URI looks valid — a
  // malformed / empty string used to produce a broken-image icon
  // because the <img> would still be display:block with an unusable src.
  const preview = $("#cvBuilderPhotoPreview");
  const removeBtn = $("#cvBuilderPhotoRemove");
  const validPhoto = typeof cvBuilder.photoDataUri === "string"
    && cvBuilder.photoDataUri.startsWith("data:image/");
  if (preview && validPhoto) {
    preview.src = cvBuilder.photoDataUri;
    preview.style.display = "block";
    if (removeBtn) removeBtn.style.display = "inline-flex";
  } else if (preview) {
    preview.removeAttribute("src");
    preview.style.display = "none";
    if (removeBtn) removeBtn.style.display = "none";
  }
  // Section host — render the current section's questions as a form.
  const host = $("#cvBuilderSectionHost");
  if (!host) return;
  host.innerHTML = "";
  const section = cvBuilder.currentSection;
  const finishBtn = $("#cvBuilderFinishBtn");
  const saveBtn = $("#cvBuilderSaveBtn");
  const addAnother = $("#cvBuilderAddAnotherBtn");
  // ``hasState`` distinguishes "user finished" vs "user hasn't started".
  // Without this we'd render the same "All sections done" copy for a
  // brand-new account, which is confusing — the screen has buttons but
  // no questions to answer.
  const hasState = Object.keys(cvBuilder.state?.sections || {}).length > 0;
  if (!section) {
    if (hasState) {
      host.innerHTML = "<p class='muted'>All sections done. Click <strong>Finish CV</strong> to assemble your CV.</p>";
      if (finishBtn) finishBtn.hidden = false;
    } else {
      host.innerHTML =
        "<p class='muted'>Welcome — click <strong>Start over</strong> "
        + "to begin a guided walk through your CV. Seven sections, "
        + "fact-grounded, never invents.</p>";
      if (finishBtn) finishBtn.hidden = true;
    }
    if (saveBtn) saveBtn.hidden = true;
    if (addAnother) addAnother.hidden = true;
    renderCvBuilderPreview();
    return;
  }
  if (finishBtn) finishBtn.hidden = true;
  if (saveBtn) saveBtn.hidden = false;
  if (addAnother) addAnother.hidden = !section.repeatable;
  const skipBtn = $("#cvBuilderSkipBtn");
  // Skip is available on the optional sections at the end.
  const optionalSections = new Set(["certifications", "projects"]);
  if (skipBtn) skipBtn.hidden = !optionalSections.has(section.sectionId);
  const heading = document.createElement("h3");
  heading.textContent = `${section.label}${section.repeatable ? " (you can add several)" : ""}`;
  host.append(heading);
  const form = document.createElement("form");
  form.id = "cvBuilderForm";
  form.style.display = "flex";
  form.style.flexDirection = "column";
  form.style.gap = "12px";
  for (const q of section.questions) {
    const label = document.createElement("label");
    label.className = "field";
    const span = document.createElement("span");
    span.textContent = q.prompt + (q.required ? " *" : "");
    label.append(span);
    const input = q.key.endsWith("_raw") || q.key === "achievements_raw"
      ? document.createElement("textarea")
      : document.createElement("input");
    input.id = `cvb_${q.key}`;
    input.dataset.key = q.key;
    if (input.tagName === "TEXTAREA") input.rows = 4;
    if (q.hint) {
      const hint = document.createElement("span");
      hint.className = "hint";
      hint.textContent = q.hint;
      label.append(input, hint);
    } else {
      label.append(input);
    }
    form.append(label);
  }
  host.append(form);
  renderCvBuilderPreview();
}

function renderCvBuilderPreview() {
  // Client-side preview — best-effort assembly so the user sees what
  // the final CV will look like as they go. Server runs the canonical
  // assembler on /finish; this is just for the in-wizard preview.
  const pre = $("#cvBuilderPreview");
  if (!pre) return;
  const sections = cvBuilder.state.sections || {};
  const lines = [];
  if (cvBuilder.photoDataUri) {
    lines.push("[photo embedded]");
  }
  const header = (sections.header || [{}])[0] || {};
  if (header.full_name) lines.push(`# ${header.full_name}`);
  const contact = [header.email, header.phone, header.location, header.linkedin, header.portfolio]
    .filter(Boolean).join(" · ");
  if (contact) lines.push(contact);
  const summary = (sections.summary || [{}])[0] || {};
  const summaryText = summary.formatted || summary.summary_raw || "";
  if (summaryText) { lines.push("\n## Summary\n", summaryText); }
  if (sections.experience?.length) {
    lines.push("\n## Experience");
    for (const e of sections.experience) {
      lines.push(`\n**${e.job_title || ""} — ${e.company_name || ""}**  · ${e.start_date || ""} – ${e.end_date || ""} · ${e.location || ""}`);
      lines.push(e.formatted || e.achievements_raw || "");
    }
  }
  if (sections.education?.length) {
    lines.push("\n## Education");
    for (const ed of sections.education) {
      lines.push(`\n**${ed.school || ""}** — ${ed.degree || ""}, ${ed.field || ""}  · ${ed.start_date || ""} – ${ed.end_date || ""}`);
    }
  }
  const skills = (sections.skills || [{}])[0] || {};
  const skillsText = skills.formatted || skills.skills_raw || "";
  if (skillsText) { lines.push("\n## Skills\n", skillsText); }
  pre.textContent = lines.join("\n");
}

// R19: search-results canvas renderer. Reads from
// state.lastSearchResults (populated by chatSend when find_jobs
// returns) and renders categorised cards into #searchResultsBody.
function renderSearchResults() {
  const host = $("#searchResultsBody");
  if (!host) return;
  const data = state.lastSearchResults;
  if (!data || !data.jobs || data.jobs.length === 0) {
    host.innerHTML = '<p class="muted">No active search. '
      + '<a href="#" id="searchResultsHint">Type "find a job" in chat to start.</a></p>';
    const hint = $("#searchResultsHint");
    if (hint) hint.addEventListener("click", (e) => {
      e.preventDefault();
      const input = $("#dockChatInput") || $("#chatInput");
      if (input) { input.focus(); input.value = "find a job"; }
    });
    setText("#searchResultsHeading", "Search results");
    setText("#searchResultsSub",
              "Categorised live aggregator hits. Click a card to focus on it in chat.");
    return;
  }
  // Heading reflects the actual query.
  const role = data.query || data.role || "";
  const loc = data.location || "";
  const where = loc ? ` in ${loc}` : "";
  setText("#searchResultsHeading",
            role ? `${data.jobs.length} ${role} result(s)${where}` : "Search results");
  setText("#searchResultsSub",
            "Click **Open** to view the source. Click **Pick** to draft a letter or get CV suggestions for that role.");
  // Group by category — server returned a flat job list; cluster by
  // the same shape we used server-side (via data.categories).
  const groups = data.groups || groupJobsByCategory(data.jobs);
  const html = [];
  for (const [category, items] of Object.entries(groups)) {
    if (!items.length) continue;
    html.push('<section class="search-category">');
    html.push('<div class="search-category-heading">'
      + `<h3>${escapeHtml(category)}</h3>`
      + `<span class="count">${items.length} job${items.length === 1 ? "" : "s"}</span>`
      + "</div>");
    for (const j of items) {
      const meta = [j.company, j.location, j.source]
        .filter(Boolean).map(escapeHtml).join(" · ");
      const url = j.url ? escapeHtml(j.url) : "";
      const safeTitle = escapeHtml(j.title || "(no title)");
      const pickToken = (j.url || j.title || "").replace(/"/g, "");
      html.push('<article class="search-job-card">'
        + `<p class="job-title">${safeTitle}</p>`
        + `<p class="job-meta">${meta}</p>`
        + '<div class="job-actions">'
        + (url
            ? `<a class="job-link" href="${url}" target="_blank" rel="noopener">Open ↗</a>`
            : "")
        + `<button class="btn btn-small btn-secondary" type="button"`
        + ` data-pick-token="${escapeHtml(pickToken)}">Pick</button>`
        + "</div>"
        + "</article>");
    }
    html.push("</section>");
  }
  host.innerHTML = html.join("\n");
  // Wire up the Pick buttons → send a chat message that the journey
  // state machine will pick up.
  host.querySelectorAll("[data-pick-token]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const token = btn.getAttribute("data-pick-token") || "";
      // Find which category + index this is so the journey can drill.
      const card = btn.closest(".search-job-card");
      const section = card?.closest(".search-category");
      const heading = section?.querySelector("h3");
      const category = heading?.textContent || "";
      if (category) {
        chatSend(category);
        // Find the 1-based index of this card within the section.
        const cards = section.querySelectorAll(".search-job-card");
        const idx = Array.from(cards).indexOf(card) + 1;
        if (idx > 0) {
          setTimeout(() => chatSend(String(idx)), 250);
        }
      }
    });
  });
}

function groupJobsByCategory(jobs) {
  // Mirror of the server's company_discovery.journey.categorize_job
  // heuristic. We use the SAME keyword buckets so the canvas group
  // labels match what the chat reply showed.
  const buckets = [
    ["Clinical / Pflege", ["pflege", "nurse", "nursing", "clinical",
      "krank", "altenpflege", "betreuung", "care", "hca", "patient"]],
    ["Hospitality / Bar", ["bartender", "barkeeper", "barista", "café",
      "cafe", "kellner", "waiter", "wait staff", "host", "server",
      "restaurant", "hotel"]],
    ["Tech / Engineering", ["engineer", "developer", "backend", "frontend",
      "devops", "sre", "platform", "ml", "data", "fullstack", "tech"]],
    ["Marketing / Brand", ["marketing", "growth", "brand", "seo",
      "content", "social", "crm", "performance"]],
    ["Operations / Admin", ["operations", "ops", "admin", "coordinator",
      "assistant", "office", "manager"]],
  ];
  const groups = {};
  for (const j of jobs) {
    const hay = `${j.title || ""} ${j.description || ""}`.toLowerCase();
    let category = "Other";
    outer: for (const [name, needles] of buckets) {
      for (const n of needles) {
        if (hay.includes(n)) { category = name; break outer; }
      }
    }
    (groups[category] = groups[category] || []).push(j);
  }
  return groups;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

async function cvBuilderSubmit(opts = {}) {
  const section = cvBuilder.currentSection;
  if (!section) return;
  const answers = {};
  for (const q of section.questions) {
    const el = document.getElementById(`cvb_${q.key}`);
    answers[q.key] = el?.value ?? "";
  }
  try {
    const payload = await api(
      `/api/cv-builder/section/${encodeURIComponent(section.sectionId)}`, {
        method: "POST",
        body: JSON.stringify({ answers, advance: !opts.stay }),
      },
    );
    cvBuilder.state = payload.state || { sections: {} };
    cvBuilder.currentSection = payload.currentSection || null;
    const ratio = payload.aiMeta?.factRatio;
    const accepted = payload.aiMeta?.aiAccepted;
    if (ratio !== undefined) {
      const msg = accepted
        ? `AI formatted (fact-ratio ${(ratio * 100).toFixed(0)}%).`
        : `AI rewrite below grounding threshold — kept your raw text.`;
      setText("#cvBuilderMessage", msg);
    } else {
      setText("#cvBuilderMessage", "Saved.");
    }
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderMessage", `Error: ${err.message}`);
  }
}

async function cvBuilderFinish() {
  try {
    const payload = await api("/api/cv-builder/finish", {
      method: "POST", body: JSON.stringify({}),
    });
    absorbBootstrap(payload.bootstrap);
    setText("#cvBuilderMessage", `CV saved (${payload.cvLength} chars). Open Settings to view.`);
    cvBuilder.state = { sections: {} };
    cvBuilder.currentSection = null;
    renderCvBuilder();
    showToast("CV saved to profile.", "success");
  } catch (err) {
    setText("#cvBuilderMessage", `Error: ${err.message}`);
  }
}

async function cvBuilderUploadPhoto(file) {
  if (!file) return;
  setText("#cvBuilderPhotoStatus", "Uploading…");
  try {
    const base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    const payload = await api("/api/profile/photo-upload", {
      method: "POST",
      body: JSON.stringify({ contentBase64: base64 }),
    });
    cvBuilder.photoDataUri = payload.cvPhotoDataUri;
    setText("#cvBuilderPhotoStatus",
            `Photo saved (${Math.round(payload.sizeBytes / 1024)} KB).`);
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderPhotoStatus", `Error: ${err.message}`);
  }
}

async function cvBuilderRemovePhoto() {
  try {
    await api("/api/profile/photo", {
      method: "POST", body: JSON.stringify({ action: "remove" }),
    });
    cvBuilder.photoDataUri = null;
    setText("#cvBuilderPhotoStatus", "Photo removed.");
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderPhotoStatus", `Error: ${err.message}`);
  }
}

$("#cvBuilderStartBtn")?.addEventListener("click", cvBuilderStart);
$("#cvBuilderSaveBtn")?.addEventListener("click", () => cvBuilderSubmit());
$("#cvBuilderAddAnotherBtn")?.addEventListener("click", () => cvBuilderSubmit({ stay: true }));
$("#cvBuilderSkipBtn")?.addEventListener("click", async () => {
  const section = cvBuilder.currentSection;
  if (!section) return;
  try {
    const payload = await api(
      `/api/cv-builder/section/${encodeURIComponent(section.sectionId)}`, {
        method: "POST",
        body: JSON.stringify({ action: "skip" }),
      },
    );
    cvBuilder.state = payload.state || { sections: {} };
    cvBuilder.currentSection = payload.currentSection || null;
    setText("#cvBuilderMessage", `Skipped ${section.label}.`);
    renderCvBuilder();
  } catch (err) {
    setText("#cvBuilderMessage", `Error: ${err.message}`);
  }
});
$("#cvBuilderFinishBtn")?.addEventListener("click", cvBuilderFinish);
// ----------------- Assistant chat -----------------
//
// One chat surface. Slash-commands route deterministically; free-form
// goes through keyword router (no AI required) → AI router (if
// configured). Confirmation gate before every DB write. Audit-log
// happens server-side. Designed to gradually replace forms.

// Inline-markdown → HTML for bubble rendering. Handles **bold** and
// `code`. ALL user text is HTML-escaped first so a chat reply
// containing literal `<script>` shows as text, not executable HTML.
function chatRenderInline(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  let html = div.innerHTML;  // entities-escaped form
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  return html;
}

function chatAppendBubble(role, text, opts = {}) {
  // R18: write to BOTH chat surfaces — the view-assistant transcript
  // AND the persistent dock — so the user sees the same conversation
  // regardless of which input they used.
  const hosts = [$("#chatTranscript"), $("#dockChatTranscript")]
    .filter(Boolean);
  if (!hosts.length) return null;
  const bubbles = [];
  for (const host of hosts) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble-${role}`;
    const isUser = role === "user";
    bubble.style.alignSelf = isUser ? "flex-end" : "flex-start";
    bubble.style.maxWidth = "82%";
    if (opts.typing) {
      bubble.setAttribute("aria-live", "polite");
      if (opts.typingLabel) {
        // Loop 14.1 (2026-05-20): phase-aware narration replaces
        // silent dots when the helper resolved a specific label.
        // EN-only Phase 1; DE bundle wiring tracked in Phase 2
        // backlog #75 (expanded to include typing labels).
        // PART 9 Loop 28 (2026-05-21): typingLabel can be a
        // milestone array [{after: ms, text}, ...]; we set the
        // initial text and schedule rotations via setTimeout.
        // Timer ids are stashed on the bubble for cleanup in
        // remove() so dismiss-during-rotation doesn't leak text
        // into other bubbles.
        // textContent (not innerHTML) -- labels are hard-coded
        // constants but textContent is the XSS-safe default.
        bubble.classList.add("chat-bubble-narration");
        const milestones = Array.isArray(opts.typingLabel)
          ? opts.typingLabel
          : [{after: 0, text: opts.typingLabel}];
        const initial = milestones[0]?.text || "";
        bubble.setAttribute("aria-label", initial);
        bubble.textContent = initial;
        const timers = [];
        for (const milestone of milestones.slice(1)) {
          const id = setTimeout(() => {
            bubble.setAttribute("aria-label", milestone.text);
            bubble.textContent = milestone.text;
          }, milestone.after);
          timers.push(id);
        }
        bubble._typingTimers = timers;
      } else {
        bubble.classList.add("chat-bubble-typing");
        bubble.setAttribute("aria-label", "Assistant is typing");
        bubble.innerHTML = "<span class='dot-1'>·</span><span class='dot-2'>·</span><span class='dot-3'>·</span>";
      }
    } else {
      if (isUser) bubble.textContent = text == null ? "" : String(text);
      else bubble.innerHTML = chatRenderInline(text);
    }
    host.append(bubble);
    host.scrollTop = host.scrollHeight;
    bubbles.push(bubble);
  }
  // Return a wrapper with .remove() that scrubs every mirror — so
  // typing bubbles disappear from all surfaces when the real reply
  // lands.
  return {
    remove() {
      for (const b of bubbles) {
        // PART 9 Loop 28: cancel pending typing-label rotations so
        // a dismissed bubble doesn't fire setTimeout callbacks
        // against a detached node.
        if (b._typingTimers) {
          for (const id of b._typingTimers) clearTimeout(id);
          b._typingTimers = null;
        }
        b.remove();
      }
    },
    // Convenience for callers that read DOM properties off the
    // returned bubble.
    nodes: bubbles,
  };
}

// Loop 14.1 (2026-05-20): phase-aware typing labels (Gate 6.6).
// Maps (last user input + last server-known journey phase) to a
// human-readable narration string shown in the typing bubble
// during the wait for the chat-message response. Closes the
// "silent waits >=2s" gap surfaced in the Loop 14 read-through.
//
// Phase 1 is intentionally static: no streaming infrastructure,
// no per-provider / per-token live progress. The label is a
// CONTEXTUAL placeholder that tells the user WHAT the assistant
// is doing during the wait. Live streaming refactor scoped to
// Phase 2 backlog #77 (combined SSE + concurrent fan-out +
// token-streamed AI + frontend in-place bubble mutation).
//
// EN-only Phase 1; DE bundle wiring tracked in Phase 2 backlog
// #75 (operator-expanded Loop 14.1 to cover typing labels).
//
// PART 9 Loop 28 (2026-05-21): values are now milestone arrays
// {after: ms, text: "..."} so the typing bubble can ROTATE during
// the wait — narrating expected pipeline stages instead of a
// frozen single-line label. This is client-side narration of
// known pipeline stages; true server-pushed progress is Phase 2
// backlog #77 (SSE streaming refactor). The honesty: we're
// telling the user what's happening based on what we EXPECT to
// happen at each elapsed time, not what's actually happening on
// the server right now. That's still a large UX win over a frozen
// label per the operator's "perceived latency != total latency"
// doctrine.
const TYPING_LABELS = {
  search: [
    {after: 0, text: "Querying job boards across the EU…"},
    {after: 3000, text: "Comparing and deduplicating results across providers…"},
    {after: 8000, text: "Ranking by relevance and scoring fit…"},
    {after: 18000, text: "Still going — slower providers can take a while…"},
  ],
  tailor: [
    {after: 0, text: "Reading your CV…"},
    {after: 4000, text: "Mapping CV bullets against the JD requirements…"},
    {after: 12000, text: "Drafting the tailored version (local AI runs slower than cloud)…"},
    {after: 30000, text: "Still going — Ollama can take 30-90 s depending on model and CPU…"},
    {after: 60000, text: "Heads up: very large CVs + local AI can take over a minute…"},
  ],
  letter: [
    {after: 0, text: "Reading your CV plus the job description…"},
    {after: 4000, text: "Drafting the letter body…"},
    {after: 12000, text: "Adding source citations (Quellen) so you can verify every claim…"},
    {after: 30000, text: "Still going — local AI takes longer; cloud AI is faster…"},
    {after: 60000, text: "Heads up: large CVs + Ollama can take over a minute…"},
  ],
  consult: [
    {after: 0, text: "Analyzing your CV against the JD…"},
    {after: 5000, text: "Surfacing improvement suggestions, never inventing facts…"},
    {after: 15000, text: "Still going — thorough analysis takes 30-90 s with local AI…"},
    {after: 45000, text: "Heads up: large CVs + local AI can run beyond a minute…"},
  ],
  inspire: [
    {after: 0, text: "Thinking about lateral roles your background unlocks…"},
    {after: 5000, text: "Drafting suggestions grounded in your actual experience…"},
    {after: 12000, text: "Almost there — finishing the suggestion list…"},
  ],
  default: [
    {after: 0, text: "Thinking…"},
  ],
};

function typingCategoryFor(message, lastJourneyPhase) {
  // PART 9 Loop 29: factored out from typingLabelFor so the
  // completion-footer + explainer logic can route off the same
  // category without re-running the regex chain.
  const m = (message || "").trim().toLowerCase();
  const phase = (lastJourneyPhase || "").toLowerCase();
  if (m === "/tailor" || m.startsWith("/tailor ")) return "tailor";
  if (m === "/letter" || m === "/motivation" || m.startsWith("/letter ") || m.startsWith("/motivation ")) return "letter";
  if (m === "/consult" || m === "/enhance" || m.startsWith("/consult ") || m.startsWith("/enhance ")) return "consult";
  if (m === "/find" || m === "/search" || m.startsWith("/find ") || m.startsWith("/search ")) return "search";
  if (/^(find|search|suche|finde)\s+/.test(m)) return "search";
  if (/^(find a job|search jobs|jobs suchen)\b/.test(m)) return "search";
  if (phase === "preferences" && m.length > 0) return "search";
  if (phase === "review" && /^(1|2|3|yes|y|ja|retry|nochmal)$/.test(m)) return "search";
  if (phase === "inspire" && !/^(no|n|nein|skip|stick|none|keine|nope)$/.test(m)) return "inspire";
  if (phase === "tailor") {
    if (m.includes("letter") || m.includes("motivation") || m.includes("schreiben")) return "letter";
    if (m.includes("consult") || m.includes("enhance") || m.includes("improve")) return "consult";
    if (m.includes("tailor")) return "tailor";
  }
  return "default";
}

function typingLabelFor(message, lastJourneyPhase) {
  const category = typingCategoryFor(message, lastJourneyPhase);
  return TYPING_LABELS[category] || TYPING_LABELS.default;
}

// PART 9 Loop 29 (2026-05-21): one-time "behind the scenes"
// explainer for the search category. Tailor / letter / consult
// already self-narrate via TYPING_LABELS rotation (Loop 28) AND
// already carry a "this can take 30-90s" expectation. Search has
// the strongest "where is my time going?" question because the
// provider fan-out is invisible. Future expansion to other
// categories sits behind Phase 2 #75 i18n + a UX review.
const EXPLAINER_TEXT = {
  search: (
    "Heads up — searching runs across multiple job-board providers in turn " +
    "(Adzuna, JSearch, Greenhouse, Lever, Personio, EURES, Remotive, " +
    "WeWorkRemotely), then ranks the merged results. Typical wait is 5-20 " +
    "seconds depending on each provider's response time. Partial results " +
    "are still shown when some providers are temporarily unavailable. " +
    "_(Shown once — close this for good by sending your next message.)_"
  ),
};

function maybeShowExplainer(category) {
  if (!category || !EXPLAINER_TEXT[category]) return;
  const flagKey = "helpmefindthejob_explainer_seen_" + category;
  try {
    if (localStorage.getItem(flagKey)) return;
    localStorage.setItem(flagKey, String(Date.now()));
  } catch (_) {
    // localStorage may be disabled (private browsing, storage quota,
    // sandboxed iframe) — skip the explainer silently rather than
    // showing it every send.
    return;
  }
  chatAppendBubble("assistant", EXPLAINER_TEXT[category]);
}

// PART 9 Loop 29: compose the post-op elapsed-time footer once the
// reply lands. Categories that benefit from the footer right now:
// "search" (provider count + elapsed give the user agency over
// "why did that take 15s?"). Other categories rely on the existing
// rotating label messaging.
function elapsedFooterFor(category, elapsedMs, payload) {
  if (category !== "search") return "";
  if (elapsedMs < 3000) return ""; // brief / cache-hit — no footer noise
  const seconds = (elapsedMs / 1000).toFixed(1);
  const errored = (payload && Array.isArray(payload.erroredOutcomes))
    ? payload.erroredOutcomes
    : [];
  const totalProviders = (payload && typeof payload.totalProviders === "number")
    ? payload.totalProviders
    : null;
  if (totalProviders === null) {
    return `_Took ${seconds}s_`;
  }
  const failed = errored.length;
  const succeeded = totalProviders - failed;
  if (failed > 0) {
    return `_Took ${seconds}s across ${totalProviders} providers — ${succeeded} succeeded, ${failed} unavailable._`;
  }
  return `_Took ${seconds}s across ${totalProviders} providers._`;
}

// Phase 2 #77 sub-piece (d): parse a find-intent message into a
// {query, location} pair the SSE endpoint accepts. Mirrors the
// server-side parsing in chat_router for the find_jobs slash + NL
// patterns (slash /find, slash /search, "find …", "search …", DE
// "suche …" / "finde …", and the "find a job in <city>" phrasing).
// Returns null when the message clearly isn't a find intent so the
// caller can fall back to the JSON endpoint.
// Phase 2 #80: parse the AI cover-letter output into its 5 sections.
// The text-shape build_cover_letter_brief_prompt tells the AI to
// emit ("1. Subject ... 2. Cover letter body ... 3. Editing notes
// ... 4. Draft assumptions ... 5. Source citations (Quellen)"). The
// parser splits on those section headers + tolerates the DE-locale
// "Quellen" alias. Returns {subject, body, editingNotes, assumptions,
// citations} with empty strings for sections not detected. Fallback:
// a non-sectioned input returns the whole text as `body` so the UI
// still renders something useful.
function parseCoverLetterSections(text) {
  const empty = {
    subject: "",
    body: "",
    editingNotes: "",
    assumptions: "",
    citations: "",
  };
  if (!text || !text.trim()) return empty;
  const markers = [
    {key: "subject", pattern: /^\s*1\.\s*Subject\s*line[^\n]*$/im},
    {key: "body", pattern: /^\s*2\.\s*Cover\s*letter\s*body[^\n]*$/im},
    {key: "editingNotes", pattern: /^\s*3\.\s*Editing\s*notes[^\n]*$/im},
    {key: "assumptions", pattern: /^\s*4\.\s*Draft\s*assumptions[^\n]*$/im},
    {
      key: "citations",
      pattern: /^\s*(?:5\.\s*Source\s*citations|##\s*Quellen|Quellen\s*\(Source)[^\n]*$/im,
    },
  ];
  const positions = [];
  for (const {key, pattern} of markers) {
    const match = text.match(pattern);
    if (match) {
      positions.push({
        key,
        start: match.index,
        headerEnd: match.index + match[0].length,
      });
    }
  }
  if (positions.length === 0) {
    return {...empty, body: text.trim()};
  }
  positions.sort((a, b) => a.start - b.start);
  const out = {...empty};
  for (let i = 0; i < positions.length; i++) {
    const pos = positions[i];
    const next = positions[i + 1];
    const slice = next
      ? text.slice(pos.headerEnd, next.start)
      : text.slice(pos.headerEnd);
    out[pos.key] = slice.trim();
  }
  return out;
}

// Phase 2 #80: parse the Source citations block into structured
// {claim, sources: [{kind, text}]} entries. Lines like:
//   - "<claim sentence>"
//     ← [CV] "<excerpt>"
//     ← [JD] "<excerpt>"
//   - "<other claim>"
//     ← [Inference] (assumption)
// Tolerant of extra whitespace + missing quotes around the
// claim/excerpt. Returns an array of entries; empty array on empty
// input.
function parseCitations(citationsText) {
  if (!citationsText || !citationsText.trim()) return [];
  const lines = citationsText.split("\n");
  const entries = [];
  let current = null;
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("-") || line.startsWith("•") || line.startsWith("*")) {
      if (current) entries.push(current);
      const claimText = line.replace(/^[-•*]\s*/, "").replace(/^"|"$/g, "").trim();
      current = {claim: claimText, sources: []};
    } else if (line.startsWith("←") || line.startsWith("→")) {
      const sourceMatch = line.match(/^[←→]\s*\[(CV|JD|Inference)\]\s*(.*)$/);
      if (sourceMatch && current) {
        const text = sourceMatch[2].replace(/^"|"$/g, "").trim();
        current.sources.push({kind: sourceMatch[1], text});
      }
    } else if (current && current.sources.length > 0) {
      // Continuation of the previous source line — append to last source
      const last = current.sources[current.sources.length - 1];
      last.text = (last.text + " " + line.replace(/^"|"$/g, "").trim()).trim();
    }
  }
  if (current) entries.push(current);
  return entries.filter((e) => e.claim || e.sources.length > 0);
}

// Phase 2 #80 in-context-highlight upgrade: locate a cited excerpt
// inside the source text + return surrounding context for rendering.
// Returns {found: true, before, match, after} when the excerpt is
// substring-matched in the source, or {found: false} otherwise.
// Context window: ~100 chars before + ~100 chars after the match,
// trimmed to word boundaries so the snippet doesn't start mid-word.
function locateExcerptInSource(excerpt, sourceText) {
  if (!excerpt || !sourceText) return {found: false};
  const ex = String(excerpt).trim().replace(/^"|"$/g, "");
  if (!ex) return {found: false};
  const src = String(sourceText);
  const idx = src.indexOf(ex);
  if (idx < 0) {
    // Try a case-insensitive search as fallback (AI may have
    // re-cased the citation).
    const lower = src.toLowerCase();
    const idxCi = lower.indexOf(ex.toLowerCase());
    if (idxCi < 0) return {found: false};
    return _buildContext(src, idxCi, ex.length);
  }
  return _buildContext(src, idx, ex.length);
}
function _buildContext(src, idx, matchLen) {
  const beforeStart = Math.max(0, idx - 100);
  const afterEnd = Math.min(src.length, idx + matchLen + 100);
  let before = src.slice(beforeStart, idx);
  let after = src.slice(idx + matchLen, afterEnd);
  // Trim to word boundaries so we don't start/end mid-word.
  if (beforeStart > 0) {
    const firstSpace = before.indexOf(" ");
    if (firstSpace >= 0 && firstSpace < 30) {
      before = "…" + before.slice(firstSpace);
    }
  }
  if (afterEnd < src.length) {
    const lastSpace = after.lastIndexOf(" ");
    if (lastSpace > after.length - 30) {
      after = after.slice(0, lastSpace) + "…";
    }
  }
  return {
    found: true,
    before,
    match: src.slice(idx, idx + matchLen),
    after,
  };
}

// Phase 2 #80: render the parsed sections into the Settings UI
// panel. Called from renderApplication() + the
// draft_cover_letter response handler so the panel updates
// whenever the textarea value changes. Citations are rendered as
// expandable <details> cards.
//
// In-context highlighting (top-tier upgrade): each [CV] / [JD]
// source is matched against the user's actual CV (state.profile.cvText)
// or the picked job's description (state.lastSearchResults's picked
// job, or the active imported job). When the excerpt is located,
// the surrounding context is shown with the excerpt wrapped in a
// <mark> tag for visual highlight. Excerpts NOT found in source get
// a "verify manually" warning — that's a genuine signal something
// could be off (AI may have invented the citation, or the user's CV
// changed since the draft was generated).
function renderCoverLetterSections(text) {
  const sections = parseCoverLetterSections(text);
  const subjectEl = $("#coverLetterSectionSubject");
  if (subjectEl) subjectEl.textContent = sections.subject || "—";
  const bodyEl = $("#coverLetterSectionBody");
  if (bodyEl) bodyEl.textContent = sections.body || "—";
  const editingEl = $("#coverLetterSectionEditingNotes");
  if (editingEl) editingEl.textContent = sections.editingNotes || "—";
  const assumpEl = $("#coverLetterSectionAssumptions");
  if (assumpEl) assumpEl.textContent = sections.assumptions || "—";
  const citationsEl = $("#coverLetterCitationsList");
  if (citationsEl) {
    const entries = parseCitations(sections.citations);
    // Sources for in-context highlighting. CV = the user's profile;
    // JD = the active imported job's description (or "" if no
    // job context).
    const cvText = state.profile?.cvText || state.profile?.cv_text || "";
    const jdText =
      state.activeImportedJob?.description
      || state.activeImportedJob?.discoveredDescription
      || "";
    citationsEl.innerHTML = "";
    if (entries.length === 0) {
      const li = document.createElement("li");
      li.className = "muted small";
      li.textContent = "—";
      citationsEl.appendChild(li);
    } else {
      for (const entry of entries) {
        const li = document.createElement("li");
        li.className = "cover-letter-citation";
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = entry.claim || "(unlabelled claim)";
        details.appendChild(summary);
        const ul = document.createElement("ul");
        ul.className = "cover-letter-citation-sources";
        for (const src of entry.sources) {
          const sli = document.createElement("li");
          const kindTag = document.createElement("span");
          kindTag.className = `cover-letter-citation-tag cover-letter-citation-tag-${src.kind.toLowerCase()}`;
          kindTag.textContent = `[${src.kind}]`;
          const textNode = document.createElement("span");
          textNode.textContent = " " + src.text;
          sli.appendChild(kindTag);
          sli.appendChild(textNode);
          // In-context-highlight upgrade: when source kind is CV or
          // JD, attempt to locate the excerpt in the actual source
          // text and render the surrounding context with the
          // excerpt wrapped in <mark>.
          if (src.kind === "CV" || src.kind === "JD") {
            const sourceText = src.kind === "CV" ? cvText : jdText;
            if (sourceText) {
              const located = locateExcerptInSource(src.text, sourceText);
              const ctx = document.createElement("div");
              ctx.className = "cover-letter-citation-context";
              if (located.found) {
                const beforeSpan = document.createElement("span");
                beforeSpan.className = "cover-letter-citation-context-before";
                beforeSpan.textContent = located.before;
                const mark = document.createElement("mark");
                mark.className = "cover-letter-citation-context-match";
                mark.textContent = located.match;
                const afterSpan = document.createElement("span");
                afterSpan.className = "cover-letter-citation-context-after";
                afterSpan.textContent = located.after;
                ctx.appendChild(beforeSpan);
                ctx.appendChild(mark);
                ctx.appendChild(afterSpan);
              } else {
                const warn = document.createElement("span");
                warn.className = "cover-letter-citation-context-missing";
                warn.textContent = `Excerpt not located in ${src.kind === "CV" ? "your CV" : "the job description"} — verify manually before sending.`;
                ctx.appendChild(warn);
              }
              sli.appendChild(ctx);
            }
          }
          ul.appendChild(sli);
        }
        details.appendChild(ul);
        li.appendChild(details);
        citationsEl.appendChild(li);
      }
    }
  }
}

function parseFindIntent(message, defaultLocation) {
  if (!message) return null;
  let m = String(message).trim();
  // Strip slash command prefix
  m = m.replace(/^\/(?:find|search)\s+/i, "");
  // Strip natural-language find/search verb
  m = m.replace(/^(?:find a job|search jobs|jobs suchen)\b\s*/i, "");
  m = m.replace(/^(?:find|search|suche|finde)\s+/i, "");
  if (!m) return null;
  // Extract trailing "in <city>" / "in Berlin" suffix
  let location = defaultLocation || "";
  // Allow letters (incl umlauts + sharp s), digits, hyphens, spaces; one or two words
  const locMatch = m.match(/\s+in\s+([\wäöüÄÖÜß\-]+(?:\s+[\wäöüÄÖÜß\-]+)?)\s*$/i);
  if (locMatch) {
    location = locMatch[1].trim();
    m = m.slice(0, locMatch.index).trim();
  }
  const query = m.trim();
  if (!query) return null;
  return { query, location };
}

// Phase 2 #77 sub-piece (d): consume an SSE event chunk + update the
// typing bubble's running narration. Three event families:
// - search_started / provider_ok / provider_error: append one-line
//   summary, cap at 6 lines so the bubble doesn't grow unbounded
// - ai_token: append tokens IN-PLACE to a single growing letter body
//   (no per-line summary; the body itself IS the narration)
// - done_payload / error: terminal — caller replaces the bubble
// First real event cancels the Loop 28 rotation timers since we now
// have actual server-side progress.
function handleStreamEvent(event, typingBubble) {
  if (!typingBubble || !typingBubble.nodes) return;
  // First real event: cancel pending milestone timers from Loop 28
  // rotation so they don't fight the actual server narration.
  for (const node of typingBubble.nodes) {
    if (node._typingTimers) {
      for (const id of node._typingTimers) clearTimeout(id);
      node._typingTimers = null;
    }
  }

  if (event.kind === "ai_token") {
    // AI token streaming: append text in-place to the running letter
    // body. Each node carries its own accumulated buffer because they
    // mirror across multiple chat surfaces (transcript + dock).
    const token = (event.data && event.data.text) || "";
    if (!token) return;
    for (const node of typingBubble.nodes) {
      if (typeof node._streamBuffer !== "string") node._streamBuffer = "";
      node._streamBuffer += token;
      // Show the full accumulated text — letter bodies stay readable.
      // Soft-cap rendering at 5000 chars (one full letter + a bit
      // more) so the bubble doesn't grow pathologically; tokens are
      // still buffered in _streamBuffer for the final replacement.
      const display = node._streamBuffer.slice(-5000);
      node.textContent = display;
      node.setAttribute("aria-label", "Drafting…");
    }
    return;
  }

  let line = "";
  if (event.kind === "search_started") {
    const providers = event.data.providers || [];
    line = `Querying ${providers.length} provider${providers.length !== 1 ? "s" : ""}…`;
  } else if (event.kind === "provider_ok") {
    const { provider, job_count, cached } = event.data;
    const cachedTag = cached ? " (cached)" : "";
    line = `✓ ${provider}: ${job_count} job${job_count !== 1 ? "s" : ""}${cachedTag}`;
  } else if (event.kind === "provider_error") {
    const { provider, error } = event.data;
    const errLabel = (error || "").split(":")[0] || "failed";
    line = `✗ ${provider}: ${errLabel}`;
  } else if (event.kind === "done_payload") {
    // No bubble update — the caller replaces the bubble with the
    // final reply on done_payload.
    return;
  } else if (event.kind === "error") {
    line = `Error: ${event.data.message || "stream failed"}`;
  }

  if (!line) return;
  for (const node of typingBubble.nodes) {
    const existing = node.textContent || "";
    const lines = existing.split("\n").filter((l) => l.trim());
    lines.push(line);
    const capped = lines.slice(-6);
    node.textContent = capped.join("\n");
    node.setAttribute("aria-label", capped.join("; "));
  }
}

// Phase 2 #77 sub-piece (d): generic SSE consumer used by both the
// find-jobs and AI-streaming paths. Takes a body to POST and a
// `onDonePayload(payload, elapsedMs)` callback that renders the
// final-payload-specific UI (search canvas vs letter draft).
// Returns true on a successful stream, false on transport failure
// (caller falls back to JSON path).
async function chatSendStreaming(rawMessage, body, category, onDonePayload) {
  chatAppendBubble("user", rawMessage || "(skip)");
  maybeShowExplainer(category);
  const typingLabel = TYPING_LABELS[category] || TYPING_LABELS.default;
  const startMs = Date.now();
  const typingBubble = chatAppendBubble("assistant", "…", {
    typing: true,
    typingLabel,
  });

  let response;
  try {
    response = await fetch("/api/chat/message/stream", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(state.auth?.user?.csrfToken
          ? { "X-CSRF-Token": state.auth.user.csrfToken }
          : {}),
      },
      body: JSON.stringify(body),
    });
  } catch (_) {
    if (typingBubble) typingBubble.remove();
    return false;
  }

  if (!response.ok || !response.body) {
    if (typingBubble) typingBubble.remove();
    return false;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload = null;
  let errorEvent = null;

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { value, done } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const rawChunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const event = parseSseChunk(rawChunk);
          if (!event) continue;
          handleStreamEvent(event, typingBubble);
          if (event.kind === "done_payload") donePayload = event.data;
          if (event.kind === "error") errorEvent = event.data;
        }
      }
      if (done) break;
    }
    if (buffer.trim()) {
      const event = parseSseChunk(buffer);
      if (event) {
        handleStreamEvent(event, typingBubble);
        if (event.kind === "done_payload") donePayload = event.data;
        if (event.kind === "error") errorEvent = event.data;
      }
    }
  } catch (err) {
    if (typingBubble) typingBubble.remove();
    chatAppendBubble("assistant", `Streaming error: ${err.message}`);
    return true;
  }

  if (typingBubble) typingBubble.remove();

  if (errorEvent) {
    chatAppendBubble(
      "assistant",
      `Error: ${errorEvent.message || "stream failed"}`,
    );
    return true;
  }

  if (!donePayload) {
    chatAppendBubble(
      "assistant",
      "Streaming response ended without a final payload.",
    );
    return true;
  }

  const elapsedMs = Date.now() - startMs;
  if (typeof onDonePayload === "function") {
    onDonePayload(donePayload, elapsedMs);
  }
  return true;
}

// Find-jobs streaming — thin wrapper around chatSendStreaming with the
// find-specific final-payload rendering (search canvas + nav).
async function chatSendFindStreaming(rawMessage, intent, category) {
  return chatSendStreaming(
    rawMessage,
    { kind: "find_jobs", query: intent.query, location: intent.location || "" },
    category,
    (donePayload, elapsedMs) => {
      if (donePayload.journeyPhase) state.lastJourneyPhase = donePayload.journeyPhase;
      chatAppendBubble(
        "assistant",
        donePayload.message || donePayload.reply || "(no reply)",
      );
      const footer = elapsedFooterFor(category, elapsedMs, donePayload);
      if (footer) chatAppendBubble("assistant", footer);
      const payloadJobs = donePayload.jobs;
      if (Array.isArray(payloadJobs) && payloadJobs.length) {
        state.lastSearchResults = {
          jobs: payloadJobs,
          query: intent.query,
          location: intent.location || "",
          categories: donePayload.categories,
        };
        renderSearchResults();
      }
      const navTarget = donePayload.navigateTo;
      if (navTarget) {
        const navBtn = document.querySelector(
          `.nav-item[data-view='${navTarget}']`,
        );
        if (navBtn) {
          navBtn.click();
        } else if (navTarget === "searchResults") {
          navigate("searchResults");
        }
      }
    },
  );
}

// Motivation-letter streaming — thin wrapper around chatSendStreaming
// with the letter-specific final-payload rendering.
async function chatSendLetterStreaming(rawMessage, category) {
  return chatSendStreaming(
    rawMessage,
    { kind: "draft_motivation_letter" },
    category,
    (donePayload, _elapsedMs) => {
      if (donePayload.journeyPhase) state.lastJourneyPhase = donePayload.journeyPhase;
      chatAppendBubble(
        "assistant",
        donePayload.message || donePayload.reply || "(no reply)",
      );
    },
  );
}

// Phase 2 #77 sub-piece (d): parse one raw SSE event chunk
// ("event: <kind>\ndata: <json>") into a {kind, data} object.
// Returns null on parse failure (silent — the chunk is just skipped).
function parseSseChunk(rawChunk) {
  if (!rawChunk) return null;
  const lines = rawChunk.split("\n");
  let kind = "";
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("event:")) {
      kind = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      // Allow multi-line data per SSE spec (concatenate with \n)
      dataStr = dataStr ? dataStr + "\n" + line.slice(5).trim() : line.slice(5).trim();
    }
  }
  if (!kind) return null;
  try {
    return { kind, data: JSON.parse(dataStr) };
  } catch (_) {
    return null;
  }
}

async function chatSend(message) {
  if (message == null) return;
  const category = typingCategoryFor(message, state.lastJourneyPhase || "");
  // Phase 2 #77 sub-piece (d): route find-intent messages through the
  // SSE endpoint when (a) the category is "search", (b) the message
  // parses as a find intent (slash / NL find verb), and (c) the
  // browser supports fetch with ReadableStream body. Otherwise fall
  // back to the JSON endpoint below — the JSON endpoint still benefits
  // from the parallel-fan-out speedup (sub-piece b) so non-streaming
  // clients aren't penalised.
  if (
    typeof window !== "undefined"
    && window.ReadableStream
    && typeof fetch === "function"
  ) {
    if (category === "search") {
      const intent = parseFindIntent(
        message,
        state.profile?.location || state.profile?.locationFilter || "",
      );
      if (intent && intent.query) {
        const streamed = await chatSendFindStreaming(message, intent, category);
        if (streamed) return;
        // chatSendFindStreaming returned falsy → fell back to JSON path
        // (network or HTTP error). Continue below with JSON dispatch.
      }
    } else if (category === "letter") {
      // Phase 2 #77 sub-piece (c+d): motivation-letter requests stream
      // tokens as the AI generates them. Picked job comes from the
      // server's journey state — no extra body parsing needed.
      const streamed = await chatSendLetterStreaming(message, category);
      if (streamed) return;
    }
  }
  chatAppendBubble("user", message || "(skip)");
  // PART 9 Loop 29: resolve typing category once + use it for both
  // the rotating label AND the one-time explainer + the
  // elapsed-time completion footer.
  maybeShowExplainer(category);
  // Loop 14.1 + Loop 28: phase-aware rotating typing label
  // (Gate 6.6 closure + PART 9 Loop 28 rotation refactor).
  const typingLabel = TYPING_LABELS[category] || TYPING_LABELS.default;
  const startMs = Date.now();
  const typingBubble = chatAppendBubble("assistant", "…", {typing: true, typingLabel});
  try {
    const payload = await api("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    if (typingBubble) typingBubble.remove();
    // Loop 14.1: cache the server-known journey phase for the
    // next chatSend's typingLabelFor() lookup.
    if (payload.journeyPhase) {
      state.lastJourneyPhase = payload.journeyPhase;
    }
    chatAppendBubble("assistant", payload.reply || "(no reply)");
    // PART 9 Loop 29: post-op elapsed-time footer with provider
    // count for search ops. Other categories self-narrate via the
    // rotating typing label and don't need a footer.
    const elapsedMs = Date.now() - startMs;
    const footer = elapsedFooterFor(category, elapsedMs, payload);
    if (footer) {
      chatAppendBubble("assistant", footer);
    }
    // R21.x: render the search-results canvas whenever a payload
    // carries jobs — regardless of whether it came from the
    // executed-command path (find_jobs direct) OR the journey path
    // (find_jobs via journey state machine). Without this, journey
    // users would see "Found 14 jobs" in chat but an empty canvas.
    const payloadJobs = payload.result?.jobs || payload.jobs;
    if (Array.isArray(payloadJobs) && payloadJobs.length) {
      state.lastSearchResults = {
        jobs: payloadJobs,
        query: payload.result?.query
                || (payload.reply || "").match(/Found \*\*\d+\*\* ([^*]+?) result/)?.[1]
                || "",
        location: payload.result?.location || "",
        categories: payload.result?.categories || payload.categories,
      };
      renderSearchResults();
    }
    const navTarget = payload.result?.navigateTo || payload.navigateTo;
    if (navTarget) {
      const navBtn = document.querySelector(`.nav-item[data-view='${navTarget}']`);
      if (navBtn) {
        navBtn.click();
      } else if (navTarget === "searchResults") {
        navigate("searchResults");
      }
    }
    if (payload.awaiting) {
      setText("#chatPendingHint", `Awaiting: ${payload.awaiting}`);
    } else if (payload.awaitingConfirmation) {
      setText("#chatPendingHint",
              "Reply yes / no to confirm.");
    } else if (payload.executed) {
      setText("#chatPendingHint", `Last executed: ${payload.executed}`);
      // Search-results + navigation are rendered above (shared with
      // journey-driven path). Just refresh bootstrap so unrelated
      // UI cards reflect any DB write the executed command made.
      try {
        const fresh = await api("/api/bootstrap");
        absorbBootstrap(fresh);
        render();
      } catch (_) { /* non-fatal */ }
    } else {
      setText("#chatPendingHint", "");
    }
  } catch (err) {
    chatAppendBubble("assistant", `Error: ${err.message}`);
  }
}

function chatFormHandler(inputSel) {
  return (event) => {
    event.preventDefault();
    const input = $(inputSel);
    const message = input?.value || "";
    if (input) input.value = "";
    chatSend(message);
  };
}
function chatResetHandler() {
  return async () => {
    try {
      await api("/api/chat/reset",
                  { method: "POST", body: JSON.stringify({}) });
    } catch (err) {
      chatAppendBubble("assistant", `Error: ${err.message}`);
      return;
    }
    for (const sel of ["#chatTranscript", "#dockChatTranscript"]) {
      const host = $(sel);
      if (host) host.innerHTML = "";
    }
    setText("#chatPendingHint", "");
    setText("#dockChatPendingHint", "");
    chatAppendBubble("assistant",
                       "Chat reset. Type a message or /help to begin.");
  };
}

// R21.6: any user interaction with the chat dock means they've
// chosen the chat-first path — silently dismiss the first-run
// wizard so it stops intercepting their flow. Called from both
// submit and focus so even "typing in the input" counts.
function dismissWizardForDockInteraction() {
  const dialog = document.getElementById("firstRunWizard");
  if (dialog?.open) {
    // Same persistence call as wizardDismiss, but fire-and-forget.
    api("/api/profile",
        { method: "POST",
          body: JSON.stringify({ onboardingDismissed: true }) })
      .catch(() => { /* non-fatal */ });
    dialog.close();
  }
}

$("#chatForm")?.addEventListener("submit", chatFormHandler("#chatInput"));
$("#dockChatForm")?.addEventListener("submit", (event) => {
  dismissWizardForDockInteraction();
  return chatFormHandler("#dockChatInput")(event);
});
$("#dockChatInput")?.addEventListener("focus",
                                         dismissWizardForDockInteraction);

$("#chatHelpBtn")?.addEventListener("click", () => chatSend("/help"));
$("#dockChatHelpBtn")?.addEventListener("click", () => chatSend("/help"));

$("#chatResetBtn")?.addEventListener("click", chatResetHandler());
$("#dockChatResetBtn")?.addEventListener("click", chatResetHandler());

// On first chat-view focus OR first appearance of the dock, seed
// a welcome bubble if the transcript is empty.
function seedChatWelcomeOnce() {
  const dock = $("#dockChatTranscript");
  if (dock && dock.childElementCount === 0) {
    chatAppendBubble("assistant",
                       "Hi — tell me what you want to do, or type **find a job** to start.");
    return;
  }
  const host = $("#chatTranscript");
  if (host && host.childElementCount === 0) {
    chatAppendBubble("assistant",
                       "Hi — tell me what you want to do, or type **find a job** to start.");
  }
}
document.addEventListener("click", (event) => {
  const target = event.target.closest(".nav-item[data-view='assistant']");
  if (!target) return;
  setTimeout(() => {
    seedChatWelcomeOnce();
    const input = $("#chatInput") || $("#dockChatInput");
    if (input) input.focus();
  }, 60);
});

$("#cvBuilderDownloadPdfBtn")?.addEventListener("click", () => {
  // Open the print page in a new tab with autoprint=1 — the browser's
  // print dialog appears and the user picks "Save as PDF" as the
  // destination. Zero server-side PDF dependency.
  window.open("/api/cv/print?autoprint=1", "_blank", "noopener");
});
$("#cvBuilderPreviewBtn")?.addEventListener("click", () => {
  window.open("/api/cv/print", "_blank", "noopener");
});
$("#cvBuilderPhotoBtn")?.addEventListener("click", () => $("#cvBuilderPhotoInput")?.click());
$("#cvBuilderPhotoInput")?.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) cvBuilderUploadPhoto(file);
});
$("#cvBuilderPhotoRemove")?.addEventListener("click", cvBuilderRemovePhoto);

// When the user navigates to the CV builder view, refresh state +
// pre-populate the photo preview from their profile.
document.addEventListener("click", (event) => {
  const target = event.target.closest(".nav-item[data-view='cvBuilder']");
  if (!target) return;
  // The view-switch handler runs separately; we just need to lazy-init
  // the builder state on first nav.
  setTimeout(() => {
    const profilePhoto = state.profile?.cvPhotoDataUri;
    if (profilePhoto && !cvBuilder.photoDataUri) {
      cvBuilder.photoDataUri = profilePhoto;
    }
    cvBuilderRefresh();
  }, 50);
});

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
  const previous = state.locale;
  const sel = event.target;
  // Disable while in flight so a quick second click doesn't double-fire.
  sel.disabled = true;
  try {
    // Save server-side FIRST and don't swallow errors. If this fails the
    // localStorage write below would lie to the next boot — server's stale
    // value would win on the bootstrap re-render and the language flip back.
    await api("/api/profile", { method: "POST", body: JSON.stringify({ locale: value }) });
    try { localStorage.setItem("dj_locale", value); } catch (_) {}
    showToast(t("settings.locale.switching", "Switching language…"), "info", 800);
    setTimeout(() => location.reload(), 220);
  } catch (error) {
    sel.value = previous;
    sel.disabled = false;
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
$("#manageSubscriptionBtn")?.addEventListener("click", manageSubscription);
$("#shareEnabledToggle")?.addEventListener("change", async (event) => {
  const toggle = event.target;
  const jobId = toggle.dataset.jobId;
  if (!jobId) return;
  const enabled = Boolean(toggle.checked);
  toggle.disabled = true;
  try {
    const payload = await api(`/api/imported-jobs/${encodeURIComponent(jobId)}/share`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    });
    absorbBootstrap(payload.bootstrap);
    const job = state.importedJobs.find((j) => j.id === jobId);
    if (job) {
      job.share_enabled = payload.job?.share_enabled ?? enabled;
      renderSharePanel(job);
    }
    showToast(
      enabled
        ? t("applications.share.enabled", "Share link enabled.")
        : t("applications.share.disabled", "Share link disabled."),
      "success",
    );
  } catch (error) {
    toggle.checked = !enabled;
    showToast(error.message, "error");
  } finally {
    toggle.disabled = false;
  }
});
$("#copyShareUrlBtn")?.addEventListener("click", async () => {
  const url = $("#shareUrl")?.textContent || "";
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
    showToast(t("applications.share.copied", "Share URL copied."), "success");
  } catch (error) {
    showToast(error.message || "Could not copy.", "error");
  }
});
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
//
// Auto-reload when a new SW activates so the user picks up new HTML /
// JS / CSS without having to hard-refresh. The SW posts a message on
// activate; we reload the page in response. Guarded against reload
// loops by a session-storage marker so a buggy SW can't spam reload.
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  // Snapshot at page load: if no controller exists yet, this is a
  // first-time SW install (or the user just hard-reloaded). In that
  // case, controllerchange will fire as the SW takes over, but the
  // page already has the latest JS — reloading is gratuitous AND it
  // races with user input. Concretely: an in-flight registration form
  // mid-fill would lose its values, then the user clicks Submit and
  // sends an empty payload.
  const __hadInitialController = !!navigator.serviceWorker.controller;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
  navigator.serviceWorker.addEventListener("message", (event) => {
    if (event.data?.type === "sw-updated") {
      if (!__hadInitialController) return;  // first install, no reload
      const last = sessionStorage.getItem("__sw_reload_v");
      if (last !== event.data.version) {
        sessionStorage.setItem("__sw_reload_v", event.data.version);
        window.location.reload();
      }
    }
  });
  // When the controller changes (a new SW took over), reload once to
  // ensure the page is running the latest shell. Skip the first
  // install — see the comment on __hadInitialController above.
  let __reloadingOnControllerChange = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!__hadInitialController) return;
    if (__reloadingOnControllerChange) return;
    __reloadingOnControllerChange = true;
    window.location.reload();
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
