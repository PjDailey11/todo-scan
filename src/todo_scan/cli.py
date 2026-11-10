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


import sys

from todo_scan.project_scan import scan_project_tree
from todo_scan.report import format_text_report


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit status.

    Parameters:
        argv: Argument list without the program name, as ``argparse`` expects.
            When omitted, ``sys.argv[1:]`` is used so the function stays easy
            to call from tests.

    Returns:
        ``0`` after a successful scan, even when no tags are found. This tool
        is a reporter, not a linter; a non-zero "has TODOs" status is left for
        a dedicated ``--check`` flag so CI users can opt into that behavior.

    Behavior:
        Writes the text report to standard output. A missing project path is
        reported to standard error and returns ``2``, the conventional
        usage-error status, instead of raising a traceback.
    """

    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    project_root = Path(arguments.project_path)
    if not project_root.exists():
        print(f"todo-scan: path not found: {project_root}", file=sys.stderr)
        return 2

    tagged_comments = scan_project_tree(project_root)
    report_text = format_text_report(tagged_comments, project_root=project_root)
    if report_text:
        sys.stdout.write(report_text)
    return 0
