"""Tests for the comment-style registry and its human-readable listing."""

from todo_scan.comment_styles import (
    _SUFFIX_TO_COMMENT_STYLE,
    comment_style_for_suffix,
    format_comment_style_listing,
)


def test_listing_has_one_row_per_registered_suffix() -> None:
    """Every suffix the scanner knows must appear exactly once in the listing."""

    listing_rows = format_comment_style_listing().splitlines()
    listed_suffixes = [row.split()[0] for row in listing_rows]

    assert sorted(listed_suffixes) == sorted(_SUFFIX_TO_COMMENT_STYLE)
    assert len(listed_suffixes) == len(set(listed_suffixes))


def test_listing_rows_agree_with_comment_style_for_suffix() -> None:
    """The listing must show the same style the scanner would pick."""

    for row in format_comment_style_listing().splitlines():
        suffix, style_name = row.split()[:2]
        assert comment_style_for_suffix(suffix).style_name == style_name


def test_listing_is_sorted_case_insensitively_and_ends_with_newline() -> None:
    """Stable, case-folded order keeps ``.R`` and ``.r`` adjacent and diffs small."""

    listing_text = format_comment_style_listing()
    listed_suffixes = [row.split()[0] for row in listing_text.splitlines()]

    assert listing_text.endswith("\n")
    assert listed_suffixes == sorted(
        listed_suffixes, key=lambda suffix: (suffix.lower(), suffix)
    )
    assert abs(listed_suffixes.index(".R") - listed_suffixes.index(".r")) == 1


def test_listing_describes_line_and_block_delimiters() -> None:
    """Both delimiter kinds are shown, quoted so ``--`` and ``;`` are unambiguous."""

    rows_by_suffix = {
        row.split()[0]: row for row in format_comment_style_listing().splitlines()
    }

    assert rows_by_suffix[".c"].endswith("line '//', block '/*' ... '*/'")
    assert rows_by_suffix[".html"].endswith("block '<!--' ... '-->'")
    assert rows_by_suffix[".sql"].endswith("line '--'")
    assert rows_by_suffix[".hs"].endswith("line '--', block '{-' ... '-}'")
