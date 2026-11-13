"""Command-line entry point for todo-scan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from todo_scan import __version__
from todo_scan.directory_walker import DEFAULT_EXCLUDED_DIRECTORY_NAMES
from todo_scan.project_scan import scan_project_tree
from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS, normalize_tag
from todo_scan.result_ordering import DEFAULT_SORT_ORDER, SORT_ORDERS, sort_tagged_comments
from todo_scan.report import (
    format_json_report,
    format_markdown_report,
    format_tag_summary,
    format_text_report,
)


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
        "--sort",
        choices=SORT_ORDERS,
        default=DEFAULT_SORT_ORDER,
        dest="sort_order",
        help=(
            "Order results by file (path, then line; default), tag (grouped by "
            "tag name), or count (files with the most matches first)."
        ),
    )
    parser.add_argument(
        "--suffix",
        action="append",
        dest="suffixes",
        metavar="SUFFIX",
        help=(
            "Only scan files with this suffix, e.g. .py (repeatable, comma lists "
            "allowed; the leading dot is optional). Default: every recognized file."
        ),
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        dest="excluded_directories",
        metavar="NAME",
        help=(
            "Skip directories with this exact name, in addition to the built-in "
            "list (.git, node_modules, .venv, ...). Repeatable."
        ),
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_false",
        dest="respect_gitignore",
        help=(
            "Do not apply the project's top-level .gitignore while walking. "
            "The built-in directory skip list still applies."
        ),
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help=(
            "Print a per-tag count summary to standard error after the report, "
            "so piped JSON or Markdown output stays valid."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit with status 1 when any tagged comment is found (for CI). "
            "The report is still printed so the log shows what failed."
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help=(
            "Do not print the report to standard output. --output and --stats "
            "still work, so this only silences the terminal report."
        ),
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        metavar="FILE",
        help="Write the report to FILE instead of standard output.",
    )
    return parser


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


def collect_included_suffixes(raw_suffix_values: list[str] | None) -> frozenset[str] | None:
    """Build the file-suffix allow-list from repeated ``--suffix`` arguments.

    Parameters:
        raw_suffix_values: Values as passed on the command line, or ``None``
            when the flag was omitted. Each value may contain commas, so
            ``--suffix py,js`` is equivalent to two flags.

    Returns:
        ``None`` when the flag was omitted, meaning "do not filter by suffix".
        Otherwise a frozenset of lowercase suffixes that always start with a
        dot, because ``Path.suffix`` includes the dot and users commonly type
        ``py`` instead of ``.py``.

    Behavior:
        Empty pieces are dropped. Case is folded here even though
        ``filter_files_by_suffix`` also compares case-insensitively, so the
        normalized set is predictable in tests and error messages.

    Raises:
        ValueError: If ``--suffix`` was given but every piece was empty. An
            empty allow-list would silently scan nothing, which looks like a
            clean project rather than a typo.
    """

    if raw_suffix_values is None:
        return None

    normalized_suffixes: set[str] = set()
    for raw_value in raw_suffix_values:
        for piece in raw_value.split(","):
            stripped_piece = piece.strip().lower()
            if not stripped_piece:
                continue
            if not stripped_piece.startswith("."):
                stripped_piece = "." + stripped_piece
            normalized_suffixes.add(stripped_piece)

    if not normalized_suffixes:
        raise ValueError("at least one non-empty --suffix value is required")
    return frozenset(normalized_suffixes)


def collect_excluded_directory_names(raw_directory_names: list[str] | None) -> frozenset[str]:
    """Merge ``--exclude-dir`` values with the walker's built-in skip list.

    Parameters:
        raw_directory_names: Directory basenames from the command line, or
            ``None`` when the flag was omitted.

    Returns:
        The union of ``DEFAULT_EXCLUDED_DIRECTORY_NAMES`` and the user's
        names. Adding to the defaults, instead of replacing them, means that
        ``--exclude-dir fixtures`` does not suddenly start walking
        ``node_modules`` and ``.git``.

    Behavior:
        Names are matched exactly by the walker, so surrounding whitespace and
        trailing slashes (``fixtures/`` from shell tab completion) are
        stripped here. Names are kept case-sensitive because most
        filesystems the tool runs on are case-sensitive.
    """

    if not raw_directory_names:
        return DEFAULT_EXCLUDED_DIRECTORY_NAMES

    user_directory_names = {
        raw_name.strip().rstrip("/\\")
        for raw_name in raw_directory_names
    }
    user_directory_names.discard("")
    return DEFAULT_EXCLUDED_DIRECTORY_NAMES | frozenset(user_directory_names)


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
        ``0`` after a successful scan, even when tags are found, because by
        default this tool is a reporter, not a linter. With ``--check``, a
        scan that found at least one tag returns ``1`` so CI users can opt
        into failing the build. ``1`` is also returned when ``--output``
        cannot be written, and ``2`` for usage errors.

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
        included_suffixes = collect_included_suffixes(arguments.suffixes)
    except ValueError as exc:
        print(f"todo-scan: {exc}", file=sys.stderr)
        return 2
    excluded_directory_names = collect_excluded_directory_names(
        arguments.excluded_directories
    )

    tagged_comments = scan_project_tree(
        project_root,
        recognized_tags=recognized_tags,
        excluded_directory_names=excluded_directory_names,
        included_suffixes=included_suffixes,
        respect_gitignore=arguments.respect_gitignore,
    )
    # Ordering happens after the scan and before every formatter so text,
    # JSON, and Markdown all agree. The Markdown formatter groups consecutive
    # rows by file, so "--sort tag" can repeat a file heading; that is the
    # honest view of a tag-first ordering rather than a bug.
    tagged_comments = sort_tagged_comments(tagged_comments, arguments.sort_order)
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
    elif report_text and not arguments.quiet:
        # --quiet deliberately does not affect --output: a CI step that wants
        # a silent log can still archive the full report as an artifact.
        sys.stdout.write(report_text)

    if arguments.stats:
        # The summary goes to stderr on purpose: `--format json --stats > out.json`
        # must still produce a parseable document, and stderr is shown in a
        # terminal or CI log either way.
        sys.stderr.write(format_tag_summary(tagged_comments))

    # Status 1 is reserved for "findings" (and output write failures); usage
    # errors stay at 2 above, so a CI step can tell a bad invocation apart
    # from a project that still has FIXMEs in it.
    if arguments.check and tagged_comments:
        return 1
    return 0
