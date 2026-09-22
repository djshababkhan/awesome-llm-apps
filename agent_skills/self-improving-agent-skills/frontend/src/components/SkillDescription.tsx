"use client";

import { useEffect, useRef, useState } from "react";

interface SkillDescriptionProps {
  text: string;
  /** Lines shown before clamping. The rest appears on hover. */
  clampLines?: number;
}

/**
 * Shows a skill's description, revealing the full text on hover when it is too
 * long to fit. The overlay floats above the card and ignores pointer events, so
 * revealing it never shifts the grid or blocks the card's own controls.
 */
export default function SkillDescription({
  text,
  clampLines = 6,
}: SkillDescriptionProps) {
  const clampedRef = useRef<HTMLParagraphElement>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  useEffect(() => {
    const measure = () => {
      const el = clampedRef.current;
      if (!el) return;
      // A clamped element reports more scroll height than it displays.
      setIsTruncated(el.scrollHeight > el.clientHeight + 1);
    };

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [text, clampLines]);

  return (
    <div className="relative">
      <p
        ref={clampedRef}
        className="text-[13px] leading-relaxed text-zinc-400"
        style={{
          display: "-webkit-box",
          WebkitLineClamp: clampLines,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {text}
      </p>

      {isTruncated && (
        <>
          <span
            aria-hidden="true"
            className="mt-1 block text-[11px] font-medium text-violet-400 opacity-80 transition-opacity group-hover:opacity-0"
          >
            Hover to read all
          </span>

          <div className="pointer-events-none absolute -left-2 -right-2 top-0 z-20 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
            <div className="max-h-80 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-[0_16px_40px_-12px_rgba(0,0,0,0.8)]">
              <p className="text-[13px] leading-relaxed text-zinc-200">
                {text}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
