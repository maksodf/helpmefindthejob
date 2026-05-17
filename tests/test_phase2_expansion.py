# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 2a — CV → query expansion prompt + parser."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.ai_providers import AIProviderConfig
from company_discovery.analysis import (
    build_cv_query_expansion_prompt,
    parse_query_expansion_output,
)
from company_discovery.models import UserProfile


class BuildExpansionPromptTests(unittest.TestCase):
    def test_inlines_free_text_and_persona(self) -> None:
        profile = UserProfile(
            user_id="u1",
            persona_id="healthcare-management",
            cv_text="20 years of healthcare-policy consulting in DACH.",
        )
        provider = AIProviderConfig(provider_id="openai", invocation_mode="api")
        result = build_cv_query_expansion_prompt(profile, "I want PPH-style work in Berlin", provider)
        prompt = result["prompt"]
        self.assertIn("Healthcare management", prompt)
        self.assertIn("PPH-style work in Berlin", prompt)
        # Must list persona enum so the LLM can pick from a valid set.
        self.assertIn("healthcare-management", prompt)
        self.assertIn("tech", prompt)
        self.assertIn("finance", prompt)


class ParseExpansionOutputTests(unittest.TestCase):
    def test_clean_json(self) -> None:
        out = parse_query_expansion_output(
            '{"persona_id":"healthcare-management","target_roles":["policy consultant"],'
            '"industry":"Healthcare consulting","location":"Berlin","keywords":["health policy"],"language":"en"}'
        )
        assert out is not None
        self.assertEqual(out["persona_id"], "healthcare-management")
        self.assertEqual(out["industry"], "Healthcare consulting")
        self.assertIn("health policy", out["keywords"])
        self.assertEqual(out["language"], "en")

    def test_fenced_json(self) -> None:
        body = """Sure, here's the JSON:

```json
{
  "persona_id": "tech",
  "target_roles": ["backend engineer"],
  "industry": "Technology",
  "location": "Munich",
  "keywords": ["python", "postgres"],
  "language": "de"
}
```
"""
        out = parse_query_expansion_output(body)
        assert out is not None
        self.assertEqual(out["persona_id"], "tech")
        self.assertEqual(out["language"], "de")

    def test_handles_arrays_and_truncation(self) -> None:
        out = parse_query_expansion_output(
            '{"target_roles":[' + ",".join(['"r' + str(i) + '"' for i in range(20)]) + ']}'
        )
        assert out is not None
        # Capped at 8 to keep prompt size sane downstream.
        self.assertLessEqual(len(out["target_roles"]), 8)

    def test_garbage_returns_none(self) -> None:
        self.assertIsNone(parse_query_expansion_output(""))
        self.assertIsNone(parse_query_expansion_output("the model rambled but produced no JSON at all"))

    def test_unsupported_language_blanked(self) -> None:
        out = parse_query_expansion_output(
            '{"target_roles":["x"],"language":"klingon"}'
        )
        assert out is not None
        self.assertIsNone(out["language"])


if __name__ == "__main__":
    unittest.main()
