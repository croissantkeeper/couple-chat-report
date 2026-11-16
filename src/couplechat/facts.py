"""The facts store: every number the report may cite, with an id and a plain-language definition.

facts.json is the only thing the narrative layer is allowed to quote numbers from.
"""
from __future__ import annotations

import json
from pathlib import Path


class Facts:
    def __init__(self) -> None:
        self.facts: dict[str, dict] = {}
        self.modules: dict[str, dict] = {}
        self.figures: list[dict] = []
        self.meta: dict = {}

    def add(self, fact_id: str, value, desc: str, unit: str = "", module: str = "core", sensitive: bool = False) -> None:
        if fact_id in self.facts:
            raise ValueError(f"duplicate fact id: {fact_id}")
        if isinstance(value, float):
            value = round(value, 2)
        self.facts[fact_id] = {"value": value, "unit": unit, "desc": desc, "module": module, "sensitive": sensitive}

    def module(self, name: str, applied: bool, reason: str) -> None:
        self.modules[name] = {"applied": applied, "reason": reason}

    def figure(self, fig_id: str, path: str, title: str, module: str, shows: str) -> None:
        self.figures.append({"id": fig_id, "path": path, "title": title, "module": module, "shows": shows})

    def to_dict(self) -> dict:
        return {"meta": self.meta, "modules": self.modules, "figures": self.figures, "facts": self.facts}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_facts(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def llm_payload(data: dict, send_vocabulary: bool) -> dict:
    """What leaves the machine: aggregates only, minus facts flagged sensitive unless allowed."""
    facts = {k: {"value": v["value"], "unit": v["unit"], "desc": v["desc"]}
             for k, v in data["facts"].items() if send_vocabulary or not v["sensitive"]}
    return {"meta": data["meta"], "modules": data["modules"],
            "figures": [{k: f[k] for k in ("id", "title", "shows")} for f in data["figures"]], "facts": facts}


def format_value(fact: dict) -> str:
    value, unit = fact["value"], fact["unit"]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return str(value)
    if isinstance(value, int):
        text = f"{value:,}"
    else:
        text = f"{value:,.1f}"
    return text + ("%" if unit == "%" else "")
