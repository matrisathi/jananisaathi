import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_staff, require_csrf_header, require_org_admin
from app.core.security import hash_password
from app.models.audit import AuditOutcome
from app.models.facility import Facility
from app.models.staff import StaffMembership, StaffUser
from app.schemas.admin import (
    FacilityCreate,
    FacilityOut,
    MembershipGrant,
    MembershipOut,
    StaffCreate,
    StaffCreateOut,
)
from app.services import audit_service

router = APIRouter(tags=["admin"])


def _facility_out(f: Facility) -> FacilityOut:
    return FacilityOut(id=str(f.id), organization_id=str(f.organization_id), name=f.name, active=f.active)


@router.post(
    "/organizations/{organization_id}/facilities", response_model=FacilityOut, status_code=status.HTTP_201_CREATED
)
def create_facility(
    organization_id: str,
    body: FacilityCreate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> FacilityOut:
    org_id = uuid.UUID(organization_id)
    # Organization-admin authority is required and is never inferred from a
    # facility-level StaffMembership role (see app/models/organization.py).
    require_org_admin(db, staff, org_id)

    facility = Facility(organization_id=org_id, name=body.name, active=True)
    db.add(facility)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="create",
        entity_type="Facility",
        entity_id=str(facility.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"organization_id": str(org_id)},
    )
    return _facility_out(facility)


@router.post("/staff", response_model=StaffCreateOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    body: StaffCreate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> StaffCreateOut:
    org_id = uuid.UUID(body.organization_id)
    # Creating staff accounts is an organization-administrative action, gated
    # the same way facility creation is — not by any facility-level role.
    require_org_admin(db, staff, org_id)

    if db.query(StaffUser).filter(StaffUser.username == body.username).first() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Username already in use")

    new_staff = StaffUser(
        username=body.username,
        full_name=body.full_name,
        phone=None,
        password_hash=hash_password(body.password),
        active=True,
    )
    db.add(new_staff)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="create",
        entity_type="StaffUser",
        entity_id=str(new_staff.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"organization_id": str(org_id)},
    )
    return StaffCreateOut(id=str(new_staff.id), username=new_staff.username, full_name=new_staff.full_name)


@router.post(
    "/facilities/{facility_id}/memberships", response_model=MembershipOut, status_code=status.HTTP_201_CREATED
)
def grant_membership(
    facility_id: str,
    body: MembershipGrant,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> MembershipOut:
    facility = db.get(Facility, uuid.UUID(facility_id))
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    require_org_admin(db, staff, facility.organization_id)

    target = db.get(StaffUser, uuid.UUID(body.staff_user_id))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    membership = StaffMembership(
        staff_user_id=target.id, facility_id=facility.id, role=body.role, active=True
    )
    db.add(membership)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="grant",
        entity_type="StaffMembership",
        entity_id=str(membership.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"facility_id": str(facility.id), "staff_user_id": str(target.id)},
    )
    return MembershipOut(
        id=str(membership.id),
        staff_user_id=str(membership.staff_user_id),
        facility_id=str(membership.facility_id),
        role=membership.role,
        active=membership.active,
    )


@router.delete("/facilities/{facility_id}/memberships/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_membership(
    facility_id: str,
    membership_id: str,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> None:
    facility = db.get(Facility, uuid.UUID(facility_id))
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    require_org_admin(db, staff, facility.organization_id)

    membership = db.get(StaffMembership, uuid.UUID(membership_id))
    if membership is None or membership.facility_id != facility.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    membership.active = False
    membership.revoked_at = datetime.now(timezone.utc)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="revoke",
        entity_type="StaffMembership",
        entity_id=str(membership.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"facility_id": str(facility.id)},
    )
