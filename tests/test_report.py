"""Tests for the text, JSON, and Markdown report formatters."""

import csv
import io
import json
from pathlib import Path

from todo_scan.report import (
    CSV_REPORT_COLUMNS,
    count_comments_by_tag,
    format_csv_report,
    format_json_report,
    format_markdown_report,
    format_tag_summary,
    format_text_report,
)
from todo_scan.tagged_comment import TaggedComment


def _sample_comments(project_root: Path) -> list[TaggedComment]:
    return [
        TaggedComment(
            source_path=project_root / "src" / "app.py",
            line_number=4,
            tag="TODO",
            message="tighten this later",
            comment_style="hash",
        ),
        TaggedComment(
            source_path=project_root / "src" / "app.py",
            line_number=9,
            tag="FIXME",
            message="",
            comment_style="hash",
        ),
    ]


def test_format_text_report_uses_grep_style_paths_relative_to_the_root(tmp_path: Path) -> None:
    """Editor-clickable ``path:line: TAG message`` lines should use a relative path."""

    report = format_text_report(_sample_comments(tmp_path), project_root=tmp_path)
    assert report == (
        "src/app.py:4: TODO tighten this later\n"
        "src/app.py:9: FIXME\n"
    )


def test_format_json_report_is_an_array_of_objects(tmp_path: Path) -> None:
    """Downstream tools should be able to parse an empty or non-empty array alike."""

    payload = json.loads(format_json_report(_sample_comments(tmp_path), project_root=tmp_path))
    assert payload[0]["path"] == "src/app.py"
    assert payload[0]["line"] == 4
    assert payload[0]["tag"] == "TODO"
    assert payload[0]["message"] == "tighten this later"
    assert payload[1]["message"] == ""
    assert json.loads(format_json_report([], project_root=tmp_path)) == []


def test_format_markdown_report_groups_matches_under_a_file_heading(tmp_path: Path) -> None:
    """A Markdown report is meant to be pasted into a ticket, so grouping matters."""

    report = format_markdown_report(_sample_comments(tmp_path), project_root=tmp_path)
    assert report.startswith("# Tagged comments\n")
    assert "## src/app.py" in report
    assert "- Line 4: `TODO` — tighten this later" in report
    assert "- Line 9: `FIXME`" in report
    assert format_markdown_report([]) == "No tagged comments found.\n"


def _comment_with_tag(tag: str, line_number: int) -> TaggedComment:
    """Build a minimal match; only the tag matters for the summary tests."""

    return TaggedComment(Path("app.py"), line_number, tag, "", "hash")


def test_count_comments_by_tag_orders_by_count_then_name() -> None:
    """Higher counts come first and ties break alphabetically for stable output."""

    tagged_comments = [
        _comment_with_tag("TODO", 1),
        _comment_with_tag("NOTE", 2),
        _comment_with_tag("TODO", 3),
        _comment_with_tag("FIXME", 4),
    ]

    counts_by_tag = count_comments_by_tag(tagged_comments)

    assert list(counts_by_tag.items()) == [("TODO", 2), ("FIXME", 1), ("NOTE", 1)]


def test_format_tag_summary_aligns_columns_and_adds_total() -> None:
    """Labels are padded to the widest label so counts line up."""

    summary_text = format_tag_summary(
        [_comment_with_tag("TODO", 1), _comment_with_tag("FIXME", 2)]
    )

    assert summary_text == "FIXME  1\nTODO   1\ntotal  2\n"


def test_format_tag_summary_reports_zero_for_an_empty_scan() -> None:
    """An empty scan still prints a total so it is distinguishable from a crash."""

    assert format_tag_summary([]) == "total  0\n"


def test_format_csv_report_writes_a_header_and_one_row_per_match(tmp_path: Path) -> None:
    """Rows keep input order and use the same relative paths as the text report."""

    report = format_csv_report(_sample_comments(tmp_path), project_root=tmp_path)

    assert report == (
        "path,line,tag,message,comment_style\r\n"
        "src/app.py,4,TODO,tighten this later,hash\r\n"
        "src/app.py,9,FIXME,,hash\r\n"
    )


def test_format_csv_report_keeps_the_header_for_an_empty_scan() -> None:
    """An empty scan is still a valid CSV document with the expected columns."""

    assert format_csv_report([]) == ",".join(CSV_REPORT_COLUMNS) + "\r\n"


def test_format_csv_report_quotes_commas_and_quotes_in_messages(tmp_path: Path) -> None:
    """Messages with delimiters must round-trip through ``csv.DictReader``."""

    tricky_message = 'handle "a, b" input'
    tricky_comment = TaggedComment(
        source_path=tmp_path / "parse.py",
        line_number=2,
        tag="TODO",
        message=tricky_message,
        comment_style="hash",
    )

    report = format_csv_report([tricky_comment], project_root=tmp_path)
    parsed_rows = list(csv.DictReader(io.StringIO(report, newline="")))

    assert '"handle ""a, b"" input"' in report
    assert parsed_rows == [
        {
            "path": "parse.py",
            "line": "2",
            "tag": "TODO",
            "message": tricky_message,
            "comment_style": "hash",
        }
    ]
