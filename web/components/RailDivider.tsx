import { RailArt } from "./RailArt";

/** The static, structural echo of RailArt — used as a section divider
 * elsewhere in the app, so the animated hero (TrackScanHero) isn't the
 * only place the rail motif appears, without adding a second animation. */
export function RailDivider() {
  return <RailArt className="h-3 w-full" />;
}
