import uuid

from app.core.db import AuditSessionLocal
from app.models.audit import AuditEvent, AuditOutcome


def record_event(
    *,
    actor_staff_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    outcome: AuditOutcome,
    metadata: dict | None = None,
) -> None:
    """Writes and commits an audit row on its own session/transaction.

    Deliberately independent of the caller's request-scoped `db` session: if
    the calling request goes on to fail or roll back (e.g. an authorization
    check denies the operation, or an exception is raised afterwards), this
    audit row must still survive. Using a separate connection/transaction
    that commits immediately guarantees that.
    """
    session = AuditSessionLocal()
    try:
        session.add(
            AuditEvent(
                actor_staff_user_id=actor_staff_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                outcome=outcome,
                metadata_json=metadata or {},
            )
        )
        session.commit()
    finally:
        session.close()
