import uuid

from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyKey


def find_existing_response(db: Session, *, staff_user_id: uuid.UUID, endpoint: str, key: str) -> uuid.UUID | None:
    row = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.staff_user_id == staff_user_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.key == key,
        )
        .first()
    )
    return row.response_entity_id if row else None


def record_response(
    db: Session, *, staff_user_id: uuid.UUID, endpoint: str, key: str, entity_id: uuid.UUID
) -> None:
    db.add(
        IdempotencyKey(
            staff_user_id=staff_user_id, endpoint=endpoint, key=key, response_entity_id=entity_id
        )
    )
    db.commit()
