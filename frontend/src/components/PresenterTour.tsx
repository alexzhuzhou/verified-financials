import { ChevronLeft, ChevronRight, Presentation, X } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAppStore } from "@/lib/store";
import { TOUR } from "@/lib/tour";
import { cn } from "@/lib/utils";

const HIGHLIGHT_DELAY_MS = 400; // let the route render before scrolling/ringing
const HIGHLIGHT_HOLD_MS = 2600;

/**
 * Guided presenter mode: a non-modal floating panel that auto-drives the app
 * through the deal narrative (navigate + set scenario + soft-highlight). Mounted
 * once in AppLayout; renders nothing unless a tour is active.
 */
export function PresenterTour() {
  const tourStep = useAppStore((s) => s.tourStep);
  const setScenario = useAppStore((s) => s.setScenario);
  const setOverrides = useAppStore((s) => s.setOverrides);
  const nextTourStep = useAppStore((s) => s.nextTourStep);
  const prevTourStep = useAppStore((s) => s.prevTourStep);
  const exitTour = useAppStore((s) => s.exitTour);
  const navigate = useNavigate();

  // Drive the app for the current step: scenario → overrides → navigate → highlight.
  useEffect(() => {
    if (tourStep === null) return;
    const step = TOUR[tourStep];
    if (!step) return;

    setScenario(step.scenario); // also clears any what-if edits
    if (step.overrides) setOverrides(step.overrides);
    navigate(step.route);

    if (!step.highlight) return;
    const id = step.highlight;
    const t = window.setTimeout(() => {
      const el = document.getElementById(id);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("tour-highlight");
      window.setTimeout(() => el.classList.remove("tour-highlight"), HIGHLIGHT_HOLD_MS);
    }, HIGHLIGHT_DELAY_MS);
    return () => {
      window.clearTimeout(t);
      document.getElementById(id)?.classList.remove("tour-highlight");
    };
    // actions/navigate are stable refs; re-run only when the step changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tourStep]);

  const total = TOUR.length;
  const isLast = tourStep !== null && tourStep === total - 1;

  // Keyboard shortcuts for the presenter (only while the tour is active).
  useEffect(() => {
    if (tourStep === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") exitTour();
      else if (e.key === "ArrowRight") isLast ? exitTour() : nextTourStep();
      else if (e.key === "ArrowLeft") prevTourStep();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tourStep, isLast]);

  if (tourStep === null) return null;
  const step = TOUR[tourStep];
  if (!step) return null;

  return (
    <div className="no-print pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-4">
      <Card
        className="pointer-events-auto w-full max-w-xl border-primary/30 shadow-lg"
        role="dialog"
        aria-label="Guided tour"
      >
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Presentation className="h-4 w-4 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                Guided tour
              </span>
              <span className="text-xs text-muted-foreground">
                Step {tourStep + 1} of {total}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={exitTour}
              aria-label="Exit tour"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <h3 className="mt-2 font-serif text-lg font-semibold">{step.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.body}</p>

          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-1.5" aria-hidden>
              {TOUR.map((_, i) => (
                <span
                  key={i}
                  className={cn(
                    "h-1.5 w-1.5 rounded-full transition-colors",
                    i === tourStep ? "bg-primary" : "bg-muted-foreground/30",
                  )}
                />
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={prevTourStep} disabled={tourStep === 0}>
                <ChevronLeft className="h-4 w-4" /> Back
              </Button>
              <Button size="sm" onClick={isLast ? exitTour : nextTourStep}>
                {isLast ? (
                  "Finish"
                ) : (
                  <>
                    Next <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
