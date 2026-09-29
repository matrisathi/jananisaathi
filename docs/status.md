# MatriSathi — project status

Last updated: 2026-09-28.

## Completed

First implementation slice: staff sign-in, synthetic mother registration,
pregnancy episode creation, and viewing the persisted record — backend
(FastAPI + PostgreSQL) and a minimal React/Vite web UI, both locally
runnable. See `README.md` for setup and `docs/specifications/` for the
approved specification and its proposed amendments.

Covered in this slice: real password-based staff authentication (unique
username separate from contact phone, login throttling, generic failure
messages, short-lived access token + rotating refresh token with reuse
detection, disabled-user checks enforced per-request); explicit
organization-admin authority (never inferred from a facility role);
facility-scoped authorization on Person and PregnancyEpisode operations,
with facility ownership always derived server-side; two-organization and
shared-phone isolation; append-only audit logging enforced at the database
role level (the application's DB credential cannot UPDATE or DELETE
`audit_event`); separate migration-owner vs. restricted application DB
roles; 26 automated tests; CI configuration (not yet run — no git remote).

## Open decisions

- Spec `R09`/`G15`: my drafted replacement (`docs/specifications/R09-G15-proposed-amendments.md`)
  is treated as operative for planning; the source workbook itself hasn't
  been updated.
- WhatsApp/BSP vendor: deliberately not chosen — needs a current cost/
  onboarding/inbound-media comparison before any account is created.
- Staff login mechanism: password-based, approved for this slice. OTP-based
  staff login was considered and deferred (would pull in the messaging
  module prematurely).
- Git hosting/remote: not yet configured.

## Known limitations

- No Child, CaregiverLink, CareTask, ApprovedContent or MessagingEvent
  tables yet — modeled in the design doc, deliberately not migrated
  (provisional; see git history for the design discussion).
- No admin UI/API for creating organizations, facilities or staff
  memberships — done via a seed script and directly in test fixtures for
  now.
- No WhatsApp integration, no audio content, no offline support.
- This is a local demonstration only. It does not satisfy any deployed-
  pilot gate — no staging/production environment, no real device testing,
  no doctor/clinical review, no legal/hosting review.

## Next proposed task

Build the caregiver-delegation flow (`CaregiverLink`: grant, staff-verified
guardian authority for a child, and revocation) on top of this slice's
access-control foundation, since it's the next piece the spec's shared-
phone/caregiver requirements (R02) depend on and reuses the same
facility-membership and audit patterns already in place.
