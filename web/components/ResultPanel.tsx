"use client";

import Link from "next/link";
import type { Report } from "@/lib/types";
import { SEVERITY_COLOR, severityLabel } from "@/lib/severity";
import { pdfUrl } from "@/lib/api";

export function ResultPanel({
  report,
  loading,
}: {
  report: Report | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex h-full flex-col justify-center px-4 py-6">
        <p className="font-mono text-[12px] text-ink-soft">RUNNING INSPECTION…</p>
      </div>
    );
  }

  if (!report || !report.severity) {
    return (
      <div className="flex h-full flex-col justify-center px-4 py-6">
        <p className="text-[13px] leading-relaxed text-ink-soft">
          Load an image to begin. Results — severity, confidence, and detected
          defects — will appear here.
        </p>
      </div>
    );
  }

  const sev = report.severity;
  const colorClass = SEVERITY_COLOR[sev.ai_severity] || "text-ink border-ink";

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto px-4 py-5">
      {report.status === "duplicate" && report.cluster_id && (
        <div className="border-l-2 border-sev-moderate bg-accent-soft px-3 py-2">
          <p className="text-[12px] font-medium text-ink">Likely a repeat report</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-ink-soft">
            This looks like the same physical defect as an earlier report, based on
            location and image similarity.{" "}
            <Link href={`/report/${report.cluster_id}`} className="text-steel underline">
              View original report →
            </Link>
          </p>
        </div>
      )}

      <div>
        <p className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">Severity (AI-estimated)</p>
        <p className={`mt-1 border-l-2 pl-2 text-[22px] font-semibold leading-none ${colorClass}`}>
          {severityLabel(sev.ai_severity)}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 font-mono text-[12px]">
        <div>
          <dt className="text-ink-soft">Confidence</dt>
          <dd className="text-ink">{(sev.ai_max_confidence * 100).toFixed(0)}%</dd>
        </div>
        <div>
          <dt className="text-ink-soft">Detections</dt>
          <dd className="text-ink">{sev.ai_detection_count}</dd>
        </div>
        <div>
          <dt className="text-ink-soft">Report ID</dt>
          <dd className="truncate text-ink" title={report.id}>{report.id.slice(0, 10)}</dd>
        </div>
        <div>
          <dt className="text-ink-soft">Status</dt>
          <dd className="text-ink">{report.status}</dd>
        </div>
      </dl>

      {report.detections.length > 0 && (
        <div>
          <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-soft">Detections</p>
          <table className="w-full border-collapse text-[11px]">
            <thead>
              <tr className="border-b border-rule text-left text-ink-soft">
                <th className="pb-1 font-mono font-normal">#</th>
                <th className="pb-1 font-mono font-normal">Class</th>
                <th className="pb-1 font-mono font-normal">Conf</th>
                <th className="pb-1 font-mono font-normal">Size</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {report.detections.map((d, i) => (
                <tr key={i} className="border-b border-rule/60">
                  <td className="py-1 text-ink-soft">{i + 1}</td>
                  <td className="py-1 text-ink">{d.class_name}</td>
                  <td className="py-1 text-ink">{(d.confidence * 100).toFixed(0)}%</td>
                  <td className="py-1 text-ink">{d.size_cat}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report.location?.lat != null && (
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">Location</p>
          <p className="mt-1 font-mono text-[11px] text-ink">
            {report.location.lat.toFixed(5)}, {report.location.lng?.toFixed(5)}
            {report.location.accuracy_m ? ` (±${Math.round(report.location.accuracy_m)}m)` : ""}
          </p>
        </div>
      )}

      <div>
        <p className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">Engineering assessment</p>
        {sev.engineering_severity ? (
          <div className="mt-1 border-l-2 border-sev-low pl-2">
            <p className="text-[13px] font-semibold text-ink">{severityLabel(sev.engineering_severity)}</p>
            <p className="mt-0.5 font-mono text-[11px] text-ink-soft">
              Verified by {sev.verified_by}
              {sev.verified_at ? ` · ${new Date(sev.verified_at).toLocaleDateString()}` : ""}
            </p>
            {sev.engineering_notes && (
              <p className="mt-1 text-[12px] leading-relaxed text-ink">{sev.engineering_notes}</p>
            )}
          </div>
        ) : (
          <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
            Not yet reviewed by a qualified engineer or authorized railway personnel.
          </p>
        )}
      </div>

      <div className="border-t border-rule pt-3 font-mono text-[11px] text-ink-soft">
        <p>✓ Submitted to platform</p>
        <p>— Authority notified: <span className="text-ink">No verified channel connected</span></p>
      </div>

      <a
        href={pdfUrl(report.id)}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto inline-flex items-center justify-center rounded border border-ink px-3 py-2 text-[12px] font-medium tracking-wide text-ink hover:bg-ink hover:text-page"
      >
        DOWNLOAD PDF REPORT
      </a>
    </div>
  );
}
