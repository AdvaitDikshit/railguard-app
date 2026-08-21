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
- `app/history/page.tsx` — recent report list
- `app/how-it-works/page.tsx` — plain-language flow + explicit disclaimer
- `components/InspectionCanvas.tsx` — drop zone, camera capture, and the
  image + bounding-box overlay (drawn client-side from detection
  coordinates, not the server's baked-in annotated image, so the visual
  style stays consistent with the rest of the UI)
- `components/BoundingBoxOverlay.tsx` — thin percentage-positioned boxes
  scaled from the image's natural pixel dimensions
- `lib/api.ts`, `lib/types.ts` — typed client for the FastAPI backend,
  mirrors `api/app/schemas.py`

## Design tokens

See `tailwind.config.ts` — `page`/`panel`/`ink`/`rule` for the calm
off-white chrome, `canvas` for the one deliberate dark inspection
viewport, `accent` (single muted railway red) for primary actions only,
`sev.*` for severity-specific colors (kept semantically separate from
the decorative accent).

## Not yet built

Authentication, duplicate-report clustering, admin dashboard, video
upload, map view — later roadmap phases, not part of this UI pass.
