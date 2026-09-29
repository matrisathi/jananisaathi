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
    password: str


class StaffCreateOut(BaseModel):
    id: str
    username: str
    full_name: str


class MembershipGrant(BaseModel):
    staff_user_id: str
    role: StaffRole


class MembershipOut(BaseModel):
    id: str
    staff_user_id: str
    facility_id: str
    role: StaffRole
    active: bool
