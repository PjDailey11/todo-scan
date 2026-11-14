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

# HTML/XML and Markdown HTML comments share the same pair. SQL and Lua use
# `--` as a line comment (Lua's `--[[ ]]` blocks are not modeled: their opener
# starts with the line prefix, so the line rule already catches the first
# line). Lisp-family languages use `;`.
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

# Haskell pairs `--` line comments with `{- -}` blocks. Real Haskell blocks
# nest, but the scanner's state machine is a single flag, so the first `-}`
# closes the block here, the same simplification made for C. Pragmas such as
# `{-# LANGUAGE ... #-}` are parsed as ordinary blocks; they never contain a
# tag word, so they cost nothing. When `--` and `{-` both appear, whichever is
# earlier on the line wins, so `{--` opens a block rather than a line comment.
HASKELL_COMMENT_STYLE = CommentStyle(
    style_name="haskell",
    line_prefix="--",
    block_start="{-",
    block_end="-}",
)

# Erlang (and its escript files) only has `%` line comments; the community
# convention of `%%` / `%%%` for section headers still works because the tag
# search runs on everything after the first `%`. A `%` inside a format string
# such as "~p%" can start a false comment; that is the same string-literal
# trade-off every other style here accepts.
PERCENT_COMMENT_STYLE = CommentStyle(
    style_name="percent",
    line_prefix="%",
)


# Suffixes are compared in lowercase with the leading dot included so that
# ".h" and "h" cannot be confused. Files with no suffix, or a suffix we have
# not seen, return None; the scanner skips them rather than guessing, because
# a wrong guess (treating a binary `.min` file as C, for example) produces
# more bad matches than it saves.
_SUFFIX_TO_COMMENT_STYLE: dict[str, CommentStyle] = {
    ".py": HASH_COMMENT_STYLE,
    ".pyi": HASH_COMMENT_STYLE,
    ".rb": HASH_COMMENT_STYLE,
    ".sh": HASH_COMMENT_STYLE,
    ".bash": HASH_COMMENT_STYLE,
    ".zsh": HASH_COMMENT_STYLE,
    ".yml": HASH_COMMENT_STYLE,
    ".yaml": HASH_COMMENT_STYLE,
    ".toml": HASH_COMMENT_STYLE,
    ".r": HASH_COMMENT_STYLE,
    ".R": HASH_COMMENT_STYLE,
    ".pl": HASH_COMMENT_STYLE,
    ".c": C_STYLE_COMMENT_STYLE,
    ".h": C_STYLE_COMMENT_STYLE,
    ".cc": C_STYLE_COMMENT_STYLE,
    ".cpp": C_STYLE_COMMENT_STYLE,
    ".cxx": C_STYLE_COMMENT_STYLE,
    ".hpp": C_STYLE_COMMENT_STYLE,
    ".hh": C_STYLE_COMMENT_STYLE,
    ".java": C_STYLE_COMMENT_STYLE,
    ".js": C_STYLE_COMMENT_STYLE,
    ".jsx": C_STYLE_COMMENT_STYLE,
    ".ts": C_STYLE_COMMENT_STYLE,
    ".tsx": C_STYLE_COMMENT_STYLE,
    ".mjs": C_STYLE_COMMENT_STYLE,
    ".cjs": C_STYLE_COMMENT_STYLE,
    ".go": C_STYLE_COMMENT_STYLE,
    ".rs": C_STYLE_COMMENT_STYLE,
    ".swift": C_STYLE_COMMENT_STYLE,
    ".kt": C_STYLE_COMMENT_STYLE,
    ".kts": C_STYLE_COMMENT_STYLE,
    ".cs": C_STYLE_COMMENT_STYLE,
    ".php": C_STYLE_COMMENT_STYLE,
    ".css": C_STYLE_COMMENT_STYLE,
    ".scss": C_STYLE_COMMENT_STYLE,
    ".jsonc": SLASH_SLASH_COMMENT_STYLE,
    ".html": HTML_COMMENT_STYLE,
    ".htm": HTML_COMMENT_STYLE,
    ".xml": HTML_COMMENT_STYLE,
    ".svg": HTML_COMMENT_STYLE,
    ".md": HTML_COMMENT_STYLE,
    ".markdown": HTML_COMMENT_STYLE,
    ".sql": DASH_DASH_COMMENT_STYLE,
    ".lua": DASH_DASH_COMMENT_STYLE,
    ".hs": HASKELL_COMMENT_STYLE,
    ".erl": PERCENT_COMMENT_STYLE,
    ".hrl": PERCENT_COMMENT_STYLE,
    ".escript": PERCENT_COMMENT_STYLE,
    ".lisp": SEMICOLON_COMMENT_STYLE,
    ".el": SEMICOLON_COMMENT_STYLE,
    ".clj": SEMICOLON_COMMENT_STYLE,
    ".cljs": SEMICOLON_COMMENT_STYLE,
    ".scm": SEMICOLON_COMMENT_STYLE,
}


def comment_style_for_suffix(file_suffix: str) -> CommentStyle | None:
    """Return the comment style registered for ``file_suffix``, if any.

    Parameters:
        file_suffix: The suffix including the leading dot, for example
            ``".py"``. Case is preserved for the rare languages that distinguish
            it (``.R`` vs ``.r`` both map to hash comments, so either works).

    Returns:
        The matching ``CommentStyle``, or ``None`` when the suffix is unknown
        or empty.

    Behavior:
        Lookup is tried first with the suffix as given, then in lowercase.
        That lets ``.PY`` still resolve without treating every mapping as
        case-insensitive, which would collapse the two ``.R``/``.r`` keys
        needlessly. Unknown suffixes return ``None`` instead of a default
        style so binary or generated files are not scanned by accident.
    """

    if not file_suffix:
        return None
    exact_match = _SUFFIX_TO_COMMENT_STYLE.get(file_suffix)
    if exact_match is not None:
        return exact_match
    return _SUFFIX_TO_COMMENT_STYLE.get(file_suffix.lower())


def _describe_delimiters(comment_style: CommentStyle) -> str:
    """Summarize a style's delimiters as ``line '#'`` / ``block '/*' ... '*/'``."""

    delimiter_parts: list[str] = []
    if comment_style.line_prefix is not None:
        delimiter_parts.append(f"line {comment_style.line_prefix!r}")
    if comment_style.block_start is not None and comment_style.block_end is not None:
        delimiter_parts.append(
            f"block {comment_style.block_start!r} ... {comment_style.block_end!r}"
        )
    return ", ".join(delimiter_parts)


def format_comment_style_listing() -> str:
    """Render every registered suffix with its comment style, one per line.

    Parameters:
        None. The listing is built from the same private mapping that
        ``comment_style_for_suffix`` reads, so it cannot disagree with what
        the scanner actually does (unlike a hand-maintained docs table).

    Returns:
        A newline-terminated string with three aligned columns: suffix, style
        name, and a delimiter summary such as
        ``.c        c-style      line '//', block '/*' ... '*/'``.

    Behavior:
        Rows are sorted case-insensitively by suffix, with the exact suffix
        as a tie-break, so ``.R`` and ``.r`` sit next to each other in a
        stable order. Delimiters are shown with ``repr`` quoting because some
        of them (``--``, ``;``) are easy to misread when printed bare. Column
        widths come from the longest value, so adding a long suffix later
        does not break alignment.
    """

    ordered_suffixes = sorted(
        _SUFFIX_TO_COMMENT_STYLE, key=lambda suffix: (suffix.lower(), suffix)
    )
    suffix_width = max(len(suffix) for suffix in ordered_suffixes)
    style_name_width = max(
        len(comment_style.style_name)
        for comment_style in _SUFFIX_TO_COMMENT_STYLE.values()
    )
    listing_lines = []
    for suffix in ordered_suffixes:
        comment_style = _SUFFIX_TO_COMMENT_STYLE[suffix]
        listing_lines.append(
            f"{suffix.ljust(suffix_width)}  "
            f"{comment_style.style_name.ljust(style_name_width)}  "
            f"{_describe_delimiters(comment_style)}"
        )
    return "\n".join(listing_lines) + "\n"
