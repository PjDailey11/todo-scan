"""Run the file scanner across every source file in a project tree."""

from __future__ import annotations

from pathlib import Path

from todo_scan.directory_walker import filter_files_by_suffix, iter_source_files
from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS
from todo_scan.scanner import scan_source_file
from todo_scan.tagged_comment import TaggedComment


def scan_project_tree(
    project_root: Path,
    recognized_tags: frozenset[str] | None = None,
    excluded_directory_names: frozenset[str] | None = None,
    included_suffixes: frozenset[str] | None = None,
) -> list[TaggedComment]:
    """Scan ``project_root`` and return every tagged comment in walk order.

    Parameters:
        project_root: Project directory, or a single file, passed through to
            the directory walker.
        recognized_tags: Uppercase tag allow-list forwarded to the file
            scanner. Defaults to ``DEFAULT_RECOGNIZED_TAGS``.
        excluded_directory_names: Directory basenames the walker should skip.
        included_suffixes: Optional suffix allow-list applied after the walk.
            When omitted, every file is passed to the scanner, which itself
            skips suffixes it does not recognize.

    Returns:
        A list of matches, grouped by the walker's sorted file order and then
        by line number within each file.

    Behavior:
        This function is the library-level entry point the CLI should call so
        walking, filtering, and scanning stay consistent for tests and for
        any future wrapper. An empty result means "no tags found or no
        scannable files," not an error.
    """

    tags_to_find = recognized_tags if recognized_tags is not None else DEFAULT_RECOGNIZED_TAGS
    discovered_files = iter_source_files(
        project_root,
        excluded_directory_names=excluded_directory_names,
    )
    files_to_scan = filter_files_by_suffix(discovered_files, included_suffixes)

    collected_matches: list[TaggedComment] = []
    for source_path in files_to_scan:
        collected_matches.extend(
            scan_source_file(source_path, recognized_tags=tags_to_find)
        )
    return collected_matches
