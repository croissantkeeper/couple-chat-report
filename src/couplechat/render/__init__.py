"""Fill {{fact.id}} placeholders and check that the draft only cites known numbers."""
from __future__ import annotations

import re

from ..facts import format_value

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
FIGURE = re.compile(r"\[\[figure:([A-Za-z0-9_]+)\]\]")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")


def check_draft(draft: str, data: dict) -> list[str]:
    """Return problems: unknown fact ids, unknown figures, and numbers typed by hand."""
    problems = []
    draft = draft.split("<!--figure-catalogue-->")[0]   # captions generated from facts.json are not model prose
    for fact_id in sorted(set(PLACEHOLDER.findall(draft))):
        if fact_id not in data["facts"]:
            problems.append(f"未知的 fact 编号：{fact_id}")
    known_figures = {f["id"] for f in data["figures"]}
    for fig in sorted(set(FIGURE.findall(draft))):
        if fig not in known_figures:
            problems.append(f"未知的图件：{fig}")
    prose = FIGURE.sub("", PLACEHOLDER.sub("", draft))
    for line in prose.splitlines():
        body = re.sub(r"^#+\s*\d+[.、]?\s*", "", line)      # section numbers in headings are fine
        for number in NUMBER.findall(body):
            if len(number.rstrip("%").replace(",", "")) >= 2:   # single digits read as ordinary words
                problems.append(f"正文里有手写数字 {number}，请改用占位符：{line.strip()[:40]}")
    return problems


def render_markdown(draft: str, data: dict) -> str:
    def fact(match: re.Match) -> str:
        item = data["facts"].get(match.group(1))
        return format_value(item) if item else match.group(0)

    figures = {f["id"]: f for f in data["figures"]}

    def figure(match: re.Match) -> str:
        f = figures.get(match.group(1))
        return f"![{f['title']}]({f['path']})" if f else match.group(0)

    return FIGURE.sub(figure, PLACEHOLDER.sub(fact, draft))


_CSS = """
body{max-width:920px;margin:40px auto;padding:0 20px;font-family:-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
line-height:1.75;color:#35291F;background:#FFFDF8}
h1{color:#A44356;font-size:1.9em;border-bottom:2px solid #FAF1DC;padding-bottom:.3em}
h2{color:#A44356;margin-top:2em}h3{color:#536126;margin-top:1.6em}
img{max-width:100%;display:block;margin:1em auto;border-radius:6px}
blockquote{margin:1em 0;padding:.6em 1em;background:#FAF1DC;border-left:4px solid #D29661}
code{background:#FAF1DC;padding:.1em .3em;border-radius:3px}
"""


def render_html(markdown: str, title: str = "") -> str:
    """A small Markdown-to-HTML step for the report: headings, paragraphs, images, quotes, bold, lists."""
    import html as _html

    def inline(text: str) -> str:
        text = _html.escape(text, quote=False)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    body, paragraph, in_list = [], [], False

    def flush() -> None:
        nonlocal in_list
        if paragraph:
            body.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()
        if in_list:
            body.append("</ul>")
            in_list = False

    for line in markdown.splitlines():
        stripped = line.strip()
        heading = re.match(r"(#{1,4})\s+(.*)", stripped)
        if not stripped or stripped.startswith("<!--"):
            flush()
        elif heading:
            flush()
            level = len(heading.group(1))
            if level == 1 and not title:
                title = heading.group(2)
            body.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif stripped.startswith("![") and stripped.endswith(")"):
            flush()
            body.append(inline(stripped))
        elif stripped.startswith(">"):
            flush()
            body.append("<blockquote>" + inline(stripped.lstrip("> ")) + "</blockquote>")
        elif stripped.startswith(("- ", "* ")):
            if paragraph:
                flush()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append("<li>" + inline(stripped[2:]) + "</li>")
        else:
            paragraph.append(stripped)
    flush()
    return (f'<!doctype html>\n<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{_html.escape(title)}</title><style>{_CSS}</style></head>\n<body>\n" + "\n".join(body) + "\n</body></html>\n")
