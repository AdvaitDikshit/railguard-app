"use client";

import { useEffect, useState } from "react";
import type { Detection } from "@/lib/types";
import { BoundingBoxOverlay } from "./BoundingBoxOverlay";

/**
 * An image with detection boxes drawn over it, scaled from the image's
 * natural pixel dimensions. Shared by the live inspect canvas (fed a
 * local blob preview URL) and the report detail page (fed a fetched
 * report's original_url) so both stay visually identical.
 *
 * Click-to-zoom: a small/hairline detection can be hard to actually see
 * at the canvas's normal display size — clicking the image opens it at
 * full size in a lightbox.
 */
export function OverlayImage({
  src,
  alt,
  detections,
  severity,
  imgClassName = "max-h-[62vh] max-w-full select-none",
}: {
  src: string;
  alt?: string;
  detections: Detection[] | null;
  severity: string | null;
  imgClassName?: string;
}) {
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null);
  const [zoomed, setZoomed] = useState(false);

  useEffect(() => {
    if (!zoomed) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomed(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomed]);

  const overlay = naturalSize && detections && severity && (
    <BoundingBoxOverlay
      detections={detections}
      naturalWidth={naturalSize.w}
      naturalHeight={naturalSize.h}
      severity={severity}
    />
  );

  return (
    <>
      <div className="relative max-h-full max-w-full">
        <button
          type="button"
          onClick={() => setZoomed(true)}
          className="group relative block cursor-zoom-in"
          aria-label="View full size"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={alt || "Track inspection frame"}
            className={imgClassName}
            onLoad={(e) => {
              const t = e.currentTarget;
              setNaturalSize({ w: t.naturalWidth, h: t.naturalHeight });
            }}
          />
          {overlay}
          <span className="pointer-events-none absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 font-mono text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">
            Click to zoom
          </span>
        </button>
      </div>

      {zoomed && (
        <div
          className="fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/90 p-6"
          onClick={() => setZoomed(false)}
        >
          <div className="relative max-h-full max-w-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={src} alt={alt || "Track inspection frame"} className="max-h-[90vh] max-w-full" />
            {overlay}
          </div>
        </div>
      )}
    </>
  );
}
