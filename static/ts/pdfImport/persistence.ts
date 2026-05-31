export const ACTIVE_JOB_KEY = "pdfImport:activeJobId";
export const DRAFT_PREFIX = "pdfImport:draft:";
export const DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
export const DRAFT_DEBOUNCE_MS = 500;

/** Return the newest saved draft job id, if any. */
export function findLatestDraftJobId(): string | null {
  let bestKey: string | null = null;
  let bestT = 0;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(DRAFT_PREFIX)) continue;
      try {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const env = JSON.parse(raw);
        if (env && typeof env.t === "number" && env.t > bestT) {
          bestT = env.t;
          bestKey = key;
        }
      } catch {
        // skip
      }
    }
  } catch {
    return null;
  }
  if (!bestKey) return null;
  return bestKey.slice(DRAFT_PREFIX.length);
}

export function loadActiveJobId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_JOB_KEY);
  } catch {
    return null;
  }
}

export function storeActiveJobId(id: string | null): void {
  try {
    if (id) localStorage.setItem(ACTIVE_JOB_KEY, id);
    else localStorage.removeItem(ACTIVE_JOB_KEY);
  } catch {
    // ignore
  }
}
