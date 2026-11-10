"""Command-line entry point for todo-scan."""

from __future__ import annotations

import argparse
from pathlib import Path

from todo_scan import __version__


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct the public CLI parser without parsing ``sys.argv``.

    Parameters:
        None. The parser is built with its defaults in one place so tests can
        inspect flags without running the process.

    Returns:
        An ``ArgumentParser`` whose program name is ``todo-scan``.

    Behavior:
        The default path is the current working directory because that is the
        usual "scan this project" invocation. Help text stays short; longer
        rationale lives in the README.
    """

    parser = argparse.ArgumentParser(
        prog="todo-scan",
        description="Scan a project tree for TODO, FIXME, and related comment tags.",
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Project directory or single file to scan (default: current directory).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser
