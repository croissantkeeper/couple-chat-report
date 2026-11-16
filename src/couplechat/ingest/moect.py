"""Moect export (https://github.com/mofan6/Moect).

Moect writes a folder holding index.html plus chunk files named c000001.js, c000002.js, ...
Each chunk is `window.__wxChunk=[ {...}, ... ]` with one object per message. Fields used here:

  create_time  Unix seconds
  is_sender    true when the message was sent by the account that made the export
  kind         text | quote | emoji | image | voice | video | voip | ...
  text         message text
  server_id    used to drop duplicates

Senders are reported as "self" (the exporting account) and "other", so the profile
should list them under source_names, e.g. A: [self] and B: [other].
System notices and raw XML payloads are dropped.
"""
import html
import json
import re
from pathlib import Path

import pandas as pd

KIND_MAP = {"text": "text", "quote": "quote", "emoji": "sticker", "image": "image", "voice": "voice", "video": "video", "voip": "call"}
_SYSTEM = re.compile(r"^(我通过了你的朋友验证请求|以上是打招呼的内容|你已添加了|你们已经是好友|以下为新消息|你撤回了一条消息|对方撤回了一条消息)")
_XML = re.compile(r"<(?:msg\b|appmsg\b|\?xml\b|recordinfo\b)")


def read_moect(path: Path) -> pd.DataFrame:
    files = sorted(path.rglob("c[0-9]*.js")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no Moect chunk files (c000001.js, ...) under {path}")
    rows, seen = [], set()
    for f in files:
        raw = f.read_text(encoding="utf-8-sig")
        for m in json.loads(raw[raw.index("=") + 1:].rstrip(";\r\n ")):
            key = (m.get("session"), m.get("server_id") or (m.get("shard"), m.get("local_id")))
            if key in seen:
                continue
            seen.add(key)
            text = html.unescape(m.get("text") or "")
            if _SYSTEM.search(text):
                continue
            kind = KIND_MAP.get(m.get("kind"), "other")
            if kind in ("text", "quote") and _XML.search(text):
                kind, text = "other", ""
            rows.append({
                "ts": pd.to_datetime(int(m["create_time"]), unit="s", utc=True),
                "sender": "self" if m.get("is_sender") else "other",
                "kind": kind,
                "text": text if kind in ("text", "quote") else "",
            })
    if not rows:
        raise ValueError(f"no messages found under {path}")
    return pd.DataFrame(rows)
