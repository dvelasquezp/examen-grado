"""Tests del normalizador."""

from src.infrastructure.documents.normalizer import normalize_text, normalize_for_hash, estimate_tokens


def test_normalize_whitespace():
    assert normalize_text("  hello   world  ") == "hello world"


def test_sanitize_nul_bytes():
    from src.infrastructure.documents.normalizer import sanitize_text

    assert "\x00" not in sanitize_text("acto\x00jurídico")
    assert sanitize_text("acto\x00jurídico") == "actojurídico"


def test_normalize_line_breaks():
    assert "acto" in normalize_text("ac-\nto jurídico")


def test_hash_normalization_lowercase():
    assert normalize_for_hash("ÁCTO") == normalize_for_hash("acto")


def test_estimate_tokens():
    assert estimate_tokens("one two three") == 3
