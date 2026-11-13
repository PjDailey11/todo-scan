"""Tests for the simplified .gitignore parser and matcher."""

from pathlib import Path

from todo_scan.gitignore_rules import (
    GitignoreRule,
    is_path_ignored,
    load_gitignore_rules,
    parse_gitignore_lines,
)


def test_parse_skips_comments_blanks_and_bare_slashes() -> None:
    """Only real patterns become rules; a lone ``/`` must not match everything."""

    parsed_rules = parse_gitignore_lines(["# generated", "", "   ", "/", "*.log\n"])
    assert parsed_rules == [
        GitignoreRule(pattern="*.log", negated=False, directory_only=False, anchored=False)
    ]


def test_parse_records_negation_directory_and_anchor_flags() -> None:
    """Each modifier is stripped from the pattern and kept as a flag instead."""

    negated_rule, directory_rule, anchored_rule, middle_slash_rule = parse_gitignore_lines(
        ["!keep.log", "generated/", "/local.cfg", "docs/drafts"]
    )
    assert negated_rule == GitignoreRule("keep.log", True, False, False)
    assert directory_rule == GitignoreRule("generated", False, True, False)
    assert anchored_rule == GitignoreRule("local.cfg", False, False, True)
    assert middle_slash_rule == GitignoreRule("docs/drafts", False, False, True)


def test_parse_honors_backslash_escape_for_literal_hash() -> None:
    """``\\#notes`` is a file literally named ``#notes``, not a comment."""

    (escaped_rule,) = parse_gitignore_lines(["\\#notes"])
    assert escaped_rule.pattern == "#notes"
    assert escaped_rule.negated is False


def test_unanchored_rule_matches_basename_at_any_depth() -> None:
    rules = parse_gitignore_lines(["*.log"])
    assert is_path_ignored("today.log", False, rules)
    assert is_path_ignored("logs/deep/today.log", False, rules)
    assert not is_path_ignored("today.py", False, rules)


def test_directory_only_rule_ignores_directories_but_not_files() -> None:
    rules = parse_gitignore_lines(["generated/"])
    assert is_path_ignored("src/generated", True, rules)
    assert not is_path_ignored("src/generated", False, rules)


def test_anchored_rule_only_matches_from_the_project_root() -> None:
    rules = parse_gitignore_lines(["/docs/drafts"])
    assert is_path_ignored("docs/drafts", True, rules)
    assert not is_path_ignored("vendor/docs/drafts", True, rules)


def test_last_matching_rule_wins_so_negation_reincludes() -> None:
    """Order matters: ``!keep.log`` after ``*.log`` keeps that one file."""

    rules = parse_gitignore_lines(["*.log", "!keep.log"])
    assert is_path_ignored("app.log", False, rules)
    assert not is_path_ignored("keep.log", False, rules)

    reversed_rules = parse_gitignore_lines(["!keep.log", "*.log"])
    assert is_path_ignored("keep.log", False, reversed_rules)


def test_matching_is_case_sensitive() -> None:
    rules = parse_gitignore_lines(["Secrets.txt"])
    assert not is_path_ignored("secrets.txt", False, rules)


def test_load_returns_empty_rules_when_file_missing_or_not_utf8(tmp_path: Path) -> None:
    """A missing or undecodable ignore file must not abort a scan."""

    assert load_gitignore_rules(tmp_path) == []
    (tmp_path / ".gitignore").write_bytes(b"\xff\xfe*.log\n")
    assert load_gitignore_rules(tmp_path) == []


def test_load_parses_the_root_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.log\nbuild-local/\n", encoding="utf-8")
    loaded_patterns = [rule.pattern for rule in load_gitignore_rules(tmp_path)]
    assert loaded_patterns == ["*.log", "build-local"]
