# RailGuard Web

Next.js + TypeScript + Tailwind frontend for the [api/](../api/) FastAPI
service. Implements the "machine-vision inspection tool disciplined with
Swiss railway-signage restraint" direction: a dark image canvas with thin
precise detection overlays, calm off-white chrome, one functional accent,
monospace data — deliberately not a generic AI-dashboard look.

## Setup

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Requires the API running at the URL in `.env.local` (defaults to
`http://localhost:8000` — see [../api/README.md](../api/README.md)).

## Structure

- `app/page.tsx` — the single Inspect screen (upload/camera → run → results)
- `app/history/page.tsx` — recent report list, links to each report's
  permanent `/report/[id]` page
- `app/report/[id]/page.tsx` — a single historic report, same visual
  treatment as a live result (via the shared `OverlayImage` component)
- `app/map/page.tsx` — Leaflet/OpenStreetMap view of every report with a
  recorded location, marker color keyed to severity
- `app/how-it-works/page.tsx` — plain-language flow + explicit disclaimer
- `components/InspectionCanvas.tsx` — drop zone, camera capture, and the
  image + bounding-box overlay
- `components/OverlayImage.tsx` — image + bounding-box overlay (drawn
  client-side from detection coordinates, not the server's baked-in
  annotated image, so the visual style stays consistent everywhere it's
  used — the live inspect flow and the historic report page both use it)
- `components/BoundingBoxOverlay.tsx` — thin percentage-positioned boxes
  scaled from the image's natural pixel dimensions
- `components/ReportsMap.tsx` — the actual Leaflet map, dynamically
  imported with `ssr: false` (Leaflet needs `window`, so it can never
  run during server rendering)
- `lib/api.ts`, `lib/types.ts` — typed client for the FastAPI backend,
  mirrors `api/app/schemas.py`

**Note on `next.config.mjs`:** `reactStrictMode` is off. react-leaflet
v4's `MapContainer` isn't StrictMode-safe — dev-mode's double-invoked
effects mount it twice, and Leaflet throws re-initializing a map on a
DOM node that already has one. Production builds don't double-invoke
effects, so this only matters in dev; disabling it is the fix
react-leaflet's own docs point to for this exact issue.

## Design tokens

See `tailwind.config.ts` — `page`/`panel`/`ink`/`rule` for the calm
off-white chrome, `canvas` for the one deliberate dark inspection
viewport, `accent` (single muted railway red) for primary actions only,
`sev.*` for severity-specific colors (kept semantically separate from
the decorative accent).

## Not yet built

Full user authentication (the API's `/verify` has a single admin
token, not user accounts), duplicate-report clustering, admin
dashboard, video upload — later roadmap phases.

## Known gap

Camera capture (`getUserMedia`) is code-complete but has not been
verified against a real physical device/browser — only against a
sandboxed test browser that blocks camera permission by design. Worth
a real-device check before relying on it.
