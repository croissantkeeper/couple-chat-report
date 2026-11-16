"""Generate a fully fictional chat export that matches profiles/example.yaml.

Nothing here comes from a real conversation: the phrases are a small hand-written
pool and the timing is random with a fixed seed, so the output is reproducible.

    python examples/synthetic/generate.py examples/synthetic/messages.csv
"""
import csv
import datetime as dt
import random
import sys
from zoneinfo import ZoneInfo

SEED = 20250301
FIRST, LAST = dt.date(2025, 3, 1), dt.date(2025, 5, 31)
APART, TOGETHER = dt.date(2025, 3, 21), dt.date(2025, 4, 1)
SH, BER = ZoneInfo("Asia/Shanghai"), ZoneInfo("Europe/Berlin")

PHRASES = {
    "A": ["哈哈哈", "今天好累", "刚下课", "你吃饭了吗", "笑死", "给你看个东西", "嘿嘿", "我到家啦", "这个好好吃", "周末想去散步"],
    "B": ["好呀", "我也是", "刚开完会", "吃过了", "确实", "等我一下", "听起来不错", "路上小心", "那家店不错", "可以的"],
}
SWEET = ["想你", "宝宝", "喜欢你"]
SLEEP = ["晚安", "早点睡", "好梦"]
MORNING = ["早安", "早上好"]


def a_zone(day):
    return BER if day >= APART else SH


def main(path):
    rng = random.Random(SEED)
    rows = []
    day = FIRST
    while day <= LAST:
        level = 12 if day < APART else 30 if day < TOGETHER else 60
        if dt.date(2025, 4, 11) <= day <= dt.date(2025, 4, 20):   # B is travelling: more to share
            level = int(level * 1.5)
        n = max(0, int(rng.gauss(level, level * .3)))
        if day < APART and rng.random() < .2:
            n = 0
        # chat window: evening in Shanghai before the move, B's evening / A's afternoon after it
        for _ in range(n):
            hour = rng.choice([20, 21, 22, 23]) if rng.random() < .7 else rng.randrange(8, 24)
            ts = dt.datetime.combine(day, dt.time(hour, rng.randrange(60), rng.randrange(60)), tzinfo=SH)
            sender = "A" if rng.random() < .54 else "B"
            roll = rng.random()
            if roll < .16:
                kind, text = "sticker", ""
            elif roll < .20:
                kind, text = "image", ""
            else:
                kind = "quote" if (sender == "B" and rng.random() < .1) else "text"
                text = rng.choice(PHRASES[sender])
                if day >= TOGETHER and rng.random() < .08:
                    text = rng.choice(SWEET)
            rows.append((ts, sender, kind, text))
        if day >= APART and n:
            # B says good night at B's bedtime; A answers from A's afternoon with a wish for B's night
            night = dt.datetime.combine(day, dt.time(23, rng.randrange(30, 59)), tzinfo=SH)
            rows.append((night, "B", "text", rng.choice(SLEEP)))
            rows.append((night + dt.timedelta(seconds=rng.randrange(10, 90)), "A", "text", rng.choice(SLEEP)))
            morning = dt.datetime.combine(day, dt.time(8, rng.randrange(60)), tzinfo=a_zone(day))
            rows.append((morning, "A", "text", rng.choice(MORNING)))
            if rng.random() < .6:
                call = dt.datetime.combine(day, dt.time(21, rng.randrange(60)), tzinfo=SH)
                rows.append((call, rng.choice("AB"), "call", ""))
        day += dt.timedelta(days=1)
    rows.sort(key=lambda r: r[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "sender", "kind", "text"])
        for ts, sender, kind, text in rows:
            w.writerow([ts.astimezone(dt.timezone.utc).isoformat(), sender, kind, text])
    print(f"wrote {len(rows)} synthetic messages to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/synthetic/messages.csv")
