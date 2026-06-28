from __future__ import annotations

from core.analytics.index_interpretation import (
    describe_rv_score,
    describe_sv_score,
    format_indices_summary,
    format_rv_peer_comparison,
    format_sv_peer_comparison,
)


def test_describe_rv_traditional() -> None:
    assert "авторитет" in describe_rv_score(10)


def test_describe_rv_balance() -> None:
    assert "баланс" in describe_rv_score(14)


def test_describe_rv_secular() -> None:
    assert "научные" in describe_rv_score(17)


def test_describe_sv_survival() -> None:
    assert "безопасность" in describe_sv_score(8)


def test_describe_sv_self_expression() -> None:
    assert "самореализация" in describe_sv_score(15)


def test_format_indices_summary_includes_scores() -> None:
    text = format_indices_summary(12, 11)
    assert "12" in text
    assert "11" in text
    assert "традиционных/секулярно-рациональных" in text


def test_format_sv_peer_comparison_self_expression() -> None:
    text = format_sv_peer_comparison(15, 60, "Россия", peers_label="сверстников")
    assert "самовыражения" in text
    assert "60%" in text
    assert "сверстников" in text


def test_sv_comparison_percent_branches() -> None:
    from core.analytics.index_interpretation import rv_comparison_percent, sv_comparison_percent

    assert sv_comparison_percent(8, 20) == 80
    assert sv_comparison_percent(15, 60) == 60
    assert rv_comparison_percent(11, 20) == 80
    assert rv_comparison_percent(18, 55) == 55


def test_format_rv_peer_comparison_traditional() -> None:
    text = format_rv_peer_comparison(11, 20, "Россия")
    assert "традиционные" in text
    assert "80%" in text
