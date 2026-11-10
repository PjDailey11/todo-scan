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
