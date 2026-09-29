import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class IdempotencyKey(Base, TimestampMixin):
    """Backs client-supplied `Idempotency-Key` headers on retryable creates
    (T002: "operation IDs for retryable creates"). A retried request with
    the same key, from the same staff user, on the same endpoint, returns
    the original result instead of creating a second record — a retried
    mother-registration submission over a flaky connection must not create
    a duplicate Person/PregnancyEpisode.
    """

    __tablename__ = "idempotency_key"
    __table_args__ = (UniqueConstraint("staff_user_id", "endpoint", "key", name="uq_idempotency_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    response_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
