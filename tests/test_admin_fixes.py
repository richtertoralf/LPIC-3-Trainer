"""P2 fixes: user creation in the web UI, supervisor visibility, duplicates, inactive flag,
provenance fields."""

import copy
import json
import re

from sqlalchemy import select

from app.content import import_document, validate
from app.db import session_scope
from app.models import ImportBatch, Question
from tests.conftest import new_client, unique
from tests.test_content_import import QUESTION_DOC


def test_admin_creates_users_in_web_ui(client, admin):
    name = unique("webuser")
    r = admin.post(
        "/admin/users",
        data={
            "username": name,
            "display_name": "Web User",
            "role": "supervisor",
            "password": "geheim123",
        },
    )
    assert r.status_code == 303
    c = new_client()
    assert c.post("/login", data={"username": name, "password": "geheim123"}).status_code == 303
    assert c.get("/api/me").json()["role"] == "supervisor"
    # validation and duplicates
    r = admin.post(
        "/admin/users", data={"username": name, "role": "learner", "password": "geheim123"}
    )
    assert r.status_code == 303 and "vergeben" in admin.get("/admin/users").text
    r = admin.post(
        "/admin/users", data={"username": "ab", "role": "learner", "password": "geheim123"}
    )
    assert "Ungültiger Benutzername" in admin.get("/admin/users").text
    assert (
        admin.post(
            "/admin/users", data={"username": "okname9", "role": "king", "password": "geheim123"}
        ).status_code
        == 400
    )
    # supervisors and learners may not create users
    sup = new_client(unique("nosup"))
    assert (
        sup.post(
            "/admin/users", data={"username": "x1234", "role": "learner", "password": "geheim123"}
        ).status_code
        == 403
    )


def test_supervisor_sees_only_pending_and_own_members(client, admin):
    sup = new_client(unique("vsup"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    stranger = new_client(unique("stranger"))
    stranger_name = stranger.get("/api/me").json()["username"]
    member = new_client(unique("member"))
    member_name = member.get("/api/me").json()["username"]
    r = sup.post("/admin/groups", data={"name": unique("Sicht "), "join_mode": "open"})
    gid = int(r.headers["location"].rsplit("/", 1)[1])
    member.post(f"/groups/{gid}/join")
    page = sup.get("/admin/users").text
    assert member_name in page and stranger_name not in page
    assert stranger_name in admin.get("/admin/users").text
    # import list: supervisors see only their own batches
    doc = copy.deepcopy(QUESTION_DOC)
    doc["source"] = unique("Fremdimport ")
    doc["questions"] = [doc["questions"][0] | {"id": unique("fi-")}]
    files = {"file": ("fremd.json", json.dumps(doc).encode(), "application/json")}
    assert admin.post("/admin/import", data={}, files=files).status_code == 303
    assert "fremd.json" not in sup.get("/admin/import").text
    assert "fremd.json" in admin.get("/admin/import").text


def test_duplicate_warning_on_import(client, admin):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["source"] = unique("Dublette ")
    with session_scope() as db:
        existing = db.execute(
            select(Question).where(Question.external_id == "303-331.1-01")
        ).scalar_one()
        text = existing.text_en
    doc["questions"] = [doc["questions"][0] | {"id": unique("dup-"), "question": text + " Really?"}]
    with session_scope() as db:
        result = import_document(db, doc, filename="dup.json")
        assert result.warnings and "303-331.1-01" in result.warnings[0]
    doc["questions"][0]["id"] = unique("dup-")
    files = {"file": ("dup.json", json.dumps(doc).encode(), "application/json")}
    assert admin.post("/admin/import", data={}, files=files).status_code == 303
    assert "Mögliche Dubletten" in admin.get("/admin/import").text


def test_inactive_flag_from_file_survives_reimport(client, admin):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["source"] = unique("Inaktiv ")
    qid = unique("inactive-")
    doc["questions"] = [doc["questions"][0] | {"id": qid, "active": False}]
    with session_scope() as db:
        import_document(db, doc, filename="in.json")
        import_document(db, doc, filename="in.json")
        q = db.execute(select(Question).where(Question.external_id == qid)).scalar_one()
        assert q.is_active is False
    bad = copy.deepcopy(doc)
    bad["questions"][0]["active"] = "no"
    assert any("'active'" in e for e in validate(bad))


def test_disputed_examtopics_questions_are_inactive_and_marked(client):
    with session_scope() as db:
        for ext in ("300-examtopics-screenshot-08", "305-examtopics-screenshot-03"):
            q = db.execute(select(Question).where(Question.external_id == ext)).scalar_one()
            assert q.is_active is False
            assert "unsicher" in q.explanation_de


def test_provenance_fields_stored_and_displayed(client, admin):
    with session_scope() as db:
        batches = (
            db.execute(select(ImportBatch).where(ImportBatch.kind == "questions")).scalars().all()
        )
        assert all(
            re.fullmatch(r"\d{3}-300", b.exam_code) and b.exam_code.startswith(b.module_code)
            for b in batches
        )
        assert all(b.source_url.startswith("https://") for b in batches if b.bundled)
        extra = (
            db.execute(
                select(ImportBatch).where(
                    ImportBatch.supplementary.is_(True),
                    ImportBatch.bundled.is_(True),
                    ImportBatch.rights == "unverified",
                )
            )
            .scalars()
            .first()
        )
        assert "examtopics.com" in extra.source_url and extra.rights == "unverified"
        q = (
            db.execute(
                select(Question).where(
                    Question.import_batch_id == extra.id, Question.is_active.is_(True)
                )
            )
            .scalars()
            .first()
        )
    page = admin.get("/admin/releases").text
    assert extra.exam_code in page and "Original-URL" in page and "Autor:" in page
    learn = admin.get(f"/question/{q.id}").text
    assert (
        f"Prüfung {extra.exam_code}" in learn and "Original" in learn and extra.source_url in learn
    )
    doc = copy.deepcopy(QUESTION_DOC)
    doc["exam_code"] = "305-300"  # wrong module
    assert any("does not belong" in e for e in validate(doc))
    doc["exam_code"] = "303-300"
    doc["source_url"] = "ftp://nope"
    assert any("source_url" in e for e in validate(doc))
