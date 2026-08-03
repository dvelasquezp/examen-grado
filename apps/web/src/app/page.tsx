"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DiscoverResult, type Document, type HealthStatus, type IngestPendingResult, type Subject, type SubjectProgress } from "@/lib/api-client";
import es from "@/locales/es-CL/common.json";

const DOC_TYPE_LABELS: Record<string, string> = es.documents.types;
const STATUS_LABELS: Record<string, string> = es.documents.status;

export default function DashboardPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [discoverResult, setDiscoverResult] = useState<DiscoverResult | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [ingestResult, setIngestResult] = useState<IngestPendingResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [healthData, subjectsData, documentsData] = await Promise.all([
        api.health(),
        api.subjects(),
        api.documents(),
      ]);
      setHealth(healthData);
      setSubjects(subjectsData);
      setDocuments(documentsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscover() {
    setDiscovering(true);
    setError(null);
    try {
      const result = await api.discover();
      setDiscoverResult(result);
      const subjectsData = await api.subjects();
      setSubjects(subjectsData);
      setDocuments(await api.documents());
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setDiscovering(false);
    }
  }

  async function handleIngestPending() {
    setIngesting(true);
    setError(null);
    try {
      const result = await api.ingestPending();
      setIngestResult(result);
      setDocuments(await api.documents());
    } catch (e) {
      setError(e instanceof Error ? e.message : es.common.error);
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="bg-primary text-white">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">{es.common.appName}</h1>
            <p className="text-sm text-blue-200">Preparación Examen de Grado Oral — U. de Chile</p>
          </div>
          {health && (
            <div className="flex items-center gap-2 text-sm">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  health.status === "ok" ? "bg-green-400" : "bg-yellow-400"
                }`}
              />
              Sistema {health.status === "ok" ? "operativo" : "degradado"}
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {loading && (
          <div className="text-center py-12 text-gray-500">{es.common.loading}</div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
            <p className="text-sm mt-1">
              Si la aplicación estuvo inactiva, puede tardar hasta un minuto en
              despertar. Espera un momento y vuelve a cargar la página.
            </p>
            <button
              onClick={loadData}
              className="mt-3 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && (
          <>
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-primary mb-4">{es.dashboard.title}</h2>
              <DashboardStats subjects={subjects} />
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <section className="lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">{es.dashboard.subjects}</h3>
                  <button
                    onClick={handleDiscover}
                    disabled={discovering}
                    className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-light disabled:opacity-50 transition"
                  >
                    {discovering ? es.maintenance.discovering : es.maintenance.discover}
                  </button>
                </div>

                {discoverResult && (
                  <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                    {es.maintenance.discoverSuccess}: {discoverResult.subjects_found} materias,{" "}
                    {discoverResult.documents_found} documentos encontrados
                    ({discoverResult.documents_new} nuevos, {discoverResult.documents_updated} actualizados)
                  </div>
                )}

                {subjects.length === 0 ? (
                  <div className="p-8 bg-white rounded-xl border border-dashed border-gray-300 text-center">
                    <p className="text-gray-500 mb-4">No se han detectado materias aún.</p>
                    <button
                      onClick={handleDiscover}
                      disabled={discovering}
                      className="px-6 py-2 bg-accent text-white rounded-lg hover:opacity-90 transition"
                    >
                      {es.maintenance.discover}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {subjects.map((subject) => (
                      <SubjectCard key={subject.id} subject={subject} />
                    ))}
                  </div>
                )}

                <div className="mt-4 p-4 bg-gray-100 rounded-xl border border-dashed border-gray-300 opacity-60">
                  <p className="text-sm text-gray-500">
                    + Derecho Penal ({es.dashboard.comingSoon})
                  </p>
                </div>

                {documents.length > 0 && (
                  <section className="mt-8">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">{es.ingestion.title}</h3>
                      <button
                        onClick={handleIngestPending}
                        disabled={ingesting}
                        className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50 transition"
                      >
                        {ingesting ? es.ingestion.ingesting : es.ingestion.ingestPending}
                      </button>
                    </div>

                    {ingestResult && (
                      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                        {es.ingestion.ingestSuccess}: {ingestResult.completed} {es.ingestion.completed},{" "}
                        {ingestResult.failed} {es.ingestion.failed}, {ingestResult.skipped} {es.ingestion.skipped}
                      </div>
                    )}

                    <div className="bg-white rounded-xl border overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="text-left p-3 font-medium text-gray-600">Documento</th>
                            <th className="text-left p-3 font-medium text-gray-600">Tipo</th>
                            <th className="text-left p-3 font-medium text-gray-600">Estado</th>
                            <th className="text-right p-3 font-medium text-gray-600">{es.ingestion.pages}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documents.map((doc) => (
                            <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50">
                              <td className="p-3 max-w-xs truncate" title={doc.filename}>
                                {doc.filename}
                              </td>
                              <td className="p-3 text-gray-500">
                                {DOC_TYPE_LABELS[doc.document_type] || doc.document_type}
                              </td>
                              <td className="p-3">
                                <StatusBadge status={doc.ingestion_status} />
                              </td>
                              <td className="p-3 text-right text-gray-500">
                                {doc.page_count ?? "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
              </section>

              <section>
                <h3 className="text-lg font-semibold mb-4">{es.dashboard.quickActions}</h3>
                <QuickActions subjects={subjects} />

                {health && (
                  <div className="mt-6 p-4 bg-white rounded-xl border">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">{es.maintenance.status}</h4>
                    <div className="space-y-1">
                      {Object.entries(health.services).map(([service, status]) => (
                        <div key={service} className="flex justify-between text-sm">
                          <span className="text-gray-600 capitalize">{service}</span>
                          <span className={status === "ok" ? "text-green-600" : "text-yellow-600"}>
                            {status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="p-4 bg-white rounded-xl border shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-primary mt-1">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}

function SubjectCard({ subject }: { subject: Subject }) {
  return (
    <Link
      href={`/subjects/${subject.slug}`}
      className="block p-5 bg-white rounded-xl border shadow-sm hover:border-primary/30 transition"
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-lg">{subject.name}</h4>
          <p className="text-sm text-gray-500">{subject.document_count} documentos</p>
        </div>
        <span className="text-2xl">⚖️</span>
      </div>
      <p className="text-xs text-primary mt-3">Explorar materia →</p>
    </Link>
  );
}

function DashboardStats({ subjects }: { subjects: Subject[] }) {
  const [progress, setProgress] = useState<SubjectProgress | null>(null);

  useEffect(() => {
    if (subjects.length === 0) return;
    api.progress(subjects[0].slug).then(setProgress).catch(() => setProgress(null));
  }, [subjects]);

  if (!progress) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StatCard label={es.dashboard.retention} value="—" sub={es.dashboard.flashcardsToday} />
        <StatCard label={es.dashboard.streak} value="—" sub={es.dashboard.weakConcepts} />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <StatCard
        label={es.dashboard.retention}
        value={`${Math.round(progress.retention_score * 100)}%`}
        sub={`${progress.cards_due} ${es.dashboard.flashcardsToday}`}
      />
      <StatCard
        label={es.dashboard.streak}
        value={String(progress.streak_days)}
        sub={`${progress.cards_reviewed} repasadas`}
      />
    </div>
  );
}

function QuickActions({ subjects }: { subjects: Subject[] }) {
  if (subjects.length === 0) {
    return (
      <div className="space-y-2">
        <ActionButton label={es.dashboard.oralExam} disabled />
        <ActionButton label={es.dashboard.conceptMap} disabled />
        <ActionButton label={es.dashboard.games} disabled />
      </div>
    );
  }
  const slug = subjects[0].slug;
  return (
    <div className="space-y-2">
      <ActionLink label={es.dashboard.startReview} href={`/subjects/${slug}/flashcards`} />
      <ActionLink label={es.dashboard.oralExam} href={`/subjects/${slug}/oral-exam`} />
      <ActionLink label={es.dashboard.conceptMap} href={`/subjects/${slug}/graph`} />
      <ActionLink label={es.dashboard.games} href={`/subjects/${slug}/games/matching`} />
    </div>
  );
}

function ActionLink({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      className="block w-full p-3 text-left bg-white rounded-lg border text-sm hover:bg-gray-50 transition"
    >
      {label}
    </Link>
  );
}

function ActionButton({ label, disabled, hint }: { label: string; disabled?: boolean; hint?: string }) {
  return (
    <button
      disabled={disabled}
      className="w-full p-3 text-left bg-white rounded-lg border text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
    >
      {label}
      {hint && <span className="float-right text-xs text-gray-400">{hint}</span>}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-gray-100 text-gray-700",
    processing: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}
