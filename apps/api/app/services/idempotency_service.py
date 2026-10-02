import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyKey


def hash_payload(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class ClaimResult:
    won: bool
    idempotency_row_id: uuid.UUID | None = None
    response_entity_id: uuid.UUID | None = None
    payload_mismatch: bool = False


def claim(
    db: Session, *, staff_user_id: uuid.UUID, endpoint: str, key: str, payload_hash: str
) -> ClaimResult:
    """Atomically claims (staff_user_id, endpoint, key) or reports who already
    holds it. Must be called within the same transaction/session that will
    go on to create the business entity and call `attach_result` — the
    caller commits once, at the end, covering the claim, the entity, and
    the attached result together. Do not call `db.commit()` between this
    and `attach_result`.

    This is a single `INSERT ... ON CONFLICT DO NOTHING`: the database's
    unique constraint is the only thing that decides who wins a race, and a
    concurrent competing INSERT blocks (at the Postgres row-lock level)
    until this transaction commits or rolls back — no process-local lock,
    no separate check-then-insert window.
    """
    stmt = (
        pg_insert(IdempotencyKey)
        .values(
            staff_user_id=staff_user_id,
            endpoint=endpoint,
            key=key,
            payload_hash=payload_hash,
            response_entity_id=None,
        )
        .on_conflict_do_nothing(index_elements=["staff_user_id", "endpoint", "key"])
        .returning(IdempotencyKey.id)
    )
    row = db.execute(stmt).first()
    if row is not None:
        return ClaimResult(won=True, idempotency_row_id=row[0])

    # Someone else already holds this key. Because the winner's claim and
    # its result are committed together atomically (see module docstring),
    # a row visible here — under Postgres's default read-committed
    # isolation, after our blocked INSERT unblocks — is always a *finished*
    # attempt: response_entity_id is never observably NULL to a different
    # transaction. (It can only be NULL within the winner's own still-open
    # transaction, which is exactly the case we're blocked behind.)
    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.staff_user_id == staff_user_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.key == key,
        )
        .first()
    )
    assert existing is not None  # the conflict proves a row exists
    if existing.payload_hash != payload_hash:
        return ClaimResult(won=False, payload_mismatch=True)
    return ClaimResult(won=False, response_entity_id=existing.response_entity_id)


def attach_result(db: Session, *, idempotency_row_id: uuid.UUID, entity_id: uuid.UUID) -> None:
    """Fills in the winning claim's result. Caller commits afterward, together
    with the entity creation — see `claim`'s docstring."""
    db.execute(
        update(IdempotencyKey).where(IdempotencyKey.id == idempotency_row_id).values(response_entity_id=entity_id)
    )
