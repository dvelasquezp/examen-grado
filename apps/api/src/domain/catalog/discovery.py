"""Servicio de descubrimiento de materias y documentos."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import Settings
from src.domain.catalog.classifier import DocumentClassifier
from src.domain.catalog.document import Document
from src.domain.catalog.enums import DocumentType
from src.domain.catalog.subject import Subject


@dataclass
class DiscoveredDocument:
    document: Document
    subject: Subject | None
    is_global: bool


@dataclass
class DiscoveryResult:
    subjects: list[Subject]
    documents: list[DiscoveredDocument]
    scanned_paths: int
    skipped_paths: int


class SubjectDiscoveryService:
    """Escanea el filesystem y descubre materias y documentos."""

    def __init__(self, settings: Settings, classifier: DocumentClassifier | None = None):
        self.settings = settings
        self.classifier = classifier or DocumentClassifier()
        self.content_root = Path(settings.content_path).resolve()

    def discover(self) -> DiscoveryResult:
        subjects: dict[str, Subject] = {}
        documents: list[DiscoveredDocument] = []
        scanned = 0
        skipped = 0

        if not self.content_root.exists():
            return DiscoveryResult([], [], 0, 0)

        for item in sorted(self.content_root.iterdir()):
            if not item.is_dir() or item.name in self.settings.exclude_dirs or item.name.startswith("."):
                continue

            subject = Subject(
                id=None,
                slug=Subject.slugify(item.name),
                name=item.name,
                folder_path=str(item.relative_to(self.content_root)),
            )
            subjects[subject.slug] = subject

            for filepath in self._walk_subject(item):
                scanned += 1
                classification = self.classifier.classify(filepath, self.content_root)
                if classification is None:
                    skipped += 1
                    continue

                doc_type, source_role, is_global = classification
                file_hash = self._compute_hash(filepath)
                file_size = filepath.stat().st_size

                doc = Document(
                    id=None,
                    subject_id=None,
                    filename=filepath.name,
                    filepath=str(filepath.relative_to(self.content_root)),
                    document_type=doc_type,
                    source_role=source_role,
                    file_hash=file_hash,
                    file_size=file_size,
                )

                documents.append(
                    DiscoveredDocument(
                        document=doc,
                        subject=None if is_global else subject,
                        is_global=is_global,
                    )
                )

        global_docs = self._discover_global_documents()
        for gd in global_docs:
            scanned += 1
            documents.append(gd)

        return DiscoveryResult(
            subjects=list(subjects.values()),
            documents=documents,
            scanned_paths=scanned,
            skipped_paths=skipped,
        )

    def _discover_global_documents(self) -> list[DiscoveredDocument]:
        results: list[DiscoveredDocument] = []
        for filepath in self.content_root.glob("Cedulario*.pdf"):
            classification = self.classifier.classify(filepath, self.content_root)
            if classification is None:
                continue
            doc_type, source_role, is_global = classification
            results.append(
                DiscoveredDocument(
                    document=Document(
                        id=None,
                        subject_id=None,
                        filename=filepath.name,
                        filepath=str(filepath.relative_to(self.content_root)),
                        document_type=doc_type,
                        source_role=source_role,
                        file_hash=self._compute_hash(filepath),
                        file_size=filepath.stat().st_size,
                    ),
                    subject=None,
                    is_global=is_global,
                )
            )
        return results

    def _walk_subject(self, subject_dir: Path):
        for filepath in subject_dir.rglob("*"):
            if filepath.is_file() and self.classifier.is_supported(filepath):
                yield filepath

    @staticmethod
    def _compute_hash(filepath: Path) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
