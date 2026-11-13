"""Reorder scan results for triage without touching the scanner.

The scanner and walker always produce matches in walk order (sorted path, then
line). Keeping ordering as a separate pure step means every report format and
any library caller share exactly the same rules, and the scan itself never
needs to know how the user wants to read the output.
"""

from __future__ import annotations

from collections import Counter

from todo_scan.tagged_comment import TaggedComment

# Public so the CLI can build its ``--sort`` choices from one source of truth.
SORT_ORDERS: tuple[str, ...] = ("file", "tag", "count")
DEFAULT_SORT_ORDER = "file"


def _location_key(comment: TaggedComment) -> tuple[str, int]:
    """Sort key for path then line; as_posix() keeps ordering OS-independent."""

    return (comment.source_path.as_posix(), comment.line_number)


def sort_tagged_comments(
    tagged_comments: list[TaggedComment],
    sort_order: str = DEFAULT_SORT_ORDER,
) -> list[TaggedComment]:
    """Return a new list of ``tagged_comments`` in the requested order.

    Parameters:
        tagged_comments: Matches from ``scan_project_tree`` (or any list of
            ``TaggedComment`` values). The input list is not modified.
        sort_order: One of ``SORT_ORDERS``:

            - ``"file"``: path, then line number (the walk order).
            - ``"tag"``: tag name alphabetically, then path and line, so all
              ``FIXME`` entries sit together.
            - ``"count"``: files with the most matches first, ties broken by
              path, and line order kept inside each file. Useful for finding
              the modules that need attention most.

    Returns:
        A newly built list; ties always fall back to path and line so the
        output is deterministic across runs and filesystems.

    Raises:
        ValueError: If ``sort_order`` is not one of ``SORT_ORDERS``. argparse
            already restricts the CLI, but library callers get a clear error
            instead of a silently unsorted report.
    """

    if sort_order == "file":
        return sorted(tagged_comments, key=_location_key)
    if sort_order == "tag":
        return sorted(
            tagged_comments,
            key=lambda comment: (comment.tag, *_location_key(comment)),
        )
    if sort_order == "count":
        # Count per path string rather than per Path object so "./a.py" and
        # "a.py" from different callers cannot split one file into two groups.
        matches_per_file = Counter(
            comment.source_path.as_posix() for comment in tagged_comments
        )
        return sorted(
            tagged_comments,
            key=lambda comment: (
                -matches_per_file[comment.source_path.as_posix()],
                *_location_key(comment),
            ),
        )
    raise ValueError(
        f"unsupported sort order: {sort_order!r} (expected one of {', '.join(SORT_ORDERS)})"
    )
