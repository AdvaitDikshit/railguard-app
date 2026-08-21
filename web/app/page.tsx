"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { TopBar } from "@/components/TopBar";
import { ModeRail, type InputMode } from "@/components/ModeRail";
import { InspectionCanvas } from "@/components/InspectionCanvas";
import { ResultPanel } from "@/components/ResultPanel";
import { AdvisoryStrip } from "@/components/AdvisoryStrip";
import { HomeIntro } from "@/components/HomeIntro";
import { submitReport, ApiError } from "@/lib/api";
import type { Report } from "@/lib/types";

export default function InspectPage() {
  const [mode, setMode] = useState<InputMode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gps, setGps] = useState<{ lat: number; lng: number; accuracy: number } | null>(null);
  const [gpsStatus, setGpsStatus] = useState<"idle" | "pending" | "granted" | "unavailable">("idle");

  const handleModeChange = useCallback((m: InputMode) => {
    if (loading) return; // guard against a race with an in-flight submission
    setMode(m);
    setFile(null);
    setPreviewUrl(null);
    setReport(null);
    setError(null);
  }, [loading]);

  const handleFileSelected = useCallback((f: File) => {
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setReport(null);
    setError(null);

    if (navigator.geolocation) {
      setGpsStatus("pending");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGps({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          });
          setGpsStatus("granted");
        },
        () => {
          setGps(null);
          setGpsStatus("unavailable");
        },
        { timeout: 8000 }
      );
    } else {
      setGpsStatus("unavailable");
    }
  }, []);

  const runInspection = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await submitReport({
        file,
        source: mode,
        lat: gps?.lat,
        lng: gps?.lng,
        accuracyM: gps?.accuracy,
      });
      setReport(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Inspection failed. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, [file, mode, gps]);

  const reset = useCallback(() => {
    setFile(null);
    setPreviewUrl(null);
    setReport(null);
    setError(null);
    setGps(null);
    setGpsStatus("idle");
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      <div className="flex flex-1 flex-col lg:flex-row">
        <ModeRail mode={mode} onChange={handleModeChange} disabled={loading} />

        <main className="flex flex-1 flex-col">
          <div className="flex flex-1 flex-col lg:flex-row">
            <div className="flex-1">
              <InspectionCanvas
                mode={mode}
                previewUrl={previewUrl}
                onFileSelected={handleFileSelected}
                onRetake={reset}
                detections={report?.detections ?? null}
                severity={report?.severity?.ai_severity ?? null}
                disabled={loading}
              />
            </div>

            <aside className="w-full border-t border-rule lg:w-[300px] lg:border-l lg:border-t-0">
              <ResultPanel report={report} loading={loading} />
            </aside>
          </div>

          {!file && !report && <HomeIntro />}

          {/* action bar */}
          {file && !report && (
            <div className="flex items-center gap-3 border-t border-rule bg-panel px-6 py-3">
              <button
                onClick={runInspection}
                disabled={loading}
                className="rounded bg-ink px-4 py-2 text-[12px] font-medium tracking-wide text-page disabled:opacity-40"
              >
                {loading ? "RUNNING…" : "RUN INSPECTION"}
              </button>
              <button
                onClick={reset}
                disabled={loading}
                className="text-[12px] text-ink-soft hover:text-ink"
              >
                Clear
              </button>
              <span className="ml-auto font-mono text-[11px] text-ink-soft">
                {gpsStatus === "pending" && "Getting location…"}
                {gpsStatus === "granted" && gps && `GPS ${gps.lat.toFixed(4)}, ${gps.lng.toFixed(4)}`}
                {gpsStatus === "unavailable" && "Location unavailable — report will have no GPS tag"}
              </span>
            </div>
          )}
          {report && (
            <div className="flex items-center gap-3 border-t border-rule bg-panel px-6 py-3">
              <button
                onClick={reset}
                className="rounded border border-ink px-4 py-2 text-[12px] font-medium tracking-wide text-ink hover:bg-ink hover:text-page"
              >
                NEW INSPECTION
              </button>
              <Link
                href={`/report/${report.id}`}
                className="text-[12px] text-ink-soft hover:text-ink"
              >
                Permanent link to this report →
              </Link>
            </div>
          )}
          {error && (
            <div className="border-t border-rule bg-accent-soft px-6 py-3">
              <p className="font-mono text-[12px] text-accent">{error}</p>
            </div>
          )}
        </main>
      </div>

      {report?.severity && <AdvisoryStrip severity={report.severity} />}
    </div>
  );
}
