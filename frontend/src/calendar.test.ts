import { describe, expect, it } from "vitest";
import { calendarDays } from "./calendar";

describe("calendarDays", () => {
  it("builds a six-week Monday-first grid", () => {
    const days = calendarDays(new Date(2026, 10, 1));
    expect(days).toHaveLength(42);
    expect(days[0].date.getDay()).toBe(1);
    expect(days.filter((day) => day.current)).toHaveLength(30);
  });

  it("uses local date keys without shifting planned content", () => {
    const days = calendarDays(new Date(2026, 11, 1));
    expect(days.some((day) => day.key === "2026-12-03" && day.current)).toBe(true);
  });
});
