"""Tests for the comment-body tag regular expression."""

import pytest

from todo_scan.tag_pattern import build_tag_search_pattern


def test_build_tag_search_pattern_rejects_an_empty_tag_set() -> None:
    """An empty set would compile a pattern that matches every comment."""

    with pytest.raises(ValueError, match="at least one tag"):
        build_tag_search_pattern(frozenset())


def test_tag_pattern_does_not_match_a_tag_used_as_a_prefix() -> None:
    """``TODO`` should not match inside ``TODOS``; word boundaries exist for this."""

    pattern = build_tag_search_pattern(frozenset({"TODO"}))
    assert pattern.search("TODOS are not reminders") is None


def test_tag_pattern_accepts_an_optional_colon_and_captures_the_message() -> None:
    """Both ``TODO fix`` and ``TODO: fix`` are conventional writings of a reminder."""

    pattern = build_tag_search_pattern(frozenset({"TODO"}))
    with_colon = pattern.search("TODO: tighten bounds")
    without_colon = pattern.search("TODO tighten bounds")
    assert with_colon is not None and with_colon.group(2) == "tighten bounds"
    assert without_colon is not None and without_colon.group(2) == "tighten bounds"
