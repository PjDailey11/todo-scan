"""Tests for CLI argument handling and the process entry point."""

import json
from pathlib import Path

import pytest

from todo_scan.cli import (
    collect_excluded_directory_names,
    collect_included_suffixes,
    collect_recognized_tags,
    main,
)
from todo_scan.directory_walker import DEFAULT_EXCLUDED_DIRECTORY_NAMES
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


def test_collect_included_suffixes_adds_missing_dots_and_lowercases() -> None:
    """``py`` and ``.PY`` should both mean the ``.py`` suffix."""

    assert collect_included_suffixes(["py,.JS", " .md "]) == {".py", ".js", ".md"}
    assert collect_included_suffixes(None) is None


def test_collect_included_suffixes_rejects_only_empty_values() -> None:
    """An empty allow-list would scan nothing, so it must be a usage error."""

    with pytest.raises(ValueError):
        collect_included_suffixes([" , "])


def test_collect_excluded_directory_names_keeps_the_defaults() -> None:
    """User names are added to the built-in skip list, never replace it."""

    excluded_names = collect_excluded_directory_names(["fixtures/", " generated "])

    assert {"fixtures", "generated"} <= excluded_names
    assert DEFAULT_EXCLUDED_DIRECTORY_NAMES <= excluded_names
    assert collect_excluded_directory_names(None) == DEFAULT_EXCLUDED_DIRECTORY_NAMES


def test_main_applies_suffix_and_exclude_dir_filters(tmp_path: Path, capsys) -> None:
    """Only ``.py`` files outside ``fixtures`` should be reported."""

    (tmp_path / "app.py").write_text("# TODO keep\n", encoding="utf-8")
    (tmp_path / "app.js").write_text("// TODO wrong suffix\n", encoding="utf-8")
    fixtures_directory = tmp_path / "fixtures"
    fixtures_directory.mkdir()
    (fixtures_directory / "sample.py").write_text("# TODO excluded\n", encoding="utf-8")

    exit_status = main([str(tmp_path), "--suffix", "py", "--exclude-dir", "fixtures"])

    assert exit_status == 0
    assert capsys.readouterr().out == "app.py:1: TODO keep\n"


def test_main_returns_usage_status_for_an_empty_suffix(tmp_path: Path) -> None:
    """``--suffix ,`` is a typo, not a request to scan nothing."""

    assert main([str(tmp_path), "--suffix", ","]) == 2


def test_main_prints_stats_to_stderr_and_keeps_stdout_clean(tmp_path: Path, capsys) -> None:
    """``--stats`` must not corrupt a JSON report written to stdout."""

    (tmp_path / "app.py").write_text("# TODO one\n# TODO two\n# FIXME three\n", encoding="utf-8")

    exit_status = main([str(tmp_path), "--format", "json", "--stats"])
    captured = capsys.readouterr()

    assert exit_status == 0
    assert len(json.loads(captured.out)) == 3
    assert captured.err == "TODO   2\nFIXME  1\ntotal  3\n"
