/* Helpmefindthejob bookmarklet — readable source.
 *
 * The Settings page minifies this into a single-line `javascript:` URL the
 * user drags to their bookmark bar. When they click it on Indeed / LinkedIn /
 * StepStone / Xing (or any job page), it opens
 * https://app.helpmefindthejob.org/capture?u=…&t=… in a new tab. The capture page is
 * served by app.py's /capture route, requires the user's existing Helpmefindthejob
 * session, persists the URL+title as a DiscoveredJob, then redirects back to
 * /queue.
 *
 * NOTE: this file is committed for readability + tests. The runtime payload
 * is generated server-side (so we can stamp the user's helpmefindthejob.org host onto
 * the URL without hardcoding it here).
 */
(function () {
  var url = window.location.href;
  // Best-effort title extraction across the four big platforms.
  function pick(selectors) {
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el && el.textContent && el.textContent.trim()) {
        return el.textContent.trim();
      }
    }
    return "";
  }
  var title = pick([
    "h1.jobsearch-JobInfoHeader-title",       // Indeed
    "h1[data-test='job-title']",              // Indeed (newer)
    "h1.t-24, h1.top-card-layout__title",     // LinkedIn
    "h1[data-at='header-job-title']",         // StepStone
    "[data-at='job-title']",                  // StepStone (newer)
    "h1.job-detail-title",                    // Xing
    "h1",                                     // generic fallback
    "title",
  ]) || document.title || "";
  var endpoint = window.__HELPMEFINDTHEJOB_CAPTURE_URL__ ||
    "https://app.helpmefindthejob.org/capture";
  var target = endpoint +
    "?u=" + encodeURIComponent(url) +
    "&t=" + encodeURIComponent(title.slice(0, 200));
  window.open(target, "_blank", "noopener,noreferrer");
})();
