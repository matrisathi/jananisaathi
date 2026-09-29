from datetime import date

from pydantic import BaseModel


class PersonCreate(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    preferred_language: str | None = None
    facility_id: str
    phone: str


class PersonOut(BaseModel):
    id: str
    full_name: str
    date_of_birth: date | None
    preferred_language: str | None
    registering_facility_id: str
    phone: str
