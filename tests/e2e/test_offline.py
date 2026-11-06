"""Offline behaviour: visited pages stay available, unknown pages show the offline fallback."""

import re

from playwright.sync_api import Page, expect

from tests.e2e.conftest import register, select_module


def test_offline_pages_from_service_worker(page: Page, server, username, admin_credentials):
    base = server["base"]
    register(page, base, username)
    select_module(page, base, "303")
    page.goto(base + "/labs")
    page.locator("a[href^='/lab/']").first.click()
    lab_url = page.url
    page.evaluate("navigator.serviceWorker.ready.then(r => r.active && r.active.state)")
    page.wait_for_function("navigator.serviceWorker.controller !== null")
    # make sure the page itself got cached after the worker took control
    page.reload()
    page.wait_for_load_state("networkidle")
    page.context.set_offline(True)
    try:
        page.goto(lab_url)
        expect(page.locator("h1")).not_to_contain_text("offline")
        expect(page.locator(".lab-steps li").first).to_be_visible()
        expect(page.locator("[data-offline-banner]")).to_be_visible()
        page.goto(base + "/exams")  # never visited
        expect(page.locator("h1")).to_have_text("Du bist offline")
    finally:
        page.context.set_offline(False)
    page.goto(base + "/exams")
    expect(page.locator("h1")).to_have_text(re.compile("Simulationen"))


def test_learning_flow_sends_no_request_to_other_hosts(
    page: Page, server, username, browser_errors, admin_credentials
):
    """Self-hosted operation (issue #12): a complete learner flow in the browser talks only to
    the own server. Any request to another host (fonts, CDNs, analytics) fails the test."""
    base = server["base"]
    foreign: list[str] = []
    page.on(
        "request",
        lambda r: (
            foreign.append(r.url)
            if r.url.startswith("http") and not r.url.startswith(base + "/")
            else None
        ),
    )
    register(page, base, username)
    select_module(page, base, "305")
    for path in (
        "/",
        "/module/305",
        "/learn/305",
        "/labs",
        "/labs/umgebung",
        "/vocab",
        "/glossary",
        "/progress",
        "/exams",
    ):
        page.goto(base + path)
        page.wait_for_load_state("networkidle")
    page.goto(base + "/learn/305")
    page.click("[data-toggle-translation]")
    page.locator(".choice input").first.check()
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    assert not foreign, foreign
