import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { money, ratio, pct } from "@/lib/format";

type Format = "money" | "ratio" | "pct";

const FORMATTERS: Record<Format, (v: number) => string> = {
  money: (v) => money(v),
  ratio: (v) => ratio(v),
  pct: (v) => pct(v),
};

// easeOutCubic — fast start, gentle settle.
function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function toNumber(value: string | number): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

export interface AnimatedNumberProps {
  value: string | number;
  format?: Format;
  className?: string;
  durationMs?: number;
}

export function AnimatedNumber({
  value,
  format = "money",
  className,
  durationMs = 600,
}: AnimatedNumberProps) {
  const formatter = FORMATTERS[format];
  const target = toNumber(value);

  // The numeric value we tween from on the next change.
  const fromRef = useRef(target);
  // Live rAF handle, so we can cancel cleanly.
  const rafRef = useRef<number | null>(null);
  // Guard so the very first effect run still tweens from the initial value
  // (mount animation) without double-running under StrictMode unnecessarily.
  const mountedRef = useRef(false);

  const [display, setDisplay] = useState(() => formatter(target));
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    const to = target;

    // Nothing to animate — keep display in sync (e.g. format prop changed).
    if (from === to) {
      setDisplay(formatter(to));
      mountedRef.current = true;
      return;
    }

    // Flash direction only after the initial mount, so we don't flash on load.
    if (mountedRef.current) {
      const dir = to > from ? "up" : "down";
      setFlash(dir);
      if (flashTimer.current) clearTimeout(flashTimer.current);
      flashTimer.current = setTimeout(() => setFlash(null), durationMs);
    }
    mountedRef.current = true;

    const delta = to - from;
    const duration = Math.max(0, durationMs);
    let start: number | null = null;

    const step = (now: number) => {
      if (start === null) start = now;
      const elapsed = now - start;
      const t = duration === 0 ? 1 : Math.min(1, elapsed / duration);
      const current = from + delta * easeOut(t);
      setDisplay(formatter(current));
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        setDisplay(formatter(to));
        fromRef.current = to;
        rafRef.current = null;
      }
    };

    if (typeof requestAnimationFrame === "undefined") {
      // SSR / non-DOM: snap to final value.
      setDisplay(formatter(to));
      fromRef.current = to;
    } else {
      rafRef.current = requestAnimationFrame(step);
    }

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      // Settle the start point so an interrupted tween resumes from where it left.
      fromRef.current = target;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, format, durationMs]);

  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current);
    },
    [],
  );

  return (
    <span
      className={cn(
        "tnum tabular-nums transition-colors duration-300",
        flash === "up" && "text-ok",
        flash === "down" && "text-bad",
        className,
      )}
    >
      {display}
    </span>
  );
}
