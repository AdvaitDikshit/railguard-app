"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TopBar } from "@/components/TopBar";
import { listReports, mediaUrl } from "@/lib/api";
import { SEVERITY_COLOR, severityLabel } from "@/lib/severity";
import type { ReportSummary } from "@/lib/types";

export default function HistoryPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReports()
      .then(setReports)
      .catch(() => setError("Could not load report history. Is the API running?"));
  }, []);

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="text-[15px] font-semibold text-ink">Inspection History</h1>
        <p className="mt-1 text-[13px] text-ink-soft">Most recent submissions, newest first.</p>

        {error && <p className="mt-6 font-mono text-[12px] text-accent">{error}</p>}

        {reports && reports.length === 0 && (
          <p className="mt-6 text-[13px] text-ink-soft">No inspections submitted yet.</p>
        )}

        {reports && reports.length > 0 && (
          <div className="mt-6 divide-y divide-rule border-y border-rule">
            {reports.map((r) => {
              const colorClass = r.ai_severity ? SEVERITY_COLOR[r.ai_severity] : "text-ink-soft border-rule";
              return (
                <Link
                  key={r.id}
                  href={`/report/${r.id}`}
                  className="flex items-center gap-4 py-3 hover:bg-page"
                >
                  {r.annotated_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={mediaUrl(r.annotated_url)}
                      alt=""
                      className="h-14 w-20 flex-shrink-0 border border-rule object-cover"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className={`border-l-2 pl-2 text-[13px] font-medium ${colorClass}`}>
                      {r.ai_severity ? severityLabel(r.ai_severity) : "—"}
                    </p>
                    <p className="mt-0.5 font-mono text-[11px] text-ink-soft">
                      {new Date(r.created_at).toLocaleString()} · {r.detection_count ?? 0} detection(s) · {r.status}
                    </p>
                  </div>
                  <span className="flex-shrink-0 font-mono text-[11px] text-ink-soft">{r.id.slice(0, 8)}</span>
                </Link>
              );
            })}
          </div>
        )}

        <Link href="/" className="mt-6 inline-block text-[12px] text-ink-soft hover:text-ink">
          ← Back to inspection
        </Link>
      </main>
    </div>
  );
}
