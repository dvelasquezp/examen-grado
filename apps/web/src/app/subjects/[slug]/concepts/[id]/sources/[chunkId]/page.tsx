"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type ChunkDetail } from "@/lib/api-client";
import { highlightTerm } from "@/lib/highlight-text";
import es from "@/locales/es-CL/common.json";

export default function SourceViewerPage() {
  const params = useParams();
  const slug = params.slug as string;
  const conceptId = params.id as string;
  const chunkId = params.chunkId as string;
  const [chunk, setChunk] = useState<ChunkDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .chunk(chunkId, conceptId)
      .then(setChunk)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [chunkId, conceptId]);

  if (loading) return <div className="p-8 text-gray-500">{es.common.loading}</div>;
  if (error || !chunk) {
    return <div className="p-8 text-red-600">{error || es.common.error}</div>;
  }

  const backHref = `/subjects/${slug}/concepts/${conceptId}`;
  const pageLabel =
    chunk.page_start && chunk.page_end && chunk.page_start !== chunk.page_end
      ? `${chunk.page_start}–${chunk.page_end}`
      : chunk.page_start?.toString();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-4xl px-6 py-4">
          <Link href={backHref} className="text-sm text-blue-200 hover:text-white">
            ← {chunk.concept_title || es.sources.backToConcept}
          </Link>
          <h1 className="text-xl font-bold mt-2">{chunk.document_filename}</h1>
          <p className="text-sm text-blue-200 mt-1">
            {es.sources.lectureNotes}
            {pageLabel && ` · ${es.sources.page} ${pageLabel}`}
            {chunk.page_count && ` / ${chunk.page_count}`}
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        {(chunk.chapter || chunk.section || chunk.heading_path?.length) && (
          <section className="bg-white rounded-xl border p-4 text-sm text-gray-600">
            {chunk.heading_path?.length ? (
              <p>{chunk.heading_path.join(" › ")}</p>
            ) : (
              <p>
                {[chunk.chapter, chunk.section].filter(Boolean).join(" · ")}
              </p>
            )}
          </section>
        )}

        {chunk.excerpt && (
          <section className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <h2 className="text-xs font-semibold uppercase text-amber-800 mb-2">
              {es.sources.matchExcerpt}
            </h2>
            <p className="text-sm text-amber-900 leading-relaxed">{chunk.excerpt}</p>
            {chunk.relevance_score != null && (
              <p className="text-xs text-amber-700 mt-2">
                {es.concepts.confidence}: {Math.round(chunk.relevance_score * 100)}%
              </p>
            )}
          </section>
        )}

        <section className="bg-white rounded-xl border p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">
            {es.sources.fullPassage}
          </h2>
          <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed whitespace-pre-wrap">
            {highlightTerm(chunk.content, chunk.highlight_term)}
          </div>
        </section>

        <div className="flex gap-3">
          <Link
            href={backHref}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm"
          >
            {es.sources.backToConcept}
          </Link>
        </div>
      </main>
    </div>
  );
}
