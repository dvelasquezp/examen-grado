"""Cliente Neo4j."""

from neo4j import AsyncGraphDatabase

from src.config.settings import get_settings


class Neo4jClient:
    def __init__(self):
        settings = get_settings()
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def verify_connectivity(self) -> bool:
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS n")
                record = await result.single()
                return record is not None and record["n"] == 1
        except Exception:
            return False

    async def close(self) -> None:
        await self._driver.close()

    async def init_constraints(self) -> None:
        constraints = [
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT subject_slug IF NOT EXISTS FOR (s:Subject) REQUIRE s.slug IS UNIQUE",
        ]
        async with self._driver.session() as session:
            for constraint in constraints:
                await session.run(constraint)


neo4j_client = Neo4jClient()
