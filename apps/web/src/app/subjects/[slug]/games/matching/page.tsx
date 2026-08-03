"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type MatchingPair } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export default function MatchingGamePage() {
  const params = useParams();
  const slug = params.slug as string;
  const [pairs, setPairs] = useState<MatchingPair[]>([]);
  const [definitions, setDefinitions] = useState<MatchingPair[]>([]);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [score, setScore] = useState(0);
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [feedback, setFeedback] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGame = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMatched(new Set());
    setSelectedConcept(null);
    setScore(0);
    setFeedback(null);
    try {
      const data = await api.matchingGame(slug);
      setPairs(data);
      setDefinitions(shuffle(data));
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadGame();
  }, [loadGame]);

  const remaining = useMemo(
    () => pairs.filter((p) => !matched.has(p.concept_id)),
    [pairs, matched]
  );

  function handleConceptClick(id: string) {
    if (matched.has(id)) return;
    setSelectedConcept(id);
    setFeedback(null);
  }

  function handleDefinitionClick(pair: MatchingPair) {
    if (!selectedConcept || matched.has(pair.concept_id)) return;
    if (selectedConcept === pair.concept_id) {
      setMatched((prev) => new Set(prev).add(pair.concept_id));
      setScore((s) => s + 1);
      setFeedback(es.games.correct);
      setSelectedConcept(null);
    } else {
      setFeedback(es.games.wrong);
    }
  }

  const t = es.games;
  const won = pairs.length > 0 && matched.size === pairs.length;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {es.subjectHub.title}
          </Link>
          <h1 className="text-xl font-bold mt-1">{t.matchingTitle}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-500">{es.common.loading}</p>}

        {!loading && pairs.length > 0 && (
          <>
            <p className="text-sm text-gray-600 mb-4">
              {t.score}: {score} / {pairs.length}
            </p>
            <p className="text-sm text-gray-500 mb-4">{t.selectDefinition}</p>

            {feedback && (
              <p
                className={`mb-4 text-sm font-medium ${
                  feedback === t.correct ? "text-green-700" : "text-red-700"
                }`}
              >
                {feedback}
              </p>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              <div className="space-y-2">
                {remaining.map((p) => (
                  <button
                    key={p.concept_id}
                    onClick={() => handleConceptClick(p.concept_id)}
                    className={`w-full p-4 text-left rounded-lg border text-sm font-medium transition ${
                      selectedConcept === p.concept_id
                        ? "border-primary bg-primary/10 text-primary"
                        : "bg-white hover:border-primary/30"
                    }`}
                  >
                    {p.title}
                  </button>
                ))}
              </div>

              <div className="space-y-3">
                {definitions
                  .filter((d) => !matched.has(d.concept_id))
                  .map((d) => (
                    <button
                      key={d.concept_id}
                      onClick={() => handleDefinitionClick(d)}
                      disabled={!selectedConcept}
                      className="w-full p-4 text-left rounded-lg border bg-white text-sm text-gray-700 leading-relaxed hover:border-primary/30 disabled:opacity-50"
                    >
                      {d.definition}
                    </button>
                  ))}
              </div>
            </div>

            {won && (
              <div className="mt-8 text-center">
                <p className="text-lg font-semibold text-primary">¡Completado!</p>
                <button
                  onClick={loadGame}
                  className="mt-4 px-4 py-2 bg-accent text-white rounded-lg"
                >
                  {t.playAgain}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
