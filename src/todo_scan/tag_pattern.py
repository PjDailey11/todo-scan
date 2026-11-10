"""Regular-expression helper that finds tags inside already-extracted comment text."""

from __future__ import annotations

import re


def build_tag_search_pattern(recognized_tags: frozenset[str]) -> re.Pattern[str]:
    """Compile a case-insensitive pattern that captures a tag and its message.

    Parameters:
        recognized_tags: Uppercase tag tokens to search for. The set may include
            custom tags such as ``WIP`` in addition to the defaults.

    Returns:
        A compiled pattern whose first group is the tag as it appeared in the
        source and whose second group is the remainder of the line after an
        optional colon.

    Behavior:
        Tags are escaped and then joined with word boundaries so a custom tag
        containing regex metacharacters cannot alter the pattern, and so
        ``TODO`` does not match inside ``TODOS``. Longer tags are listed first
        to keep alternation predictable if a team later adds a tag that is a
        prefix of another. The optional colon is accepted because both
        ``TODO fix this`` and ``TODO: fix this`` are conventional.

    Raises:
        ValueError: If ``recognized_tags`` is empty, which would compile a
            pattern that matches every comment.
    """

    if not recognized_tags:
        raise ValueError("recognized_tags must contain at least one tag")

    escaped_tags = [
        re.escape(tag) for tag in sorted(recognized_tags, key=len, reverse=True)
    ]
    alternation = "|".join(escaped_tags)
    return re.compile(
        rf"\b({alternation})\b\s*:?\s*(.*)$",
        re.IGNORECASE,
    )
