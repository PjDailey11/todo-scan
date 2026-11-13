"""Parse and apply a practical subset of ``.gitignore`` patterns.

todo-scan only needs to answer "would git ignore this path?" well enough to
keep generated and local-only files out of a report. Re-implementing every
corner of git's wildmatch is not worth it for a comment scanner, so this module
supports the patterns that cover nearly every real ``.gitignore``:

- blank lines and ``#`` comments are skipped,
- ``!pattern`` re-includes a path that an earlier rule ignored,
- a trailing ``/`` limits the rule to directories,
- a ``/`` at the start or in the middle anchors the rule to the project root,
- otherwise the rule matches a basename at any depth,
- wildcards follow :mod:`fnmatch` (``*``, ``?``, ``[abc]``).

Known gaps are listed in ``docs/how-it-works.md``: nested ``.gitignore``
files, global excludes, and git's special ``**`` semantics are not modeled.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

GITIGNORE_FILE_NAME = ".gitignore"


@dataclass(frozen=True)
class GitignoreRule:
    """One parsed, non-comment line of a ``.gitignore`` file.

    Parameters:
        pattern: The glob with the leading ``!``/``/`` and trailing ``/``
            already removed, so matching code never has to re-strip it.
        negated: ``True`` for ``!pattern`` lines, which re-include a path.
        directory_only: ``True`` when the line ended in ``/``; such a rule
            never matches a regular file.
        anchored: ``True`` when the rule is relative to the project root
            (a leading slash, or a slash anywhere inside the pattern, as git
            defines it). Unanchored rules match a basename at any depth.

    Returns:
        An immutable record; instances are hashable and safe to share.
    """

    pattern: str
    negated: bool
    directory_only: bool
    anchored: bool


def parse_gitignore_lines(gitignore_lines: list[str]) -> list[GitignoreRule]:
    """Turn raw ``.gitignore`` lines into ordered ``GitignoreRule`` values.

    Parameters:
        gitignore_lines: Lines as read from the file, with or without their
            trailing newline.

    Returns:
        Rules in file order. Order matters because the last matching rule
        decides, which is how ``!`` negation can undo an earlier ignore.

    Behavior:
        Blank lines and ``#`` comments produce no rule. A leading backslash
        escapes a literal ``#`` or ``!`` (``\\#notes.txt``). Trailing
        whitespace is dropped because editors leave it behind and git ignores
        it unless escaped; escaped trailing spaces are rare enough that they
        are not supported. A line that is only ``/`` or ``!`` after stripping
        is skipped instead of becoming a rule that matches everything.
    """

    parsed_rules: list[GitignoreRule] = []
    for raw_line in gitignore_lines:
        line_text = raw_line.rstrip("\r\n").rstrip()
        if not line_text or line_text.startswith("#"):
            continue

        negated = False
        if line_text.startswith("!"):
            negated = True
            line_text = line_text[1:]
        elif line_text.startswith("\\"):
            # "\#" and "\!" mean a literal first character, not a comment
            # or a negation, so drop only the escaping backslash.
            line_text = line_text[1:]

        directory_only = line_text.endswith("/")
        line_text = line_text.rstrip("/")

        # Git anchors a pattern that contains a slash anywhere except at the
        # end; the trailing slash was removed above, so any remaining slash
        # (leading or middle) makes the rule root-relative.
        anchored = "/" in line_text
        line_text = line_text.lstrip("/")
        if not line_text:
            continue

        parsed_rules.append(
            GitignoreRule(
                pattern=line_text,
                negated=negated,
                directory_only=directory_only,
                anchored=anchored,
            )
        )
    return parsed_rules


def load_gitignore_rules(project_root: Path) -> list[GitignoreRule]:
    """Read and parse ``project_root/.gitignore`` if it exists.

    Parameters:
        project_root: Directory whose top-level ``.gitignore`` should apply.

    Returns:
        The parsed rules, or an empty list when the file is missing,
        unreadable, or not valid UTF-8. A broken ignore file should never stop
        a scan; scanning a few extra files is the safer failure.
    """

    gitignore_path = project_root / GITIGNORE_FILE_NAME
    try:
        gitignore_text = gitignore_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return parse_gitignore_lines(gitignore_text.splitlines())
