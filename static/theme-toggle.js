// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 Helpmefindthejob contributors
//
// UX-F1 (2026-05-23): theme-toggle for public content pages
// (legal, /help, /status, /changelog, /api/docs, /forgot-password,
// 404). These pages don't load the full SPA app.js, so they need
// their own lightweight theme handling. The SPA's app.js has its
// own applyTheme()/cmdK toggle for signed-in users.
//
// Behaviour:
// * On load, the active theme is whatever `data-theme` attribute
//   the server set on <html> (via the `theme` cookie). If no cookie,
//   the @media (prefers-color-scheme: light) CSS block kicks in for
//   light-OS users, otherwise the dark default applies. So there is
//   NO flash of wrong theme.
// * Clicking the toggle cycles between dark and light explicitly.
//   The choice persists via the `theme` cookie (one year) + the
//   `dj_theme` localStorage key (fallback for third-party-cookie
//   blockers).
// * The toggle button is keyboard-accessible (it's a real
//   <button>); the icon visibility flips via CSS (.icon-sun vs
//   .icon-moon) so we never need to manipulate the DOM tree.

(function () {
  "use strict";

  var btn = document.getElementById("siteHeaderThemeToggle");
  if (!btn) return;
  var html = document.documentElement;

  function readStored() {
    // Cookie takes precedence (server is the source of truth).
    var cookieMatch = document.cookie.match(/(?:^|;\s*)theme=([^;]+)/);
    if (cookieMatch) {
      var val = decodeURIComponent(cookieMatch[1]);
      if (val === "light" || val === "dark") return val;
    }
    try {
      var ls = window.localStorage.getItem("dj_theme");
      if (ls === "light" || ls === "dark") return ls;
    } catch (_) { /* localStorage blocked */ }
    return null;
  }

  function resolveActive() {
    var stored = readStored();
    if (stored) return stored;
    // No explicit choice → reflect the @media prefers-color-scheme.
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  }

  function setTheme(theme) {
    if (theme !== "light" && theme !== "dark") return;
    html.dataset.theme = theme;
    // Cookie for SSR on next request — 1 year, root path, SameSite=Lax
    // so it travels with normal navigation but blocks third-party use.
    var expires = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toUTCString();
    document.cookie = "theme=" + encodeURIComponent(theme) +
      "; expires=" + expires +
      "; path=/; SameSite=Lax";
    try { window.localStorage.setItem("dj_theme", theme); } catch (_) { /* ignore */ }
    btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
  }

  // Sync the button's aria-pressed at load so screen readers
  // announce the current state.
  btn.setAttribute("aria-pressed", resolveActive() === "light" ? "true" : "false");

  btn.addEventListener("click", function () {
    var next = resolveActive() === "light" ? "dark" : "light";
    setTheme(next);
  });

  // UX-A10/E3 (2026-05-23): auto-generate an in-page TOC for long
  // legal pages (privacy / terms / data-retention / impressum).
  // Triggered when the page has 4+ h2 sections inside .legal-page,
  // so short pages don't get a useless 1-item nav.
  (function buildLegalToc() {
    var page = document.querySelector(".legal-page");
    if (!page) return;
    var sections = page.querySelectorAll(":scope > section > h2");
    if (sections.length < 4) return;
    // Skip if a TOC is already present (manual on /help, /changelog).
    if (page.querySelector(".legal-toc")) return;
    if (page.querySelector('nav[aria-label="On this page"]')) return;

    function slugify(text) {
      return (text || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "")
        .slice(0, 60);
    }

    var nav = document.createElement("nav");
    nav.className = "legal-toc";
    nav.setAttribute("aria-label", "On this page");
    var ol = document.createElement("ol");

    var seen = {};
    for (var i = 0; i < sections.length; i += 1) {
      var h2 = sections[i];
      var parent = h2.parentElement;
      if (!parent) continue;
      var label = (h2.textContent || "").trim();
      if (!label) continue;
      var base = slugify(label) || ("section-" + (i + 1));
      var id = base;
      var n = 2;
      while (seen[id]) { id = base + "-" + n; n += 1; }
      seen[id] = true;
      if (!parent.id) parent.id = id;
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + parent.id;
      a.textContent = label;
      li.appendChild(a);
      ol.appendChild(li);
    }
    nav.appendChild(ol);

    // Insert the TOC right after the <header> if present, else as
    // the first child of .legal-page.
    var header = page.querySelector(":scope > header");
    if (header) {
      header.insertAdjacentElement("afterend", nav);
    } else {
      page.insertAdjacentElement("afterbegin", nav);
    }
  })();

  // If the user toggles their OS theme AND has no explicit choice,
  // follow the system. Once they've clicked the button, their choice
  // is sticky (the cookie wins).
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: light)");
    var listener = function () {
      if (readStored()) return; // explicit choice — don't override
      // Just let the CSS @media block re-apply; no DOM change needed.
      btn.setAttribute("aria-pressed", mq.matches ? "true" : "false");
    };
    if (mq.addEventListener) {
      mq.addEventListener("change", listener);
    } else if (mq.addListener) {
      mq.addListener(listener);  // Safari < 14 / very old browsers
    }
  }
})();
