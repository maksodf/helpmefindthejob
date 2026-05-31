<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# PWA install-banner verification recipe

**Audience**: maintainer's per-release pre-flight checklist + deployer's first-launch verification.
**Status**: living recipe. Re-run on every major release; append a dated row to §3 on each verification.

---

## 1. Why this recipe exists

The PWA install banner is a browser-side prompt offered by Chromium-based browsers when the install-eligibility criteria are all met simultaneously. iOS Safari does NOT fire `beforeinstallprompt` — it surfaces "Add to Home Screen" through the share sheet instead. Both pathways are covered by the same manifest + service-worker contract on the project side; the verification differs per platform.

The install-eligibility criteria are testable programmatically against the static-file contract (see `tests/test_pwa_install_eligibility.py` — 7 tests across 5 TestCase classes covering criteria 2-5 from the W3C list). Criteria 1 (HTTPS context) + 6 (Chrome heuristics) are environmental — not testable from a unit test, only via a real device or emulator. This recipe documents the manual cadence for that environmental verification.

---

## 2. Per-platform verification recipe

### Chrome Android (Chromium-based)

1. Visit `https://helpmefindthejob.org` (or `https://demo.helpmefindthejob.org` once the demo subdomain is live) in Chrome on an Android device or via Chrome DevTools mobile emulation.
2. Wait for the page to load + interact (scroll, click anywhere). The user-gesture heuristic requires interaction before Chrome will offer the install prompt.
3. Expected: within ~10 seconds of meaningful interaction, Chrome surfaces a "Install Helpmefindthejob" banner OR a small install icon in the address bar.
4. If the banner / icon does NOT appear:
   - Open DevTools → Application tab → Manifest. Chrome lists every install-eligibility issue under "Issues" or "Warnings".
   - Open DevTools → Application → Service Workers. Confirm the SW is registered + activated + has scope `/`.
   - Open DevTools → Lighthouse → PWA category. Run the audit. Lighthouse explicitly names each missing criterion.
5. Once the banner appears, click "Install" (or the address-bar icon). The app should install + appear on the home screen with the manifest's name + icon.
6. Open the installed app. The display mode should be `standalone` per `manifest.webmanifest` — no browser chrome visible.

### iOS Safari (Add to Home Screen flow)

1. Visit `https://helpmefindthejob.org` (or the demo subdomain) in Safari on iOS.
2. Tap the share icon (square-with-up-arrow at the bottom of the screen).
3. Scroll the share-sheet bottom section to find "Add to Home Screen". (If absent, swipe up on the bottom action-row to surface the full list.)
4. The "Add to Home Screen" sheet shows the manifest's name + icon as a preview. Tap "Add" in the top-right.
5. The app appears on the home screen with the manifest's name + icon. Opening it launches Safari in PWA-mode (display standalone) without the browser chrome.

iOS Safari has additional quirks the recipe records:
- Safari requires the user to discover the share-sheet manually; there's no auto-prompt analogous to Chrome's banner.
- iOS PWA storage is sandboxed per origin; uninstall purges the storage. Deployers who serve sensitive workflow data should educate users about this.
- Some iOS Safari versions don't honour `theme_color` in the standalone-mode status bar; cosmetic only.

### Chrome Desktop (additional install path)

Chrome Desktop (Windows / macOS / Linux) supports the same install-eligibility flow as Chrome Android, with the prompt surfacing as a small install icon in the address bar instead of a banner. Click → Install. The installed app launches as a standalone window. Useful for self-hosters who want to pin the app to their dock / taskbar.

---

## 3. Verification log

| Date | Platform | URL | Result | Notes |
|---|---|---|---|---|
| 2026-05-24 | Static-file contract (programmatic) | n/a | ✓ install-eligibility tests pass (`tests/test_pwa_install_eligibility.py`) | Initial verification of the manifest + service-worker + index.html contract. Per-platform live-device verification scheduled for 2026-Q3 alongside the v0.80.0 + DNS-flipped demo subdomain. |
| (future) | Chrome Android | `https://helpmefindthejob.org` | (operator fills) | First per-platform live verification — runs once the demo subdomain DNS resolves + after 1.1.1 closes. |
| (future) | iOS Safari | `https://helpmefindthejob.org` | (operator fills) | Same cadence as Chrome Android. |
| (future) | Chrome Desktop | `https://helpmefindthejob.org` | (operator fills) | Same cadence. |

Future rows append below. Per-release cadence at minimum.

---

## 4. Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| Install banner doesn't appear on Chrome Android | One of the install-eligibility criteria not met | DevTools → Application → Manifest "Issues" section |
| `beforeinstallprompt` event never fires in JS | Page not served over HTTPS (or localhost); manifest missing or invalid; SW not registered | DevTools → Application → Service Workers + Manifest |
| Installed app shows browser chrome instead of standalone | `display` field in manifest not set to `standalone` or `fullscreen` | `static/manifest.webmanifest` |
| Icon displays as default browser icon instead of branded | `icons` array missing the ≥192×192 PNG OR `sizes="any"` SVG entry | `static/manifest.webmanifest` icons array |
| iOS "Add to Home Screen" missing | Some iOS versions hide the option for sites without `apple-mobile-web-app-capable` meta tag | `static/index.html` head — add `<meta name="apple-mobile-web-app-capable" content="yes">` (if absent) |

For the static-file contract issues, the programmatic test (`tests/test_pwa_install_eligibility.py`) catches them at CI time — a failing test there is the first place to look before opening DevTools.

---

## 5. Cross-references

- Static-file contract test: [`tests/test_pwa_install_eligibility.py`](https://github.com/maksodf/helpmefindthejob/blob/main/tests/test_pwa_install_eligibility.py)
- Existing PWA / offline-mode contract test: [`tests/test_pwa_offline.py`](https://github.com/maksodf/helpmefindthejob/blob/main/tests/test_pwa_offline.py)
- Web app manifest: `static/manifest.webmanifest`
- Service worker: `static/sw.js`
- W3C install-eligibility criteria reference: <https://web.dev/learn/pwa/installation-prompt/>
- Chrome install-eligibility detail: <https://web.dev/articles/install-criteria>
- iOS Safari "Add to Home Screen" reference: <https://developer.apple.com/documentation/webkit>
