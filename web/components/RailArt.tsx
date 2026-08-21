/**
 * The one shared rail line-art asset behind RailGuard's visual identity —
 * a small station canopy anchoring the left end, two rails + sleeper
 * ticks running open-ended to the right (cropped by the container, not
 * faded — a station gives the left end a deliberate reason to stop; the
 * right end reads as "the line continues" precisely because nothing
 * marks an end there). Flat line-art throughout, no gradient/photo/fill.
 *
 * `shapeRendering="crispEdges"` turns off anti-aliasing on these
 * axis-aligned strokes — without it, stretching the 800x100 viewBox to
 * an arbitrary container width leaves sub-pixel line edges that render
 * soft/blurry instead of crisp.
 */
export function RailArt({ className = "" }: { className?: string }) {
  const sleeperXs = Array.from({ length: 18 }, (_, i) => 90 + i * 40);

  return (
    <svg
      viewBox="0 0 800 100"
      className={className}
      preserveAspectRatio="none"
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      {/* Station: a flat canopy roof on two posts, roofing over the start
          of the line — reads as a platform shelter rather than a mark on
          the track itself. */}
      <line x1={10} y1={16} x2={56} y2={16} strokeWidth={3} className="stroke-ink-soft" />
      <line x1={10} y1={16} x2={10} y2={24} strokeWidth={2} className="stroke-ink-soft" />
      <line x1={56} y1={16} x2={56} y2={24} strokeWidth={2} className="stroke-ink-soft" />
      <line x1={20} y1={22} x2={20} y2={88} strokeWidth={3} className="stroke-ink-soft" />
      <line x1={46} y1={22} x2={46} y2={88} strokeWidth={3} className="stroke-ink-soft" />
      {/* Small caps label under the roofline, Swiss-signage style, so the
          glyph reads unambiguously as "station" rather than a generic
          shelter shape. */}
      <text
        x={33}
        y={12}
        textAnchor="middle"
        className="font-mono fill-ink-soft"
        style={{ fontSize: 9, letterSpacing: 1, fontWeight: 600 }}
      >
        STATION
      </text>

      {sleeperXs.map((x) => (
        <line key={x} x1={x} y1={24} x2={x} y2={76} strokeWidth={2} className="stroke-rule" opacity={0.7} />
      ))}
      <line x1={0} y1={35} x2={800} y2={35} strokeWidth={4} className="stroke-ink-soft" />
      <line x1={0} y1={65} x2={800} y2={65} strokeWidth={4} className="stroke-ink-soft" />
    </svg>
  );
}
