/**
 * The one shared rail line-art asset behind RailGuard's visual identity —
 * a small station anchoring the left end, two rails + sleeper ticks
 * running open-ended to the right (cropped by the container, not faded —
 * a station gives the left end a deliberate reason to stop; the right
 * end reads as "the line continues" precisely because nothing marks an
 * end there). Flat line-art throughout, no gradient/photo/fill.
 */
export function RailArt({ className = "" }: { className?: string }) {
  const sleeperXs = Array.from({ length: 19 }, (_, i) => 80 + i * 40);

  return (
    <svg viewBox="0 0 800 100" className={className} preserveAspectRatio="none" aria-hidden="true">
      {/* Station: a minimal canopy-on-a-post, marking a deliberate start
          of the line rather than an arbitrary crop. */}
      <line x1={6} y1={8} x2={6} y2={94} strokeWidth={3} className="stroke-ink-soft" />
      <line x1={6} y1={10} x2={58} y2={10} strokeWidth={2} className="stroke-ink-soft" />
      <line x1={58} y1={10} x2={58} y2={26} strokeWidth={2} className="stroke-ink-soft" />

      {sleeperXs.map((x) => (
        <line key={x} x1={x} y1={24} x2={x} y2={76} strokeWidth={2} className="stroke-rule" opacity={0.7} />
      ))}
      <line x1={0} y1={35} x2={800} y2={35} strokeWidth={3} className="stroke-ink-soft" />
      <line x1={0} y1={65} x2={800} y2={65} strokeWidth={3} className="stroke-ink-soft" />
    </svg>
  );
}
