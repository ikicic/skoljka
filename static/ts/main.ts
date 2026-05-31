import "./components/ContentEditor";
import "./components/TagPicker";
import "./components/ListProblemPicker";
import "./components/ProblemViewSwitcher";
import "./components/ClickableRows";
import "./components/StatusCells";
import "./components/PdfExportPreview";

// Focus note textarea when navigating with #note-section
if (location.hash === "#note-section") {
  document.getElementById("note-textarea")?.focus();
}
window.addEventListener("hashchange", () => {
  if (location.hash === "#note-section") {
    document.getElementById("note-textarea")?.focus();
  }
});

document.addEventListener("click", (event) => {
  const toggle = (event.target as Element | null)?.closest("[data-nav-toggle]");
  if (!toggle) return;
  document.querySelector(".nav-menu")?.classList.toggle("open");
});

document.addEventListener("submit", (event) => {
  const form = event.target as HTMLFormElement | null;
  const message = form?.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

function updateConfirmCountForm(form: HTMLFormElement): void {
  const expected = form.querySelector<HTMLInputElement>("[data-confirm-count-expected]");
  const input = form.querySelector<HTMLInputElement>("[data-confirm-count-input]");
  const button = form.querySelector<HTMLButtonElement>("button[type=submit]");
  if (!expected || !input || !button) return;
  button.disabled = input.value !== expected.value;
}

document.addEventListener("input", (event) => {
  const form = (event.target as Element | null)?.closest<HTMLFormElement>(
    "[data-confirm-count-form]",
  );
  if (form) updateConfirmCountForm(form);
});

document
  .querySelectorAll<HTMLFormElement>("[data-confirm-count-form]")
  .forEach(updateConfirmCountForm);
