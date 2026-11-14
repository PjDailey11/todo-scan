"""Tests for CLI argument handling and the process entry point."""

import argparse
import json
from pathlib import Path

import pytest

from todo_scan.cli import (
    collect_excluded_directory_names,
    collect_included_suffixes,
    collect_recognized_tags,
    main,
    parse_non_negative_count,
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


def test_main_check_returns_one_when_tags_are_found(tmp_path: Path, capsys) -> None:
    """``--check`` fails the run but still prints the report for the CI log."""

    (tmp_path / "app.py").write_text("# FIXME before release\n", encoding="utf-8")

    exit_status = main([str(tmp_path), "--check"])

    assert exit_status == 1
    assert capsys.readouterr().out == "app.py:1: FIXME before release\n"


def test_main_check_returns_zero_when_filtered_tags_are_absent(tmp_path: Path) -> None:
    """Gating on ``--tag FIXME`` should ignore other tags such as TODO."""

    (tmp_path / "app.py").write_text("# TODO later is fine\n", encoding="utf-8")

    assert main([str(tmp_path), "--check", "--tag", "FIXME"]) == 0


def test_main_check_keeps_usage_errors_at_status_two() -> None:
    """A bad path must not be confused with "tags found" in CI."""

    assert main(["/this/path/does/not/exist", "--check"]) == 2


def test_main_quiet_with_check_prints_nothing_but_still_fails(tmp_path: Path, capsys) -> None:
    """``--quiet --check`` is a pure exit-status gate for hooks and CI."""

    (tmp_path / "app.py").write_text("# FIXME before release\n", encoding="utf-8")

    exit_status = main([str(tmp_path), "--check", "--quiet"])
    captured = capsys.readouterr()

    assert exit_status == 1
    assert captured.out == ""
    assert captured.err == ""


def test_main_quiet_still_writes_output_file_and_stats(tmp_path: Path, capsys) -> None:
    """``--quiet`` only silences stdout; the artifact and stderr summary remain."""

    (tmp_path / "app.py").write_text("# TODO one\n", encoding="utf-8")
    report_path = tmp_path / "report.json"

    exit_status = main(
        [str(tmp_path / "app.py"), "-q", "--stats", "--format", "json", "--output", str(report_path)]
    )
    captured = capsys.readouterr()

    assert exit_status == 0
    assert captured.out == ""
    assert captured.err == "TODO   1\ntotal  1\n"
    assert json.loads(report_path.read_text(encoding="utf-8"))[0]["tag"] == "TODO"


def test_parse_non_negative_count_accepts_zero_and_rejects_bad_values() -> None:
    """Zero is a valid budget; negatives and non-numbers are typos."""

    assert parse_non_negative_count("0") == 0
    assert parse_non_negative_count(" 12 ") == 12
    for bad_value in ("-1", "three", "1.5", ""):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_non_negative_count(bad_value)


def test_main_max_count_fails_only_above_the_budget(tmp_path: Path) -> None:
    """Two tags pass a budget of two and fail a budget of one."""

    (tmp_path / "app.py").write_text("# TODO one\n# FIXME two\n", encoding="utf-8")

    assert main([str(tmp_path), "-q", "--max-count", "2"]) == 0
    assert main([str(tmp_path), "-q", "--max-count", "1"]) == 1


def test_main_max_count_overrides_check(tmp_path: Path) -> None:
    """An explicit budget wins over the zero budget implied by ``--check``."""

    (tmp_path / "app.py").write_text("# TODO one\n", encoding="utf-8")

    assert main([str(tmp_path), "-q", "--check", "--max-count", "5"]) == 0


def test_main_rejects_a_negative_max_count(tmp_path: Path, capsys) -> None:
    """argparse turns the type error into a usage error with status 2."""

    with pytest.raises(SystemExit) as exit_info:
        main([str(tmp_path), "--max-count", "-3"])

    assert exit_info.value.code == 2
    assert "must be zero or greater" in capsys.readouterr().err


def test_main_honors_gitignore_by_default_and_no_gitignore_disables_it(
    tmp_path: Path, capsys
) -> None:
    """Ignored files are skipped unless the user opts out with --no-gitignore."""

    (tmp_path / ".gitignore").write_text("generated/\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("# TODO real work\n", encoding="utf-8")
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    (generated_dir / "client.py").write_text("# TODO regenerate\n", encoding="utf-8")

    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == "app.py:1: TODO real work\n"

    assert main([str(tmp_path), "--no-gitignore"]) == 0
    assert capsys.readouterr().out == (
        "app.py:1: TODO real work\n"
        "generated/client.py:1: TODO regenerate\n"
    )


def test_main_scans_an_explicit_file_even_if_gitignore_matches_it(
    tmp_path: Path, capsys
) -> None:
    """Naming a file directly is a request to scan it, ignore rules or not."""

    (tmp_path / ".gitignore").write_text("*.py\n", encoding="utf-8")
    ignored_file = tmp_path / "scratch.py"
    ignored_file.write_text("# FIXME still wanted\n", encoding="utf-8")

    assert main([str(ignored_file)]) == 0
    assert "FIXME still wanted" in capsys.readouterr().out


def _write_sort_fixture(project_root: Path) -> None:
    """One file with a single TODO and one with two matches, so orders differ."""

    (project_root / "alpha.py").write_text("# TODO alpha task\n", encoding="utf-8")
    (project_root / "beta.py").write_text(
        "# FIXME beta bug\n# TODO beta task\n", encoding="utf-8"
    )


def test_main_sort_defaults_to_file_order(tmp_path: Path, capsys) -> None:
    _write_sort_fixture(tmp_path)
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "alpha.py:1: TODO alpha task\n"
        "beta.py:1: FIXME beta bug\n"
        "beta.py:2: TODO beta task\n"
    )


def test_main_sort_tag_and_count_reorder_the_report(tmp_path: Path, capsys) -> None:
    _write_sort_fixture(tmp_path)

    assert main([str(tmp_path), "--sort", "tag"]) == 0
    assert capsys.readouterr().out == (
        "beta.py:1: FIXME beta bug\n"
        "alpha.py:1: TODO alpha task\n"
        "beta.py:2: TODO beta task\n"
    )

    assert main([str(tmp_path), "--sort", "count"]) == 0
    assert capsys.readouterr().out == (
        "beta.py:1: FIXME beta bug\n"
        "beta.py:2: TODO beta task\n"
        "alpha.py:1: TODO alpha task\n"
    )


def test_main_sort_applies_to_json_output(tmp_path: Path, capsys) -> None:
    """Every format shares the ordering, not just the text report."""

    _write_sort_fixture(tmp_path)
    assert main([str(tmp_path), "--sort", "tag", "--format", "json"]) == 0
    reported_tags = [row["tag"] for row in json.loads(capsys.readouterr().out)]
    assert reported_tags == ["FIXME", "TODO", "TODO"]


def test_main_rejects_an_unknown_sort_order(tmp_path: Path, capsys) -> None:
    """argparse turns a bad --sort value into exit status 2 with a message."""

    with pytest.raises(SystemExit) as exit_info:
        main([str(tmp_path), "--sort", "severity"])
    assert exit_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
