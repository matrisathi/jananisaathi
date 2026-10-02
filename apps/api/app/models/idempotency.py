import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class IdempotencyKey(Base, TimestampMixin):
    """Backs client-supplied `Idempotency-Key` headers on retryable creates
    (T002: "operation IDs for retryable creates").

    Concurrency-safe by construction, not by convention: a row is claimed
    with `INSERT ... ON CONFLICT (staff_user_id, endpoint, key) DO NOTHING`
    (see app/services/idempotency_service.py), which is a single
    database-enforced atomic operation — two concurrent requests racing on
    the same key cannot both "win" the unique constraint, and Postgres
    blocks the loser until the winner's transaction resolves rather than
    letting both proceed. `response_entity_id` starts NULL and is filled in
    in the SAME transaction that creates the business entity, so a claim
    and its result either commit together or (on any failure/crash before
    commit) neither is ever visible to another request at all.
    """

    __tablename__ = "idempotency_key"
    __table_args__ = (UniqueConstraint("staff_user_id", "endpoint", "key", name="uq_idempotency_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_user.id"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    # Hash of the normalized request body. A retry must resend the same
    # payload; reusing a key with a different payload is a client error,
    # not a legitimate retry, and is rejected rather than silently
    # returning whichever result happened to be created first.
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
