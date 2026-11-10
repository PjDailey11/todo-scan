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


HASH_COMMENT_STYLE = CommentStyle(style_name="hash", line_prefix="#")
"""Line comments introduced by ``#`` (Python, Ruby, Shell, YAML, Toml, and similar)."""

# C, C++, Java, JavaScript, TypeScript, Go, Rust, and many others share the
# same two delimiters. We keep a slash-only style as well because some languages
# (JSON-with-comments, certain shader dialects) allow `//` but not block
# comments, and treating them as "c-style" would search for `/*` that never
# legally appears.
SLASH_SLASH_COMMENT_STYLE = CommentStyle(
    style_name="slash-slash",
    line_prefix="//",
)
C_STYLE_COMMENT_STYLE = CommentStyle(
    style_name="c-style",
    line_prefix="//",
    block_start="/*",
    block_end="*/",
)

# HTML/XML and Markdown HTML comments share the same pair. SQL, Lua, and Haskell
# use `--` as a line comment; we do not attempt Haskell's `{--}` blocks here
# because they are uncommon in the trees this tool is aimed at. Lisp-family
# languages use `;`.
HTML_COMMENT_STYLE = CommentStyle(
    style_name="html",
    block_start="<!--",
    block_end="-->",
)
DASH_DASH_COMMENT_STYLE = CommentStyle(
    style_name="dash-dash",
    line_prefix="--",
)
SEMICOLON_COMMENT_STYLE = CommentStyle(
    style_name="semicolon",
    line_prefix=";",
)
