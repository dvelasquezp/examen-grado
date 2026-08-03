"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type FillBlankExercise } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function FillBlankGamePage() {
  const params = useParams();
  const slug = params.slug as string;
  const [exercises, setExercises] = useState<FillBlankExercise[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<{ correct: boolean; expected: string } | null>(null);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIndex(0);
    setScore(0);
    setAnswer("");
    setFeedback(null);
    try {
      const data = await api.fillBlankGame(slug);
      setExercises(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const current = exercises[index];
  const t = es.games;

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    if (!current || !answer.trim()) return;
    setChecking(true);
    try {
      const result = await api.checkFillBlank(slug, {
        exercise_id: current.id,
        answer: answer.trim(),
        expected: current.answer,
      });
      setFeedback(result);
      if (result.correct) setScore((s) => s + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : es.common.error);
    } finally {
      setChecking(false);
    }
  }

  function handleNext() {
    setFeedback(null);
    setAnswer("");
    setIndex((i) => i + 1);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {es.subjectHub.title}
          </Link>
          <h1 className="text-xl font-bold mt-1">{t.fillBlankTitle}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-500">{es.common.loading}</p>}

        {!loading && exercises.length === 0 && (
          <p className="text-gray-500 text-center py-8">{t.fillBlankEmpty}</p>
        )}

        {!loading && current && (
          <>
            <p className="text-sm text-gray-500 mb-4">
              {t.score}: {score} / {exercises.length} · {index + 1}/{exercises.length}
            </p>

            <div className="p-6 bg-white rounded-xl border mb-4">
              <p className="text-xs text-gray-400 mb-3">{current.source}</p>
              <p className="text-base text-gray-800 leading-loose whitespace-pre-wrap">{current.prompt}</p>
            </div>

            {!feedback ? (
              <form onSubmit={handleCheck} className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">{t.fillBlankLabel}</label>
                <input
                  ref={inputRef}
                  type="text"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg"
                  placeholder={t.fillBlankPlaceholder}
                  autoFocus
                />
                <button
                  type="submit"
                  disabled={checking || !answer.trim()}
                  className="px-4 py-2 bg-primary text-white rounded-lg disabled:opacity-50"
                >
                  {checking ? es.common.loading : t.fillBlankCheck}
                </button>
              </form>
            ) : (
              <div
                className={`p-4 rounded-xl border ${
                  feedback.correct ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
                }`}
              >
                <p className="font-medium">
                  {feedback.correct ? t.correct : t.wrong}
                </p>
                {!feedback.correct && (
                  <p className="text-sm mt-1 text-gray-700">
                    {t.fillBlankExpected}: <strong>{feedback.expected}</strong>
                  </p>
                )}
                {index < exercises.length - 1 ? (
                  <button
                    onClick={handleNext}
                    className="mt-3 px-4 py-2 bg-primary text-white rounded-lg text-sm"
                  >
                    {t.fillBlankNext}
                  </button>
                ) : (
                  <p className="mt-3 text-sm text-primary font-medium">{t.fillBlankDone}</p>
                )}
              </div>
            )}
          </>
        )}

        {!loading && exercises.length > 0 && index >= exercises.length - 1 && feedback && (
          <button onClick={load} className="mt-6 px-4 py-2 bg-accent text-white rounded-lg">
            {t.playAgain}
          </button>
        )}
      </main>
    </div>
  );
}
