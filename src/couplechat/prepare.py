"""Turn the canonical message table into the analysis table, and build the shared context.

Added columns:
  day, week        calendar day / Monday of that week in the reference timezone
  hour_A, hour_B   the hour this message was sent at on each person's own clock
  local_hour       the sender's own hour; other_hour is the receiver's
  local_day        the sender's own calendar day
  gap              B's UTC offset minus A's, in hours (0 = same clock)
  is_text, chars   text or quoted reply; non-whitespace characters
  clean            text with links, bracketed sticker names and ids removed
  session          id of the conversation session (gap > profile.session_gap_minutes starts a new one)
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .facts import Facts
from .profile import KEYS, Profile

TEXT_KINDS = ("text", "quote")
_NOISE = re.compile(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]+|\[[^\]\n]{1,20}\]|<[^>]+>|\b[0-9a-fA-F]{24,}\b")


def prepare(df: pd.DataFrame, profile: Profile) -> pd.DataFrame:
    df = df.copy()
    ref = df["ts"].dt.tz_convert(profile.reference_timezone)
    df["day"] = ref.dt.date
    df["week"] = [d - dt.timedelta(days=d.weekday()) for d in df["day"]]
    cols = {f"hour_{k}": [] for k in KEYS} | {f"day_{k}": [] for k in KEYS} | {"gap": []}
    for ts, day in zip(df["ts"], df["day"]):
        offsets = {}
        for k in KEYS:
            local = ts.tz_convert(profile.people[k].timezone_on(day))
            cols[f"hour_{k}"].append(local.hour)
            cols[f"day_{k}"].append(local.date())
            offsets[k] = local.utcoffset().total_seconds() / 3600
        cols["gap"].append(offsets["B"] - offsets["A"])
    for name, values in cols.items():
        df[name] = values
    is_a = df["sender"] == "A"
    df["local_hour"] = df["hour_A"].where(is_a, df["hour_B"])
    df["other_hour"] = df["hour_B"].where(is_a, df["hour_A"])
    df["local_day"] = df["day_A"].where(is_a, df["day_B"])
    df["weekday"] = [d.weekday() for d in df["local_day"]]
    df["is_text"] = df["kind"].isin(TEXT_KINDS)
    df["clean"] = df["text"].str.replace(_NOISE, " ", regex=True).where(df["is_text"], "")
    df["chars"] = df["clean"].str.replace(r"\s+", "", regex=True).str.len()
    pause = df["ts"].diff().dt.total_seconds().div(60)
    df["session"] = (pause.isna() | (pause > profile.session_gap_minutes)).cumsum()
    return df


def stage_label(gap: float) -> str:
    return "同一时区" if gap == 0 else f"时差{abs(gap):g}小时"


@dataclass
class Context:
    """Everything an analysis needs. Analyses read from it and write facts, figures and tables."""
    df: pd.DataFrame
    profile: Profile
    facts: Facts
    out: Path
    text: pd.DataFrame = field(init=False)
    days: list = field(init=False)
    daily: pd.DataFrame = field(init=False)      # index: day; columns A, B, total (text records)
    weeks: list = field(init=False)
    stages: list = field(init=False)             # distinct clock gaps in order of appearance
    shared: dict = field(default_factory=dict)   # results one analysis leaves for a later one

    def __post_init__(self) -> None:
        self.text = self.df[self.df["is_text"]]
        self.days = list(pd.date_range(min(self.df["day"]), max(self.df["day"]), freq="D").date)
        counts = self.text.groupby(["day", "sender"]).size().unstack(fill_value=0)
        self.daily = counts.reindex(self.days, fill_value=0).reindex(columns=list(KEYS), fill_value=0)
        self.daily["total"] = self.daily["A"] + self.daily["B"]
        self.weeks = sorted(set(self.df["week"]))
        per_gap = self.df.groupby("gap")["day"].agg(["nunique", "min"])
        self.stages = list(per_gap[per_gap["nunique"] >= 3].sort_values("min").index)
        (self.out / "figures").mkdir(parents=True, exist_ok=True)
        (self.out / "tables").mkdir(parents=True, exist_ok=True)

    def label(self, key: str) -> str:
        return self.profile.label(key)

    def inner_days(self) -> list:
        """Days excluding the first and last, which an export usually covers only partly."""
        return self.days[1:-1] if len(self.days) > 2 else self.days

    def table(self, name: str, frame: pd.DataFrame) -> None:
        frame.to_csv(self.out / "tables" / name, index=False, encoding="utf-8-sig")

    def figure(self, fig, fig_id: str, title: str, group: str, shows: str) -> None:
        import matplotlib.pyplot as plt
        fig.savefig(self.out / "figures" / f"{fig_id}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        self.facts.figure(fig_id, f"figures/{fig_id}.png", title, group, shows)
