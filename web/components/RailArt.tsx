/**
 * The one shared rail line-art asset behind RailGuard's visual identity —
 * two rails + sleeper ticks, flat line-art, no gradient/photo. Used both
 * as the static structural divider (RailDivider) and as the base for the
 * animated scan/detect loop (TrackScanHero). Keeping it as one asset means
 * the animated hero and the quiet dividers elsewhere read as the same
 * visual language, not two competing ideas.
 */
export function RailArt({ className = "" }: { className?: string }) {
  const sleeperXs = Array.from({ length: 20 }, (_, i) => 20 + i * 40);

  return (
    <svg viewBox="0 0 800 100" className={className} preserveAspectRatio="none" aria-hidden="true">
      {sleeperXs.map((x) => (
        <line key={x} x1={x} y1={24} x2={x} y2={76} strokeWidth={2} className="stroke-rule" opacity={0.7} />
      ))}
      <line x1={10} y1={35} x2={790} y2={35} strokeWidth={3} strokeLinecap="round" className="stroke-ink-soft" />
      <line x1={10} y1={65} x2={790} y2={65} strokeWidth={3} strokeLinecap="round" className="stroke-ink-soft" />
    </svg>
  );
}
