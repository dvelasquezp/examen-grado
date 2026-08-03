"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type ConceptDetail } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function ConceptDetailPage() {
  const params = useParams();
  const slug = params.slug as string;
  const conceptId = params.id as string;
  const [concept, setConcept] = useState<ConceptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.concept(conceptId)
      .then(setConcept)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [conceptId]);

  if (loading) return <div className="p-8 text-gray-500">{es.common.loading}</div>;
  if (error || !concept) {
    return (
      <div className="p-8 text-red-600">{error || es.common.error}</div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-4xl px-6 py-4">
          <Link
            href={`/subjects/${slug}/concepts`}
            className="text-sm text-blue-200 hover:text-white"
          >
            ← {es.concepts.backToList}
          </Link>
          <h1 className="text-2xl font-bold mt-2">{concept.title}</h1>
          {concept.subtopic && (
            <p className="text-sm text-blue-200 mt-1">{concept.subtopic}</p>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        {concept.definition && (
          <section className="bg-white rounded-xl border p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">
              {es.concepts.definition}
            </h2>
            <p className="text-lg leading-relaxed">{concept.definition}</p>
            {concept.definitions[0] && (
              <ProvenanceBadge definition={concept.definitions[0]} />
            )}
          </section>
        )}

        {concept.definitions.length > 1 && (
          <section className="bg-white rounded-xl border p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">
              {es.concepts.alternativeDefinitions}
            </h2>
            <div className="space-y-4">
              {concept.definitions.slice(1).map((d, i) => (
                <div key={i} className="border-l-4 border-primary/30 pl-4">
                  <p className="text-gray-700">{d.text}</p>
                  <ProvenanceBadge definition={d} />
                </div>
              ))}
            </div>
          </section>
        )}

        {concept.note_references?.length > 0 && (
          <section className="bg-white rounded-xl border p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">
              {es.concepts.noteReferences}
            </h2>
            <div className="space-y-4">
              {concept.note_references.slice(0, 20).map((ref) => (
                <div key={ref.chunk_id} className="border-l-4 border-doctrine/40 pl-4">
                  <p className="text-gray-700 text-sm leading-relaxed">{ref.excerpt}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="px-2 py-1 bg-amber-50 text-doctrine rounded-full border border-amber-200">
                      📚 {ref.display_label || es.provenance.linkedNotes}
                    </span>
                    <span className="text-gray-500">{ref.document_filename}</span>
                    {ref.page_number && (
                      <span className="text-gray-400">pág. {ref.page_number}</span>
                    )}
                    <span className="text-gray-400">
                      {Math.round(ref.relevance_score * 100)}%
                    </span>
                    <Link
                      href={`/subjects/${slug}/concepts/${conceptId}/sources/${ref.chunk_id}`}
                      className="ml-auto px-3 py-1 bg-primary text-white rounded-full hover:bg-primary/90 transition"
                    >
                      {es.sources.openInApp}
                    </Link>
                  </div>
                </div>
              ))}
              {concept.note_references.length > 20 && (
                <p className="text-sm text-gray-500">
                  {es.sources.showingTop} 20 / {concept.note_references.length}
                </p>
              )}
            </div>
          </section>
        )}

        <section className="bg-white rounded-xl border p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">
            {es.concepts.metadata}
          </h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-gray-500">{es.concepts.confidence}</dt>
            <dd>{Math.round(concept.confidence_score * 100)}%</dd>
            <dt className="text-gray-500">{es.concepts.difficulty}</dt>
            <dd>{concept.difficulty}/5</dd>
            <dt className="text-gray-500">{es.concepts.sources}</dt>
            <dd>{concept.definitions.length + (concept.note_references?.length || 0)}</dd>
          </dl>
        </section>
      </main>
    </div>
  );
}

function ProvenanceBadge({ definition }: { definition: { display_label: string; page_number: number | null; confidence: number } }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
      <span className="px-2 py-1 bg-blue-50 text-doctrine rounded-full border border-blue-200">
        📄 {definition.display_label || es.provenance.extractedNotes}
      </span>
      {definition.page_number && (
        <span className="text-gray-500">pág. {definition.page_number}</span>
      )}
      <span className="text-gray-400">
        {es.concepts.confidence}: {Math.round(definition.confidence * 100)}%
      </span>
    </div>
  );
}
