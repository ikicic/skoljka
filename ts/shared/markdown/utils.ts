export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function isSafeUrl(url: string, { allowAttachment = false }: { allowAttachment?: boolean } = {}): boolean {
  const trimmed = url.trim().replace(/[\u0000-\u001f\u007f\s]+/g, "");
  if (allowAttachment && trimmed.startsWith("attachment:")) return true;
  const schemeMatch = /^([A-Za-z][A-Za-z0-9+.-]*):/.exec(trimmed);
  if (!schemeMatch) return true;
  return ["http", "https", "mailto"].includes(schemeMatch[1].toLowerCase());
}

export function stripHtml(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, "")
    .replace(/&shy;/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_match, code) => String.fromCodePoint(Number.parseInt(code, 10)))
    .replace(/\s+/g, " ")
    .trim();
}
