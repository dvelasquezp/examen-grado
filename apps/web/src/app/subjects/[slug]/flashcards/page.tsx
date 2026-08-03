"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, type FlashcardItem } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

export default function FlashcardsPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [card, setCard] = useState<FlashcardItem | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNext = useCallback(async () => {
    setLoading(true);
    setError(null);
    setShowAnswer(false);
    try {
      const next = await api.nextFlashcard(slug);
      if (!next) {
        setDone(true);
        setCard(null);
      } else {
        setDone(false);
        setCard(next);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadNext();
  }, [loadNext]);

  async function handleReview(quality: number) {
    if (!card) return;
    setSubmitting(true);
    try {
      await api.reviewFlashcard(slug, card.concept_id, quality);
      await loadNext();
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setSubmitting(false);
    }
  }

  const t = es.flashcards;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href={`/subjects/${slug}`} className="text-sm text-blue-200 hover:text-white">
            ← {t.back}
          </Link>
          <h1 className="text-xl font-bold mt-1">{t.title}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-8">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <p className="text-center text-gray-500">{es.common.loading}</p>}

        {!loading && done && (
          <div className="text-center p-8 bg-white rounded-xl border">
            <p className="text-lg font-semibold text-primary">{t.done}</p>
            <button
              onClick={loadNext}
              className="mt-4 px-4 py-2 bg-primary text-white rounded-lg"
            >
              {es.games.playAgain}
            </button>
          </div>
        )}

        {!loading && card && (
          <div className="space-y-6">
            <div
              className="min-h-[200px] p-8 bg-white rounded-xl border shadow-sm flex flex-col items-center justify-center text-center cursor-pointer"
              onClick={() => setShowAnswer((v) => !v)}
            >
              {!showAnswer ? (
                <>
                  <h2 className="text-2xl font-bold text-primary">{card.title}</h2>
                  {card.subtopic && (
                    <p className="text-sm text-gray-500 mt-2">{card.subtopic}</p>
                  )}
                  <p className="text-sm text-gray-400 mt-6">{t.showAnswer}</p>
                </>
              ) : (
                <p className="text-gray-700 whitespace-pre-wrap">
                  {card.definition || "—"}
                </p>
              )}
            </div>

            {showAnswer && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ReviewBtn
                  label={t.again}
                  hint={t.againHint}
                  color="red"
                  disabled={submitting}
                  onClick={() => handleReview(0)}
                />
                <ReviewBtn
                  label={t.hard}
                  hint={t.hardHint}
                  color="orange"
                  disabled={submitting}
                  onClick={() => handleReview(2)}
                />
                <ReviewBtn
                  label={t.good}
                  hint={t.goodHint}
                  color="green"
                  disabled={submitting}
                  onClick={() => handleReview(3)}
                />
                <ReviewBtn
                  label={t.easy}
                  hint={t.easyHint}
                  color="blue"
                  disabled={submitting}
                  onClick={() => handleReview(5)}
                />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function ReviewBtn({
  label,
  hint,
  color,
  disabled,
  onClick,
}: {
  label: string;
  hint: string;
  color: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  const colors: Record<string, string> = {
    red: "bg-red-100 text-red-800 hover:bg-red-200",
    orange: "bg-orange-100 text-orange-800 hover:bg-orange-200",
    green: "bg-green-100 text-green-800 hover:bg-green-200",
    blue: "bg-blue-100 text-blue-800 hover:bg-blue-200",
  };
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`p-4 rounded-lg text-left disabled:opacity-50 transition ${colors[color]}`}
    >
      <span className="block font-medium text-sm">{label}</span>
      <span className="block text-xs opacity-75 mt-1 leading-snug">{hint}</span>
    </button>
  );
}
