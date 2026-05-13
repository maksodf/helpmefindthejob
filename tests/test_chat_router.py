"""Chat-router unit tests.

Cover the deterministic surfaces the chat depends on — slash parsing,
keyword routing, AI-response parsing, validators, confirmation
detection — so the hard-to-test end-to-end flow has a solid base."""

from __future__ import annotations

import unittest

from company_discovery.chat_router import (
    REGISTRY,
    _validate_application_status,
    _validate_bool,
    _validate_list_csv,
    _validate_string,
    _validate_url,
    is_confirmation_no,
    is_confirmation_yes,
    keyword_route,
    list_commands,
    parse_ai_router_response,
    parse_slash_command,
    parse_slash_inline_args,
    render_help_text,
)


class RegistryShapeTests(unittest.TestCase):
    def test_eighteen_core_commands(self):
        names = set(REGISTRY)
        self.assertEqual(
            names,
            {"add_company", "create_saved_search", "find_jobs",
             "update_profile", "mark_applied",
             "tailor_cv", "run_saved_search", "set_persona",
             "delete_company", "open_cv_builder",
             "start_job_journey", "accept_cv_text", "build_cv_via_chat",
             "draft_motivation_letter", "suggest_cv_enhancements",
             "show_view", "delete_account",
             "help"},
        )

    def test_every_command_has_label_and_description(self):
        for cmd in REGISTRY.values():
            self.assertTrue(cmd.label.strip())
            self.assertTrue(cmd.description.strip())

    def test_every_command_has_at_least_one_slash_alias(self):
        for cmd in REGISTRY.values():
            self.assertTrue(cmd.slash_aliases,
                              f"{cmd.name} has no slash aliases")

    def test_list_commands_payload_shape(self):
        payload = list_commands()
        self.assertEqual(len(payload), 18)
        for item in payload:
            self.assertIn("name", item)
            self.assertIn("label", item)
            self.assertIn("description", item)
            self.assertIn("slashAliases", item)
            self.assertIn("params", item)


class SlashCommandTests(unittest.TestCase):
    def test_add_company_alias(self):
        result = parse_slash_command("/add-company Charité https://x.com")
        self.assertEqual(result[0], "add_company")
        self.assertEqual(result[1], "Charité https://x.com")

    def test_short_add_alias(self):
        result = parse_slash_command("/add Acme")
        self.assertEqual(result[0], "add_company")

    def test_find_alias(self):
        result = parse_slash_command("/find Senior Backend Berlin")
        self.assertEqual(result[0], "find_jobs")

    def test_help_alias(self):
        result = parse_slash_command("/help")
        self.assertEqual(result[0], "help")

    def test_no_match(self):
        self.assertIsNone(parse_slash_command("/unknown-command"))

    def test_non_slash_message_returns_none(self):
        self.assertIsNone(parse_slash_command("just chatting"))


class V2CommandRoutingTests(unittest.TestCase):
    """Round-13 commands: tailor_cv, run_saved_search, set_persona,
    delete_company."""

    def test_tailor_alias(self):
        result = parse_slash_command("/tailor job_abc123")
        self.assertEqual(result[0], "tailor_cv")
        self.assertEqual(result[1], "job_abc123")

    def test_tailor_keyword(self):
        self.assertEqual(keyword_route("tailor my CV for this role"),
                          "tailor_cv")
        self.assertEqual(keyword_route("rewrite my resume"),
                          "tailor_cv")

    def test_run_search_alias(self):
        result = parse_slash_command("/run-search search_xyz")
        self.assertEqual(result[0], "run_saved_search")

    def test_run_search_keyword(self):
        self.assertEqual(keyword_route("run my saved search"),
                          "run_saved_search")

    def test_set_persona_alias(self):
        result = parse_slash_command("/persona tech")
        self.assertEqual(result[0], "set_persona")
        self.assertEqual(result[1], "tech")

    def test_set_persona_keyword(self):
        self.assertEqual(keyword_route("change my persona"),
                          "set_persona")
        self.assertEqual(keyword_route("set my persona"),
                          "set_persona")

    def test_delete_company_alias(self):
        result = parse_slash_command("/unwatch company_abc")
        self.assertEqual(result[0], "delete_company")

    def test_delete_company_keyword(self):
        self.assertEqual(keyword_route("stop watching"),
                          "delete_company")
        self.assertEqual(keyword_route("remove a company"),
                          "delete_company")


class SlashInlineArgsTests(unittest.TestCase):
    def test_two_positional_args(self):
        args = parse_slash_inline_args(
            "add_company", "Charité https://charite.de")
        self.assertEqual(args["name"], "Charité")
        self.assertEqual(args["websiteUrl"], "https://charite.de")

    def test_quoted_arg_preserves_spaces(self):
        args = parse_slash_inline_args(
            "add_company", '"Acme Corp Berlin" https://acme.example')
        self.assertEqual(args["name"], "Acme Corp Berlin")
        self.assertEqual(args["websiteUrl"], "https://acme.example")

    def test_no_rest_returns_empty(self):
        self.assertEqual(parse_slash_inline_args("add_company", ""), {})

    def test_optional_param_filled_when_provided(self):
        args = parse_slash_inline_args(
            "add_company", "Acme https://x.example https://x.example/careers")
        self.assertEqual(args.get("careerPageUrl"),
                          "https://x.example/careers")


class KeywordRouteTests(unittest.TestCase):
    def test_add_company_intent(self):
        self.assertEqual(keyword_route("I want to add a company"),
                          "add_company")
        self.assertEqual(keyword_route("can you watch a company for me"),
                          "add_company")

    def test_find_jobs_intent(self):
        self.assertEqual(keyword_route("find me jobs in Berlin"),
                          "find_jobs")
        self.assertEqual(keyword_route("search for senior roles"),
                          "find_jobs")

    def test_help_intent(self):
        self.assertEqual(keyword_route("help"), "help")
        self.assertEqual(keyword_route("what can you do?"), "help")

    def test_unrelated_text_returns_none(self):
        self.assertIsNone(keyword_route("hello there friend"))


class AIRouterResponseTests(unittest.TestCase):
    def test_clean_response(self):
        self.assertEqual(parse_ai_router_response("add_company"),
                          "add_company")

    def test_quoted_response(self):
        self.assertEqual(parse_ai_router_response("`add_company`"),
                          "add_company")
        self.assertEqual(parse_ai_router_response("'add_company'"),
                          "add_company")

    def test_first_token_only(self):
        # AI returns trailing prose — first token wins.
        self.assertEqual(parse_ai_router_response("add_company because the user wants to watch a company"),
                          "add_company")

    def test_unknown_response(self):
        self.assertIsNone(parse_ai_router_response("unknown"))
        self.assertIsNone(parse_ai_router_response("nonsense_command"))
        self.assertIsNone(parse_ai_router_response(""))

    def test_json_command_only(self):
        self.assertEqual(parse_ai_router_response(
            '{"command": "find_jobs"}'), "find_jobs")

    def test_json_with_args(self):
        self.assertEqual(parse_ai_router_response(
            '{"command": "add_company", "args": {"name": "Acme"}}'),
            "add_company")

    def test_json_unknown_command(self):
        self.assertIsNone(parse_ai_router_response(
            '{"command": "do_anything"}'))

    def test_json_malformed_falls_back_to_first_token(self):
        # Truncated JSON; the regex grabs nothing usable. First-token
        # path also fails because there's no bare command id. → None.
        self.assertIsNone(parse_ai_router_response(
            '{"command":'))


class AIRouterArgExtractionTests(unittest.TestCase):
    def test_extracts_string_args(self):
        from company_discovery.chat_router import parse_ai_router_extracted_args
        out = parse_ai_router_extracted_args(
            '{"command": "add_company", "args": '
            '{"name": "Acme Corp", "websiteUrl": "https://acme.example"}}'
        )
        self.assertEqual(out, {
            "name": "Acme Corp",
            "websiteUrl": "https://acme.example",
        })

    def test_no_args_returns_empty_dict(self):
        from company_discovery.chat_router import parse_ai_router_extracted_args
        self.assertEqual(
            parse_ai_router_extracted_args('{"command": "find_jobs"}'),
            {},
        )

    def test_legacy_bare_name_returns_empty(self):
        from company_discovery.chat_router import parse_ai_router_extracted_args
        self.assertEqual(parse_ai_router_extracted_args("find_jobs"), {})

    def test_null_arg_values_filtered_out(self):
        from company_discovery.chat_router import parse_ai_router_extracted_args
        out = parse_ai_router_extracted_args(
            '{"command": "add_company", "args": '
            '{"name": "X", "careerPageUrl": null}}'
        )
        self.assertEqual(out, {"name": "X"})

    def test_malformed_json_returns_empty(self):
        from company_discovery.chat_router import parse_ai_router_extracted_args
        self.assertEqual(parse_ai_router_extracted_args(
            '{"command": "add_company", "args": {NOT VALID JSON}'),
            {})


class ValidatorTests(unittest.TestCase):
    def test_url_validator_strict(self):
        ok, val = _validate_url("https://acme.example")
        self.assertTrue(ok)
        self.assertEqual(val, "https://acme.example")

    def test_url_validator_auto_https(self):
        ok, val = _validate_url("acme.example")
        self.assertTrue(ok)
        self.assertEqual(val, "https://acme.example")

    def test_url_validator_rejects_garbage(self):
        ok, _ = _validate_url("not a url at all")
        self.assertFalse(ok)

    def test_string_validator_strips_whitespace(self):
        ok, val = _validate_string("  hello  ")
        self.assertTrue(ok)
        self.assertEqual(val, "hello")

    def test_string_validator_rejects_empty(self):
        ok, _ = _validate_string("")
        self.assertFalse(ok)
        ok, _ = _validate_string("   ")
        self.assertFalse(ok)

    def test_string_validator_rejects_oversize(self):
        ok, _ = _validate_string("x" * 6000)
        self.assertFalse(ok)

    def test_csv_validator_splits(self):
        ok, val = _validate_list_csv("python, postgres, kubernetes")
        self.assertTrue(ok)
        self.assertEqual(val, ["python", "postgres", "kubernetes"])

    def test_csv_validator_caps_at_50(self):
        ok, _ = _validate_list_csv(",".join(str(i) for i in range(60)))
        self.assertFalse(ok)

    def test_bool_validator_yes_words(self):
        for word in ["yes", "y", "true", "1", "ja", "on"]:
            ok, val = _validate_bool(word)
            self.assertTrue(ok, word)
            self.assertTrue(val)

    def test_bool_validator_no_words(self):
        for word in ["no", "n", "false", "0", "nein", "off"]:
            ok, val = _validate_bool(word)
            self.assertTrue(ok, word)
            self.assertFalse(val)

    def test_bool_validator_rejects_other(self):
        ok, _ = _validate_bool("maybe")
        self.assertFalse(ok)

    def test_application_status_validator(self):
        for valid in ["saved", "applied", "interview", "rejected", "archived"]:
            ok, _ = _validate_application_status(valid)
            self.assertTrue(ok, valid)
        ok, _ = _validate_application_status("yolo")
        self.assertFalse(ok)


class ConfirmationDetectionTests(unittest.TestCase):
    def test_yes_variants(self):
        for word in ["yes", "y", "ok", "confirm", "go", "ja", "proceed"]:
            self.assertTrue(is_confirmation_yes(word), word)

    def test_no_variants(self):
        for word in ["no", "n", "cancel", "abort", "nein"]:
            self.assertTrue(is_confirmation_no(word), word)

    def test_ambiguous_returns_neither(self):
        self.assertFalse(is_confirmation_yes("maybe"))
        self.assertFalse(is_confirmation_no("maybe"))


class HelpRenderTests(unittest.TestCase):
    def test_help_includes_every_command(self):
        text = render_help_text()
        for cmd in REGISTRY.values():
            self.assertIn(cmd.label, text)


if __name__ == "__main__":
    unittest.main()
