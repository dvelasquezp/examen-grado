"""Entidad de materia."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class Subject:
    id: UUID | None
    slug: str
    name: str
    folder_path: str
    is_active: bool = True
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def slugify(name: str) -> str:
        import re
        import unicodedata

        normalized = unicodedata.normalize("NFKD", name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name.lower()).strip("-")
        return slug or "materia"
