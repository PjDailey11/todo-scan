"""Find recognized tags inside the comments of a single source file."""

from __future__ import annotations

from pathlib import Path

# One mebibyte is large enough for ordinary source and small enough to skip
# minified bundles, lockfiles, and accidental binary drops without reading them
# fully into memory.
DEFAULT_MAX_SOURCE_FILE_BYTES = 1_048_576

# A NUL in the first chunk is the usual "this is not text" signal used by
# tools such as grep. We only sample the head of the file so a large asset is
# rejected quickly.
BINARY_PROBE_BYTE_COUNT = 8192


def looks_like_binary_file(source_path: Path) -> bool:
    """Return whether ``source_path`` appears to be a binary file, not source text.

    Parameters:
        source_path: File to probe. The file is opened in binary mode and only
            the first ``BINARY_PROBE_BYTE_COUNT`` bytes are read.

    Returns:
        ``True`` if a NUL byte is present in the probed prefix, which is a
        reliable sign of images, compiled objects, and similar non-text files.
        ``False`` if the prefix is NUL-free or the file is empty.

    Behavior:
        An unreadable file raises the underlying ``OSError``. The caller is
        expected to treat that as "skip this path" rather than aborting a
        whole-tree scan. Empty files are treated as text so a placeholder
        module does not get flagged as binary.
    """

    with source_path.open("rb") as binary_file:
        probed_prefix = binary_file.read(BINARY_PROBE_BYTE_COUNT)
    return b"\x00" in probed_prefix


def is_oversized_source_file(
    source_path: Path,
    size_limit_bytes: int = DEFAULT_MAX_SOURCE_FILE_BYTES,
) -> bool:
    """Return whether ``source_path`` is larger than the scan size limit.

    Parameters:
        source_path: File whose size will be checked with ``stat``.
        size_limit_bytes: Maximum allowed size in bytes. The default skips
            files over one mebibyte.

    Returns:
        ``True`` when the file's size is strictly greater than
        ``size_limit_bytes``.

    Behavior:
        Size is checked before the file is decoded so a multi-megabyte
        generated bundle does not pay a UTF-8 decode cost. Equality with the
        limit is allowed; only files that overflow it are skipped.
    """

    return source_path.stat().st_size > size_limit_bytes


def find_line_comment_start(line_text: str, line_prefix: str) -> int:
    """Return the index of a real line-comment prefix, or ``-1`` if none exists.

    Parameters:
        line_text: The raw source line, without its newline.
        line_prefix: The delimiter to search for, such as ``#`` or ``//``.

    Returns:
        The character index of the first prefix that should be treated as a
        comment starter, or ``-1`` when the line has none.

    Behavior:
        A bare ``str.find`` would treat the ``//`` in ``https://example`` as a
        C++ comment and then report a tag inside the URL. When the prefix is
        ``//``, a match immediately preceded by ``:`` is skipped and the search
        continues. Other prefixes are taken at their first occurrence; skipping
        string literals would require a full lexer, which this tool deliberately
        does not implement.
    """

    search_from = 0
    while True:
        prefix_index = line_text.find(line_prefix, search_from)
        if prefix_index < 0:
            return -1
        if line_prefix == "//" and prefix_index > 0 and line_text[prefix_index - 1] == ":":
            search_from = prefix_index + len(line_prefix)
            continue
        return prefix_index


from re import Pattern

from todo_scan.recognized_tags import normalize_tag
from todo_scan.tagged_comment import TaggedComment


def extract_tagged_comments_from_text(
    comment_text: str,
    source_path: Path,
    line_number: int,
    comment_style_name: str,
    tag_search_pattern: Pattern[str],
) -> list[TaggedComment]:
    """Return every recognized tag found in already-extracted comment text.

    Parameters:
        comment_text: The comment body only, with delimiters already stripped
            or at least with the line-comment prefix removed. Trailing block
            closers such as ``*/`` may still be present and are trimmed from
            the captured message.
        source_path: File the comment came from, stored on each match.
        line_number: 1-based line of this comment text.
        comment_style_name: Style identifier recorded on each match.
        tag_search_pattern: Pattern built by ``build_tag_search_pattern``.

    Returns:
        A list of ``TaggedComment`` values, one per tag match, in left-to-right
        order. The list is empty when the comment has no recognized tag.

    Behavior:
        Only the first tag on a line is recorded. A comment such as
        ``TODO: fix this FIXME later`` is almost always one reminder, and
        reporting both tags would double-count it in summaries. The captured
        message has trailing ``*/`` or ``-->`` removed so block-comment closers
        do not show up in the report.
    """

    pattern_match = tag_search_pattern.search(comment_text)
    if pattern_match is None:
        return []

    raw_tag, raw_message = pattern_match.group(1), pattern_match.group(2)
    cleaned_message = raw_message.strip()
    for block_closer in ("*/", "-->"):
        if cleaned_message.endswith(block_closer):
            cleaned_message = cleaned_message[: -len(block_closer)].rstrip()

    return [
        TaggedComment(
            source_path=source_path,
            line_number=line_number,
            tag=normalize_tag(raw_tag),
            message=cleaned_message,
            comment_style=comment_style_name,
        )
    ]


from todo_scan.comment_styles import CommentStyle, comment_style_for_suffix
from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS
from todo_scan.tag_pattern import build_tag_search_pattern


def scan_source_file(
    source_path: Path,
    recognized_tags: frozenset[str] | None = None,
    comment_style: CommentStyle | None = None,
    size_limit_bytes: int = DEFAULT_MAX_SOURCE_FILE_BYTES,
) -> list[TaggedComment]:
    """Return tagged comments found in ``source_path``.

    Parameters:
        source_path: File to read. The suffix selects a comment style when
            ``comment_style`` is omitted.
        recognized_tags: Tag allow-list, already normalized to uppercase. When
            omitted, ``DEFAULT_RECOGNIZED_TAGS`` is used.
        comment_style: Delimiters to apply. When omitted, the style is chosen
            from the file suffix; if that lookup fails, the file is skipped.
        size_limit_bytes: Maximum file size to decode; larger files are skipped.

    Returns:
        Matches in file order. The list is empty when the file is skipped
        (unknown suffix, binary, oversized, undecodable, or unreadable) or when
        it simply contains no recognized tags.

    Behavior:
        This is a heuristic scan, not a language parser. Tags inside string
        literals can still match when a comment delimiter also appears in the
        string. Block comments follow C rules: the first closer ends the block,
        and blocks do not nest. Lines are decoded as UTF-8; a decode error
        skips the file rather than inserting replacement characters that could
        fabricate a tag. Unreadable files are skipped for the same reason a
        tree walk should survive a single permission error.
    """

    tags_to_find = recognized_tags if recognized_tags is not None else DEFAULT_RECOGNIZED_TAGS
    applied_style = comment_style or comment_style_for_suffix(source_path.suffix)
    if applied_style is None:
        return []

    try:
        if is_oversized_source_file(source_path, size_limit_bytes=size_limit_bytes):
            return []
        if looks_like_binary_file(source_path):
            return []
        source_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    tag_search_pattern = build_tag_search_pattern(tags_to_find)
    collected_matches: list[TaggedComment] = []
    inside_block_comment = False

    for line_index, raw_line in enumerate(source_text.splitlines(), start=1):
        line_matches, inside_block_comment = _scan_source_line(
            raw_line=raw_line,
            source_path=source_path,
            line_number=line_index,
            comment_style=applied_style,
            tag_search_pattern=tag_search_pattern,
            inside_block_comment=inside_block_comment,
        )
        collected_matches.extend(line_matches)

    return collected_matches


def _scan_source_line(
    raw_line: str,
    source_path: Path,
    line_number: int,
    comment_style: CommentStyle,
    tag_search_pattern: Pattern[str],
    inside_block_comment: bool,
) -> tuple[list[TaggedComment], bool]:
    """Scan one line, continuing a block comment if the previous line opened one.

    This helper is intentionally private: the state machine is an implementation
    detail of ``scan_source_file``. It returns both the matches and the updated
    block-comment flag so the caller can carry that flag to the next line.

    A line can legally contain code, then a block comment, then more code, then
    a line comment, so the function walks the line rather than assuming a single
    comment region.
    """

    matches: list[TaggedComment] = []
    cursor = 0
    line_length = len(raw_line)

    while cursor <= line_length:
        if inside_block_comment:
            if comment_style.block_end is None:
                # A style without a closer should never enter this branch; treat
                # the rest of the line as comment text and stay inside rather
                # than raising, so a bad test fixture cannot crash a scan.
                remainder = raw_line[cursor:]
                matches.extend(
                    extract_tagged_comments_from_text(
                        remainder,
                        source_path,
                        line_number,
                        comment_style.style_name,
                        tag_search_pattern,
                    )
                )
                return matches, True

            closer_index = raw_line.find(comment_style.block_end, cursor)
            if closer_index < 0:
                matches.extend(
                    extract_tagged_comments_from_text(
                        raw_line[cursor:],
                        source_path,
                        line_number,
                        comment_style.style_name,
                        tag_search_pattern,
                    )
                )
                return matches, True

            matches.extend(
                extract_tagged_comments_from_text(
                    raw_line[cursor:closer_index],
                    source_path,
                    line_number,
                    comment_style.style_name,
                    tag_search_pattern,
                )
            )
            cursor = closer_index + len(comment_style.block_end)
            inside_block_comment = False
            continue

        next_marker_index, marker_kind = _next_comment_marker(
            raw_line, cursor, comment_style
        )
        if next_marker_index is None:
            break

        if marker_kind == "line":
            assert comment_style.line_prefix is not None
            comment_body = raw_line[next_marker_index + len(comment_style.line_prefix) :]
            matches.extend(
                extract_tagged_comments_from_text(
                    comment_body,
                    source_path,
                    line_number,
                    comment_style.style_name,
                    tag_search_pattern,
                )
            )
            break

        assert comment_style.block_start is not None
        cursor = next_marker_index + len(comment_style.block_start)
        inside_block_comment = True

    return matches, inside_block_comment


def _next_comment_marker(
    raw_line: str,
    start_index: int,
    comment_style: CommentStyle,
) -> tuple[int | None, str | None]:
    """Return the earliest comment marker in ``raw_line`` at or after ``start_index``.

    The second item is ``"line"`` or ``"block"`` so the caller knows which
    delimiter won when both appear on the same line. Line markers still use
    ``find_line_comment_start`` so a URL's ``://`` is not treated as ``//``.
    """

    line_index: int | None = None
    if comment_style.line_prefix:
        found_at = find_line_comment_start(raw_line[start_index:], comment_style.line_prefix)
        if found_at >= 0:
            line_index = start_index + found_at

    block_index: int | None = None
    if comment_style.block_start:
        found_block = raw_line.find(comment_style.block_start, start_index)
        if found_block >= 0:
            block_index = found_block

    if line_index is None and block_index is None:
        return None, None
    if block_index is None or (line_index is not None and line_index <= block_index):
        return line_index, "line"
    return block_index, "block"
