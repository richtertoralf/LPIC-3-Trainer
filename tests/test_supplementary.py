"""Supplementary question pools: validation, import paths, enabling per group, visibility."""

import copy
import json
import os
import re
import subprocess
import sys

from sqlalchemy import select

from app.content import import_document, validate
from app.db import session_scope
from app.models import GroupSource, ImportBatch, Question
from tests.conftest import PROJECT_DIR, new_client, unique
from tests.test_content_import import QUESTION_DOC

EXTRA_FILE = PROJECT_DIR / "content" / "questions" / "extra" / "305-examtopics-2026-11-04.json"


def _extra_doc(prefix: str) -> dict:
    doc = copy.deepcopy(QUESTION_DOC)
    doc["module"] = "305"
    for q in doc["questions"]:
        q.pop("objective", None)
    doc["questions"][0]["id"] = unique(f"{prefix}-a-")
    doc["questions"][1]["id"] = unique(f"{prefix}-b-")
    doc["supplementary"] = True
    doc["source"] = f"Testquelle {prefix}"
    doc["rights"] = "unverified"
    doc["license"] = "Rechte nicht geklärt (Test)"
    return doc


def _make_supervisor(admin):
    sup = new_client(unique("tsup"))
    sup_id = sup.get("/api/me").json()["id"]
    assert admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"}).status_code == 303
    return sup, sup_id


def _make_group(client, name, join_mode="open"):
    r = client.post("/admin/groups", data={"name": name, "join_mode": join_mode})
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[1])


def test_validation_of_supplementary_header():
    doc = _extra_doc("val")
    assert validate(doc) == []
    bad = copy.deepcopy(doc)
    bad.pop("source")
    assert any("source" in e for e in validate(bad))
    bad = copy.deepcopy(doc)
    bad["rights"] = "maybe"
    assert any("rights" in e for e in validate(bad))
    bad = copy.deepcopy(doc)
    bad["supplementary"] = "yes"
    assert any("supplementary" in e for e in validate(bad))


def test_bundled_extra_file_is_marked_and_hidden(client, admin):
    """The bundled ExamTopics file imports as supplementary and stays hidden by default."""
    with session_scope() as db:
        batch = db.execute(
            select(ImportBatch).where(ImportBatch.filename == EXTRA_FILE.name)
        ).scalar_one()
        assert batch.supplementary and batch.source == "ExamTopics 04.11.2026"
        assert batch.rights == "unverified" and batch.bundled
        ids = [
            q.id
            for q in db.execute(
                select(Question).where(Question.import_batch_id == batch.id)
            ).scalars()
        ]
        assert len(ids) == 2
    learner = new_client(unique("hidden"))
    learner.post("/modules/select", data={"module_code": "305", "action": "add"})
    for qid in ids:
        assert learner.get(f"/question/{qid}").status_code == 404
        assert admin.get(f"/question/{qid}").status_code == 200
    assert (
        "Zusatzfragen"
        not in learner.get("/module/305").text.split("<main")[1].split("Zusatzfragen üben")[0]
    )
    # the admin sees the tag
    assert "Zusatzfrage" in admin.get(f"/question/{ids[0]}").text


def test_supervisor_enables_source_for_group(client, admin):
    sup, sup_id = _make_supervisor(admin)
    gid = _make_group(sup, unique("Kurs Zusatz "))
    doc = _extra_doc("ena")
    files = {"file": ("extra.json", json.dumps(doc).encode(), "application/json")}
    r = sup.post(
        "/admin/import",
        data={
            "visibility": "public",
            "supplementary": "1",
            "source": doc["source"],
            "rights": "unverified",
        },
        files=files,
    )
    assert r.status_code == 303, r.text
    with session_scope() as db:
        batch = db.execute(
            select(ImportBatch).where(ImportBatch.source == doc["source"])
        ).scalar_one()
        assert batch.supplementary and batch.rights == "unverified"
        qids = [
            q.id
            for q in db.execute(
                select(Question).where(Question.import_batch_id == batch.id)
            ).scalars()
        ]
    member = new_client(unique("member"))
    member.post("/modules/select", data={"module_code": "305", "action": "add"})
    assert member.post(f"/groups/{gid}/join").status_code == 303
    # not enabled yet
    assert member.get(f"/question/{qids[0]}").status_code == 404
    page = sup.get("/admin/extra").text
    assert doc["source"] in page and "nicht geklärt" in page
    assert sup.post(f"/admin/extra/{gid}", data={"batch": [batch.id]}).status_code == 303
    with session_scope() as db:
        assert db.execute(
            select(GroupSource).where(GroupSource.group_id == gid, GroupSource.batch_id == batch.id)
        ).scalar_one()
    assert member.get(f"/question/{qids[0]}").status_code == 200
    html = member.get("/module/305").text
    assert "Zusatzfragen" in html and doc["source"] in html and "Nur Zusatzfragen üben" in html
    # practice restricted to the pool returns one of the supplementary questions, tagged
    seen = set()
    for _ in range(6):
        h = member.get("/learn/305?pool=extra").text
        assert "Zusatzfrage" in h and doc["source"] in h
        seen.add(int(re.search(r'name="question_id" value="(\d+)"', h).group(1)))
    assert seen <= set(qids)
    h = member.get("/learn/305?pool=core").text
    assert int(re.search(r'name="question_id" value="(\d+)"', h).group(1)) not in qids
    assert member.get("/learn/305?pool=bogus").status_code == 400
    # outsiders still do not see it
    outsider = new_client(unique("out"))
    assert outsider.get(f"/question/{qids[0]}").status_code == 404
    # disabling removes access again
    assert sup.post(f"/admin/extra/{gid}", data={}).status_code == 303
    assert member.get(f"/question/{qids[0]}").status_code == 404


def test_supervisor_cannot_enable_for_foreign_group(client, admin):
    sup, _ = _make_supervisor(admin)
    other = _make_group(admin, unique("Fremd "))
    with session_scope() as db:
        batch_id = (
            db.execute(select(ImportBatch.id).where(ImportBatch.supplementary.is_(True)))
            .scalars()
            .first()
        )
    assert sup.post(f"/admin/extra/{other}", data={"batch": [batch_id]}).status_code == 403
    learner = new_client(unique("nl"))
    assert learner.get("/admin/extra").status_code == 403


def test_web_import_requires_source_for_supplementary(client, admin):
    doc = _extra_doc("nosrc")
    doc.pop("source")
    doc.pop("supplementary")
    files = {"file": ("x.json", json.dumps(doc).encode(), "application/json")}
    r = admin.post(
        "/admin/import",
        data={"visibility": "private", "supplementary": "1", "source": ""},
        files=files,
    )
    assert r.status_code == 400 and "Quellenbezeichnung" in r.text


def test_cli_import_supplementary(tmp_path, data_dir):
    doc = _extra_doc("cli")
    doc.pop("supplementary")
    doc.pop("source")
    path = tmp_path / "extra-cli.json"
    path.write_text(json.dumps(doc))
    env = {"LPIC3_DATA_DIR": str(data_dir), "PATH": os.environ.get("PATH", "")}
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "import",
            str(path),
            "--supplementary",
            "--source",
            "CLI-Quelle 2026",
            "--rights",
            "unverified",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )
    assert r.returncode == 0, r.stderr
    with session_scope() as db:
        batch = db.execute(
            select(ImportBatch).where(ImportBatch.source == "CLI-Quelle 2026")
        ).scalar_one()
        assert batch.supplementary and batch.rights == "unverified"
        q = (
            db.execute(select(Question).where(Question.import_batch_id == batch.id))
            .scalars()
            .first()
        )
        assert q.supplementary


def test_reimport_keeps_supplementary_flag(client):
    doc = _extra_doc("re")
    with session_scope() as db:
        import_document(db, doc, filename="re.json", visibility="public")
        import_document(db, doc, filename="re.json", visibility="public")
        qs = (
            db.execute(select(Question).where(Question.external_id == doc["questions"][0]["id"]))
            .scalars()
            .all()
        )
        assert len(qs) == 1 and qs[0].supplementary
