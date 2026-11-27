import { describe, expect, it } from "vitest";
import { formatDate, formatMetric } from "./format";

describe("formatDate", () => {
  it("labels missing freshness clearly", () => {
    expect(formatDate(null)).toBe("Not yet");
  });

  it("formats a provider timestamp deterministically", () => {
    expect(formatDate("2026-11-25T14:30:00Z")).toContain("25 Nov 2026");
  });

  it("formats metric units without converting unavailable to zero", () => {
    expect(formatMetric(null, "count")).toBe("Unavailable");
    expect(formatMetric(84, "seconds")).toBe("1m 24s");
    expect(formatMetric(2.25, "minutes")).toBe("2.3 min");
    expect(formatMetric(0, "count")).toBe("0");
  });
});
