function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, "");
  }
  if (typeof window !== "undefined") {
    return "";
  }
  return (process.env.API_PROXY_TARGET || "http://localhost:8000").replace(/\/$/, "");
}

const API_BASE = resolveApiBase();
const API_URL = API_BASE ? `${API_BASE}/api/v1` : "/api/v1";

export interface Subject {
  id: string;
  slug: string;
  name: string;
  folder_path: string;
  is_active: boolean;
  discovered_at: string;
  document_count: number;
}

export interface Document {
  id: string;
  subject_id: string | null;
  filename: string;
  filepath: string;
  document_type: string;
  source_role: string;
  file_hash: string;
  file_size: number | null;
  page_count: number | null;
  ingestion_status: string;
  last_ingested_at: string | null;
}

export interface HealthStatus {
  status: string;
  services: Record<string, string>;
  version: string;
}

export interface DiscoverResult {
  subjects_found: number;
  documents_found: number;
  documents_new: number;
  documents_updated: number;
  scanned_paths: number;
  skipped_paths: number;
}

export interface MaintenanceStatus {
  subjects: number;
  documents: number;
  documents_by_status: Record<string, number>;
  content_path: string;
}

export interface IngestPendingResult {
  total: number;
  completed: number;
  failed: number;
  skipped: number;
  results: Array<{
    document_id: string;
    filename: string;
    status: string;
    chunks_created: number;
    embeddings_created: number;
    page_count: number;
    skipped?: boolean;
    error?: string | null;
  }>;
}

export interface ConceptSummary {
  id: string;
  slug: string;
  title: string;
  definition: string | null;
  subtopic: string | null;
  difficulty: number;
  confidence_score: number;
  definition_count: number;
}

export interface ConceptDefinition {
  text: string;
  is_primary: boolean;
  source_type: string;
  page_number: number | null;
  confidence: number;
  provenance: Record<string, unknown>;
  display_label: string;
}

export interface ConceptDetail {
  id: string;
  slug: string;
  title: string;
  definition: string | null;
  simple_explanation: string | null;
  practical_case: string | null;
  subtopic: string | null;
  difficulty: number;
  importance_score: number;
  confidence_score: number;
  definitions: ConceptDefinition[];
  note_references: ConceptNoteReference[];
  created_at: string | null;
}

export interface ExtractConceptsResult {
  subject_slug: string;
  candidates_found: number;
  concepts_created: number;
  concepts_updated: number;
  definitions_added: number;
}

export interface LinkNotesResult {
  subject_slug: string;
  concepts_total: number;
  chunks_scanned: number;
  links_found: number;
  links_created: number;
  links_skipped: number;
}

export interface ClassifyAreasResult {
  subject_slug: string;
  concepts_total: number;
  with_evidence: number;
  unassigned: number;
  areas: Record<string, number>;
}

export interface EnrichDefinitionsResult {
  subject_slug: string;
  concepts_total: number;
  memorizador_path: string;
  entries_scanned: number;
  enriched: number;
  titles_fixed: number;
  unchanged: number;
  examples: string[];
}

export interface ConceptNoteReference {
  chunk_id: string;
  document_id: string | null;
  document_filename: string;
  page_number: number | null;
  match_type: string;
  relevance_score: number;
  excerpt: string | null;
  display_label: string;
}

export interface ChunkDetail {
  chunk_id: string;
  content: string;
  page_start: number | null;
  page_end: number | null;
  chapter: string | null;
  section: string | null;
  heading_path: string[] | null;
  chunk_type: string | null;
  document_id: string;
  document_filename: string;
  document_filepath: string;
  document_type: string;
  page_count: number | null;
  excerpt: string | null;
  relevance_score: number | null;
  match_type: string | null;
  highlight_term: string | null;
  concept_id: string | null;
  concept_title: string | null;
  concept_slug: string | null;
}

export interface SubjectProgress {
  concepts_total: number;
  concepts_with_notes: number;
  cards_reviewed: number;
  cards_due: number;
  concepts_mastered: number;
  readiness_score: number;
  retention_score: number;
  streak_days: number;
}

export interface FlashcardItem {
  concept_id: string;
  title: string;
  slug: string;
  definition: string | null;
  subtopic: string | null;
}

export interface FlashcardCategory {
  name: string;
  concept_count: number;
}

export interface OralExamEvaluation {
  score: number;
  feedback: string;
  coverage: number;
  method?: string;
  missing_points?: string[];
  strengths?: string[];
  llm_error?: string;
}

export interface OralExamState {
  session_id?: string;
  status?: string;
  question: string | null;
  concept_id?: string | null;
  concept_title?: string | null;
  model_answer_hint?: string | null;
  done?: boolean;
  evaluation?: OralExamEvaluation;
  transcript?: Array<Record<string, unknown>>;
}

export interface ConceptExamples {
  concept_id: string;
  title: string;
  short_example: string | null;
  practical_case: string | null;
}

export interface GraphData {
  nodes: Array<{ id: string; title: string; slug: string; subtopic: string | null; link_count: number }>;
  edges: Array<{ source: string; target: string; weight: number; type: string }>;
}

export interface MatchingPair {
  concept_id: string;
  title: string;
  definition: string;
}

export interface FillBlankExercise {
  id: string;
  prompt: string;
  sentence: string;
  answer: string;
  concept_id: string;
  concept_title: string;
  chunk_id: string;
  source: string;
}

export interface LogicExercise {
  id: string;
  kind: string;
  context: string;
  question: string;
  concept_a: string;
  concept_b: string;
  options: Array<{ id: string; label: string }>;
  correct_option: string;
  explanation: string;
}

export interface TranscribeResult {
  text: string;
  language?: string;
  duration?: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  concepts: Array<{
    id: string;
    title: string;
    slug: string;
    definition: string | null;
    subtopic: string | null;
    score: number;
    match_type: string;
    final_score?: number;
  }>;
  chunks: Array<{
    chunk_id: string;
    content: string;
    page_start: number | null;
    page_end: number | null;
    filename: string;
    document_type: string;
    score: number;
  }>;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(await errorMessage(res));
  }
  return res.json();
}

/** Prefiere el mensaje que envía la API; el código HTTP no le dice nada a quien estudia. */
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string" && body.detail) {
      return body.detail;
    }
  } catch {
    // Respuesta sin cuerpo JSON: nos quedamos con el código.
  }
  return `API error: ${res.status} ${res.statusText}`;
}

export const api = {
  health: () => fetch(`${API_BASE}/health`).then((r) => {
    if (!r.ok) throw new Error(`API error: ${r.status}`);
    return r.json() as Promise<HealthStatus>;
  }),
  subjects: () => fetchApi<Subject[]>("/catalog/subjects"),
  documents: (subject?: string) =>
    fetchApi<Document[]>(`/catalog/documents${subject ? `?subject=${subject}` : ""}`),
  discover: () => fetchApi<DiscoverResult>("/catalog/discover", { method: "POST" }),
  maintenanceStatus: () => fetchApi<MaintenanceStatus>("/catalog/maintenance/status"),
  ingestPending: (force = false) =>
    fetchApi<IngestPendingResult>(`/ingestion/ingest-pending?force=${force}`, { method: "POST" }),
  extractConcepts: (slug: string) =>
    fetchApi<ExtractConceptsResult>(`/subjects/${slug}/concepts/extract`, { method: "POST" }),
  linkNotes: (slug: string) =>
    fetchApi<LinkNotesResult>(`/subjects/${slug}/concepts/link-notes`, { method: "POST" }),
  classifyAreas: (slug: string) =>
    fetchApi<ClassifyAreasResult>(`/subjects/${slug}/concepts/classify-areas`, {
      method: "POST",
    }),
  enrichDefinitions: (slug: string) =>
    fetchApi<EnrichDefinitionsResult>(`/subjects/${slug}/concepts/enrich-definitions`, {
      method: "POST",
    }),
  concepts: (slug: string, q?: string, limit = 500) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(limit));
    return fetchApi<ConceptSummary[]>(`/subjects/${slug}/concepts?${params}`);
  },
  importExcelDefinitions: async (slug: string, file: File, pruneMissing = true) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_URL}/subjects/${slug}/concepts/import-excel?create_missing=true&prune_missing=${pruneMissing}`,
      { method: "POST", body: form }
    );
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `API error: ${res.status}`);
    }
    return res.json() as Promise<{
      subject_slug: string;
      excel_rows: number;
      updated: number;
      created: number;
      unchanged: number;
      unmatched: number;
      pruned: number;
      examples: string[];
    }>;
  },
  concept: (id: string) => fetchApi<ConceptDetail>(`/concepts/${id}`),
  chunk: (chunkId: string, conceptId?: string) =>
    fetchApi<ChunkDetail>(
      `/chunks/${chunkId}${conceptId ? `?concept_id=${conceptId}` : ""}`
    ),
  search: (q: string, subject?: string) =>
    fetchApi<SearchResponse>(
      `/search?q=${encodeURIComponent(q)}${subject ? `&subject=${subject}` : ""}`
    ),
  progress: (slug: string) => fetchApi<SubjectProgress>(`/subjects/${slug}/progress`),
  flashcardCategories: (slug: string) =>
    fetchApi<FlashcardCategory[]>(`/subjects/${slug}/flashcards/categories`),
  nextFlashcard: (slug: string, category?: string) =>
    fetchApi<FlashcardItem | null>(
      `/subjects/${slug}/flashcards/next${
        category ? `?category=${encodeURIComponent(category)}` : ""
      }`
    ),
  reviewFlashcard: (slug: string, conceptId: string, quality: number) =>
    fetchApi<{ concept_id: string; mastery_score: number; next_review_days: number }>(
      `/subjects/${slug}/flashcards/${conceptId}/review`,
      { method: "POST", body: JSON.stringify({ quality }) }
    ),
  generateQuestions: (slug: string) =>
    fetchApi<{ created: number }>(`/subjects/${slug}/questions/generate`, { method: "POST" }),
  generateConceptExamples: (slug: string, conceptId: string) =>
    fetchApi<ConceptExamples>(`/subjects/${slug}/concepts/${conceptId}/examples/generate`, {
      method: "POST",
    }),
  generateExamples: (slug: string, limit = 10, force = false) =>
    fetchApi<{
      subject_slug: string;
      requested: number;
      generated: number;
      failed: number;
      examples: ConceptExamples[];
    }>(`/subjects/${slug}/examples/generate`, {
      method: "POST",
      body: JSON.stringify({ limit, force }),
    }),
  startOralExam: (slug: string) =>
    fetchApi<OralExamState>(`/subjects/${slug}/oral-exam/start`, { method: "POST" }),
  answerOralExam: (slug: string, sessionId: string, answer: string) =>
    fetchApi<OralExamState>(`/subjects/${slug}/oral-exam/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),
  skipOralExam: (slug: string, sessionId: string) =>
    fetchApi<OralExamState>(`/subjects/${slug}/oral-exam/${sessionId}/skip`, {
      method: "POST",
    }),
  graph: (slug: string) => fetchApi<GraphData>(`/subjects/${slug}/graph`),
  matchingGame: (slug: string) => fetchApi<MatchingPair[]>(`/subjects/${slug}/games/matching`),
  fillBlankGame: (slug: string) => fetchApi<FillBlankExercise[]>(`/subjects/${slug}/games/fill-blank`),
  checkFillBlank: (slug: string, body: { exercise_id: string; answer: string; expected: string }) =>
    fetchApi<{ correct: boolean; expected: string }>(
      `/subjects/${slug}/games/fill-blank/check`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  logicExercises: (slug: string) => fetchApi<LogicExercise[]>(`/subjects/${slug}/games/logic`),
  checkLogic: (slug: string, body: { exercise_id: string; selected_option: string; correct_option: string; explanation?: string }) =>
    fetchApi<{ correct: boolean; explanation?: string }>(
      `/subjects/${slug}/games/logic/check`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  transcribeOralAudio: async (slug: string, blob: Blob, filename = "audio.webm") => {
    const form = new FormData();
    form.append("audio", blob, filename);
    const res = await fetch(`${API_URL}/subjects/${slug}/oral-exam/transcribe`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `API error: ${res.status}`);
    }
    return res.json() as Promise<TranscribeResult>;
  },
};
