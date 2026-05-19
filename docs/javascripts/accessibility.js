/* SPDX-License-Identifier: Apache-2.0 */
/* Copyright (c) 2026 DirectJob Scout contributors */

/* DirectJob Scout — accessibility workarounds for mkdocs-material.
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchSearchDialog);
  } else {
    patchSearchDialog();
  }
})();
