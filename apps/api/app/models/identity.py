import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ContactType(str, enum.Enum):
    PHONE = "PHONE"


class Person(Base, TimestampMixin):
    __tablename__ = "person"

    id: Mapped[uuid.UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # The facility that registered this person. This is the server-derived
    # ownership boundary for the person and everything created from them
    # (e.g. a PregnancyEpisode) — never a client-supplied value.
    registering_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facility.id"), nullable=False
    )
    created_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=True
    )


class ContactMethod(Base, TimestampMixin):
    """A contact channel for a Person — deliberately not unique.

    Two different Person rows may share the same phone number (a household
    handset). `value` therefore carries no identity meaning: the application
    must never resolve "the person" from a phone number alone.
    """

    __tablename__ = "contact_method"
    __table_args__ = (Index("ix_contact_method_value", "value"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id"), nullable=False
    )
    type: Mapped[ContactType] = mapped_column(Enum(ContactType, name="contact_type"), nullable=False)
    value: Mapped[str] = mapped_column(String(32), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
