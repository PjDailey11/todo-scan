"""Format lists of tagged comments for people and for other tools."""

from __future__ import annotations

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
