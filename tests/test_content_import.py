"""Validation and import of content files."""

import copy
import json

import pytest
from sqlalchemy import func, select

from app.content import ContentError, content_files, import_document, load_json, validate
from app.db import session_scope
from app.models import Choice, Question, Term
from tests.conftest import PROJECT_DIR, new_client, unique

QUESTION_DOC = {
    "schema_version": 1,
    "kind": "questions",
    "module": "303",
    "license": "CC BY-SA 4.0",
    "questions": [
        {
            "id": "test-q-1",
            "objective": "331.1",
            "type": "single",
            "question": "Which tool signs a CSR?",
            "question_de": "Welches Werkzeug signiert einen CSR?",
            "choices": [{"text": "openssl ca", "correct": True}, {"text": "ssh-keygen"}],
            "explanation_de": "openssl ca signiert.",
            "terms": [{"term": "sign", "de": "signieren"}],
        },
        {
            "id": "test-q-2",
            "type": "multiple",
            "question": "Pick two true statements.",
            "choices": [
                {"text": "A", "correct": True},
                {"text": "B", "correct": True},
                {"text": "C"},
            ],
        },
    ],
}


def test_bundled_content_files_are_valid():
    files = content_files(PROJECT_DIR / "content")
    assert len(files) >= 13
    for path in files:
        assert validate(load_json(path)) == [], path.name


def test_bundled_objectives_weights_sum_to_60():
    for path in (PROJECT_DIR / "content" / "objectives").glob("*.json"):
        data = load_json(path)
        assert sum(o["weight"] for t in data["topics"] for o in t["objectives"]) == 60, path.name


def test_envelope_errors():
    assert "schema_version" in validate({"kind": "questions"})[0]
    assert "kind" in validate({"schema_version": 1, "kind": "foo"})[0]


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (
            lambda d: d["questions"][0].__setitem__("choices", [{"text": "A", "correct": True}]),
            "2 to 6",
        ),
        (lambda d: d["questions"][0]["choices"][0].__setitem__("correct", False), "exactly one"),
        (lambda d: d["questions"][1]["choices"][1].__setitem__("correct", False), "at least two"),
        (lambda d: d["questions"][0].__setitem__("id", "bad id!"), "'id'"),
        (lambda d: d["questions"][1].__setitem__("id", "test-q-1"), "duplicate"),
        (lambda d: d["questions"][0].__setitem__("objective", "9"), "'objective'"),
        (lambda d: d["questions"][0].__setitem__("question", ""), "'question'"),
        (lambda d: d["questions"][0].__setitem__("difficulty", 7), "'difficulty'"),
        (lambda d: d.__setitem__("module", "30x"), "'module'"),
        (lambda d: d.__setitem__("questions", []), "'questions'"),
        (lambda d: d["questions"][0].__setitem__("terms", [{"term": "x"}]), "'de'"),
    ],
)
def test_question_validation_errors(mutate, fragment):
    doc = copy.deepcopy(QUESTION_DOC)
    mutate(doc)
    errors = validate(doc)
    assert errors and any(fragment in e for e in errors), errors


def test_invalid_file_is_rejected_completely(client):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["questions"][1]["choices"] = [{"text": "only one"}]
    with session_scope() as db:
        before = db.execute(select(func.count(Question.id))).scalar_one()
        with pytest.raises(ContentError) as exc:
            import_document(db, doc, filename="bad.json")
        assert exc.value.errors
        after = db.execute(select(func.count(Question.id))).scalar_one()
    assert before == after


def test_unknown_objective_rejected(client):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["questions"][0]["objective"] = "999.9"
    with session_scope() as db:
        with pytest.raises(ContentError):
            import_document(db, doc, filename="bad.json")


def test_import_and_reimport_updates_in_place(client):
    doc = copy.deepcopy(QUESTION_DOC)
    with session_scope() as db:
        result = import_document(db, doc, filename="t.json", visibility="private")
        assert result.created == 2 and result.updated == 0
        q = db.execute(select(Question).where(Question.external_id == "test-q-1")).scalar_one()
        qid = q.id
        assert q.visibility == "private" and len(q.choices) == 2 and q.objective.code == "331.1"
        term = db.execute(select(Term).where(Term.term == "sign")).scalar_one()
        assert term.translation_de == "signieren"
    doc["questions"][0]["question"] = "Which tool signs a CSR? (updated)"
    doc["questions"][0]["choices"].append({"text": "gpg"})
    with session_scope() as db:
        result = import_document(db, doc, filename="t.json", visibility="private")
        assert result.created == 0 and result.updated == 2
        q = db.execute(select(Question).where(Question.external_id == "test-q-1")).scalar_one()
        assert q.id == qid and q.text_en.endswith("(updated)") and len(q.choices) == 3
        orphan = db.execute(
            select(func.count(Choice.id)).where(Choice.question_id == qid)
        ).scalar_one()
        assert orphan == 3


def test_import_via_web_upload_and_visibility(client, admin):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["questions"][0]["id"] = unique("web-q-")
    doc["questions"][1]["id"] = unique("web-q-")
    files = {"file": ("upload.json", json.dumps(doc).encode(), "application/json")}
    r = admin.post("/admin/import", data={"visibility": "private"}, files=files)
    assert r.status_code == 303
    page = admin.get("/admin/import").text
    assert "upload.json" in page
    # a learner must not see private questions of the admin
    learner = new_client(unique("imp"))
    learner.post("/modules/select", data={"module_code": "303", "action": "add"})
    r = learner.get(f"/admin/questions?q={doc['questions'][0]['id']}")
    assert r.status_code == 403
    with session_scope() as db:
        q = db.execute(
            select(Question).where(Question.external_id == doc["questions"][0]["id"])
        ).scalar_one()
        private_id = q.id
    assert learner.get(f"/question/{private_id}").status_code == 404
    assert admin.get(f"/question/{private_id}").status_code == 200


def test_web_upload_rejects_invalid_file(client, admin):
    files = {"file": ("broken.json", b"{not json", "application/json")}
    r = admin.post("/admin/import", data={"visibility": "private"}, files=files)
    assert r.status_code == 400 and "abgelehnt" in r.text


def test_imported_text_is_escaped(client, admin):
    doc = copy.deepcopy(QUESTION_DOC)
    qid = unique("xss-q-")
    doc["questions"] = [
        {
            "id": qid,
            "type": "single",
            "question": "<script>alert(1)</script> which?",
            "choices": [{"text": "<b>bold</b>", "correct": True}, {"text": "x"}],
            "explanation_de": "<img src=x onerror=alert(1)>",
        }
    ]
    files = {"file": ("xss.json", json.dumps(doc).encode(), "application/json")}
    assert (
        admin.post("/admin/import", data={"visibility": "public"}, files=files).status_code == 303
    )
    with session_scope() as db:
        q = db.execute(select(Question).where(Question.external_id == qid)).scalar_one()
        db_id = q.id
    html = admin.get(f"/question/{db_id}").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>bold</b>" not in html and "&lt;b&gt;bold" in html
    assert "<img" not in html and "&lt;img src=x onerror=alert(1)&gt;" in html


def test_cli_validate_and_import(tmp_path, data_dir):
    import subprocess
    import sys

    doc = copy.deepcopy(QUESTION_DOC)
    path = tmp_path / "cli.json"
    path.write_text(json.dumps(doc))
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    env = {"LPIC3_DATA_DIR": str(data_dir), "PATH": "/usr/bin:/bin"}
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "validate", str(path), str(bad)],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )
    assert r.returncode == 1 and "gültig" in r.stdout and "bad.json" in r.stderr
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "import", str(path), "--visibility", "private"],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )
    assert r.returncode == 0, r.stderr
    assert "aktualisiert" in r.stdout


def test_delete_batch_removes_questions(client, admin):
    doc = copy.deepcopy(QUESTION_DOC)
    doc["questions"] = [doc["questions"][0] | {"id": unique("del-q-")}]
    files = {"file": ("del.json", json.dumps(doc).encode(), "application/json")}
    assert (
        admin.post("/admin/import", data={"visibility": "private"}, files=files).status_code == 303
    )
    with session_scope() as db:
        q = db.execute(
            select(Question).where(Question.external_id == doc["questions"][0]["id"])
        ).scalar_one()
        batch_id = q.import_batch_id
    assert admin.post(f"/admin/batches/{batch_id}/delete").status_code == 303
    with session_scope() as db:
        assert (
            db.execute(
                select(Question).where(Question.external_id == doc["questions"][0]["id"])
            ).scalar_one_or_none()
            is None
        )
