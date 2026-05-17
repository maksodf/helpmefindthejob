"""R23.7 — chatRenderInline markdown safety.

Pure-text harness for the regex set in static/app.js#chatRenderInline.
Mirrors the JS replacements in Python so we can prove:

  * **bold** + `code` still work (no regression).
  * _italic_ renders for fallback notes.
  * [text](https://safe) and [text](#anchor) render as anchors.
  * [text](javascript:alert(1)) DROPS the href — XSS guard.
  * [text](data:...) DROPS the href.

If we ever port chatRenderInline to a different engine, this test
pins the safety contract.
"""

from __future__ import annotations

import re
import unittest


# Mirror of the JS regex set. Keep in lock-step with app.js.

def chat_render_inline(text: str) -> str:
    if text is None:
        return ""
    # HTML-entity escape via minimal substitution (the JS uses
    # textContent for the same effect).
    html = (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    html = re.sub(
        r"(^|[\s(>])_((?:[^_\n]|_(?=\w))+?)_(?=[\s).,;:!?<]|$)",
        r"\1<em>\2</em>",
        html,
    )

    def _link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        if re.match(r"^https?://", href, flags=re.IGNORECASE):
            return (f'<a href="{href.replace(chr(34), "&quot;")}" '
                    f'target="_blank" rel="noopener noreferrer">{label}</a>')
        if href.startswith("#"):
            return (f'<a href="{href.replace(chr(34), "&quot;")}" '
                    f'data-chat-link>{label}</a>')
        return label

    html = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, html)
    return html


class MarkdownRenderingTests(unittest.TestCase):
    def test_bold_renders(self):
        self.assertEqual(
            chat_render_inline("hello **world**"),
            "hello <strong>world</strong>")

    def test_code_renders(self):
        self.assertEqual(
            chat_render_inline("try `find_jobs`"),
            "try <code>find_jobs</code>")

    def test_italic_in_fallback_note_renders(self):
        out = chat_render_inline(
            "_(AI is taking a break — running the simple chat.)_")
        self.assertIn("<em>", out)
        self.assertIn("</em>", out)

    def test_italic_does_not_swallow_variable_names(self):
        # snake_case_var should NOT render as italic.
        out = chat_render_inline("Set the my_var_name to true")
        self.assertNotIn("<em>", out,
                          f"snake_case rendered as italic: {out!r}")

    def test_https_link_renders_with_safe_target(self):
        out = chat_render_inline(
            "Read [the docs](https://app.khalo.org/docs)")
        self.assertIn('href="https://app.khalo.org/docs"', out)
        self.assertIn('target="_blank"', out)
        self.assertIn('rel="noopener noreferrer"', out)

    def test_anchor_link_uses_chat_link_attr(self):
        out = chat_render_inline("[upgrade](#billing)")
        self.assertIn("data-chat-link", out)
        self.assertIn('href="#billing"', out)

    def test_javascript_protocol_dropped_xss_guard(self):
        out = chat_render_inline("[click me](javascript:alert(1))")
        self.assertNotIn("javascript:", out,
                          "XSS: javascript: protocol leaked through")
        self.assertNotIn("<a ", out)
        self.assertIn("click me", out)  # text preserved

    def test_data_protocol_dropped_xss_guard(self):
        out = chat_render_inline("[svg](data:image/svg+xml;base64,...)")
        self.assertNotIn("data:", out)
        self.assertNotIn("<a ", out)
        self.assertIn("svg", out)

    def test_file_protocol_dropped(self):
        out = chat_render_inline("[open](file:///etc/passwd)")
        self.assertNotIn("file:", out)
        self.assertNotIn("<a ", out)

    def test_link_text_html_entities_escaped(self):
        out = chat_render_inline("[<script>](https://x.com)")
        self.assertNotIn("<script>", out,
                          "label HTML was not escaped")

    def test_combined_markdown_in_fallback_note(self):
        """The actual R23.7 quota-exceeded note."""
        note = ("_(You've used today's AI chats. Running the simple "
                "chat for the rest of the day — or "
                "[upgrade for more](#billing).)_")
        out = chat_render_inline(note)
        self.assertIn("<em>", out)
        self.assertIn("</em>", out)
        self.assertIn("data-chat-link", out)
        self.assertIn("upgrade for more", out)


if __name__ == "__main__":
    unittest.main()
