import Link from "next/link";

const STEPS: [string, string][] = [
  ["Observe safely", "Notice something unusual from a safe location — never approach the track."],
  ["Capture evidence", "Upload a photo, or use your device camera from where you're standing."],
  ["Get an AI-assisted read", "A computer-vision model checks the image and estimates a severity level."],
];

export function HomeIntro() {
  return (
    <div className="border-t border-rule bg-panel px-6 py-6">
      <div className="mx-auto max-w-4xl">
        <ol className="grid gap-5 sm:grid-cols-3">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="flex gap-3">
              <span className="font-mono text-[11px] text-ink-soft">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="text-[13px] font-medium text-ink">{title}</p>
                <p className="mt-0.5 text-[12px] leading-relaxed text-ink-soft">{body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-rule pt-4">
          <p className="font-mono text-[11px] text-ink-soft">
            Model: YOLOv8 crack detector · Confidence threshold 55%
          </p>
          <Link href="/how-it-works" className="text-[11px] text-ink-soft underline hover:text-ink">
            What this system does and does not do →
          </Link>
        </div>
      </div>
    </div>
  );
}
