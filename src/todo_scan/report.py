"""Format lists of tagged comments for people and for other tools."""

from __future__ import annotations

import json
from pathlib import Path

from todo_scan.tagged_comment import TaggedComment


def format_text_report(
    tagged_comments: list[TaggedComment],
    project_root: Path | None = None,
) -> str:
    """Render matches as one ``path:line: TAG message`` line each.

    Parameters:
        tagged_comments: Matches in the order they should be printed.
        project_root: If given, paths are shown relative to this directory so
            a report started from a project root is not dominated by absolute
            prefixes. When the path is not relative to the root (a user passed
            a file outside it, for example), the original path is kept.

    Returns:
        A trailing-newline-terminated string, or an empty string when there are
        no matches. An empty result is easier for a CLI to print without a
        stray blank line than a hard-coded "no results" message; the CLI can
        still add a summary later.

    Behavior:
        The ``path:line:`` prefix is the same shape as grep and many editor
        error formats, so the output is clickable in terminals and CI logs.
        The tag is written in uppercase to match the normalized data model.
    """

    if not tagged_comments:
        return ""

    report_lines: list[str] = []
    for comment in tagged_comments:
        display_path = _display_path(comment.source_path, project_root)
        message_suffix = f" {comment.message}" if comment.message else ""
        report_lines.append(
            f"{display_path}:{comment.line_number}: {comment.tag}{message_suffix}"
        )
    return "\n".join(report_lines) + "\n"


def _display_path(source_path: Path, project_root: Path | None) -> str:
    """Return a readable path for reports, relative to ``project_root`` when possible."""

    if project_root is None:
        return str(source_path)
    try:
        return str(source_path.relative_to(project_root))
    except ValueError:
        return str(source_path)



def format_json_report(
    tagged_comments: list[TaggedComment],
    project_root: Path | None = None,
) -> str:
    """Render matches as a pretty-printed JSON array.

    Parameters:
        tagged_comments: Matches in the order they should appear in the array.
        project_root: Optional root used to relativize ``path`` values, same
            rule as ``format_text_report``.

    Returns:
        A UTF-8 JSON document ending in a newline. The document is always an
        array, including when it is empty, so downstream tools can parse it
        without a special "no matches" schema.

    Behavior:
        Each object has ``path``, ``line``, ``tag``, ``message``, and
        ``comment_style`` keys. ``ensure_ascii`` is left at the default True
        so the report stays readable in terminals that do not handle escaped
        non-ASCII well; a later flag can relax this if someone needs it.
    """

    payload = [
        {
            "path": _display_path(comment.source_path, project_root),
            "line": comment.line_number,
            "tag": comment.tag,
            "message": comment.message,
            "comment_style": comment.comment_style,
        }
        for comment in tagged_comments
    ]
    return json.dumps(payload, indent=2) + "\n"


def format_markdown_report(
    tagged_comments: list[TaggedComment],
    project_root: Path | None = None,
) -> str:
    """Render matches as a Markdown document grouped by file.

    Parameters:
        tagged_comments: Matches in walk order. Grouping uses that order, so
            callers should not pre-shuffle the list if they want stable
            headings.
        project_root: Optional root used to relativize heading paths.

    Returns:
        A Markdown string ending in a newline, or a short "no tagged comments"
        document when the list is empty, because an empty Markdown file is
        easy to mistake for a failed run.

    Behavior:
        Each file becomes an ``##`` heading, and each match becomes a list
        item with a line number, tag, and message. Grouping by file is more
        useful in a README-style report than a flat table, especially when one
        module accumulates many reminders.
    """

    if not tagged_comments:
        return "No tagged comments found.\n"

    sections: list[str] = ["# Tagged comments", ""]
    current_path: str | None = None
    for comment in tagged_comments:
        display_path = _display_path(comment.source_path, project_root)
        if display_path != current_path:
            if current_path is not None:
                sections.append("")
            sections.append(f"## {display_path}")
            sections.append("")
            current_path = display_path
        message_suffix = f" — {comment.message}" if comment.message else ""
        sections.append(f"- Line {comment.line_number}: `{comment.tag}`{message_suffix}")
    return "\n".join(sections) + "\n"
