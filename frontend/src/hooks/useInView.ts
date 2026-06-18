import { useCallback, useState } from "react";

/**
 * Reveal helper for the landing page. Flips `inView` to true a couple of frames
 * after the element attaches, so CSS can transition it in (fade/rise, count-ups,
 * frame settle). Deliberately NOT gated on IntersectionObserver — content must
 * never be left hidden if the observer misbehaves. Attach the returned callback
 * `ref` to any element (callback ref → works on div/section/etc.).
 */
export function useInView() {
  const [inView, setInView] = useState(false);

  const ref = useCallback((node: HTMLElement | null) => {
    if (!node) return;
    if (typeof requestAnimationFrame === "undefined") {
      setInView(true);
      return;
    }
    // Two frames: let the element paint in its hidden state first, then
    // transition to visible so the CSS animation actually runs.
    requestAnimationFrame(() => requestAnimationFrame(() => setInView(true)));
  }, []);

  return { ref, inView };
}
