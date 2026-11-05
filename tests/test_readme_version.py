"""Version consistency (RICHTER.PROJECTS ADR-002, section 9): one authoritative version in
``app/__init__.py``; pyproject, the static README badge and the current checkout hints
in the documentation change in the same commit."""

from __future__ import annotations

import re

from app import __version__
from tests.conftest import PROJECT_DIR


def test_pyproject_matches_package_version():
    text = (PROJECT_DIR / "pyproject.toml").read_text()
    assert re.search(rf'^version = "{re.escape(__version__)}"$', text, re.M)


def test_readme_has_exactly_one_version_badge_with_the_branch_version():
    readme = (PROJECT_DIR / "README.md").read_text()
    badges = re.findall(r"img\.shields\.io/badge/version-([^-]+)-", readme)
    assert badges == [__version__], badges
    assert f"[![Version {__version__}]" in readme
    assert "](app/__init__.py)" in readme, "the badge links to the version source"
    assert "img.shields.io/github/v/release" not in readme, "no release badge labelled version"


def test_current_checkout_hints_name_the_current_version():
    for name in ("README.md", "docs/installation.md"):
        text = (PROJECT_DIR / name).read_text()
        tags = set(re.findall(r"git checkout (v\d+\.\d+\.\d+)", text))
        assert tags == {f"v{__version__}"}, (name, tags)


def test_readme_names_only_existing_management_commands():
    from app.cli import LONG_OPTIONS

    readme = (PROJECT_DIR / "README.md").read_text()
    for option in re.findall(r"`(?:sudo )?lpic3ctl (--[a-z]+)", readme):
        assert option in LONG_OPTIONS or option == "--help", option
