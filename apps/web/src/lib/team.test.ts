import { describe, expect, it } from "vitest";
import { suggestUsername } from "./team";

describe("username suggestion", () => {
  it("joins first two names with a dot, lowercase", () => {
    expect(suggestUsername("Sunita Devi Sharma")).toBe("sunita.devi");
    expect(suggestUsername("  Dr. Rao ")).toBe("dr.rao");
  });
  it("drops accents and symbols", () => {
    expect(suggestUsername("Zoë O'Neil")).toBe("zoe.oneil");
  });
  it("is empty for an empty name", () => {
    expect(suggestUsername("   ")).toBe("");
  });
});
