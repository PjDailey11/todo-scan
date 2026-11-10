"""Canonical tag names the scanner looks for by default."""

from __future__ import annotations

# These five tokens are the de-facto convention in most style guides and
# issue-tracker integrations (GitHub, Jira, and many linters). The set stays
# small and uppercase so a user-supplied filter can be compared with simple
# membership after normalization. The three-X token is included because older
# codebases use it as a louder synonym for a fix-me reminder, even though those
# letters can appear in unrelated identifiers; callers who dislike that noise
# can drop it with a tag filter instead of forcing a code change.
DEFAULT_RECOGNIZED_TAGS: frozenset[str] = frozenset(
    {"TODO", "FIXME", "HACK", "XXX", "NOTE"}
)


def normalize_tag(raw_tag: str) -> str:
    """Return ``raw_tag`` in the canonical uppercase form used for comparisons.

    Parameters:
        raw_tag: A tag as it appeared in source or on the command line. Leading
            and trailing whitespace is ignored because comma-separated CLI lists
            are easy to type with spaces.

    Returns:
        The uppercase tag with surrounding whitespace removed.

    Behavior:
        Does not check whether the tag is in ``DEFAULT_RECOGNIZED_TAGS``. Custom
        tags are allowed so a team can search for ``WIP`` or ``SECURITY``
        without patching the tool. An empty string after stripping is returned
        as empty; callers that build allow-lists should reject that themselves.
    """

    return raw_tag.strip().upper()
