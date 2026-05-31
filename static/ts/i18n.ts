type InterpolationValues = Record<string, string | number>;

declare global {
  interface Window {
    gettext?: (message: string) => string;
    ngettext?: (singular: string, plural: string, count: number) => string;
    interpolate?: (
      format: string,
      values: InterpolationValues,
      named: boolean,
    ) => string;
  }
}

export function gettext(message: string): string {
  return window.gettext ? window.gettext(message) : message;
}

export function ngettext(
  singular: string,
  plural: string,
  count: number,
): string {
  if (window.ngettext) return window.ngettext(singular, plural, count);
  return count === 1 ? singular : plural;
}

export function interpolate(
  format: string,
  values: InterpolationValues,
): string {
  if (window.interpolate) return window.interpolate(format, values, true);
  return format.replace(/%\(([^)]+)\)s/g, (_match, key) => String(values[key] ?? ""));
}
