"use client";

import { useEffect, useRef, useState } from "react";
import { RailArt } from "./RailArt";

/**
 * RailGuard's one memorable visual moment: a schematic track, a scan-line
 * sweep, then a detection tag appears — a slow, quiet rehearsal of the
 * actual upload -> detect -> severity pipeline, using the app's own real
 * detection-tag styling (see BoundingBoxOverlay), not an illustrated train.
 * Only shown in the idle state (see app/page.tsx) — it steps out of the
 * way once someone is actually using the tool.
 *
 * The crack's position and confidence re-roll on every loop (via the
 * scan-line's `animationiteration` event), so it doesn't always "find"
 * the same defect in the same spot — a static repeat would read as a
 * canned demo rather than a live inspection.
 */
const MIN_X = 15; // stay clear of the station glyph on the left
const MAX_X = 85; // stay clear of the marker label clipping at the edge
const MIN_CONF = 76;
const MAX_CONF = 97;

function randomTargetX() {
  return Math.round(MIN_X + Math.random() * (MAX_X - MIN_X));
}
function randomConfidence() {
  return Math.round(MIN_CONF + Math.random() * (MAX_CONF - MIN_CONF));
}

export function TrackScanHero() {
  // Static defaults for the server-rendered/first-paint markup — actual
  // randomization happens client-side in the effect below, so hydration
  // never mismatches a server-random value against a client-random one.
  const [targetX, setTargetX] = useState(70);
  const [confidence, setConfidence] = useState(91);
  const lineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTargetX(randomTargetX());
    setConfidence(randomConfidence());

    const el = lineRef.current;
    if (!el) return;
    const reroll = () => {
      setTargetX(randomTargetX());
      setConfidence(randomConfidence());
    };
    el.addEventListener("animationiteration", reroll);
    return () => el.removeEventListener("animationiteration", reroll);
  }, []);

  return (
    <div className="border-b border-rule bg-panel px-6 py-5">
      <p className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">
        AI-assisted railway track inspection
      </p>
      <div
        className="relative mt-3 h-[90px] w-full overflow-hidden"
        style={{ "--target-x": `${targetX}%` } as React.CSSProperties}
      >
        <RailArt className="h-full w-full" />

        <div
          ref={lineRef}
          className="track-scan-line absolute left-0 top-[14px] h-[62px] w-[2px] bg-accent shadow-[0_0_8px_rgba(163,24,42,0.55)]"
        />

        {/* Box straddles the top rail (rendered at 35% of container height,
            see RailArt's viewBox) — like a real detection sitting on the
            rail head, not floating above the track. Position is plain
            inline style (not the keyframe) since it only needs to change
            between cycles, not animate mid-cycle. */}
        <div
          className="track-scan-marker absolute top-6 opacity-0"
          style={{ left: `${targetX}%` }}
        >
          <div className="h-4 w-8 rounded-[2px] border-2 border-sev-high" />
          <span className="mt-1 block whitespace-nowrap rounded bg-sev-high px-1 py-0.5 font-mono text-[9px] font-medium text-white">
            CRACK {confidence}%
          </span>
        </div>
      </div>
    </div>
  );
}
