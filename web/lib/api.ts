import type { Report, ReportSummary } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {}

async function parseErrorBody(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail.map((d: any) => d.msg).join(", ");
    return JSON.stringify(body);
  } catch {
    return res.statusText;
  }
}

export interface SubmitReportOptions {
  file: File;
  source: "upload" | "camera";
  lat?: number;
  lng?: number;
  accuracyM?: number;
}

export async function submitReport(opts: SubmitReportOptions): Promise<Report> {
  const fd = new FormData();
  fd.append("file", opts.file);
  fd.append("source", opts.source);
  if (opts.lat !== undefined) fd.append("lat", String(opts.lat));
  if (opts.lng !== undefined) fd.append("lng", String(opts.lng));
  if (opts.accuracyM !== undefined) fd.append("accuracy_m", String(opts.accuracyM));

  const res = await fetch(`${API_URL}/api/reports`, { method: "POST", body: fd });
  if (!res.ok) throw new ApiError(await parseErrorBody(res));
  return res.json();
}

export async function listReports(limit = 50): Promise<ReportSummary[]> {
  const res = await fetch(`${API_URL}/api/reports?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(await parseErrorBody(res));
  return res.json();
}

export async function getReport(id: string): Promise<Report> {
  const res = await fetch(`${API_URL}/api/reports/${id}`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(await parseErrorBody(res));
  return res.json();
}

export function pdfUrl(id: string): string {
  return `${API_URL}/api/reports/${id}/pdf`;
}

export function mediaUrl(path: string): string {
  // original_url/annotated_url come back as "/media/..." relative paths.
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}
