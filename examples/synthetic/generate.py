"""Generate a fully fictional chat export that matches profiles/example.yaml.

Nothing here comes from a real conversation. Two invented people, 阿橘 (A) and 小鲸 (B),
talk in sessions drawn at random from small hand-written phrase pools, with a fixed seed
so the output is reproducible. The story built into the data, so every analysis has
something to show:

  03-01  they meet, both in Shanghai: a few evening chats, some days silent
  03-21  A moves to Berlin: the clocks split (7 hours, then 6 after daylight saving on 03-30)
  04-01  they get together: more sessions, affectionate words, calls
  04-11  B spends ten days in Chengdu: more photos and the busiest days
  05-18  a quieter fortnight to end on

    python examples/synthetic/generate.py examples/synthetic/messages.csv
"""
import csv
import datetime as dt
import math
import random
import sys
from zoneinfo import ZoneInfo

SEED = 20250301
FIRST, LAST = dt.date(2025, 3, 1), dt.date(2025, 5, 31)
APART, TOGETHER = dt.date(2025, 3, 21), dt.date(2025, 4, 1)
TRIP = (dt.date(2025, 4, 11), dt.date(2025, 4, 20))
QUIET = dt.date(2025, 5, 18)
SH, BER = ZoneInfo("Asia/Shanghai"), ZoneInfo("Europe/Berlin")

TALK = {
    "A": ["今天好累", "刚下课", "你吃饭了吗", "给你看个东西", "我到家啦", "这个好好吃", "周末想去散步", "外面下雨了",
          "作业还没写完", "图书馆人好多", "今天的咖啡太苦了", "我迷路了", "超市打折", "地铁又晚点", "室友在做饭",
          "好困", "不想起床", "今天天气超好", "刚跑完步", "考试终于结束了", "我在排队", "这边天黑得好晚", "面包店关门了",
          "猜我看到了什么", "好想吃火锅", "等下要开会", "今天学了一个新单词", "楼下有只猫"],
    "B": ["我也是", "刚开完会", "吃过了", "等我一下", "听起来不错", "路上小心", "那家店不错", "可以的",
          "感觉今天过得特别快", "其实我也有点累", "我这边刚下班", "晚上想煮面", "同事请了奶茶", "今天加班了一会儿",
          "感觉你最近很忙", "记得带伞", "那就周末再说", "我看了你发的照片", "这个确实好看", "我在等外卖",
          "刚洗完澡", "今天地铁特别挤", "其实还好", "感觉可以试试", "我帮你查了一下", "明天要早起", "好的我知道了",
          "今天的夕阳很好看"],
}
REACT = {
    "A": [("哈哈哈", 8), ("哈哈哈哈", 9), ("哈哈哈哈哈", 6), ("笑死", 6), ("嘿嘿", 4), ("呜呜", 4), ("真的吗", 3), ("好耶", 3)],
    "B": [("好呀", 10), ("确实", 7), ("嗯嗯", 5), ("可以的", 4), ("哈哈", 2), ("好的", 4), ("没问题", 3), ("辛苦了", 3)],
}
SWEET = {"A": ["想你", "宝宝", "好想你", "喜欢你", "宝宝在干嘛"], "B": ["想你", "宝宝", "我也想你", "喜欢你", "宝宝辛苦了"]}
CARE = ["记得吃饭", "多喝水", "注意安全", "早点睡", "辛苦了"]
TRIP_TALK = ["成都好热", "这边的火锅太辣了", "今天去看了熊猫", "酒店楼下有夜市", "走了两万步"]


def pick(rng, weighted):
    items, weights = zip(*weighted)
    return rng.choices(items, weights)[0]


def phase(day):
    return "met" if day < APART else "apart" if day < TOGETHER else "together"


def a_zone(day):
    return BER if day >= APART else SH


class Chat:
    def __init__(self, rng):
        self.rng = rng
        self.rows = []

    def add(self, when, sender, kind="text", text=""):
        self.rows.append((when, sender, kind, text if kind in ("text", "quote") else ""))

    def line(self, sender, day):
        """One message: (kind, text)."""
        rng, ph = self.rng, phase(day)
        on_trip = sender == "B" and TRIP[0] <= day <= TRIP[1]
        roll = rng.random()
        sticker = .20 if sender == "A" else .11
        image = .04 if sender == "A" else (.12 if on_trip else .03)
        if roll < sticker:
            return "sticker", ""
        if roll < sticker + image:
            return "image", ""
        if roll < sticker + image + .012:
            return "voice", ""
        if roll < sticker + image + .015:
            return "video", ""
        weeks_together = max(0, (day - TOGETHER).days) / 7
        sweet = {"met": .02, "apart": .03, "together": min(.14, .07 + .008 * weeks_together)}[ph]
        roll = rng.random()
        if roll < sweet:
            text = rng.choice(SWEET[sender])
        elif roll < sweet + .02:
            text = rng.choice(CARE)
        elif roll < sweet + .02 + (.30 if sender == "A" else .26):
            text = pick(rng, REACT[sender])
        else:
            pool = TALK[sender] + (TRIP_TALK * 3 if on_trip else [])
            text = rng.choice(pool)
            if rng.random() < (.10 if sender == "A" else .30):      # B writes longer messages
                text += "，" + rng.choice(pool)
        quote = .04 if sender == "A" else .13
        return ("quote" if rng.random() < quote else "text"), text

    def session(self, start, day, turns):
        rng = self.rng
        sender = "A" if rng.random() < .57 else "B"
        when = start
        for _ in range(turns):
            kind, text = self.line(sender, day)
            self.add(when, sender, kind, text)
            burst = .45 if sender == "A" else .22        # A sends several short messages in a row
            if rng.random() < burst:
                when += dt.timedelta(seconds=rng.randint(2, 12))
                continue
            sender = "B" if sender == "A" else "A"
            mean = 2.6 if sender == "A" else 3.0          # log-seconds: A answers a little faster
            gap = math.exp(rng.gauss(mean, .9))
            if rng.random() < .05:
                gap = rng.uniform(300, 2400)              # someone steps away for a while
            when += dt.timedelta(seconds=gap)
        return when


def start_time(rng, day):
    """A session start as a Shanghai clock time; the windows change once the clocks split."""
    if day < APART:      # same city: evenings, a little at lunch, now and then past midnight
        hour = pick(rng, [(12, 2), (13, 1), (18, 1), (19, 2), (20, 4), (21, 5), (22, 5), (23, 3), (0, 1)])
    else:                # B's evening and late night = A's afternoon; B's lunch = A's morning; B's morning = A's late night
        hour = pick(rng, [(20, 4), (21, 6), (22, 6), (23, 4), (0, 2), (1, 1), (12, 3), (13, 3), (14, 1), (6, 1), (7, 2), (8, 1), (16, 1)])
    when = dt.datetime.combine(day, dt.time(hour, rng.randrange(60), rng.randrange(60)), tzinfo=SH)
    return when + dt.timedelta(days=1) if hour < 2 else when


def rituals(chat, day):
    """Greetings, good nights and calls: the small daily habits."""
    rng, ph = chat.rng, phase(day)
    weekend = day.weekday() >= 5
    if day < APART:
        if rng.random() < .45:
            night = dt.datetime.combine(day, dt.time(23, rng.randrange(20, 59)), tzinfo=SH)
            first = rng.choice("AB")
            chat.add(night, first, text=rng.choice(["晚安", "我睡啦，晚安"]))
            if rng.random() < .8:
                chat.add(night + dt.timedelta(seconds=rng.randint(15, 200)), "B" if first == "A" else "A", text=rng.choice(["晚安", "好梦"]))
        if rng.random() < .25:
            chat.add(dt.datetime.combine(day, dt.time(8, rng.randrange(60)), tzinfo=SH), rng.choice("AB"), text=rng.choice(["早安", "早上好"]))
        return
    # B's bedtime (Shanghai, around midnight) is A's afternoon in Berlin.
    if rng.random() < .85:
        night = dt.datetime.combine(day, dt.time(23, rng.randrange(10, 59)), tzinfo=SH) + dt.timedelta(minutes=rng.randrange(0, 70))
        chat.add(night, "B", text=rng.choice(["晚安", "我先睡啦，晚安", "困了，晚安"]))
        if rng.random() < .85:
            reply = rng.choice(["晚安", "好梦", "晚安，早点睡", "睡个好觉"]) if rng.random() < .8 else "好的"
            chat.add(night + dt.timedelta(seconds=rng.randint(10, 400)), "A", text=reply)
        if rng.random() < .3:
            chat.add(night + dt.timedelta(seconds=rng.randint(420, 600)), "B", text=rng.choice(["今天也加油", "祝你今天上课顺利"]))
    # A's bedtime (Berlin, after midnight) is B's morning in Shanghai.
    if rng.random() < .55:
        night = dt.datetime.combine(day, dt.time(0, rng.randrange(0, 59)), tzinfo=BER) + dt.timedelta(days=1)
        chat.add(night, "A", text=rng.choice(["晚安", "我也睡啦，晚安", "好梦"]))
        if rng.random() < .75:
            chat.add(night + dt.timedelta(seconds=rng.randint(20, 500)), "B", text=rng.choice(["早安", "早上好", "晚安，我起床了", "今天也加油"]))
    # Morning greetings on each person's own clock.
    if rng.random() < .5:
        chat.add(dt.datetime.combine(day, dt.time(7, rng.randrange(20, 59)), tzinfo=SH), "B", text=rng.choice(["早安", "早上好", "早呀"]))
    if rng.random() < .45:
        morning = dt.datetime.combine(day, dt.time(8, rng.randrange(60)), tzinfo=BER)
        chat.add(morning, "A", text=rng.choice(["早安", "早上好", "早呀"]))
        if rng.random() < .25:
            chat.add(morning + dt.timedelta(seconds=rng.randint(30, 300)), "B", text="晚上好")
    if rng.random() < .12:
        chat.add(dt.datetime.combine(day, dt.time(19, rng.randrange(60)), tzinfo=SH), "B", text="晚上好")
    # Calls: more once they are together, more at weekends, more often placed by B.
    expected = {"apart": .5, "together": 1.6}[ph] * (1.5 if weekend else 1) * (.7 if day >= QUIET else 1)
    for _ in range(sum(rng.random() < expected / 4 for _ in range(4))):
        hour = pick(rng, [(21, 4), (22, 4), (13, 2), (7, 1)])
        chat.add(dt.datetime.combine(day, dt.time(hour, rng.randrange(60)), tzinfo=SH), "B" if rng.random() < .62 else "A", kind="call")


def main(path):
    rng = random.Random(SEED)
    chat = Chat(rng)
    day = FIRST
    while day <= LAST:
        ph = phase(day)
        level = {"met": 1.0, "apart": 2.4, "together": 4.2}[ph]
        if day.weekday() >= 5:
            level *= 1.3
        if TRIP[0] <= day <= TRIP[1]:
            level *= 1.5
        if day >= QUIET:
            level *= .7
        if ph == "met" and rng.random() < .22:
            level = 0                                   # some silent days before they are close
        sessions = sum(rng.random() < level / 8 for _ in range(8))
        for _ in range(sessions):
            turns = max(2, int(rng.expovariate(1 / {"met": 9, "apart": 14, "together": 20}[ph])))
            chat.session(start_time(rng, day), day, turns)
        rituals(chat, day)
        day += dt.timedelta(days=1)
    end = dt.datetime.combine(LAST, dt.time(23, 59, 59), tzinfo=SH)
    rows = sorted((r for r in chat.rows if r[0] <= end), key=lambda r: r[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "sender", "kind", "text"])
        for ts, sender, kind, text in rows:
            w.writerow([ts.astimezone(dt.timezone.utc).isoformat(), sender, kind, text])
    print(f"wrote {len(rows)} synthetic messages to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/synthetic/messages.csv")
