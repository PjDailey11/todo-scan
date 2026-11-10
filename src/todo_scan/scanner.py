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
