"""Tests for single-file scanning, including skip rules and URL false positives."""

from pathlib import Path

from todo_scan.scanner import scan_source_file


def test_scan_source_file_finds_hash_and_end_of_line_comments(tmp_path: Path) -> None:
    """A Python file should report both a full-line reminder and a trailing one."""

    source_file = tmp_path / "sample.py"
    source_file.write_text(
        "value = 1  # TODO: tighten this later\n"
        "# FIXME handle empty input\n",
        encoding="utf-8",
    )

    matches = scan_source_file(source_file)
    tags_and_messages = [(match.tag, match.message, match.line_number) for match in matches]
    assert tags_and_messages == [
        ("TODO", "tighten this later", 1),
        ("FIXME", "handle empty input", 2),
    ]
    assert all(match.comment_style == "hash" for match in matches)


def test_scan_source_file_ignores_todo_inside_a_url(tmp_path: Path) -> None:
    """``https://`` must not be treated as a slash-slash comment starter."""

    source_file = tmp_path / "sample.c"
    source_file.write_text(
        'const char *endpoint = "https://TODO.example";\n',
        encoding="utf-8",
    )

    assert scan_source_file(source_file) == []


def test_scan_source_file_reads_tags_inside_block_comments(tmp_path: Path) -> None:
    """A tag may sit on the opener line, a middle line, or beside a closer."""

    source_file = tmp_path / "sample.c"
    source_file.write_text(
        "/* FIXME: wrap the allocator */\n"
        "int ready = 1;\n"
        "/*\n"
        " * TODO split this module\n"
        " */\n",
        encoding="utf-8",
    )

    matches = scan_source_file(source_file)
    tags_and_lines = [(match.tag, match.line_number, match.message) for match in matches]
    assert tags_and_lines == [
        ("FIXME", 1, "wrap the allocator"),
        ("TODO", 4, "split this module"),
    ]


def test_scan_source_file_skips_binary_and_undecodable_files(tmp_path: Path) -> None:
    """A NUL probe or a UTF-8 failure should skip the file, not raise."""

    binary_file = tmp_path / "blob.dat"
    # Give it a C suffix so a missing skip would actually try to scan it.
    binary_as_source = tmp_path / "blob.c"
    binary_as_source.write_bytes(b"int x = 1; // TODO never read\n\x00\xff")

    undecodable = tmp_path / "latin1.c"
    undecodable.write_bytes(b"int x = 1; // TODO caf\xe9\n")

    assert scan_source_file(binary_as_source) == []
    assert scan_source_file(undecodable) == []
    assert scan_source_file(binary_file) == []
