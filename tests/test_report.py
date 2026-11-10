"""Tests for the text, JSON, and Markdown report formatters."""

import json
from pathlib import Path

from todo_scan.report import format_json_report, format_markdown_report, format_text_report
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
