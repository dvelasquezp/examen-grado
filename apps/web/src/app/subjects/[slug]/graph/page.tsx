"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type GraphData } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function GraphPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    api
      .graph(slug)
      .then(setGraph)
      .catch((e) => setError(e instanceof Error ? e.message : es.common.error))
      .finally(() => setLoading(false));
  }, [slug]);

  const t = es.graph;
  const nodeMap = new Map(graph?.nodes.map((n) => [n.id, n]) ?? []);
  const related =
    selected && graph
      ? graph.edges.filter((e) => e.source === selected || e.target === selected)
      : [];

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
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-500">{es.common.loading}</p>}

        {graph && graph.nodes.length === 0 && (
          <p className="text-gray-500 text-center py-8">{t.empty}</p>
        )}

        {graph && graph.nodes.length > 0 && (
          <>
            <p className="text-sm text-gray-500 mb-4">
              {graph.nodes.length} {t.nodes} · {graph.edges.length} {t.edges} ({t.coOccurs})
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl border p-4 max-h-[60vh] overflow-y-auto">
                <div className="flex flex-wrap gap-2">
                  {graph.nodes
                    .sort((a, b) => b.link_count - a.link_count)
                    .map((n) => (
                      <button
                        key={n.id}
                        onClick={() => setSelected(n.id === selected ? null : n.id)}
                        className={`px-3 py-1.5 rounded-full text-sm border transition ${
                          selected === n.id
                            ? "bg-primary text-white border-primary"
                            : "bg-gray-50 hover:border-primary/40"
                        }`}
                      >
                        {n.title}
                        <span className="ml-1 text-xs opacity-70">({n.link_count})</span>
                      </button>
                    ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border p-4">
                {!selected ? (
                  <p className="text-gray-500 text-sm">Selecciona un concepto para ver relaciones.</p>
                ) : (
                  <>
                    <h2 className="font-semibold text-primary mb-3">
                      {nodeMap.get(selected)?.title}
                    </h2>
                    <ul className="space-y-2">
                      {related.map((e) => {
                        const otherId = e.source === selected ? e.target : e.source;
                        const other = nodeMap.get(otherId);
                        return (
                          <li key={`${e.source}-${e.target}`}>
                            <Link
                              href={`/subjects/${slug}/concepts/${otherId}`}
                              className="text-sm text-primary hover:underline"
                            >
                              {other?.title ?? otherId}
                            </Link>
                            <span className="text-xs text-gray-400 ml-2">
                              peso {e.weight}
                            </span>
                          </li>
                        );
                      })}
                      {related.length === 0 && (
                        <li className="text-sm text-gray-500">Sin relaciones registradas.</li>
                      )}
                    </ul>
                  </>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
