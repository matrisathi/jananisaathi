/** Mirrors the server rule (app/core/security.py new_password_problem) so the
 * person sees the problem before submitting. The server still decides. */
export const MIN_PASSWORD_LENGTH = 12;

export type PasswordProblem = "tooShort" | "isUsername" | "sameAsCurrent" | "mismatch";

export function passwordProblem(
  next: string,
  { username, current, confirm }: { username: string; current?: string; confirm?: string },
): PasswordProblem | null {
  if (next.length < MIN_PASSWORD_LENGTH) return "tooShort";
  if (next.trim().toLowerCase() === username.trim().toLowerCase()) return "isUsername";
  if (current !== undefined && next === current) return "sameAsCurrent";
  if (confirm !== undefined && next !== confirm) return "mismatch";
  return null;
}
