export type SeverityLevel = "NO_CRACK" | "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "text-sev-critical border-sev-critical",
  HIGH: "text-sev-high border-sev-high",
  MODERATE: "text-sev-moderate border-sev-moderate",
  LOW: "text-sev-low border-sev-low",
  NO_CRACK: "text-sev-ok border-sev-ok",
};

export const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "bg-sev-critical",
  HIGH: "bg-sev-high",
  MODERATE: "bg-sev-moderate",
  LOW: "bg-sev-low",
  NO_CRACK: "bg-sev-ok",
};

export function severityLabel(sev: string): string {
  return sev.replace("_", " ");
}
