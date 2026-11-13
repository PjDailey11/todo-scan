"""Tests for project walking, ignore rules, and suffix filtering."""

from pathlib import Path

from todo_scan.directory_walker import (
    DEFAULT_EXCLUDED_DIRECTORY_NAMES,
    filter_files_by_suffix,
    iter_source_files,
)
from todo_scan.gitignore_rules import parse_gitignore_lines


def test_iter_source_files_skips_excluded_directory_names(tmp_path: Path) -> None:
    """Files under ``node_modules`` or ``.git`` must not appear in the walk."""

    (tmp_path / "src").mkdir()
    visible_source = tmp_path / "src" / "app.py"
    visible_source.write_text("print(1)\n", encoding="utf-8")

    hidden_root = tmp_path / "node_modules" / "pkg"
    hidden_root.mkdir(parents=True)
    (hidden_root / "index.js").write_text("console.log(1)\n", encoding="utf-8")

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    walked_paths = iter_source_files(tmp_path)
    assert walked_paths == [visible_source]
    assert "node_modules" in DEFAULT_EXCLUDED_DIRECTORY_NAMES
    assert ".git" in DEFAULT_EXCLUDED_DIRECTORY_NAMES


def test_iter_source_files_does_not_follow_symlinks(tmp_path: Path) -> None:
    """A symlink into another tree should be ignored so the walk cannot escape.

    The destination tree is created *beside* the project root, not inside it.
    Otherwise the walker would correctly find the real files and the test would
    not be checking symlink handling at all.
    """

    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "real.py").write_text("value = 1\n", encoding="utf-8")

    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    (outside_root / "secret.py").write_text("secret = 1\n", encoding="utf-8")
    (project_root / "link-dir").symlink_to(outside_root)
    (project_root / "link.py").symlink_to(outside_root / "secret.py")

    walked_names = {path.name for path in iter_source_files(project_root)}
    assert walked_names == {"real.py"}


def test_filter_files_by_suffix_is_case_insensitive() -> None:
    """A ``.PY`` filter should still keep a ``.py`` file."""

    kept, dropped = Path("app.py"), Path("app.js")
    filtered = filter_files_by_suffix([kept, dropped], {".PY"})
    assert filtered == [kept]


def test_filter_files_by_suffix_returns_all_paths_when_no_allow_list() -> None:
    """Passing None means no suffix filter is applied, not that nothing matches."""

    sample_paths = [Path("app.py"), Path("Makefile")]
    assert filter_files_by_suffix(sample_paths, None) == sample_paths


def test_iter_source_files_prunes_paths_matched_by_gitignore_rules(tmp_path: Path) -> None:
    """Ignored files are dropped and ignored directories are never entered."""

    kept_source = tmp_path / "src" / "app.py"
    kept_source.parent.mkdir()
    kept_source.write_text("# TODO keep\n", encoding="utf-8")
    (tmp_path / "debug.log").write_text("TODO noise\n", encoding="utf-8")
    generated_dir = tmp_path / "src" / "generated"
    generated_dir.mkdir()
    (generated_dir / "api.py").write_text("# TODO generated\n", encoding="utf-8")

    ignore_rules = parse_gitignore_lines(["*.log", "generated/"])
    walked_paths = iter_source_files(tmp_path, gitignore_rules=ignore_rules)
    assert walked_paths == [kept_source]


def test_iter_source_files_without_rules_keeps_previous_behavior(tmp_path: Path) -> None:
    """Library callers that pass no rules must still see every non-skipped file."""

    (tmp_path / "debug.log").write_text("x\n", encoding="utf-8")
    assert iter_source_files(tmp_path) == [tmp_path / "debug.log"]
    assert iter_source_files(tmp_path, gitignore_rules=[]) == [tmp_path / "debug.log"]
