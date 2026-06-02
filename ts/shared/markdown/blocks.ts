import type { RenderError } from "./types";

export type MarkdownBlock = { kind: "markdown"; source: string };
export type ListItem = {
  label?: string;
  blocks: Block[];
};
export type ListBlock = {
  kind: "list";
  env: "itemize" | "enumerate";
  items: ListItem[];
  source: string;
};
export type ErrorBlock = { kind: "error"; message: string; source: string };
export type Block = MarkdownBlock | ListBlock | ErrorBlock;

const SUPPORTED_ENVS = new Set(["itemize", "enumerate"]);
const COMMAND_RE_SOURCE = "\\\\(begin|end)\\{([A-Za-z]+)\\}|\\\\item\\b";

function isSupportedEnv(env: string): env is "itemize" | "enumerate" {
  return env === "itemize" || env === "enumerate";
}

function pushMarkdown(blocks: Block[], source: string): void {
  if (source) blocks.push({ kind: "markdown", source });
}

function errorBlock(message: string, source: string, errors: RenderError[]): ErrorBlock {
  errors.push({ message, source });
  return { kind: "error", message, source };
}

function parseItemLabel(source: string, itemEnd: number, errors: RenderError[]): {
  label?: string;
  contentStart: number;
} {
  const prefixMatch = /^[^\S\r\n]*/.exec(source.slice(itemEnd));
  const openIndex = itemEnd + (prefixMatch?.[0].length ?? 0);
  if (source[openIndex] !== "[") {
    return { contentStart: itemEnd };
  }

  let bracketDepth = 1;
  let braceDepth = 0;
  for (let i = openIndex + 1; i < source.length; i += 1) {
    if (source[i] === "\\") {
      i += 1;
      continue;
    }
    if (source[i] === "{") {
      braceDepth += 1;
      continue;
    }
    if (source[i] === "}" && braceDepth > 0) {
      braceDepth -= 1;
      continue;
    }
    if (braceDepth > 0) {
      continue;
    }
    if (source[i] === "[") {
      bracketDepth += 1;
      continue;
    }
    if (source[i] !== "]") continue;
    bracketDepth -= 1;
    if (bracketDepth === 0) {
      return {
        label: source.slice(openIndex + 1, i).trim(),
        contentStart: i + 1,
      };
    }
  }

  errors.push({ message: "Unclosed optional \\item label", source: source.slice(openIndex) });
  return { contentStart: itemEnd };
}

function parseItem(
  source: string,
  contentStart: number,
  contentEnd: number,
  label: string | undefined,
  errors: RenderError[],
): ListItem {
  return {
    label,
    blocks: parseBlocks(source.slice(contentStart, contentEnd).trim(), errors),
  };
}

export function parseBlocks(source: string, errors: RenderError[]): Block[] {
  const blocks: Block[] = [];
  let cursor = 0;
  while (cursor < source.length) {
    const begin = findNextSupportedBegin(source, cursor);
    if (!begin) {
      pushMarkdown(blocks, source.slice(cursor));
      break;
    }
    pushMarkdown(blocks, source.slice(cursor, begin.index));
    const parsed = parseListEnvironment(source, begin.index, begin.env, errors);
    blocks.push(parsed.block);
    cursor = parsed.endIndex;
  }
  return blocks;
}

function findNextSupportedBegin(source: string, start: number): { index: number; env: "itemize" | "enumerate" } | null {
  const re = /\\begin\{([A-Za-z]+)\}/g;
  re.lastIndex = start;
  for (;;) {
    const match = re.exec(source);
    if (!match) return null;
    if (isSupportedEnv(match[1])) return { index: match.index, env: match[1] };
  }
}

function parseListEnvironment(
  source: string,
  beginIndex: number,
  env: "itemize" | "enumerate",
  errors: RenderError[],
): { block: Block; endIndex: number } {
  const beginMatch = /^\\begin\{([A-Za-z]+)\}/.exec(source.slice(beginIndex));
  const contentStart = beginIndex + (beginMatch?.[0].length ?? 0);
  const items: ListItem[] = [];
  let currentItemStart: number | null = null;
  let currentItemLabel: string | undefined;
  let scanStart = contentStart;
  let nestedDepth = 0;

  const commandRe = new RegExp(COMMAND_RE_SOURCE, "g");
  commandRe.lastIndex = contentStart;
  for (;;) {
    const match = commandRe.exec(source);
    if (!match) {
      const broken = source.slice(beginIndex);
      const block = errorBlock(`Unclosed ${env} environment`, broken, errors);
      return { block, endIndex: source.length };
    }

    const raw = match[0];
    const command = match[1];
    const matchedEnv = match[2];

    if (command === "begin" && SUPPORTED_ENVS.has(matchedEnv)) {
      nestedDepth += 1;
      continue;
    }

    if (command === "end" && SUPPORTED_ENVS.has(matchedEnv)) {
      if (nestedDepth > 0) {
        nestedDepth -= 1;
        continue;
      }
      if (matchedEnv !== env) {
        const broken = source.slice(beginIndex, match.index + raw.length);
        const block = errorBlock(`Expected \\end{${env}} before \\end{${matchedEnv}}`, broken, errors);
        return { block, endIndex: match.index + raw.length };
      }
      if (currentItemStart !== null) {
        items.push(parseItem(source, currentItemStart, match.index, currentItemLabel, errors));
      } else if (source.slice(contentStart, match.index).trim()) {
        const broken = source.slice(contentStart, match.index).trim();
        items.push({
          blocks: [errorBlock(`Expected \\item in ${env} environment`, broken, errors)],
        });
      }
      return {
        block: {
          kind: "list",
          env,
          items,
          source: source.slice(beginIndex, match.index + raw.length),
        },
        endIndex: match.index + raw.length,
      };
    }

    if (raw === "\\item" && nestedDepth === 0) {
      if (currentItemStart !== null) {
        items.push(parseItem(source, currentItemStart, match.index, currentItemLabel, errors));
      } else if (source.slice(scanStart, match.index).trim()) {
        const broken = source.slice(scanStart, match.index).trim();
        items.push({
          blocks: [errorBlock(`Expected \\item in ${env} environment`, broken, errors)],
        });
      }
      const itemParts = parseItemLabel(source, match.index + raw.length, errors);
      currentItemStart = itemParts.contentStart;
      currentItemLabel = itemParts.label;
      scanStart = currentItemStart;
      commandRe.lastIndex = currentItemStart;
    }
  }
}
