"""Admin-created staff accounts: temporary password, forced change at first
sign-in, team list and password reset, all limited to organization admins."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.audit import AuditEvent
from app.models.staff import StaffRole
from tests.conftest import CSRF_HEADERS
from tests.factories import make_facility, make_membership, make_org, make_org_admin, make_staff

PASSWORD = "synthetic-password-123"
NEW_PASSWORD = "a-new-synthetic-pass-42"


def _client(username: str, password: str = PASSWORD) -> TestClient:
    c = TestClient(app)
    c.__enter__()
    r = c.post("/api/v1/auth/login", json={"username": username, "password": password}, headers=CSRF_HEADERS)
    assert r.status_code == 200, r.text
    return c


def _post(c, url, body=None):
    return c.post(url, json=body or {}, headers=CSRF_HEADERS)


def _world(db):
    org, other_org = make_org(db, "Org A"), make_org(db, "Org B")
    fa, fb = make_facility(db, org, "Facility A"), make_facility(db, other_org, "Facility B")
    admin, coord, other_admin = make_staff(db, "a_admin"), make_staff(db, "a_coord"), make_staff(db, "b_admin")
    make_org_admin(db, admin, org)
    make_org_admin(db, other_admin, other_org)
    make_membership(db, admin, fa, StaffRole.COORDINATOR)
    make_membership(db, coord, fa, StaffRole.COORDINATOR)
    make_membership(db, other_admin, fb, StaffRole.COORDINATOR)
    return {"org": str(org.id), "other_org": str(other_org.id), "fa": str(fa.id), "fb": str(fb.id)}


def _create(c, w, username="new.asha", **extra):
    body = {"organization_id": w["org"], "username": username, "full_name": "Synthetic New ASHA", "facility_id": w["fa"], "role": "ASHA"}
    body.update(extra)
    return _post(c, "/api/v1/staff", body)


def test_admin_creates_account_and_new_person_must_set_own_password(db_session):
    w = _world(db_session)
    admin = _client("a_admin")
    r = _create(admin, w)
    assert r.status_code == 201
    body = r.json()
    temp = body["temporary_password"]
    assert temp and len(temp) >= 12 and body["membership_id"]

    new = _client("new.asha", temp)
    me = new.get("/api/v1/auth/me").json()
    assert me["must_change_password"] is True
    assert [m["role"] for m in me["memberships"]] == ["ASHA"]
    # Nothing else works until the password is changed.
    blocked = new.get("/api/v1/tasks")
    assert blocked.status_code == 403 and blocked.json()["detail"] == "Password change required"

    assert _post(new, "/api/v1/auth/change-password", {"current_password": "wrong-password-xx", "new_password": NEW_PASSWORD}).status_code == 400
    assert _post(new, "/api/v1/auth/change-password", {"current_password": temp, "new_password": "short"}).status_code == 422
    assert _post(new, "/api/v1/auth/change-password", {"current_password": temp, "new_password": temp}).status_code == 422
    ok = _post(new, "/api/v1/auth/change-password", {"current_password": temp, "new_password": NEW_PASSWORD})
    assert ok.status_code == 200 and ok.json()["must_change_password"] is False
    assert new.get("/api/v1/tasks").status_code == 200
    # The session that changed the password keeps working after a refresh.
    assert _post(new, "/api/v1/auth/refresh").status_code == 200
    # The temporary password no longer signs in; the new one does.
    with TestClient(app) as fresh:
        assert _post(fresh, "/api/v1/auth/login", {"username": "new.asha", "password": temp}).status_code == 401
        assert _post(fresh, "/api/v1/auth/login", {"username": "new.asha", "password": NEW_PASSWORD}).status_code == 200


def test_only_org_admins_create_list_or_reset(db_session):
    w = _world(db_session)
    coord = _client("a_coord")
    assert _create(coord, w).status_code == 404
    assert coord.get(f"/api/v1/organizations/{w['org']}/team").status_code == 404
    admin = _client("a_admin")
    target = _create(admin, w).json()["id"]
    assert _post(coord, f"/api/v1/staff/{target}/reset-password").status_code == 404


def test_admin_of_another_org_cannot_reach_this_one(db_session):
    w = _world(db_session)
    other = _client("b_admin")
    assert _create(other, w).status_code == 404  # not admin of org A
    assert _create(other, {**w, "org": w["other_org"]}).status_code == 404  # facility A is not in org B
    assert other.get(f"/api/v1/organizations/{w['org']}/team").status_code == 404
    admin = _client("a_admin")
    target = _create(admin, w).json()["id"]
    assert _post(other, f"/api/v1/staff/{target}/reset-password").status_code == 404


def test_team_lists_people_with_roles(db_session):
    w = _world(db_session)
    admin = _client("a_admin")
    _create(admin, w)
    team = admin.get(f"/api/v1/organizations/{w['org']}/team").json()
    assert [f["name"] for f in team["facilities"]] == ["Facility A"]
    by_user = {s["username"]: s for s in team["staff"]}
    assert set(by_user) == {"a_admin", "a_coord", "new.asha"}
    assert by_user["a_admin"]["is_org_admin"] is True
    assert by_user["new.asha"]["must_change_password"] is True
    assert by_user["new.asha"]["memberships"][0]["role"] == "ASHA"


def test_reset_password_ends_sessions_and_forces_a_new_one(db_session):
    w = _world(db_session)
    admin = _client("a_admin")
    created = _create(admin, w).json()
    person = _client("new.asha", created["temporary_password"])
    _post(person, "/api/v1/auth/change-password", {"current_password": created["temporary_password"], "new_password": NEW_PASSWORD})

    reset = _post(admin, f"/api/v1/staff/{created['id']}/reset-password")
    assert reset.status_code == 200
    temp2 = reset.json()["temporary_password"]
    assert _post(person, "/api/v1/auth/refresh").status_code == 401  # session ended
    again = _client("new.asha", temp2)
    assert again.get("/api/v1/tasks").status_code == 403
    # An admin cannot reset their own password this way.
    admin_id = admin.get("/api/v1/auth/me").json()["id"]
    assert _post(admin, f"/api/v1/staff/{admin_id}/reset-password").status_code == 404


def test_validation_and_duplicates(db_session):
    w = _world(db_session)
    admin = _client("a_admin")
    assert _create(admin, w, username="No Spaces Allowed").status_code == 422
    assert _create(admin, w, username="ab").status_code == 422
    assert _create(admin, w, role=None).status_code == 422  # facility without role
    assert _create(admin, w, password="short").status_code == 422
    assert _create(admin, w).status_code == 201
    assert _create(admin, w, username="NEW.ASHA").status_code == 400  # usernames are case-insensitive


def test_temporary_passwords_never_reach_the_audit_log(db_session):
    w = _world(db_session)
    admin = _client("a_admin")
    created = _create(admin, w).json()
    reset = _post(admin, f"/api/v1/staff/{created['id']}/reset-password").json()
    events = db_session.execute(select(AuditEvent)).scalars().all()
    text = " ".join(str(e.metadata_json) for e in events)
    assert created["temporary_password"] not in text and reset["temporary_password"] not in text
    actions = {e.action for e in events}
    assert {"create", "reset_password"} <= actions
