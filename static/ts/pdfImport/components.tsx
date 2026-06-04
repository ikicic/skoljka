import { useEffect, useRef, useState, type RefObject } from "react";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

import { PdfPageCanvas, renderPdfPage } from "../components/PdfPreview";
import { TagPicker, getCachedTags, type SelectedTag } from "../components/TagPicker";
import { normalizeSelectedTags, type DraftAttachment, type ProblemDraft } from "../components/ProblemDraftEditor";
import { compileMarkdown } from "../content-markdown";
import { gettext, interpolate, ngettext } from "../i18n";
import { sourceOptionLabel, slugifySource } from "./sourceOptions";
import type {
  CreateSourceResponse,
  JobProgress,
  JobProgressStep,
  ProgressStepStatus,
  SourceOption,
  WizardDraft,
} from "./types";

const THUMB_WIDTH = 200;

export const PENDING_TRANSCRIPTION_PROGRESS: JobProgress = {
  current: null,
  steps: [
    { key: "ocr", label: "OCR", status: "pending" },
    { key: "llm", label: "LLM cleanup", status: "pending" },
  ],
};

export function PdfThumbnail({
  pdfDoc,
  pageNum,
  selected,
  onToggle,
}: {
  pdfDoc: pdfjsLib.PDFDocumentProxy;
  pageNum: number;
  selected: boolean;
  onToggle: (page: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (canvasRef.current) {
      renderPdfPage(pdfDoc, pageNum, canvasRef.current, THUMB_WIDTH);
    }
  }, [pdfDoc, pageNum]);

  return (
    <label className={`pdf-thumb${selected ? " selected" : ""}`}>
      <canvas ref={canvasRef} />
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggle(pageNum)}
      />
      <span className="pdf-thumb-num">{pageNum}</span>
    </label>
  );
}

export function MetaForm({
  sourceId,
  onSourceChange,
  year,
  onYearChange,
  language,
  onLanguageChange,
  globalTags,
  onGlobalTagsChange,
  keepOriginalPdfRef,
  sources,
  onSourceCreated,
  createSourceUrl,
  csrfHeaders,
}: {
  sourceId: string;
  onSourceChange: (v: string) => void;
  year: string;
  onYearChange: (v: string) => void;
  language: string;
  onLanguageChange: (v: string) => void;
  globalTags: SelectedTag[];
  onGlobalTagsChange: (tags: SelectedTag[]) => void;
  keepOriginalPdfRef?: RefObject<HTMLInputElement | null>;
  sources: SourceOption[];
  onSourceCreated: (source: SourceOption) => void;
  createSourceUrl: string;
  csrfHeaders: Record<string, string>;
}) {
  const [showSourceForm, setShowSourceForm] = useState(false);
  const selectedSource = sources.find((s) => String(s.id) === sourceId);
  const pdfDestination = selectedSource
    ? year
      ? interpolate(gettext("The whole PDF will be attached to %(source)s, %(year)s."), {
          source: selectedSource.name,
          year,
        })
      : interpolate(gettext("The whole PDF will be attached to %(source)s."), {
          source: selectedSource.name,
        })
    : gettext("Choose a source to decide where the whole PDF will be attached.");
  return (
    <div className="pdf-meta-form form-stack">
      <div className="form-row-inline">
        <div className="form-field">
          <label htmlFor="pdf-source">{gettext("Source")}</label>
          <div className="input-with-action">
            <select
              id="pdf-source"
              value={sourceId}
              onChange={(e) => onSourceChange(e.target.value)}
              required
            >
              <option value="">{gettext("-- Select source --")}</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {sourceOptionLabel(s)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setShowSourceForm(true)}
            >
              {gettext("New source")}
            </button>
          </div>
        </div>
        <div className="form-field">
          <label htmlFor="pdf-year">{gettext("Year")}</label>
          <input
            id="pdf-year"
            type="number"
            value={year}
            onChange={(e) => onYearChange(e.target.value)}
            placeholder={gettext("e.g. 2024")}
          />
        </div>
        <div className="form-field">
          <label htmlFor="pdf-language">{gettext("Language")}</label>
          <input
            id="pdf-language"
            type="text"
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            placeholder={gettext("hr or en")}
            className="form-field-max-narrow"
          />
        </div>
      </div>
      <div className="form-field">
        <label>{gettext("Tags for all problems")}</label>
        <TagPicker selected={globalTags} onChange={onGlobalTagsChange} />
      </div>
      {keepOriginalPdfRef && (
        <label className="checkbox-row">
          <input
            ref={keepOriginalPdfRef}
            type="checkbox"
            defaultChecked
          />
          <span>
            {gettext("Save whole PDF")}
            <small className="text-muted">{pdfDestination}</small>
          </span>
        </label>
      )}
      {showSourceForm && (
        <InlineSourceForm
          sources={sources}
          createSourceUrl={createSourceUrl}
          csrfHeaders={csrfHeaders}
          onCancel={() => setShowSourceForm(false)}
          onCreated={(source) => {
            onSourceCreated(source);
            onSourceChange(String(source.id));
            setShowSourceForm(false);
          }}
        />
      )}
    </div>
  );
}

function InlineSourceForm({
  sources,
  createSourceUrl,
  csrfHeaders,
  onCancel,
  onCreated,
}: {
  sources: SourceOption[];
  createSourceUrl: string;
  csrfHeaders: Record<string, string>;
  onCancel: () => void;
  onCreated: (source: SourceOption) => void;
}) {
  const [nameEn, setNameEn] = useState("");
  const [nameHr, setNameHr] = useState("");
  const [slug, setSlug] = useState("");
  const [parent, setParent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);

  function updateNameEn(value: string) {
    setNameEn(value);
    if (!slugEdited) setSlug(slugifySource(value));
  }

  async function saveSource() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(createSourceUrl, {
        method: "POST",
        headers: { ...csrfHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          slug,
          name_en: nameEn,
          name_hr: nameHr,
          parent,
        }),
      });
      const data = (await response
        .json()
        .catch(() => ({ error: gettext("Invalid response") }))) as CreateSourceResponse;
      if (!response.ok || !data.source) {
        setError(data.error || gettext("Could not create source."));
        return;
      }
      onCreated(data.source);
    } catch {
      setError(gettext("Network error while creating source."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="inline-panel form-stack">
      {error && <div className="form-errors">{error}</div>}
      <div className="form-row-inline">
        <div className="form-field">
          <label htmlFor="pdf-source-name-en">{gettext("Name (EN)")}</label>
          <input
            id="pdf-source-name-en"
            type="text"
            value={nameEn}
            onChange={(e) => updateNameEn(e.target.value)}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="pdf-source-name-hr">{gettext("Name (HR)")}</label>
          <input
            id="pdf-source-name-hr"
            type="text"
            value={nameHr}
            onChange={(e) => setNameHr(e.target.value)}
          />
        </div>
      </div>
      <div className="form-row-inline">
        <div className="form-field">
          <label htmlFor="pdf-source-slug">{gettext("Slug")}</label>
          <input
            id="pdf-source-slug"
            type="text"
            value={slug}
            onChange={(e) => {
              setSlugEdited(true);
              setSlug(slugifySource(e.target.value));
            }}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="pdf-source-parent">{gettext("Parent")}</label>
          <select
            id="pdf-source-parent"
            value={parent}
            onChange={(e) => setParent(e.target.value)}
          >
            <option value="">{gettext("-- No parent --")}</option>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {sourceOptionLabel(source)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-sm"
          onClick={saveSource}
          disabled={saving || !nameEn.trim() || !slug.trim()}
        >
          {saving ? gettext("Creating source...") : gettext("Create source")}
        </button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={onCancel}>
          {gettext("Cancel")}
        </button>
      </div>
    </div>
  );
}

export function ProblemSourceMeta({
  problem,
  index,
  sources,
  onChange,
}: {
  problem: ProblemDraft;
  index: number;
  sources: SourceOption[];
  onChange: (patch: Partial<ProblemDraft>) => void;
}) {
  return (
    <div className="form-row-inline pdf-problem-meta-fields">
      <div className="form-field">
        <label htmlFor={`pdf-problem-source-${index}`}>{gettext("Source")}</label>
        <select
          id={`pdf-problem-source-${index}`}
          value={problem.sourceId || ""}
          onChange={(e) => onChange({ sourceId: e.target.value })}
        >
          {sources.map((source) => (
            <option key={source.id} value={source.id}>
              {sourceOptionLabel(source)}
            </option>
          ))}
        </select>
      </div>
      <div className="form-field form-field-max-narrow">
        <label htmlFor={`pdf-problem-number-${index}`}>{gettext("Problem")}</label>
        <input
          id={`pdf-problem-number-${index}`}
          type="text"
          value={problem.problemLabel || String(index + 1)}
          onChange={(e) => onChange({ problemLabel: e.target.value.trim() || undefined })}
        />
      </div>
    </div>
  );
}

function TagPills({ tags }: { tags: SelectedTag[] }) {
  if (tags.length === 0) return <span className="text-muted">-</span>;
  const cached = getCachedTags();
  return (
    <span className="tag-list-inline">
      {tags.map((tag) => {
        const option = cached?.find((t) => t.slug === tag.slug);
        return (
          <span key={`${tag.kind}:${tag.slug}`} className="tag">
            {option?.name || tag.name}
          </span>
        );
      })}
    </span>
  );
}

function progressStepLabel(step: JobProgressStep): string {
  if (step.key === "ocr") return gettext("OCR");
  if (step.key === "llm") return gettext("LLM cleanup");
  return step.label;
}

function progressStatusLabel(status: ProgressStepStatus): string {
  switch (status) {
    case "running":
      return gettext("Running");
    case "done":
      return gettext("Done");
    case "failed":
      return gettext("Failed");
    case "pending":
    default:
      return gettext("Pending");
  }
}

export function TranscriptionProgress({ progress }: { progress: JobProgress | null }) {
  const steps = progress?.steps?.length
    ? progress.steps
    : PENDING_TRANSCRIPTION_PROGRESS.steps;
  return (
    <div className="transcription-progress" aria-live="polite">
      {steps.map((step) => (
        <div
          key={step.key}
          className={`transcription-progress-step ${step.status}`.trim()}
        >
          <span className="transcription-progress-dot" aria-hidden="true" />
          <span className="transcription-progress-label">{progressStepLabel(step)}</span>
          <span className="transcription-progress-status">{progressStatusLabel(step.status)}</span>
        </div>
      ))}
    </div>
  );
}

export function ConfirmationView({
  draft,
  sourceName,
  sources,
  willSaveOriginalPdf,
  attachments,
}: {
  draft: WizardDraft;
  sourceName: string;
  sources: SourceOption[];
  willSaveOriginalPdf: boolean;
  attachments: DraftAttachment[];
}) {
  const sourceById = new Map(sources.map((source) => [String(source.id), source]));
  const attachmentUrls = Object.fromEntries(attachments.map((attachment) => [
    attachment.name,
    attachment.url,
  ]));
  const pdfDestination = draft.year
    ? interpolate(gettext("The whole PDF will be saved for %(source)s, %(year)s."), {
        source: sourceName || gettext("(none)"),
        year: draft.year,
      })
    : interpolate(gettext("The whole PDF will be saved for %(source)s."), {
        source: sourceName || gettext("(none)"),
      });
  return (
    <div className="pdf-confirm">
      <div className="pdf-meta-form form-stack">
        <div className="form-row-inline">
          <div className="form-field">
            <span className="form-field-label">{gettext("Source")}</span>
            <span>{sourceName || <em className="text-muted">{gettext("(none)")}</em>}</span>
          </div>
          <div className="form-field">
            <span className="form-field-label">{gettext("Year")}</span>
            <span>{draft.year || <em className="text-muted">{gettext("(none)")}</em>}</span>
          </div>
          <div className="form-field">
            <span className="form-field-label">{gettext("Language")}</span>
            <span>{draft.language}</span>
          </div>
        </div>
        <div className="form-field">
          <span className="form-field-label">{gettext("Tags for all problems")}</span>
          <TagPills tags={normalizeSelectedTags(draft.globalTags)} />
        </div>
        <div className="form-field">
          <span className="form-field-label">{gettext("Original PDF")}</span>
          <span>
            {willSaveOriginalPdf ? pdfDestination : gettext("The original PDF will not be saved.")}
          </span>
        </div>
      </div>
      {draft.problems.map((p, i) => (
        <div key={i} className="pdf-problem-card">
          <div className="pdf-problem-header">
            <span className="pdf-problem-index">{sourceById.get(p.sourceId || "")?.name || sourceName || gettext("(none)")}</span>
            <span className="pdf-problem-index">
              {interpolate(gettext("Problem %(number)s."), { number: p.problemLabel || i + 1 })}
            </span>
            <TagPills tags={normalizeSelectedTags(p.tags)} />
          </div>
          <div
            className="pdf-problem-body content-editor-preview math-content"
            dangerouslySetInnerHTML={{ __html: compileMarkdown(p.sourceMd, attachmentUrls) }}
          />
        </div>
      ))}
    </div>
  );
}

export { PdfPageCanvas };
