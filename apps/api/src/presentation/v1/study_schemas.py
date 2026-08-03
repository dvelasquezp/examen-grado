"""Esquemas de estudio, repaso y simulacro."""

from uuid import UUID

from pydantic import BaseModel, Field


class SubjectProgressResponse(BaseModel):
    concepts_total: int
    concepts_with_notes: int
    cards_reviewed: int
    cards_due: int
    concepts_mastered: int
    readiness_score: float
    retention_score: float
    streak_days: int


class FlashcardResponse(BaseModel):
    concept_id: UUID
    title: str
    slug: str
    definition: str | None
    subtopic: str | None


class FlashcardCategoryResponse(BaseModel):
    name: str
    concept_count: int


class FlashcardReviewRequest(BaseModel):
    quality: int = Field(ge=0, le=5, description="0=olvidé, 3=bien, 5=fácil")


class FlashcardReviewResponse(BaseModel):
    concept_id: UUID
    mastery_score: float
    next_review_days: int


class OralExamStartResponse(BaseModel):
    session_id: UUID
    question: str | None
    concept_id: UUID | None = None
    concept_title: str | None = None
    model_answer_hint: str | None = None
    done: bool = False


class OralExamAnswerRequest(BaseModel):
    answer: str


class OralExamAnswerResponse(BaseModel):
    status: str
    evaluation: dict | None = None
    question: str | None = None
    concept_id: UUID | None = None
    concept_title: str | None = None
    model_answer_hint: str | None = None
    done: bool = False
    transcript: list | None = None


class GraphNodeResponse(BaseModel):
    id: str
    title: str
    slug: str
    subtopic: str | None
    link_count: int


class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    weight: int
    type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class MatchingPairResponse(BaseModel):
    concept_id: str
    title: str
    definition: str


class GenerateQuestionsResponse(BaseModel):
    created: int


class TranscribeResponse(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None


class FillBlankExerciseResponse(BaseModel):
    id: str
    prompt: str
    sentence: str
    answer: str
    concept_id: str
    concept_title: str
    chunk_id: str
    source: str


class FillBlankCheckRequest(BaseModel):
    exercise_id: str
    answer: str
    expected: str


class FillBlankCheckResponse(BaseModel):
    correct: bool
    expected: str


class LogicOptionResponse(BaseModel):
    id: str
    label: str


class LogicExerciseResponse(BaseModel):
    id: str
    kind: str
    context: str
    question: str
    concept_a: str
    concept_b: str
    options: list[LogicOptionResponse]
    correct_option: str
    explanation: str


class LogicCheckRequest(BaseModel):
    exercise_id: str
    selected_option: str
    correct_option: str
    explanation: str | None = None


class LogicCheckResponse(BaseModel):
    correct: bool
    explanation: str | None = None
