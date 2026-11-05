"""Lab didactics (work package 2): status flow, instructor notes, group view, environment guide."""

import re

from tests.conftest import new_client, unique


def _first_lab_id(client) -> int:
    r = client.get("/labs")
    assert r.status_code == 200
    return int(re.search(r'href="/lab/(\d+)"', r.text).group(1))


def test_lab_detail_shows_didactic_sections_and_practice_link(learner):
    lab_id = _first_lab_id(learner)
    html = learner.get(f"/lab/{lab_id}").text
    for heading in (
        "Lernziel",
        "Prüfungsziel",
        "Voraussetzungen",
        "Aufgabe",
        "Werkzeuge und Dokumentation",
        "Erfolgskriterien",
        "Hilfestellung",
        "Selbstkontrolle",
        "Typische Fehler",
    ):
        assert heading in html, heading
    assert "Fragen zu diesem Prüfungsziel üben" in html
    assert re.search(r'href="/learn/\d{3}\?objective=\d{3}\.\d"', html)
    # the full command sequences stay available, but collapsed as hints
    assert '<details class="hint">' in html
    assert "kein verpflichtender Weg" in html
    # instructor notes are not shown to learners
    assert "Hinweise für Dozenten" not in html


def test_instructor_notes_only_for_supervisors_and_admins(learner, admin):
    lab_id = _first_lab_id(learner)
    assert "Hinweise für Dozenten" not in learner.get(f"/lab/{lab_id}").text
    assert "Hinweise für Dozenten" in admin.get(f"/lab/{lab_id}").text
    sup = new_client(unique("sup"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    assert "Hinweise für Dozenten" in sup.get(f"/lab/{lab_id}").text


def test_lab_status_flow_not_started_started_completed(learner):
    lab_id = _first_lab_id(learner)
    assert "nicht begonnen" in learner.get(f"/lab/{lab_id}").text
    assert learner.post(f"/lab/{lab_id}/start").status_code == 303
    html = learner.get(f"/lab/{lab_id}").text
    assert "in Bearbeitung seit" in html and "Als abgeschlossen markieren" in html
    me = learner.get("/api/me").json()
    assert learner.post(f"/lab/{lab_id}/complete").status_code == 303
    html = learner.get(f"/lab/{lab_id}").text
    assert "abgeschlossen am" in html
    # back to started keeps the row but clears the completion
    assert learner.post(f"/lab/{lab_id}/start").status_code == 303
    assert "in Bearbeitung seit" in learner.get(f"/lab/{lab_id}").text
    assert learner.post(f"/lab/{lab_id}/reset").status_code == 303
    assert "nicht begonnen" in learner.get(f"/lab/{lab_id}").text
    assert learner.post("/lab/99999/start").status_code == 404
    assert me["role"] == "learner"


def test_only_completed_labs_count_in_progress(learner):
    lab_id = _first_lab_id(learner)
    page = learner.get(f"/lab/{lab_id}").text
    module = re.search(r'href="/module/(\d{3})"', page).group(1)
    learner.post("/modules/select", data={"module_code": module, "action": "add"})

    def labs_done() -> int:
        html = learner.get("/progress").text
        m = re.search(r"<strong>(\d+)</strong>/\d+ Labs", html)
        return int(m.group(1))

    learner.post(f"/lab/{lab_id}/start")
    assert labs_done() == 0
    learner.post(f"/lab/{lab_id}/complete")
    assert labs_done() == 1
    learner.post(f"/lab/{lab_id}/reset")
    assert labs_done() == 0


def test_environment_guide_is_rendered_as_own_learning_area(learner):
    r = learner.get("/labs/umgebung")
    assert r.status_code == 200
    assert "LAB-Umgebung einrichten" in r.text
    assert "KVM/QEMU" in r.text and "Snapshot" in r.text
    assert "<h2" in r.text and "<pre><code>" in r.text and "<table" in r.text
    # the labs list links to the guide
    assert 'href="/labs/umgebung"' in learner.get("/labs").text


def test_group_lab_overview_and_recommendations(admin):
    sup = new_client(unique("sup"))
    sup_id = sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{sup_id}/role", data={"role": "supervisor"})
    member = new_client(unique("member"))
    member_id = member.get("/api/me").json()["id"]
    other_sup = new_client(unique("othersup"))
    other_id = other_sup.get("/api/me").json()["id"]
    admin.post(f"/admin/users/{other_id}/role", data={"role": "supervisor"})

    r = sup.post(
        "/admin/groups", data={"name": unique("labgroup"), "description": "", "join_mode": "open"}
    )
    group_id = int(r.headers["location"].rsplit("/", 1)[1])
    assert (
        sup.post(
            f"/admin/groups/{group_id}/members", data={"user_id": member_id, "role": "member"}
        ).status_code
        == 303
    )

    lab_id = _first_lab_id(member)
    member.post(f"/lab/{lab_id}/start")
    html = sup.get(f"/admin/groups/{group_id}").text
    assert "LAB-Stände der Gruppe" in html
    row = re.search(rf'value="{lab_id}"[^\n]*\n[^\n]*\n(.*?)</tr>', html, re.S).group(1)
    assert '1<span class="names">' in row  # one member in exactly one state column
    member.post(f"/lab/{lab_id}/complete")
    html = sup.get(f"/admin/groups/{group_id}").text
    assert "1 abgeschlossen, 0 in Bearbeitung" in html

    # recommend the lab: the member sees it, a non-member does not
    assert (
        sup.post(f"/admin/groups/{group_id}/labs", data={"lab_ids": [str(lab_id)]}).status_code
        == 303
    )
    assert "empfohlen · " in member.get("/labs").text
    assert "empfohlen in " in member.get(f"/lab/{lab_id}").text
    stranger = new_client(unique("stranger"))
    assert "empfohlen · " not in stranger.get("/labs").text
    # clearing the recommendations removes the tag
    assert sup.post(f"/admin/groups/{group_id}/labs", data={}).status_code == 303
    assert "empfohlen · " not in member.get("/labs").text

    # a supervisor of another group sees nothing of this group (server-side)
    assert other_sup.get(f"/admin/groups/{group_id}").status_code == 403
    assert (
        other_sup.post(
            f"/admin/groups/{group_id}/labs", data={"lab_ids": [str(lab_id)]}
        ).status_code
        == 403
    )
    # learners cannot touch recommendations at all
    assert member.post(f"/admin/groups/{group_id}/labs", data={}).status_code == 403


def test_lab_content_validation_of_didactic_fields():
    from app.content import validate

    doc = {
        "schema_version": 1,
        "kind": "labs",
        "module": "303",
        "labs": [
            {
                "id": "lab-test-1",
                "objective": "331.1",
                "title": "T",
                "goal_de": "G",
                "task_de": "A",
                "tools_de": ["man openssl"],
                "success_criteria_de": ["ok"],
                "pitfalls_de": ["p"],
                "instructor_notes_de": ["n"],
                "steps": [{"title": "S", "text_de": "x", "commands": ["ls"], "warning_de": "w"}],
            }
        ],
    }
    assert validate(doc) == []
    bad = dict(doc)
    bad["labs"] = [dict(doc["labs"][0], tools_de="man openssl")]
    assert any("tools_de" in e for e in validate(bad))
    bad["labs"] = [dict(doc["labs"][0], success_criteria_de=[""])]
    assert any("success_criteria_de" in e for e in validate(bad))
    bad["labs"] = [dict(doc["labs"][0], steps=[{"title": "S", "text_de": "x", "warning_de": 5}])]
    assert any("warning_de" in e for e in validate(bad))


def test_bundled_labs_have_complete_didactics():
    """Every bundled lab carries the fields the didactic concept requires."""
    import json
    from pathlib import Path

    from app.config import PROJECT_DIR

    labs = []
    for path in sorted((PROJECT_DIR / "content" / "labs").glob("*-labs.json")):
        labs += json.loads(Path(path).read_text(encoding="utf-8"))["labs"]
    assert len(labs) == 12
    for lab in labs:
        assert lab["objective"], lab["id"]
        for key in ("goal_de", "task_de", "environment_de"):
            assert lab[key].strip(), (lab["id"], key)
        for key in ("tools_de", "success_criteria_de", "pitfalls_de", "instructor_notes_de"):
            assert len(lab[key]) >= 3, (lab["id"], key)
        assert lab["duration_minutes"] >= 5
        assert lab["checks"], lab["id"]
        # destructive commands carry a warning
        joined = "\n".join(c for s in lab["steps"] for c in s.get("commands", []))
        for marker in ("luksFormat", "mdadm --create", "create-md", "--remove-all-storage"):
            if marker in joined:
                assert any(
                    marker in "\n".join(s.get("commands", [])) and s.get("warning_de")
                    for s in lab["steps"]
                ), (lab["id"], marker)
