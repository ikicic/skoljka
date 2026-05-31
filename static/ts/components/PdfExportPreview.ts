const DEBOUNCE_MS = 400;

function mountPdfExportForm(form: HTMLFormElement) {
  let timer: number | undefined;
  let controller: AbortController | undefined;

  const updatePreview = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(async () => {
      controller?.abort();
      controller = new AbortController();

      const data = new FormData(form);
      data.set("action", "preview");

      let response: Response;
      try {
        response = await fetch(form.getAttribute("action") || location.href, {
          method: "POST",
          body: data,
          signal: controller.signal,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
      } catch (error) {
        if ((error as DOMException).name !== "AbortError") console.error(error);
        return;
      }
      if (!response.ok) return;

      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const nextPreview = doc.querySelector<HTMLElement>("[data-pdf-export-preview]");
      const preview = document.querySelector<HTMLElement>("[data-pdf-export-preview]");
      if (nextPreview && preview) {
        preview.replaceWith(nextPreview);
      }
    }, DEBOUNCE_MS);
  };

  form.addEventListener("input", updatePreview);
  form.addEventListener("change", updatePreview);
  form.addEventListener("submit", (event) => {
    const submitter = event.submitter;
    if (submitter instanceof HTMLButtonElement && submitter.value === "preview") {
      event.preventDefault();
      updatePreview();
    }
  });
}

document.querySelectorAll<HTMLFormElement>("[data-pdf-export-form]").forEach(mountPdfExportForm);
