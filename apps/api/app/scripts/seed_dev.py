"""Seeds one synthetic organization, facility and coordinator for local
manual demonstration. Safe to run repeatedly (skips if already seeded).

Usage: uv run python -m app.scripts.seed_dev
"""

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.facility import Facility
from app.models.organization import Organization
from app.models.staff import StaffMembership, StaffRole, StaffUser

DEV_USERNAME = "coordinator1"
DEV_PASSWORD = "synthetic-dev-password-123"  # noqa: S105 — synthetic, local dev only


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.query(StaffUser).filter(StaffUser.username == DEV_USERNAME).first()
        if existing:
            print(f"Already seeded. Login with username={DEV_USERNAME!r}, password={DEV_PASSWORD!r}")
            return

        org = Organization(name="Synthetic Pilot NGO")
        db.add(org)
        db.flush()

        facility = Facility(organization_id=org.id, name="Synthetic Rural Facility", active=True)
        db.add(facility)
        db.flush()

        staff = StaffUser(
            username=DEV_USERNAME,
            full_name="Synthetic Coordinator",
            phone="+910000000001",
            password_hash=hash_password(DEV_PASSWORD),
            active=True,
        )
        db.add(staff)
        db.flush()

        db.add(
            StaffMembership(
                staff_user_id=staff.id,
                facility_id=facility.id,
                role=StaffRole.COORDINATOR,
                active=True,
            )
        )
        db.commit()

        print("Seeded synthetic dev data:")
        print(f"  organization = {org.name} ({org.id})")
        print(f"  facility     = {facility.name} ({facility.id})")
        print(f"  login        = username={DEV_USERNAME!r}, password={DEV_PASSWORD!r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
