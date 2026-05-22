// Copyright (c) 2026 Helpmefindthejob contributors
// SPDX-License-Identifier: Apache-2.0
//
// Status page client: polls /api/health every 30s, hydrates the
// overall pill + app status + uptime history cells. Extracted from
// status.html's inline <script> on 2026-05-22 (AUDIT-2) because the
// production CSP is `script-src 'self'` with no `'unsafe-inline'` —
// the inline script was being blocked silently, freezing the pill on
// initial render. External file referenced via `<script src="/status.js" defer>`.

const REFRESH_MS = 30000;
const TIMEOUT_MS = 5000;
const overall = document.getElementById("overallPill");
const lastChecked = document.getElementById("lastChecked");
const appStatus = document.getElementById("appStatus");
const appVersion = document.getElementById("appVersion");
const appStorage = document.getElementById("appStorage");
const appLatency = document.getElementById("appLatency");
const uptime24h = document.getElementById("uptime24h");
const uptime7d = document.getElementById("uptime7d");

function setOverall(state, text) {
  overall.classList.remove("ok", "warn", "bad");
  overall.classList.add(state);
  overall.textContent = text;
}

function formatUptime(payload) {
  if (!payload || payload.uptimePercent == null) {
    return payload && payload.snapshotCount === 0 ? "no data yet" : "—";
  }
  return `${payload.uptimePercent.toFixed(2)}%`;
}

async function loadUptimeHistory() {
  try {
    const [r24, r7d] = await Promise.all([
      fetch("/api/health/history?window=24", { cache: "no-store" }),
      fetch("/api/health/history?window=168", { cache: "no-store" }),
    ]);
    if (r24.ok) uptime24h.textContent = formatUptime(await r24.json());
    if (r7d.ok) uptime7d.textContent = formatUptime(await r7d.json());
  } catch (_) {
    // best-effort — leave dashes
  }
}

async function tick() {
  const start = performance.now();
  let ok = false;
  let payload = null;
  try {
    const ctrl = new AbortController();
    const id = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const resp = await fetch("/api/health", { signal: ctrl.signal, cache: "no-store" });
    clearTimeout(id);
    if (resp.ok) {
      payload = await resp.json();
      ok = payload && payload.status === "ok";
    }
  } catch (_) {
    ok = false;
  }
  const latency = Math.round(performance.now() - start);
  lastChecked.textContent = `Checked ${new Date().toLocaleTimeString()}`;
  if (ok && payload) {
    setOverall("ok", "Operational");
    appStatus.textContent = payload.status;
    appVersion.textContent = payload.version || "—";
    appStorage.textContent = payload.storage || "—";
    appLatency.textContent = `${latency} ms`;
  } else {
    setOverall("bad", "Degraded");
    appStatus.textContent = "unreachable";
    appLatency.textContent = `${latency} ms (timeout/error)`;
  }
  // Refresh uptime tallies alongside the live check
  loadUptimeHistory();
}

tick();
setInterval(tick, REFRESH_MS);
