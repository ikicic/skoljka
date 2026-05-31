import {
  HTML_PLACEHOLDER_PREFIX,
  HTML_PLACEHOLDER_RE,
  IMAGE_WIDTH_RE,
  LATEX_PLACEHOLDER_PREFIX,
  LATEX_PLACEHOLDER_RE,
  MATH_RE,
  PLACEHOLDER_PREFIX,
  PLACEHOLDER_RE,
  type LatexContext,
} from "./types";
import { escapeHtml } from "./utils";

export function protectHtml(htmlBlocks: string[], html: string): string {
  const idx = htmlBlocks.length;
  htmlBlocks.push(html);
  return `${HTML_PLACEHOLDER_PREFIX}${idx}\x00§`;
}

export function restoreProtectedHtml(source: string, htmlBlocks: string[]): string {
  return source.replace(HTML_PLACEHOLDER_RE, (_match, idxStr: string) => {
    return htmlBlocks[Number.parseInt(idxStr, 10)] ?? "";
  });
}

export function protectMath(source: string): { source: string; mathBlocks: string[] } {
  const mathBlocks: string[] = [];
  return {
    mathBlocks,
    source: source.replace(MATH_RE, (match) => {
      const idx = mathBlocks.length;
      mathBlocks.push(match);
      return `${PLACEHOLDER_PREFIX}${idx}\x00`;
    }),
  };
}

export function restoreMath(source: string, mathBlocks: string[]): string {
  return source.replace(PLACEHOLDER_RE, (_match, idxStr: string) => {
    return mathBlocks[Number.parseInt(idxStr, 10)] ?? "";
  });
}

export function protectSizedImages(source: string, htmlBlocks: string[]): string {
  return source.replace(IMAGE_WIDTH_RE, (_match, alt, src, title, width) => {
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
    return protectHtml(
      htmlBlocks,
      `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}"${titleAttr} style="width: ${width};">`,
    );
  });
}

export function protectLatex(ctx: LatexContext, latex: string): string {
  const idx = ctx.latexBlocks.length;
  ctx.latexBlocks.push(latex);
  return `${LATEX_PLACEHOLDER_PREFIX}${idx}\x00`;
}

export function renderLatexTextWithPlaceholders(source: string, ctx: LatexContext): string {
  let out = "";
  let last = 0;
  for (const match of source.matchAll(LATEX_PLACEHOLDER_RE)) {
    out += escapeLatexText(source.slice(last, match.index));
    out += ctx.latexBlocks[Number.parseInt(match[1], 10)] ?? "";
    last = match.index! + match[0].length;
  }
  out += escapeLatexText(source.slice(last));
  return out;
}

export function escapeLatexText(s: string): string {
  let out = "";
  for (const ch of s) {
    if (ch === "\\") out += "\\textbackslash{}";
    else if ("#$%&_{}".includes(ch)) out += `\\${ch}`;
    else if (ch === "~") out += "\\textasciitilde{}";
    else if (ch === "^") out += "\\textasciicircum{}";
    else if (ch === "<") out += "\\textless{}";
    else if (ch === ">") out += "\\textgreater{}";
    else out += ch;
  }
  return out;
}

export function escapeLatexUrl(url: string): string {
  return url
    .trim()
    .replace(/[\u0000-\u001f\u007f\s]+/g, "")
    .replace(/[{}\\]/g, "")
    .replace(/%/g, "\\%");
}
