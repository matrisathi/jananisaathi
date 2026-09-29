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
from app.models.identity import ContactMethod, ContactType, Person
from app.models.staff import StaffUser
from app.schemas.person import PersonCreate, PersonOut
from app.services import audit_service

router = APIRouter(prefix="/people", tags=["people"])


def _to_out(person: Person, phone: str) -> PersonOut:
    return PersonOut(
        id=str(person.id),
        full_name=person.full_name,
        date_of_birth=person.date_of_birth,
        preferred_language=person.preferred_language,
        registering_facility_id=str(person.registering_facility_id),
        phone=phone,
    )


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(
    body: PersonCreate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
    _csrf: None = Depends(require_csrf_header),
) -> PersonOut:
    facility_id = uuid.UUID(body.facility_id)
    # Server-side ownership: the caller must hold an active membership at the
    # facility they're registering this person under, and that facility must
    # be active. facility_id is never trusted beyond that validation.
    require_facility_membership(db, staff, facility_id)
    require_active_facility(db, facility_id)

    person = Person(
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        preferred_language=body.preferred_language,
        registering_facility_id=facility_id,
        created_by_staff_user_id=staff.id,
    )
    db.add(person)
    db.flush()
    contact = ContactMethod(person_id=person.id, type=ContactType.PHONE, value=body.phone)
    db.add(contact)
    db.commit()

    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="create",
        entity_type="Person",
        entity_id=str(person.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={"facility_id": str(facility_id)},
    )
    return _to_out(person, body.phone)


@router.get("/{person_id}", response_model=PersonOut)
def get_person(
    person_id: str,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
) -> PersonOut:
    person = db.get(Person, uuid.UUID(person_id))
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        require_facility_membership(db, staff, person.registering_facility_id)
    except HTTPException:
        audit_service.record_event(
            actor_staff_user_id=staff.id,
            action="read",
            entity_type="Person",
            entity_id=str(person.id),
            outcome=AuditOutcome.DENIED,
            metadata={},
        )
        raise

    contact = (
        db.query(ContactMethod)
        .filter(ContactMethod.person_id == person.id, ContactMethod.type == ContactType.PHONE)
        .first()
    )
    audit_service.record_event(
        actor_staff_user_id=staff.id,
        action="read",
        entity_type="Person",
        entity_id=str(person.id),
        outcome=AuditOutcome.SUCCESS,
        metadata={},
    )
    return _to_out(person, contact.value if contact else "")
