"""Self-hosted operation (issue #12): every page, stylesheet, script, icon and the service
worker refer only to the own server. No web fonts, CDNs, analytics or tracking. Links a user
may click (``<a href>``) are allowed to point elsewhere; they open in the learner's browser."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser

from tests.conftest import PROJECT_DIR, new_client

EXTERNAL = re.compile(r"^\s*(https?:)?//", re.I)
RESOURCE_ATTRS = {"src", "href", "action", "poster", "data", "srcset", "content"}
STATIC_DIR = PROJECT_DIR / "app" / "static"

ANONYMOUS_PAGES = ["/", "/login", "/register", "/offline"]
LEARNER_PAGES = [
    "/",
    "/modules",
    "/module/303",
    "/learn/303",
    "/labs",
    "/labs/umgebung",
    "/vocab",
    "/glossary",
    "/progress",
    "/exams",
    "/account",
]
ADMIN_PAGES = [
    "/admin",
    "/admin/users",
    "/admin/groups",
    "/admin/import",
    "/admin/releases",
    "/admin/questions",
    "/admin/stats",
    "/admin/settings",
]


class ResourceCollector(HTMLParser):
    """Collects resource references (not user links) that leave the own origin."""

    def __init__(self) -> None:
        super().__init__()
        self.external: list[tuple[str, str, str]] = []
        self.loaded: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            return
        for key, value in attrs:
            if key in RESOURCE_ATTRS and value:
                if EXTERNAL.match(value):
                    self.external.append((tag, key, value))
                elif tag in {"link", "script", "img"} and key in {"src", "href"}:
                    self.loaded.append(value)


def _check_pages(client, paths: list[str]) -> int:
    rendered = 0
    for path in paths:
        response = client.get(path)
        if response.status_code != 200:
            continue
        rendered += 1
        parser = ResourceCollector()
        parser.feed(response.text)
        assert not parser.external, (path, parser.external)
        assert parser.loaded, (path, "expected at least the stylesheet")
        for resource in parser.loaded:
            assert resource.startswith("/"), (path, resource)
    return rendered


def test_pages_reference_only_the_own_server(client, admin):
    anonymous = new_client()
    assert _check_pages(anonymous, ANONYMOUS_PAGES) == len(ANONYMOUS_PAGES)
    learner = new_client("offline_learner")
    learner.post("/modules/select", data={"module_code": "303"}, follow_redirects=False)
    assert _check_pages(learner, LEARNER_PAGES) == len(LEARNER_PAGES)
    assert _check_pages(admin, ADMIN_PAGES) >= len(ADMIN_PAGES) - 1


def test_static_files_and_service_worker_stay_on_the_own_origin():
    css = (STATIC_DIR / "app.css").read_text()
    assert "@import" not in css and "@font-face" not in css
    assert not re.search(r"url\(\s*['\"]?(https?:)?//", css, re.I), "CSS loads a remote resource"
    for name in ("app.js", "sw.js"):
        text = (STATIC_DIR / name).read_text()
        assert not re.search(r"https?://", text), f"{name} contains an absolute URL"
    assert "url.origin !== self.location.origin" in (STATIC_DIR / "sw.js").read_text()
    manifest = json.loads((STATIC_DIR / "manifest.webmanifest").read_text())
    assert all(icon["src"].startswith("/") for icon in manifest["icons"])
    assert manifest["start_url"] == "/"


def test_templates_do_not_embed_remote_scripts_styles_or_fonts():
    offenders = []
    for template in (PROJECT_DIR / "app" / "templates").rglob("*.html"):
        text = template.read_text()
        for match in re.finditer(r"<(link|script|img|iframe|source)\b[^>]*>", text, re.I):
            tag = match.group(0)
            if EXTERNAL.search(re.sub(r"^<\w+", "", tag).split("=", 1)[-1]) and re.search(
                r"(src|href)\s*=\s*[\"'](https?:)?//", tag, re.I
            ):
                offenders.append((template.relative_to(PROJECT_DIR).as_posix(), tag[:80]))
        assert "fonts.googleapis" not in text and "fonts.gstatic" not in text, template
    assert not offenders, offenders
