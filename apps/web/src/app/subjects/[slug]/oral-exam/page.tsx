"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api, type OralExamState } from "@/lib/api-client";
import { useAudioRecorder } from "@/lib/use-audio-recorder";
import es from "@/locales/es-CL/common.json";

export default function OralExamPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<OralExamState | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "audio">("audio");

  const recorder = useAudioRecorder();
  const t = es.oralExam;

  async function handleStart() {
    setLoading(true);
    setError(null);
    recorder.reset();
    try {
      const data = await api.startOralExam(slug);
      setSessionId(data.session_id ?? null);
      setState(data);
      setAnswer("");
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }

  async function handleTranscribe() {
    const blob = recorder.getBlob();
    if (!blob) return;
    setTranscribing(true);
    setError(null);
    try {
      const result = await api.transcribeOralAudio(slug, blob, "recording.webm");
      setAnswer((prev) => (prev ? `${prev} ${result.text}` : result.text).trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setTranscribing(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!sessionId || !answer.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.answerOralExam(slug, sessionId, answer.trim());
      setState(data);
      setAnswer("");
      recorder.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }

  const finished = state?.done || state?.status === "completed";
  const evaluation = state?.evaluation;
  const canSubmit = answer.trim().length > 0;

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

      <main className="mx-auto max-w-2xl px-6 py-8">
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6">
          {es.subjectHub.draftNotice}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {!sessionId && (
          <button
            onClick={handleStart}
            disabled={loading}
            className="px-6 py-3 bg-accent text-white rounded-lg font-medium disabled:opacity-50"
          >
            {loading ? es.common.loading : t.start}
          </button>
        )}

        {sessionId && state?.question && !finished && (
          <div className="space-y-4">
            <div className="p-6 bg-white rounded-xl border">
              <p className="text-xs text-gray-500 mb-2">{state.concept_title}</p>
              <p className="text-lg font-medium text-primary">{state.question}</p>
            </div>

            <div className="flex gap-2 mb-2">
              <ModeBtn active={inputMode === "audio"} onClick={() => setInputMode("audio")}>
                🎤 {t.modeAudio}
              </ModeBtn>
              <ModeBtn active={inputMode === "text"} onClick={() => setInputMode("text")}>
                ✏️ {t.modeText}
              </ModeBtn>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              {inputMode === "audio" && (
                <div className="p-4 bg-white rounded-xl border space-y-3">
                  <p className="text-sm text-gray-600">{t.audioInstructions}</p>
                  {recorder.error && (
                    <p className="text-sm text-red-600">{recorder.error}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {!recorder.recording ? (
                      <button
                        type="button"
                        onClick={recorder.startRecording}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm"
                      >
                        {t.recordStart}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={recorder.stopRecording}
                        className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm animate-pulse"
                      >
                        {t.recordStop}
                      </button>
                    )}
                    {recorder.audioUrl && (
                      <>
                        <audio src={recorder.audioUrl} controls className="max-w-full" />
                        <button
                          type="button"
                          onClick={handleTranscribe}
                          disabled={transcribing}
                          className="px-4 py-2 bg-primary text-white rounded-lg text-sm disabled:opacity-50"
                        >
                          {transcribing ? t.transcribing : t.transcribe}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}

              <label className="block text-sm font-medium text-gray-700">{t.yourAnswer}</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                className="w-full px-4 py-2 border rounded-lg"
                placeholder={inputMode === "audio" ? t.answerPlaceholderAudio : t.answerPlaceholderText}
              />

              <button
                type="submit"
                disabled={loading || !canSubmit}
                className="px-4 py-2 bg-primary text-white rounded-lg disabled:opacity-50"
              >
                {loading ? es.common.loading : t.submit}
              </button>
            </form>
          </div>
        )}

        {evaluation && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
            <h3 className="font-semibold text-blue-900">{t.feedback}</h3>
            <p className="text-sm text-blue-800 mt-1">
              {t.score}: {Math.round((evaluation.coverage ?? evaluation.score ?? 0) * 100)}%
            </p>
            <p className="text-sm text-gray-700 mt-2">{evaluation.feedback}</p>
            {state?.model_answer_hint && (
              <details className="mt-3">
                <summary className="text-sm text-primary cursor-pointer">{t.hint}</summary>
                <p className="text-sm text-gray-600 mt-2">{state.model_answer_hint}</p>
              </details>
            )}
          </div>
        )}

        {finished && (
          <div className="mt-6 p-6 bg-white rounded-xl border text-center">
            <h2 className="text-lg font-semibold text-primary">{t.finished}</h2>
            <button
              onClick={handleStart}
              disabled={loading}
              className="mt-4 px-4 py-2 bg-accent text-white rounded-lg"
            >
              {t.start}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

function ModeBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm border transition ${
        active ? "bg-primary text-white border-primary" : "bg-white text-gray-600"
      }`}
    >
      {children}
    </button>
  );
}
