# SG1 delivery evidence — MatriSathi

Prepared by: Claude (implementer), across three passes: 2026-09-29 (initial
SG1 technical build), 2026-09-30 (closure pass — concurrency fix,
F002–F004/T002–T007 reconciliation, status corrections), and 2026-09-30,
later the same day (browser-workflow completion — §6a). **This report is
evidence for the named human reviewers to act on. It is not a self-declared
gate pass** — see §13.

## 0. Status model

Four distinct things get conflated if not tracked separately. This report
(and the tracker's own Status/Result columns, corrected this pass) now
distinguish them explicitly:

| State | Means |
|---|---|
| **Implemented** | Code exists and does what it's supposed to. |
| **Locally verified** | Automated tests exercise it and pass, on this machine. |
| **CI verified** | The same checks ran in CI, tied to a commit SHA, on infrastructure nobody hand-tuned. |
| **Reviewer accepted** | A named human (tech lead / doctor / team lead) actually looked at it and signed off. |

Everything in this report through SG1 has reached **locally verified**.
Nothing has reached **CI verified** (no remote — §9) or **reviewer
accepted** (M003/M008 review hasn't happened). The tracker's `Tasks` sheet
already has a formula (`Verified done`, column Q) that only reads `1` when
Status=Done **and** Review result=Accepted **and** an evidence link **and**
an actual reviewer are all present — so M004–M006 are set to **Review**
(not Done) this pass, and that formula correctly stays at `0` until a human
actually accepts them.

## 1. Source snapshot identity

- **Baseline commit**: `7f39792` (root commit, branch `main`, no remote).
- **Pass 1 commit**: `0a69382` — SG1 technical build (35 tests, `/api/v1`,
  admin API, first idempotency-key attempt, `updated_at`).
- **Closure-pass snapshot (uncommitted)**: backend fixes (§2–§7), snapshotted
  via `git stash create` for the fresh/empty-DB verification —
  snapshot commit `4734e63a4d2a7fd4bb7f84c7712e2ce98608feb2`.
- **UI-completion-pass snapshot (uncommitted)**: the browser-workflow work
  in §6a, snapshotted the same way — snapshot commit
  `ca31fc1fc904a1d28a5f3b6c3a67d2172865d8ad`. Neither snapshot was
  committed; no commit approval obtained either pass (§10 covers what's
  prepared for when it is).
- `git status --short` at time of writing: schema/router/test/frontend
  changes described in §2–§7 and §6a, all staged, none committed.

## 2. Known defects (recorded even though the suite passes)

Per this pass's instructions: a passing suite doesn't mean no defects.

| # | Defect | Found | Status |
|---|---|---|---|
| D-1 | **Idempotency check-then-insert race.** The pass-1 implementation queried for an existing `IdempotencyKey` row, and only inserted one *after* creating the business entity, in a separate commit. Two genuinely concurrent requests with the same key could both pass the "not found" check and each create their own `Person`/`PregnancyEpisode` — the unique constraint only caught the *second* commit (the idempotency row itself), by which point the duplicate entity already existed. | This pass, by design review (not by observing a failure in production — there was none to observe, since pass 1 never had concurrent traffic) | **Fixed** — §5. Verified with a real multi-threaded concurrent test against Postgres (`test_truly_concurrent_identical_requests_create_exactly_one_person`), not a mock. |
| D-2 | **`create_person`'s authorization failures weren't audited**, unlike the other three endpoints (`get_person`, `create_pregnancy_episode`, `get_pregnancy_episode`), which all log a DENIED audit event on a failed authorization check. | This pass, during the T005/T006 clause-by-clause re-read | **Fixed** — wrapped in the same try/except-and-audit pattern as the others. |
| D-3 | **No `age`/`date_of_birth` precision field existed at all** — F002 and T003 both explicitly require representing "unknown," "year only," and "approximate age" without inventing a day-of-month or defaulting to zero/today, and pass 1 had only a single nullable `date_of_birth`. | This pass, clause-by-clause reconciliation (§7) | **Fixed** — `AgePrecision` enum + three mutually-exclusive fields, enforced by a Pydantic validator (`test_age_precision_rejects_mismatched_fields`). |
| D-4 | **No way to search for or select an existing Person** — F002's "find an authorized record" half was simply missing; only create-new existed. | Pass 1's own report already flagged this as a gap; not fixed until now | **Fixed** — §8. |
| D-5 | **`ContactMethod.verified_at` existed as a column but nothing ever set it** — F003's "confirm which person a contact relates to" had no endpoint. | This pass | **Fixed** — §8. |

## 3. M001–M008 status

| ID | Owner | Status | Notes |
|---|---|---|---|
| M001 | Team lead | Not started | Human decision (D01/D02) — unchanged since pass 1. |
| M002 | Tech lead | Partial | Repo exists locally, 2 commits, no remote, no branch/PR/merge-approver policy (D03). |
| M003 | Tech lead | **Evidence prepared, not yet reviewed** | §9 below is written specifically for this review. |
| M004 | Developer | **Review** (was "Done" in pass 1 — corrected) | Implemented and locally verified; not CI-verified, not reviewer-accepted. Tracker `Tasks` sheet Status corrected to "Review" this pass. |
| M005 | Developer | **Review** (corrected) | Same basis. |
| M006 | Developer | **Review** (corrected) | Browser UI unchanged this pass — pass 1's browser-demo evidence (§6) still applies to it; CI still not run. |
| M007 | Team lead | Not started | Checklist unchanged from pass 1's report. |
| M008 | Doctor | Not started | Checklist unchanged; §7's Person-field additions (medical history, allergies, age precision) are new and specifically need the doctor's eyes before SG2 builds on them. |

## 4. AT01–AT05 results (tracker `Acceptance` sheet corrected to match)

| AT | Result | Evidence |
|---|---|---|
| AT01 | **Pass** | Unchanged from pass 1 (12 tests, `test_auth.py`) — locally verified, not reviewer-accepted. |
| AT02 | **Pass** | Pass 1's tests plus `test_org_admin_authority_alone_grants_no_clinical_record_access` (new, T005 confirmation). |
| AT03 | **Pass** | Pass 1's tests plus the new F002 search-isolation tests (§8). |
| AT04 | **Pass** | Unchanged from pass 1. |
| AT05 | **Blocked** (was marked "Pass" in pass 1 — **corrected**) | AT05's own expected outcome explicitly includes "CI output tied to SHA." Pass 1 marked it Pass on the strength of the fresh-checkout + browser-restart evidence alone, without CI — that was premature. Local/fresh-checkout/browser evidence is real and still stands (§6), but the case as *written* isn't fully satisfiable until CI actually runs (§9), so "Blocked" (on that missing piece) is the honest tracker value, not "Pass." |

`Tasks` and `Acceptance` sheet cells were corrected in place (Status,
Result, Evidence link, Candidate SHA/date columns) — verified after
saving that the sheet's structured table and dropdown data validations
survived the edit intact.

## 5. Idempotency concurrency fix

**Design** (`app/services/idempotency_service.py`): a single
`INSERT ... ON CONFLICT (staff_user_id, endpoint, key) DO NOTHING RETURNING id`
is the entire claim — no process-local lock, no check-then-insert window.
Two concurrent transactions racing on the same key: Postgres blocks the
loser at the row-lock level until the winner's transaction resolves, then
the loser's `ON CONFLICT DO NOTHING` sees the conflict and returns zero
rows. The claim, the business entity's creation, and attaching the
entity's id to the claim row all happen in **one transaction, one commit**
(`db.flush()` to get the new id, `attach_result`, then a single
`db.commit()`) — so a crash between claiming and committing leaves nothing
behind at all (the whole thing rolls back together), not an orphaned
"in-progress" row.

A reused key with a **different** request body is rejected (409) via a
stored `payload_hash` comparison — a retry must resend the same payload; a
mismatch is a client bug, not a legitimate retry.

A **replay** (the loser's path, or a plain sequential retry) re-runs the
same facility-membership authorization check before returning the cached
entity — revoking access between the original request and a retry means
the retry gets denied too, not a stale cached success.

**Verification** (`tests/test_idempotency_concurrency.py`, all passing
against real Postgres, not mocks):
- `test_truly_concurrent_identical_requests_create_exactly_one_person` —
  two real OS threads, two independent `TestClient`s (independent
  connections), synchronized with a `threading.Barrier`, firing the
  identical request at the same instant. Both get `201` with the **same**
  id; a direct SQL count confirms exactly one `Person` row exists.
- `test_sequential_retry_returns_same_record` — the flaky-connection case.
- `test_same_key_different_payload_is_rejected` — `409`.
- `test_identical_key_string_is_isolated_across_staff_users` — two staff
  members using the literal same key string never collide (scoped by
  `staff_user_id`).
- `test_replay_re_enforces_current_authorization` — membership revoked
  between the original request and a same-key retry → retry gets `404`,
  not the cached record.

## 6. F002/F003 additions this pass

**F002 "find an authorized record"** — `GET /people?phone=<value>`
(`app/api/routers/people.py::search_people`), scoped to the caller's
active facility memberships only, capped at 50 results (bounded, not
paginated — an exact-phone match within one coordinator's facilities is
never going to be a large result set; add real pagination if that
assumption ever breaks). A phone match outside the caller's facilities is
simply excluded from the results, not surfaced-then-denied.

Verified (`tests/test_person_search_and_intake.py`):
- results are facility-scoped (a match at another facility never appears);
- a shared phone number returns **multiple distinct Person rows**, never
  merged into one;
- an id obtained by any means (search or otherwise) still cannot be linked
  into a new `PregnancyEpisode` without facility access — reuses the
  existing `require_facility_membership` check, so this can't be bypassed
  by a new code path.

**F003 "confirm which person a contact relates to"** —
`POST /people/{id}/contact/verify`, facility-scoped, records
`verified_at` + `verified_by_staff_user_id` (attribution). Verified for
both the happy path and facility-scoping.

**F002 intake precision** — `Person.age_precision`
(`EXACT_DOB`/`YEAR_ONLY`/`APPROXIMATE_AGE`/`UNKNOWN`) plus three
mutually-exclusive fields (`date_of_birth`, `birth_year`,
`reported_age_years`), enforced by a Pydantic validator so a mismatched
combination (e.g. claiming `EXACT_DOB` while sending a `birth_year`) is
rejected at the API boundary, not silently accepted. Plus
`reported_medical_history` and `known_allergies_medicines` — free-text,
nullable, administrative capture only (no scoring, no interpretation,
matching CLAUDE.md's clinical boundary).

**Frontend** (this section's own pass): none of the above was wired into
the browser UI yet at the time it was written — API-only, consistent with
how the admin API was handled in pass 1. **That gap is closed in §6a**,
written later the same day.

## 6a. Browser workflow completion

Closes the frontend gap the previous section (and pass 1's own report)
left open: search, select-existing, contact verification, and age/DOB
precision are now real, working screens, not just API endpoints.

**Changed files**:
- `apps/api/app/api/routers/people.py` — extended `search_people` to
  accept `full_name` (case-insensitive partial match) alongside `phone`,
  requires at least one; `_to_out` now also resolves and returns
  `contact_verified_by_name` (a join to `StaffUser`, not just the raw
  `verified_by_staff_user_id`).
- `apps/api/app/schemas/person.py` — added `contact_verified_by_name` to
  `PersonOut`.
- `apps/api/tests/test_person_search_and_intake.py` — 3 new tests (below).
- `apps/web/src/api/client.ts` — `searchPeople`, `verifyContact`, full
  `Person`/`PersonCreateInput` types matching the backend schema exactly.
- `apps/web/src/lib/age.ts` — new: `formatAge()`, one place that turns
  `age_precision` + the matching field into display text, shared by both
  screens below so the "unknown" / "year only" / "approximate" / "exact"
  cases render identically everywhere.
- `apps/web/src/pages/FindMother.tsx` — new: the search screen. Phone
  and/or name inputs, results listed as separate cards (name, age display,
  phone, facility, contact-verification status), a "Select & create
  episode" button per result (calls `createPregnancyEpisode` directly —
  never calls `createPerson`), and a "Confirm this is their number" button
  per unverified result.
- `apps/web/src/pages/RegisterNewMother.tsx` — new: the create-new screen
  (the old `MotherRegister.tsx` content), extended with the age-precision
  radio group (four mutually-exclusive options matching the backend
  validator exactly, each with its own stable `id` for testability) and
  the medical-history/allergies text areas.
- `apps/web/src/pages/MotherRegister.tsx` — now a thin tab container:
  "Find existing mother" / "Register new mother", defaulting to Find
  (search-before-create, to actually reduce duplicate registrations rather
  than just prevent them server-side).
- `apps/web/src/pages/PregnancyView.tsx` — now also fetches the mother's
  full `Person` record (not just the episode's denormalized name), and
  displays age/DOB, reported history/allergies, and contact-verification
  status with a "Confirm this is their number" action available from the
  persisted-record view too.
- `apps/web/src/App.tsx` — nav label "New registration" → "Find / register
  mother" (accuracy, not a functional change).

**Targeted test results**: full backend suite **52 passed** (49 from the
closure pass + 3 new: `test_search_by_partial_name_scoped_to_facility`,
`test_search_requires_at_least_one_field`,
`test_verifier_name_is_exposed_after_verification`), `ruff` clean, `mypy`
clean on 32 files. Re-verified from a genuine fresh checkout (empty DB,
pinned lockfiles) — snapshot `ca31fc1fc904a1d28a5f3b6c3a67d2172865d8ad` —
alongside a fresh `npm ci` + `tsc --noEmit` + `vite build`, all clean.

**Browser evidence** (Playwright, the same `chrome-headless-shell` binary
used in pass 1, driving the actual running app — not a mock, not a
component test):

1. Logged in as `coordinator1`, registered "Verify Mother X" via **Register
   new mother** with age precision = Approximate age = 24 — the persisted
   view immediately showed "~24 years (approximate)".
2. Clicked **Confirm this is their number** on her record, then reloaded
   the page: the confirmation ("Confirmed by Synthetic Coordinator on
   ...") was still there — **persists after reload**, not just in local
   React state.
3. Registered "Verify Mother Y (shares phone)" with the *same* phone
   number as Mother X.
4. Switched to **Find existing mother**, searched that phone number:
   **both** mothers appeared as separate result cards — never merged —
   each showing its own name, age, phone, facility, and contact status.
5. Clicked **Select & create episode** on Mother X's card specifically
   (not Y's): the resulting record showed "Verify Mother X" — **the
   correct person**, not whichever was clicked last or first.
6. Checked the database directly afterward: `SELECT full_name, count(*)
   FROM person WHERE full_name LIKE 'Verify Mother%' GROUP BY full_name`
   → **exactly 1 row each** for both X and Y, even though X now has two
   pregnancy episodes (one from registration, one from the "select
   existing" step) — selecting an existing person to open a new episode
   does not duplicate her `Person` record.
7. Logged in as a second, unrelated staff member (`coordinator2`, a
   different facility, no membership in common with Mother X/Y's
   facility): searching the identical shared phone number, and separately
   the name "Verify Mother", both returned **"No matching records
   found"**. Navigating directly to Mother X's episode URL (a known,
   valid id — not a guess) rendered a plain **"Not found"** state with no
   record content anywhere in the page — confirmed by checking the full
   page text, not just the visible UI.
8. Checked the remaining UI states directly: submitting the search form
   with both fields empty shows "Enter a phone number, a name, or both."
   (validation); searching a phone that matches nobody shows "No matching
   records found... register a new mother instead" (empty result).
   Loading states (`Searching...` / `Confirming...` / `Opening...`) are
   implemented via per-action busy flags in `FindMother.tsx`, visible in
   the UI during each in-flight request.

Six screenshots from this run and two from the states check exist in a
scratch directory (synthetic data only, not committed).

**Remaining blockers specific to this section**:
- Contact **value** editing is still not built (§7, proposed deferral,
  unchanged) — the UI has no path to it either, correctly, since the
  capability doesn't exist.
- Name search is a plain `ILIKE '%...%'`, not fuzzy/phonetic matching —
  fine for a pilot's data volume; flagging in case that assumption is
  wrong for how staff actually spell names back.
- This section's evidence, like §8's, is **locally verified only** — not
  CI-verified, not reviewer-accepted. Nothing here changes §9's or §13's
  status.

## 7. F002–F004 / T002–T007 clause-by-clause reconciliation

Every clause, checked against actual code. Unambiguous gaps were fixed
(§2, §5, §6). What's left is genuinely either out of scope for this slice
or needs a human decision — presented here, not silently dropped:

| Clause | Status |
|---|---|
| F002: "capture available intake... history; existing medicines/allergies" | **Fixed** this pass (§6). |
| F002: "available age/DOB with precision" | **Fixed** this pass (§6). |
| F002: "find an authorized record" | **Fixed** — API in §6, browser UI in §6a. |
| F003: "confirm which person a contact relates to" | **Fixed** — API in §6, browser UI in §6a. |
| F003: "record safe preferences" (safe contact time, message detail) | **Correctly deferred to SG3** — this is R01/F016 territory (WhatsApp preferences), not SG1. |
| F003: "Review suspected duplicates manually" | **Satisfied in bounded form**: the new search endpoint *is* the manual-duplicate-review mechanism — a coordinator searching a phone number and seeing two distinct people is the review. A dedicated "flag as duplicate" workflow is a separate, bigger feature — **proposed deferral**, needs a decision on whether SG1 requires more than this. |
| F003: contact **value** editing (a phone number changing) — "change actor/date" | **Proposed deferral, needs human sign-off.** F003's own warning ("never transfer identity on number change") means this needs careful design, not a quick PATCH endpoint. Not built this pass. |
| F004: "Clinician-only actions are reserved for clinical users" | **N/A yet** — no clinician-only actions exist in this slice's surface (report-review, prescriptions are SG2/F009-F010). Nothing to enforce differently between roles until those actions exist. |
| F004/T005: role-based capability scope beyond facility membership | **Proposed deferral** — `StaffRole` is stored and available; all four roles currently have identical permissions on this slice's two actions (register person, create episode) because F004's example restrictions don't apply to actions that don't exist yet. Will need real enforcement once SG2 introduces role-differentiated actions. |
| T002: "entity version on updates" | **Correctly deferred** — no update endpoint exists yet (no PATCH on Person/PregnancyEpisode), so there's nothing to protect with optimistic concurrency. Needs to land with SG2's first update (F005, dating correction) — flagging now so it isn't forgotten then. |
| T003: "Session" (entity name) vs. `RefreshToken` (actual name) | **Cosmetic**, not a functional gap — worth aligning terminology with the tech lead during M003 review. |
| T002: pagination | **Bounded instead** (hard cap, §6) — proposed as sufficient for pilot scale; revisit if wrong. |

Nothing in F002–F004/T002–T007 was silently dropped or left uncovered by a
missing test as an excuse to skip it — every row above is either fixed,
explicitly out-of-scope-until-SG2, or flagged as needing a human decision.

## 8. AT05 in detail — fresh checkout, restart, browser demo

**This section's evidence predates this pass's fixes** (D-1 through D-5,
§2) — it was captured in pass 1, against the code as it stood then. It
remains valid for what it actually tested (fresh checkout mechanics,
browser login/register/create/reload/restart, DB persistence across a real
restart); it does **not** cover the concurrency fix, the search endpoint,
or the intake fields, which are new this pass and covered by §5/§6's test
suites instead (locally verified, same caveat — not CI-verified).

**Re-verified this pass** (§ at top of this report, and directly above):
the *current* migration chain (now 4 revisions, including this pass's
schema changes) still applies cleanly to a genuinely empty database, and
all 49 tests / ruff / mypy still pass from a fresh `git stash create` +
`git archive` checkout — commands identical to pass 1's, snapshot SHA
`4734e63a4d2a7fd4bb7f84c7712e2ce98608feb2`.

Pass 1's original fresh-checkout / browser-demo record (unchanged,
included here for continuity):

```
# Postgres, isolated instance on a different port
cd infra && docker compose -p matrisathi_fresh up -d db

# Backend, fresh venv from the pinned lockfile
cd apps/api && cp .env.example .env && uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_dev
uv run pytest -q && uv run ruff check . && uv run mypy app

# Frontend, fresh node_modules from the pinned lockfile
cd apps/web && npm ci && npm run typecheck && npm run build
```

Browser demonstration output (Playwright, headless Chromium):

```
[demo] logged in
[demo] episode A created, url = http://localhost:5173/#/episodes/c79bcdcf-1d5d-4207-b763-48a4a6c9999c
[demo] after reload, first <dd> = "Playwright Demo Mother A"
[demo] episode B created (shared phone with A), url = http://localhost:5173/#/episodes/1d43bb41-a522-48a9-9a6d-0b2b1e5134c0
[demo] episode A and B distinct urls: true
[demo] episode A still shows: "Playwright Demo Mother A"
[demo] PASS: full browser flow + shared-phone case verified
```

Then, after killing and restarting the API/web processes outright, a
brand-new cookie-less browser context logged in again and confirmed the
same record:

```
[restart-check] after killing and restarting api+web processes, episode shows: "Playwright Demo Mother A"
[restart-check] PASS
```

Five screenshots from that run exist in a scratch directory from that
session (synthetic data only; not committed — not durable artifacts the
codebase needs).

## 9. M003 review evidence

Consolidated for the tech lead's independent review — reusing the tests
above rather than re-describing them:

**Database runtime/default grants and audit protection**
(`alembic/versions/0002_app_role_grants.py`, `79d282bcc5f3`): a dedicated
`matrisathi_app` login role, distinct from the `matrisathi_migrator` role
that owns the schema; `ALTER DEFAULT PRIVILEGES` so any table the migrator
creates in the future is automatically granted to the app role without a
manual per-migration grant; `audit_event` specifically has UPDATE/DELETE
revoked from the app role. Verified with a real permission-denied check
against the live database (`test_app_db_role_cannot_update_or_delete_audit_rows`),
not a code-review assumption.

**Role, facility and record-assignment authorization**: every
read/write/search checks *live* `StaffMembership` state per request
(`app/core/deps.py::require_facility_membership`) — never cached at login.
Organization-admin authority is a separate, explicit grant
(`OrganizationAdmin`), never inferred from any facility role
(`test_org_admin_grant_is_required_not_inferred_from_membership_role`,
`test_org_admin_authority_alone_grants_no_clinical_record_access`). Cross-
facility and cross-organization references return `404`, never `403`, so a
denial never confirms another tenant's record exists.

**Session expiry, refresh reuse, logout, revocation**: access tokens are
short-lived JWTs (15 min) re-validated against the live `StaffUser.active`
flag on every request (not just at token-issue time); refresh tokens are
opaque, hashed at rest, rotated on every use, with reuse of an
already-rotated token treated as a theft signal that revokes every live
session for that user
(`test_refresh_rotates_token_and_old_one_stops_working`); disabling a user
mid-session invalidates access on the very next request
(`test_disabled_user_loses_access_mid_session`); logout revokes the
specific refresh token and requires the CSRF header
(`test_logout_revokes_refresh_token`, `test_logout_requires_csrf_header`).
Login failures are uniform regardless of cause (unknown user, wrong
password, disabled account, or throttled) —
`test_login_throttled_after_repeated_failures` and its neighbors.

**D04 (auth/session/runtime/dependency versions)**: proposed, not yet
approved by the tech lead (tracker `Decisions` sheet still shows Status
"Open" — I did not mark it Accepted). The concrete proposal, already built
and tested: password-based staff login; 15-minute access token + 14-day
rotating refresh with reuse detection; Python 3.12.14 pinned via
`uv.lock`; Node 26.8.1 pinned via `.nvmrc`; every dependency pinned
exactly (`pyproject.toml`/`uv.lock`, `package.json`/`package-lock.json`).
Remaining open question for the tech lead: whether 15 min / 14 days are
the right lifetimes for this user population (rural staff, shared
devices, variable connectivity) versus pass 1's alternative
consideration of longer-lived sessions — I chose the shorter/rotating
design for revocability and flagged the tradeoff in pass 1's report; it
hasn't been revisited.

## 10. Remote/CI steps — prepared, not executed

Per this pass's instructions: no remote created, nothing committed,
pushed, or dispatched. For the authorized human owner (tech lead / team
lead per D03), once approved:

```
# 1. Create the remote (GitHub or wherever D03 decides), then:
git remote add origin <url>

# 2. Commit this pass's changes (review the diff first):
git add -A
git commit -m "<message>"

# 3. Push:
git push -u origin main

# 4. CI (.github/workflows/ci.yml) runs automatically on push, covering:
#    - backend: uv sync --frozen, alembic upgrade head against a service
#      Postgres, ruff, mypy, pytest
#    - frontend: npm ci, typecheck, build
# Link the resulting Actions run URL and commit SHA into this report's
# §4 (Evidence link / Candidate SHA columns in the tracker) once it's run.
```

I have not run any of this. Once it's authorized and the SHA is real, this
section should be replaced with the actual CI run link and result, and
AT05's tracker Result should move from "Blocked" to "Pass" or "Fail"
accordingly — not before.

## 11. Doctor feedback and approval status

**None obtained**, unchanged from pass 1. This pass added clinically-
adjacent fields (`reported_medical_history`, `known_allergies_medicines`,
age precision) that specifically should be in front of the doctor before
SG2 builds on them — added to the M008 checklist (§3, unchanged text from
pass 1's report, still open).

## 12. Closure table

| Finding | Change | Verification | Reviewer | Remaining blocker |
|---|---|---|---|---|
| D-1: idempotency check-then-insert race | Atomic `INSERT ... ON CONFLICT` claim, single-transaction commit with the business entity | `test_idempotency_concurrency.py`, 5 tests incl. a real multi-threaded race | Not yet — tech lead (M003) | Human review |
| D-2: `create_person` denials unaudited | Added try/except + DENIED audit event, matching the other 3 endpoints | Existing audit test pattern, re-run | Not yet | Human review |
| D-3: no age/DOB precision | `AgePrecision` enum + 3 mutually-exclusive fields + validator | `test_age_precision_rejects_mismatched_fields`, `test_unknown_age_precision_stores_no_invented_values` | Not yet | Doctor review (M008) of the new fields |
| D-4: no person search | `GET /people?phone=\|full_name=`, facility-scoped, capped | `test_person_search_and_intake.py`, 7 tests; browser-verified (§6a) | Not yet | Human review |
| D-5: no contact verification | `POST /people/{id}/contact/verify` | Same file; browser-verified incl. persistence-after-reload (§6a) | Not yet | Human review |
| Tracker status inflation (M004–M006 "Done", AT05 "Pass") | Corrected to "Review" / "Blocked" in the actual `.xlsx`, table/validation integrity confirmed after edit | Re-opened and read back with openpyxl | Not yet | Tech lead/team lead acceptance |
| Contact value editing | Not built | — | — | **Needs a human decision** before building (identity-transfer risk) |
| Role-based capability scope | Not built | — | — | Deferred until SG2 introduces role-differentiated actions |
| Entity version/optimistic concurrency | Not built | — | — | Deferred until SG2's first update endpoint (F005) |
| CI never run | Steps prepared (§10) | — | — | No remote; needs D03 + explicit push authorization |
| SG0 decisions D01–D03 | Unchanged, still Open | — | — | Team lead |
| D04 (auth/runtime) | Concrete proposal written into the tracker's Decision/rationale field, Status left Open | Built and tested (§9) | Not yet | Tech lead approval |
| Doctor review (M008) | Checklist prepared, now includes new intake fields | — | — | Doctor |
| Search/select/verify not wired into the browser UI | Built: `FindMother.tsx`, `RegisterNewMother.tsx`, updated `PregnancyView.tsx` (§6a) | 8-step real-browser script incl. shared-phone-not-merged, correct-record-selected, no-duplicate-person (DB-checked), persistence-after-reload, and unauthorized-search/-direct-access denial | Not yet | Human review |

## 13. Recommendation

**Still Conditional. Not declaring SG1 passed.** Locally-verified technical
evidence is now broader and more honest than pass 1's (a real concurrency
bug was found and fixed rather than papered over; the tracker's own status
cells no longer overstate completion; the browser workflow this gate
actually depends on — find, select, verify, register, all with correct
isolation — is now real and demonstrated end to end, not just API-tested).
What's still missing to close SG1 is unchanged in kind: SG0's human
decisions (D01–D03), M003's independent tech-lead review (this report is
written for exactly that), M008's doctor review (now covering more surface
than before, including the new intake fields), and an actual CI run once a
remote exists and is authorized. None of these are things I can do on the
team's behalf.
