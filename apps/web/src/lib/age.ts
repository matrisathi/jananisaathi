import type { AgePrecision } from "../api/client";

export function formatAge(person: {
  age_precision: AgePrecision;
  date_of_birth: string | null;
  birth_year: number | null;
  reported_age_years: number | null;
}): string {
  switch (person.age_precision) {
    case "EXACT_DOB":
      return person.date_of_birth ? `DOB ${person.date_of_birth}` : "DOB unknown";
    case "YEAR_ONLY":
      return person.birth_year ? `Born ${person.birth_year} (year only)` : "Birth year unknown";
    case "APPROXIMATE_AGE":
      return person.reported_age_years != null
        ? `~${person.reported_age_years} years (approximate)`
        : "Approximate age unknown";
    case "UNKNOWN":
    default:
      return "Age/DOB not recorded";
  }
}
