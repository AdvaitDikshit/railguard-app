"use client";

export type InputMode = "upload" | "camera";

export function ModeRail({
  mode,
  onChange,
}: {
  mode: InputMode;
  onChange: (m: InputMode) => void;
}) {
  const items: { key: InputMode; label: string }[] = [
    { key: "upload", label: "Upload" },
    { key: "camera", label: "Camera" },
  ];

  return (
    <div className="flex flex-row gap-2 border-b border-rule px-4 py-2 lg:flex-col lg:border-b-0 lg:border-r lg:px-3 lg:py-4">
      {items.map((item) => {
        const active = mode === item.key;
        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            className={[
              "rounded px-3 py-2 text-left text-[12px] font-medium tracking-wide",
              active
                ? "bg-ink text-page"
                : "text-ink-soft hover:bg-panel hover:text-ink",
            ].join(" ")}
            aria-pressed={active}
          >
            {item.label.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
