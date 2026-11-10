"""Comment-syntax descriptions used to decide where a tag is legal.

The scanner is a heuristic, not a language parser. We therefore describe only
the comment delimiters that matter for finding tags, and we key them off file
suffixes later. This will miss unusual dialects and can still false-positive
inside strings; that trade-off is documented on the scanner and in the README
because a full lexer per language would be far more code than this tool
warrants.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommentStyle:
    """Delimiters that introduce comments in one language family.

    Parameters:
        style_name: Stable identifier stored on each match and used in tests.
        line_prefix: Marker that starts a comment running to the end of the
            line (``#``, ``//``, ``--``, ``;``), or ``None`` if this style has
            no line comments we recognize.
        block_start: Opening delimiter of a multi-line comment, or ``None``.
        block_end: Closing delimiter matching ``block_start``, or ``None``.

    Returns:
        An immutable syntax record. The scanner assumes ``block_start`` and
        ``block_end`` are either both set or both ``None``.

    Behavior:
        This object is a pure description of delimiters. Mapping file suffixes
        onto a style lives in a separate helper so tests can construct a style
        without inventing a path.
    """

    style_name: str
    line_prefix: str | None = None
    block_start: str | None = None
    block_end: str | None = None
