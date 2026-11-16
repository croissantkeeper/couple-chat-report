"""Generic CSV: columns timestamp, sender, kind, text.

timestamp is ISO 8601; a value without an offset is read as UTC.
This is the format produced by examples/synthetic/generate.py and the easiest
target to convert any other export into.
"""
from pathlib import Path

import pandas as pd


def read_generic_csv(path: Path) -> pd.DataFrame:
    files = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no CSV files under {path}")
    df = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype=str) for f in files], ignore_index=True)
    missing = {"timestamp", "sender", "kind", "text"} - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")
    return df.rename(columns={"timestamp": "ts"})
