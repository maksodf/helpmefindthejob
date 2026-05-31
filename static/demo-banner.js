// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 Helpmefindthejob contributors
//
// The "demo deployment" banner.
//
// When the user is on `demo.helpmefindthejob.org` (or has the
// `?demo=1` query param for QA), reveal a small banner explaining
// that accounts reset nightly so the user does not worry about
// mutating shared data.
//
// Why client-side hostname check rather than server-side env var:
// the demo subdomain reverse-proxies to the same backend instance
// as the live apex (per `deploy/Caddyfile` — both hostnames share
// one upstream). Distinguishing demo vs apex therefore happens at
// the hostname layer, not the backend. A pure-JS check is the
// simplest correct mechanism and ships with zero server changes.
//
// The banner div lives in `static/index.html` with the `hidden`
// attribute so it never appears on the apex. This script reveals
// it iff the runtime hostname matches.

(function () {
  "use strict";

  var DEMO_HOST_SUFFIX = "demo.helpmefindthejob.org";
  var url;
  try {
    url = new URL(window.location.href);
  } catch (e) {
    return;
  }

  var isDemoHost = url.hostname === DEMO_HOST_SUFFIX;
  var demoQueryParam = url.searchParams.get("demo") === "1";
  if (!isDemoHost && !demoQueryParam) {
    return;
  }

  var banner = document.getElementById("demoBanner");
  if (!banner) return;
  banner.hidden = false;
  // Mark the body so other CSS hooks (e.g., shifting layout to
  // make room for the banner) can react.
  document.body.classList.add("demo-mode");
})();
