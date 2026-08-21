import { RailArt } from "./RailArt";

/**
 * RailGuard's one memorable visual moment: a schematic track, a scan-line
 * sweep, then a detection tag appears — a slow, quiet rehearsal of the
 * actual upload -> detect -> severity pipeline, using the app's own real
 * detection-tag styling (see BoundingBoxOverlay), not an illustrated train.
 * Only shown in the idle state (see app/page.tsx) — it steps out of the
 * way once someone is actually using the tool.
 */
export function TrackScanHero() {
  return (
    <div className="border-b border-rule bg-panel px-6 py-5">
      <p className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">
        AI-assisted railway track inspection
      </p>
      <div className="relative mt-3 h-[90px] w-full overflow-hidden">
        <RailArt className="h-full w-full" />

        <div className="track-scan-line absolute left-0 top-[14px] h-[62px] w-[2px] bg-accent shadow-[0_0_8px_rgba(163,24,42,0.55)]" />

        {/* Box straddles the top rail (rendered at 35% of container height,
            see RailArt's viewBox) — like a real detection sitting on the
            rail head, not floating above the track. */}
        <div className="track-scan-marker absolute left-[70%] top-6 opacity-0">
          <div className="h-4 w-8 rounded-[2px] border-2 border-sev-high" />
          <span className="mt-1 block whitespace-nowrap rounded bg-sev-high px-1 py-0.5 font-mono text-[9px] font-medium text-white">
            CRACK 91%
          </span>
        </div>
      </div>
    </div>
  );
}
