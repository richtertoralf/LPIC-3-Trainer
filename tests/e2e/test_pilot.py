"""Pilot run through the browser (work package 4): one administrator, one lecturer
(supervisor) and one learner work through the complete scenario of the pilot order.

The steps run in order and share names through PILOT. They work against the test server or,
with LPIC3_E2E_BASE, against a real installation. Exam sizes are read from the page, so the
run copes with the production defaults (60 questions) as well as the small test sizes.
"""

import re
import time

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import login, register, select_module

MODULE = "305"
PHONE = {"width": 390, "height": 844}
stamp = int(time.time()) % 100000
PILOT = {
    "dozent": f"dozent{stamp}",
    "lernender": f"lernender{stamp}",
    "fremd": f"fremd{stamp}",
    "gruppe": f"Pilotgruppe {stamp}",
    "fremdgruppe": f"Fremdgruppe {stamp}",
    "passwort": "Pilot-Passwort-1",
}


def _answer_all(page: Page) -> int:
    """Answer every question of an exam page: first option, or a text for blanks."""
    cards = page.locator("form[data-exam-form] .question-card")
    n = cards.count()
    for i in range(n):
        card = cards.nth(i)
        text = card.locator("input[type=text]")
        if text.count():
            text.fill("pilot")
        else:
            card.locator("input").first.check()
    return n


def _logout(page: Page) -> None:
    toggle = page.locator("[data-nav-toggle]")
    if toggle.is_visible():  # phone layout: the navigation is behind a menu button
        toggle.click()
    page.click("button:has-text('Abmelden')")
    page.wait_for_load_state("networkidle")


def _no_horizontal_scroll(page: Page) -> None:
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]


def test_pilot_01_admin_sets_up_lecturer_and_checks_system(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, admin_credentials["username"], admin_credentials["password"])
    # system status is reachable from the browser
    page.goto(base + "/health")
    assert '"status":"ok"' in page.content().replace(" ", "")
    page.goto(base + "/admin")
    expect(page.locator("h1")).to_contain_text("Verwaltung")
    # 4.1 create the lecturer account with the supervisor role (no CLI needed)
    page.goto(base + "/admin/users")
    page.click("summary:has-text('Benutzer anlegen')")
    page.fill("form[action='/admin/users'] input[name=username]", PILOT["dozent"])
    page.fill("form[action='/admin/users'] input[name=display_name]", "Dozent Pilot")
    page.select_option("form[action='/admin/users'] select[name=role]", "supervisor")
    page.fill("form[action='/admin/users'] input[name=password]", PILOT["passwort"])
    page.click("form[action='/admin/users'] button[type=submit]")
    expect(page.locator(".flash-success")).to_be_visible()
    expect(page.locator("table")).to_contain_text(PILOT["dozent"])
    # bundled supplementary pools exist but are not released anywhere
    page.goto(base + "/admin/releases")
    expect(page.locator("table").first).to_contain_text("Ergänzungspool")
    # a group of the administrator that the lecturer must not see
    page.goto(base + "/admin/groups")
    page.fill("input[name=name]", PILOT["fremdgruppe"])
    page.click("form[action='/admin/groups'] button:has-text('Anlegen')")
    expect(page.locator("h1")).to_contain_text(PILOT["fremdgruppe"])
    PILOT["fremdgruppe_url"] = page.url
    page.goto(base + "/admin/stats")
    expect(page.locator("h1")).to_be_visible()
    _logout(page)


def test_pilot_02_lecturer_creates_group_and_reviews_material(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, PILOT["dozent"], PILOT["passwort"])
    expect(page.locator("nav.nav a[href='/admin']")).to_be_visible()
    # 4.2 own group with open join mode
    page.goto(base + "/admin/groups")
    page.fill("input[name=name]", PILOT["gruppe"])
    page.select_option("select[name=join_mode]", "open")
    page.click("form[action='/admin/groups'] button:has-text('Anlegen')")
    expect(page.locator("h1")).to_contain_text(PILOT["gruppe"])
    PILOT["gruppe_url"] = page.url
    # the administrator's group is not visible or reachable
    page.goto(base + "/admin/groups")
    expect(page.locator("main")).not_to_contain_text(PILOT["fremdgruppe"])
    page.goto(PILOT["fremdgruppe_url"])
    expect(page.locator("h1")).to_contain_text("403")
    # review questions and labs for lesson preparation
    select_module(page, base, MODULE)
    page.goto(base + f"/admin/questions?module={MODULE}")
    expect(page.locator("table").first).to_be_visible()
    page.goto(base + "/labs")
    page.locator(f"section:has-text('{MODULE}') a[href^='/lab/']").first.click()
    expect(page.locator("h2", has_text="Hinweise für Dozenten")).to_be_visible()
    expect(page.locator("h2", has_text="Erfolgskriterien")).to_be_visible()
    PILOT["lab_url"] = page.url
    _logout(page)


def test_pilot_03_learner_registers_joins_and_starts(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    register(page, base, PILOT["lernender"], PILOT["passwort"])
    expect(page).to_have_url(re.compile(r"/modules$"))
    # no administration for learners, server side as well
    expect(page.locator("nav.nav a[href='/admin']")).to_have_count(0)
    page.goto(base + "/admin/releases")
    expect(page.locator("h1")).to_contain_text("403")
    page.goto(PILOT["gruppe_url"])
    expect(page.locator("h1")).to_contain_text("403")
    # join the lecturer's open group
    page.goto(base + "/groups")
    page.locator(f"section:has-text('{PILOT['gruppe']}') button:has-text('Beitreten')").click()
    expect(page.locator(f"section:has-text('{PILOT['gruppe']}')")).to_contain_text("Mitglied")
    # choose the module and take the entry test
    select_module(page, base, MODULE)
    page.click("a:has-text('Eingangstest')")
    expect(page.locator("h1")).to_contain_text("Eingangstest")
    n = _answer_all(page)
    assert n > 0
    page.click("button:has-text('Abgeben')")
    expect(page.locator(".verdict")).to_be_visible()
    # practice with German help
    page.goto(base + f"/learn/{MODULE}")
    page.click("[data-toggle-translation]")
    expect(page.locator("[data-translation]").first).to_be_visible()
    page.locator(".choice input, input[type=text]").first.click()
    if page.locator("input[type=text]").count():
        page.fill("input[type=text]", "pilot")
    page.click("form[data-question-form] button[type=submit]")
    expect(page.locator(".verdict")).to_be_visible()
    expect(page.locator(".explanation")).to_be_visible()
    # supplementary questions are invisible before the lecturer releases them
    page.goto(base + f"/learn/{MODULE}?pool=extra")
    expect(page.locator("main")).not_to_contain_text("Zusatzfrage")
    expect(page.locator(".question-text")).to_have_count(0)
    _logout(page)


def test_pilot_04_lecturer_releases_extra_questions_and_recommends_lab(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, PILOT["dozent"], PILOT["passwort"])
    page.goto(base + "/admin/releases")
    form = page.locator(f"section:has(h2:has-text('{PILOT['gruppe']}')) form")
    extra = form.locator(f"label.radio:has-text('Ergänzungspool'):has-text('{MODULE}-300') input")
    extra.first.check()
    form.locator("button[type=submit]").click()
    expect(page.locator(".flash-success, .flash-info").first).to_be_visible()
    # recommend the reviewed lab for the group
    page.goto(PILOT["gruppe_url"])
    expect(page.locator("table").first).to_contain_text(PILOT["lernender"])
    lab_id = PILOT["lab_url"].rsplit("/", 1)[1]
    page.locator(f"input[name=lab_ids][value='{lab_id}']").check()
    page.click("button:has-text('Empfehlungen speichern')")
    expect(page.locator(".flash-success, .flash-info").first).to_contain_text("empfohlen")
    # the evaluation page already knows the entry test answers
    page.click("a:has-text('Auswertung je Prüfungsziel')")
    expect(page.locator("h1")).to_contain_text("Auswertung")
    expect(page.locator("table.eval").first).to_be_visible()
    _logout(page)


def test_pilot_05_learner_works_through_lab_chapter_test_and_simulation(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, PILOT["lernender"], PILOT["passwort"])
    # released supplementary questions are now visible and marked
    page.goto(base + f"/learn/{MODULE}?pool=extra")
    expect(page.locator(".question-text")).to_be_visible()
    expect(page.locator("main")).to_contain_text("Zusatzfrage")
    # lab environment guide, recommended lab, status, questions of the lab's objective
    page.goto(base + "/labs")
    expect(page.locator(".tag-warn", has_text="empfohlen").first).to_be_visible()
    page.click("a[href='/labs/umgebung']")
    expect(page.locator("h1")).to_contain_text("LAB-Umgebung")
    page.goto(PILOT["lab_url"])
    expect(page.locator("h2", has_text="Hinweise für Dozenten")).to_have_count(0)
    page.click("button:has-text('LAB beginnen')")
    expect(page.locator(".tag-progress")).to_contain_text("in Bearbeitung")
    page.click("a:has-text('Fragen zu diesem Prüfungsziel üben')")
    expect(page.locator(".question-text")).to_be_visible()
    page.locator(".choice input, input[type=text]").first.click()
    if page.locator("input[type=text]").count():
        page.fill("input[type=text]", "pilot")
    page.click("form[data-question-form] button[type=submit]")
    expect(page.locator(".verdict")).to_be_visible()
    page.goto(PILOT["lab_url"])
    page.locator("button:has-text('Als abgeschlossen markieren')").first.click()
    expect(page.locator(".tag-ok")).to_contain_text("abgeschlossen")
    # chapter test of the first topic, then the full simulation
    page.goto(base + f"/module/{MODULE}")
    page.locator("a:has-text('Kapiteltest')").first.click()
    expect(page.locator("h1")).to_contain_text("Kapitel")
    _answer_all(page)
    page.click("button:has-text('Abgeben')")
    expect(page.locator(".verdict")).to_be_visible()
    page.goto(base + f"/module/{MODULE}")
    page.click("a:has-text('Prüfungssimulation')")
    expect(page.locator("[data-timer]")).to_be_visible()
    n = _answer_all(page)
    assert n >= 6
    page.click("button:has-text('Abgeben')")
    expect(page.locator(".verdict")).to_be_visible()
    expect(page.locator("h2", has_text="Fragen im Detail")).to_be_visible()
    # own results and progress
    page.goto(base + "/progress")
    expect(page.locator("h1")).to_contain_text("Lernfortschritt")
    expect(page.locator("main")).to_contain_text("Labs")
    page.goto(base + "/exams")
    expect(page.locator("table, .card").first).to_be_visible()
    _logout(page)


def test_pilot_06_lecturer_sees_progress_and_weaknesses(
    page: Page, server, browser_errors, admin_credentials
):
    base = server["base"]
    login(page, base, PILOT["dozent"], PILOT["passwort"])
    page.goto(PILOT["gruppe_url"])
    expect(page.locator("table").first).to_contain_text("1 abgeschlossen")
    lab_id = PILOT["lab_url"].rsplit("/", 1)[1]
    row = page.locator(f"table.lab-matrix tr:has(input[value='{lab_id}'])")
    expect(row).to_contain_text(PILOT["lernender"])
    page.click("a:has-text('Auswertung je Prüfungsziel')")
    expect(page.locator("table.eval").first).to_be_visible()
    expect(page.locator("main")).to_contain_text("Antworten")
    _logout(page)


@pytest.mark.parametrize("viewport", [PHONE])
def test_pilot_07_phone_layout_for_learner_and_lecturer(
    page: Page, server, browser_errors, admin_credentials, viewport
):
    base = server["base"]
    page.set_viewport_size(viewport)
    login(page, base, PILOT["lernender"], PILOT["passwort"])
    for path in ("/modules", f"/module/{MODULE}", "/labs", "/labs/umgebung", "/progress"):
        page.goto(base + path)
        _no_horizontal_scroll(page)
    page.goto(PILOT["lab_url"])
    _no_horizontal_scroll(page)
    page.goto(base + f"/learn/{MODULE}")
    _no_horizontal_scroll(page)
    _logout(page)
    login(page, base, PILOT["dozent"], PILOT["passwort"])
    page.goto(PILOT["gruppe_url"])
    _no_horizontal_scroll(page)
    page.click("a:has-text('Auswertung je Prüfungsziel')")
    _no_horizontal_scroll(page)
    _logout(page)
