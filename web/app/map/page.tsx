"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { TopBar } from "@/components/TopBar";
import { listReports } from "@/lib/api";
import type { ReportSummary } from "@/lib/types";

// Leaflet touches `window` at import time — must never run during SSR.
const ReportsMap = dynamic(() => import("@/components/ReportsMap").then((m) => m.ReportsMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-canvas">
      <p className="font-mono text-[12px] text-page/70">Loading map…</p>
    </div>
  ),
});

export default function MapPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReports(200)
      .then(setReports)
      .catch(() => setError("Could not load reports. Is the API running?"));
  }, []);

  const withLocation = reports?.filter((r) => r.lat != null && r.lng != null) ?? [];

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <div className="border-b border-rule px-6 py-4">
        <h1 className="text-[15px] font-semibold text-ink">Report Map</h1>
        <p className="mt-1 text-[13px] text-ink-soft">
          {reports === null
            ? "Loading…"
            : `${withLocation.length} of ${reports.length} report(s) have a recorded location.`}
        </p>
      </div>

      {error && <p className="px-6 py-8 font-mono text-[12px] text-accent">{error}</p>}

      {reports && (
        <div className="flex-1" style={{ minHeight: "70vh" }}>
          <ReportsMap reports={reports} />
        </div>
      )}
    </div>
  );
}
