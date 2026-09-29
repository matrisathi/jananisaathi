import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import (
    get_current_staff,
    require_active_facility,
    require_csrf_header,
    require_facility_membership,
)
from app.models.audit import AuditOutcome
from app.models.identity import Person
from app.models.pregnancy import PregnancyEpisode
from app.models.staff import StaffUser
from app.schemas.pregnancy import PregnancyEpisodeCreate, PregnancyEpisodeOut
from app.services import audit_service

router = APIRouter(prefix="/pregnancy-episodes", tags=["pregnancies"])


def _to_out(episode: PregnancyEpisode, mother_name: str) -> PregnancyEpisodeOut:
    return PregnancyEpisodeOut(
        id=str(episode.id),
        mother_person_id=str(episode.mother_person_id),
        mother_full_name=mother_name,
        facility_id=str(episode.facility_id),
        dating_estimate=episode.dating_estimate,
        dating_source=episode.dating_source,
        status=episode.status,
        created_at=episode.created_at,
    )


@router.post("", response_model=PregnancyEpisodeOut, status_code=status.HTTP_201_CREATED)
def create_pregnancy_episode(
    body: PregnancyEpisodeCreate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> PregnancyEpisodeOut:
    person = db.get(Person, uuid.UUID(body.person_id))
    if person is None:
        audit_service.record_event(
            actor_staff_user_id=staff.id,
            action="create",
            entity_type="PregnancyEpisode",
            entity_id=None,
            outcome=AuditOutcome.DENIED,
            metadata={"reason": "person_not_found_or_inaccessible"},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    # Reject creating an episode against a person the caller cannot access —
    # access to a Person is the same facility-membership check used for
    # everything else, so this can't be bypassed by supplying a bare id.
    try:
        require_facility_membership(db, staff, person.registering_facility_id)
        require_active_facility(db, person.registering_facility_id)
    except HTTPException:
        audit_service.record_event(
            actor_staff_user_id=staff.id,
            action="create",
            entity_type="PregnancyEpisode",
            entity_id=None,
            outcome=AuditOutcome.DENIED,
            metadata={"reason": "person_not_found_or_inaccessible"},
        )
        raise

    # facility_id is derived from the person's registering facility, never
    # accepted from the client — the episode cannot be created under an
    # arbitrary facility the caller merely names in the request body.
    episode = PregnancyEpisode(
        mother_person_id=person.id,
        facility_id=person.registering_facility_id,
        dating_estimate=body.dating_estimate,
        dating_source=body.dating_source,
        created_by_staff_user_id=staff.id,
    )
    db.add(episode)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="create",
        entity_type="PregnancyEpisode",
        entity_id=str(episode.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"facility_id": str(episode.facility_id)},
    )
    return _to_out(episode, person.full_name)


@router.get("/{episode_id}", response_model=PregnancyEpisodeOut)
def get_pregnancy_episode(
    episode_id: str,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
) -> PregnancyEpisodeOut:
    episode = db.get(PregnancyEpisode, uuid.UUID(episode_id))
    if episode is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        require_facility_membership(db, staff, episode.facility_id)
    except HTTPException:
        audit_service.record_event(
            actor_staff_user_id=staff.id,
            action="read",
            entity_type="PregnancyEpisode",
            entity_id=str(episode.id),
            outcome=AuditOutcome.DENIED,
            metadata={},
        )
        raise

    mother = db.get(Person, episode.mother_person_id)
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="read",
        entity_type="PregnancyEpisode",
        entity_id=str(episode.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={},
    )
    return _to_out(episode, mother.full_name if mother else "")
