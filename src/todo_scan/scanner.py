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
