"""Practice mode, language help, vocabulary, labs and progress."""

import re

from sqlalchemy import select

from app.db import session_scope
from app.models import Attempt, Question, UserTerm
from tests.conftest import new_client, unique


def _question_id(html: str) -> int:
    return int(re.search(r'name="question_id" value="(\d+)"', html).group(1))


def _correct_choice_ids(qid: int) -> set[int]:
    with session_scope() as db:
        q = db.get(Question, qid)
        return {c.id for c in q.choices if c.is_correct}


def _all_choice_ids(qid: int) -> set[int]:
    with session_scope() as db:
        q = db.get(Question, qid)
        return {c.id for c in q.choices}


def test_module_selection_and_dashboard(client, learner):
    r = learner.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/modules"
    assert (
        learner.post("/modules/select", data={"module_code": "305", "action": "add"}).status_code
        == 303
    )
    r = learner.get("/")
    assert r.status_code == 200 and "305" in r.text
    assert (
        learner.post("/modules/select", data={"module_code": "305", "action": "remove"}).status_code
        == 303
    )
    assert learner.get("/").status_code == 303
    assert (
        learner.post("/modules/select", data={"module_code": "999", "action": "add"}).status_code
        == 404
    )


def test_practice_question_is_english_with_german_help(client, learner):
    learner.post("/modules/select", data={"module_code": "303", "action": "add"})
    r = learner.get("/learn/303?objective=331.1")
    assert r.status_code == 200
    assert "Übersetzung anzeigen" in r.text and "Fachbegriffe markieren" in r.text
    assert "data-terms=" in r.text
    assert "data-translation" in r.text


def test_answer_correct_and_wrong_recorded_with_help_flag(client, learner):
    learner.post("/modules/select", data={"module_code": "303", "action": "add"})
    html = learner.get("/learn/303").text
    qid = _question_id(html)
    correct = _correct_choice_ids(qid)
    data = {"question_id": qid, "used_help": "1", "choice": list(correct)}
    r = learner.post("/learn/303/answer", data=data)
    assert r.status_code == 200 and "Richtig!" in r.text and "Sprachhilfe genutzt" in r.text
    assert "Erklärung" in r.text
    wrong = list(_all_choice_ids(qid) - correct)[:1]
    r = learner.post(
        "/learn/303/answer", data={"question_id": qid, "used_help": "0", "choice": wrong[0]}
    )
    assert r.status_code == 200 and "Leider falsch" in r.text
    with session_scope() as db:
        rows = (
            db.execute(select(Attempt).where(Attempt.question_id == qid).order_by(Attempt.id))
            .scalars()
            .all()
        )
        mine = [a for a in rows if a.mode == "practice"][-2:]
        assert [a.is_correct for a in mine] == [True, False]
        assert [a.used_help for a in mine] == [True, False]


def test_multiple_choice_needs_all_correct(client, learner):
    with session_scope() as db:
        q = (
            db.execute(
                select(Question).where(Question.kind == "multiple", Question.visibility == "public")
            )
            .scalars()
            .first()
        )
        qid, code = q.id, q.module.code
        correct = {c.id for c in q.choices if c.is_correct}
    learner.post("/modules/select", data={"module_code": code, "action": "add"})
    partial = list(correct)[:1]
    r = learner.post(f"/learn/{code}/answer", data={"question_id": qid, "choice": partial[0]})
    assert "Leider falsch" in r.text
    r = learner.post(f"/learn/{code}/answer", data={"question_id": qid, "choice": list(correct)})
    assert "Richtig!" in r.text


def test_answer_invalid_question_rejected(client, learner):
    assert learner.post("/learn/303/answer", data={"question_id": "abc"}).status_code == 400
    assert learner.post("/learn/303/answer", data={"question_id": "999999"}).status_code == 404


def test_question_terms_api_and_vocabulary_flow(client, learner):
    learner.post("/modules/select", data={"module_code": "306", "action": "add"})
    qid = _question_id(learner.get("/learn/306").text)
    r = learner.get(f"/api/questions/{qid}/terms")
    assert r.status_code == 200
    terms = r.json()["terms"]
    assert terms, "every bundled question should match at least one glossary term"
    tid = terms[0]["id"]
    r = learner.post(f"/api/terms/{tid}/learn")
    assert r.status_code == 200 and r.json()["status"] == "learning"
    page = learner.get("/vocab").text
    assert terms[0]["term"] in page
    r = learner.get("/vocab/review")
    assert r.status_code == 200 and terms[0]["term"] in r.text
    assert (
        learner.post(f"/vocab/{tid}/status", data={"status": "known", "next": "/vocab"}).status_code
        == 303
    )
    with session_scope() as db:
        row = db.execute(select(UserTerm).where(UserTerm.term_id == tid)).scalars().all()
        assert any(r.status == "known" for r in row)
    r = learner.get("/vocab/review")
    assert r.status_code == 303  # nothing left to review
    assert learner.post(f"/vocab/{tid}/status", data={"status": "bogus"}).status_code == 400


def test_glossary_search(client, learner):
    r = learner.get("/glossary?q=quorum")
    assert r.status_code == 200 and "Quorum" in r.text and "merken" in r.text


def test_labs_listing_detail_and_completion(client, learner):
    r = learner.get("/labs")
    assert r.status_code == 200
    lab_id = int(re.search(r'href="/lab/(\d+)"', r.text).group(1))
    r = learner.get(f"/lab/{lab_id}")
    assert r.status_code == 200 and "Selbstkontrolle" in r.text and "<pre>" in r.text
    assert learner.post(f"/lab/{lab_id}/complete").status_code == 303
    assert "abgeschlossen am" in learner.get(f"/lab/{lab_id}").text
    assert learner.post(f"/lab/{lab_id}/reset").status_code == 303
    assert "abgeschlossen am" not in learner.get(f"/lab/{lab_id}").text
    assert learner.get("/lab/99999").status_code == 404


def test_progress_page_and_api(client, learner):
    learner.post("/modules/select", data={"module_code": "300", "action": "add"})
    qid = _question_id(learner.get("/learn/300").text)
    learner.post(
        "/learn/300/answer", data={"question_id": qid, "choice": list(_correct_choice_ids(qid))}
    )
    data = learner.get("/api/progress").json()["modules"]
    m = [x for x in data if x["module"] == "300"][0]
    assert m["answered"] == 1 and m["correct"] == 1 and m["questions"] > 30
    r = learner.get("/progress")
    assert r.status_code == 200 and "300" in r.text


def test_private_questions_visible_only_to_owner(client):
    import copy

    from app.content import import_document
    from tests.test_content_import import QUESTION_DOC

    owner = new_client(unique("owner"))
    other = new_client(unique("other"))
    uid = owner.get("/api/me").json()["id"]
    doc = copy.deepcopy(QUESTION_DOC)
    doc["module"] = "305"
    for q in doc["questions"]:
        q.pop("objective", None)
    doc["questions"][0]["id"] = unique("own-a-")
    doc["questions"][1]["id"] = unique("own-b-")
    with session_scope() as db:
        doc["source"] = unique("Ownerquelle ")
        import_document(db, doc, filename="o.json", imported_by=uid)
        ids = [
            q.id for q in db.execute(select(Question).where(Question.created_by == uid)).scalars()
        ]
    assert len(ids) == 2
    for qid in ids:
        assert owner.get(f"/question/{qid}").status_code == 200
        assert other.get(f"/question/{qid}").status_code == 404
    owner.post("/modules/select", data={"module_code": "305", "action": "add"})
    other.post("/modules/select", data={"module_code": "305", "action": "add"})
    mine = [m for m in owner.get("/api/progress").json()["modules"] if m["module"] == "305"][0]
    theirs = [m for m in other.get("/api/progress").json()["modules"] if m["module"] == "305"][0]
    assert mine["questions"] == theirs["questions"] + 2
