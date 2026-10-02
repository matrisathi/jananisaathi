# MatriSathi — project status

Last updated: 2026-09-30. Full detail and the SG1 closure table:
`docs/delivery/evidence/SG1/report.md`.

## Completed (locally verified, not yet CI-verified or reviewer-accepted — see the evidence report's status model)

Staff sign-in, mother registration (with intake precision for age/DOB and
free-text history/allergies), pregnancy episode creation, an
authorized-existing-person search by phone and/or name, contact
verification, and viewing the persisted record — backend (FastAPI +
PostgreSQL) and a React/Vite web UI, both locally runnable. Find/select/
verify are now real screens (`FindMother.tsx`, `RegisterNewMother.tsx`),
not just API endpoints — browser-verified end to end, including that
selecting an existing mother never duplicates her person record and a
shared phone number never gets merged or auto-selected. 52 automated
tests, including a real multi-threaded concurrency test proving
duplicate-creation is prevented at the database level, not by a
process-local lock.

Also covered: real password-based staff auth (throttled, generic failures,
rotating refresh with reuse detection, live disabled-user checks);
explicit organization-admin authority (never inferred from a facility
role, with an admin API to create facilities/staff and grant/revoke
memberships); facility-scoped authorization everywhere, ownership always
derived server-side; shared-phone isolation (never merged, never
leaked cross-facility even via search); append-only audit logging
enforced at the database role level; CI configuration (not yet run — no
git remote).

## Open decisions

- SG0 decisions D01–D03 (named team lead/tech lead/developer, confirmed
  hours, pilot site/language, repo/merge policy): unrecorded, tracker
  Status still "Open." Not mine to approve.
- D04 (auth/session/runtime versions): concrete proposal written into the
  tracker, already built and tested, Status left "Open" pending tech-lead
  approval.
- Contact **value** editing (changing a phone number): deliberately not
  built — needs a human decision on the identity-transfer risk first.
- WhatsApp/BSP vendor: still not chosen.
- Git hosting/remote: still not configured; steps prepared in the evidence
  report §10 for when it's authorized.

## Known limitations

- No Child, CaregiverLink, CareTask, ApprovedContent or MessagingEvent
  tables (correctly out of SG1 scope).
- No entity `version`/optimistic-concurrency columns — nothing to protect
  yet since no update endpoint exists; needs to land with SG2's first one.
- No role-based capability differences beyond facility membership — all
  four staff roles currently have identical permissions on this slice's
  two actions, since F004's example restrictions (clinical plan approval,
  report review) don't exist as actions yet.
- Admin capabilities (creating facilities/staff, granting memberships) are
  still API-only — not wired into the browser UI. Search/verify now are.
- Contact value editing (changing a phone number) and name search's
  matching (plain `ILIKE`, not fuzzy/phonetic) are known simplifications.
- This is a local demonstration only. No staging/production environment,
  no CI run, no doctor/clinical review, no legal/hosting review.

## Next proposed task

Build the caregiver-delegation flow (`CaregiverLink`), reusing the
facility-membership and audit patterns already in place — but only after
SG1's open human reviews (M003, M008) and SG0 decisions are actually
recorded, per this stage's own instructions not to start SG2 early.
