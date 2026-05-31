function shouldUseRowLink(target: EventTarget | null): boolean {
  return target instanceof Element && !target.closest("a, button, input, select, textarea, label");
}

function installClickableRows(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>("[data-row-href]").forEach((row) => {
    if (row.dataset.clickableRowMounted) return;
    row.dataset.clickableRowMounted = "1";

    row.addEventListener("click", (event) => {
      if (!shouldUseRowLink(event.target)) return;
      const href = row.dataset.rowHref;
      if (href) window.location.href = href;
    });
  });
}

installClickableRows();
document.addEventListener("htmx:afterSwap", (event: Event) => {
  installClickableRows(event.target instanceof Element ? event.target : document);
});
