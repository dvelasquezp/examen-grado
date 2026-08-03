"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, type LogicExercise } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function LogicGamePage() {
  const params = useParams();
  const slug = params.slug as string;
  const [exercises, setExercises] = useState<LogicExercise[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ correct: boolean; explanation?: string } | null>(null);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIndex(0);
    setScore(0);
    setSelected(null);
    setFeedback(null);
    try {
      const data = await api.logicExercises(slug);
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

  async function handleSelect(optionId: string) {
    if (!current || feedback) return;
    setSelected(optionId);
    try {
      const result = await api.checkLogic(slug, {
        exercise_id: current.id,
        selected_option: optionId,
        correct_option: current.correct_option,
        explanation: current.explanation,
      });
      setFeedback(result);
      if (result.correct) setScore((s) => s + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : es.common.error);
    }
  }

  function handleNext() {
    setFeedback(null);
    setSelected(null);
    setIndex((i) => i + 1);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {es.subjectHub.title}
          </Link>
          <h1 className="text-xl font-bold mt-1">{t.logicTitle}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-8">
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6">
          {t.logicNotice}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-500">{es.common.loading}</p>}

        {!loading && current && (
          <>
            <p className="text-sm text-gray-500 mb-4">
              {t.score}: {score} / {exercises.length} · {index + 1}/{exercises.length}
            </p>

            <div className="p-5 bg-blue-50 border border-blue-100 rounded-xl mb-4">
              <p className="text-xs font-semibold text-blue-800 uppercase tracking-wide mb-2">
                {t.logicContext}
              </p>
              <p className="text-sm text-blue-900 leading-relaxed italic">
                «{current.context}»
              </p>
              <p className="text-xs text-blue-700 mt-2">
                {t.logicConcepts}: {current.concept_a} · {current.concept_b}
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl border mb-4">
              <p className="text-base text-gray-800 leading-relaxed">{current.question}</p>
            </div>

            <div className="space-y-2">
              {current.options.map((opt) => {
                let style = "bg-white border hover:border-primary/40";
                if (feedback && opt.id === current.correct_option) {
                  style = "bg-green-100 border-green-400";
                } else if (feedback && opt.id === selected && !feedback.correct) {
                  style = "bg-red-100 border-red-400";
                } else if (opt.id === selected) {
                  style = "bg-primary/10 border-primary";
                }
                return (
                  <button
                    key={opt.id}
                    disabled={!!feedback}
                    onClick={() => handleSelect(opt.id)}
                    className={`w-full p-4 text-left rounded-lg border text-sm leading-relaxed transition ${style}`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>

            {feedback && (
              <div className="mt-4 p-4 rounded-xl border bg-white border-gray-200">
                <p className={`font-medium ${feedback.correct ? "text-green-800" : "text-red-800"}`}>
                  {feedback.correct ? t.correct : t.wrong}
                </p>
                {feedback.explanation && (
                  <p className="text-sm text-gray-700 mt-2 leading-relaxed">
                    <span className="font-medium text-primary">{t.logicWhy}: </span>
                    {feedback.explanation}
                  </p>
                )}
                {index < exercises.length - 1 ? (
                  <button
                    onClick={handleNext}
                    className="mt-3 px-4 py-2 bg-primary text-white rounded-lg text-sm"
                  >
                    {t.logicNext}
                  </button>
                ) : (
                  <button onClick={load} className="mt-3 px-4 py-2 bg-accent text-white rounded-lg text-sm">
                    {t.playAgain}
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
