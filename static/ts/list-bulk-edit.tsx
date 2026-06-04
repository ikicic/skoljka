import { createRoot } from "react-dom/client";
import { useMemo, useState } from "react";
import {
  ProblemDraftEditor,
  normalizeSelectedTags,
  type ProblemDraft,
} from "./components/ProblemDraftEditor";
import { ResizableColumns } from "./components/ResizableColumns";
import { PdfDocumentPreview } from "./components/PdfPreview";
import { gettext } from "./i18n";

interface InitialPayload {
  problems: ProblemDraft[];
  document?: {
    url: string;
    label: string;
  } | null;
}

interface SaveResponse {
  ok?: boolean;
  redirect_url?: string;
  error?: string;
}

const rootEl = document.getElementById("list-bulk-edit")!;
const saveUrl = rootEl.dataset.saveUrl!;
const suggestTagsUrl = rootEl.dataset.suggestTagsUrl!;
const listUrl = rootEl.dataset.listUrl!;
const csrfHeaders: Record<string, string> = JSON.parse(rootEl.dataset.csrf || "{}");
const initial: InitialPayload = JSON.parse(
  document.getElementById("list-bulk-edit-data")!.textContent || '{"problems":[]}',
);

function sameDraft(a: ProblemDraft[], b: ProblemDraft[]): boolean {
  return JSON.stringify(a.map(saveComparableProblem)) === JSON.stringify(b.map(saveComparableProblem));
}

function saveComparableProblem(problem: ProblemDraft) {
  const tags = normalizeSelectedTags(problem.tags);
  return {
    id: problem.id,
    sourceMd: problem.sourceMd,
    language: problem.language || "en",
    tags: tags.map((tag) => ({
      kind: tag.kind,
      slug: tag.slug,
      name: tag.name,
    })),
  };
}

function ListBulkEdit() {
  const [problems, setProblems] = useState<ProblemDraft[]>(initial.problems || []);
  const [saving, setSaving] = useState(false);
  const dirty = useMemo(() => !sameDraft(initial.problems || [], problems), [problems]);

  async function save() {
    if (saving || !dirty) return;
    setSaving(true);
    try {
      const response = await fetch(saveUrl, {
        method: "POST",
        headers: { ...csrfHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          problems: problems.map((problem) => {
            const tags = normalizeSelectedTags(problem.tags);
            return {
              id: problem.id,
              source_md: problem.sourceMd,
              language: problem.language || "en",
              tags: tags.filter((tag) => tag.kind === "existing").map((tag) => tag.slug),
              new_tags: tags.filter((tag) => tag.kind === "new").map((tag) => tag.name),
            };
          }),
        }),
      });
      const data = (await response.json().catch(() => ({ error: gettext("Invalid response") }))) as SaveResponse;
      if (!response.ok || !data.ok) {
        alert(data.error || gettext("Save failed"));
        return;
      }
      window.location.href = data.redirect_url || listUrl;
    } catch {
      alert(gettext("Network error during save"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="list-bulk-edit">
      {initial.document?.url ? (
        <ResizableColumns
          className="bulk-edit-with-pdf"
          minPercent={25}
          maxPercent={65}
          leftClassName="pdf-col-pdf bulk-edit-pdf-col"
          rightClassName="pdf-col-problems"
          left={(
            <PdfDocumentPreview
              url={initial.document.url}
              label={initial.document.label}
            />
          )}
          right={(
            <ProblemDraftEditor
              problems={problems}
              onChange={setProblems}
              suggestTagsUrl={suggestTagsUrl}
              csrfHeaders={csrfHeaders}
              emptyText={gettext("No problems yet.")}
            />
          )}
        />
      ) : (
        <ProblemDraftEditor
          problems={problems}
          onChange={setProblems}
          suggestTagsUrl={suggestTagsUrl}
          csrfHeaders={csrfHeaders}
          emptyText={gettext("No problems yet.")}
        />
      )}
      <div className="pdf-review-actions">
        <button type="button" className="btn" onClick={save} disabled={!dirty || saving}>
          {saving ? gettext("Saving problems...") : gettext("Save changes")}
        </button>
        <a href={listUrl} className="btn btn-secondary">{gettext("Back")}</a>
      </div>
    </div>
  );
}

createRoot(rootEl).render(<ListBulkEdit />);
