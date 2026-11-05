"""Tiny Markdown renderer for the project's own documentation pages.

Supports what ``docs/*.md`` uses: headings, paragraphs, bullet and numbered lists, fenced
code blocks, tables, and inline code, bold and links. Everything is HTML-escaped; it is not
a general Markdown implementation and is only fed with files from the repository.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*|#[^)\s]*)\)")


def _inline(text: str) -> str:
    out = str(escape(text))
    out = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)
    return out


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9äöüß]+", "-", text.lower()).strip("-")
    return slug or "abschnitt"


def render_markdown(source: str) -> Markup:
    html: list[str] = []
    lines = source.splitlines()
    i = 0
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            html.append(f"<pre><code>{escape(chr(10).join(code))}</code></pre>")
            i += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            html.append(f'<h{level} id="{_slug(text)}">{_inline(text)}</h{level}>')
            i += 1
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            cells = [c for c in cells if not all(re.fullmatch(r":?-+:?", x) for x in c)]
            if cells:
                head = "".join(f"<th>{_inline(c)}</th>" for c in cells[0])
                body = "".join(
                    "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>"
                    for row in cells[1:]
                )
                html.append(
                    f'<table class="table"><thead><tr>{head}</tr></thead>'
                    f"<tbody>{body}</tbody></table>"
                )
            continue
        list_match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if list_match:
            flush_paragraph()
            ordered = list_match.group(2)[0].isdigit()
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines):
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if m and (m.group(2)[0].isdigit()) == ordered:
                    items.append(m.group(3))
                    i += 1
                elif lines[i].startswith("  ") and items and lines[i].strip():
                    items[-1] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            html.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if not stripped:
            flush_paragraph()
            i += 1
            continue
        paragraph.append(stripped)
        i += 1
    flush_paragraph()
    return Markup("\n".join(html))
