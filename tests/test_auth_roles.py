"""Registration, login, sessions and role based access control."""

from tests.conftest import login, new_client, unique


def test_first_user_is_admin_and_others_are_learners(client, admin):
    c = new_client(unique("user"))
    assert c.get("/api/me").json()["role"] == "learner"


def test_registration_validation(client, admin):
    c = new_client()
    r = c.post(
        "/register", data={"username": "ab", "password": "geheim123", "password2": "geheim123"}
    )
    assert r.status_code == 400 and "Benutzername" in r.text
    r = c.post("/register", data={"username": "okname", "password": "kurz", "password2": "kurz"})
    assert r.status_code == 400 and "mindestens" in r.text
    r = c.post(
        "/register", data={"username": "okname", "password": "geheim123", "password2": "anders123"}
    )
    assert r.status_code == 400 and "stimmen nicht" in r.text


def test_duplicate_username_rejected(client, admin):
    name = unique("dup")
    new_client(name)
    c = new_client()
    r = c.post(
        "/register", data={"username": name, "password": "geheim123", "password2": "geheim123"}
    )
    assert r.status_code == 400 and "vergeben" in r.text


def test_wrong_password_and_logout(client, admin):
    name = unique("auth")
    c = new_client(name)
    c.cookies.clear()
    r = c.post("/login", data={"username": name, "password": "falsch123"})
    assert r.status_code == 400
    login(c, name)
    assert c.get("/account").status_code == 200
    r = c.post("/logout")
    assert r.status_code == 303
    r = c.get("/account")
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


def test_anonymous_redirected_and_api_401(client):
    c = new_client()
    r = c.get("/progress")
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/progress"
    assert c.get("/api/progress").status_code == 401


def test_learner_cannot_access_admin(client, admin):
    c = new_client(unique("lrn"))
    assert c.get("/admin").status_code == 403
    assert c.get("/admin/users").status_code == 403
    assert c.post("/admin/settings", data={"registration_mode": "open"}).status_code == 403
    assert c.get("/admin/import").status_code == 403


def test_supervisor_role_limits(client, admin):
    name = unique("sup")
    c = new_client(name)
    uid = c.get("/api/me").json()["id"]
    r = admin.post(f"/admin/users/{uid}/role", data={"role": "supervisor"})
    assert r.status_code == 303
    assert c.get("/admin").status_code == 200
    assert c.get("/admin/import").status_code == 200
    assert c.get("/admin/settings").status_code == 403  # admin only
    assert c.post(f"/admin/users/{uid}/role", data={"role": "admin"}).status_code == 403


def test_registration_with_approval(client, admin):
    assert admin.post("/admin/settings", data={"registration_mode": "approval"}).status_code == 303
    try:
        name = unique("pending")
        c = new_client()
        r = c.post(
            "/register", data={"username": name, "password": "geheim123", "password2": "geheim123"}
        )
        assert r.status_code == 200 and "Freigabe" in r.text
        r = c.post("/login", data={"username": name, "password": "geheim123"})
        assert r.status_code == 403
        users = admin.get("/admin/users").text
        assert name in users and "pending" in users
        uid = [u for u in _user_rows(admin) if u[0] == name][0][1]
        assert admin.post(f"/admin/users/{uid}/approve").status_code == 303
        login(c, name)
        assert c.get("/api/me").json()["username"] == name
    finally:
        admin.post("/admin/settings", data={"registration_mode": "open"})


def _user_rows(admin):
    from sqlalchemy import select

    from app.db import session_scope
    from app.models import User

    with session_scope() as db:
        return [(u.username, u.id) for u in db.execute(select(User)).scalars()]


def test_disable_user_terminates_session(client, admin):
    name = unique("dis")
    c = new_client(name)
    uid = c.get("/api/me").json()["id"]
    assert admin.post(f"/admin/users/{uid}/status", data={"status": "disabled"}).status_code == 303
    assert c.get("/api/me").status_code == 401
    r = c.post("/login", data={"username": name, "password": "geheim123"})
    assert r.status_code == 403
    admin.post(f"/admin/users/{uid}/status", data={"status": "active"})


def test_password_change_invalidates_other_sessions(client, admin):
    name = unique("pw")
    c1 = new_client(name)
    c2 = new_client()
    login(c2, name)
    r = c1.post(
        "/account/password",
        data={"current_password": "geheim123", "password": "neuespw123", "password2": "neuespw123"},
    )
    assert r.status_code == 303
    assert c1.get("/api/me").status_code == 200
    assert c2.get("/api/me").status_code == 401
    login(c2, name, "neuespw123")


def test_origin_check_blocks_cross_site_post(client, admin):
    r = admin.post(
        "/account/profile", data={"display_name": "x"}, headers={"Origin": "https://evil.example"}
    )
    assert r.status_code == 403


def test_user_data_isolation(client, admin):
    """A learner cannot open another learner's exam."""
    a = new_client(unique("isoA"))
    b = new_client(unique("isoB"))
    a.post("/modules/select", data={"module_code": "303", "action": "add"})
    r = a.get("/exam/303/start")
    exam_url = r.headers["location"]
    assert a.get(exam_url).status_code == 200
    assert b.get(exam_url).status_code == 404
    assert b.get(exam_url + "/result").status_code == 404
