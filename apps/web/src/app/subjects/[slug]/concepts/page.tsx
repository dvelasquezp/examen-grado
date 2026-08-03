"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type ConceptSummary } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function ConceptsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string;
  const [concepts, setConcepts] = useState<ConceptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [linking, setLinking] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [extractResult, setExtractResult] = useState<string | null>(null);
  const [linkResult, setLinkResult] = useState<string | null>(null);
  const [classifyResult, setClassifyResult] = useState<string | null>(null);
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConcepts(q || undefined);
  }, [slug]);

  async function loadConcepts(query?: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.concepts(slug, query);
      setConcepts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }

  async function handleExtract() {
    setExtracting(true);
    setError(null);
    try {
      const result = await api.extractConcepts(slug);
      setExtractResult(
        `${result.concepts_created} conceptos nuevos, ${result.definitions_added} definiciones (${result.candidates_found} candidatos)`
      );
      await loadConcepts(q || undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setExtracting(false);
    }
  }

  async function handleLinkNotes() {
    setLinking(true);
    setError(null);
    try {
      const result = await api.linkNotes(slug);
      setLinkResult(
        `${result.links_created} vínculos nuevos (${result.links_found} menciones en ${result.chunks_scanned} chunks)`
      );
      await loadConcepts(q || undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLinking(false);
    }
  }

  async function handleClassifyAreas() {
    setClassifying(true);
    setError(null);
    try {
      const result = await api.classifyAreas(slug);
      const areas = Object.entries(result.areas)
        .map(([name, count]) => `${name} (${count})`)
        .join(", ");
      setClassifyResult(
        `${result.concepts_total - result.unassigned} de ${result.concepts_total} conceptos: ${areas}`
      );
      await loadConcepts(q || undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setClassifying(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    loadConcepts(q || undefined);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {es.subjectHub.title}
          </Link>
          <h1 className="text-xl font-bold mt-1">{es.concepts.title}</h1>
          <p className="text-sm text-blue-200 capitalize">{slug.replace("-", " ")}</p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={es.concepts.searchPlaceholder}
              className="flex-1 px-4 py-2 border rounded-lg"
            />
            <button type="submit" className="px-4 py-2 bg-primary text-white rounded-lg">
              {es.concepts.search}
            </button>
          </form>
          <button
            onClick={handleExtract}
            disabled={extracting || linking}
            className="px-4 py-2 bg-accent text-white rounded-lg disabled:opacity-50"
          >
            {extracting ? es.concepts.extracting : es.concepts.extract}
          </button>
          <button
            onClick={handleLinkNotes}
            disabled={linking || extracting || concepts.length === 0}
            className="px-4 py-2 bg-primary text-white rounded-lg disabled:opacity-50"
            title={concepts.length === 0 ? es.concepts.empty : undefined}
          >
            {linking ? es.concepts.linkingNotes : es.concepts.linkNotes}
          </button>
          <button
            onClick={handleClassifyAreas}
            disabled={classifying || linking || extracting || concepts.length === 0}
            className="px-4 py-2 bg-primary text-white rounded-lg disabled:opacity-50"
            title={concepts.length === 0 ? es.concepts.empty : undefined}
          >
            {classifying ? es.concepts.classifying : es.concepts.classifyAreas}
          </button>
        </div>

        {extractResult && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-800 text-sm">
            {es.concepts.extractSuccess}: {extractResult}
          </div>
        )}

        {linkResult && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
            {es.concepts.linkNotesSuccess}: {linkResult}
          </div>
        )}

        {classifyResult && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
            {es.concepts.classifySuccess}: {classifyResult}
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">{es.common.loading}</p>
        ) : concepts.length === 0 ? (
          <div className="p-8 bg-white rounded-xl border text-center text-gray-500">
            <p className="mb-4">{es.concepts.empty}</p>
            <button
              onClick={handleExtract}
              disabled={extracting}
              className="px-6 py-2 bg-accent text-white rounded-lg"
            >
              {es.concepts.extract}
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">
              {concepts.length} {es.concepts.count}
            </p>
            <div className="grid gap-3">
              {concepts.map((c) => (
                <Link
                  key={c.id}
                  href={`/subjects/${slug}/concepts/${c.id}`}
                  className="block p-4 bg-white rounded-xl border hover:border-primary/40 transition"
                >
                  <div className="flex justify-between items-start">
                    <h2 className="font-semibold text-primary">{c.title}</h2>
                    <span className="text-xs text-gray-400">
                      {Math.round(c.confidence_score * 100)}%
                    </span>
                  </div>
                  {c.subtopic && (
                    <p className="text-xs text-gray-500 mt-1">{c.subtopic}</p>
                  )}
                  {c.definition && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">{c.definition}</p>
                  )}
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
