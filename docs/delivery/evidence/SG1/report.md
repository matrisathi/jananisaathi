# SG1 delivery evidence — MatriSathi

Prepared by: Claude (acting as implementer/tech-reviewer for this pass), 2026-09-29.
This report is evidence for the named human reviewers to act on. **It is not a
self-declared gate pass.** Per the working instructions for this stage, SG1 is
not declared Passed here — see Recommendation at the end.

## 1. Baseline commit and uncommitted changes

- **Baseline commit**: `7f39792` — "Add MatriSathi foundation: independent
  auth, org/facility isolation, first pregnancy-episode slice" (root commit,
  branch `main`, no remote configured).
- **Uncommitted changes since baseline** (staged, not committed — no fresh
  commit approval obtained this pass): 19 files, +629/−69 lines. Summary:
  - Mounted all API routes under `/api/v1` (T002).
  - Added `app/api/routers/admin.py` — organization-admin endpoints to
    create facilities, create staff accounts, and grant/revoke
    `StaffMembership` through the application itself (F004 — previously
    only exercised via direct DB test fixtures).
  - Added `Idempotency-Key` support on `POST /people` and
    `POST /pregnancy-episodes` (T002 "operation IDs for retryable
    creates"; `app/models/idempotency.py`,
    `app/services/idempotency_service.py`).
  - Added `updated_at` to every table (`app/models/base.py`); migration
    `79d282bcc5f3` backfills existing rows via a temporary server default,
    then drops it, and grants the restricted app DB role rights on the new
    table plus `ALTER DEFAULT PRIVILEGES` for any future table.
  - Fixed a real bug the `/api/v1` prefix change exposed: the refresh-token
    cookie's `path` still pointed at `/auth`, so it was never sent to the
    now-`/api/v1/auth/refresh` endpoint — a fresh, full test run caught
    this immediately (`test_refresh_rotates_token_and_old_one_stops_working`
    failed, then passed after the fix).
  - Added `docs/specifications/MatriSathi_Stage_Gate_Task_Tracker_with_FS_and_TS.xlsx`
    (supplied this pass) and 9 new tests.
  - Updated `apps/web/src/api/client.ts` for the new `/api/v1` base path.

## 2. M001–M008 status, owners, outstanding human actions

| ID | Owner | Status | Notes |
|---|---|---|---|
| M001 | Team lead | **Not started** | Human decision (D01/D02) — no recorded names, hours, or pilot site/language. |
| M002 | Tech lead | **Partial** | Repository now exists locally (`git init`, one commit). No remote, no branch/PR/merge-approver policy recorded (D03). |
| M003 | Tech lead | **Ready for review, not yet reviewed** | Identity/auth/tenant/audit design is built and passing (see §4). Needs the tech lead's independent review — I designed and built it, so my own review of it doesn't satisfy this. |
| M004 | Developer | **Done** | Verified via a genuine fresh checkout this pass (§5). |
| M005 | Developer | **Done** | Login + scoped identity/pregnancy endpoints; AT01–AT04 pass. |
| M006 | Developer | **Done** | Browser UI built (login/register/create/view); CI config written, not yet run (no remote — see §6). |
| M007 | Team lead | **Not started — checklist prepared below, not approved by me** | |
| M008 | Doctor | **Not started — checklist prepared below, not approved by me** | |

### M007 checklist (team lead: language, clinical-content, messaging-onboarding)
- [ ] Name the pilot language (English + which local language?)
- [ ] Name the two pilot settings (one rural, one semi-urban facility)
- [ ] Name a pediatric reviewer, distinct from the maternal/gynecologist reviewer (D02)
- [ ] Confirm D01's proposed capacity baseline (10h lead / 10h tech / 25h developer / 2h doctor / 0→4h tester) or supply real numbers
- [ ] Decide repository hosting + branch/PR/merge-approver policy (D03) — CI cannot run until this exists
- [ ] (Not SG1-blocking, but worth starting early) Begin the WhatsApp BSP provider comparison for D06

### M008 checklist (doctor: intake, role-boundary, journey-review)
- [ ] Review the intake fields built this slice — `full_name`, `date_of_birth` (nullable), `preferred_language`, contact phone — confirm nothing clinically necessary is missing for first-contact registration (Stage 1)
- [ ] Confirm the built role set (ASHA / NURSE / COORDINATOR / DOCTOR facility memberships, with organization-admin as a separate, explicit grant) matches intended role boundaries
- [ ] Confirm this slice correctly has **no** clinical fields, scoring, or interpretation yet (by design — deferred to SG2 per F005–F015)
- [ ] Flag anything in F002–F004 that needs correction before SG2 begins

## 3. Implemented F/T spec coverage

- **F002** (People and pregnancy registration): implemented and tested. One gap against the spec text: "find an authorized record" (searching for an existing person) is not built — only create-new is; no AT case in AT01–AT05 exercises search, so this doesn't block SG1, but flagging it for SG2 (F002 is also linked to AT06 at SG2).
- **F003** (Shared phones): implemented — `ContactMethod.value` has no uniqueness constraint, verified via `test_shared_phone.py`. Preference/duplicate-review workflow (the messaging-facing part of F003) is correctly deferred to SG3.
- **F004** (Staff roles and assigned records): implemented, including the admin API gap closed this pass.
- **T001–T007**: all implemented. T002's `/api/v1` versioning and idempotency-key requirement, and T003's `updated_at` requirement, were gaps I found and closed this pass (§1). T004–T006 (auth, authorization, audit) were already built in the prior pass and re-verified. T007 (reproducible setup + CI config) — CI *config* exists; CI *execution* is blocked on M002/D03 (no remote).

## 4. AT01–AT05: exact commands and results

All commands run from `apps/api` with `.venv` active unless noted. Database:
local Postgres via `infra/docker-compose.yml`, migrator/app-role separation
per `alembic/versions/0002_app_role_grants.py`.

```
uv sync
alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run mypy app
```

**Result: 35 passed, 0 failed. `ruff check .`: all checks passed. `mypy app`: no issues in 32 source files.**

| AT | Scenario | Result | Evidence (tests) |
|---|---|---|---|
| **AT01** | Staff login and sessions: valid/invalid/expired, refresh, logout, replay, disable | **Pass** | `test_login_success_sets_cookies`, `test_no_session_is_rejected`, `test_malformed_access_token_is_rejected`, `test_access_token_signed_with_wrong_secret_is_rejected`, `test_login_wrong_password_is_generic`, `test_login_unknown_username_is_same_generic_error`, `test_disabled_user_cannot_login`, `test_login_throttled_after_repeated_failures`, `test_disabled_user_loses_access_mid_session`, `test_logout_requires_csrf_header`, `test_logout_revokes_refresh_token`, `test_refresh_rotates_token_and_old_one_stops_working` (12 tests, `test_auth.py`) |
| **AT02** | Organization/facility isolation; org admin cannot cross organizations; revoked membership loses access on the same token | **Pass** | `test_staff_at_facility_b_cannot_read_facility_a_episode`, `test_revoked_membership_loses_access_immediately`, `test_disabled_facility_blocks_new_person_registration`, `test_two_organizations_are_isolated` (`test_access_isolation.py`); `test_org_admin_grant_is_required_not_inferred_from_membership_role`, `test_org_admin_of_org_a_cannot_administer_org_b`, `test_revoked_org_admin_grant_loses_authority` (`test_org_admin.py`); all 4 of `test_admin_membership.py` |
| **AT03** | Shared phone stays distinct; inaccessible-Person reference into a new episode is denied | **Pass** | `test_two_people_can_share_a_phone_without_being_merged`, `test_shared_phone_does_not_leak_across_organizations` (`test_shared_phone.py`); `test_episode_creation_rejected_for_inaccessible_person`, `test_episode_creation_rejected_for_nonexistent_person` (`test_person_pregnancy_authz.py`) |
| **AT04** | Successful/denied audit persistence; runtime DB role cannot UPDATE/DELETE audit history | **Pass** | `test_create_and_read_each_produce_one_audit_row`, `test_denied_access_writes_a_denied_audit_row`, `test_audit_row_survives_rollback_of_the_caller_session`, `test_app_db_role_cannot_update_or_delete_audit_rows` (`test_audit.py`) — the last one is a real `psql`/SQLAlchemy-level permission-denied check, not a mocked assertion |
| **AT05** | Fresh checkout; locked install; migrations; real browser login/create/read; reload and restart | **Pass** | See §5 below |

## 5. AT05 in detail — fresh checkout and persistence

To genuinely test "fresh checkout" without a new commit (not separately
authorized this pass), I used `git stash create` (a snapshot of the exact
staged working tree, respecting `.gitignore` exactly as a real commit
would) and `git archive` to extract it into `/tmp/matrisathi_fresh_checkout`
— a directory with **no** `.git`, `.venv`, `node_modules`, or `.env`.

```
# Postgres, isolated instance on a different port
cd infra && docker compose -p matrisathi_fresh up -d db   # (5433 -> 5434 to avoid the dev instance)

# Backend, fresh venv from the pinned lockfile
cd apps/api && cp .env.example .env && uv sync
uv run alembic upgrade head      # empty DB -> full schema, in one run
uv run python -m app.scripts.seed_dev
uv run pytest -q && uv run ruff check . && uv run mypy app

# Frontend, fresh node_modules from the pinned lockfile
cd apps/web && npm ci && npm run typecheck && npm run build
```

**All of the above passed identically to the working-tree run** (35 tests,
clean lint/typecheck, clean frontend build) — proving the pinned
dependencies and documented commands are sufficient from nothing.

**Persistence across a real restart** (not simulated): earlier in this
session, the local Postgres container from the *previous* session's work
(synthetic `coordinator1` staff user, two `Person` rows sharing one phone
number, one `PregnancyEpisode`) was stopped when the machine went through a
restart between sessions. I brought Docker back up, `docker compose up -d
db`, and queried the same rows back out with `psql` — all three were
intact, unchanged, with no migration or reseed needed. That's a real
restart, not a mocked one.

**Real browser demonstration**: a Playwright-scripted headless-Chromium run
against the fresh checkout, done. Output:

```
[demo] logged in
[demo] episode A created, url = http://localhost:5173/#/episodes/c79bcdcf-1d5d-4207-b763-48a4a6c9999c
[demo] after reload, first <dd> = "Playwright Demo Mother A"
[demo] episode B created (shared phone with A), url = http://localhost:5173/#/episodes/1d43bb41-a522-48a9-9a6d-0b2b1e5134c0
[demo] episode A and B distinct urls: true
[demo] episode A still shows: "Playwright Demo Mother A"
[demo] PASS: full browser flow + shared-phone case verified
```

Then, separately, I killed the fresh checkout's `uvicorn` and `vite`
processes outright (not just closing the browser tab) and started both
back up from nothing, then opened episode A's URL in a **brand-new browser
context with no cookies**, logged in again, and navigated straight to it:

```
[restart-check] after killing and restarting api+web processes, episode shows: "Playwright Demo Mother A"
[restart-check] PASS
```

That's a real process restart, not a page reload within a still-running
server. Five screenshots from the run (login, episode A created, after
reload, episode B with the shared phone, episode A still intact, and the
post-restart view) were captured to a scratch directory during this
session; they're evidence of this run, not committed to the repository
(synthetic data only, and not durable artifacts the codebase needs).

Getting here took two failed Chromium downloads in this sandbox (a ~140 MB
fetch that silently produced a corrupt install both times despite
reporting 100%/exit-0) before I found and reused an already-present,
verified-working `chrome-headless-shell` binary on this machine instead of
downloading a third time.

## 6. CI evidence

**Blocked, as expected**: `.github/workflows/ci.yml` exists and mirrors the
commands in §4/§5 exactly, but there is no git remote (M002/D03 open), so
no CI run has ever executed. This is a named blocker, not a silent gap.

## 7. Schema, authorization and audit review findings (self-review — needs independent tech-lead sign-off per M003)

- **Schema**: matches T003's required first-slice entities (Organization,
  Facility, StaffUser, Membership, Person, ContactMethod, PregnancyEpisode)
  plus RefreshToken (T003 calls this "Session" — same role, different
  name; worth aligning terminology with the tech lead). `updated_at` added
  this pass; optimistic-concurrency `version` columns are **not** built —
  no endpoint currently updates a clinical record (PregnancyEpisode has no
  PATCH yet), so there's nothing to protect a lost-update race on yet, but
  this should be built before SG2's dating-correction work (F005) adds the
  first real update path.
- **Authorization**: every read/write path checks live `StaffMembership`
  state per-request (never cached at login); organization-admin authority
  is a distinct grant, never inferred from a facility role; cross-facility
  and cross-organization references return 404 (never 403) to avoid
  confirming another tenant's record exists.
- **Audit**: append-only is enforced at the database-role level (verified
  by an actual `UPDATE`/`DELETE` permission-denied test, not a code-review
  assumption); denied-access events are written on a separate
  session/transaction so they survive the caller's own rollback; no
  clinical content, passwords, or tokens appear in audit metadata (every
  `metadata_json` value in the test suite is inspected for this).
- **Known gap**: idempotency-key storage has no row-level locking — two
  truly concurrent retries with the same key could both pass the "not
  found" check before either commits. Sequential retries (the realistic
  flaky-connection case) are handled correctly; true concurrent duplicate
  submission is not. Worth a follow-up if load testing (SG6, AT26) surfaces
  it.

## 8. Doctor feedback and approval status

**None obtained.** M008 has not been run. This slice has no clinical
content or fields, so there is nothing clinically substantive for the
doctor to have reviewed yet — but the role-boundary and intake-field
confirmation in the M008 checklist above still needs their sign-off before
SG2 begins.

## 9. Open defects, limitations, decisions required

- **Defects**: none currently open in the automated suite (35/35 passing).
- **Limitations**: no Child/CaregiverLink/CareTask/content/messaging tables
  (correctly out of SG1 scope); no admin UI (API only); idempotency-key
  concurrency gap (§7); F002's "find an authorized record" search isn't
  built (SG2-relevant, not SG1-blocking).
- **Decisions required before SG0/SG1 can be formally closed**: D01, D02,
  D03 (all "Open" in the tracker, no recorded approval) and D04 (I
  recommend the tech lead formally adopt what's already built and tested —
  see the SG0 readiness summary in my chat response for the concrete,
  already-implemented answer).

## 10. Recommendation

**Conditional.** The SG1 *technical* scope (M004–M006, F002–F004, T001–T007,
AT01–AT05) is built and passing, including a genuine fresh-checkout proof
and real restart-persistence evidence. It is not a Pass because: (a) SG0's
own human decisions (D01–D03) remain unrecorded — no named team lead, tech
lead, developer, or pediatric reviewer, no confirmed hours, no pilot
site/language; (b) M003's independent tech-lead review of this design
hasn't happened — I designed and built it, so my own assessment above isn't
a substitute; (c) M008's doctor review hasn't happened; (d) CI has never
actually run (no remote). None of these are technical defects — they're the
named human steps this stage was always going to need. I am not declaring
SG1 passed; this is the evidence for the team lead, tech lead, and doctor to
make that call.
