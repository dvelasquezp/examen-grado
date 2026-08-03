"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type SubjectProgress } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

const FEATURES = [
  { href: "concepts", icon: "📚", titleKey: "concepts", descKey: "conceptsDesc" },
  { href: "search", icon: "🔍", titleKey: "search", descKey: "searchDesc" },
  { href: "flashcards", icon: "🃏", titleKey: "flashcards", descKey: "flashcardsDesc" },
  { href: "oral-exam", icon: "🎤", titleKey: "oralExam", descKey: "oralExamDesc" },
  { href: "graph", icon: "🗺️", titleKey: "graph", descKey: "graphDesc" },
  { href: "games/matching", icon: "🎯", titleKey: "matchingGame", descKey: "matchingDesc" },
  { href: "games/fill-blank", icon: "✍️", titleKey: "fillBlankGame", descKey: "fillBlankDesc" },
  { href: "games/logic", icon: "🔣", titleKey: "logicGame", descKey: "logicDesc" },
] as const;

export default function SubjectHubPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [progress, setProgress] = useState<SubjectProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .progress(slug)
      .then(setProgress)
      .catch((e) => setError(e instanceof Error ? e.message : es.common.error))
      .finally(() => setLoading(false));
  }, [slug]);

  const t = es.subjectHub;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link href="/" className="text-sm text-blue-200 hover:text-white">
            ← {t.back}
          </Link>
          <h1 className="text-xl font-bold mt-1 capitalize">{slug.replace(/-/g, " ")}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {!loading && progress && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-8">
            <MiniStat label="Conceptos" value={progress.concepts_total} />
            <MiniStat label="Con apuntes" value={progress.concepts_with_notes} />
            <MiniStat label="Repaso hoy" value={progress.cards_due} />
          </div>
        )}

        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6">
          {t.draftNotice}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <Link
              key={f.href}
              href={`/subjects/${slug}/${f.href}`}
              className="block p-5 bg-white rounded-xl border shadow-sm hover:border-primary/40 transition"
            >
              <span className="text-2xl">{f.icon}</span>
              <h2 className="font-semibold text-lg mt-2 text-primary">
                {t[f.titleKey as keyof typeof t]}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {t[f.descKey as keyof typeof t]}
              </p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 bg-white rounded-lg border text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold text-primary">{value}</p>
    </div>
  );
}
