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
