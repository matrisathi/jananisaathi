from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.facility import Facility
from app.models.organization import Organization, OrganizationAdmin
from app.models.staff import StaffMembership, StaffRole, StaffUser


def make_org(db: Session, name: str = "Test Org") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    return org


def make_facility(db: Session, org: Organization, name: str = "Test Facility", active: bool = True) -> Facility:
    facility = Facility(organization_id=org.id, name=name, active=active)
    db.add(facility)
    db.commit()
    return facility


def make_staff(
    db: Session,
    username: str,
    password: str = "synthetic-password-123",
    active: bool = True,
    full_name: str = "Test Staff",
) -> StaffUser:
    staff = StaffUser(
        username=username,
        full_name=full_name,
        phone=None,
        password_hash=hash_password(password),
        active=active,
    )
    db.add(staff)
    db.commit()
    return staff


def make_membership(
    db: Session,
    staff: StaffUser,
    facility: Facility,
    role: StaffRole = StaffRole.COORDINATOR,
    active: bool = True,
) -> StaffMembership:
    from datetime import datetime, timezone

    membership = StaffMembership(
        staff_user_id=staff.id,
        facility_id=facility.id,
        role=role,
        active=active,
        revoked_at=None if active else datetime.now(timezone.utc),
    )
    db.add(membership)
    db.commit()
    return membership


def make_org_admin(db: Session, staff: StaffUser, org: Organization) -> OrganizationAdmin:
    grant = OrganizationAdmin(organization_id=org.id, staff_user_id=staff.id)
    db.add(grant)
    db.commit()
    return grant
