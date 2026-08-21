"use client";

import { useState } from "react";
import Link from "next/link";

const NAV_ITEMS = [
  { href: "/", label: "Inspect" },
  { href: "/history", label: "History" },
  { href: "/video", label: "Video" },
  { href: "/map", label: "Map" },
  { href: "/how-it-works", label: "How it works" },
];

export function TopBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-rule">
      <div className="flex items-center justify-between px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="text-[15px] font-semibold tracking-tight text-ink"
          onClick={() => setOpen(false)}
        >
          RailGuard
        </Link>

        {/* Full nav row — only room for this from tablet width up. */}
        <nav className="hidden items-center gap-6 text-[13px] text-ink-soft md:flex">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-ink">
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Phone/narrow-tablet: a single toggle instead of squeezing five
            links into one row (which overflowed the viewport). */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="mobile-nav"
          className="flex h-8 w-8 flex-col items-center justify-center gap-1 md:hidden"
        >
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          <span
            className={`block h-[1.5px] w-5 bg-ink transition-transform ${open ? "translate-y-[3px] rotate-45" : ""}`}
          />
          <span
            className={`block h-[1.5px] w-5 bg-ink transition-transform ${open ? "-translate-y-[3px] -rotate-45" : ""}`}
          />
        </button>
      </div>

      {open && (
        <nav
          id="mobile-nav"
          className="flex flex-col border-t border-rule text-[13px] text-ink-soft md:hidden"
        >
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="border-b border-rule px-4 py-3 last:border-b-0 hover:bg-panel hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
