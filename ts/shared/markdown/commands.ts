import {
  ESCAPED_CHARS,
  ONE_ARG_COMMANDS,
  SYMBOL_COMMANDS,
  type RenderError,
} from "./types";
import { protectHtml } from "./placeholders";
import { escapeHtml, isSafeUrl } from "./utils";

export function findMatchingBrace(source: string, openIndex: number): number | null {
  let depth = 0;
  for (let i = openIndex; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === "\\" && i + 1 < source.length) {
      i += 1;
      continue;
    }
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return null;
}

function renderError(message: string, source: string): string {
  const body = [...source]
    .map((ch) => `&#${ch.codePointAt(0)};`)
    .join("");
  return `<span class="render-error" title="${escapeHtml(message)}">${body}</span>`;
}

function parseBracedArgument(
  source: string,
  openIndex: number,
  {
    mode,
    errors,
    htmlBlocks,
  }: {
    mode: "html" | "text";
    errors: RenderError[];
    htmlBlocks?: string[];
  },
): { raw: string; value: string; closeIndex: number } | null {
  const closeIndex = findMatchingBrace(source, openIndex);
  if (closeIndex === null) return null;
  const raw = source.slice(openIndex + 1, closeIndex);
  return {
    raw,
    value: renderTextCommands(raw, { mode, errors, htmlBlocks }),
    closeIndex,
  };
}

function renderOneArgCommand(
  spec: { tag: string; className?: string },
  inner: string,
  mode: "html" | "text",
  htmlBlocks?: string[],
): string {
  if (mode === "text") return inner;
  const classAttr = spec.className ? ` class="${spec.className}"` : "";
  return `${protectHtml(htmlBlocks!, `<${spec.tag}${classAttr}>`)}${inner}${protectHtml(htmlBlocks!, `</${spec.tag}>`)}`;
}

function renderUrl(url: string, mode: "html" | "text", htmlBlocks?: string[]): string {
  if (mode === "text") return url;
  if (!isSafeUrl(url)) return escapeHtml(url);
  return protectHtml(htmlBlocks!, `<a href="${escapeHtml(url)}">${escapeHtml(url)}</a>`);
}

function renderHref(url: string, label: string, mode: "html" | "text", htmlBlocks?: string[]): string {
  if (mode === "text") return label;
  if (!isSafeUrl(url)) return label;
  return `${protectHtml(htmlBlocks!, `<a href="${escapeHtml(url)}">`)}${label}${protectHtml(htmlBlocks!, "</a>")}`;
}

function renderUrlArgument(raw: string): string {
  return renderTextCommands(raw, { mode: "text", errors: [] });
}

export function renderTextCommands(
  source: string,
  {
    mode,
    errors,
    htmlBlocks,
  }: {
    mode: "html" | "text";
    errors: RenderError[];
    htmlBlocks?: string[];
  },
): string {
  let out = "";
  for (let i = 0; i < source.length; i += 1) {
    if (source[i] !== "\\") {
      out += source[i];
      continue;
    }

    const escaped = source[i + 1] ? ESCAPED_CHARS[source[i + 1]] : undefined;
    if (escaped) {
      out += mode === "html" && escaped.html.startsWith("<")
        ? protectHtml(htmlBlocks!, escaped.html)
        : mode === "html"
          ? escaped.html
          : escaped.text;
      i += 1;
      continue;
    }

    const commandMatch = /^\\([A-Za-z]+)/.exec(source.slice(i));
    if (!commandMatch) {
      out += source[i];
      continue;
    }

    const command = commandMatch[1];
    const oneArgSpec = ONE_ARG_COMMANDS[command];
    const symbol = SYMBOL_COMMANDS[command];
    if (!oneArgSpec && symbol === undefined && command !== "url" && command !== "href") {
      out += source[i];
      continue;
    }

    const commandEnd = i + commandMatch[0].length;
    if (symbol !== undefined) {
      out += mode === "html" ? escapeHtml(symbol).replace(/\\/g, "&#92;") : symbol;
      i = source.startsWith("{}", commandEnd) ? commandEnd + 1 : commandEnd - 1;
      continue;
    }

    if (source[commandEnd] !== "{") {
      const broken = source.slice(i, commandEnd);
      const message = `Expected { after \\${command}`;
      errors.push({ message, source: broken });
      out += mode === "html" ? protectHtml(htmlBlocks!, renderError(message, broken)) : broken;
      i = commandEnd - 1;
      continue;
    }

    const firstArg = parseBracedArgument(source, commandEnd, { mode, errors, htmlBlocks });
    if (!firstArg) {
      const broken = source.slice(i);
      const message = `Unclosed \\${command} command`;
      errors.push({ message, source: broken });
      out += mode === "html" ? protectHtml(htmlBlocks!, renderError(message, broken)) : broken;
      break;
    }

    if (oneArgSpec) {
      out += renderOneArgCommand(oneArgSpec, firstArg.value, mode, htmlBlocks);
      i = firstArg.closeIndex;
      continue;
    }

    if (command === "url") {
      out += renderUrl(renderUrlArgument(firstArg.raw), mode, htmlBlocks);
      i = firstArg.closeIndex;
      continue;
    }

    if (command === "href") {
      const secondOpen = firstArg.closeIndex + 1;
      if (source[secondOpen] !== "{") {
        const broken = source.slice(i, firstArg.closeIndex + 1);
        const message = `Expected second {…} argument after \\href`;
        errors.push({ message, source: broken });
        out += mode === "html" ? protectHtml(htmlBlocks!, renderError(message, broken)) : broken;
        i = firstArg.closeIndex;
        continue;
      }
      const secondArg = parseBracedArgument(source, secondOpen, { mode, errors, htmlBlocks });
      if (!secondArg) {
        const broken = source.slice(i);
        const message = `Unclosed \\href command`;
        errors.push({ message, source: broken });
        out += mode === "html" ? protectHtml(htmlBlocks!, renderError(message, broken)) : broken;
        break;
      }
      out += renderHref(renderUrlArgument(firstArg.raw), secondArg.value, mode, htmlBlocks);
      i = secondArg.closeIndex;
    }
  }
  return out;
}
