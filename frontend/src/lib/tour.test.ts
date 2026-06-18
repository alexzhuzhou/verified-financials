import { describe, expect, it } from "vitest";

import { TOUR } from "./tour";

const ROUTES = new Set([
  "/app",
  "/app/briefing",
  "/app/verification",
  "/app/borrowing-base",
  "/app/fccr",
  "/app/compare",
  "/app/setup",
]);

describe("guided tour script", () => {
  it("has six steps", () => {
    expect(TOUR).toHaveLength(6);
  });

  it("every step targets a known route and a valid scenario, with title + body", () => {
    for (const step of TOUR) {
      expect(ROUTES.has(step.route)).toBe(true);
      expect(["baseline", "stress"]).toContain(step.scenario);
      expect(step.title.length).toBeGreaterThan(0);
      expect(step.body).toBeTruthy();
    }
  });

  it("opens on the baseline overview and ends on the stress FCCR breach", () => {
    expect(TOUR[0]).toMatchObject({ route: "/app", scenario: "baseline" });
    expect(TOUR[TOUR.length - 1]).toMatchObject({ route: "/app/fccr", scenario: "stress" });
  });
});
