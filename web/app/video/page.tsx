"use client";

import { useCallback, useRef, useState } from "react";
import { TopBar } from "@/components/TopBar";
import { submitVideo, ApiError } from "@/lib/api";
import { SEVERITY_COLOR, severityLabel } from "@/lib/severity";
import type { VideoReport } from "@/lib/types";

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function VideoPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<VideoReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File | null) => {
    if (!f) return;
    setFile(f);
    setReport(null);
    setError(null);
  }, []);

  const run = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await submitVideo({ file });
      setReport(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Video analysis failed. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, [file]);

  const reset = useCallback(() => {
    setFile(null);
    setReport(null);
    setError(null);
  }, []);

  const highSeverityCount = report?.detections.filter(
    (d) => report.severity && ["HIGH", "CRITICAL"].includes(report.severity.ai_severity)
  ).length;

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />

      <div className="border-b border-rule px-6 py-4">
        <h1 className="text-[15px] font-semibold text-ink">Video Inspection</h1>
        <p className="mt-1 max-w-[65ch] text-[13px] text-ink-soft">
          Upload a short clip recorded walking beside the track. Each visible crack is
          tracked across frames and counted once, not once per frame. Longer clips are
          truncated to a processing cap — see below once analyzed.
        </p>
      </div>

      <main className="flex flex-1 flex-col px-6 py-6">
        {!report && (
          <div
            className={[
              "flex h-56 w-full max-w-2xl cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed p-8 text-center transition-colors",
              dragOver ? "border-accent bg-accent-soft" : "border-rule bg-canvas",
            ].join(" ")}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files[0] ?? null);
            }}
          >
            <p className={`font-mono text-[13px] ${dragOver ? "text-ink" : "text-page/80"}`}>
              {file ? file.name : "Drop a track video here, or click to browse"}
            </p>
            <p className={`font-mono text-[11px] ${dragOver ? "text-ink/60" : "text-page/40"}`}>
              MP4 · MOV · AVI · WEBP · MKV — up to 100MB
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.mov,.avi,.webm,.mkv"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
          </div>
        )}

        {file && !report && (
          <div className="mt-4 flex max-w-2xl items-center gap-3">
            <button
              onClick={run}
              disabled={loading}
              className="rounded bg-ink px-4 py-2 text-[12px] font-medium tracking-wide text-page disabled:opacity-40"
            >
              {loading ? "ANALYZING VIDEO…" : "RUN VIDEO ANALYSIS"}
            </button>
            <button onClick={reset} disabled={loading} className="text-[12px] text-ink-soft hover:text-ink">
              Clear
            </button>
          </div>
        )}

        {loading && (
          <p className="mt-3 max-w-2xl font-mono text-[12px] text-ink-soft">
            Running tracked detection across the video — this can take a while for longer clips.
          </p>
        )}

        {error && <p className="mt-4 font-mono text-[12px] text-accent">{error}</p>}

        {report && report.severity && (
          <div className="max-w-2xl">
            <div className={`border-l-2 pl-3 ${SEVERITY_COLOR[report.severity.ai_severity]}`}>
              <p className="text-[20px] font-semibold leading-none">
                {severityLabel(report.severity.ai_severity)}
              </p>
              <p className="mt-1 text-[13px] text-ink-soft">{report.severity.ai_heading}</p>
            </div>

            <dl className="mt-5 grid grid-cols-2 gap-4 font-mono text-[13px] sm:grid-cols-4">
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-ink-soft">Duration</dt>
                <dd className="text-ink">{report.duration_s?.toFixed(1)}s</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-ink-soft">Frames analyzed</dt>
                <dd className="text-ink">{report.frames_analyzed}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-ink-soft">Potential defects</dt>
                <dd className="text-ink">{report.detections.length}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-ink-soft">High-severity</dt>
                <dd className="text-ink">{highSeverityCount ?? 0}</dd>
              </div>
            </dl>

            {report.detections.length > 0 && (
              <div className="mt-6">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-soft">
                  Detections, in order of first appearance
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[420px] border-collapse text-[12px]">
                    <thead>
                      <tr className="border-b border-rule text-left text-ink-soft">
                        <th className="pb-1 font-mono font-normal">#</th>
                        <th className="pb-1 font-mono font-normal">First detected</th>
                        <th className="pb-1 font-mono font-normal">Confidence</th>
                        <th className="pb-1 font-mono font-normal">Size</th>
                        <th className="pb-1 font-mono font-normal">Frames seen</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono">
                      {report.detections
                        .slice()
                        .sort((a, b) => a.first_seen_s - b.first_seen_s)
                        .map((d, i) => (
                          <tr key={d.track_id} className="border-b border-rule/60">
                            <td className="py-1.5 text-ink-soft">{i + 1}</td>
                            <td className="py-1.5 text-ink">{formatTimestamp(d.first_seen_s)}</td>
                            <td className="py-1.5 text-ink">{(d.confidence * 100).toFixed(0)}%</td>
                            <td className="py-1.5 text-ink">{d.size_cat}</td>
                            <td className="py-1.5 text-ink">{d.frame_count}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <p className="mt-6 max-w-[65ch] text-[11px] leading-relaxed text-ink-soft">
              RailGuard is an AI-assisted visual screening tool, not a certified railway
              engineering inspection. This estimate does not confirm the track is safe or
              unsafe — a qualified engineer or authorized railway personnel must verify any
              finding before an operational decision is made.
            </p>

            <button
              onClick={reset}
              className="mt-6 rounded border border-ink px-4 py-2 text-[12px] font-medium tracking-wide text-ink hover:bg-ink hover:text-page"
            >
              NEW VIDEO
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
