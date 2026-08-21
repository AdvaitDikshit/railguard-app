"use client";

import type { Detection } from "@/lib/types";
import { SEVERITY_BG, SEVERITY_COLOR } from "@/lib/severity";

/**
 * Thin, precise overlay boxes with monospace corner labels — the
 * "instrument readout" treatment from Direction A, drawn client-side
 * over the original image using percentage positioning so it stays
 * aligned regardless of how large the image renders.
 */
export function BoundingBoxOverlay({
  detections,
  naturalWidth,
  naturalHeight,
  severity,
}: {
  detections: Detection[];
  naturalWidth: number;
  naturalHeight: number;
  severity: string;
}) {
  if (!naturalWidth || !naturalHeight) return null;
  const bgClass = SEVERITY_BG[severity] || "bg-ink";
  const borderClass = SEVERITY_COLOR[severity]?.split(" ")[1] || "border-ink"; // "border-sev-*"

  return (
    <div className="pointer-events-none absolute inset-0">
      {detections.map((d, i) => {
        const [x1, y1, x2, y2] = d.bbox;
        const left = (x1 / naturalWidth) * 100;
        const top = (y1 / naturalHeight) * 100;
        const width = ((x2 - x1) / naturalWidth) * 100;
        const height = ((y2 - y1) / naturalHeight) * 100;
        return (
          <div
            key={i}
            className={`absolute border-[1.5px] ${borderClass}`}
            style={{
              left: `${left}%`,
              top: `${top}%`,
              width: `${width}%`,
              height: `${height}%`,
            }}
          >
            <span
              className={`absolute -top-5 left-0 whitespace-nowrap px-1 py-[1px] font-mono text-[10px] text-white ${bgClass}`}
            >
              {d.class_name.toUpperCase()} {Math.round(d.confidence * 100)}% [{d.size_cat.toUpperCase()}]
            </span>
          </div>
        );
      })}
    </div>
  );
}
