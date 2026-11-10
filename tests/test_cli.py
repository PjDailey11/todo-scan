"""Tests for CLI argument handling and the process entry point."""

from pathlib import Path

from todo_scan.cli import collect_recognized_tags, main
from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS


def test_collect_recognized_tags_splits_comma_lists_and_repeats() -> None:
    """Users should be able to write ``--tag A,B`` or two ``--tag`` flags."""

    assert collect_recognized_tags(["todo, fixme", "HACK"]) == {"TODO", "FIXME", "HACK"}
    assert collect_recognized_tags(None) == DEFAULT_RECOGNIZED_TAGS


def test_main_writes_a_text_report_and_returns_zero(tmp_path: Path, capsys) -> None:
    """A successful scan is a reporter, so findings still exit with status 0."""

    source_file = tmp_path / "app.py"
    source_file.write_text("# TODO: tighten later\n", encoding="utf-8")

    exit_status = main([str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_status == 0
    assert captured.out == "app.py:1: TODO tighten later\n"
    assert captured.err == ""


def test_main_returns_usage_status_for_a_missing_path() -> None:
    """A bad path should be a usage error, not a traceback."""

    assert main(["/this/path/does/not/exist"]) == 2


def test_main_writes_json_to_an_output_file(tmp_path: Path) -> None:
    """``--output`` should land a JSON report on disk without printing it."""

    source_file = tmp_path / "app.py"
    source_file.write_text("# FIXME handle this\n", encoding="utf-8")
    report_path = tmp_path / "report.json"

    exit_status = main(
        [str(tmp_path), "--format", "json", "--output", str(report_path), "--tag", "FIXME"]
    )

    assert exit_status == 0
    report_text = report_path.read_text(encoding="utf-8")
    assert '"tag": "FIXME"' in report_text
    assert '"message": "handle this"' in report_text
