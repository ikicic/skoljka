import { gettext } from "../i18n";

declare global {
  interface Window {
    htmx?: {
      process: (element: Element) => void;
    };
  }
}

type StatusKind = "solved" | "bookmark" | "like" | "notes";

type StatusSpec = {
  kind: StatusKind;
  activeKey: "solved" | "bookmarked" | "liked" | "hasNotes";
  path: string;
  label: string;
  interactive: "button" | "link";
};

const STATUS_SPECS: StatusSpec[] = [
  { kind: "solved", activeKey: "solved", path: "solve", label: gettext("Solved"), interactive: "button" },
  { kind: "bookmark", activeKey: "bookmarked", path: "bookmark", label: gettext("Bookmarked"), interactive: "button" },
  { kind: "like", activeKey: "liked", path: "like", label: gettext("Liked"), interactive: "button" },
  { kind: "notes", activeKey: "hasNotes", path: "notes", label: gettext("Notes"), interactive: "link" },
];

function isActive(value: string | undefined): boolean {
  return value === "1" || value === "true";
}

const STATUS_SPRITE_URL = "/static/icons/status-icons.svg";

function createIcon(kind: StatusKind, active: boolean, title: string): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("status-icon", `status-${kind}`);
  if (active) svg.classList.add("active");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("title", title);
  svg.setAttribute("aria-hidden", "true");

  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `${STATUS_SPRITE_URL}#icon-${kind}`);
  svg.append(use);
  return svg;
}

function createStatusButton(cell: HTMLElement, spec: StatusSpec): HTMLElement | null {
  const problemId = cell.dataset.problemId;
  if (!problemId) return null;
  const url = spec.kind === "notes"
    ? `/problems/${problemId}/#note-section`
    : `/tracking/${problemId}/${spec.path}/`;

  const active = isActive(cell.dataset[spec.activeKey]);
  const element = spec.interactive === "link"
    ? document.createElement("a")
    : document.createElement("button");
  element.className = "status-icon-btn";
  element.setAttribute("title", spec.label);
  element.setAttribute("aria-label", spec.label);

  if (element instanceof HTMLButtonElement) {
    element.type = "button";
    element.setAttribute("hx-post", url);
    element.setAttribute("hx-target", `#problem-actions-${problemId}`);
    element.setAttribute("hx-swap", "innerHTML");
  } else {
    element.href = url;
  }

  element.append(createIcon(spec.kind, active, spec.label));
  return element;
}

function applyPayload(cell: HTMLElement) {
  const payload = cell.querySelector<HTMLElement>("[data-status-payload]");
  if (!payload) return;
  cell.dataset.solved = payload.dataset.solved || "0";
  cell.dataset.bookmarked = payload.dataset.bookmarked || "0";
  cell.dataset.liked = payload.dataset.liked || "0";
  cell.dataset.hasNotes = payload.dataset.hasNotes || "0";
}

function renderStatusCell(cell: HTMLElement) {
  applyPayload(cell);
  cell.replaceChildren();
  STATUS_SPECS.forEach((spec) => {
    const button = createStatusButton(cell, spec);
    if (button) cell.append(button);
  });
  window.htmx?.process(cell);
  syncSolvedState(cell);
}

function syncSolvedState(cell: HTMLElement) {
  const solved = isActive(cell.dataset.solved);
  const rowOrCard = cell.closest("tr, .problem-card");
  rowOrCard?.classList.toggle("solved", solved);
}

function syncSolvedStates(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>("[data-problem-actions]").forEach(syncSolvedState);
}

function renderStatusCells(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>("[data-problem-actions]").forEach(renderStatusCell);
}

renderStatusCells();
document.addEventListener("htmx:afterSwap", (event: Event) => {
  if (!(event.target instanceof Element)) return;
  if (event.target instanceof HTMLElement && event.target.matches("[data-problem-actions]")) {
    renderStatusCell(event.target);
    return;
  }
  renderStatusCells(event.target);
  syncSolvedStates(event.target);
});
