import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_staff, require_csrf_header, require_org_admin
from app.core.security import generate_temporary_password, hash_password, new_password_problem
from app.models.audit import AuditOutcome
from app.models.facility import Facility
from app.models.organization import OrganizationAdmin
from app.models.staff import RefreshToken, StaffMembership, StaffUser
from app.schemas.admin import (
    FacilityCreate,
    FacilityOut,
    MembershipGrant,
    MembershipOut,
    PasswordResetOut,
    StaffCreate,
    StaffCreateOut,
    TeamMember,
    TeamMembership,
    TeamOut,
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


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")


@router.post("/staff", response_model=StaffCreateOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    body: StaffCreate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> StaffCreateOut:
    """An organization admin creates a staff account. Without a password, a
    temporary one is generated and returned once; either way the person must
    choose their own at first sign-in. With facility_id and role, the facility
    membership is granted in the same transaction."""
    org_id = uuid.UUID(body.organization_id)
    # Creating staff accounts is an organization-administrative action, gated
    # the same way facility creation is, not by any facility-level role.
    require_org_admin(db, staff, org_id)

    username = body.username.strip().lower()
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username: 3 to 50 characters; lowercase letters, numbers, dots, dashes or underscores.",
        )
    full_name = body.full_name.strip()
    if not full_name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter the person's full name.")
    if db.query(StaffUser).filter(StaffUser.username == username).first() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Username already in use")
    if (body.facility_id is None) != (body.role is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Give both a facility and a role, or neither.")

    facility = None
    if body.facility_id is not None:
        facility = db.get(Facility, uuid.UUID(body.facility_id))
        if facility is None or facility.organization_id != org_id or not facility.active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    temporary = None
    if body.password is None:
        temporary = generate_temporary_password()
        password = temporary
    else:
        password = body.password
        problem = new_password_problem(password, username=username)
        if problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problem)

    new_staff = StaffUser(
        username=username,
        full_name=full_name,
        phone=None,
        password_hash=hash_password(password),
        active=True,
        must_change_password=True,
    )
    db.add(new_staff)
    db.flush()
    membership = None
    if facility is not None and body.role is not None:
        membership = StaffMembership(staff_user_id=new_staff.id, facility_id=facility.id, role=body.role, active=True)
        db.add(membership)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="create",
        entity_type="StaffUser",
        entity_id=str(new_staff.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={
            "organization_id": str(org_id),
            "facility_id": str(facility.id) if facility else None,
            "role": body.role.value if body.role else None,
            "temporary_password_generated": temporary is not None,
        },
    )
    return StaffCreateOut(
        id=str(new_staff.id),
        username=new_staff.username,
        full_name=new_staff.full_name,
        temporary_password=temporary,
        membership_id=str(membership.id) if membership else None,
    )


@router.get("/organizations/{organization_id}/team", response_model=TeamOut)
def list_team(
    organization_id: str,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
) -> TeamOut:
    """Facilities of the organization and the staff with an active role at any of them."""
    org_id = uuid.UUID(organization_id)
    require_org_admin(db, staff, org_id)
    facilities = db.query(Facility).filter(Facility.organization_id == org_id).order_by(Facility.name).all()
    by_id = {f.id: f for f in facilities}
    rows = (
        db.query(StaffMembership, StaffUser)
        .join(StaffUser, StaffUser.id == StaffMembership.staff_user_id)
        .filter(
            StaffMembership.facility_id.in_(by_id.keys()),
            StaffMembership.active.is_(True),
            StaffMembership.revoked_at.is_(None),
        )
        .all()
    )
    admins = {
        a.staff_user_id
        for a in db.query(OrganizationAdmin).filter(
            OrganizationAdmin.organization_id == org_id, OrganizationAdmin.revoked_at.is_(None)
        )
    }
    members: dict[uuid.UUID, TeamMember] = {}
    for m, u in rows:
        member = members.setdefault(
            u.id,
            TeamMember(
                id=str(u.id),
                username=u.username,
                full_name=u.full_name,
                active=u.active,
                must_change_password=u.must_change_password,
                is_org_admin=u.id in admins,
                memberships=[],
            ),
        )
        member.memberships.append(
            TeamMembership(
                id=str(m.id), facility_id=str(m.facility_id), facility_name=by_id[m.facility_id].name, role=m.role
            )
        )
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="list_team",
        entity_type="Organization",
        entity_id=str(org_id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"count": len(members)},
    )
    return TeamOut(
        organization_id=str(org_id),
        facilities=[_facility_out(f) for f in facilities],
        staff=sorted(members.values(), key=lambda x: x.full_name.lower()),
    )


@router.post("/staff/{staff_user_id}/reset-password", response_model=PasswordResetOut)
def reset_password(
    staff_user_id: str,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> PasswordResetOut:
    """An org admin issues a new temporary password for someone with a role at
    one of their organization's facilities. The person's sessions end and
    they must choose a new password at next sign-in."""
    target = db.get(StaffUser, uuid.UUID(staff_user_id))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    org_ids = {
        f.organization_id
        for _, f in db.query(StaffMembership, Facility)
        .join(Facility, Facility.id == StaffMembership.facility_id)
        .filter(StaffMembership.staff_user_id == target.id)
        .all()
    }
    administered = [
        a.organization_id
        for a in db.query(OrganizationAdmin).filter(
            OrganizationAdmin.staff_user_id == staff.id,
            OrganizationAdmin.revoked_at.is_(None),
            OrganizationAdmin.organization_id.in_(org_ids),
        )
    ]
    if not administered or target.id == staff.id:
        # 404 for "not yours" (as elsewhere); an admin changes their own password themselves.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    temporary = generate_temporary_password()
    target.password_hash = hash_password(temporary)
    target.must_change_password = True
    db.query(RefreshToken).filter(RefreshToken.staff_user_id == target.id, RefreshToken.revoked_at.is_(None)).update(
        {RefreshToken.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False
    )
    db.commit()
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="reset_password",
        entity_type="StaffUser",
        entity_id=str(target.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"organization_id": str(administered[0])},
    )
    return PasswordResetOut(temporary_password=temporary)


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
