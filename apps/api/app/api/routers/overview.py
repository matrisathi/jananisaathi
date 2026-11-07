"""Overview summary: which active pregnancy records need attention, across the
caller's facilities. Feeds the role-specific panels on the staff home page.

Counts are administrative (what is waiting for whom), never clinical risk:
nothing here interprets a result, a value or a date. Each bucket counts
distinct ACTIVE pregnancy records and lists a few of them, oldest first,
so a panel can link straight to the record.
"""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, exists, func, select
from sqlalchemy.orm import Session

from app.api.routers.care import _caller_facility_ids, _local_tz, _now, _today
from app.core.db import get_db
from app.core.deps import get_current_staff
from app.models.audit import AuditOutcome
from app.models.care import (
    Appointment,
    AppointmentStatus,
    CarePlan,
    CarePlanStatus,
    CareTask,
    Investigation,
    InvestigationStatus,
    TaskStatus,
)
from app.models.identity import ContactMethod, Person
from app.models.pregnancy import DatingSource, PregnancyEpisode, PregnancyEpisodeStatus
from app.models.records import InstructionStatus, Prescription, Referral, ReferralStatus
from app.models.staff import StaffUser
from app.services import audit_service

router = APIRouter(prefix="/overview", tags=["overview"])

RECORDS_PER_BUCKET = 5

# Referral steps after which nothing is waiting on staff.
_REFERRAL_DONE = (ReferralStatus.FOLLOW_UP_COMPLETED, ReferralStatus.CLOSED)


class RecordRef(BaseModel):
    episode_id: str
    mother_full_name: str


class Bucket(BaseModel):
    count: int
    records: list[RecordRef]


class OverviewSummary(BaseModel):
    reports_to_review: Bucket
    prescriptions_to_review: Bucket
    dating_not_confirmed: Bucket
    no_care_plan: Bucket
    contact_not_confirmed: Bucket
    referrals_in_progress: Bucket


def _conditions() -> dict[str, ColumnElement[bool]]:
    episode = PregnancyEpisode.id
    return {
        # A report has arrived and no clinician has reviewed it yet (AT08).
        "reports_to_review": exists().where(
            Investigation.episode_id == episode, Investigation.status == InvestigationStatus.RECEIVED
        ),
        # A prescription document is recorded but its instruction is not yet transcribed.
        "prescriptions_to_review": exists().where(
            Prescription.episode_id == episode, Prescription.instruction_status == InstructionStatus.UNREVIEWED
        ),
        # Unknown or provisional dating; a clinician has not confirmed it.
        "dating_not_confirmed": PregnancyEpisode.dating_source != DatingSource.CLINICIAN_CONFIRMED,
        "no_care_plan": ~exists().where(CarePlan.episode_id == episode, CarePlan.status == CarePlanStatus.ACTIVE),
        # No contact number for the mother has been confirmed with the family.
        "contact_not_confirmed": ~exists().where(
            ContactMethod.person_id == PregnancyEpisode.mother_person_id, ContactMethod.verified_at.is_not(None)
        ),
        "referrals_in_progress": exists().where(
            and_(Referral.episode_id == episode, Referral.status.not_in(_REFERRAL_DONE))
        ),
    }


@router.get("/summary", response_model=OverviewSummary)
def overview_summary(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)) -> OverviewSummary:
    facility_ids = _caller_facility_ids(db, staff)
    base = (
        select(PregnancyEpisode.id, Person.full_name)
        .join(Person, Person.id == PregnancyEpisode.mother_person_id)
        .where(PregnancyEpisode.facility_id.in_(facility_ids), PregnancyEpisode.status == PregnancyEpisodeStatus.ACTIVE)
    )
    buckets: dict[str, Bucket] = {}
    for name, condition in _conditions().items():
        query = base.where(condition)
        count = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = db.execute(query.order_by(PregnancyEpisode.created_at, PregnancyEpisode.id).limit(RECORDS_PER_BUCKET)).all()
        buckets[name] = Bucket(count=count, records=[RecordRef(episode_id=str(r[0]), mother_full_name=r[1]) for r in rows])
    # Counts only in the audit metadata: no names.
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="overview_summary",
        entity_type="Facility",
        entity_id=None,
        outcome=AuditOutcome.SUCCESS,
        metadata={k: b.count for k, b in buckets.items()},
    )
    return OverviewSummary(**buckets)


# --- Trends for the Insights page -------------------------------------------

TREND_WEEKS = 8
ON_TIME_WINDOW_DAYS = 30


def week_starts(today: date, weeks: int = TREND_WEEKS) -> list[date]:
    """Mondays of the last `weeks` weeks, oldest first, ending with this week."""
    this_monday = today - timedelta(days=today.weekday())
    return [this_monday - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]


def bucket_by_week(days: Iterable[date], starts: list[date]) -> list[int]:
    """Counts of `days` per week in `starts`; days outside the range are ignored."""
    counts = [0] * len(starts)
    end = starts[-1] + timedelta(days=7)
    for d in days:
        if starts[0] <= d < end:
            counts[(d - starts[0]).days // 7] += 1
    return counts


class TrendTiles(BaseModel):
    active_pregnancies: int
    visits_this_month: int
    reports_awaiting_review: int
    follow_ups_closed: int
    follow_ups_closed_on_time: int


class Trends(BaseModel):
    week_starts: list[date]
    registrations: list[int]
    visits_attended: list[int]
    visits_missed: list[int]
    referrals_by_status: dict[str, int]
    tiles: TrendTiles


@router.get("/trends", response_model=Trends)
def overview_trends(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)) -> Trends:
    """Administrative counts over time for the caller's facilities. No clinical
    values are read; a visit counts by its confirmed (else requested) date."""
    facility_ids = _caller_facility_ids(db, staff)
    tz = _local_tz()
    today = _today()
    starts = week_starts(today)
    window_start = datetime.combine(starts[0], time.min, tzinfo=tz)

    created = db.execute(
        select(PregnancyEpisode.created_at).where(
            PregnancyEpisode.facility_id.in_(facility_ids), PregnancyEpisode.created_at >= window_start
        )
    ).scalars()
    registrations = bucket_by_week((c.astimezone(tz).date() for c in created), starts)

    visits = db.execute(
        select(Appointment.status, Appointment.confirmed_for, Appointment.requested_for).where(
            Appointment.facility_id.in_(facility_ids),
            Appointment.status.in_((AppointmentStatus.ATTENDED, AppointmentStatus.MISSED)),
        )
    ).all()

    def visit_day(confirmed: datetime | None, requested: date | None) -> date | None:
        return confirmed.astimezone(tz).date() if confirmed else requested

    attended_days = [d for s, c, r in visits if s == AppointmentStatus.ATTENDED and (d := visit_day(c, r))]
    missed_days = [d for s, c, r in visits if s == AppointmentStatus.MISSED and (d := visit_day(c, r))]

    active = PregnancyEpisode.status == PregnancyEpisodeStatus.ACTIVE
    referral_rows = db.execute(
        select(Referral.status, func.count())
        .join(PregnancyEpisode, PregnancyEpisode.id == Referral.episode_id)
        .where(Referral.facility_id.in_(facility_ids), active)
        .group_by(Referral.status)
    ).all()
    referrals_by_status = {s.value: 0 for s in ReferralStatus}
    referrals_by_status.update({s.value: n for s, n in referral_rows})

    active_pregnancies = db.scalar(
        select(func.count()).select_from(PregnancyEpisode).where(PregnancyEpisode.facility_id.in_(facility_ids), active)
    ) or 0
    reports = db.scalar(
        select(func.count())
        .select_from(Investigation)
        .join(PregnancyEpisode, PregnancyEpisode.id == Investigation.episode_id)
        .where(Investigation.facility_id.in_(facility_ids), Investigation.status == InvestigationStatus.RECEIVED, active)
    ) or 0
    # Completed follow-ups with a due time, closed in the last 30 days.
    closed = db.execute(
        select(CareTask.closed_at, CareTask.due_at).where(
            CareTask.facility_id.in_(facility_ids),
            CareTask.status == TaskStatus.COMPLETED,
            CareTask.due_at.is_not(None),
            CareTask.closed_at >= _now() - timedelta(days=ON_TIME_WINDOW_DAYS),
        )
    ).all()

    tiles = TrendTiles(
        active_pregnancies=active_pregnancies,
        visits_this_month=sum(1 for d in attended_days if (d.year, d.month) == (today.year, today.month)),
        reports_awaiting_review=reports,
        follow_ups_closed=len(closed),
        follow_ups_closed_on_time=sum(1 for closed_at, due_at in closed if closed_at <= due_at),
    )
    result = Trends(
        week_starts=starts,
        registrations=registrations,
        visits_attended=bucket_by_week(attended_days, starts),
        visits_missed=bucket_by_week(missed_days, starts),
        referrals_by_status=referrals_by_status,
        tiles=tiles,
    )
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="overview_trends",
        entity_type="Facility",
        entity_id=None,
        outcome=AuditOutcome.SUCCESS,
        metadata={"weeks": TREND_WEEKS, "active_pregnancies": active_pregnancies},
    )
    return result
