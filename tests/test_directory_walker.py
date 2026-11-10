"""Tests for project walking, ignore rules, and suffix filtering."""

from pathlib import Path

from todo_scan.directory_walker import (
    DEFAULT_EXCLUDED_DIRECTORY_NAMES,
    filter_files_by_suffix,
    iter_source_files,
)


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
    """A symlink into another tree should be ignored so the walk cannot escape."""

    (tmp_path / "real.py").write_text("value = 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("secret = 1\n", encoding="utf-8")
    (tmp_path / "link-dir").symlink_to(outside)
    (tmp_path / "link.py").symlink_to(outside / "secret.py")

    walked_names = {path.name for path in iter_source_files(tmp_path)}
    assert walked_names == {"real.py"}


def test_filter_files_by_suffix_is_case_insensitive() -> None:
    """A ``.PY`` filter should still keep a ``.py`` file."""

    kept, dropped = Path("app.py"), Path("app.js")
    filtered = filter_files_by_suffix([kept, dropped], {".PY"})
    assert filtered == [kept]


def test_filter_files_by_suffix_returns_all_paths_when_no_allow_list() -> None:
    """``None`` means "no suffix filter," not "match nothing.""" "

    sample_paths = [Path("app.py"), Path("Makefile")]
    assert filter_files_by_suffix(sample_paths, None) == sample_paths
