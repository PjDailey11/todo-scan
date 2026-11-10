"""Data model for a single tagged comment occurrence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaggedComment:
    """A tagged reminder (TODO, FIXME, and similar) found inside a source comment.

    Line numbers are 1-based so they match editor gutters and ``grep -n`` output.
    The tag is stored in uppercase so callers can group results without
    re-normalizing each row. The message is the remainder of the comment after
    the tag and an optional colon; it may be empty when someone writes a bare
    ``TODO``.

    Parameters:
        source_path: Path of the file that contained the comment, preserved as
            the scanner received it rather than forced to an absolute path, so
            reports stay readable when the user passed a relative project root.
        line_number: 1-based line where the tag appeared.
        tag: Normalized uppercase tag, for example ``"TODO"`` or ``"FIXME"``.
        message: Text following the tag, stripped of surrounding whitespace.
        comment_style: Short name of the comment syntax that matched, such as
            ``"hash"`` or ``"c-style"``. Formatters can show this when a file
            mixes more than one dialect.

    Returns:
        An immutable, hashable value object. Instances can be placed in sets or
        used as dictionary keys without a further identity helper.

    Behavior:
        No validation is performed at construction time. The scanner is
        responsible for supplying a positive line number and an already
        normalized tag; treating this as a plain record keeps it easy to build
        in tests.
    """

    source_path: Path
    line_number: int
    tag: str
    message: str
    comment_style: str
