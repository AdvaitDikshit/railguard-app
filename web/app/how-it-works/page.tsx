import Link from "next/link";
import { TopBar } from "@/components/TopBar";

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-[15px] font-semibold text-ink">How it works</h1>

        <ol className="mt-6 space-y-5">
          {[
            ["Observe safely", "Notice something unusual on a railway track from a safe location. Never approach the track or step onto railway property to get a better photo."],
            ["Capture evidence", "Photograph it from where you're standing — upload an existing photo, or use your device camera."],
            ["Automated screening", "A computer-vision model trained on railway track imagery checks the photo for visible defects and estimates a severity level."],
            ["Review the result", "You see the detection, an AI-estimated severity, and recommended precautions — clearly labeled as AI-assisted, not a certified inspection."],
            ["Report generated", "A PDF evidence report is produced, including the image, detection data, and a disclaimer of what this system does and does not certify."],
            ["Qualified review", "Any escalation to an authority or engineering decision is made by a qualified human, not automatically by this system."],
          ].map(([title, body], i) => (
            <li key={title} className="flex gap-4">
              <span className="font-mono text-[12px] text-ink-soft">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="text-[13px] font-medium text-ink">{title}</p>
                <p className="mt-1 max-w-[60ch] text-[13px] leading-relaxed text-ink-soft">{body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-10 border-l-2 border-sev-high pl-3">
          <p className="text-[13px] font-medium text-ink">What RailGuard is not</p>
          <p className="mt-1 max-w-[60ch] text-[13px] leading-relaxed text-ink-soft">
            RailGuard does not certify a track as safe or unsafe, does not replace a
            physical engineering inspection, and does not automatically notify any
            railway authority. Submitting a report here means it has been submitted
            to this platform — it does not mean an authority has been notified.
          </p>
        </div>

        <Link href="/" className="mt-8 inline-block text-[12px] text-ink-soft hover:text-ink">
          ← Back to inspection
        </Link>
      </main>
    </div>
  );
}
