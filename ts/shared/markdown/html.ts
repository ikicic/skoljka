import katex from "katex";
import { marked } from "marked";
import { parseBlocks, type Block } from "./blocks";
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
  return marked.parse(source, { async: false, renderer: markdownRenderer() }) as string;
}

function parseMarkdownInline(source: string): string {
  return marked.parseInline(source, { async: false, renderer: markdownRenderer() }) as string;
}

function markdownRenderer() {
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
  return renderer;
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

function renderBlockError(message: string, source: string): string {
  const body = [...source]
    .map((ch) => `&#${ch.codePointAt(0)};`)
    .join("");
  return `<span class="render-error" title="${escapeHtml(message)}">${body}</span>`;
}

function renderMarkdownBlock(
  source: string,
  errors: RenderError[],
  htmlBlocks: string[],
  attachmentUrls?: Record<string, string>,
): string {
  const withTextCommands = renderTextCommands(source, { mode: "html", errors, htmlBlocks });
  let html = parseMarkdown(withTextCommands);
  html = restoreProtectedHtml(html, htmlBlocks);
  return replaceAttachmentUrls(html, attachmentUrls);
}

function renderMarkdownInline(
  source: string,
  errors: RenderError[],
  htmlBlocks: string[],
  attachmentUrls?: Record<string, string>,
): string {
  const withTextCommands = renderTextCommands(source, { mode: "html", errors, htmlBlocks });
  let html = parseMarkdownInline(withTextCommands);
  html = restoreProtectedHtml(html, htmlBlocks);
  return replaceAttachmentUrls(html, attachmentUrls);
}

function prependListItemLabel(renderedItem: string, labelHtml: string): string {
  if (!labelHtml) return renderedItem;
  const label = `<span class="latex-item-label">${labelHtml}</span> `;
  return renderedItem.startsWith("<p>")
    ? `<p>${label}${renderedItem.slice("<p>".length)}`
    : `${label}${renderedItem}`;
}

function renderBlocksHtml(
  blocks: Block[],
  errors: RenderError[],
  htmlBlocks: string[],
  attachmentUrls?: Record<string, string>,
): string {
  return blocks
    .map((block) => {
      if (block.kind === "markdown") {
        return renderMarkdownBlock(block.source, errors, htmlBlocks, attachmentUrls);
      }
      if (block.kind === "error") {
        return renderBlockError(block.message, block.source);
      }
      const tag = block.env === "enumerate" ? "ol" : "ul";
      const items = block.items
        .map((item) => {
          const label = item.label
            ? renderMarkdownInline(item.label, errors, htmlBlocks, attachmentUrls)
            : "";
          const body = renderBlocksHtml(item.blocks, errors, htmlBlocks, attachmentUrls);
          const itemClass = label ? ' class="latex-labeled-item"' : "";
          return `<li${itemClass}>${prependListItemLabel(body, label)}</li>`;
        })
        .join("");
      return `<${tag}>\n${items}</${tag}>\n`;
    })
    .join("");
}

function renderMarkdownText(
  source: string,
  mathBlocks: string[],
  htmlBlocks: string[],
  errors: RenderError[],
): string {
  const searchSource = renderTextCommands(source, { mode: "text", errors });
  return stripHtml(restoreProtectedHtml(parseMarkdown(restoreMath(searchSource, mathBlocks)), htmlBlocks));
}

function renderBlocksText(blocks: Block[], mathBlocks: string[], htmlBlocks: string[]): string {
  const parts: string[] = [];
  for (const block of blocks) {
    if (block.kind === "markdown") {
      const text = renderMarkdownText(block.source, mathBlocks, htmlBlocks, []);
      if (text) parts.push(text);
    } else if (block.kind === "error") {
      const text = stripHtml(parseMarkdown(restoreMath(block.source, mathBlocks)));
      if (text) parts.push(text);
    } else {
      for (const item of block.items) {
        const label = item.label ? renderMarkdownText(item.label, mathBlocks, htmlBlocks, []) : "";
        const text = renderBlocksText(item.blocks, mathBlocks, htmlBlocks);
        const combined = [label, text].filter(Boolean).join(" ");
        if (combined) parts.push(combined);
      }
    }
  }
  return parts.join(" ").replace(/\s+/g, " ").trim();
}

export function renderMarkdown(
  source: string,
  options: RenderMarkdownOptions = {},
): RenderMarkdownResult {
  const errors: RenderError[] = [];
  const htmlBlocks: string[] = [];
  const { source: mathProtected, mathBlocks } = protectMath(protectSizedImages(source, htmlBlocks));
  const blocks = parseBlocks(mathProtected, errors);
  let html = renderBlocksHtml(blocks, errors, htmlBlocks, options.attachmentUrls);
  html = renderMath(html, mathBlocks);

  return {
    html,
    text: renderBlocksText(blocks, mathBlocks, htmlBlocks),
    errors,
  };
}

export function compileMarkdown(source: string, attachmentUrls?: Record<string, string>): string {
  return renderMarkdown(source, { attachmentUrls }).html;
}
