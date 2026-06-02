import { marked } from "marked";
import { parseBlocks, type Block } from "./blocks";
import { findMatchingBrace, renderTextCommands } from "./commands";
import {
  escapeLatexText,
  escapeLatexUrl,
  protectLatex,
  protectMath,
  renderLatexTextWithPlaceholders,
} from "./placeholders";
import {
  ESCAPED_CHARS,
  IMAGE_WIDTH_RE,
  ONE_ARG_COMMANDS,
  PLACEHOLDER_RE,
  SYMBOL_COMMANDS,
  type LatexContext,
  type RenderLatexOptions,
  type RenderLatexResult,
} from "./types";
import { isSafeUrl } from "./utils";

function latexWidth(width: string): string {
  if (width.endsWith("%")) {
    const value = Number.parseFloat(width.slice(0, -1));
    if (Number.isFinite(value) && value > 0) return `${value / 100}\\linewidth`;
  }
  if (/^\d+(?:\.\d+)?(?:px|pt)$/.test(width)) return width;
  return "";
}

function latexPath(path: string): string {
  return path
    .trim()
    .replace(/\\/g, "/")
    .replace(/[{}\u0000-\u001f\u007f]/g, "");
}

function latexDetokenizedPath(path: string): string {
  return `\\detokenize{${latexPath(path)}}`;
}

function attachmentLatexPath(src: string, ctx: LatexContext): string {
  if (!src.startsWith("attachment:")) return src;
  const name = src.slice("attachment:".length);
  return ctx.attachmentPaths?.[name] ?? name;
}

function renderLatexImage(src: string, alt: string, width: string | undefined, ctx: LatexContext): string {
  if (!isSafeUrl(src, { allowAttachment: true })) return escapeLatexText(alt);
  const path = latexPath(attachmentLatexPath(src, ctx));
  if (!path) return escapeLatexText(alt);
  ctx.packages.add("graphicx");
  const widthOpt = width ? latexWidth(width) : "";
  const options = widthOpt ? `[width=${widthOpt}]` : "";
  return `\\includegraphics${options}{${latexDetokenizedPath(path)}}`;
}

function protectSizedImagesLatex(source: string, ctx: LatexContext): string {
  return source.replace(IMAGE_WIDTH_RE, (_match, alt, src, _title, width) => {
    return protectLatex(ctx, renderLatexImage(src, alt, width, ctx));
  });
}

function renderLatexMathPlaceholder(raw: string): string {
  const isDisplay = raw.startsWith("$$");
  const tex = (isDisplay ? raw.slice(2, -2) : raw.slice(1, -1)).trim();
  return isDisplay ? `\\[\n${tex}\n\\]` : `$${tex}$`;
}

function renderLatexErrorText(message: string, source: string, ctx: LatexContext): string {
  ctx.packages.add("xcolor");
  return `\\textcolor{red}{${escapeLatexText(source)}}`;
}

function renderLatexUrlArgument(raw: string): string {
  return renderTextCommands(raw, { mode: "text", errors: [] });
}

function renderLatexInline(source: string, ctx: LatexContext): string {
  const withTextCommands = renderLatexTextCommands(source, ctx);
  return renderLatexInlineTokens(marked.Lexer.lexInline(withTextCommands) as any[], ctx);
}

function renderLatexOneArgCommand(command: string, rawInner: string, ctx: LatexContext): string {
  const inner = renderLatexInline(rawInner, ctx);
  if (command === "textbf") return `\\textbf{${inner}}`;
  if (command === "emph" || command === "textit") return `\\emph{${inner}}`;
  if (command === "sout") {
    ctx.packages.add("ulem");
    return `\\sout{${inner}}`;
  }
  if (command === "uline" || command === "underline") {
    ctx.packages.add("ulem");
    return `\\uline{${inner}}`;
  }
  if (command === "texttt") return `\\texttt{${inner}}`;
  if (command === "fbox") return `\\fbox{\\mbox{${inner}}}`;
  if (command === "mbox") return `\\mbox{${inner}}`;
  return inner;
}

function renderLatexTextCommands(source: string, ctx: LatexContext): string {
  let out = "";
  for (let i = 0; i < source.length; i += 1) {
    if (source[i] !== "\\") {
      out += source[i];
      continue;
    }

    const escaped = source[i + 1] ? ESCAPED_CHARS[source[i + 1]] : undefined;
    if (escaped) {
      if (source[i + 1] === "\\") out += protectLatex(ctx, "\\\\");
      else if (source[i + 1] === "-") out += protectLatex(ctx, "\\-");
      else out += escaped.text;
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
      out += symbol;
      i = source.startsWith("{}", commandEnd) ? commandEnd + 1 : commandEnd - 1;
      continue;
    }

    if (source[commandEnd] !== "{") {
      const broken = source.slice(i, commandEnd);
      const message = `Expected { after \\${command}`;
      ctx.errors.push({ message, source: broken });
      out += protectLatex(ctx, renderLatexErrorText(message, broken, ctx));
      i = commandEnd - 1;
      continue;
    }

    const closeIndex = findMatchingBrace(source, commandEnd);
    if (closeIndex === null) {
      const broken = source.slice(i);
      const message = `Unclosed \\${command} command`;
      ctx.errors.push({ message, source: broken });
      out += protectLatex(ctx, renderLatexErrorText(message, broken, ctx));
      break;
    }

    const rawInner = source.slice(commandEnd + 1, closeIndex);
    if (oneArgSpec) {
      out += protectLatex(ctx, renderLatexOneArgCommand(command, rawInner, ctx));
      i = closeIndex;
      continue;
    }

    if (command === "url") {
      const url = renderLatexUrlArgument(rawInner);
      if (isSafeUrl(url)) {
        ctx.packages.add("hyperref");
        out += protectLatex(ctx, `\\url{${escapeLatexUrl(url)}}`);
      } else {
        out += url;
      }
      i = closeIndex;
      continue;
    }

    if (command === "href") {
      const secondOpen = closeIndex + 1;
      if (source[secondOpen] !== "{") {
        const broken = source.slice(i, closeIndex + 1);
        const message = `Expected second {…} argument after \\href`;
        ctx.errors.push({ message, source: broken });
        out += protectLatex(ctx, renderLatexErrorText(message, broken, ctx));
        i = closeIndex;
        continue;
      }
      const secondClose = findMatchingBrace(source, secondOpen);
      if (secondClose === null) {
        const broken = source.slice(i);
        const message = `Unclosed \\href command`;
        ctx.errors.push({ message, source: broken });
        out += protectLatex(ctx, renderLatexErrorText(message, broken, ctx));
        break;
      }
      const url = renderLatexUrlArgument(rawInner);
      const label = renderLatexInline(source.slice(secondOpen + 1, secondClose), ctx);
      if (isSafeUrl(url)) {
        ctx.packages.add("hyperref");
        out += protectLatex(ctx, `\\href{${escapeLatexUrl(url)}}{${label}}`);
      } else {
        out += protectLatex(ctx, label);
      }
      i = secondClose;
    }
  }
  return out;
}

function renderLatexInlineTokens(tokens: any[], ctx: LatexContext): string {
  return tokens.map((token) => renderLatexInlineToken(token, ctx)).join("");
}

function renderLatexInlineToken(token: any, ctx: LatexContext): string {
  switch (token.type) {
    case "text":
    case "escape":
      return renderLatexTextWithPlaceholders(token.text ?? token.raw ?? "", ctx)
        .replace(PLACEHOLDER_RE, (_match, idxStr: string) => {
          const raw = ctx.mathBlocks[Number.parseInt(idxStr, 10)] ?? "";
          return renderLatexMathPlaceholder(raw);
        });
    case "strong":
      return `\\textbf{${renderLatexInlineTokens(token.tokens ?? [], ctx)}}`;
    case "em":
      return `\\emph{${renderLatexInlineTokens(token.tokens ?? [], ctx)}}`;
    case "del":
      ctx.packages.add("ulem");
      return `\\sout{${renderLatexInlineTokens(token.tokens ?? [], ctx)}}`;
    case "codespan":
      return `\\texttt{${escapeLatexText(token.text ?? "")}}`;
    case "br":
      return "\\\\";
    case "link": {
      const label = renderLatexInlineTokens(token.tokens ?? [], ctx);
      if (!isSafeUrl(token.href ?? "")) return label;
      ctx.packages.add("hyperref");
      return `\\href{${escapeLatexUrl(token.href)}}{${label}}`;
    }
    case "image":
      return renderLatexImage(token.href ?? "", token.text ?? "", undefined, ctx);
    case "html":
      return escapeLatexText(token.raw ?? token.text ?? "");
    default:
      if (token.tokens) return renderLatexInlineTokens(token.tokens, ctx);
      return renderLatexTextWithPlaceholders(token.text ?? token.raw ?? "", ctx);
  }
}

function renderLatexMarkdownTokens(tokens: any[], ctx: LatexContext): string {
  return tokens.map((token) => renderLatexMarkdownToken(token, ctx)).join("");
}

function renderLatexMarkdownToken(token: any, ctx: LatexContext): string {
  switch (token.type) {
    case "space":
      return "";
    case "paragraph":
      return `${renderLatexInlineTokens(token.tokens ?? marked.Lexer.lexInline(token.text ?? ""), ctx)}\n\n`;
    case "heading": {
      const heading = renderLatexInlineTokens(token.tokens ?? marked.Lexer.lexInline(token.text ?? ""), ctx);
      const command = token.depth <= 2 ? "subsection" : "paragraph";
      return `\\${command}*{${heading}}\n\n`;
    }
    case "list": {
      const env = token.ordered ? "enumerate" : "itemize";
      const items = (token.items ?? [])
        .map((item: any) => `\\item ${renderLatexMarkdownTokens(item.tokens ?? [], ctx).trim()}\n`)
        .join("");
      return `\\begin{${env}}\n${items}\\end{${env}}\n\n`;
    }
    case "blockquote":
      return `\\begin{quote}\n${renderLatexMarkdownTokens(token.tokens ?? [], ctx).trim()}\n\\end{quote}\n\n`;
    case "code":
      return `\\begin{verbatim}\n${token.text ?? ""}\n\\end{verbatim}\n\n`;
    case "html":
      return `${escapeLatexText(token.raw ?? token.text ?? "")}\n\n`;
    default:
      if (token.tokens) return `${renderLatexInlineTokens(token.tokens, ctx)}\n\n`;
      return `${renderLatexTextWithPlaceholders(token.text ?? token.raw ?? "", ctx)}\n\n`;
  }
}

function renderLatexMarkdownBlock(source: string, ctx: LatexContext): string {
  const withTextCommands = renderLatexTextCommands(source, ctx);
  return renderLatexMarkdownTokens(marked.lexer(withTextCommands) as any[], ctx);
}

function renderAstBlocksLatex(blocks: Block[], ctx: LatexContext): string {
  return blocks
    .map((block) => {
      if (block.kind === "markdown") return renderLatexMarkdownBlock(block.source, ctx);
      if (block.kind === "error") {
        return `${renderLatexErrorText(block.message, block.source, ctx)}\n\n`;
      }
      const items = block.items
        .map((item) => {
          const label = item.label ? `[${renderLatexInline(item.label, ctx)}]` : "";
          return `\\item${label} ${renderAstBlocksLatex(item.blocks, ctx).trim()}\n`;
        })
        .join("");
      return `\\begin{${block.env}}\n${items}\\end{${block.env}}\n\n`;
    })
    .join("");
}

export function renderLatex(
  source: string,
  options: RenderLatexOptions = {},
): RenderLatexResult {
  const { source: mathProtected, mathBlocks } = protectMath(source);
  const ctx: LatexContext = {
    errors: [],
    latexBlocks: [],
    mathBlocks,
    packages: new Set(),
    attachmentPaths: options.attachmentPaths,
  };
  const withSizedImages = protectSizedImagesLatex(mathProtected, ctx);
  const blocks = parseBlocks(withSizedImages, ctx.errors);
  const body = renderAstBlocksLatex(blocks, ctx).trim();
  return {
    body,
    errors: ctx.errors,
    packages: Array.from(ctx.packages).sort(),
  };
}
