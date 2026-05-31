const COOKIE_NAME = "problem_views";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function parseViews(raw: string): Map<string, string> {
  const views = new Map<string, string>();
  for (const item of raw.split(",")) {
    const [key, value] = item.split(":", 2);
    if (key && (value === "c" || value === "t")) {
      views.set(key, value);
    }
  }
  return views;
}

function readCookie(name: string): string {
  const prefix = `${name}=`;
  return document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
    ?.slice(prefix.length) ?? "";
}

function writeViewsCookie(views: Map<string, string>) {
  const value = [...views.entries()]
    .map(([key, view]) => `${key}:${view}`)
    .join(",");
  document.cookie = `${COOKIE_NAME}=${value}; Max-Age=${MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
}

document.addEventListener("click", (event) => {
  const link = (event.target as Element | null)?.closest<HTMLAnchorElement>("[data-problem-view-link]");
  if (!link) return;

  const key = link.dataset.problemViewKey;
  const view = link.dataset.problemView;
  if (!key || (view !== "c" && view !== "t")) return;

  const views = parseViews(readCookie(COOKIE_NAME));
  views.set(key, view);
  writeViewsCookie(views);
});
