export const MATH_RE =
  /(?<!\\)\$\$([\s\S]+?)(?<!\\)\$\$|(?<!\\)\$([^\$]+?)(?<!\\)\$/g;
export const PLACEHOLDER_PREFIX = "\x00MATH";
export const PLACEHOLDER_RE = /\x00MATH(\d+)\x00/g;
export const HTML_PLACEHOLDER_PREFIX = "§\x00HTML";
export const HTML_PLACEHOLDER_RE = /§\x00HTML(\d+)\x00§/g;
export const LATEX_PLACEHOLDER_PREFIX = "\x00LATEX";
export const LATEX_PLACEHOLDER_RE = /\x00LATEX(\d+)\x00/g;
export const IMAGE_WIDTH_RE =
  /!\[([^\]\n]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\{width=(\d+(?:\.\d+)?(?:px|pt|%))\}/g;

export const ONE_ARG_COMMANDS: Record<string, { tag: string; className?: string }> = {
  textbf: { tag: "strong" },
  emph: { tag: "em" },
  textit: { tag: "em" },
  sout: { tag: "s" },
  uline: { tag: "u" },
  underline: { tag: "u" },
  texttt: { tag: "code" },
  fbox: { tag: "span", className: "latex-fbox" },
  mbox: { tag: "span", className: "latex-mbox" },
};

export const SYMBOL_COMMANDS: Record<string, string> = {
  textasciicircum: "^",
  textasciitilde: "~",
  textbackslash: "\\",
};

export const ESCAPED_CHARS: Record<string, { html: string; text: string }> = {
  "\\": { html: "<br>", text: "\n" },
  "-": { html: "&shy;", text: "-" },
  "{": { html: "{", text: "{" },
  "}": { html: "}", text: "}" },
  "%": { html: "%", text: "%" },
  "_": { html: "&#95;", text: "_" },
  "&": { html: "&amp;", text: "&" },
  "$": { html: "$", text: "$" },
  "#": { html: "&#35;", text: "#" },
};

export interface RenderError {
  message: string;
  source: string;
}

export interface RenderMarkdownResult {
  html: string;
  text: string;
  errors: RenderError[];
}

export interface RenderMarkdownOptions {
  attachmentUrls?: Record<string, string>;
}

export interface RenderLatexOptions {
  attachmentPaths?: Record<string, string>;
}

export interface RenderLatexResult {
  body: string;
  errors: RenderError[];
  packages: string[];
}

export interface LatexContext {
  errors: RenderError[];
  latexBlocks: string[];
  mathBlocks: string[];
  packages: Set<string>;
  attachmentPaths?: Record<string, string>;
}
