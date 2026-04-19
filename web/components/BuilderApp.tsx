"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "./Header";
import { Toast } from "./Toast";
import { apiFetch, apiJson } from "@/lib/api";

type TemplateOpt = { id: string; name: string; origin: string };
type DataOpt = { id: string; name: string; origin: string };

type AtsReport = { errors: string[]; warnings: string[]; suggestions: string[] } | null;

export function BuilderApp() {
  const [templates, setTemplates] = useState<TemplateOpt[]>([]);
  const [dataFiles, setDataFiles] = useState<DataOpt[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [dataFileId, setDataFileId] = useState("");
  const [generatePdf, setGeneratePdf] = useState(true);
  const [runAts, setRunAts] = useState(false);
  const [pdfVariant, setPdfVariant] = useState("pdf/a-2b");
  const [developerHtml, setDeveloperHtml] = useState(false);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [toastVariant, setToastVariant] = useState<"info" | "error" | "success">("info");
  const [atsReport, setAtsReport] = useState<AtsReport>(null);
  const [showAts, setShowAts] = useState(false);
  const [history, setHistory] = useState<{ items: unknown[]; total: number } | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((msg: string, variant: "info" | "error" | "success" = "info") => {
    setToastVariant(variant);
    setToast(msg);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [t, d] = await Promise.all([
          apiJson<TemplateOpt[]>("/api/templates"),
          apiJson<DataOpt[]>("/api/data-files"),
        ]);
        setTemplates(t);
        setDataFiles(d);
        if (t[0]) setTemplateId(t[0].id);
        if (d[0]) setDataFileId(d[0].id);
      } catch {
        showToast("Failed to load lists", "error");
      }
    })();
  }, [showToast]);

  const runPreview = useCallback(async () => {
    if (!templateId || !dataFileId) return;
    setLoading(true);
    setAtsReport(null);
    try {
      const formats = ["pdf"];
      if (developerHtml) formats.push("html");
      const body = {
        template_id: templateId,
        data_file_id: dataFileId,
        formats,
        pdf_variant: pdfVariant,
        run_ats_check: runAts,
        preview_only: true,
      };
      const res = await apiFetch("/api/generate", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error((j.detail && JSON.stringify(j.detail)) || res.statusText);
      }
      const data = (await res.json()) as {
        submission_id: string;
        ats_report: AtsReport;
      };
      setSubmissionId(data.submission_id);
      setAtsReport(data.ats_report ?? null);
    } catch (e) {
      setSubmissionId(null);
      showToast(e instanceof Error ? e.message : "Preview failed", "error");
    } finally {
      setLoading(false);
    }
  }, [templateId, dataFileId, pdfVariant, runAts, developerHtml, showToast]);

  useEffect(() => {
    if (!templateId || !dataFileId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runPreview();
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [templateId, dataFileId, pdfVariant, runAts, developerHtml, runPreview]);

  async function fullGenerate(previewOnly: boolean) {
    if (!templateId || !dataFileId) return;
    setLoading(true);
    try {
      const formats: string[] = [];
      if (generatePdf) formats.push("pdf");
      formats.push("docx");
      if (developerHtml) formats.push("html");
      const body = {
        template_id: templateId,
        data_file_id: dataFileId,
        formats,
        pdf_variant: pdfVariant,
        run_ats_check: runAts,
        preview_only: previewOnly,
      };
      const res = await apiFetch("/api/generate", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(JSON.stringify(data.detail || data));
      }
      setSubmissionId(data.submission_id as string);
      setAtsReport((data.ats_report as AtsReport) ?? null);
      showToast(previewOnly ? "Preview updated" : "Saved to outputs folder", "success");
      const h = await apiJson<{ items: unknown[]; total: number }>("/api/submissions?limit=25");
      setHistory(h);
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Generation failed", "error");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    try {
      const h = await apiJson<{ items: unknown[]; total: number }>("/api/submissions?limit=25");
      setHistory(h);
    } catch {
      showToast("Failed to load history", "error");
    }
  }

  useEffect(() => {
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once on mount
  }, []);

  const previewSrc = submissionId ? `/api/preview/${submissionId}` : "";

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <Toast message={toast} variant={toastVariant} onClose={() => setToast(null)} />
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 lg:flex-row">
        <section className="flex w-full flex-col gap-4 lg:w-[40%]">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">
            Controls
          </h2>
          <label className="flex flex-col gap-1 text-sm">
            <span>Template</span>
            <select
              className="min-tap rounded border border-[var(--color-border)] bg-transparent px-2 py-2"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.origin})
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span>Data file</span>
            <select
              className="min-tap rounded border border-[var(--color-border)] bg-transparent px-2 py-2"
              value={dataFileId}
              onChange={(e) => setDataFileId(e.target.value)}
            >
              {dataFiles.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.origin})
                </option>
              ))}
            </select>
          </label>
          <div className="rounded border border-[var(--color-border)] p-3 text-sm">
            <p className="mb-2 font-medium">Options</p>
            <label className="flex min-h-[44px] items-center gap-2 py-1">
              <input type="checkbox" checked={generatePdf} onChange={(e) => setGeneratePdf(e.target.checked)} />
              Generate PDF (full build)
            </label>
            <label className="flex min-h-[44px] items-center gap-2 py-1">
              <input type="checkbox" checked={runAts} onChange={(e) => setRunAts(e.target.checked)} />
              Run ATS compliance check
            </label>
            <label className="flex min-h-[44px] flex-col gap-1 py-2">
              <span>PDF/A variant</span>
              <select
                className="rounded border border-[var(--color-border)] bg-transparent px-2 py-2"
                value={pdfVariant}
                onChange={(e) => setPdfVariant(e.target.value)}
              >
                <option value="pdf/a-1b">PDF/A-1b</option>
                <option value="pdf/a-2b">PDF/A-2b</option>
                <option value="pdf/a-3b">PDF/A-3b</option>
                <option value="pdf/a-4b">PDF/A-4b</option>
              </select>
            </label>
            <label className="flex min-h-[44px] items-center gap-2 py-1">
              <input type="checkbox" checked={developerHtml} onChange={(e) => setDeveloperHtml(e.target.checked)} />
              Developer: include HTML download
            </label>
          </div>
          <button
            type="button"
            disabled={loading}
            className="min-tap rounded bg-[var(--color-accent)] py-3 text-[var(--color-accent-fg)] disabled:opacity-50"
            onClick={() => void fullGenerate(false)}
          >
            {loading ? "Working…" : "Generate & save to outputs"}
          </button>
          {runAts && atsReport ? (
            <button
              type="button"
              className="min-tap rounded border border-[var(--color-border)] py-2 text-sm"
              onClick={() => setShowAts(true)}
            >
              View ATS report
            </button>
          ) : null}
        </section>
        <section className="flex w-full flex-1 flex-col gap-4 lg:w-[60%]">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">Preview</h2>
          <div className="relative min-h-[480px] flex-1 overflow-hidden rounded border border-[var(--color-border)] bg-white dark:bg-neutral-900">
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-black/10 text-sm">Loading…</div>
            ) : null}
            {previewSrc ? (
              <iframe title="PDF preview" src={previewSrc} className="h-[70vh] w-full" />
            ) : (
              <p className="p-4 text-sm text-[var(--color-muted)]">Select template and data to preview.</p>
            )}
          </div>
          <div className="sticky bottom-0 flex flex-wrap gap-2 border-t border-[var(--color-border)] bg-[var(--color-bg)] py-3">
            {submissionId ? (
              <>
                <a
                  className="min-tap inline-flex items-center justify-center rounded border border-[var(--color-border)] px-3 text-sm"
                  href={`/api/download/${submissionId}/pdf`}
                >
                  Download PDF
                </a>
                <a
                  className="min-tap inline-flex items-center justify-center rounded border border-[var(--color-border)] px-3 text-sm"
                  href={`/api/download/${submissionId}/docx`}
                >
                  Download DOCX
                </a>
                {developerHtml ? (
                  <a
                    className="min-tap inline-flex items-center justify-center rounded border border-[var(--color-border)] px-3 text-sm"
                    href={`/api/download/${submissionId}/html`}
                  >
                    Download HTML
                  </a>
                ) : null}
              </>
            ) : null}
          </div>
        </section>
      </div>
      {showAts && atsReport ? (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="max-h-[80vh] w-full max-w-lg overflow-auto rounded border border-[var(--color-border)] bg-[var(--color-bg)] p-4 text-sm shadow-lg">
            <div className="mb-3 flex justify-between">
              <h3 className="font-semibold">ATS report</h3>
              <button type="button" className="min-tap px-2" onClick={() => setShowAts(false)}>
                Close
              </button>
            </div>
            <Section title="Errors" items={atsReport.errors} />
            <Section title="Warnings" items={atsReport.warnings} />
            <Section title="Suggestions" items={atsReport.suggestions} />
          </div>
        </div>
      ) : null}
      <section className="mx-auto w-full max-w-6xl px-4 pb-10">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">History</h2>
          <button type="button" className="text-sm underline" onClick={() => void loadHistory()}>
            Refresh
          </button>
        </div>
        <div className="overflow-x-auto rounded border border-[var(--color-border)]">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-[var(--color-border)] bg-[var(--color-border)]/20">
              <tr>
                <th className="p-2">When</th>
                <th className="p-2">Template</th>
                <th className="p-2">Data</th>
                <th className="p-2">ATS</th>
                <th className="p-2">Formats</th>
              </tr>
            </thead>
            <tbody>
              {(history?.items as Record<string, unknown>[] | undefined)?.map((row) => (
                <tr key={String(row.id)} className="border-b border-[var(--color-border)]/60">
                  <td className="p-2 font-mono text-xs">{String(row.created_at)}</td>
                  <td className="p-2">{String(row.template_name)}</td>
                  <td className="p-2">{String(row.data_file)}</td>
                  <td className="p-2">{row.ats_check_run ? "yes" : "no"}</td>
                  <td className="p-2 font-mono text-xs">{JSON.stringify(row.output_formats)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="mb-3">
      <h4 className="mb-1 font-medium">{title}</h4>
      <ul className="list-inside list-disc text-[var(--color-muted)]">
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}
