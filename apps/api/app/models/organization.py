import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class Organization(Base, TimestampMixin):
    __tablename__ = "organization"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class OrganizationAdmin(Base, TimestampMixin):
    """Explicit grant of organization-wide administrative authority.

    Deliberately NOT inferred from a StaffMembership role: facility-level
    roles (ASHA/NURSE/COORDINATOR/DOCTOR) govern facility-scoped clinical
    data only. Managing facilities and staff memberships across an
    organization requires a separate, auditable grant in this table.
    """

    __tablename__ = "organization_admin"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=False
    )
    granted_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def active(self) -> bool:
        return self.revoked_at is None
