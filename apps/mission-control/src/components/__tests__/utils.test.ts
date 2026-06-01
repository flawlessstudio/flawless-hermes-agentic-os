import { describe, it, expect } from "vitest";
import { formatRelativeTime, truncate, cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("handles conditional classes", () => {
    expect(cn("a", false && "b", "c")).toBe("a c");
  });
});

describe("truncate", () => {
  it("does not truncate short strings", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates long strings", () => {
    const result = truncate("hello world", 8);
    expect(result).toHaveLength(8);
    expect(result).toEndWith("…");
  });
});

describe("formatRelativeTime", () => {
  it("returns seconds for recent ts", () => {
    const ts = (Date.now() - 5000) / 1000;
    expect(formatRelativeTime(ts)).toMatch(/\ds ago/);
  });

  it("returns minutes for older ts", () => {
    const ts = (Date.now() - 120000) / 1000;
    expect(formatRelativeTime(ts)).toMatch(/\dm ago/);
  });
});
