"""Utilidades de trazabilidad legal."""

from uuid import UUID

from src.domain.catalog.enums import DocumentType, SourceRole


def build_provenance(
    *,
    text: str,
    source_document: str,
    document_type: DocumentType,
    source_role: SourceRole,
    page: int | None,
    chunk_id: UUID | None,
    extraction_method: str,
    confidence: float,
) -> dict:
    display_label = _display_label(document_type, source_role, extraction_method)
    return {
        "statements": [
            {
                "text": text,
                "origin": {
                    "source_document": source_document,
                    "source_type": document_type.value,
                    "source_role": source_role.value,
                    "page": page,
                    "chunk_id": str(chunk_id) if chunk_id else None,
                    "extraction_method": extraction_method,
                    "confidence": confidence,
                },
                "display_label": display_label,
            }
        ],
        "generated_by": None,
        "verified_against": [str(chunk_id)] if chunk_id else [],
    }


def _display_label(
    document_type: DocumentType,
    source_role: SourceRole,
    extraction_method: str,
) -> str:
    if source_role == SourceRole.EXAM_PATTERN_ONLY:
        return "Patrón de examen oral histórico"
    if extraction_method == "GENERATED":
        return "Generado por IA"
    labels = {
        DocumentType.FLASHCARDS: "Definición extraída de Flashcards PDF",
        DocumentType.LECTURE_NOTES: "Explicación extraída de Apuntes",
        DocumentType.OFFICIAL_SYLLABUS: "Extraído del Cedulario oficial",
    }
    return labels.get(document_type, "Extraído de fuente doctrinal")


def build_link_provenance(
    *,
    excerpt: str,
    source_document: str,
    document_type: DocumentType,
    source_role: SourceRole,
    page: int | None,
    chunk_id: UUID | None,
    match_type: str,
    relevance: float,
    concept_title: str,
) -> dict:
    return {
        "statements": [
            {
                "text": excerpt,
                "origin": {
                    "source_document": source_document,
                    "source_type": document_type.value,
                    "source_role": source_role.value,
                    "page": page,
                    "chunk_id": str(chunk_id) if chunk_id else None,
                    "match_type": match_type,
                    "relevance": relevance,
                    "concept_title": concept_title,
                },
                "display_label": "Mención en Apuntes",
            }
        ],
        "generated_by": None,
        "verified_against": [str(chunk_id)] if chunk_id else [],
    }
