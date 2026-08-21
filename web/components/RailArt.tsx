"use client";

import { useId } from "react";

/**
 * The one shared rail line-art asset behind RailGuard's visual identity —
 * two rails + sleeper ticks, flat line-art, no gradient/photo. Used both
 * as the static structural divider (RailDivider) and as the base for the
 * animated scan/detect loop (TrackScanHero). Keeping it as one asset means
 * the animated hero and the quiet dividers elsewhere read as the same
 * visual language, not two competing ideas.
 *
 * The track runs the FULL viewBox width and fades to transparent at both
 * ends, rather than stopping short with a hard-capped line end — a rail
 * that just stops mid-frame with empty space after it reads as an
 * arbitrary, unfinished edge; fading it out reads as "the track
 * continues beyond what's shown," which is what a cropped view of a
 * real track actually looks like.
 */
export function RailArt({ className = "" }: { className?: string }) {
  const sleeperXs = Array.from({ length: 21 }, (_, i) => i * 40);
  const uid = useId();
  const gradientId = `rail-fade-${uid}`;
  const maskId = `rail-mask-${uid}`;

  return (
    <svg viewBox="0 0 800 100" className={className} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="white" stopOpacity="0" />
          <stop offset="8%" stopColor="white" stopOpacity="1" />
          <stop offset="92%" stopColor="white" stopOpacity="1" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </linearGradient>
        <mask id={maskId}>
          <rect x="0" y="0" width="800" height="100" fill={`url(#${gradientId})`} />
        </mask>
      </defs>
      <g mask={`url(#${maskId})`}>
        {sleeperXs.map((x) => (
          <line key={x} x1={x} y1={24} x2={x} y2={76} strokeWidth={2} className="stroke-rule" opacity={0.7} />
        ))}
        <line x1={0} y1={35} x2={800} y2={35} strokeWidth={3} className="stroke-ink-soft" />
        <line x1={0} y1={65} x2={800} y2={65} strokeWidth={3} className="stroke-ink-soft" />
      </g>
    </svg>
  );
}
