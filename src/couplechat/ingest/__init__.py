"""Adapters turn one export format into the canonical message table.

Canonical columns:
  ts      timezone-aware UTC timestamp
  sender  "A" or "B" (mapped through profile.participants[*].source_names)
  kind    text | quote | sticker | image | voice | video | call | other
  text    message text ("" for non-text kinds)

Everything downstream reads only this table, so supporting a new export tool
means writing one function here and registering it in ADAPTERS.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..profile import Profile
from .generic_csv import read_generic_csv
from .moect import read_moect
from .wechat_json import read_wechat_json

ADAPTERS = {"csv": read_generic_csv, "moect": read_moect, "wechat-json": read_wechat_json}
KINDS = {"text", "quote", "sticker", "image", "voice", "video", "call", "other"}


def ingest(path: str | Path, fmt: str, profile: Profile) -> pd.DataFrame:
    if fmt not in ADAPTERS:
        raise ValueError(f"unknown format {fmt!r}; available: {sorted(ADAPTERS)}")
    df = ADAPTERS[fmt](Path(path))
    df["sender"] = df["sender"].astype(str).map(profile.sender_key)
    unknown = int(df["sender"].isna().sum())
    df = df.dropna(subset=["sender"]).copy()
    df["kind"] = df["kind"].where(df["kind"].isin(KINDS), "other")
    df["text"] = df["text"].fillna("").astype(str)
    if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")   # accepts timestamps with or without fractions
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").drop_duplicates(subset=["ts", "sender", "kind", "text"]).reset_index(drop=True)
    df.attrs["dropped_unknown_sender"] = unknown
    return df[["ts", "sender", "kind", "text"]]
