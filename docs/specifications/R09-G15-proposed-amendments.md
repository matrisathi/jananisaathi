# Proposed amendments to R09 and G15 — withdrawal of external-platform reuse

**Status: proposed only.** The source workbook
(`MatriSathi_Specifications_Updated.xlsx`) has **not** been changed. This
document is a drafted replacement for two cells, pending the workbook owner
updating the actual spec. Until then, treat this file — not the original
R09/G15 wording — as the operative requirement for planning and build work.

## Why

The original R09/G15 assumed MatriSathi would reuse an existing external
platform's web/backend, identity, records and uploads, proven by a "Day 5"
suitability check. That assumption has been withdrawn: MatriSathi is a fully
independent product with no dependency on, or planned merge into, any other
system. This replaces the *reuse* requirement with a *prove-your-own-stack*
requirement, keeping the same delivery discipline (an early, real, deployed
proof; one coherent application path; a documented fallback if the proof
fails).

## R09 (proposed replacement) — MVP technology and delivery proof

| Column | Proposed text |
|---|---|
| Mother & Family App | Responsive patient views plus WhatsApp and assisted use. Where video is offered, a failed call has a phone/in-person fallback. No native mobile app is required for MVP. |
| Care Coordination Logic | Build MatriSathi's own web/backend, identity, records and uploads as an independently runnable, testable and deployable application. Prove the chosen stack end-to-end — a real persisted record, real authentication, real facility scoping, deployed to a staging environment — by Day 5. One maintained application path: no parallel or competing frameworks within MatriSathi itself. REST plus token refresh is sufficient; no premature WebSocket or native-mobile stack. |
| Field Worker / Operations | Tech lead records the Day-5 proof outcome and any stack decisions. Test one persisted pregnancy record and facility-scoped access in staging in Week 1. If the proof fails or surfaces major risk, revise scope, capacity or date before promising delivery. |
| Doctor / Clinical Review | All essential workflows work with AI disabled. Defer generative FAQ/transcription agents, automated calling, growth-chart interpretation, GPS/ambulance APIs and government sync. |

## G15 (proposed replacement)

| Field | Proposed text |
|---|---|
| Finding | Risk of building multiple, inconsistent technology stacks within MatriSathi itself. |
| Updated Specification Cells | R09 |
| Resolution in This Workbook | MatriSathi proves its own stack (React/Vite/TypeScript, FastAPI, PostgreSQL) end-to-end and deploys it independently by Day 5, before further build-out. One maintained application path within MatriSathi. |
| Verification / Evidence Required | Week 1 persisted-record slice running in staging, plus a written stack-decision record; P23 regression. |
| Accountable Reviewer | Tech lead |

## Unaffected

Everything else in the workbook — the 8 clinical stages, R01–R08, R10–R12,
and the "Care Coordination Logic" column header itself (generic terminology
for MatriSathi's own task/appointment/referral tracking, not an external
platform) — is unrelated to this withdrawal and needs no change.
