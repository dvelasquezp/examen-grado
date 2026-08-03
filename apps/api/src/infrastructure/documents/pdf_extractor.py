"""Extractor de PDF con PyMuPDF."""

import re
from pathlib import Path

import fitz

from src.domain.ingestion.chunk import ExtractedBlock, ExtractedDocument
from src.infrastructure.documents.normalizer import sanitize_text

HEADING_PATTERN = re.compile(
    r"^("
    r"CAP[ÍI]TULO\s+[IVXLCDM\d]+"
    r"|SECCI[ÓO]N\s+[IVXLCDM\d]+"
    r"|\d+[\.\)]\s+[A-ZÁÉÍÓÚÑ]"
    r"|[IVXLCDM]+\.\s+"
    r")",
    re.IGNORECASE,
)


class PdfExtractor:
    def extract(self, filepath: Path) -> ExtractedDocument:
        doc = fitz.open(filepath)
        blocks: list[ExtractedBlock] = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_number = page_idx + 1
            text = sanitize_text(page.get_text("text"))
            if not text.strip():
                continue

            for paragraph in text.split("\n\n"):
                paragraph = paragraph.strip()
                if not paragraph or len(paragraph) < 3:
                    continue

                first_line = paragraph.split("\n")[0].strip()
                is_heading, heading_level = self._classify_heading(first_line, paragraph)

                block_text = paragraph
                if is_heading and len(paragraph) > len(first_line) + 30:
                    block_text = first_line

                blocks.append(
                    ExtractedBlock(
                        text=block_text,
                        page_number=page_number,
                        block_type="heading" if is_heading else "paragraph",
                        heading_level=heading_level if is_heading else None,
                    )
                )

        page_count = len(doc)
        doc.close()
        return ExtractedDocument(blocks=blocks, page_count=page_count)

    @staticmethod
    def _classify_heading(first_line: str, paragraph: str) -> tuple[bool, int | None]:
        if len(paragraph) > 400 or paragraph.count("\n") > 6:
            return False, None
        if HEADING_PATTERN.match(first_line):
            level = 1 if "CAP" in first_line.upper() else 2
            return True, level
        if (
            len(first_line) <= 120
            and first_line.isupper()
            and len(first_line.split()) <= 12
            and len(first_line) >= 3
        ):
            return True, 2
        return False, None
