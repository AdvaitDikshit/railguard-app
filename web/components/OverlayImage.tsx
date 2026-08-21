"use client";

import { useState } from "react";
import type { Detection } from "@/lib/types";
import { BoundingBoxOverlay } from "./BoundingBoxOverlay";

/**
 * An image with detection boxes drawn over it, scaled from the image's
 * natural pixel dimensions. Shared by the live inspect canvas (fed a
 * local blob preview URL) and the report detail page (fed a fetched
 * report's original_url) so both stay visually identical.
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

  return (
    <div className="relative max-h-full max-w-full">
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
      {detections && severity && naturalSize && (
        <BoundingBoxOverlay
          detections={detections}
          naturalWidth={naturalSize.w}
          naturalHeight={naturalSize.h}
          severity={severity}
        />
      )}
    </div>
  );
}
