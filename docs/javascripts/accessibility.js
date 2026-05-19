/* SPDX-License-Identifier: Apache-2.0 */
/* Copyright (c) 2026 Helpmefindthejob contributors */

/* Helpmefindthejob — accessibility workarounds for mkdocs-material.
 *
 * The §3.6 first-pass accessibility audit (axe-core CLI 4.11.4,
 * 2026-05-19) found that mkdocs-material renders its search dialog
 * with `role="dialog"` but no accessible name (no aria-label /
 * aria-labelledby / title), failing axe's `aria-dialog-name` rule
 * (SERIOUS). This is an upstream theme issue, not project markup.
 *
 * Workaround: at DOMContentLoaded, set aria-label="Site search" on
 * any `.md-search[role="dialog"]` element that lacks an accessible
 * name. Idempotent (re-running is a no-op). Removing the override
 * is safe when mkdocs-material ships the fix upstream.
 *
 * Audit evidence: docs/grant/accessibility-audit-2026-05-19/ (raw
 * axe JSON). Remediation reference: ACCESSIBILITY.md.
 */

(function () {
  function patchSearchDialog() {
    var nodes = document.querySelectorAll('.md-search[role="dialog"]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (!el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby")) {
        el.setAttribute("aria-label", "Site search");
      }
    }
  }

  // mkdocs-material's content.code.copy feature wraps each code block's
  // copy button in `<nav class="md-code__nav">`. When a page contains
  // more than one code block, axe's `landmark-unique` rule (MODERATE)
  // flags every nav after the first because they all share the same
  // implicit "navigation" landmark name. Surfaced 2026-05-19 post-rename
  // audit. Each nav gets a unique aria-label derived from its anchor id.
  function patchCodeBlockNavs() {
    var navs = document.querySelectorAll("nav.md-code__nav");
    for (var i = 0; i < navs.length; i++) {
      var nav = navs[i];
      if (nav.getAttribute("aria-label") || nav.getAttribute("aria-labelledby")) {
        continue;
      }
      var parent = nav.parentElement;
      var id = parent ? parent.getAttribute("id") : null;
      var label = id ? "Code block actions for " + id : "Code block actions " + (i + 1);
      nav.setAttribute("aria-label", label);
    }
  }

  function patchAll() {
    patchSearchDialog();
    patchCodeBlockNavs();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchAll);
  } else {
    patchAll();
  }
})();
