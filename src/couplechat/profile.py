"""Load a couple profile (YAML) and answer "where / which timezone was X on day D"."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("A", "B")


@dataclass
class Segment:
    city: str
    timezone: str
    first: dt.date
    last: dt.date


@dataclass
class Person:
    key: str
    label: str
    source_names: list[str]
    default_timezone: str
    locations: list[Segment] = field(default_factory=list)

    def segment_on(self, day: dt.date) -> Segment | None:
        for seg in self.locations:
            if seg.first <= day <= seg.last:
                return seg
        return None

    def timezone_on(self, day: dt.date) -> ZoneInfo:
        seg = self.segment_on(day)
        return ZoneInfo(seg.timezone if seg else self.default_timezone)


@dataclass
class Profile:
    people: dict[str, Person]
    reference_timezone: ZoneInfo
    milestones: list[dict]
    context: list[str]
    lexicons: dict[str, list[str]]
    session_gap_minutes: int
    story: dict
    privacy: dict

    def label(self, key: str) -> str:
        return self.people[key].label

    def sender_key(self, raw_name: str) -> str | None:
        for person in self.people.values():
            if raw_name in person.source_names:
                return person.key
        return None

    def phases(self, first: dt.date, last: dt.date) -> list[dict]:
        """Split [first, last] at milestone dates into labelled phases."""
        cuts = sorted((m for m in self.milestones if first < _date(m["date"]) <= last), key=lambda m: _date(m["date"]))
        out, start, label, key = [], first, "开始", "start"
        before = [m for m in self.milestones if _date(m["date"]) <= first]
        if before:
            label, key = before[-1]["label"], before[-1]["key"]
        for m in cuts:
            out.append({"key": key, "label": label, "first": start, "last": _date(m["date"]) - dt.timedelta(days=1)})
            start, label, key = _date(m["date"]), m["label"], m["key"]
        out.append({"key": key, "label": label, "first": start, "last": last})
        return out


def _date(value) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))


def load_profile(path: str | Path) -> Profile:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    people = {}
    for key in KEYS:
        p = raw["participants"][key]
        segs = [Segment(s["city"], s["timezone"], _date(s["first"]), _date(s["last"])) for s in p.get("locations", [])]
        people[key] = Person(key, p["label"], [str(n) for n in p.get("source_names", [key])], p["default_timezone"], segs)
    lex = yaml.safe_load((ROOT / "lexicons" / "default.yaml").read_text(encoding="utf-8"))
    for name, terms in (raw.get("lexicons") or {}).items():
        lex[name] = sorted(set(lex.get(name, [])) | set(terms))
    return Profile(
        people=people,
        reference_timezone=ZoneInfo(raw.get("reference_timezone", people["A"].default_timezone)),
        milestones=raw.get("milestones") or [],
        context=raw.get("context") or [],
        lexicons=lex,
        session_gap_minutes=int(raw.get("session_gap_minutes", 60)),
        story={"language": "zh", "tone": "", "model": "claude-opus-5-5", **(raw.get("story") or {})},
        privacy={"send_vocabulary": False, "send_context": True, **(raw.get("privacy") or {})},
    )
