/** PDF import wizard. */

import { createRoot } from "react-dom/client";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { ResizableColumns } from "./components/ResizableColumns";
import { fetchTags, getCachedTags, type SelectedTag } from "./components/TagPicker";
import {
  ProblemDraftEditor,
  normalizeSelectedTags,
  type DraftAttachment,
} from "./components/ProblemDraftEditor";
import { useLocalStorage, purgeLocalStorage } from "./hooks/useLocalStorage";
import { gettext, interpolate, ngettext } from "./i18n";
import {
  deletePdf as idbDeletePdf,
  loadPdf as idbLoadPdf,
  purgePdfs as idbPurgePdfs,
  savePdf as idbSavePdf,
} from "./utils/pdfStore";
import {
  cancelJob,
  deleteJob,
  fetchFirstActiveJobId,
  fetchJob,
  type PdfImportApiConfig,
} from "./pdfImport/api";
import {
  ConfirmationView,
  MetaForm,
  PENDING_TRANSCRIPTION_PROGRESS,
  PdfPageCanvas,
  PdfThumbnail,
  ProblemSourceMeta,
  TranscriptionProgress,
} from "./pdfImport/components";
import {
  DRAFT_DEBOUNCE_MS,
  DRAFT_PREFIX,
  DRAFT_TTL_MS,
  findLatestDraftJobId,
  loadActiveJobId,
  storeActiveJobId,
} from "./pdfImport/persistence";
import { sortSourcesByHierarchy } from "./pdfImport/sourceOptions";
import type {
  JobProgress,
  JobResponse,
  JobStatus,
  SourceOption,
  Step,
  WizardDraft,
} from "./pdfImport/types";

// --- Read embedded data before React takes over ---

const rootEl = document.getElementById("pdf-import")!;
const transcribeUrl = rootEl.dataset.transcribeUrl!;
const activeUrl = rootEl.dataset.activeUrl!;
const suggestTagsUrl = rootEl.dataset.suggestTagsUrl!;
const createSourceUrl = rootEl.dataset.createSourceUrl!;
const confirmUrl = rootEl.dataset.confirmUrl!;
const csrfHeaders: Record<string, string> = JSON.parse(
  rootEl.dataset.csrf || "{}",
);
const initialSources: SourceOption[] = JSON.parse(
  document.getElementById("pdf-sources-data")!.textContent || "[]",
);

const apiConfig: PdfImportApiConfig = {
  transcribeUrl,
  activeUrl,
  csrfHeaders,
};

function imageAttachments(images: Record<string, string>): DraftAttachment[] {
  return Object.entries(images).map(([name, base64]) => ({
    name,
    url: `data:image/png;base64,${base64}`,
    is_image: true,
  }));
}

const EMPTY_DRAFT: WizardDraft = {
  problems: [],
  pages: [],
  sourceId: "",
  year: "",
  language: "",
  globalTags: [],
};

const POLL_INTERVAL_MS = 1000;

purgeLocalStorage(DRAFT_PREFIX, DRAFT_TTL_MS);
void idbPurgePdfs(DRAFT_TTL_MS);

const INITIAL_DRAFT_JOB_ID = findLatestDraftJobId();

// --- Main wizard ---

function PdfImportWizard() {
  // Server sends sources via source_options_payload() already in hierarchical order.
  const [sourceOptions, setSourceOptions] = useState<SourceOption[]>(() => initialSources);
  const [step, setStep] = useState<Step>(() =>
    INITIAL_DRAFT_JOB_ID ? "review" : "upload",
  );
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [selectedPages, setSelectedPages] = useState<Set<number>>(new Set());
  const keepOriginalPdfRef = useRef<HTMLInputElement>(null);
  const [uploadDragActive, setUploadDragActive] = useState(false);
  const [willSaveOriginalPdf, setWillSaveOriginalPdf] = useState(false);

  const [draftJobId, setDraftJobId] = useState<string | null>(
    INITIAL_DRAFT_JOB_ID,
  );
  const draftKey = draftJobId ? `${DRAFT_PREFIX}${draftJobId}` : null;
  const [draft, setDraft, clearDraft] = useLocalStorage<WizardDraft>(
    draftKey,
    EMPTY_DRAFT,
    { debounceMs: DRAFT_DEBOUNCE_MS },
  );

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobProgress, setJobProgress] = useState<JobProgress | null>(null);
  const [jobImages, setJobImages] = useState<Record<string, string>>({});
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getCachedTags()) fetchTags();
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const hydrateFromJob = useCallback(
    (job: JobResponse, pages: number[]) => {
      const sourceByKey = new Map(sourceOptions.map((source) => [source.slug, source]));
      const problems = (job.problems ?? []).map((p) => ({
        sourceMd: p.source_md,
        sourceId: sourceByKey.get(p.source_key || "")?.id.toString() || draft.sourceId,
        problemLabel: p.problem_label,
        tags: [] as SelectedTag[],
      }));
      setDraftJobId(job.id);
      setJobImages(job.images ?? {});
      setDraft({
        ...EMPTY_DRAFT,
        problems,
        pages,
        sourceId: draft.sourceId,
        year: job.year ? String(job.year) : draft.year,
        language: job.language || draft.language || EMPTY_DRAFT.language,
        globalTags: draft.globalTags,
      });
    },
    [draft.globalTags, draft.language, draft.sourceId, draft.year, setDraft, sourceOptions],
  );

  const pollOnce = useCallback(
    async (id: string) => {
      const job = await fetchJob(apiConfig, id);
      if (!job) {
        stopPolling();
        setJobId(null);
        setJobStatus(null);
        setJobProgress(null);
        storeActiveJobId(null);
        setStep("upload");
        return;
      }
      setJobStatus(job.status);
      setJobProgress(job.progress ?? null);
      if (job.status === "pending" || job.status === "running") {
        pollTimer.current = setTimeout(() => pollOnce(id), POLL_INTERVAL_MS);
        return;
      }
      stopPolling();
      storeActiveJobId(null);
      setJobId(null);
      if (job.status === "done") {
        const sorted = [...selectedPages].sort((a, b) => a - b);
        hydrateFromJob(job, sorted);
        setWillSaveOriginalPdf(Boolean(job.has_original_pdf));
        setStep("review");
      } else if (job.status === "failed") {
        alert(
          interpolate(gettext("Transcription failed: %(error)s"), {
            error: job.error || gettext("unknown error"),
          }),
        );
        void idbDeletePdf(id);
        void deleteJob(apiConfig, id);
        setStep("pages");
      } else if (job.status === "cancelled") {
        void idbDeletePdf(id);
        void deleteJob(apiConfig, id);
        setStep("pages");
      }
    },
    [hydrateFromJob, stopPolling, selectedPages],
  );

  const handleCancel = useCallback(async () => {
    if (!jobId) return;
    stopPolling();
    await cancelJob(apiConfig, jobId);
    void idbDeletePdf(jobId);
    void deleteJob(apiConfig, jobId);
    storeActiveJobId(null);
    setJobId(null);
    setJobStatus(null);
    setJobProgress(null);
    if (keepOriginalPdfRef.current) keepOriginalPdfRef.current.checked = true;
    setStep("pages");
  }, [jobId, stopPolling]);

  // Prefer active server work over a local draft.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let id = loadActiveJobId();
      if (!id) id = await fetchFirstActiveJobId(apiConfig);
      if (cancelled || !id) return;
      const job = await fetchJob(apiConfig, id);
      if (cancelled || !job) {
        storeActiveJobId(null);
        return;
      }
      if (job.status === "pending" || job.status === "running") {
        setJobId(id);
        setJobStatus(job.status);
        setJobProgress(job.progress ?? null);
        storeActiveJobId(id);
        setStep("transcribing");
        pollTimer.current = setTimeout(() => pollOnce(id), POLL_INTERVAL_MS);
      } else if (job.status === "done" && !INITIAL_DRAFT_JOB_ID) {
        hydrateFromJob(job, []);
        setWillSaveOriginalPdf(Boolean(job.has_original_pdf));
        storeActiveJobId(null);
        setStep("review");
      } else {
        storeActiveJobId(null);
      }
    })();
    return () => {
      cancelled = true;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!INITIAL_DRAFT_JOB_ID) return;
    let cancelled = false;
    (async () => {
      const job = await fetchJob(apiConfig, INITIAL_DRAFT_JOB_ID);
      if (!cancelled && job?.status === "done") {
        setWillSaveOriginalPdf(Boolean(job.has_original_pdf));
        setJobImages(job.images ?? {});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Restore the PDF panel for a recovered draft.
  useEffect(() => {
    if (!INITIAL_DRAFT_JOB_ID || pdfDoc) return;
    let cancelled = false;
    (async () => {
      const bytes = await idbLoadPdf(INITIAL_DRAFT_JOB_ID);
      if (cancelled || !bytes) return;
      try {
        const doc = await pdfjsLib.getDocument({ data: bytes }).promise;
        if (cancelled) return;
        setPdfDoc(doc);
        if (draft.pages.length > 0) setSelectedPages(new Set(draft.pages));
      } catch {
        // Review will show the re-upload notice.
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPdfFile = useCallback(async (file: File) => {
    setPdfFile(file);
    if (keepOriginalPdfRef.current) keepOriginalPdfRef.current.checked = true;
    const arrayBuffer = await file.arrayBuffer();
    const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    setPdfDoc(doc);
    const allPages = new Set<number>();
    for (let i = 1; i <= doc.numPages; i++) allPages.add(i);
    setSelectedPages(allPages);
    setStep("pages");
  }, []);

  const handleFileChange = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      await loadPdfFile(file);
    },
    [loadPdfFile],
  );

  const handleUploadDrag = useCallback((e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setUploadDragActive(e.type === "dragenter" || e.type === "dragover");
  }, []);

  const handleUploadDrop = useCallback(
    async (e: DragEvent<HTMLLabelElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setUploadDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (!file) return;
      await loadPdfFile(file);
    },
    [loadPdfFile],
  );

  const togglePage = useCallback((page: number) => {
    setSelectedPages((prev) => {
      const next = new Set(prev);
      if (next.has(page)) next.delete(page);
      else next.add(page);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    if (!pdfDoc) return;
    const all = new Set<number>();
    for (let i = 1; i <= pdfDoc.numPages; i++) all.add(i);
    setSelectedPages(all);
  }, [pdfDoc]);

  const deselectAll = useCallback(() => {
    setSelectedPages(new Set());
    setJobImages({});
  }, []);

  const handleTranscribe = useCallback(async () => {
    if (!pdfFile || selectedPages.size === 0) return;
    if (!draft.sourceId) {
      alert(gettext("Choose a source before importing."));
      return;
    }
    setStep("transcribing");
    setJobStatus("pending");
    setJobProgress(PENDING_TRANSCRIPTION_PROGRESS);

    const zeroBased = [...selectedPages]
      .map((p) => p - 1)
      .sort((a, b) => a - b);

    const formData = new FormData();
    formData.append("pdf", pdfFile);
    formData.append("pages", JSON.stringify(zeroBased));
    formData.append("source_id", draft.sourceId);
    if (keepOriginalPdfRef.current?.checked ?? true) formData.append("keep_original_pdf", "1");

    let resp: Response;
    try {
      resp = await fetch(transcribeUrl, {
        method: "POST",
        headers: csrfHeaders,
        body: formData,
      });
    } catch {
      alert(gettext("Network error during transcription"));
      setStep("pages");
      return;
    }

    if (!resp.ok) {
      const err = await resp
        .json()
        .catch(() => ({ error: gettext("Request failed") }));
      alert(err.error || gettext("Transcription failed"));
      setStep("pages");
      return;
    }

    const data = (await resp.json()) as JobResponse;
    setJobId(data.id);
    setJobStatus(data.status);
    setJobProgress(data.progress ?? PENDING_TRANSCRIPTION_PROGRESS);
    storeActiveJobId(data.id);
    try {
      const bytes = await pdfFile.arrayBuffer();
      void idbSavePdf(data.id, bytes);
    } catch {
      // Non-fatal.
    }
    pollTimer.current = setTimeout(() => pollOnce(data.id), POLL_INTERVAL_MS);
  }, [draft.sourceId, pdfFile, selectedPages, pollOnce]);

  // --- Draft updaters ---

  const setSourceId = useCallback(
    (v: string) => setDraft((d) => ({ ...d, sourceId: v })),
    [setDraft],
  );
  const addSourceOption = useCallback((source: SourceOption) => {
    setSourceOptions((options) => sortSourcesByHierarchy([...options.filter((item) => item.id !== source.id), source]));
  }, []);
  const setYear = useCallback(
    (v: string) => setDraft((d) => ({ ...d, year: v })),
    [setDraft],
  );
  const setLanguage = useCallback(
    (v: string) => setDraft((d) => ({ ...d, language: v })),
    [setDraft],
  );
  const setGlobalTags = useCallback(
    (tags: SelectedTag[]) => setDraft((d) => ({ ...d, globalTags: tags })),
    [setDraft],
  );
  const normalizedGlobalTags = useMemo(
    () => normalizeSelectedTags(draft.globalTags),
    [draft.globalTags],
  );
  const normalizedProblemTags = useMemo(
    () => draft.problems.map((p) => normalizeSelectedTags(p.tags)),
    [draft.problems],
  );

  const handleDiscardDraft = useCallback(() => {
    if (!confirm(
      gettext("Discard this import? Your edits will be lost."),
    )) return;
    clearDraft();
    if (draftJobId) {
      void idbDeletePdf(draftJobId);
      void deleteJob(apiConfig, draftJobId);
    }
    setDraftJobId(null);
    setPdfFile(null);
    setPdfDoc(null);
    setSelectedPages(new Set());
    if (keepOriginalPdfRef.current) keepOriginalPdfRef.current.checked = true;
    setWillSaveOriginalPdf(false);
    setStep("upload");
  }, [clearDraft, draftJobId]);

  const handleConfirm = useCallback(async () => {
    if (!draft.sourceId) {
      alert(gettext("Choose a source before importing."));
      setStep("review");
      return;
    }
    setStep("saving");

    const payload = {
      source_id: draft.sourceId ? parseInt(draft.sourceId, 10) : null,
      job_id: draftJobId,
      year: draft.year ? parseInt(draft.year, 10) : null,
      language: draft.language || "en",
      global_tags: normalizedGlobalTags
        .filter((tag) => tag.kind === "existing")
        .map((tag) => tag.slug),
      global_new_tags: normalizedGlobalTags
        .filter((tag) => tag.kind === "new")
        .map((tag) => tag.name),
      problems: draft.problems.map((p, i) => ({
        source_md: p.sourceMd,
        source_id: p.sourceId ? parseInt(p.sourceId, 10) : undefined,
        problem_label: p.problemLabel,
        tags: normalizedProblemTags[i]
          .filter((tag) => tag.kind === "existing")
          .map((tag) => tag.slug),
        new_tags: normalizedProblemTags[i]
          .filter((tag) => tag.kind === "new")
          .map((tag) => tag.name),
      })),
    };

    try {
      const resp = await fetch(confirmUrl, {
        method: "POST",
        headers: { ...csrfHeaders, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp
        .json()
        .catch(() => ({ error: gettext("Invalid response") }));

      if (!resp.ok) {
        alert(data.error || gettext("Import failed"));
        setStep("confirm");
        return;
      }

      clearDraft();
      if (draftJobId) {
        void idbDeletePdf(draftJobId);
        void deleteJob(apiConfig, draftJobId);
      }
      window.location.href = data.redirect_url;
    } catch {
      alert(gettext("Network error during import"));
      setStep("confirm");
    }
  }, [draft, normalizedGlobalTags, normalizedProblemTags, clearDraft, draftJobId]);

  const draftAttachments = useMemo(() => imageAttachments(jobImages), [jobImages]);

  const n = selectedPages.size;
  const sortedPages = [...selectedPages].sort((a, b) => a - b);

  const selectedSourceName = useMemo(() => {
    if (!draft.sourceId) return "";
    const s = sourceOptions.find((x) => x.id === parseInt(draft.sourceId, 10));
    return s ? s.name : "";
  }, [draft.sourceId, sourceOptions]);

  return (
    <>
      {/* Step 1: Upload */}
      {step === "upload" && (
        <div className="pdf-step">
          <p>{gettext("Select a PDF file to import problems from.")}</p>
          <label
            className={"pdf-upload-dropzone" + (uploadDragActive ? " active" : "")}
            onDragEnter={handleUploadDrag}
            onDragOver={handleUploadDrag}
            onDragLeave={handleUploadDrag}
            onDrop={handleUploadDrop}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
            />
            <span className="pdf-upload-title">{gettext("Drop PDF here")}</span>
            <span className="pdf-upload-subtitle">{gettext("or click to choose a file")}</span>
          </label>
        </div>
      )}

      {/* Step 2: Pages */}
      {step === "pages" && pdfDoc && (
        <div className="pdf-step">
          <MetaForm
            sourceId={draft.sourceId}
            onSourceChange={setSourceId}
            year={draft.year}
            onYearChange={setYear}
            language={draft.language}
            onLanguageChange={setLanguage}
            globalTags={normalizedGlobalTags}
            onGlobalTagsChange={setGlobalTags}
            keepOriginalPdfRef={keepOriginalPdfRef}
            sources={sourceOptions}
            onSourceCreated={addSourceOption}
            createSourceUrl={createSourceUrl}
            csrfHeaders={csrfHeaders}
          />
          <div className="pdf-pages-toolbar">
            <button type="button" className="btn btn-sm" onClick={selectAll}>
              {gettext("Select all")}
            </button>
            <button type="button" className="btn btn-sm" onClick={deselectAll}>
              {gettext("Deselect all")}
            </button>
            <span className="text-muted">
              {interpolate(
                ngettext("%(count)s page", "%(count)s pages", pdfDoc.numPages),
                { count: pdfDoc.numPages },
              )}
            </span>
          </div>
          <div className="pdf-thumbnails">
            {Array.from({ length: pdfDoc.numPages }, (_, i) => i + 1).map(
              (pageNum) => (
                <PdfThumbnail
                  key={pageNum}
                  pdfDoc={pdfDoc}
                  pageNum={pageNum}
                  selected={selectedPages.has(pageNum)}
                  onToggle={togglePage}
                />
              ),
            )}
          </div>
          <button
            type="button"
            className="btn"
            disabled={n === 0 || !draft.sourceId}
            onClick={handleTranscribe}
          >
            {n
              ? interpolate(
                  ngettext(
                    "Transcribe %(count)s page",
                    "Transcribe %(count)s pages",
                    n,
                  ),
                  { count: n },
                )
              : gettext("Transcribe selected pages")}
          </button>
        </div>
      )}

      {/* Step 3: Transcribing */}
      {step === "transcribing" && (
        <div className="pdf-step">
          <div className="spinner-container">
            <div className="spinner" />
            <p className="text-muted">
              {jobStatus === "pending"
                ? gettext("Queued...")
                : jobStatus === "running"
                  ? gettext("Transcribing selected pages...")
                  : gettext("Starting transcription...")}
            </p>
            <TranscriptionProgress progress={jobProgress} />
            {jobId && (
              <button
                type="button"
                className="btn btn-sm"
                onClick={handleCancel}
              >
                {gettext("Cancel")}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step 4: Review */}
      {step === "review" && (
        <div className="pdf-step">
          <MetaForm
            sourceId={draft.sourceId}
            onSourceChange={setSourceId}
            year={draft.year}
            onYearChange={setYear}
            language={draft.language}
            onLanguageChange={setLanguage}
            globalTags={normalizedGlobalTags}
            onGlobalTagsChange={setGlobalTags}
            sources={sourceOptions}
            onSourceCreated={addSourceOption}
            createSourceUrl={createSourceUrl}
            csrfHeaders={csrfHeaders}
          />
          {!pdfDoc && (
            <p className="text-muted">
              {gettext("Resumed from a previous session; re-upload the PDF to see it alongside the problems.")}
            </p>
          )}
          <ResizableColumns
            leftClassName="pdf-col-pdf"
            rightClassName="pdf-col-problems"
            left={
              pdfDoc ? (
                <>
                  {sortedPages.map((pageNum) => (
                    <PdfPageCanvas
                      key={pageNum}
                      pdfDoc={pdfDoc}
                      pageNum={pageNum}
                    />
                  ))}
                </>
              ) : (
                <p className="text-muted">{gettext("PDF not loaded.")}</p>
              )
            }
            right={
              <ProblemDraftEditor
                problems={draft.problems}
                onChange={(problems) => setDraft((d) => ({ ...d, problems }))}
                suggestTagsUrl={suggestTagsUrl}
                csrfHeaders={csrfHeaders}
                attachments={draftAttachments}
                renderMeta={(problem, index) => (
                  <ProblemSourceMeta
                    problem={problem}
                    index={index}
                    sources={sourceOptions}
                    onChange={(patch) => setDraft((d) => ({
                      ...d,
                      problems: d.problems.map((item, i) => (
                        i === index ? { ...item, ...patch } : item
                      )),
                    }))}
                  />
                )}
              />
            }
          />
          <div className="pdf-review-actions">
            {pdfDoc && (
              <button
                type="button"
                className="btn"
                onClick={() => setStep("pages")}
              >
                {gettext("Back to page selection")}
              </button>
            )}
            <button
              type="button"
              className="btn"
              onClick={() => {
                if (!draft.sourceId) {
                  alert(gettext("Choose a source before importing."));
                  return;
                }
                setStep("confirm");
              }}
              disabled={draft.problems.length === 0 || !draft.sourceId}
            >
              {gettext("Review & import")}
            </button>
            <button
              type="button"
              className="btn-link"
              onClick={handleDiscardDraft}
            >
              {gettext("Cancel import")}
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Confirm */}
      {step === "confirm" && (
        <div className="pdf-step">
          <p className="text-muted">
            {gettext("Please check the details below. Click Confirm to import, or Back to keep editing.")}
          </p>
          <ConfirmationView
            draft={draft}
            sourceName={selectedSourceName}
            sources={sourceOptions}
            willSaveOriginalPdf={willSaveOriginalPdf}
            attachments={draftAttachments}
          />
          <div className="pdf-review-actions">
            <button
              type="button"
              className="btn"
              onClick={() => setStep("review")}
            >
              {gettext("Back")}
            </button>
            <button type="button" className="btn" onClick={handleConfirm}>
              {willSaveOriginalPdf
                ? interpolate(
                    ngettext(
                      "Confirm - import %(count)s problem and save PDF",
                      "Confirm - import %(count)s problems and save PDF",
                      draft.problems.length,
                    ),
                    { count: draft.problems.length },
                  )
                : interpolate(
                    ngettext(
                      "Confirm - import %(count)s problem",
                      "Confirm - import %(count)s problems",
                      draft.problems.length,
                    ),
                    { count: draft.problems.length },
                  )}
            </button>
            <button
              type="button"
              className="btn-link"
              onClick={handleDiscardDraft}
            >
              {gettext("Cancel import")}
            </button>
          </div>
        </div>
      )}

      {/* Step 6: Saving */}
      {step === "saving" && (
        <div className="pdf-step">
          <div className="spinner-container">
            <div className="spinner" />
            <p className="text-muted">{gettext("Saving problems...")}</p>
          </div>
        </div>
      )}
    </>
  );
}

// --- Mount ---

createRoot(rootEl).render(<PdfImportWizard />);
