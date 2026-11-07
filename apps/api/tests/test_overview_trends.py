"""Insights trends: weekly counts by local week, facility-scoped, counts-only audit."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routers.care import _local_tz, _today
from app.api.routers.overview import bucket_by_week, week_starts
from app.main import app
from app.models.audit import AuditEvent
from app.models.care import Appointment, AppointmentStatus, CareTask, TaskKind, TaskOutcome, TaskStatus
from app.models.identity import ContactMethod, ContactType, Person
from app.models.pregnancy import PregnancyEpisode
from app.models.staff import StaffRole
from tests.conftest import CSRF_HEADERS
from tests.factories import make_facility, make_membership, make_org, make_staff

PASSWORD = "synthetic-password-123"
URL = "/api/v1/overview/trends"


# --- Pure week maths ---------------------------------------------------------


def test_week_starts_are_mondays_ending_this_week():
    starts = week_starts(date(2026, 11, 7), 3)  # a Saturday
    assert starts == [date(2026, 10, 19), date(2026, 10, 26), date(2026, 11, 2)]
    assert all(d.weekday() == 0 for d in starts)


def test_bucket_by_week_ignores_days_outside_the_range():
    starts = week_starts(date(2026, 11, 7), 2)  # Oct 26, Nov 2
    days = [date(2026, 10, 25), date(2026, 10, 26), date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 8), date(2026, 11, 9)]
    assert bucket_by_week(days, starts) == [2, 2]


# --- Through the API ---------------------------------------------------------


def _client(username: str) -> TestClient:
    c = TestClient(app)
    c.__enter__()
    r = c.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD}, headers=CSRF_HEADERS)
    assert r.status_code == 200
    return c


def _local_noon(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, tzinfo=_local_tz())


@pytest.fixture
def w(db_session):
    org = make_org(db_session)
    fa, fb = make_facility(db_session, org, "Facility A"), make_facility(db_session, org, "Facility B")
    coord, other = make_staff(db_session, "t_coord"), make_staff(db_session, "t_other")
    doc = make_staff(db_session, "t_doc")
    make_membership(db_session, coord, fa, StaffRole.COORDINATOR)
    make_membership(db_session, doc, fa, StaffRole.DOCTOR)
    make_membership(db_session, other, fb, StaffRole.COORDINATOR)
    today = _today()
    this_monday = today - timedelta(days=today.weekday())

    episodes = []
    # Two registered this week, one three weeks ago, one long before the window.
    for i, created_day in enumerate([this_monday, this_monday, this_monday - timedelta(weeks=3), this_monday - timedelta(weeks=20)]):
        person = Person(full_name=f"Synthetic Trend Mother {i}", registering_facility_id=fa.id, created_by_staff_user_id=coord.id)
        db_session.add(person)
        db_session.flush()
        db_session.add(ContactMethod(person_id=person.id, type=ContactType.PHONE, value=f"+9166666000{i}"))
        ep = PregnancyEpisode(
            mother_person_id=person.id, facility_id=fa.id, created_by_staff_user_id=coord.id, created_at=_local_noon(created_day)
        )
        db_session.add(ep)
        db_session.flush()
        episodes.append(ep)

    def visit(status, *, confirmed=None, requested=None):
        db_session.add(Appointment(episode_id=episodes[0].id, facility_id=fa.id, status=status, confirmed_for=confirmed, requested_for=requested))

    visit(AppointmentStatus.ATTENDED, confirmed=_local_noon(this_monday))
    visit(AppointmentStatus.ATTENDED, requested=this_monday - timedelta(weeks=1))  # no confirmed date: requested date counts
    visit(AppointmentStatus.MISSED, requested=this_monday)
    visit(AppointmentStatus.REQUESTED, requested=this_monday)  # not attended or missed: ignored
    visit(AppointmentStatus.ATTENDED)  # no date at all: never guessed into a week

    now = datetime.now(timezone.utc)

    def done(due, closed):
        db_session.add(
            CareTask(
                episode_id=episodes[0].id, facility_id=fa.id, kind=TaskKind.CONTACT, status=TaskStatus.COMPLETED,
                owner_staff_user_id=coord.id, outcome=TaskOutcome.DONE, closure_reason="DONE_AS_PLANNED", due_at=due, closed_at=closed,
            )
        )

    done(now + timedelta(hours=1), now - timedelta(days=1))  # on time
    done(now - timedelta(days=3), now - timedelta(days=2))  # late
    done(now, now - timedelta(days=60))  # outside the 30-day window
    db_session.commit()

    clients = {n: _client(n) for n in ("t_coord", "t_other", "t_doc")}
    yield {"coord": clients["t_coord"], "other": clients["t_other"], "doc": clients["t_doc"], "today": today, "fa": str(fa.id), "episode": str(episodes[0].id)}
    for cl in clients.values():
        cl.__exit__(None, None, None)


def test_weekly_counts_and_tiles(w):
    r = w["coord"].get(URL)
    assert r.status_code == 200
    body = r.json()
    assert len(body["week_starts"]) == 8
    assert body["registrations"][-1] == 2 and body["registrations"][-4] == 1 and sum(body["registrations"]) == 3
    assert body["visits_attended"][-1] == 1 and body["visits_attended"][-2] == 1 and sum(body["visits_attended"]) == 2
    assert body["visits_missed"][-1] == 1 and sum(body["visits_missed"]) == 1
    assert set(body["referrals_by_status"]) == {"SENT", "CONTACTED", "ATTENDED", "ADVICE_RECEIVED", "FOLLOW_UP_COMPLETED", "CLOSED"}
    tiles = body["tiles"]
    assert tiles["active_pregnancies"] == 4
    assert tiles["reports_awaiting_review"] == 0
    assert (tiles["follow_ups_closed"], tiles["follow_ups_closed_on_time"]) == (2, 1)
    # This Monday's visit counts this month unless the month started mid-week.
    expected_month = 1 if (w["today"] - timedelta(days=w["today"].weekday())).month == w["today"].month else 0
    expected_month += 1 if (w["today"] - timedelta(days=w["today"].weekday() + 7)).month == w["today"].month else 0
    assert tiles["visits_this_month"] == expected_month


def test_other_facility_sees_only_zeros(w):
    body = w["other"].get(URL).json()
    assert sum(body["registrations"]) == sum(body["visits_attended"]) == sum(body["visits_missed"]) == 0
    assert all(v == 0 for v in body["referrals_by_status"].values())
    assert all(v == 0 for v in body["tiles"].values())


def test_audit_holds_no_names(w, db_session):
    w["coord"].get(URL)
    event = db_session.execute(
        select(AuditEvent).where(AuditEvent.action == "overview_trends").order_by(AuditEvent.id.desc())
    ).scalars().first()
    assert event is not None and "Synthetic" not in str(event.metadata_json)


def test_requires_sign_in():
    with TestClient(app) as anon:
        assert anon.get(URL).status_code == 401


def test_referrals_count_by_current_step(w):
    post = lambda c, url, body: c.post(url, json=body, headers=CSRF_HEADERS)  # noqa: E731
    contact = post(w["coord"], "/api/v1/local-contacts", {"facility_id": w["fa"], "service_type": "REFERRAL_HOSPITAL", "name": "Synthetic district hospital", "phone": "+910000000777"}).json()
    r = post(w["doc"], f"/api/v1/pregnancy-episodes/{w['episode']}/referrals", {"destination_contact_id": contact["id"], "urgency": "ROUTINE", "clinician_instruction": "Synthetic instruction"})
    assert r.status_code == 201
    counts = w["coord"].get(URL).json()["referrals_by_status"]
    assert counts["SENT"] == 1 and sum(counts.values()) == 1
