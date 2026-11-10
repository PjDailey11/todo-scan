"""Walk a project tree and yield source files worth scanning.

The walker never follows symlinks. A symlink can point outside the project
(or loop back to a parent), and a comment scanner should not escape the tree
the user asked it to inspect. Directory names are compared exactly, not as
glob patterns, because the common ignore list is a set of well-known tool
output folders rather than a second gitignore implementation.
"""

from __future__ import annotations

from pathlib import Path

# These names are the usual package-manager, VCS, and tool-cache directories
# that dwarf a project's own source. Walking them is slow and almost never
# surfaces a TODO the author can act on. `.github` is deliberately not in the
# list: workflow files are source and often carry real reminders.
DEFAULT_EXCLUDED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".eggs",
        "dist",
        "build",
        "htmlcov",
        "target",
        "vendor",
    }
)


def iter_source_files(
    project_root: Path,
    excluded_directory_names: frozenset[str] | None = None,
) -> list[Path]:
    """Return the source files under ``project_root``, in sorted path order.

    Parameters:
        project_root: Directory to walk, or a single file to yield as-is. A
            file argument is supported so the CLI can accept either a tree or
            one path without a second code path in the caller.
        excluded_directory_names: Directory basenames that should not be
            descended into. When omitted, ``DEFAULT_EXCLUDED_DIRECTORY_NAMES``
            is used.

    Returns:
        A sorted list of file paths. Sorting keeps later reports and tests
        stable across filesystems that do not walk in a deterministic order.

    Behavior:
        Directories whose basename is in the exclude set are not descended
        into, even if they appear in the middle of the tree. Symlinks are not
        followed. Unreadable directories are skipped, so a single permission
        error cannot abort the walk. If ``project_root`` is a file, the exclude
        list is ignored and that file is returned alone.
    """

    names_to_skip = (
        excluded_directory_names
        if excluded_directory_names is not None
        else DEFAULT_EXCLUDED_DIRECTORY_NAMES
    )
    resolved_root = project_root

    if resolved_root.is_file():
        return [resolved_root]
    if not resolved_root.is_dir():
        return []

    discovered_files: list[Path] = []
    directories_to_visit = [resolved_root]
    while directories_to_visit:
        current_directory = directories_to_visit.pop()
        try:
            child_entries = list(current_directory.iterdir())
        except OSError:
            continue
        for child_entry in child_entries:
            try:
                if child_entry.is_symlink():
                    continue
                if child_entry.is_dir():
                    if child_entry.name in names_to_skip:
                        continue
                    directories_to_visit.append(child_entry)
                elif child_entry.is_file():
                    discovered_files.append(child_entry)
            except OSError:
                continue

    discovered_files.sort()
    return discovered_files


def filter_files_by_suffix(
    file_paths: list[Path],
    included_suffixes: frozenset[str] | None,
) -> list[Path]:
    """Return the subset of ``file_paths`` whose suffix is in the allow-list.

    Parameters:
        file_paths: Paths already discovered by ``iter_source_files``.
        included_suffixes: Suffixes including the leading dot, for example
            ``{".py", ".js"}``. When ``None``, the input list is returned
            unchanged so the caller can treat "no filter" as a first-class
            case instead of passing every known suffix.

    Returns:
        A new list in the same order as ``file_paths``. Paths with an empty
        suffix (a file named ``Makefile``, for example) are dropped when a
        filter is provided, because the comment-style table is suffix-based.

    Behavior:
        Comparison is case-insensitive. That matches how
        ``comment_style_for_suffix`` already resolves ``.PY`` to the Python
        style, and it keeps a CLI flag like ``--suffix .PY`` from silently
        matching nothing on a case-sensitive filesystem.
    """

    if included_suffixes is None:
        return list(file_paths)

    lowered_suffixes = {suffix.lower() for suffix in included_suffixes}
    return [
        file_path
        for file_path in file_paths
        if file_path.suffix.lower() in lowered_suffixes
    ]
