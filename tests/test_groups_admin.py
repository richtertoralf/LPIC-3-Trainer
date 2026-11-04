"""Groups, supervisor views and administration pages."""

import re

from tests.conftest import new_client, unique


def test_group_lifecycle_with_approval(client, admin):
    name = unique("Gruppe ")
    r = admin.post("/admin/groups", data={"name": name, "join_mode": "approval"})
    assert r.status_code == 303
    gid = int(r.headers["location"].rsplit("/", 1)[1])
    member = new_client(unique("member"))
    assert name in member.get("/groups").text
    assert member.post(f"/groups/{gid}/join").status_code == 303
    assert "wartet auf Freigabe" in member.get("/groups").text
    uid = member.get("/api/me").json()["id"]
    page = admin.get(f"/admin/groups/{gid}").text
    assert "Beitrittsanfragen" in page
    assert admin.post(f"/admin/groups/{gid}/members/{uid}/approve").status_code == 303
    assert "Du bist Mitglied" in member.get("/groups").text
    member.post("/modules/select", data={"module_code": "303", "action": "add"})
    page = admin.get(f"/admin/groups/{gid}").text
    assert "303:" in page
    assert member.post(f"/groups/{gid}/leave").status_code == 303
    assert "Beitreten" in member.get("/groups").text or "anfragen" in member.get("/groups").text


def test_supervisor_sees_only_own_groups(client, admin):
    sup = new_client(unique("sup"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    own = unique("Eigene ")
    other = unique("Fremde ")
    r = sup.post("/admin/groups", data={"name": own, "join_mode": "open"})
    own_id = int(r.headers["location"].rsplit("/", 1)[1])
    r = admin.post("/admin/groups", data={"name": other, "join_mode": "open"})
    other_id = int(r.headers["location"].rsplit("/", 1)[1])
    page = sup.get("/admin/groups").text
    assert own in page and other not in page
    assert sup.get(f"/admin/groups/{own_id}").status_code == 200
    assert sup.get(f"/admin/groups/{other_id}").status_code == 403
    assert sup.post(f"/admin/groups/{other_id}/delete").status_code == 403


def test_supervisor_private_questions_visible_to_group_members(client, admin):
    import copy
    import json

    from tests.test_content_import import QUESTION_DOC

    sup = new_client(unique("supq"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    r = sup.post("/admin/groups", data={"name": unique("Kurs "), "join_mode": "open"})
    gid = int(r.headers["location"].rsplit("/", 1)[1])
    doc = copy.deepcopy(QUESTION_DOC)
    ext = unique("supq-")
    doc["questions"] = [doc["questions"][0] | {"id": ext}]
    files = {"file": ("kurs.json", json.dumps(doc).encode(), "application/json")}
    assert sup.post("/admin/import", data={"visibility": "public"}, files=files).status_code == 303
    page = sup.get(f"/admin/questions?q={ext}").text
    qid = int(re.search(r'href="/question/(\d+)"', page).group(1))
    assert "private" in page  # supervisors cannot publish
    outsider = new_client(unique("out"))
    assert outsider.get(f"/question/{qid}").status_code == 404
    insider = new_client(unique("in"))
    insider.post(f"/groups/{gid}/join")
    assert insider.get(f"/question/{qid}").status_code == 200


def test_admin_user_management(client, admin):
    target = new_client(unique("victim"))
    uid = target.get("/api/me").json()["id"]
    r = admin.post(f"/admin/users/{uid}/reset-password")
    assert r.status_code == 303
    page = admin.get("/admin/users").text
    pw = re.search(r"Neues Passwort für \w+: (\S+) ", page).group(1)
    assert target.get("/api/me").status_code == 401
    assert (
        target.post(
            "/login", data={"username": target_name(target, uid), "password": pw}
        ).status_code
        == 303
    )
    assert admin.post(f"/admin/users/{uid}/delete").status_code == 303
    assert target.get("/api/me").status_code == 401
    me = admin.get("/api/me").json()["id"]
    assert (
        "eigene Konto" in admin.get("/admin/users", cookies=admin.cookies).text
        or admin.post(f"/admin/users/{me}/delete").status_code == 303
    )
    assert admin.get("/api/me").status_code == 200


def target_name(client, uid):
    from app.db import session_scope
    from app.models import User

    with session_scope() as db:
        return db.get(User, uid).username


def test_admin_pages_render(client, admin):
    for path in (
        "/admin",
        "/admin/users",
        "/admin/groups",
        "/admin/import",
        "/admin/questions",
        "/admin/questions?module=303",
        "/admin/settings",
        "/admin/stats",
    ):
        assert admin.get(path).status_code == 200, path


def test_toggle_question_active(client, admin):
    page = admin.get("/admin/questions?module=303&q=303-331.1-01").text
    qid = int(re.search(r'href="/question/(\d+)"', page).group(1))
    assert admin.post(f"/admin/questions/{qid}/toggle").status_code == 303
    learner = new_client(unique("tog"))
    assert learner.get(f"/question/{qid}").status_code == 404
    admin.post(f"/admin/questions/{qid}/toggle")
    assert learner.get(f"/question/{qid}").status_code == 200
