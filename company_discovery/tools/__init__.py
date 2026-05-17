"""Tools subpackage.

Each module here defines one chat-callable tool using the
portfolio-standard ``tool_registry``. Importing this package triggers
registration via side effect — so every importer who wants the
registry populated must do:

    import company_discovery.tools  # noqa: F401

at startup. The lazy-load helper ``tool_registry._ensure_loaded``
does this on the first access from inside the registry's public API.

Migration tracker
=================

All 13 LLM-exposed legacy commands are migrated:

  add_company             (Tier I)
  create_saved_search     (Tier I)
  delete_account          (Tier N)
  delete_company          (Tier N)
  download_cv             (Tier R)
  draft_motivation_letter (Tier R)
  find_jobs               (Tier R)
  mark_applied            (Tier I)
  open_cv_builder         (Tier R)
  run_saved_search        (Tier R)
  set_persona             (Tier I)
  suggest_cv_enhancements (Tier R)
  tailor_cv               (Tier R)
  update_profile          (Tier I)

Not migrated (kept in ``_TOOLS_TO_EXCLUDE`` because they are never
exposed to the LLM as tools — journey state-machine internals or
features the LLM already covers via the system prompt):

  start_job_journey, accept_cv_text, build_cv_via_chat, help, show_view
"""

# Import order is alphabetical to make additions easy to review.
from company_discovery.tools import add_company  # noqa: F401
from company_discovery.tools import create_saved_search  # noqa: F401
from company_discovery.tools import delete_account  # noqa: F401
from company_discovery.tools import delete_company  # noqa: F401
from company_discovery.tools import delete_saved_search  # noqa: F401
from company_discovery.tools import discover_companies  # noqa: F401
from company_discovery.tools import download_cv  # noqa: F401
from company_discovery.tools import draft_motivation_letter  # noqa: F401
from company_discovery.tools import find_jobs  # noqa: F401
from company_discovery.tools import get_account_status  # noqa: F401
from company_discovery.tools import get_billing_status  # noqa: F401
from company_discovery.tools import get_referral_info  # noqa: F401
from company_discovery.tools import mark_applied  # noqa: F401
from company_discovery.tools import open_cv_builder  # noqa: F401
from company_discovery.tools import request_data_export  # noqa: F401
from company_discovery.tools import run_saved_search  # noqa: F401
from company_discovery.tools import set_persona  # noqa: F401
from company_discovery.tools import set_slack_webhook  # noqa: F401
from company_discovery.tools import suggest_cv_enhancements  # noqa: F401
from company_discovery.tools import tailor_cv  # noqa: F401
from company_discovery.tools import test_slack_webhook  # noqa: F401
from company_discovery.tools import undo_last_action  # noqa: F401
from company_discovery.tools import update_company  # noqa: F401
from company_discovery.tools import update_profile  # noqa: F401
from company_discovery.tools import update_saved_search  # noqa: F401
