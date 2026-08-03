"""Áreas temáticas de una materia, derivadas de los apuntes."""

import re
import unicodedata
from dataclasses import dataclass

# Los apuntes siguen el patrón "(4) Bienes (v06-2025).pdf": el número marca el
# orden del temario y el texto intermedio es el nombre del área. El sufijo final
# entre paréntesis es la versión del apunte ("(v2023)", "(01.2025)") y se omite.
_VERSION_SUFFIX = r"\(\s*(?:v[\d.\-/\s]*|[\d.\-/\s]+)\)"
_FILENAME_PATTERN = re.compile(
    rf"^\((?P<order>\d+)\)\s*(?P<name>.+?)\s*(?:{_VERSION_SUFFIX})?\s*\.\w+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SubjectArea:
    order: int
    name: str


def parse_area(filename: str) -> SubjectArea | None:
    """Extrae el área desde el nombre del apunte. None si no sigue el patrón."""
    # Los PDF traen las tildes descompuestas (NFD); sin normalizar, el nombre
    # del área no coincidiría con el que envía el navegador al filtrar.
    normalized = unicodedata.normalize("NFC", filename.strip())
    match = _FILENAME_PATTERN.match(normalized)
    if not match:
        return None
    name = match.group("name").strip()
    if not name:
        return None
    return SubjectArea(order=int(match.group("order")), name=name)
