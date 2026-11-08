/** Suggested username from a full name: "Sunita Devi" -> "sunita.devi".
 * Only letters and digits survive; matches the server's username rule. */
export function suggestUsername(fullName: string): string {
  return fullName
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .join(".")
    .slice(0, 50);
}
