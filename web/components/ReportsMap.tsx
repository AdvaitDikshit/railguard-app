"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import Link from "next/link";
import type { ReportSummary } from "@/lib/types";
import { severityLabel } from "@/lib/severity";

// Severity -> marker color, matching the same palette used everywhere
// else (ResultPanel, AdvisoryStrip, History) — one consistent visual
// language for severity across the whole app.
const MARKER_COLOR: Record<string, string> = {
  CRITICAL: "#b3261e",
  HIGH: "#c1701f",
  MODERATE: "#a68a1f",
  LOW: "#2f7a4f",
  NO_CRACK: "#2f7a4f",
};

function markerIcon(severity: string | null) {
  const color = (severity && MARKER_COLOR[severity]) || "#5b6470";
  return L.divIcon({
    className: "",
    html: `<span style="
      display:block; width:14px; height:14px; border-radius:50%;
      background:${color}; border:2px solid white;
      box-shadow:0 0 0 1px rgba(0,0,0,.3);
    "></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export function ReportsMap({ reports }: { reports: ReportSummary[] }) {
  const withLocation = reports.filter((r) => r.lat != null && r.lng != null);

  if (withLocation.length === 0) {
    return (
      <div className="flex h-full items-center justify-center bg-canvas">
        <p className="max-w-sm text-center font-mono text-[12px] text-page/70">
          No reports with a recorded location yet.
        </p>
      </div>
    );
  }

  const center: [number, number] = [withLocation[0].lat as number, withLocation[0].lng as number];

  return (
    <MapContainer center={center} zoom={12} className="h-full w-full" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {withLocation.map((r) => (
        <Marker key={r.id} position={[r.lat as number, r.lng as number]} icon={markerIcon(r.ai_severity)}>
          <Popup>
            <div className="font-sans text-[12px]">
              <p className="font-semibold">{r.ai_severity ? severityLabel(r.ai_severity) : "Unknown"}</p>
              <p className="mt-0.5 text-ink-soft">
                {new Date(r.created_at).toLocaleDateString()} · {r.detection_count ?? 0} detection(s)
              </p>
              <Link href={`/report/${r.id}`} className="mt-1 inline-block text-steel underline">
                View report →
              </Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
