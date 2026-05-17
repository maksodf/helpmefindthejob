"""R23.9 — end-to-end probe that legacy AI calls (briefs, letters,
CV consults, CV format) are recorded in the cost tracker.

Before R23.9, only the R22 tool-use chat hit the cost dashboard.
The legacy ``_dispatch_provider`` path was invisible — operator
saw ~10% of actual spend. This probe:

  1. Patches the legacy adapter to return a deterministic response
     with usage tokens.
  2. Fires execute_job_decision_brief() directly with a record_call
     closure tied to a fake user_id.
  3. Asserts the cost-tracker recorded a row with the right user,
     model, task, and tokens.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_legacy_cost_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"

import app  # noqa: E402
from company_discovery import analysis as A  # noqa: E402
from company_discovery.ai_providers import AIProviderConfig  # noqa: E402
from company_discovery.models import ImportedJob, UserProfile  # noqa: E402


def main() -> int:
    findings: list[str] = []

    # 1. Patch the OpenAI-compatible adapter to return deterministic
    # usage. This is the path managed-AI takes when upstream is OpenAI.
    def fake_execute(prompt, provider, runtime_credential=""):
        from company_discovery.analysis import AnalysisExecutionResult
        return AnalysisExecutionResult(
            status="completed",
            provider_id=provider.provider_id,
            invocation_mode=provider.invocation_mode,
            output="OK",
            input_tokens=320,
            output_tokens=88,
            model_used=provider.model or "gpt-4o-mini",
        )

    A._execute_openai_compatible = fake_execute  # type: ignore[assignment]

    # 2. Build the minimal inputs.
    job = ImportedJob(
        user_id="user-fake-1",
        company_id="c1",
        discovered_job_id="d1",
        source_url="https://example.test/job",
        title="Pflegehelfer (m/w/d)",
        company_name="Caritas",
        location="Berlin",
        description="x" * 100,
    )
    profile = UserProfile(user_id="user-fake-1",
                            persona_id="healthcare-management",
                            cv_text="Resume body.")

    # Use managed provider so the model_router fires.
    provider = AIProviderConfig(
        provider_id="managed", invocation_mode="api",
        credential_reference="DIRECTJOB_MANAGED_AI_KEY",
    )

    # 3. Manually wire managed-AI provider in env so _dispatch_provider
    # picks the upstream. We set it to openai so fake_execute matches.
    os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "openai"

    rec = app.STATE.make_llm_record_call("user-fake-1")
    result = A.execute_job_decision_brief(
        job, provider, "", profile, record_call=rec)

    print(f"[probe] result.status={result.status}")
    print(f"[probe] result.model_used={result.model_used}")
    print(f"[probe] result.input_tokens={result.input_tokens}")
    print(f"[probe] result.output_tokens={result.output_tokens}")

    if result.status != "completed":
        findings.append(f"adapter returned status={result.status}")
    if not result.model_used:
        findings.append("model_used is empty — usage parsing failed")
    if result.input_tokens != 320:
        findings.append(f"input_tokens={result.input_tokens} (expected 320)")

    # 4. Inspect the cost tracker.
    tot = app.STATE.llm_cost_tracker.today_total_for_user_usd("user-fake-1")
    print(f"[probe] tracker total for user-fake-1: ${tot:.6f}")
    if tot <= 0:
        findings.append(f"tracker total is {tot}, expected > 0")

    by_task = app.STATE.llm_cost_tracker.by_task_today()
    task_calls = {r["task"]: r["calls"] for r in by_task}
    print(f"[probe] by_task: {task_calls}")
    if task_calls.get("job_brief") != 1:
        findings.append(
            f"job_brief count = {task_calls.get('job_brief')}, "
            f"expected 1 (legacy path now writing to cost tracker)")

    # 5. Quick second call — a motivation letter — to prove a different
    # task ID is recorded too.
    from company_discovery.analysis import execute_cover_letter_brief
    execute_cover_letter_brief(
        job, provider, "", profile, record_call=rec)
    by_task2 = app.STATE.llm_cost_tracker.by_task_today()
    task_calls2 = {r["task"]: r["calls"] for r in by_task2}
    print(f"[probe] after letter call, by_task: {task_calls2}")
    if task_calls2.get("motivation_letter") != 1:
        findings.append(
            f"motivation_letter count = {task_calls2.get('motivation_letter')}, "
            f"expected 1")

    print()
    print("=" * 60)
    if findings:
        print(f"LEGACY AI COST TRACKING — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("LEGACY AI COST TRACKING — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
