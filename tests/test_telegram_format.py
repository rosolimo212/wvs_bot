from __future__ import annotations

from ui.telegram_format import markdown_bold_to_telegram_html


def test_markdown_bold_to_telegram_html() -> None:
    assert markdown_bold_to_telegram_html("**HKG** (RV 1)") == "<b>HKG</b> (RV 1)"


def test_markdown_bold_escapes_html() -> None:
    assert markdown_bold_to_telegram_html("a < b & **c**") == "a &lt; b &amp; <b>c</b>"
