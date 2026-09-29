from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Main request-scoped engine — used for the transactional work of a request.
engine = create_engine(settings.database_url_app, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# A separate engine/session factory dedicated to audit writes. Audit events for
# a *denied* request must survive even if the rest of that request's
# transaction is rolled back (e.g. an authorization failure raised mid-request).
# Using an independent connection/transaction — committed immediately inside
# app.services.audit_service — guarantees that durability regardless of what
# happens to the caller's own session.
audit_engine = create_engine(settings.database_url_app, pool_pre_ping=True)
AuditSessionLocal = sessionmaker(bind=audit_engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
