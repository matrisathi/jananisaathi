from pydantic import BaseModel

from app.models.staff import StaffRole


class FacilityCreate(BaseModel):
    name: str


class FacilityOut(BaseModel):
    id: str
    organization_id: str
    name: str
    active: bool


class StaffCreate(BaseModel):
    organization_id: str
    username: str
    full_name: str
    # Omit to have a temporary password generated and returned once.
    password: str | None = None
    # Optional: give the new account a facility role in the same step.
    facility_id: str | None = None
    role: StaffRole | None = None


class StaffCreateOut(BaseModel):
    id: str
    username: str
    full_name: str
    # Shown once to the admin; never stored or retrievable again.
    temporary_password: str | None = None
    membership_id: str | None = None


class TeamMembership(BaseModel):
    id: str
    facility_id: str
    facility_name: str
    role: StaffRole


class TeamMember(BaseModel):
    id: str
    username: str
    full_name: str
    active: bool
    must_change_password: bool
    is_org_admin: bool
    memberships: list[TeamMembership]


class TeamOut(BaseModel):
    organization_id: str
    facilities: list[FacilityOut]
    staff: list[TeamMember]


class PasswordResetOut(BaseModel):
    temporary_password: str


class MembershipGrant(BaseModel):
    staff_user_id: str
    role: StaffRole


class MembershipOut(BaseModel):
    id: str
    staff_user_id: str
    facility_id: str
    role: StaffRole
    active: bool
