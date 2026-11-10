"""Tests for tag normalization and default membership."""

from todo_scan.recognized_tags import DEFAULT_RECOGNIZED_TAGS, normalize_tag


def test_normalize_tag_strips_whitespace_and_uppercases() -> None:
    """CLI input like `` fixme `` should compare equal to the canonical token."""

    assert normalize_tag("  fixme ") == "FIXME"


def test_normalize_tag_preserves_custom_tokens() -> None:
    """Custom tags are allowed; normalization must not drop unknown names."""

    assert normalize_tag("wip") == "WIP"


def test_default_recognized_tags_use_uppercase_canonical_names() -> None:
    """Callers should be able to test membership without normalizing defaults."""

    assert DEFAULT_RECOGNIZED_TAGS == {"TODO", "FIXME", "HACK", "XXX", "NOTE"}
