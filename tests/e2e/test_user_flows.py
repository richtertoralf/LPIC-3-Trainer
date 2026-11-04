"""Central user flows through the browser: registration, learning, exam, labs, admin, mobile."""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import login, register, select_module


def test_register_login_logout(page: Page, server, username, browser_errors, admin_credentials):
    base = server["base"]
    register(page, base, username)
    expect(page).to_have_url(re.compile(r"/modules$"))
    expect(page.locator(".flash-success")).to_contain_text("Willkommen")
    page.click("button:has-text('Abmelden')")
    expect(page).to_have_url(re.compile(r"/login$"))
    login(page, base, username, "falsch123")
    expect(page.locator(".flash-error")).to_contain_text("falsch")
    login(page, base, username)
    expect(page.locator(".nav-user")).to_have_text(username)


def test_practice_with_german_help(page: Page, server, username, browser_errors, admin_credentials):
    base = server["base"]
    register(page, base, username)
    select_module(page, base, "303")
    expect(page.locator("h1")).to_contain_text("303")
    page.goto(base + "/learn/303?objective=331.1")
    question = page.locator(".question-text")
    expect(question).to_be_visible()
    # translation hidden by default, visible after click, marks help usage
    expect(page.locator("[data-translation]").first).to_be_hidden()
    page.click("[data-toggle-translation]")
    expect(page.locator("[data-translation]").first).to_be_visible()
    expect(page.locator("[data-used-help]")).to_have_value("1")
    # term highlighting and popover
    page.click("[data-toggle-terms]")
    terms = page.locator(".term[data-term-id]")
    assert terms.count() > 0
    terms.first.click()
    popover = page.locator("[data-term-popover]")
    expect(popover).to_be_visible()
    expect(popover.locator("[data-popover-de]")).not_to_have_text("")
    popover.locator("[data-popover-learn]").click()
    expect(popover.locator("[data-popover-learn]")).to_have_text("Wird gelernt")
    # answer
    page.locator(".choice input").first.check()
    page.click("form[data-question-form] button[type=submit]")
    expect(page.locator(".verdict")).to_be_visible()
    expect(page.locator(".explanation")).to_contain_text("Erklärung")
    expect(page.locator("text=Sprachhilfe genutzt")).to_be_visible()
    page.click("a:has-text('Nächste Frage')")
    expect(page.locator(".question-text")).to_be_visible()
    # the learned term is in the vocabulary list
    page.goto(base + "/vocab")
    expect(page.locator(".term-rows li").first).to_be_visible()
    page.goto(base + "/vocab/review")
    page.click("[data-reveal]")
    expect(page.locator("[data-answer]")).to_be_visible()
    page.click("button:has-text('Gewusst')")
    expect(page).to_have_url(re.compile(r"/vocab$"))


def test_exam_simulation_without_help(
    page: Page, server, username, browser_errors, admin_credentials
):
    base = server["base"]
    register(page, base, username)
    select_module(page, base, "305")
    page.goto(base + "/exam/305/start")
    expect(page).to_have_url(re.compile(r"/exam/\d+$"))
    expect(page.locator("[data-timer]")).not_to_have_text("--:--")
    assert page.locator("[data-toggle-translation]").count() == 0
    assert page.locator("[data-translation]").count() == 0
    cards = page.locator(".question-card")
    assert cards.count() == 6
    for i in range(cards.count()):
        cards.nth(i).locator("input").first.check()
    expect(page.locator("[data-answered-count]")).to_have_text("6 von 6 beantwortet")
    page.click("button:has-text('Abgeben')")
    expect(page).to_have_url(re.compile(r"/exam/\d+/result$"))
    expect(page.locator(".verdict")).to_contain_text("von 6 richtig")
    page.goto(base + "/exams")
    expect(page.locator("table")).to_contain_text("305")


def test_entry_test_and_progress(page: Page, server, username, browser_errors, admin_credentials):
    base = server["base"]
    register(page, base, username)
    select_module(page, base, "306")
    page.click("a:has-text('Eingangstest')")
    expect(page.locator("h1")).to_contain_text("Eingangstest")
    assert page.locator("[data-timer]").count() == 0
    cards = page.locator(".question-card")
    for i in range(cards.count()):
        cards.nth(i).locator("input").first.check()
    page.click("button:has-text('Abgeben')")
    page.goto(base + "/module/306")
    expect(page.locator("summary", has_text="Eingangstest:")).to_be_visible()
    page.goto(base + "/progress")
    expect(page.locator("h1")).to_have_text("Mein Lernfortschritt")
    expect(page.locator("text=Eingangstest")).to_be_visible()


def test_labs(page: Page, server, username, browser_errors, admin_credentials):
    base = server["base"]
    register(page, base, username)
    page.goto(base + "/labs")
    page.locator("a[href^='/lab/']").first.click()
    expect(page.locator(".lab-steps li").first).to_be_visible()
    expect(page.locator("pre").first).to_be_visible()
    page.locator(".checks summary").first.click()
    expect(page.locator(".checks details[open] p").first).to_be_visible()
    page.click("button:has-text('Lab als erledigt markieren')")
    expect(page.locator(".tag-ok")).to_contain_text("erledigt")
    page.goto(base + "/labs")
    expect(page.locator(".tag-ok").first).to_be_visible()


def test_admin_import_and_role_check(
    page: Page, server, username, browser_errors, admin_credentials, question_file, tmp_path
):
    base = server["base"]
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    page.goto(base + "/admin/import")
    page.set_input_files("input[type=file]", str(question_file))
    page.click("button:has-text('Importieren')")
    expect(page.locator(".flash-success")).to_contain_text("1 neu")
    expect(page.locator(".flash-success")).to_contain_text("nicht freigegeben")
    expect(page.locator("table")).to_contain_text("e2e-questions.json")
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"schema_version": 1, "kind": "questions", "module": "303", "source": "x", '
        '"exam_version": "3.0", "questions": [{"id": "x"}]}'
    )
    page.set_input_files("input[type=file]", str(bad))
    page.click("button:has-text('Importieren')")
    expect(page.locator(".flash-error")).to_contain_text("abgelehnt")
    page.goto(base + "/admin/questions?q=e2e-q-")
    expect(page.locator("table")).to_contain_text("e2e-q-")
    # learner must not reach the administration
    page.click("button:has-text('Abmelden')")
    register(page, base, username)
    page.goto(base + "/admin")
    expect(page.locator("h1")).to_contain_text("403")
    assert page.locator("nav.nav a[href='/admin']").count() == 0


def test_group_approval_flow(page: Page, server, username, browser_errors, admin_credentials):
    base = server["base"]
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    page.goto(base + "/admin/groups")
    page.fill("input[name=name]", f"Gruppe {username}")
    page.click("button:has-text('Anlegen')")
    expect(page.locator("h1")).to_contain_text("Gruppe")
    page.click("button:has-text('Abmelden')")
    register(page, base, username)
    page.goto(base + "/groups")
    page.locator(f"section:has-text('Gruppe {username}') button").click()
    expect(page.locator(f"section:has-text('Gruppe {username}')")).to_contain_text(
        "wartet auf Freigabe"
    )
    page.click("button:has-text('Abmelden')")
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    page.goto(base + "/admin/groups")
    page.click(f"a:has-text('Gruppe {username}')")
    page.click("button:has-text('Freigeben')")
    expect(page.locator("table")).to_contain_text(username)


@pytest.mark.parametrize("viewport", [{"width": 390, "height": 844}], ids=["android-phone"])
def test_mobile_layout(page: Page, server, username, browser_errors, admin_credentials, viewport):
    base = server["base"]
    page.set_viewport_size(viewport)
    register(page, base, username)
    nav = page.locator("[data-nav]")
    expect(nav).to_be_hidden()
    page.click("[data-nav-toggle]")
    expect(nav).to_be_visible()
    select_module(page, base, "300")
    page.goto(base + "/learn/300")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= viewport["width"], "page must not scroll horizontally on a phone"
    page.click("[data-toggle-translation]")
    page.locator(".choice input").first.check()
    page.click("form[data-question-form] button[type=submit]")
    expect(page.locator(".verdict")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= viewport["width"]


def test_external_questions_released_by_supervisor(
    page: Page, server, username, browser_errors, admin_credentials, tmp_path
):
    """Teacher imports an external source and releases it; the learner sees the tag."""
    import json
    import time

    base = server["base"]
    source = f"ExamTopics Test {int(time.time())}"
    doc = {
        "schema_version": 1,
        "kind": "questions",
        "module": "305",
        "source": source,
        "exam_version": "3.0",
        "rights": "unverified",
        "license": "Rechte nicht geklärt (Test)",
        "questions": [
            {
                "id": f"e2e-extra-{int(time.time() * 1000)}",
                "objective": "353.4",
                "type": "single",
                "question": "What is the purpose of the command vagrant init?",
                "question_de": "Welchen Zweck hat vagrant init?",
                "choices": [
                    {"text": "It creates a Vagrantfile.", "correct": True},
                    {"text": "It starts a box."},
                ],
                "explanation_de": "vagrant init erzeugt ein Vagrantfile.",
            }
        ],
    }
    path = tmp_path / "extra.json"
    path.write_text(json.dumps(doc))
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    page.goto(base + "/admin/import")
    page.set_input_files("input[type=file]", str(path))
    page.click("button:has-text('Importieren')")
    expect(page.locator(".flash-success")).to_contain_text("1 neu")
    expect(page.locator("table")).to_contain_text(f"{source} · unveröffentlicht")
    group = f"Kurs {username}"
    page.goto(base + "/admin/groups")
    page.fill("input[name=name]", group)
    page.select_option("select[name=join_mode]", "open")
    page.click("button:has-text('Anlegen')")
    page.goto(base + "/admin/releases")
    expect(page.locator("table")).to_contain_text(source)
    section = page.locator(f"section:has-text('Freigaben für Gruppe {group}')")
    section.locator(f"label:has-text('{source}') input").check()
    section.locator("button:has-text('Speichern')").click()
    expect(page.locator(".flash-success")).to_contain_text("gespeichert")
    page.click("button:has-text('Abmelden')")
    register(page, base, username)
    select_module(page, base, "305")
    page.goto(base + "/groups")
    page.locator(f"section:has-text('{group}') button").click()
    page.goto(base + "/module/305")
    expect(page.locator("h2", has_text="Zusatzfragen")).to_be_visible()
    page.click("a:has-text('Nur Zusatzfragen üben')")
    expect(page.locator(".source-tag")).to_contain_text("Zusatzfrage")
    expect(page.locator(".source-tag")).to_contain_text(source)
    expect(page.locator(".source-tag")).to_contain_text("Prüfungsgeneration 3.0")
    expect(page.locator(".source-tag")).to_contain_text("nicht geklärt")
    page.locator(".choice input").first.check()
    page.click("form[data-question-form] button[type=submit]")
    expect(page.locator(".verdict")).to_be_visible()
    expect(page.locator(".source-tag")).to_contain_text("Zusatzfrage")
    # a learner has no access to import or release pages
    page.goto(base + "/admin/releases")
    expect(page.locator("h1")).to_contain_text("403")


def test_exam_submit_asks_before_leaving_questions_open(
    page: Page, server, username, browser_errors, admin_credentials
):
    base = server["base"]
    register(page, base, username)
    select_module(page, base, "303")
    page.goto(base + "/exam/303/start")
    expect(page).to_have_url(re.compile(r"/exam/\d+$"))
    dialogs = []

    def on_dialog(dialog):
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", on_dialog)
    page.click("button:has-text('Abgeben')")
    assert dialogs and "unbeantwortet" in dialogs[0]
    expect(page).to_have_url(re.compile(r"/exam/\d+$"))  # still on the exam
    page.remove_listener("dialog", on_dialog)
    page.on("dialog", lambda d: d.accept())
    page.click("button:has-text('Abgeben')")
    expect(page).to_have_url(re.compile(r"/exam/\d+/result$"))


def test_admin_creates_user_in_browser(
    page: Page, server, username, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    page.goto(base + "/admin/users")
    page.click("summary:has-text('Benutzer anlegen')")
    page.fill("form[action='/admin/users'] input[name=username]", username)
    page.select_option("form[action='/admin/users'] select[name=role]", "supervisor")
    page.fill("form[action='/admin/users'] input[name=password]", "geheim123")
    page.click("form[action='/admin/users'] button[type=submit]")
    expect(page.locator(".flash-success")).to_contain_text("angelegt")
    page.click("button:has-text('Abmelden')")
    login(page, base, username)
    expect(page.locator("nav.nav a[href='/admin']")).to_be_visible()
