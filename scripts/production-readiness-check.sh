#!/usr/bin/env sh
# production-readiness-check.sh
#
# Print the production-readiness report for the current shell
# environment, without making any network calls. Useful before a
# deploy, in CI, or as a `--env-file` self-check.
#
# Usage:
#   ./scripts/production-readiness-check.sh
#   ENV_FILE=.env ./scripts/production-readiness-check.sh
#
# When ENV_FILE is set, the script sources it before invoking the
# Python builder. Sourcing happens in this shell only — secrets are
# never echoed; we only print the structured report.
#
# Exit codes:
#   0  overall status is "ok"
#   1  overall status is "partial" (one or more partial items, no missing items)
#   2  overall status is "missing"

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -n "${ENV_FILE:-}" ] && [ -f "$ENV_FILE" ]; then
  # Allow common ".env" formats: KEY=value, optional `export`, ignore
  # comments and blank lines. We never print the values.
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

cd "$ROOT"
python3 - "$@" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from company_discovery.readiness import build_report


# Read the version straight out of app.py to avoid importing it (which
# would attempt to bind a sqlite file under COMPANY_DISCOVERY_DATA_DIR).
app_text = Path("app.py").read_text(encoding="utf-8")
match = re.search(r'APP_VERSION = "([^"]+)"', app_text)
app_version = match.group(1) if match else "unknown"

env_name = (os.environ.get("COMPANY_DISCOVERY_ENV") or "development").strip().casefold()
data_dir_raw = os.environ.get("COMPANY_DISCOVERY_DATA_DIR") or str(Path("./data").resolve())
data_dir = Path(data_dir_raw)
audit_path = data_dir / "admin_audit.log"
scheduler_path = data_dir / "scheduler.sqlite3"

report = build_report(
    app_version=app_version,
    environment=env_name,
    data_dir=data_dir,
    audit_path=audit_path,
    scheduler_path=scheduler_path,
    active_scheduler_jobs=None,
)

print(json.dumps(report.to_dict(), indent=2))
print()
print(f"Overall: {report.overall_status.upper()} (env={report.environment}, version={report.app_version})")
for signal in report.signals:
    print(f"  [{signal.status:7s}] {signal.label} — {signal.summary}")

if report.overall_status == "ok":
    sys.exit(0)
if report.overall_status == "partial":
    sys.exit(1)
sys.exit(2)
PY
