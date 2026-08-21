import Link from "next/link";

export function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-rule px-6 py-3">
      <Link href="/" className="text-[15px] font-semibold tracking-tight text-ink">
        RailGuard
      </Link>
      <nav className="flex items-center gap-6 text-[13px] text-ink-soft">
        <Link href="/" className="hover:text-ink">
          Inspect
        </Link>
        <Link href="/history" className="hover:text-ink">
          History
        </Link>
        <Link href="/video" className="hover:text-ink">
          Video
        </Link>
        <Link href="/map" className="hover:text-ink">
          Map
        </Link>
        <Link href="/how-it-works" className="hover:text-ink">
          How it works
        </Link>
      </nav>
    </header>
  );
}
