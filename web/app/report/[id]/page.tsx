"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { TopBar } from "@/components/TopBar";
import { OverlayImage } from "@/components/OverlayImage";
import { ResultPanel } from "@/components/ResultPanel";
import { AdvisoryStrip } from "@/components/AdvisoryStrip";
import { getReport, mediaUrl, ApiError } from "@/lib/api";
import type { Report } from "@/lib/types";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;
    getReport(params.id)
      .then(setReport)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Report not found."))
      .finally(() => setLoading(false));
  }, [params.id]);

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      {loading && (
        <p className="px-6 py-8 font-mono text-[12px] text-ink-soft">Loading report…</p>
      )}

      {error && (
        <div className="px-6 py-8">
          <p className="font-mono text-[12px] text-accent">{error}</p>
          <Link href="/history" className="mt-3 inline-block text-[12px] text-ink-soft hover:text-ink">
            ← Back to history
          </Link>
        </div>
      )}

      {report && (
        <>
          <div className="flex flex-1 flex-col lg:flex-row">
            <div className="flex-1">
              {report.original_url ? (
                <div className="relative flex w-full items-center justify-center bg-canvas p-3">
                  <OverlayImage
                    src={mediaUrl(report.original_url)}
                    detections={report.detections}
                    severity={report.severity?.ai_severity ?? null}
                  />
                </div>
              ) : (
                <div className="flex h-64 items-center justify-center bg-canvas">
                  <p className="font-mono text-[12px] text-page/60">Original image unavailable</p>
                </div>
              )}
            </div>

            <aside className="w-full border-t border-rule lg:w-[300px] lg:border-l lg:border-t-0">
              <ResultPanel report={report} loading={false} />
            </aside>
          </div>

          {report.severity && <AdvisoryStrip severity={report.severity} />}

          <div className="border-t border-rule px-6 py-3">
            <Link href="/history" className="text-[12px] text-ink-soft hover:text-ink">
              ← Back to history
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
