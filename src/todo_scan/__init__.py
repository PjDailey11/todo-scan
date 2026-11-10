"""Scan a project tree for TODO, FIXME, and related comment tags.

The public surface of this package is intentionally small: a data type for one
match, a file scanner, a directory walker, report formatters, and a CLI. Import
the symbols you need from the submodules rather than relying on a large
re-export list; that keeps the installable version and the library API easy to
keep in sync.

Attributes:
    __version__: The installable package version. It is duplicated in
        ``pyproject.toml`` because setuptools reads the project table at build
        time, while this module attribute is what ``todo-scan --version`` and
        runtime callers should use.
"""

__version__ = "0.1.0"
