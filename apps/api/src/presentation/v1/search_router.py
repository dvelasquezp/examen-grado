"""Router de búsqueda híbrida."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.search.hybrid_search import HybridSearchService
from src.config.settings import Settings, get_settings
from src.infrastructure.persistence.postgres.database import get_db_session
from src.infrastructure.persistence.postgres.models import SubjectModel
from src.presentation.v1.knowledge_schemas import ChunkSearchResult, SearchResponse, SearchResultItem

router = APIRouter(prefix="/search", tags=["Búsqueda"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2),
    subject: str | None = None,
    limit: int = Query(20, le=50),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    subject_id = None
    if subject:
        result = await session.execute(
            select(SubjectModel).where(SubjectModel.slug == subject)
        )
        subj = result.scalar_one_or_none()
        if subj:
            subject_id = subj.id

    service = HybridSearchService(session, settings)
    results = await service.search(q, subject_id=subject_id, limit=limit)

    return SearchResponse(
        query=results["query"],
        total=results["total"],
        concepts=[
            SearchResultItem(
                id=item["id"],
                title=item["title"],
                slug=item["slug"],
                definition=item.get("definition"),
                subtopic=item.get("subtopic"),
                score=item.get("score", 0.0),
                match_type=item.get("match_type", "keyword"),
                final_score=item.get("final_score"),
            )
            for item in results["concepts"]
        ],
        chunks=[
            ChunkSearchResult(**chunk) for chunk in results.get("chunks", [])
        ],
    )
