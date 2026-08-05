"""Router de estudio: repaso, simulacro, mapa, juegos."""

import asyncio

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.study.example_generator import ExampleGenerator
from src.application.study.fill_blank_generator import FillBlankGenerator
from src.application.study.graph_service import GraphService
from src.application.study.logic_exercise_generator import LogicExerciseGenerator
from src.application.study.oral_exam_service import OralExamService
from src.application.study.progress_service import ProgressService
from src.application.study.question_generator import QuestionGenerator
from src.config.settings import Settings, get_settings
from src.infrastructure.ai.stt_service import transcribe_audio
from src.infrastructure.persistence.postgres.database import get_db_session
from src.infrastructure.persistence.postgres.models import SubjectModel
from src.presentation.v1.study_schemas import (
    ConceptExamplesResponse,
    FillBlankCheckRequest,
    FillBlankCheckResponse,
    FillBlankExerciseResponse,
    FlashcardCategoryResponse,
    FlashcardResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    GenerateExamplesRequest,
    GenerateExamplesResponse,
    GenerateQuestionsResponse,
    GraphResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    LogicCheckRequest,
    LogicCheckResponse,
    LogicExerciseResponse,
    LogicOptionResponse,
    MatchingPairResponse,
    OralExamAnswerRequest,
    OralExamAnswerResponse,
    OralExamStartResponse,
    SubjectProgressResponse,
    TranscribeResponse,
)

router = APIRouter(tags=["Estudio"])


@router.get("/subjects/{slug}/progress", response_model=SubjectProgressResponse)
async def subject_progress(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    stats = await ProgressService(session).get_subject_stats(subject.id)
    return SubjectProgressResponse(**stats)


@router.get(
    "/subjects/{slug}/flashcards/categories",
    response_model=list[FlashcardCategoryResponse],
)
async def flashcard_categories(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    categories = await ProgressService(session).get_categories(subject.id)
    return [FlashcardCategoryResponse(**category) for category in categories]


@router.get("/subjects/{slug}/flashcards/next", response_model=FlashcardResponse | None)
async def next_flashcard(
    slug: str,
    category: str | None = Query(default=None, description="Área del temario a repasar"),
    session: AsyncSession = Depends(get_db_session),
):
    subject = await _get_subject(session, slug)
    concept = await ProgressService(session).get_next_flashcard(subject.id, category)
    if not concept:
        return None
    return FlashcardResponse(
        concept_id=concept.id,
        title=concept.title,
        slug=concept.slug,
        definition=concept.definition,
        subtopic=concept.subtopic,
    )


@router.post(
    "/subjects/{slug}/flashcards/{concept_id}/review",
    response_model=FlashcardReviewResponse,
)
async def review_flashcard(
    slug: str,
    concept_id: UUID,
    body: FlashcardReviewRequest,
    session: AsyncSession = Depends(get_db_session),
):
    await _get_subject(session, slug)
    prog = await ProgressService(session).record_review(concept_id, body.quality)
    return FlashcardReviewResponse(
        concept_id=concept_id,
        mastery_score=prog.mastery_score,
        next_review_days=prog.interval_days,
    )


@router.post("/subjects/{slug}/questions/generate", response_model=GenerateQuestionsResponse)
async def generate_questions(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    created = await QuestionGenerator(session).ensure_questions_for_subject(subject.id)
    return GenerateQuestionsResponse(created=created)


@router.post(
    "/subjects/{slug}/examples/generate",
    response_model=GenerateExamplesResponse,
)
async def generate_examples(
    slug: str,
    body: GenerateExamplesRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    await _get_subject(session, slug)
    req = body or GenerateExamplesRequest()
    try:
        result = await ExampleGenerator(session, settings).generate_for_subject(
            slug, limit=req.limit, force=req.force
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return GenerateExamplesResponse(
        subject_slug=result.subject_slug,
        requested=result.requested,
        generated=result.generated,
        failed=result.failed,
        examples=result.examples,
    )


@router.post(
    "/subjects/{slug}/concepts/{concept_id}/examples/generate",
    response_model=ConceptExamplesResponse,
)
async def generate_concept_examples(
    slug: str,
    concept_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    await _get_subject(session, slug)
    try:
        result = await ExampleGenerator(session, settings).generate_for_concept(concept_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return ConceptExamplesResponse(**result)


@router.post("/subjects/{slug}/oral-exam/start", response_model=OralExamStartResponse)
async def start_oral_exam(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    result = await OralExamService(session).start_session(subject.id)
    return OralExamStartResponse(**result)


@router.post("/subjects/{slug}/oral-exam/{session_id}/answer", response_model=OralExamAnswerResponse)
async def oral_exam_answer(
    slug: str,
    session_id: UUID,
    body: OralExamAnswerRequest,
    session: AsyncSession = Depends(get_db_session),
):
    await _get_subject(session, slug)
    try:
        result = await OralExamService(session).submit_answer(session_id, body.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return OralExamAnswerResponse(**result)


@router.get("/subjects/{slug}/graph", response_model=GraphResponse)
async def concept_graph(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    data = await GraphService(session).get_subject_graph(subject.id)
    return GraphResponse(
        nodes=[GraphNodeResponse(**n) for n in data["nodes"]],
        edges=[GraphEdgeResponse(**e) for e in data["edges"]],
    )


@router.get("/subjects/{slug}/games/matching", response_model=list[MatchingPairResponse])
async def matching_game(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    pairs = await GraphService(session).get_matching_game_pairs(subject.id)
    return [MatchingPairResponse(**p) for p in pairs]


@router.get("/subjects/{slug}/games/fill-blank", response_model=list[FillBlankExerciseResponse])
async def fill_blank_game(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    exercises = await FillBlankGenerator(session).get_exercises(subject.id)
    return [FillBlankExerciseResponse(**e) for e in exercises]


@router.post("/subjects/{slug}/games/fill-blank/check", response_model=FillBlankCheckResponse)
async def fill_blank_check(slug: str, body: FillBlankCheckRequest):
    await _noop_subject(slug)
    result = FillBlankGenerator.check_answer(body.expected, body.answer)
    return FillBlankCheckResponse(**result)


@router.get("/subjects/{slug}/games/logic", response_model=list[LogicExerciseResponse])
async def logic_exercises(slug: str, session: AsyncSession = Depends(get_db_session)):
    subject = await _get_subject(session, slug)
    exercises = await LogicExerciseGenerator(session).get_exercises(subject.id)
    return [
        LogicExerciseResponse(
            id=e["id"],
            kind=e["kind"],
            context=e["context"],
            question=e["question"],
            concept_a=e["concept_a"],
            concept_b=e["concept_b"],
            options=[LogicOptionResponse(**o) for o in e["options"]],
            correct_option=e["correct_option"],
            explanation=e["explanation"],
        )
        for e in exercises
    ]


@router.post("/subjects/{slug}/games/logic/check", response_model=LogicCheckResponse)
async def logic_check(slug: str, body: LogicCheckRequest):
    await _noop_subject(slug)
    correct = LogicExerciseGenerator.check_answer(body.correct_option, body.selected_option)
    explanation = body.explanation if body.explanation else None
    if not correct and not explanation:
        explanation = f"La respuesta correcta era otra opción."
    return LogicCheckResponse(correct=correct, explanation=explanation)


@router.post("/subjects/{slug}/oral-exam/transcribe", response_model=TranscribeResponse)
async def transcribe_oral_audio(
    slug: str,
    audio: UploadFile = File(...),
):
    await _noop_subject(slug)
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo de audio vacío")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio demasiado grande (máx. 15 MB)")
    try:
        result = await asyncio.to_thread(transcribe_audio, data, audio.filename or "audio.webm")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return TranscribeResponse(**result)


async def _get_subject(session: AsyncSession, slug: str) -> SubjectModel:
    result = await session.execute(select(SubjectModel).where(SubjectModel.slug == slug))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    return subject


async def _noop_subject(slug: str) -> None:
    if not slug.strip():
        raise HTTPException(status_code=404, detail="Materia no encontrada")
