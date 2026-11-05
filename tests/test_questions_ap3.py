"""Work package 3: shuffled choices, multiple-choice feedback, fill-in-the-blank questions and
the per-objective group evaluation."""

import re

from sqlalchemy import select

from app.content import validate
from app.db import session_scope
from app.models import Exam, Question, utcnow
from app.services import display_choices, grade_submission, stored_answer_correct
from tests.conftest import new_client, unique

TEXT_DOC = {
    "schema_version": 1,
    "kind": "questions",
    "module": "303",
    "source": "Test",
    "exam_version": "3.0",
    "questions": [
        {
            "id": "t-text-1",
            "objective": "334.3",
            "type": "text",
            "question": "Which command lists the ruleset? ______",
            "answers": ["nft list ruleset", "sudo nft list ruleset"],
            "explanation_de": "x",
        }
    ],
}


def _text_question():
    with session_scope() as db:
        q = (
            db.execute(
                select(Question).where(Question.kind == "text", Question.visibility == "public")
            )
            .scalars()
            .first()
        )
        assert q is not None, "bundled content must contain a fill-in-the-blank example"
        return q.id, q.module.code, q.objective.topic.code, [c.text_en for c in q.choices]


def test_text_question_validation(client):
    assert validate(TEXT_DOC) == []
    doc = dict(TEXT_DOC)
    bad = dict(TEXT_DOC["questions"][0])
    bad.pop("answers")
    doc["questions"] = [bad]
    assert any("'answers'" in e for e in validate(doc))
    bad = dict(TEXT_DOC["questions"][0], choices=[{"text": "a", "correct": True}])
    doc["questions"] = [bad]
    assert any("not 'choices'" in e for e in validate(doc))
    bad = dict(TEXT_DOC["questions"][0], answers=["A", "a"], case_sensitive=False)
    doc["questions"] = [bad]
    assert any("duplicates" in e for e in validate(doc))
    bad = dict(TEXT_DOC["questions"][0], case_sensitive="yes")
    doc["questions"] = [bad]
    assert any("case_sensitive" in e for e in validate(doc))


def test_text_grading_is_literal_after_whitespace_normalisation(client):
    qid, code, _topic, answers = _text_question()
    with session_scope() as db:
        q = db.get(Question, qid)
        ok, stored = grade_submission(q, [f"  {answers[0].replace(' ', '   ')} "])
        assert ok and stored == [answers[0]]
        if q.case_sensitive:
            assert grade_submission(q, [answers[0].upper()])[0] is False
        assert grade_submission(q, [""])[0] is False
        assert grade_submission(q, [answers[0] + " --all"])[0] is False
        assert stored_answer_correct(q, [answers[0]]) is True
        assert stored_answer_correct(q, []) is False


def test_text_question_in_practice_mode(learner):
    qid, code, _topic, answers = _text_question()
    learner.post("/modules/select", data={"module_code": code, "action": "add"})
    html = learner.get(f"/question/{qid}").text
    assert 'type="text"' in html and "Lückentext" in html
    r = learner.post(f"/learn/{code}/answer", data={"question_id": qid, "choice_text": answers[0]})
    assert r.status_code == 200 and "Richtig!" in r.text
    assert "Akzeptierte Antwort" in r.text and answers[0] in r.text
    r = learner.post(
        f"/learn/{code}/answer", data={"question_id": qid, "choice_text": "something else"}
    )
    assert "Leider falsch" in r.text and 'value="something else"' in r.text
    r = learner.post(f"/learn/{code}/answer", data={"question_id": qid})
    assert "Leider falsch" in r.text


def test_text_question_in_exam_is_stored_and_graded(learner):
    qid, code, _topic, answers = _text_question()
    uid = learner.get("/api/me").json()["id"]
    with session_scope() as db:
        q = db.get(Question, qid)
        exam = Exam(
            user_id=uid,
            module_id=q.module_id,
            mode="exam",
            question_ids=[qid],
            duration_minutes=10,
            started_at=utcnow(),
        )
        db.add(exam)
        db.flush()
        exam_id = exam.id
    page = learner.get(f"/exam/{exam_id}").text
    assert f'name="q{qid}_text"' in page
    r = learner.post(f"/exam/{exam_id}/submit", data={f"q{qid}_text": answers[0] + "  "})
    assert r.status_code == 303
    result = learner.get(f"/exam/{exam_id}/result").text
    assert "1 von 1 richtig" in result and "Akzeptierte Antwort" in result
    with session_scope() as db:
        exam = db.get(Exam, exam_id)
        assert exam.answers == {str(qid): [answers[0]]}
        assert exam.correct_count == 1


def test_choices_are_shuffled_but_stable_per_seed(learner):
    with session_scope() as db:
        questions = list(
            db.execute(
                select(Question).where(Question.kind == "single", Question.visibility == "public")
            )
            .scalars()
            .fetchmany(60)
        )
        first_is_correct = 0
        for q in questions:
            shown = display_choices(q, "u1")
            assert sorted(c.id for c in shown) == sorted(c.id for c in q.choices)
            assert [c.id for c in shown] == [c.id for c in display_choices(q, "u1")]
            first_is_correct += int(shown[0].is_correct)
        # in the files the correct choice is almost always first; on screen it must not be
        assert 10 <= first_is_correct <= 50, first_is_correct
        # a different user sees a different order for at least some questions
        assert any(
            [c.id for c in display_choices(q, "u1")] != [c.id for c in display_choices(q, "u2")]
            for q in questions
        )
        qid, code, n_choices = questions[0].id, questions[0].module.code, len(questions[0].choices)
    # the question page and the result page use the same order for the same user
    learner.post("/modules/select", data={"module_code": code, "action": "add"})
    page = learner.get(f"/question/{qid}").text
    order_page = re.findall(r'name="choice" value="(\d+)"', page)
    assert len(order_page) == n_choices
    result = learner.post(
        f"/learn/{code}/answer", data={"question_id": qid, "choice": order_page[0]}
    ).text
    assert re.findall(r'name="choice" value="(\d+)"', result) == order_page


def test_multiple_choice_shows_count_and_partial_feedback(learner):
    with session_scope() as db:
        q = (
            db.execute(
                select(Question).where(Question.kind == "multiple", Question.visibility == "public")
            )
            .scalars()
            .first()
        )
        qid, code = q.id, q.module.code
        correct = sorted(c.id for c in q.choices if c.is_correct)
        wrong = [c.id for c in q.choices if not c.is_correct][0]
    learner.post("/modules/select", data={"module_code": code, "action": "add"})
    page = learner.get(f"/question/{qid}").text
    assert f"genau {len(correct)} Antworten sind richtig" in page
    r = learner.post(
        f"/learn/{code}/answer", data={"question_id": qid, "choice": [correct[0], wrong]}
    ).text
    assert "Leider falsch" in r
    assert f"1 von {len(correct)} richtigen Antworten gewählt, dazu 1 falsche" in r
    r = learner.post(f"/learn/{code}/answer", data={"question_id": qid, "choice": correct}).text
    assert "Richtig!" in r and "Teilweise richtig" not in r


def test_group_evaluation_per_objective(admin):
    sup = new_client(unique("evsup"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    member = new_client(unique("evmember"))
    member_id = member.get("/api/me").json()["id"]
    r = sup.post(
        "/admin/groups", data={"name": unique("evgroup"), "description": "", "join_mode": "open"}
    )
    group_id = int(r.headers["location"].rsplit("/", 1)[1])
    sup.post(f"/admin/groups/{group_id}/members", data={"user_id": member_id, "role": "member"})
    html = sup.get(f"/admin/groups/{group_id}/auswertung").text
    assert "Noch keine Antworten" in html

    with session_scope() as db:
        qs = list(
            db.execute(
                select(Question).where(
                    Question.kind == "single",
                    Question.visibility == "public",
                    Question.objective_id.is_not(None),
                )
            )
            .scalars()
            .fetchmany(3)
        )
        code = qs[0].module.code
        objective = qs[0].objective.code
        qid = qs[0].id
        wrong = [c.id for c in qs[0].choices if not c.is_correct][0]
    member.post("/modules/select", data={"module_code": code, "action": "add"})
    for _ in range(5):  # five wrong answers to the same question
        member.post(
            f"/learn/{code}/answer", data={"question_id": qid, "choice": wrong, "used_help": "1"}
        )
    html = sup.get(f"/admin/groups/{group_id}/auswertung").text
    assert f"?objective={objective}" in html
    assert "vertiefen" in html and "Häufig falsch beantwortete Fragen" in html
    assert "5 von 5 falsch" in html
    # other supervisors and learners get nothing
    other = new_client(unique("evother"))
    admin.post(
        f"/admin/users/{other.get('/api/me').json()['id']}/role", data={"role": "supervisor"}
    )
    assert other.get(f"/admin/groups/{group_id}/auswertung").status_code == 403
    assert member.get(f"/admin/groups/{group_id}/auswertung").status_code == 403
    # admins see every group
    assert admin.get(f"/admin/groups/{group_id}/auswertung").status_code == 200
