import { describe, expect, it } from "vitest";
import { formatDate } from "./format";

describe("formatDate", () => {
  it("labels missing freshness clearly", () => {
    expect(formatDate(null)).toBe("Not yet");
  });

  it("formats a provider timestamp deterministically", () => {
    expect(formatDate("2026-11-25T14:30:00Z")).toContain("25 Nov 2026");
  });
});
