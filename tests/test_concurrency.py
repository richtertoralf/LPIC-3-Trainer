"""Several users answer questions at the same time (SQLite WAL, busy timeout)."""

import re
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.db import session_scope
from app.models import Attempt, Question
from tests.conftest import new_client, unique


def _worker(index: int) -> int:
    c = new_client(unique(f"conc{index}_"))
    c.post("/modules/select", data={"module_code": "303", "action": "add"})
    answered = 0
    for _ in range(8):
        html = c.get("/learn/303").text
        qid = int(re.search(r'name="question_id" value="(\d+)"', html).group(1))
        with session_scope() as db:
            q = db.get(Question, qid)
            choice = q.choices[0].id
        r = c.post("/learn/303/answer", data={"question_id": qid, "choice": choice})
        assert r.status_code == 200
        answered += 1
    return answered


def test_parallel_users(client, admin):
    with session_scope() as db:
        before = db.execute(select(func.count(Attempt.id))).scalar_one()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_worker, range(8)))
    assert results == [8] * 8
    with session_scope() as db:
        after = db.execute(select(func.count(Attempt.id))).scalar_one()
    assert after - before == 64
