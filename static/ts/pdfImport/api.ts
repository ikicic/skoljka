import type { JobResponse } from "./types";

export interface PdfImportApiConfig {
  transcribeUrl: string;
  activeUrl: string;
  csrfHeaders: Record<string, string>;
}

export async function fetchJob(config: PdfImportApiConfig, jobId: string): Promise<JobResponse | null> {
  try {
    const r = await fetch(`${config.transcribeUrl}${jobId}/`, { headers: config.csrfHeaders });
    if (r.status === 404) return null;
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

export async function cancelJob(config: PdfImportApiConfig, jobId: string): Promise<void> {
  try {
    await fetch(`${config.transcribeUrl}${jobId}/cancel/`, {
      method: "POST",
      headers: config.csrfHeaders,
    });
  } catch {
    // best-effort
  }
}

export async function deleteJob(config: PdfImportApiConfig, jobId: string): Promise<void> {
  try {
    await fetch(`${config.transcribeUrl}${jobId}/delete/`, {
      method: "POST",
      headers: config.csrfHeaders,
    });
  } catch {
    // best-effort
  }
}

export async function fetchFirstActiveJobId(config: PdfImportApiConfig): Promise<string | null> {
  try {
    const r = await fetch(config.activeUrl, { headers: config.csrfHeaders });
    if (!r.ok) return null;
    const data = await r.json();
    return data.jobs?.[0]?.id ?? null;
  } catch {
    return null;
  }
}
