// Copyright (c) 2026 Helpmefindthejob contributors
// SPDX-License-Identifier: Apache-2.0
//
// Status page client.
//
// 2026-05-23 extension (Public status page with uptime history):
//   - 30-day uptime tile alongside 24h / 7d
//   - 24-cell visual uptime bar (one cell per hour, green/amber/red
//     based on the per-hour ok% from /api/health/history?window=24)
//   - Response-time trend (last 20 latency samples + p50/p95 stats)
//
// Original surface from AUDIT-2 (2026-05-22) extraction unchanged —
// polls /api/health every 30 s, hydrates the overall pill + app
// version + storage + latency. External file referenced via
// `<script src="/status.js" defer>` because production CSP is
// `script-src 'self'`.

"use strict";

const REFRESH_MS = 30000;
const TIMEOUT_MS = 5000;
const LATENCY_TREND_LEN = 20;

const overall = document.getElementById("overallPill");
const lastChecked = document.getElementById("lastChecked");
const appStatus = document.getElementById("appStatus");
const appVersion = document.getElementById("appVersion");
// 2026-05-23 (UX-A2): Storage card deleted; AUDIT-42 stripped
// `storage` from public /api/health, so the field never arrived
// and the card showed an em-dash placeholder. Backend info lives
// on /api/admin/system-info now.
const appLatency = document.getElementById("appLatency");
const uptime24h = document.getElementById("uptime24h");
const uptime7d = document.getElementById("uptime7d");
const uptime30d = document.getElementById("uptime30d");
const uptimeBar = document.getElementById("uptimeBar");
const latencyTrend = document.getElementById("latencyTrend");
const latencyStats = document.getElementById("latencyStats");

const latencyBuffer = [];  // last N latency samples (ms)

function setOverall(state, text) {
  if (!overall) return;
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

function renderUptimeBar(payload) {
  if (!uptimeBar) return;
  uptimeBar.replaceChildren();
  const snapshots = (payload && payload.snapshots) || [];
  const now = Date.now();
  const ONE_HOUR = 3_600_000;
  // 24 hourly buckets, [0] = oldest, [23] = current hour
  const buckets = Array.from({ length: 24 }, () => ({ ok: 0, total: 0 }));
  for (const snap of snapshots) {
    const t = Date.parse(snap.at);
    if (Number.isNaN(t)) continue;
    const hoursAgo = Math.floor((now - t) / ONE_HOUR);
    const idx = 23 - hoursAgo;
    if (idx < 0 || idx > 23) continue;
    buckets[idx].total += 1;
    if (snap.status === "ok") buckets[idx].ok += 1;
  }
  for (let i = 0; i < 24; i += 1) {
    const b = buckets[i];
    const cell = document.createElement("span");
    cell.className = "uptime-cell";
    const hourLabel = `${23 - i}h ago`;
    if (b.total === 0) {
      cell.classList.add("uptime-cell--empty");
      cell.title = `${hourLabel}: no data`;
    } else {
      const pct = (100 * b.ok) / b.total;
      if (pct >= 99) cell.classList.add("uptime-cell--ok");
      else if (pct >= 80) cell.classList.add("uptime-cell--warn");
      else cell.classList.add("uptime-cell--bad");
      cell.title = `${hourLabel}: ${pct.toFixed(0)}% (${b.ok}/${b.total} checks ok)`;
    }
    uptimeBar.appendChild(cell);
  }
}

function renderLatencyTrend() {
  if (!latencyTrend) return;
  if (latencyBuffer.length === 0) {
    // 2026-05-23 (UX-A3): keep the SSR-rendered empty-state copy
    // ("Not enough data yet — check back in a minute.") instead
    // of overwriting it with a bare em-dash. The em-dash looked
    // like the feature was broken.
    return;
  }
  // Simple Unicode block sparkline — 8 levels
  const levels = "▁▂▃▄▅▆▇█";
  const max = Math.max(...latencyBuffer);
  const min = Math.min(...latencyBuffer);
  const range = Math.max(1, max - min);
  const chars = latencyBuffer.map((v) => {
    const idx = Math.min(7, Math.floor(((v - min) / range) * 7));
    return levels[idx];
  }).join("");
  latencyTrend.textContent = chars;
  if (latencyStats) {
    const sorted = [...latencyBuffer].sort((a, b) => a - b);
    const p50 = sorted[Math.floor(sorted.length / 2)];
    const p95 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))];
    latencyStats.textContent = `min ${min} ms · p50 ${p50} ms · p95 ${p95} ms · max ${max} ms`;
  }
}

async function loadUptimeHistory() {
  try {
    const [r24, r7d, r30d] = await Promise.all([
      fetch("/api/health/history?window=24", { cache: "no-store" }),
      fetch("/api/health/history?window=168", { cache: "no-store" }),
      fetch("/api/health/history?window=720", { cache: "no-store" }),
    ]);
    if (r24.ok) {
      const payload = await r24.json();
      if (uptime24h) uptime24h.textContent = formatUptime(payload);
      renderUptimeBar(payload);
    }
    if (r7d.ok && uptime7d) uptime7d.textContent = formatUptime(await r7d.json());
    if (r30d.ok && uptime30d) uptime30d.textContent = formatUptime(await r30d.json());
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
  if (lastChecked) lastChecked.textContent = `Checked ${new Date().toLocaleTimeString()}`;
  if (ok && payload) {
    setOverall("ok", "Operational");
    if (appStatus) appStatus.textContent = payload.status;
    if (appVersion) appVersion.textContent = payload.version || "—";
    // appStorage deleted — see top-of-file comment.
    if (appLatency) appLatency.textContent = `${latency} ms`;
    // Only push successful checks into the latency trend; failures
    // would skew the line with timeout-bounded values.
    latencyBuffer.push(latency);
    if (latencyBuffer.length > LATENCY_TREND_LEN) latencyBuffer.shift();
    renderLatencyTrend();
  } else {
    setOverall("bad", "Degraded");
    if (appStatus) appStatus.textContent = "unreachable";
    if (appLatency) appLatency.textContent = `${latency} ms (timeout/error)`;
  }
  loadUptimeHistory();
}

tick();
setInterval(tick, REFRESH_MS);
