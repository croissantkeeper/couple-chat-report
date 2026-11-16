"""WeChat JSON export adapter (template).

Export tools differ in field names, so this reads a common shape and is meant
to be adjusted: a JSON file (or folder of files) holding a list of messages,
each with a Unix timestamp, a sender id, a type and a content string.
Edit FIELD and TYPE_MAP to match your tool's output.
"""
import json
from pathlib import Path

import pandas as pd

FIELD = {"ts": "timestamp", "sender": "sender", "type": "type", "text": "content"}
TYPE_MAP = {
    "text": "text", "quote": "quote", "emoji": "sticker", "sticker": "sticker", "image": "image",
    "voice": "voice", "video": "video", "voip": "call", "call": "call",
}


def read_wechat_json(path: Path) -> pd.DataFrame:
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    rows = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8-sig"))
        messages = data.get("messages", []) if isinstance(data, dict) else data
        for m in messages:
            if not isinstance(m, dict) or FIELD["ts"] not in m:
                continue
            kind = TYPE_MAP.get(str(m.get(FIELD["type"], "")).lower(), "other")
            rows.append({
                "ts": pd.to_datetime(int(m[FIELD["ts"]]), unit="s", utc=True),
                "sender": m.get(FIELD["sender"], ""),
                "kind": kind,
                "text": m.get(FIELD["text"], "") if kind in ("text", "quote") else "",
            })
    if not rows:
        raise ValueError(f"no messages found under {path}; check FIELD in wechat_json.py")
    return pd.DataFrame(rows)
