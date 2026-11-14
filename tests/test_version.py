"""Guard against the package version drifting between its two sources."""

import re
from pathlib import Path

import pytest

from todo_scan import __version__
from todo_scan.cli import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read_pyproject_version() -> str:
    """Return the ``[project]`` version string from ``pyproject.toml``.

    ``tomllib`` only exists on Python 3.11+, and the package supports 3.9, so
    a narrow regex is used instead of adding a test dependency. It looks for
    the first ``version = "..."`` line, which is the ``[project]`` table's in
    this file; a second table with its own ``version`` key would need a real
    TOML parser.
    """

    pyproject_text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    assert version_match is not None, "pyproject.toml has no version line"
    return version_match.group(1)


def test_package_version_matches_pyproject() -> None:
    """``__version__`` and ``pyproject.toml`` are bumped by hand and must agree."""

    assert __version__ == _read_pyproject_version()


def test_changelog_has_a_section_for_the_current_version() -> None:
    """A release bump without a changelog entry is easy to forget."""

    changelog_text = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__} - " in changelog_text


def test_cli_version_flag_prints_the_package_version(capsys) -> None:
    """``--version`` exits via argparse with status 0 and the current version."""

    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"todo-scan {__version__}"
