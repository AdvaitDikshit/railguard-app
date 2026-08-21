import type { Severity } from "@/lib/types";
import { SEVERITY_COLOR, severityLabel } from "@/lib/severity";
import { RailDivider } from "./RailDivider";

export function AdvisoryStrip({ severity }: { severity: Severity }) {
  if (!severity.ai_heading) return null;
  const colorClass = SEVERITY_COLOR[severity.ai_severity] || "text-ink border-ink";

  return (
    <div className="border-t border-rule bg-panel px-6 py-5">
      <RailDivider />
      <div className="mx-auto mt-4 max-w-4xl">
        <p className={`border-l-2 pl-3 text-[15px] font-semibold ${colorClass}`}>
          {severity.ai_heading}
        </p>
        {severity.ai_risk_summary && (
          <p className="mt-2 max-w-[70ch] text-[13px] leading-relaxed text-ink-soft">
            {severity.ai_risk_summary}
          </p>
        )}

        {severity.ai_actions && severity.ai_actions.length > 0 && (
          <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
            {severity.ai_actions.map((a, i) => (
              <li key={i} className="flex gap-2 text-[12.5px] leading-snug text-ink">
                <span className="font-mono text-ink-soft">{String(i + 1).padStart(2, "0")}</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] text-ink-soft">
          {severity.ai_timeline && <span>Timeline: {severity.ai_timeline}</span>}
          {severity.ai_authority && <span>Escalate to: {severity.ai_authority}</span>}
        </div>

        <p className="mt-4 max-w-[70ch] text-[11px] leading-relaxed text-ink-soft">
          RailGuard is an AI-assisted visual screening tool, not a certified railway
          engineering inspection. This estimate does not confirm the track is safe or
          unsafe — a qualified engineer or authorized railway personnel must verify any
          finding before an operational decision is made.
        </p>
      </div>
    </div>
  );
}
