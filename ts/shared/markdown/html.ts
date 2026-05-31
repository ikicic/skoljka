import katex from "katex";
import { marked } from "marked";
import { renderTextCommands } from "./commands";
import {
  protectMath,
  protectSizedImages,
  restoreMath,
  restoreProtectedHtml,
} from "./placeholders";
import {
  PLACEHOLDER_RE,
  type RenderError,
  type RenderMarkdownOptions,
  type RenderMarkdownResult,
} from "./types";
import { escapeHtml, isSafeUrl, stripHtml } from "./utils";

function parseMarkdown(source: string): string {
  const renderer = new marked.Renderer();
  renderer.html = ({ raw }) => escapeHtml(raw);
  renderer.link = function ({ href, title, tokens }) {
    const label = this.parser.parseInline(tokens);
    if (!isSafeUrl(href)) return label;
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
    return `<a href="${escapeHtml(href)}"${titleAttr}>${label}</a>`;
  };
  renderer.image = ({ href, title, text }) => {
    if (!isSafeUrl(href, { allowAttachment: true })) return escapeHtml(text);
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
    return `<img src="${escapeHtml(href)}" alt="${escapeHtml(text)}"${titleAttr}>`;
  };
  return marked.parse(source, { async: false, renderer }) as string;
}

function replaceAttachmentUrls(html: string, attachmentUrls?: Record<string, string>): string {
  if (!attachmentUrls) return html;
  let result = html;
  for (const [name, url] of Object.entries(attachmentUrls)) {
    result = result
      .split(`src="attachment:${escapeHtml(name)}"`)
      .join(`src="${escapeHtml(url)}"`);
  }
  return result;
}

function renderMath(html: string, mathBlocks: string[]): string {
  return html.replace(PLACEHOLDER_RE, (_match, idxStr: string) => {
    const raw = mathBlocks[Number.parseInt(idxStr, 10)];
    const isDisplay = raw.startsWith("$$");
    const tex = isDisplay ? raw.slice(2, -2) : raw.slice(1, -1);
    try {
      return katex.renderToString(tex.trim(), {
        displayMode: isDisplay,
        throwOnError: false,
      });
    } catch {
      const delim = isDisplay ? "$$" : "$";
      return `${delim}${escapeHtml(tex)}${delim}`;
    }
  });
}

export function renderMarkdown(
  source: string,
  options: RenderMarkdownOptions = {},
): RenderMarkdownResult {
  const errors: RenderError[] = [];
  const htmlBlocks: string[] = [];
  const { source: mathProtected, mathBlocks } = protectMath(protectSizedImages(source, htmlBlocks));
  const withTextCommands = renderTextCommands(mathProtected, { mode: "html", errors, htmlBlocks });
  let html = parseMarkdown(withTextCommands);
  html = restoreProtectedHtml(html, htmlBlocks);
  html = replaceAttachmentUrls(html, options.attachmentUrls);
  html = renderMath(html, mathBlocks);

  const searchSource = renderTextCommands(mathProtected, { mode: "text", errors: [] });
  const searchHtml = restoreProtectedHtml(parseMarkdown(restoreMath(searchSource, mathBlocks)), htmlBlocks);

  return {
    html,
    text: stripHtml(searchHtml),
    errors,
  };
}

export function compileMarkdown(source: string, attachmentUrls?: Record<string, string>): string {
  return renderMarkdown(source, { attachmentUrls }).html;
}
