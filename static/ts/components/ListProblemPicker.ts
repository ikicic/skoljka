/**
 * Interactive problem-list editor for /lists/<pk>/edit/.
 *
 * The server renders the initial list as JSON, then this module owns the draft
 * list in browser memory until the user clicks "Save changes". Search still
 * comes from the backend, but add/remove/reorder/select/drag operations are
 * local draft mutations.
 *
 * Implementation quirks:
 * - The table bodies are rendered manually because this started as progressive
 *   enhancement over server-rendered HTML.
 * - Dragging a selected row drags the whole selection; dropping into the list
 *   computes the insertion point after removing dragged rows from the draft.
 * - Search results are re-rendered when the draft changes so "In list" state
 *   stays synchronized with unsaved edits.
 *
 * If this editor grows much more complex, migrate it to React/TSX. At this
 * point it is already a small stateful client app, and React would make the
 * rendering/state relationship easier to maintain.
 */
import { gettext, ngettext } from "../i18n";

interface ProblemRow {
  id: number;
  title: string;
  url: string;
  source: string;
  source_url: string;
  year: number | null;
  number: number | null;
  tags: Array<{ name: string; full_name?: string; url: string }>;
  already_added: boolean;
  solved: boolean;
}

interface SearchResponse {
  results: ProblemRow[];
}

type TableKind = "list" | "search";

interface DragState {
  source: TableKind;
  ids: number[];
}

function csrfTokenFor(root: HTMLElement): string {
  return root.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')?.value || "";
}

function problemMeta(problem: ProblemRow): string {
  const bits: string[] = [];
  if (problem.source) bits.push(problem.source);
  if (problem.year) bits.push(String(problem.year));
  return bits.join(" ");
}

function link(href: string, text: string, className = ""): HTMLAnchorElement {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = text;
  if (className) a.className = className;
  return a;
}

function parseInitialProblems(root: HTMLElement): ProblemRow[] {
  const script = root.querySelector<HTMLScriptElement>("[data-list-initial]");
  if (!script?.textContent) return [];
  try {
    return JSON.parse(script.textContent) as ProblemRow[];
  } catch {
    return [];
  }
}

function sameOrder(a: ProblemRow[], b: ProblemRow[]): boolean {
  return a.length === b.length && a.every((problem, index) => problem.id === b[index]?.id);
}

function insertionIndex(tbody: HTMLTableSectionElement, y: number): number {
  const rows = [...tbody.querySelectorAll<HTMLTableRowElement>("tr[data-problem-id]:not(.dragging)")];
  const row = rows.find((candidate) => {
    const box = candidate.getBoundingClientRect();
    return y < box.top + box.height / 2;
  });
  if (!row) return rows.length;
  return rows.indexOf(row);
}

function initListEditor(root: HTMLElement) {
  if (root.dataset.listEditorMounted === "1") return;
  root.dataset.listEditorMounted = "1";

  const picker = root.querySelector<HTMLElement>("[data-list-problem-picker]");
  const form = picker?.querySelector<HTMLFormElement>("form");
  const input = picker?.querySelector<HTMLInputElement>("[data-list-problem-query]");
  const resultsEl = picker?.querySelector<HTMLElement>("[data-list-problem-results]");
  const listTableContainer = root.querySelector<HTMLElement>("[data-list-table-container]");
  const emptyMessage = root.querySelector<HTMLElement>("[data-list-empty]");
  const saveButton = root.querySelector<HTMLButtonElement>("[data-list-save]");
  const removeSelectedButton = root.querySelector<HTMLButtonElement>("[data-list-remove-selected]");
  const dirtyStatus = root.querySelector<HTMLElement>("[data-list-dirty-status]");
  const searchUrl = picker?.dataset.searchUrl;
  const saveUrl = root.dataset.saveUrl;
  if (!picker || !form || !input || !resultsEl || !listTableContainer || !searchUrl || !saveUrl) return;
  const searchInput = input;
  const searchResultsEl = resultsEl;
  const problemSearchUrl = searchUrl;
  const listSaveUrl = saveUrl;

  const listWrapper = document.createElement("div");
  listWrapper.className = "table-wrapper";
  const listTable = document.createElement("table");
  listTable.className = "table list-editor-table";
  const listHead = document.createElement("thead");
  const listHeadRow = document.createElement("tr");
  const listSelectAllCell = document.createElement("th");
  listSelectAllCell.className = "select-col";
  const listSelectAll = document.createElement("input");
  listSelectAll.type = "checkbox";
  listSelectAll.setAttribute("aria-label", gettext("Select all"));
  listSelectAllCell.append(listSelectAll);
  listHeadRow.append(listSelectAllCell);
  [
    ["order-col", "#"],
    ["", gettext("Problem")],
    ["", gettext("Source")],
    ["", gettext("Tags")],
  ].forEach(([className, label]) => {
    const th = document.createElement("th");
    if (className) th.className = className;
    th.textContent = label;
    listHeadRow.append(th);
  });
  listHead.append(listHeadRow);
  const listBody = document.createElement("tbody");
  listBody.dataset.listItems = "";
  listTable.append(listHead, listBody);
  listWrapper.append(listTable);
  listTableContainer.append(listWrapper);

  let initialList = parseInitialProblems(root);
  let draftList = [...initialList];
  let results: ProblemRow[] = [];
  let listSelection = new Set<number>();
  let searchSelection = new Set<number>();
  let lastSelected: Record<TableKind, number | null> = { list: null, search: null };
  let highlightedIndex = -1;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let abortController: AbortController | null = null;
  let dragState: DragState | null = null;
  let dragPreviewEl: HTMLElement | null = null;
  let saving = false;

  function problemInList(problemId: number): boolean {
    return draftList.some((problem) => problem.id === problemId);
  }

  function syncResultState() {
    results = results.map((problem) => ({ ...problem, already_added: problemInList(problem.id) }));
    searchSelection = new Set([...searchSelection].filter((id) => !problemInList(id)));
  }

  function selectedProblems(kind: TableKind, anchorId: number): ProblemRow[] {
    if (kind === "list") {
      const ids = listSelection.has(anchorId) ? listSelection : new Set([anchorId]);
      return draftList.filter((problem) => ids.has(problem.id));
    }
    const ids = searchSelection.has(anchorId) ? searchSelection : new Set([anchorId]);
    return results.filter((problem) => ids.has(problem.id) && !problemInList(problem.id));
  }

  function setSelection(kind: TableKind, problemId: number, event: MouseEvent) {
    const rows = kind === "list" ? draftList : results.filter((problem) => !problemInList(problem.id));
    const ids = rows.map((problem) => problem.id);
    const selection = kind === "list" ? listSelection : searchSelection;

    if (event.shiftKey && lastSelected[kind]) {
      const start = ids.indexOf(lastSelected[kind] as number);
      const end = ids.indexOf(problemId);
      if (start !== -1 && end !== -1) {
        const [from, to] = start < end ? [start, end] : [end, start];
        ids.slice(from, to + 1).forEach((id) => selection.add(id));
      }
    } else if (event.ctrlKey || event.metaKey) {
      if (selection.has(problemId)) selection.delete(problemId);
      else selection.add(problemId);
      lastSelected[kind] = problemId;
    } else {
      selection.clear();
      selection.add(problemId);
      lastSelected[kind] = problemId;
    }
    render();
  }

  function toggleOne(kind: TableKind, problemId: number, checked: boolean, event?: MouseEvent) {
    if (event?.shiftKey && lastSelected[kind]) {
      setSelection(kind, problemId, event);
      return;
    }
    const selection = kind === "list" ? listSelection : searchSelection;
    if (checked) selection.add(problemId);
    else selection.delete(problemId);
    lastSelected[kind] = problemId;
    render();
  }

  function setAll(kind: TableKind, checked: boolean) {
    if (kind === "list") {
      listSelection = checked ? new Set(draftList.map((problem) => problem.id)) : new Set();
    } else {
      searchSelection = checked
        ? new Set(results.filter((problem) => !problemInList(problem.id)).map((problem) => problem.id))
        : new Set();
    }
    render();
  }

  function addProblems(problems: ProblemRow[], index = draftList.length) {
    const incoming = problems.filter((problem) => !problemInList(problem.id));
    if (incoming.length === 0) return;
    draftList.splice(index, 0, ...incoming.map((problem) => ({ ...problem, already_added: true })));
    searchSelection = new Set([...searchSelection].filter((id) => !incoming.some((problem) => problem.id === id)));
    syncResultState();
    render();
  }

  function removeProblems(ids: Set<number>) {
    if (ids.size === 0) return;
    draftList = draftList.filter((problem) => !ids.has(problem.id));
    listSelection = new Set([...listSelection].filter((id) => !ids.has(id)));
    syncResultState();
    render();
  }

  function moveProblems(ids: number[], index: number) {
    const moving = draftList.filter((problem) => ids.includes(problem.id));
    if (moving.length === 0) return;
    const remaining = draftList.filter((problem) => !ids.includes(problem.id));
    const adjustedIndex = Math.max(0, Math.min(remaining.length, index));
    remaining.splice(adjustedIndex, 0, ...moving);
    draftList = remaining;
    render();
  }

  function updateSelectionCheckbox(checkbox: HTMLInputElement, total: number, selected: number) {
    checkbox.checked = total > 0 && selected === total;
    checkbox.indeterminate = selected > 0 && selected < total;
    checkbox.disabled = total === 0;
  }

  function updateChrome() {
    const dirty = !sameOrder(initialList, draftList);
    if (emptyMessage) emptyMessage.style.display = draftList.length === 0 ? "" : "none";
    if (saveButton) saveButton.disabled = !dirty || saving;
    if (removeSelectedButton) {
      removeSelectedButton.disabled = listSelection.size === 0;
      removeSelectedButton.hidden = listSelection.size === 0;
    }
    if (dirtyStatus) {
      dirtyStatus.textContent = dirty
        ? ngettext("%(count)s unsaved change", "%(count)s unsaved changes", Math.abs(draftList.length - initialList.length) || 1)
            .replace("%(count)s", String(Math.abs(draftList.length - initialList.length) || 1))
        : "";
    }
    updateSelectionCheckbox(listSelectAll, draftList.length, listSelection.size);
  }

  function render() {
    syncResultState();
    renderList();
    renderSearch();
    updateChrome();
  }

  function renderList() {
    listBody.innerHTML = "";
    draftList.forEach((problem, index) => listBody.append(renderListRow(problem, index)));
  }

  function clearDropIndicator() {
    listBody
      .querySelectorAll("tr.drop-before, tr.drop-after")
      .forEach((row) => row.classList.remove("drop-before", "drop-after"));
    listBody.classList.remove("drop-empty");
  }

  function updateDropIndicator(y: number) {
    clearDropIndicator();
    if (draftList.length === 0) {
      listBody.classList.add("drop-empty");
      return;
    }
    const rows = [...listBody.querySelectorAll<HTMLTableRowElement>("tr[data-problem-id]:not(.dragging)")];
    if (rows.length === 0) {
      listBody.classList.add("drop-empty");
      return;
    }
    const index = insertionIndex(listBody, y);
    if (index >= rows.length) rows[rows.length - 1]?.classList.add("drop-after");
    else rows[index]?.classList.add("drop-before");
  }

  function clearDraggingRows() {
    root.querySelectorAll("tr.dragging").forEach((row) => row.classList.remove("dragging"));
  }

  function clearDragState() {
    dragState = null;
    clearDropIndicator();
    clearDraggingRows();
    dragPreviewEl?.remove();
    dragPreviewEl = null;
  }

  function markDraggingRows(container: ParentNode, ids: number[]) {
    ids.forEach((id) => {
      container
        .querySelector<HTMLTableRowElement>(`tr[data-problem-id="${id}"]`)
        ?.classList.add("dragging");
    });
  }

  function setDragPreview(event: DragEvent, count: number) {
    dragPreviewEl?.remove();
    dragPreviewEl = document.createElement("div");
    dragPreviewEl.className = "list-drag-preview";
    dragPreviewEl.textContent = ngettext("%(count)s problem", "%(count)s problems", count)
      .replace("%(count)s", String(count));
    document.body.append(dragPreviewEl);
    event.dataTransfer?.setDragImage(dragPreviewEl, -12, -12);
  }

  function renderListRow(problem: ProblemRow, index: number): HTMLTableRowElement {
    const row = document.createElement("tr");
    row.dataset.problemId = String(problem.id);
    row.draggable = true;
    if (listSelection.has(problem.id)) row.classList.add("selected");
    if (problem.solved) row.classList.add("solved");

    row.addEventListener("click", (event) => {
      if ((event.target as Element).closest("a,input,button")) return;
      setSelection("list", problem.id, event);
    });
    row.addEventListener("dragstart", (event) => {
      const problems = selectedProblems("list", problem.id);
      dragState = { source: "list", ids: problems.map((selected) => selected.id) };
      markDraggingRows(listBody, dragState.ids);
      setDragPreview(event, dragState.ids.length);
      event.dataTransfer?.setData("text/plain", dragState.ids.join(","));
    });
    row.addEventListener("dragend", () => {
      clearDragState();
    });

    const selectCell = document.createElement("td");
    selectCell.className = "select-col";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = listSelection.has(problem.id);
    checkbox.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleOne("list", problem.id, checkbox.checked, event);
    });
    selectCell.append(checkbox);
    row.append(selectCell);

    const orderCell = document.createElement("td");
    orderCell.className = "order-col text-muted";
    orderCell.textContent = String(index + 1);
    row.append(orderCell);

    const titleCell = document.createElement("td");
    titleCell.append(link(problem.url, problem.title));
    row.append(titleCell);
    row.append(renderSourceCell(problem));
    row.append(renderTagsCell(problem));
    return row;
  }

  function renderSourceCell(problem: ProblemRow): HTMLTableCellElement {
    const cell = document.createElement("td");
    cell.className = "text-muted";
    const text = problemMeta(problem);
    if (problem.source_url && text) cell.append(link(problem.source_url, text, "text-muted"));
    else cell.textContent = text;
    return cell;
  }

  function renderTagsCell(problem: ProblemRow): HTMLTableCellElement {
    const cell = document.createElement("td");
    if (problem.tags.length > 0) {
      const tags = document.createElement("span");
      tags.className = "tag-list-inline";
      problem.tags.forEach((tag) => {
        const tagLink = link(tag.url, tag.name, "tag");
        if (tag.full_name) tagLink.title = tag.full_name;
        tags.append(tagLink);
      });
      cell.append(tags);
    }
    return cell;
  }

  function renderSearch(message = "") {
    searchResultsEl.innerHTML = "";
    if (message) {
      const p = document.createElement("p");
      p.className = "text-muted list-problem-picker-message";
      p.textContent = message;
      searchResultsEl.append(p);
      return;
    }
    if (results.length === 0) return;

    const wrapper = document.createElement("div");
    wrapper.className = "table-wrapper";
    const table = document.createElement("table");
    table.className = "table list-editor-table list-problem-picker-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");

    const selectHead = document.createElement("th");
    selectHead.className = "select-col";
    const searchSelectAll = document.createElement("input");
    searchSelectAll.type = "checkbox";
    searchSelectAll.setAttribute("aria-label", gettext("Select all"));
    const selectableCount = results.filter((problem) => !problemInList(problem.id)).length;
    updateSelectionCheckbox(searchSelectAll, selectableCount, searchSelection.size);
    searchSelectAll.addEventListener("change", () => setAll("search", searchSelectAll.checked));
    selectHead.append(searchSelectAll);
    headRow.append(selectHead);

    [gettext("Problem"), gettext("Source"), gettext("Tags")].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headRow.append(th);
    });
    thead.append(headRow);
    table.append(thead);

    const tbody = document.createElement("tbody");
    results.forEach((problem, index) => tbody.append(renderSearchRow(problem, index === highlightedIndex)));
    table.append(tbody);
    wrapper.append(table);

    const actions = document.createElement("div");
    actions.className = "list-search-actions";
    const addSelected = document.createElement("button");
    addSelected.type = "button";
    addSelected.className = "btn btn-sm";
    addSelected.disabled = searchSelection.size === 0;
    addSelected.textContent = gettext("Add selected");
    addSelected.addEventListener("click", () => addProblems(results.filter((problem) => searchSelection.has(problem.id))));
    actions.append(addSelected);

    searchResultsEl.append(actions, wrapper);
  }

  function renderSearchRow(problem: ProblemRow, highlighted: boolean): HTMLTableRowElement {
    const row = document.createElement("tr");
    row.dataset.problemId = String(problem.id);
    const inList = problemInList(problem.id);
    if (highlighted) row.classList.add("highlighted");
    if (searchSelection.has(problem.id)) row.classList.add("selected");
    if (inList) row.classList.add("disabled-row");
    if (problem.solved) row.classList.add("solved");
    row.draggable = !inList;
    row.addEventListener("click", (event) => {
      if ((event.target as Element).closest("a,input,button") || inList) return;
      setSelection("search", problem.id, event);
    });
    row.addEventListener("dblclick", () => {
      if (!inList) addProblems([problem]);
    });
    row.addEventListener("dragstart", (event) => {
      if (inList) {
        event.preventDefault();
        return;
      }
      const problems = selectedProblems("search", problem.id);
      dragState = { source: "search", ids: problems.map((selected) => selected.id) };
      markDraggingRows(searchResultsEl, dragState.ids);
      setDragPreview(event, dragState.ids.length);
      event.dataTransfer?.setData("text/plain", dragState.ids.join(","));
    });
    row.addEventListener("dragend", () => {
      clearDragState();
    });

    const selectCell = document.createElement("td");
    selectCell.className = "select-col";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = searchSelection.has(problem.id);
    checkbox.disabled = inList;
    checkbox.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleOne("search", problem.id, checkbox.checked, event);
    });
    selectCell.append(checkbox);
    row.append(selectCell);

    const problemCell = document.createElement("td");
    problemCell.append(link(problem.url, problem.title));
    if (inList) {
      const badge = document.createElement("span");
      badge.className = "list-row-badge";
      badge.textContent = gettext("In list");
      problemCell.append(" ", badge);
    }
    row.append(problemCell);
    row.append(renderSourceCell(problem));
    row.append(renderTagsCell(problem));
    return row;
  }

  async function searchNow() {
    const q = searchInput.value.trim();
    if (!q) {
      results = [];
      searchSelection.clear();
      highlightedIndex = -1;
      render();
      return;
    }
    abortController?.abort();
    abortController = new AbortController();
    const url = new URL(problemSearchUrl, window.location.origin);
    url.searchParams.set("q", q);
    const response = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      signal: abortController.signal,
    }).catch((error) => {
      if (error.name === "AbortError") return null;
      throw error;
    });
    if (!response) return;
    if (!response.ok) {
      renderSearch(gettext("Search failed."));
      return;
    }
    const data = (await response.json()) as SearchResponse;
    results = data.results;
    syncResultState();
    highlightedIndex = results.findIndex((problem) => !problemInList(problem.id));
    render();
    if (results.length === 0) renderSearch(gettext("No matching problems."));
  }

  function scheduleSearch() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void searchNow(), 180);
  }

  async function saveDraft() {
    if (saving || sameOrder(initialList, draftList)) return;
    saving = true;
    updateChrome();
    const response = await fetch(listSaveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfTokenFor(root),
      },
      body: JSON.stringify({ problem_ids: draftList.map((problem) => problem.id) }),
    });
    saving = false;
    if (!response.ok) {
      updateChrome();
      return;
    }
    initialList = [...draftList];
    updateChrome();
  }

  listSelectAll.addEventListener("change", () => setAll("list", listSelectAll.checked));
  saveButton?.addEventListener("click", () => void saveDraft());
  removeSelectedButton?.addEventListener("click", () => removeProblems(listSelection));

  listBody.addEventListener("dragover", (event) => {
    if (!dragState) return;
    event.preventDefault();
    updateDropIndicator(event.clientY);
  });
  listBody.addEventListener("dragleave", (event) => {
    if (event.relatedTarget instanceof Node && listBody.contains(event.relatedTarget)) return;
    clearDropIndicator();
  });
  listBody.addEventListener("drop", (event) => {
    if (!dragState) return;
    event.preventDefault();
    const index = insertionIndex(listBody, event.clientY);
    if (dragState.source === "list") {
      moveProblems(dragState.ids, index);
    } else {
      const incoming = results.filter((problem) => dragState?.ids.includes(problem.id));
      addProblems(incoming, index);
    }
    clearDragState();
  });

  input.addEventListener("input", scheduleSearch);
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      highlightedIndex = Math.min(highlightedIndex + 1, results.length - 1);
      while (results[highlightedIndex] && problemInList(results[highlightedIndex].id) && highlightedIndex < results.length - 1) {
        highlightedIndex += 1;
      }
      render();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      highlightedIndex = Math.max(highlightedIndex - 1, 0);
      while (results[highlightedIndex] && problemInList(results[highlightedIndex].id) && highlightedIndex > 0) {
        highlightedIndex -= 1;
      }
      render();
    } else if (event.key === "Enter") {
      const selected = results[highlightedIndex];
      if (selected && !problemInList(selected.id)) {
        event.preventDefault();
        addProblems([selected]);
      }
    } else if (event.key === "Escape") {
      results = [];
      searchSelection.clear();
      highlightedIndex = -1;
      render();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (sameOrder(initialList, draftList)) return;
    event.preventDefault();
    event.returnValue = "";
  });

  render();
}

function initAllListEditors(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>("[data-list-editor]").forEach(initListEditor);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initAllListEditors());
} else {
  initAllListEditors();
}

document.addEventListener("htmx:afterSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target;
  if (target instanceof HTMLElement) initAllListEditors(target);
});
