import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class DatingSource(str, enum.Enum):
    SELF_REPORTED = "SELF_REPORTED"
    CLINICIAN_CONFIRMED = "CLINICIAN_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class PregnancyEpisodeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class PregnancyEpisode(Base, TimestampMixin):
    __tablename__ = "pregnancy_episode"

    id: Mapped[uuid.UUID] = uuid_pk()
    mother_person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id"), nullable=False
    )
    # Always derived server-side from the mother Person's registering
    # facility at creation time — never accepted from the client. A change
    # of facility is a transfer action (later work), not a field edit.
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facility.id"), nullable=False
    )
    dating_estimate: Mapped[date | None] = mapped_column(Date, nullable=True)
    dating_source: Mapped[DatingSource] = mapped_column(
        Enum(DatingSource, name="dating_source"), nullable=False, default=DatingSource.UNKNOWN
    )
    status: Mapped[PregnancyEpisodeStatus] = mapped_column(
        Enum(PregnancyEpisodeStatus, name="pregnancy_episode_status"),
        nullable=False,
        default=PregnancyEpisodeStatus.ACTIVE,
    )
    created_by_staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
