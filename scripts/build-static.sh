#!/usr/bin/env sh
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# build-static.sh — AUDIT-17 production-bundle builder.
#
# Regenerates the two minified bundles the production HTML references:
#   static/app.min.js     (from static/app.js)
#   static/styles.min.css (from static/styles.css)
#
# Run this:
#   - After editing static/app.js or static/styles.css
#   - As part of any deploy pipeline before pushing static/ to prod
#   - In CI to verify the minified bundles match the sources
#
# Uses esbuild via npx so no global install is required. esbuild
# bundle size is ~20 MB on first npx fetch then cached.
#
# Minification flags:
#   --minify-whitespace : collapse runs of whitespace
#   --minify-syntax     : shorter equivalent syntax (e.g. true → !0)
# We deliberately DO NOT pass --minify-identifiers because tests and
# operator log-greps grep the served bundle for identifier names
# (e.g. _materialiseAppShellTemplate, history.replaceState). Keeping
# identifiers preserved still gives ~33% size reduction on app.js.

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: npx (Node.js) not on PATH. Install Node.js to run this script." >&2
  exit 1
fi

echo "==> Minifying static/app.js → static/app.min.js"
npx --yes esbuild static/app.js \
  --minify-whitespace --minify-syntax \
  --target=es2020 --legal-comments=none \
  --outfile=static/app.min.js

echo "==> Minifying static/styles.css → static/styles.min.css"
npx --yes esbuild static/styles.css \
  --minify \
  --loader:.css=css \
  --outfile=static/styles.min.css

echo
echo "==> Sizes"
ls -la static/app.js static/app.min.js static/styles.css static/styles.min.css 2>/dev/null \
  | awk '{ printf "  %10d  %s\n", $5, $9 }'

echo
echo "Build complete."
