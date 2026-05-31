import katex from "katex";

/** Unescape HTML entities that the server escapes inside math delimiters. */
function unescapeHtml(s: string): string {
    return s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
}

function renderMath(element: HTMLElement): void {
    const text = element.innerHTML;

    // Replace display math $$...$$ first, then inline math $...$
    const rendered = text
        .replace(/\$\$([\s\S]+?)\$\$/g, (_match, tex: string) => {
            try {
                return katex.renderToString(unescapeHtml(tex).trim(), {
                    displayMode: true,
                    throwOnError: false,
                });
            } catch {
                return _match;
            }
        })
        .replace(/\$([^\$]+?)\$/g, (_match, tex: string) => {
            try {
                return katex.renderToString(unescapeHtml(tex).trim(), {
                    displayMode: false,
                    throwOnError: false,
                });
            } catch {
                return _match;
            }
        });

    element.innerHTML = rendered;
}

function initKaTeX(): void {
    document.querySelectorAll<HTMLElement>(".math-content").forEach(renderMath);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initKaTeX);
} else {
    initKaTeX();
}

// Re-render after HTMX swaps
document.addEventListener("htmx:afterSwap", (event: Event) => {
    const target = (event as CustomEvent).detail?.target;
    if (target instanceof HTMLElement) {
        target.querySelectorAll<HTMLElement>(".math-content").forEach(renderMath);
    }
});
