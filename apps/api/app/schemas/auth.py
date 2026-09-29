from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class MembershipOut(BaseModel):
    facility_id: str
    facility_name: str
    role: str


class StaffOut(BaseModel):
    id: str
    username: str
    full_name: str
    memberships: list[MembershipOut] = []
