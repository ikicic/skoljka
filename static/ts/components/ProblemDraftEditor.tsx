import { useCallback, useState, type ReactNode } from "react";
import { ContentEditor } from "./ContentEditor";
import {
  TagPicker,
  fetchTags,
  type SelectedTag,
  type TagSuggestionState,
} from "./TagPicker";
import { gettext, interpolate } from "../i18n";

export interface ProblemDraft {
  id?: number;
  sourceMd: string;
  sourceId?: string;
  problemLabel?: string;
  language?: string;
  tags: SelectedTag[];
}

export interface DraftAttachment {
  name: string;
  url: string;
  is_image?: boolean;
}

interface TagSuggestionsResponse {
  tags?: string[][];
  error?: string;
}

export function normalizeSelectedTags(value: unknown): SelectedTag[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (
      item &&
      typeof item === "object" &&
      "slug" in item &&
      "name" in item &&
      typeof item.slug === "string" &&
      typeof item.name === "string" &&
      (item.kind === "existing" || item.kind === "new")
    ) {
      const suggestionState = "suggestionState" in item && isTagSuggestionState(item.suggestionState)
        ? item.suggestionState
        : undefined;
      return [{
        kind: item.kind,
        slug: item.slug,
        name: item.name,
        ...(suggestionState ? { suggestionState } : {}),
      } as SelectedTag];
    }
    return [];
  });
}

function isTagSuggestionState(value: unknown): value is TagSuggestionState {
  return value === "confirmed" || value === "suggested" || value === "not-suggested";
}

export function ProblemDraftEditor({
  problems,
  onChange,
  suggestTagsUrl,
  csrfHeaders,
  emptyText = gettext("No problems transcribed."),
  renderMeta,
  attachments = [],
}: {
  problems: ProblemDraft[];
  onChange: (problems: ProblemDraft[]) => void;
  suggestTagsUrl: string;
  csrfHeaders: Record<string, string>;
  emptyText?: string;
  renderMeta?: (problem: ProblemDraft, index: number) => ReactNode;
  attachments?: DraftAttachment[];
}) {
  const [suggestingTags, setSuggestingTags] = useState(false);

  const updateProblemText = useCallback((index: number, value: string) => {
    onChange(problems.map((p, i) => (i === index ? { ...p, sourceMd: value } : p)));
  }, [onChange, problems]);

  const updateProblemTags = useCallback((index: number, tags: SelectedTag[]) => {
    onChange(problems.map((p, i) => (i === index ? { ...p, tags } : p)));
  }, [onChange, problems]);

  const handleSuggestTags = useCallback(async () => {
    if (suggestingTags || problems.length === 0) return;
    setSuggestingTags(true);
    try {
      const resp = await fetch(suggestTagsUrl, {
        method: "POST",
        headers: { ...csrfHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          problems: problems.map((problem) => ({ source_md: problem.sourceMd })),
        }),
      });
      const data = (await resp
        .json()
        .catch(() => ({ error: gettext("Invalid response") }))) as TagSuggestionsResponse;
      if (!resp.ok || !Array.isArray(data.tags)) {
        alert(data.error || gettext("Tag suggestion failed"));
        return;
      }

      const tagOptions = await fetchTags();
      const bySlug = new Map(tagOptions.map((tag) => [tag.slug, tag]));
      onChange(problems.map((problem, index) => {
        const suggested = new Set(data.tags?.[index] || []);
        const existing = normalizeSelectedTags(problem.tags);
        const taggedExisting = existing.map((tag): SelectedTag => {
          if (tag.kind !== "existing") return tag;
          return {
            ...tag,
            suggestionState: suggested.has(tag.slug) ? "confirmed" : "not-suggested",
          };
        });
        const seen = new Set(taggedExisting.map((tag) => tag.slug));
        const additions = [...suggested].flatMap((slug) => {
          if (seen.has(slug)) return [];
          const option = bySlug.get(slug);
          if (!option) return [];
          seen.add(slug);
          return [{
            kind: "existing" as const,
            slug,
            name: option.name,
            suggestionState: "suggested" as const,
          }];
        });
        return { ...problem, tags: [...taggedExisting, ...additions] };
      }));
    } catch {
      alert(gettext("Network error during tag suggestion"));
    } finally {
      setSuggestingTags(false);
    }
  }, [csrfHeaders, onChange, problems, suggestTagsUrl, suggestingTags]);

  return (
    <div className="problem-draft-editor">
      <div className="problem-draft-actions">
        <button
          type="button"
          className="btn btn-sm"
          onClick={handleSuggestTags}
          disabled={problems.length === 0 || suggestingTags}
        >
          {suggestingTags ? gettext("Suggesting tags...") : gettext("Autosuggest tags")}
        </button>
      </div>
      {problems.length === 0 ? (
        <p className="text-muted">{emptyText}</p>
      ) : (
        problems.map((p, i) => (
          <ProblemDraftCard
            key={p.id ?? i}
            index={i}
            value={p.sourceMd}
            onChange={(v) => updateProblemText(i, v)}
            problemTags={normalizeSelectedTags(p.tags)}
            onTagsChange={(tags) => updateProblemTags(i, tags)}
            meta={renderMeta?.(p, i)}
            attachments={attachments}
          />
        ))
      )}
    </div>
  );
}

function ProblemDraftCard({
  index,
  value,
  onChange,
  problemTags,
  onTagsChange,
  meta,
  attachments,
}: {
  index: number;
  value: string;
  onChange: (v: string) => void;
  problemTags: SelectedTag[];
  onTagsChange: (tags: SelectedTag[]) => void;
  meta?: ReactNode;
  attachments: DraftAttachment[];
}) {
  return (
    <div className="pdf-problem-card">
      <div className="pdf-problem-header">
        <span className="pdf-problem-index">
          {interpolate(gettext("Problem %(number)s."), { number: index + 1 })}
        </span>
        <TagPicker selected={problemTags} onChange={onTagsChange} />
      </div>
      {meta && <div className="pdf-problem-meta">{meta}</div>}
      <div className="pdf-problem-body">
        <ContentEditor
          value={value}
          onChange={onChange}
          layout="vertical"
          verticalOrder="preview-source"
          className="pdf-content-editor"
          previewClassName="pdf-content-preview"
          attachments={attachments}
        />
      </div>
    </div>
  );
}
