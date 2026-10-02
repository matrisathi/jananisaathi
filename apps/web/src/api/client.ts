// Set VITE_API_BASE in Vercel's project env vars for a deployed frontend —
// this must point at wherever the backend actually runs (it is never
// Vercel itself; see README "Deploying a staging environment").
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

// The auth session rides on httpOnly cookies (set by the API), never in
// localStorage or a JS-readable cookie — this frontend never touches the
// token value directly, it just needs `credentials: "include"` so the
// browser sends/receives those cookies on same-site cross-port requests.
const CSRF_HEADER_NAME = "X-MatriSathi-Client";
const CSRF_HEADER_VALUE = "web";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const isMutating = method !== "GET";

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(isMutating ? { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE } : {}),
      ...(options.headers ?? {}),
    },
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, body.detail ?? `Request failed (${res.status})`);
  }
  return body as T;
}

export interface Membership {
  facility_id: string;
  facility_name: string;
  role: string;
}

export interface Staff {
  id: string;
  username: string;
  full_name: string;
  memberships: Membership[];
}

export type AgePrecision = "EXACT_DOB" | "YEAR_ONLY" | "APPROXIMATE_AGE" | "UNKNOWN";

export interface Person {
  id: string;
  full_name: string;
  age_precision: AgePrecision;
  date_of_birth: string | null;
  birth_year: number | null;
  reported_age_years: number | null;
  preferred_language: string | null;
  reported_medical_history: string | null;
  known_allergies_medicines: string | null;
  registering_facility_id: string;
  phone: string;
  contact_verified_at: string | null;
  contact_verified_by_name: string | null;
}

export interface PregnancyEpisode {
  id: string;
  mother_person_id: string;
  mother_full_name: string;
  facility_id: string;
  dating_estimate: string | null;
  dating_source: string;
  status: string;
  created_at: string;
}

export interface PersonCreateInput {
  full_name: string;
  facility_id: string;
  phone: string;
  age_precision?: AgePrecision;
  date_of_birth?: string | null;
  birth_year?: number | null;
  reported_age_years?: number | null;
  preferred_language?: string | null;
  reported_medical_history?: string | null;
  known_allergies_medicines?: string | null;
}

export const api = {
  login: (username: string, password: string) =>
    request<Staff>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<Staff>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  createPerson: (input: PersonCreateInput) =>
    request<Person>("/people", { method: "POST", body: JSON.stringify(input) }),
  getPerson: (id: string) => request<Person>(`/people/${id}`),
  searchPeople: (params: { phone?: string; full_name?: string }) => {
    const q = new URLSearchParams();
    if (params.phone) q.set("phone", params.phone);
    if (params.full_name) q.set("full_name", params.full_name);
    return request<Person[]>(`/people?${q.toString()}`);
  },
  verifyContact: (personId: string) =>
    request<Person>(`/people/${personId}/contact/verify`, { method: "POST" }),
  createPregnancyEpisode: (personId: string) =>
    request<PregnancyEpisode>("/pregnancy-episodes", {
      method: "POST",
      body: JSON.stringify({ person_id: personId }),
    }),
  getPregnancyEpisode: (id: string) => request<PregnancyEpisode>(`/pregnancy-episodes/${id}`),
};
