"""Fusión de candidatos a conceptos."""

import re
from difflib import SequenceMatcher

from src.domain.knowledge.concept import Concept
from src.infrastructure.knowledge.rule_extractor import ExtractedConceptCandidate


class ConceptMerger:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def merge_candidates(
        self,
        candidates: list[ExtractedConceptCandidate],
        existing: list[Concept],
    ) -> tuple[list[Concept], list[ExtractedConceptCandidate]]:
        """Agrupa candidatos nuevos y existentes por similitud de título."""
        concepts_by_slug: dict[str, Concept] = {c.slug: c for c in existing}
        unmatched: list[ExtractedConceptCandidate] = []

        for candidate in candidates:
            slug = Concept.slugify(candidate.title)
            concept = concepts_by_slug.get(slug)

            if concept is None:
                concept = self._find_similar(candidate.title, list(concepts_by_slug.values()))
                if concept:
                    slug = concept.slug

            if concept is None:
                unmatched.append(candidate)
            else:
                concepts_by_slug[concept.slug] = concept

        new_concepts: list[Concept] = []
        for candidate in unmatched:
            slug = Concept.slugify(candidate.title)
            if slug in concepts_by_slug:
                continue
            concept = Concept(
                id=None,
                subject_id=candidate.document_id,  # placeholder, set by use case
                slug=slug,
                title=candidate.title,
                subtopic=candidate.subtopic,
                confidence_score=candidate.confidence,
            )
            concepts_by_slug[slug] = concept
            new_concepts.append(concept)

        return new_concepts, candidates

    def find_matching_concept(self, title: str, concepts: list[Concept]) -> Concept | None:
        slug = Concept.slugify(title)
        for c in concepts:
            if c.slug == slug:
                return c
        return self._find_similar(title, concepts)

    def _find_similar(self, title: str, concepts: list[Concept]) -> Concept | None:
        normalized = self._normalize(title)
        best: Concept | None = None
        best_score = 0.0
        for concept in concepts:
            score = SequenceMatcher(None, normalized, self._normalize(concept.title)).ratio()
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best = concept
        return best

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text
