const API_BASE = "http://localhost:8000";

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

export interface Person {
  id: string;
  full_name: string;
  date_of_birth: string | null;
  preferred_language: string | null;
  registering_facility_id: string;
  phone: string;
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

export const api = {
  login: (username: string, password: string) =>
    request<Staff>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<Staff>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  createPerson: (input: {
    full_name: string;
    facility_id: string;
    phone: string;
    date_of_birth?: string | null;
    preferred_language?: string | null;
  }) => request<Person>("/people", { method: "POST", body: JSON.stringify(input) }),
  getPerson: (id: string) => request<Person>(`/people/${id}`),
  createPregnancyEpisode: (personId: string) =>
    request<PregnancyEpisode>("/pregnancy-episodes", {
      method: "POST",
      body: JSON.stringify({ person_id: personId }),
    }),
  getPregnancyEpisode: (id: string) => request<PregnancyEpisode>(`/pregnancy-episodes/${id}`),
};
