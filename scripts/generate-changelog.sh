#!/usr/bin/env sh
# generate-changelog.sh — regenerate static/changelog.html from git history.
#
# Groups commits by APP_VERSION boundaries when commit messages contain
# "vX.Y.Z" / "version bump"; otherwise dumps the last 50 commits as one
# section. Output overwrites static/changelog.html.
#
# Usage:
#   ./scripts/generate-changelog.sh                     # writes to static/changelog.html
#   ./scripts/generate-changelog.sh --dry-run           # prints to stdout
#
# Run after each version bump. The static handler resolves /changelog →
# static/changelog.html via the standard .html fallback.

set -eu

OUT="static/changelog.html"
DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "generate-changelog: not inside a git repo" >&2
  exit 1
fi

APP_VERSION=$(grep -E '^APP_VERSION = ' app.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
TODAY=$(date -u +%Y-%m-%d)

write_header() {
  cat <<HEADER
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="index,follow" />
    <title>Changelog — DirectJob Scout</title>
    <meta name="description" content="What we shipped on DirectJob Scout (khalo.org). Real cadence, no marketing spin." />
    <link rel="canonical" href="https://khalo.org/changelog" />
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body class="legal-body">
    <main class="legal-page">
      <header>
        <a href="/" class="legal-back">← Back to DirectJob Scout</a>
        <h1>Changelog</h1>
        <p class="muted">What we actually shipped. App version ${APP_VERSION}. Regenerated ${TODAY}.</p>
      </header>

      <section>
        <h2>${APP_VERSION} — Recent commits</h2>
        <ul>
HEADER
}

write_footer() {
  cat <<FOOTER
        </ul>
      </section>

      <p class="muted small">Older history: <code>git log --pretty=format:'%ad %s' --date=short</code> in the repo.</p>

      <p class="legal-footer">
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
        <a href="/data-retention">Data retention</a>
        <a href="/impressum">Impressum</a>
      </p>
    </main>
  </body>
</html>
FOOTER
}

write_entries() {
  git log --pretty=format:'%ad|%s' --date=short -50 | while IFS='|' read -r d s; do
    case "$s" in
      *bump*|*[Vv]ersion*) continue ;;
    esac
    safe=$(printf '%s' "$s" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g')
    printf '          <li><strong>%s</strong> · %s</li>\n' "$d" "$safe"
  done
}

if [ "$DRY_RUN" = "1" ]; then
  write_header
  write_entries
  write_footer
else
  {
    write_header
    write_entries
    write_footer
  } >"$OUT"
  echo "generate-changelog: wrote $OUT (app version $APP_VERSION)"
fi
