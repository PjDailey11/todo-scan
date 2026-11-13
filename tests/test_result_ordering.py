"""Tests for reordering scan results with sort_tagged_comments."""

from pathlib import Path

import pytest

from todo_scan.result_ordering import SORT_ORDERS, sort_tagged_comments
from todo_scan.tagged_comment import TaggedComment


def _comment(path: str, line: int, tag: str) -> TaggedComment:
    """Build a minimal record; message and style do not affect ordering."""

    return TaggedComment(Path(path), line, tag, f"{tag.lower()} at {line}", "hash")


# b.py has three matches and a.py one, so "count" and "file" disagree on order.
SAMPLE_COMMENTS = [
    _comment("b.py", 9, "TODO"),
    _comment("a.py", 4, "TODO"),
    _comment("b.py", 2, "FIXME"),
    _comment("b.py", 5, "NOTE"),
]


def _locations(comments: list[TaggedComment]) -> list[tuple[str, int]]:
    return [(comment.source_path.as_posix(), comment.line_number) for comment in comments]


def test_file_order_sorts_by_path_then_line() -> None:
    assert _locations(sort_tagged_comments(SAMPLE_COMMENTS, "file")) == [
        ("a.py", 4),
        ("b.py", 2),
        ("b.py", 5),
        ("b.py", 9),
    ]


def test_tag_order_groups_tags_alphabetically_then_by_location() -> None:
    ordered = sort_tagged_comments(SAMPLE_COMMENTS, "tag")
    assert [comment.tag for comment in ordered] == ["FIXME", "NOTE", "TODO", "TODO"]
    assert _locations(ordered)[2:] == [("a.py", 4), ("b.py", 9)]


def test_count_order_puts_busiest_file_first_and_keeps_line_order() -> None:
    assert _locations(sort_tagged_comments(SAMPLE_COMMENTS, "count")) == [
        ("b.py", 2),
        ("b.py", 5),
        ("b.py", 9),
        ("a.py", 4),
    ]


def test_count_order_breaks_ties_by_path() -> None:
    tied_comments = [_comment("z.py", 1, "TODO"), _comment("m.py", 1, "TODO")]
    assert _locations(sort_tagged_comments(tied_comments, "count")) == [
        ("m.py", 1),
        ("z.py", 1),
    ]


def test_sorting_returns_a_new_list_and_leaves_input_untouched() -> None:
    original_order = list(SAMPLE_COMMENTS)
    for sort_order in SORT_ORDERS:
        assert sort_tagged_comments(SAMPLE_COMMENTS, sort_order) is not SAMPLE_COMMENTS
    assert SAMPLE_COMMENTS == original_order


def test_empty_input_and_unknown_order() -> None:
    assert sort_tagged_comments([], "count") == []
    with pytest.raises(ValueError, match="unsupported sort order"):
        sort_tagged_comments(SAMPLE_COMMENTS, "severity")
