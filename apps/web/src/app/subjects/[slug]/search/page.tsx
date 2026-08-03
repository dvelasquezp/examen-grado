"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api, type SearchResponse } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function SearchPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(q.trim(), slug);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }

  const t = es.search;
  const hasResults =
    results && (results.concepts.length > 0 || results.chunks.length > 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {es.subjectHub.title}
          </Link>
          <h1 className="text-xl font-bold mt-1">{t.title}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <form onSubmit={handleSearch} className="flex gap-2 mb-6">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t.placeholder}
            className="flex-1 px-4 py-2 border rounded-lg"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-primary text-white rounded-lg disabled:opacity-50"
          >
            {loading ? es.common.loading : es.concepts.search}
          </button>
        </form>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {results && !hasResults && (
          <p className="text-gray-500 text-center py-8">{t.noResults}</p>
        )}

        {results && results.concepts.length > 0 && (
          <section className="mb-8">
            <h2 className="font-semibold mb-3">{t.concepts}</h2>
            <div className="space-y-2">
              {results.concepts.map((c) => (
                <Link
                  key={c.id}
                  href={`/subjects/${slug}/concepts/${c.id}`}
                  className="block p-4 bg-white rounded-xl border hover:border-primary/40"
                >
                  <h3 className="font-medium text-primary">{c.title}</h3>
                  {c.definition && (
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">{c.definition}</p>
                  )}
                </Link>
              ))}
            </div>
          </section>
        )}

        {results && results.chunks.length > 0 && (
          <section>
            <h2 className="font-semibold mb-3">{t.chunks}</h2>
            <div className="space-y-2">
              {results.chunks.map((ch) => (
                <div key={ch.chunk_id} className="p-4 bg-white rounded-xl border">
                  <p className="text-xs text-gray-500 mb-1">
                    {ch.filename}
                    {ch.page_start != null && ` · pág. ${ch.page_start}`}
                  </p>
                  <p className="text-sm text-gray-700 line-clamp-3">{ch.content}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
