import { describe, expect, it } from "vitest";
import { passwordProblem } from "./password";

describe("new password rule", () => {
  const base = { username: "asha.devi", current: "Temp-Pass-123x" };
  it("needs 12 characters", () => {
    expect(passwordProblem("short", base)).toBe("tooShort");
  });
  it("refuses the username and the temporary password", () => {
    expect(passwordProblem("ASHA.DEVI-not", { ...base, username: "asha.devi-not" })).toBe("isUsername");
    expect(passwordProblem("Temp-Pass-123x", base)).toBe("sameAsCurrent");
  });
  it("needs the confirmation to match", () => {
    expect(passwordProblem("a-good-new-pass", { ...base, confirm: "a-good-new-pas" })).toBe("mismatch");
    expect(passwordProblem("a-good-new-pass", { ...base, confirm: "a-good-new-pass" })).toBeNull();
  });
});
