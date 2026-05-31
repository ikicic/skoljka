import type { SourceOption } from "./types";

function sourceSortKey(source: SourceOption): [number, string] {
  return [source.order ?? 0, source.slug];
}

export function sortSourcesByHierarchy(sources: SourceOption[]): SourceOption[] {
  const visibleIds = new Set(sources.map((source) => source.id));
  const byParent = new Map<number | null, SourceOption[]>();
  for (const source of sources) {
    const parentId = source.parentId && visibleIds.has(source.parentId)
      ? source.parentId
      : null;
    const children = byParent.get(parentId);
    if (children) children.push(source);
    else byParent.set(parentId, [source]);
  }
  for (const children of byParent.values()) {
    children.sort((a, b) => {
      const [orderA, slugA] = sourceSortKey(a);
      const [orderB, slugB] = sourceSortKey(b);
      return orderA - orderB || slugA.localeCompare(slugB);
    });
  }

  const result: SourceOption[] = [];
  const seen = new Set<number>();
  function visit(parentId: number | null, depth: number) {
    for (const source of byParent.get(parentId) ?? []) {
      if (seen.has(source.id)) continue;
      seen.add(source.id);
      result.push({ ...source, depth });
      visit(source.id, depth + 1);
    }
  }
  visit(null, 0);
  const remaining = sources
    .filter((source) => !seen.has(source.id))
    .sort((a, b) => {
      const [orderA, slugA] = sourceSortKey(a);
      const [orderB, slugB] = sourceSortKey(b);
      return orderA - orderB || slugA.localeCompare(slugB);
    });
  for (const source of remaining) {
    if (seen.has(source.id)) continue;
    seen.add(source.id);
    result.push({ ...source, depth: 0 });
    visit(source.id, 1);
  }
  return result;
}

export function sourceOptionLabel(source: SourceOption): string {
  return `${"— ".repeat(source.depth ?? 0)}${source.name}`;
}

export function slugifySource(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
