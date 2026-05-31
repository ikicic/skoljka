/**
 * TagPicker - autocomplete tag selection with chips.
 *
 * The component uses tag slugs as its frontend identity. Existing tags submit
 * as `tags=<slug>`, while newly typed tags submit as `new_tags=<name>`.
 */

import { hydrateRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import { gettext } from "../i18n";

export interface TagOption {
  name: string;
  fullName?: string;
  slug: string;
  kind?: string;
}

export type TagSuggestionState = "confirmed" | "suggested" | "not-suggested";

export type SelectedTag =
  | { kind: "existing"; slug: string; name: string; suggestionState?: TagSuggestionState }
  | { kind: "new"; slug: string; name: string; suggestionState?: TagSuggestionState };

let cachedTags: TagOption[] | null = null;
let fetchPromise: Promise<TagOption[]> | null = null;

interface TagApiResponse {
  names: string[];
  full_names?: string[];
  slugs: string[];
  kinds: string[];
}

function slugifyTag(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function queryAutocompletePart(query: string): { prefix: string; term: string } {
  const match = query.match(/^(.*?)([^\s]+)$/);
  return match ? { prefix: match[1], term: match[2] } : { prefix: query, term: "" };
}

export function fetchTags(): Promise<TagOption[]> {
  if (cachedTags) return Promise.resolve(cachedTags);
  if (!fetchPromise) {
    const url = document.body.dataset.tagApiUrl;
    if (!url) return Promise.reject(new Error("Missing tag API URL."));
    fetchPromise = fetch(url)
      .then((r) => r.json())
      .then((data: TagApiResponse) => {
        cachedTags = data.slugs.map((slug, i) => ({
          slug,
          name: data.names[i],
          fullName: data.full_names?.[i],
          kind: data.kinds[i],
        }));
        return cachedTags;
      });
  }
  return fetchPromise;
}

export function getCachedTags(): TagOption[] | null {
  return cachedTags;
}

interface Props {
  selected: SelectedTag[];
  onChange: (tags: SelectedTag[]) => void;
  inputName?: string;
  queryInputName?: string;
  initialQuery?: string;
  placeholder?: string;
  inputType?: string;
  allowNew?: boolean;
  submitOnEnterWhenNoMatch?: boolean;
}

export function TagPicker({
  selected,
  onChange,
  inputName,
  queryInputName,
  initialQuery = "",
  placeholder = gettext("Add tag..."),
  inputType = "text",
  allowNew = true,
  submitOnEnterWhenNoMatch = false,
}: Props) {
  const [tags, setTags] = useState<TagOption[]>(cachedTags || []);
  const [query, setQuery] = useState(initialQuery);
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [focusedPill, setFocusedPill] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!cachedTags) {
      fetchTags().then(setTags);
    }
  }, []);

  const selectedSlugs = new Set(selected.map((tag) => tag.slug));
  const trimmedQuery = query.trim();
  const autocompletePart = queryInputName ? queryAutocompletePart(query) : { prefix: "", term: trimmedQuery };
  const tagQuery = autocompletePart.term.trim();
  const matches =
    tagQuery === ""
      ? []
      : tags
          .filter(
            (tag) =>
              !selectedSlugs.has(tag.slug) && (
                tag.name.toLowerCase().includes(tagQuery.toLowerCase()) ||
                (tag.fullName || "").toLowerCase().includes(tagQuery.toLowerCase())
              ),
          )
          .slice(0, 10);

  function selectedDisplay(tag: SelectedTag): SelectedTag {
    if (tag.kind === "new") return tag;
    const option = tags.find((t) => t.slug === tag.slug);
    return option ? { ...tag, slug: option.slug, name: option.name } : tag;
  }

  function finishAdd(next: SelectedTag, nextQuery = "") {
    if (selectedSlugs.has(next.slug)) return;
    onChange([...selected, next]);
    setQuery(nextQuery);
    setOpen(false);
    setHighlightedIndex(0);
    setFocusedPill(-1);
    inputRef.current?.focus();
  }

  function addExisting(tag: TagOption) {
    finishAdd(
      { kind: "existing", slug: tag.slug, name: tag.name },
      queryInputName ? autocompletePart.prefix.trimEnd() : "",
    );
  }

  function addNew(name: string) {
    const cleanName = name.trim();
    const slug = slugifyTag(cleanName);
    if (!cleanName || !slug) return;
    const existing = tags.find((tag) => tag.slug === slug);
    if (existing) {
      addExisting(existing);
    } else {
      finishAdd({ kind: "new", slug, name: cleanName });
    }
  }

  function removeAt(index: number) {
    onChange(selected.filter((_tag, i) => i !== index));
  }

  function removeFocusedPill() {
    if (focusedPill < 0 || focusedPill >= selected.length) return;
    removeAt(focusedPill);
    const newLen = selected.length - 1;
    if (newLen === 0) {
      setFocusedPill(-1);
      inputRef.current?.focus();
    } else if (focusedPill >= newLen) {
      setFocusedPill(newLen - 1);
    }
    inputRef.current?.focus();
  }

  function inputCaretAtStart(): boolean {
    const input = inputRef.current;
    if (!input) return query === "";
    return input.selectionStart === 0 && input.selectionEnd === 0;
  }

  function focusLastPill() {
    setFocusedPill(selected.length - 1);
    inputRef.current?.focus();
  }

  function handleInputKeyDown(e: React.KeyboardEvent) {
    if (focusedPill >= 0) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setFocusedPill((i) => Math.max(i - 1, 0));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        if (focusedPill < selected.length - 1) {
          setFocusedPill(focusedPill + 1);
        } else {
          setFocusedPill(-1);
        }
      } else if (e.key === "Backspace" || e.key === "Delete") {
        e.preventDefault();
        removeFocusedPill();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setFocusedPill(-1);
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        setFocusedPill(-1);
        setOpen(true);
      }
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      if (matches.length > 0) {
        addExisting(matches[highlightedIndex] ?? matches[0]);
      } else if (allowNew) {
        addNew(query);
      } else if (submitOnEnterWhenNoMatch) {
        inputRef.current?.form?.requestSubmit();
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlightedIndex((i) => Math.min(i + 1, Math.max(matches.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "ArrowLeft" && selected.length > 0 && inputCaretAtStart()) {
      e.preventDefault();
      focusLastPill();
    } else if (e.key === "Backspace" && selected.length > 0 && inputCaretAtStart()) {
      e.preventDefault();
      focusLastPill();
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery("");
    }
  }

  function focusInput() {
    setFocusedPill(-1);
    inputRef.current?.focus();
  }

  return (
    <div
      ref={containerRef}
      className={`tag-picker${focusedPill >= 0 ? " tag-picker-pill-focused" : ""}`}
      onClick={focusInput}
    >
      {selected.map((rawTag, i) => {
        const tag = selectedDisplay(rawTag);
        const stateClass = tag.suggestionState ? ` tag-pill-${tag.suggestionState}` : "";
        return (
          <span
            key={`${tag.kind}:${tag.slug}`}
            className={`tag-pill${tag.kind === "new" ? " tag-pill-new" : ""}${stateClass}${i === focusedPill ? " tag-pill-focused" : ""}`}
            title={tag.kind === "existing" ? tags.find((option) => option.slug === tag.slug)?.fullName : undefined}
          >
            {tag.name}
            {tag.kind === "new" && <sup>{gettext("NEW")}</sup>}
            <button
              type="button"
              className="tag-pill-remove"
              onClick={(e) => {
                e.stopPropagation();
                removeAt(i);
              }}
              tabIndex={-1}
            >
              ×
            </button>
          </span>
        );
      })}
      <input
        ref={inputRef}
        type={inputType}
        name={queryInputName}
        className="tag-picker-input"
        placeholder={selected.length === 0 ? placeholder : ""}
        value={query}
        onChange={(e) => {
          setFocusedPill(-1);
          setQuery(e.target.value);
          setOpen(true);
          setHighlightedIndex(0);
        }}
        onKeyDown={handleInputKeyDown}
        onFocus={() => {
          if (query.trim()) setOpen(true);
        }}
        onBlur={() => setTimeout(() => {
          setOpen(false);
          if (!containerRef.current?.contains(document.activeElement)) {
            setFocusedPill(-1);
          }
        }, 150)}
      />
      {open && matches.length > 0 && (
        <ul className="tag-picker-dropdown">
          {matches.map((tag, i) => (
            <li
              key={tag.slug}
              className={i === highlightedIndex ? "highlighted" : ""}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setHighlightedIndex(i)}
              onClick={() => addExisting(tag)}
            >
              {tag.name}
              {tag.fullName && tag.fullName !== tag.name && <span className="tag-picker-full-name"> {tag.fullName}</span>}
            </li>
          ))}
        </ul>
      )}
      {inputName &&
        selected.map((tag) => (
          <input
            key={`${tag.kind}:${tag.slug}:input`}
            type="hidden"
            name={tag.kind === "new" ? "new_tags" : inputName}
            value={tag.kind === "new" ? tag.name : tag.slug}
          />
        ))}
    </div>
  );
}

function ManagedTagPicker({
  initialSlugs,
  initialNames,
  inputName,
  queryInputName,
  initialQuery,
  placeholder,
  inputType,
  allowNew,
  submitOnEnterWhenNoMatch,
}: {
  initialSlugs: string[];
  initialNames: string[];
  inputName: string;
  queryInputName?: string;
  initialQuery?: string;
  placeholder?: string;
  inputType?: string;
  allowNew: boolean;
  submitOnEnterWhenNoMatch: boolean;
}) {
  const [selected, setSelected] = useState<SelectedTag[]>(
    initialSlugs.map((slug, i) => ({
      kind: "existing",
      slug,
      name: initialNames[i] || slug,
    })),
  );
  return (
    <TagPicker
      selected={selected}
      onChange={setSelected}
      inputName={inputName}
      queryInputName={queryInputName}
      initialQuery={initialQuery}
      placeholder={placeholder}
      inputType={inputType}
      allowNew={allowNew}
      submitOnEnterWhenNoMatch={submitOnEnterWhenNoMatch}
    />
  );
}

function mountTagPicker(el: HTMLElement) {
  if (el.dataset.tagPickerMounted === "1") return;
  el.dataset.tagPickerMounted = "1";
  const initialSlugs = JSON.parse(el.dataset.selected || "[]") as string[];
  const initialNames = JSON.parse(el.dataset.selectedNames || "[]") as string[];
  const inputName = el.dataset.name || "tags";
  const queryInputName = el.dataset.queryName || undefined;
  const initialQuery = el.dataset.initialQuery || "";
  const placeholder = el.dataset.placeholder || undefined;
  const inputType = el.dataset.inputType || undefined;
  const allowNew = el.dataset.allowNew !== "0";
  const submitOnEnterWhenNoMatch = el.dataset.submitOnEnter === "1";

  hydrateRoot(
    el,
    <ManagedTagPicker
      initialSlugs={initialSlugs}
      initialNames={initialNames}
      inputName={inputName}
      queryInputName={queryInputName}
      initialQuery={initialQuery}
      placeholder={placeholder}
      inputType={inputType}
      allowNew={allowNew}
      submitOnEnterWhenNoMatch={submitOnEnterWhenNoMatch}
    />,
  );
}

function initAllTagPickers(root: ParentNode = document) {
  root
    .querySelectorAll<HTMLElement>("[data-tag-picker]")
    .forEach(mountTagPicker);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initAllTagPickers());
} else {
  initAllTagPickers();
}

document.addEventListener("htmx:afterSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target;
  if (target instanceof HTMLElement) {
    initAllTagPickers(target);
  }
});
