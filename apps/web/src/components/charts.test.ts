import { describe, expect, it } from "vitest";
import { niceMax } from "./charts";

describe("count axis", () => {
  it("is always even so the middle tick is a whole number", () => {
    for (const v of [0, 1, 2, 3, 4, 7, 9, 13, 27, 48, 230]) {
      const max = niceMax(v);
      expect(max).toBeGreaterThanOrEqual(v);
      expect(max % 2).toBe(0);
    }
  });
});
