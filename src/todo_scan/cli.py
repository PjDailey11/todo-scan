"""Command-line entry point for todo-scan."""

from __future__ import annotations

import argparse
from pathlib import Path

from todo_scan import __version__
from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS, normalize_tag


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
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        metavar="TAG",
        help=(
            "Limit results to this tag (case-insensitive, repeatable). "
            "May also be a comma-separated list. Default: TODO, FIXME, HACK, XXX, NOTE."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        dest="output_format",
        help="Report format (default: text).",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        metavar="FILE",
        help="Write the report to FILE instead of standard output.",
    )
    return parser


import sys

from todo_scan.project_scan import scan_project_tree
from todo_scan.report import format_json_report, format_markdown_report, format_text_report

def collect_recognized_tags(raw_tag_values: list[str] | None) -> frozenset[str]:
    """Build the tag allow-list from repeated ``--tag`` arguments.

    Parameters:
        raw_tag_values: Values as passed on the command line, or ``None`` when
            the flag was omitted. Each value may itself contain commas so
            ``--tag TODO,FIXME`` works as well as two ``--tag`` flags.

    Returns:
        A frozenset of uppercase tags. When the flag is omitted, the default
        recognized set is returned.

    Behavior:
        Empty pieces (a trailing comma, for example) are dropped. If the user
        supplies only empty pieces, a ``ValueError`` is raised so the CLI can
        turn it into a usage error rather than compiling a pattern that
        matches every comment.

    Raises:
        ValueError: If at least one ``--tag`` was given but no non-empty tag
            remained after splitting and stripping.
    """

    if not raw_tag_values:
        return DEFAULT_RECOGNIZED_TAGS

    collected_tags: set[str] = set()
    for raw_value in raw_tag_values:
        for piece in raw_value.split(","):
            normalized = normalize_tag(piece)
            if normalized:
                collected_tags.add(normalized)

    if not collected_tags:
        raise ValueError("at least one non-empty --tag value is required")
    return frozenset(collected_tags)



def render_report(
    tagged_comments,
    output_format: str,
    project_root,
) -> str:
    """Render ``tagged_comments`` in the user-selected format.

    Parameters:
        tagged_comments: Matches from ``scan_project_tree``.
        output_format: One of ``text``, ``json``, or ``markdown``, already
            validated by argparse.
        project_root: Path used to relativize file names in the report.

    Returns:
        The formatted report string, which may be empty for the text format
        when there are no matches.

    Behavior:
        Unknown formats raise ``ValueError``. argparse should prevent that at
        the CLI, but the helper stays strict so a mistaken internal call is
        obvious in tests.
    """

    if output_format == "text":
        return format_text_report(tagged_comments, project_root=project_root)
    if output_format == "json":
        return format_json_report(tagged_comments, project_root=project_root)
    if output_format == "markdown":
        return format_markdown_report(tagged_comments, project_root=project_root)
    raise ValueError(f"unsupported report format: {output_format}")


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

    try:
        recognized_tags = collect_recognized_tags(arguments.tags)
    except ValueError as exc:
        print(f"todo-scan: {exc}", file=sys.stderr)
        return 2

    tagged_comments = scan_project_tree(project_root, recognized_tags=recognized_tags)
    report_text = render_report(
        tagged_comments,
        output_format=arguments.output_format,
        project_root=project_root,
    )
    if arguments.output_path:
        try:
            Path(arguments.output_path).write_text(report_text, encoding="utf-8")
        except OSError as exc:
            print(f"todo-scan: could not write {arguments.output_path}: {exc}", file=sys.stderr)
            return 1
    elif report_text:
        sys.stdout.write(report_text)
    return 0
