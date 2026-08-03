"""Sincronización de conceptos con Neo4j."""

from uuid import UUID

from src.infrastructure.persistence.neo4j.client import neo4j_client


class ConceptGraphSync:
    async def upsert_concept(
        self,
        *,
        concept_id: UUID,
        title: str,
        slug: str,
        subject_slug: str,
        subtopic: str | None,
        confidence: float,
    ) -> None:
        query = """
        MERGE (s:Subject {slug: $subject_slug})
        MERGE (c:Concept {id: $concept_id})
        SET c.title = $title,
            c.slug = $slug,
            c.subject_slug = $subject_slug,
            c.subtopic = $subtopic,
            c.confidence_score = $confidence
        MERGE (c)-[:PART_OF]->(s)
        """
        async with neo4j_client._driver.session() as session:
            await session.run(
                query,
                concept_id=str(concept_id),
                title=title,
                slug=slug,
                subject_slug=subject_slug,
                subtopic=subtopic or "",
                confidence=confidence,
            )

    async def link_related(self, concept_id_a: UUID, concept_id_b: UUID, explanation: str) -> None:
        query = """
        MATCH (a:Concept {id: $id_a}), (b:Concept {id: $id_b})
        MERGE (a)-[r:RELATED_TO]->(b)
        SET r.explanation = $explanation
        """
        async with neo4j_client._driver.session() as session:
            await session.run(
                query,
                id_a=str(concept_id_a),
                id_b=str(concept_id_b),
                explanation=explanation,
            )

    async def link_chunk_mention(
        self,
        *,
        concept_id: UUID,
        chunk_id: UUID,
        document_filename: str,
        relevance: float,
    ) -> None:
        query = """
        MERGE (c:Concept {id: $concept_id})
        MERGE (ch:Chunk {id: $chunk_id})
        SET ch.document = $document_filename
        MERGE (c)-[r:MENTIONED_IN]->(ch)
        SET r.relevance = $relevance
        """
        async with neo4j_client._driver.session() as session:
            await session.run(
                query,
                concept_id=str(concept_id),
                chunk_id=str(chunk_id),
                document_filename=document_filename,
                relevance=relevance,
            )
