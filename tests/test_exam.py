"""Exam simulation and entry test."""

from app.db import session_scope
from app.models import Exam, Question
from tests.conftest import new_client, unique


def _start(c, code, topic=None):
    url = f"/exam/{code}/start" + (f"?topic={topic}" if topic else "")
    r = c.get(url)
    assert r.status_code == 303, r.text
    return r.headers["location"]


def _answers_for(exam_url, correct_count):
    exam_id = int(exam_url.rsplit("/", 1)[1])
    with session_scope() as db:
        exam = db.get(Exam, exam_id)
        data = {}
        for i, qid in enumerate(exam.question_ids):
            q = db.get(Question, qid)
            if q.kind == "text":
                data[f"q{qid}_text"] = q.choices[0].text_en if i < correct_count else "wrong"
            elif i < correct_count:
                data[f"q{qid}"] = [c.id for c in q.choices if c.is_correct]
            else:
                wrong = [c for c in q.choices if not c.is_correct]
                data[f"q{qid}"] = wrong[0].id
        return exam_id, data, len(exam.question_ids)


def test_exam_has_no_language_help_and_timer(client, learner):
    learner.post("/modules/select", data={"module_code": "303", "action": "add"})
    url = _start(learner, "303")
    html = learner.get(url).text
    assert "data-timer" in html
    assert "Übersetzung anzeigen" not in html and "data-translation" not in html
    assert "data-terms" not in html
    assert html.count('class="card question-card"') == 12


def test_exam_submit_grades_and_history(client, learner):
    learner.post("/modules/select", data={"module_code": "303", "action": "add"})
    url = _start(learner, "303")
    exam_id, data, total = _answers_for(url, 9)
    r = learner.post(f"{url}/submit", data=data)
    assert r.status_code == 303 and r.headers["location"] == f"/exam/{exam_id}/result"
    result = learner.get(f"/exam/{exam_id}/result").text
    assert f"9 von {total} richtig (75 %)" in result
    assert "Das hätte gereicht" in result
    # resubmission is ignored
    assert learner.post(f"{url}/submit", data={}).headers["location"].endswith("/result")
    history = learner.get("/exams").text
    assert f"9/{total}" in history
    page = learner.get("/module/303").text
    assert "Beste Simulation" in learner.get("/").text or "75" in page


def test_topic_exam_uses_only_topic_questions(client, learner):
    learner.post("/modules/select", data={"module_code": "306", "action": "add"})
    url = _start(learner, "306", topic="364")
    exam_id = int(url.rsplit("/", 1)[1])
    with session_scope() as db:
        exam = db.get(Exam, exam_id)
        assert exam.topic.code == "364" and 0 < len(exam.question_ids) <= 5
        for qid in exam.question_ids:
            assert db.get(Question, qid).objective.code.startswith("364.")
    assert learner.get("/exam/306/start?topic=999").status_code == 404


def test_failed_exam_message(client, learner):
    learner.post("/modules/select", data={"module_code": "305", "action": "add"})
    url = _start(learner, "305")
    exam_id, data, total = _answers_for(url, 2)
    learner.post(f"{url}/submit", data=data)
    result = learner.get(f"/exam/{exam_id}/result").text
    assert "noch nicht gereicht" in result and f"2 von {total}" in result


def test_entry_test_stores_topic_scores(client, learner):
    learner.post("/modules/select", data={"module_code": "300", "action": "add"})
    assert "Eingangstest" in learner.get("/module/300").text
    r = learner.get("/entry/300/start")
    url = r.headers["location"]
    html = learner.get(url).text
    assert "Eingangstest" in html and "data-timer" not in html
    exam_id, data, total = _answers_for(url, total := 6)
    learner.post(f"{url}/submit", data=data)
    page = learner.get("/module/300").text
    assert "Eingangstest: 100 % richtig" in page and "sicher" in page
    assert 'href="/entry/300/start"' not in page


def test_exam_without_questions_redirects(client, admin):
    c = new_client(unique("noq"))
    r = c.get("/exam/303/start?topic=331")
    assert r.status_code == 303 and r.headers["location"].startswith("/exam/")
