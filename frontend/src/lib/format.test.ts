import { describe, expect, it } from "vitest";

import { money, pct, ratio } from "./format";

describe("formatters", () => {
  it("formats Decimal-string money", () => {
    expect(money("27327500.00")).toBe("$27,327,500.00");
    expect(money("0")).toBe("$0.00");
    expect(money(null)).toBe("—");
  });

  it("formats ratios and percentages", () => {
    expect(ratio("1.20")).toBe("1.20x");
    expect(ratio("0.89")).toBe("0.89x");
    expect(pct("0.85", 0)).toBe("85%");
    expect(pct("0.0909")).toBe("9.1%");
  });
});
