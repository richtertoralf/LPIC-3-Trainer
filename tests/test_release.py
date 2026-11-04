"""Import permissions and the release workflow for external question pools.

Rules: only administrators and supervisors import; every import stays unreleased;
supervisors release their own imports for their own groups; administrators release
system-wide; learners see only the released pool and their groups' releases.
"""

import copy
import json
import os
import re
import subprocess
import sys

from sqlalchemy import select

from app.content import validate
from app.db import session_scope
from app.models import GroupSource, ImportBatch, Question
from tests.conftest import PROJECT_DIR, new_client, unique
from tests.test_content_import import QUESTION_DOC

EXTRA_FILES = sorted((PROJECT_DIR / "content" / "questions" / "extra").glob("*.json"))


def _doc(prefix: str, module: str = "305") -> dict:
    doc = copy.deepcopy(QUESTION_DOC)
    doc["module"] = module
    for q in doc["questions"]:
        q.pop("objective", None)
    doc["questions"][0]["id"] = unique(f"{prefix}-a-")
    doc["questions"][1]["id"] = unique(f"{prefix}-b-")
    doc["source"] = f"Quelle {prefix}"
    doc["exam_version"] = "3.0"
    return doc


def _upload(client, doc, **form):
    files = {"file": ("fragen.json", json.dumps(doc).encode(), "application/json")}
    return client.post("/admin/import", data=form, files=files)


def _batch_and_ids(source):
    with session_scope() as db:
        batch = db.execute(select(ImportBatch).where(ImportBatch.source == source)).scalar_one()
        ids = [
            q.id
            for q in db.execute(
                select(Question).where(Question.import_batch_id == batch.id)
            ).scalars()
        ]
        return batch.id, ids


def _supervisor(admin):
    sup = new_client(unique("rsup"))
    sup_id = sup.get("/api/me").json()["id"]
    assert admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"}).status_code == 303
    return sup, sup_id


def _group(client, name, join_mode="open"):
    r = client.post("/admin/groups", data={"name": name, "join_mode": join_mode})
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[1])


# ------------------------------------------------------------------ permissions


def test_learners_cannot_import_create_or_release(client, admin):
    learner = new_client(unique("rl"))
    doc = _doc("learner")
    assert _upload(learner, doc).status_code == 403
    assert learner.get("/admin/import").status_code == 403
    assert learner.get("/admin/releases").status_code == 403
    assert learner.post("/admin/releases/group/1", data={}).status_code == 403
    assert learner.post("/admin/releases/1/global", data={"released": "1"}).status_code == 403
    assert learner.post("/admin/questions/1/toggle").status_code == 403
    assert learner.post("/admin/batches/1/delete").status_code == 403


def test_source_and_exam_version_are_required():
    doc = _doc("req")
    assert validate(doc) == []
    bad = copy.deepcopy(doc)
    bad.pop("source")
    assert any("'source'" in e for e in validate(bad))
    bad = copy.deepcopy(doc)
    bad["exam_version"] = "latest"
    assert any("exam_version" in e for e in validate(bad))


def test_web_import_requires_origin(client, admin):
    doc = _doc("noorigin")
    doc.pop("source")
    doc.pop("exam_version")
    r = _upload(admin, doc, source="", exam_version="")
    assert r.status_code == 400 and "source" in r.text and "exam_version" in r.text
    r = _upload(admin, doc, source="Formularquelle", exam_version="3.0")
    assert r.status_code == 303
    with session_scope() as db:
        batch = db.execute(
            select(ImportBatch).where(ImportBatch.source == "Formularquelle")
        ).scalar_one()
        assert batch.exam_version == "3.0" and batch.supplementary and not batch.released


# ---------------------------------------------------------------- release flow


def test_import_stays_unreleased_until_released(client, admin):
    doc = _doc("unrel")
    assert _upload(admin, doc, exam_version="3.0").status_code == 303
    batch_id, ids = _batch_and_ids(doc["source"])
    learner = new_client(unique("rlearn"))
    learner.post("/modules/select", data={"module_code": "305", "action": "add"})
    for qid in ids:
        assert learner.get(f"/question/{qid}").status_code == 404
        assert admin.get(f"/question/{qid}").status_code == 200  # importer and admin
    # administrator releases system-wide
    assert (
        admin.post(f"/admin/releases/{batch_id}/global", data={"released": "1"}).status_code == 303
    )
    for qid in ids:
        html = learner.get(f"/question/{qid}")
        assert html.status_code == 200 and "Zusatzfrage" in html.text and doc["source"] in html.text
    assert "Prüfungsgeneration 3.0" in learner.get(f"/question/{ids[0]}").text
    # and withdraws it again
    assert (
        admin.post(f"/admin/releases/{batch_id}/global", data={"released": "0"}).status_code == 303
    )
    assert learner.get(f"/question/{ids[0]}").status_code == 404


def test_supervisor_releases_own_import_for_own_group(client, admin):
    sup, sup_id = _supervisor(admin)
    gid = _group(sup, unique("Kurs R "))
    doc = _doc("supown")
    assert _upload(sup, doc, rights="unverified").status_code == 303
    batch_id, ids = _batch_and_ids(doc["source"])
    member = new_client(unique("rmem"))
    member.post("/modules/select", data={"module_code": "305", "action": "add"})
    assert member.post(f"/groups/{gid}/join").status_code == 303
    assert member.get(f"/question/{ids[0]}").status_code == 404
    page = sup.get("/admin/releases").text
    assert doc["source"] in page and "Systemweit freigeben" not in page  # no global button
    assert sup.post(f"/admin/releases/group/{gid}", data={"batch": [batch_id]}).status_code == 303
    with session_scope() as db:
        assert (
            db.execute(
                select(GroupSource).where(
                    GroupSource.group_id == gid, GroupSource.batch_id == batch_id
                )
            ).scalar_one_or_none()
            is not None
        )
    assert member.get(f"/question/{ids[0]}").status_code == 200
    html = member.get("/module/305").text
    assert "Zusatzfragen" in html and doc["source"] in html
    seen = set()
    for _ in range(6):
        h = member.get("/learn/305?pool=extra").text
        assert "Zusatzfrage" in h
        seen.add(int(re.search(r'name="question_id" value="(\d+)"', h).group(1)))
    assert seen <= set(ids)
    h = member.get("/learn/305?pool=core").text
    assert int(re.search(r'name="question_id" value="(\d+)"', h).group(1)) not in ids
    outsider = new_client(unique("rout"))
    assert outsider.get(f"/question/{ids[0]}").status_code == 404
    # supervisors cannot release system-wide
    assert sup.post(f"/admin/releases/{batch_id}/global", data={"released": "1"}).status_code == 403
    assert outsider.get(f"/question/{ids[0]}").status_code == 404
    # withdrawing the group release hides the questions again
    assert sup.post(f"/admin/releases/group/{gid}", data={}).status_code == 303
    assert member.get(f"/question/{ids[0]}").status_code == 404


def test_supervisor_cannot_release_foreign_imports_or_groups(client, admin):
    sup_a, _ = _supervisor(admin)
    sup_b, _ = _supervisor(admin)
    gid_a = _group(sup_a, unique("Kurs A "))
    gid_b = _group(sup_b, unique("Kurs B "))
    doc = _doc("foreign")
    assert _upload(sup_b, doc).status_code == 303
    batch_id, ids = _batch_and_ids(doc["source"])
    # A does not even see B's import on the release page
    assert doc["source"] not in sup_a.get("/admin/releases").text
    # A cannot enable B's import for A's group (silently ignored)
    assert (
        sup_a.post(f"/admin/releases/group/{gid_a}", data={"batch": [batch_id]}).status_code == 303
    )
    with session_scope() as db:
        assert (
            db.execute(select(GroupSource).where(GroupSource.batch_id == batch_id)).first() is None
        )
    # B cannot touch A's group at all
    assert (
        sup_b.post(f"/admin/releases/group/{gid_a}", data={"batch": [batch_id]}).status_code == 403
    )
    # the administrator may release any import for any group
    assert (
        admin.post(f"/admin/releases/group/{gid_b}", data={"batch": [batch_id]}).status_code == 303
    )
    assert (
        admin.post(f"/admin/releases/group/{gid_a}", data={"batch": [batch_id]}).status_code == 303
    )
    member_a = new_client(unique("ma"))
    member_a.post(f"/groups/{gid_a}/join")
    assert member_a.get(f"/question/{ids[0]}").status_code == 200


def test_bundled_core_pool_is_released_and_extra_sources_are_not(client, admin):
    learner = new_client(unique("core"))
    with session_scope() as db:
        core = (
            db.execute(
                select(ImportBatch).where(
                    ImportBatch.bundled.is_(True),
                    ImportBatch.supplementary.is_(False),
                    ImportBatch.kind == "questions",
                )
            )
            .scalars()
            .all()
        )
        assert core and all(b.released and b.exam_version == "3.0" and b.source for b in core)
        extra = (
            db.execute(
                select(ImportBatch).where(
                    ImportBatch.bundled.is_(True), ImportBatch.supplementary.is_(True)
                )
            )
            .scalars()
            .all()
        )
        assert len(extra) == len(EXTRA_FILES) and all(not b.released for b in extra)
        assert all(
            b.rights in ("unverified", "cleared") and b.source and b.exam_version for b in extra
        )
        assert any(b.rights == "unverified" for b in extra)
        core_q = (
            db.execute(select(Question).where(Question.import_batch_id == core[0].id))
            .scalars()
            .first()
        )
        extra_q = (
            db.execute(select(Question).where(Question.import_batch_id == extra[0].id))
            .scalars()
            .first()
        )
    assert learner.get(f"/question/{core_q.id}").status_code == 200
    assert learner.get(f"/question/{extra_q.id}").status_code == 404


def test_every_question_has_source_and_exam_version(client):
    with session_scope() as db:
        rows = (
            db.execute(select(ImportBatch).where(ImportBatch.kind == "questions")).scalars().all()
        )
        assert rows and all(b.source and b.exam_version for b in rows)
        orphan = db.execute(select(Question).where(Question.import_batch_id.is_(None))).first()
        assert orphan is None


def test_cli_import_is_unreleased_and_needs_origin(tmp_path, data_dir):
    doc = _doc("cli")
    doc.pop("source")
    path = tmp_path / "cli.json"
    path.write_text(json.dumps(doc))
    env = {"LPIC3_DATA_DIR": str(data_dir), "PATH": os.environ.get("PATH", "")}
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "import", str(path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )
    assert r.returncode == 1 and "source" in r.stderr
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "import",
            str(path),
            "--source",
            "CLI-Quelle",
            "--exam-version",
            "3.0",
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
            select(ImportBatch).where(ImportBatch.source == "CLI-Quelle")
        ).scalar_one()
        assert batch.supplementary and not batch.released and batch.exam_version == "3.0"
