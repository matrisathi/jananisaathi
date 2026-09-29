from datetime import date, datetime

from pydantic import BaseModel

from app.models.pregnancy import DatingSource, PregnancyEpisodeStatus


class PregnancyEpisodeCreate(BaseModel):
    person_id: str
    dating_estimate: date | None = None
    dating_source: DatingSource = DatingSource.UNKNOWN


class PregnancyEpisodeOut(BaseModel):
    id: str
    mother_person_id: str
    mother_full_name: str
    facility_id: str
    dating_estimate: date | None
    dating_source: DatingSource
    status: PregnancyEpisodeStatus
    created_at: datetime
