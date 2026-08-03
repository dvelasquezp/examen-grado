"""Normalización de texto legal."""

import re
import unicodedata

from unidecode import unidecode


def sanitize_text(text: str) -> str:
    """Elimina caracteres inválidos para PostgreSQL (NUL, controles)."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def normalize_text(text: str) -> str:
    text = sanitize_text(text)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_hash(text: str) -> str:
    normalized = normalize_text(text).lower()
    return unidecode(normalized)


def truncate_field(text: str | None, max_len: int = 500) -> str | None:
    """Trunca campos de metadata para límites de BD."""
    if text is None:
        return None
    text = normalize_text(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))
