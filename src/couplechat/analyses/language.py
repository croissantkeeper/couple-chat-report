"""Language: each person's words, the words they share, and whole-message catchphrases.

Everything here is sensitive: vocabulary facts are flagged so they are not sent to the
model unless the profile allows it, and the figures show real words from the chat.

Figures: word_clouds, shared_words, distinctive_words, catchphrases, lexicon_weekly.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from ..plotting import COLOR, HEAT, PALETTE, cjk_font_path, plt
from ..prepare import Context
from ..profile import KEYS, ROOT

GROUP = "language"
_WORD = re.compile(r"[一-鿿]+|[A-Za-z]{2,}")
_LAUGH = [(re.compile(r"哈{2,}"), "哈哈"), (re.compile(r"h{2,}"), "hhh"), (re.compile(r"呜{2,}"), "呜呜"), (re.compile(r"嘿{2,}"), "嘿嘿"), (re.compile(r"嘻{2,}"), "嘻嘻")]
_PUNCT = re.compile(r"[\s，。！？、,.!?~～…]+")
MIN_WEEK_TEXTS = 30


def _stopwords() -> set[str]:
    return set((ROOT / "lexicons" / "stopwords.txt").read_text(encoding="utf-8").split())


def tokenize(text: str, protected: list[str]) -> list[str]:
    """Words of two or more characters. Uses jieba when installed, else two-character grams."""
    text = text.lower()
    for pattern, norm in _LAUGH:       # stretched laughter counts as one word
        text = pattern.sub(f" {norm} ", text)
    try:
        import jieba
    except ImportError:
        jieba = None
    out = []
    for piece in re.split("(" + "|".join(map(re.escape, protected)) + ")", text) if protected else [text]:
        if piece in protected:
            out.append(piece)
        elif jieba:
            out.extend(t for t in jieba.lcut(piece) if len(t) >= 2 and _WORD.fullmatch(t))
        else:
            for run in _WORD.findall(piece):
                out.extend([run] if run.isascii() or len(run) <= 3 else [run[i:i + 2] for i in range(len(run) - 1)])
    return [t for t in out if len(t) >= 2]


def run(ctx: Context) -> None:
    f = ctx.facts
    f.module(GROUP, True, "词频与口头禅属于敏感信息，默认不发送给大模型；未安装 jieba 时按相邻两字切分，结果较粗")
    stop = _stopwords()
    protected = sorted({t for terms in ctx.profile.lexicons.values() for t in terms}, key=len, reverse=True)
    counts = {k: Counter() for k in KEYS}
    term_days = {k: defaultdict(set) for k in KEYS}
    phrases = {k: Counter() for k in KEYS}
    phrase_days = {k: defaultdict(set) for k in KEYS}
    for sender, clean, day in zip(ctx.text["sender"], ctx.text["clean"], ctx.text["day"]):
        for t in tokenize(clean, protected):
            if t not in stop:
                counts[sender][t] += 1
                term_days[sender][t].add(day)
        phrase = _PUNCT.sub("", clean.lower())
        if 2 <= len(phrase) <= 12 and _WORD.search(phrase):
            phrases[sender][phrase] += 1
            phrase_days[sender][phrase].add(day)
    total = {k: max(1, sum(counts[k].values())) for k in KEYS}
    combined = counts["A"] + counts["B"]
    ctx.table("vocabulary.csv", pd.DataFrame([{"term": t, "A": counts["A"][t], "B": counts["B"][t], "days": len(term_days["A"][t] | term_days["B"][t])} for t, _ in combined.most_common()]))
    ctx.table("catchphrases.csv", pd.DataFrame([{"person": k, "phrase": p, "count": n, "days": len(phrase_days[k][p])} for k in KEYS for p, n in phrases[k].most_common(200)]))

    shared = [t for t, _ in combined.most_common() if len(term_days["A"][t] | term_days["B"][t]) >= 3][:25]
    for rank, term in enumerate(shared[:12], 1):
        for k in KEYS:
            f.add(f"vocab.top{rank}.{k}", counts[k][term], f"高频词“{term}”在{ctx.label(k)}文字中的出现次数", module=GROUP, sensitive=True)
    distinct = {}
    for k, other in (("A", "B"), ("B", "A")):
        diff = [(t, 1000 * (counts[k][t] / total[k] - counts[other][t] / total[other])) for t in counts[k] if counts[k][t] >= 10 and len(term_days[k][t]) >= 3]
        distinct[k] = sorted((x for x in diff if x[1] > 0), key=lambda x: -x[1])[:20]
        for rank, (term, _) in enumerate(distinct[k][:5], 1):
            f.add(f"vocab.distinct{rank}.{k}", counts[k][term], f"{ctx.label(k)}的特征词“{term}”出现次数（对方 {counts[other][term]} 次）", module=GROUP, sensitive=True)
    top_phrases = {k: [(p, n) for p, n in phrases[k].most_common() if len(phrase_days[k][p]) >= 3][:15] for k in KEYS}
    for k in KEYS:
        for rank, (p, n) in enumerate(top_phrases[k][:5], 1):
            f.add(f"vocab.phrase{rank}.{k}", n, f"{ctx.label(k)}单独发出整句“{p}”的次数", module=GROUP, sensitive=True)

    for name, terms in ctx.profile.lexicons.items():
        hit = ctx.text["clean"].apply(lambda s: any(t in s for t in terms))
        for k in KEYS:
            mine = ctx.text["sender"] == k
            f.add(f"lexicon.{name}.count.{k}", int((hit & mine).sum()), f"{ctx.label(k)}含“{name}”类词的消息条数", module=GROUP)
            f.add(f"lexicon.{name}.per_1000.{k}", 1000 * float((hit & mine).sum()) / max(1, int(mine.sum())), f"{ctx.label(k)}每千条文字中含“{name}”类词的条数", module=GROUP)

    _word_clouds(ctx, counts, term_days)
    _shared_words(ctx, shared, counts, term_days)
    _distinctive(ctx, distinct)
    _catchphrases(ctx, top_phrases, phrase_days)
    _lexicon_weekly(ctx)


def _word_clouds(ctx: Context, counts, term_days) -> None:
    font_path = cjk_font_path()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    if not font_path:
        return
    width, height = 1500, 650
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 8))
    for ax, k in zip(axes, KEYS):
        rng = np.random.default_rng(43)
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        items = [(w, n) for w, n in counts[k].most_common() if n >= 3 and len(term_days[k][w]) >= 2][:65]
        boxes, placed = [], 0
        rgb = tuple(int(255 * c) for c in plt.matplotlib.colors.to_rgb(COLOR[k]))
        for word, n in items:
            size = int(26 + 85 * (n / items[0][1]) ** .5)
            for _ in range(3):      # try, then shrink and try again
                font = ImageFont.truetype(font_path, size)
                box = draw.textbbox((0, 0), word, font=font)
                w, h = box[2] - box[0], box[3] - box[1]
                spot = None
                for trial in range(350):
                    if w + 12 >= width or h + 12 >= height:
                        break
                    x = (width - w) // 2 if trial == 0 else int(rng.integers(5, width - w - 5))
                    y = (height - h) // 2 if trial == 0 else int(rng.integers(5, height - h - 5))
                    rect = (x - 4, y - 3, x + w + 4, y + h + 3)
                    if all(rect[2] < b[0] or rect[0] > b[2] or rect[3] < b[1] or rect[1] > b[3] for b in boxes):
                        spot = (x, y, rect)
                        break
                if spot:
                    draw.text((spot[0] - box[0], spot[1] - box[1]), word, font=font, fill=rgb)
                    boxes.append(spot[2])
                    placed += 1
                    break
                size = int(size * .8)
        ax.imshow(image)
        ax.set_title(f"{ctx.label(k)}｜{placed} 个词", loc="left")
        ax.axis("off")
    fig.tight_layout()
    ctx.figure(fig, "word_clouds", "两人各自的词云", GROUP, "各自最常用的词，字号只在本人内部可比；用于浏览表达，不用于比较两人的绝对数量")


def _shared_words(ctx: Context, shared, counts, term_days) -> None:
    if not shared:
        return
    fig, (left, mid, right) = plt.subplots(1, 3, figsize=(10, max(3, .32 * len(shared))), sharey=True, gridspec_kw={"width_ratios": [1, .5, 1], "wspace": .01})
    y = np.arange(len(shared))
    limit = max(counts[k][w] for k in KEYS for w in shared) * 1.22
    for ax, k in ((left, "A"), (right, "B")):
        values = [counts[k][w] for w in shared]
        ax.barh(y, values, color=COLOR[k])
        ax.set_xlim(0, limit)
        ax.set_xlabel("出现次数")
        ax.set_title(ctx.label(k))
        for yy, v in zip(y, values):
            ax.text(v + limit * .01, yy, str(v), va="center", ha="right" if k == "A" else "left", fontsize=7)
    left.invert_xaxis()
    left.invert_yaxis()
    left.set_yticks([])
    mid.axis("off")
    for yy, w in enumerate(shared):
        mid.text(.5, yy - .15, w, ha="center", va="center", fontsize=8)
        mid.text(.5, yy + .33, f"{len(term_days['A'][w] | term_days['B'][w])} 天", ha="center", va="center", fontsize=5.5)
    right.tick_params(axis="y", left=False, labelleft=False)
    ctx.figure(fig, "shared_words", "共同高频词的镜像对照", GROUP, "合计最常用的词在两人各自的出现次数，中间小字为出现天数；能同时看出两人都爱用的词和只有一人爱用的词")


def _distinctive(ctx: Context, distinct) -> None:
    if not any(distinct.values()):
        return
    fig, axes = plt.subplots(1, 2, figsize=(10.5, max(3, .36 * max(len(v) for v in distinct.values()) + 1)))
    limit = max((n for v in distinct.values() for _, n in v), default=1) * 1.2
    for ax, k in zip(axes, KEYS):
        v = distinct[k]
        ax.barh(range(len(v)), [n for _, n in v], color=COLOR[k])
        ax.set_yticks(range(len(v)), [w for w, _ in v])
        ax.invert_yaxis()
        ax.set(title=ctx.label(k), xlabel="比对方每千词多出现的次数", xlim=(0, limit))
        for i, (_, n) in enumerate(v):
            ax.text(n + limit * .01, i, f"{n:.1f}", va="center", fontsize=7)
    fig.tight_layout()
    ctx.figure(fig, "distinctive_words", "双方各自更常使用的特征词", GROUP, "每千词频率比对方高出最多的词；衡量的是相对偏好，不是绝对次数")


def _catchphrases(ctx: Context, top, phrase_days) -> None:
    if not any(top.values()):
        return
    fig, axes = plt.subplots(1, 2, figsize=(10.5, max(3, .4 * max(len(v) for v in top.values()) + 1)))
    for ax, k in zip(axes, KEYS):
        v = top[k]
        ax.barh(range(len(v)), [n for _, n in v], color=COLOR[k])
        ax.set_yticks(range(len(v)), [p for p, _ in v])
        ax.invert_yaxis()
        ax.set(title=ctx.label(k), xlabel="整条消息就是这一句的次数", xlim=(0, max((n for _, n in v), default=1) * 1.4))
        for i, (p, n) in enumerate(v):
            ax.text(n, i, f" {n} 次 / {len(phrase_days[k][p])} 天", va="center", fontsize=7)
    fig.tight_layout()
    ctx.figure(fig, "catchphrases", "各自的高频完整短句", GROUP, "整条消息只有这一句的短句排行（至少出现在 3 天）；即两人的口头禅")


def _lexicon_weekly(ctx: Context) -> None:
    names = list(ctx.profile.lexicons)
    mats = {}
    for k in KEYS:
        mat = np.full((len(names), len(ctx.weeks)), np.nan)
        mine = ctx.text[ctx.text["sender"] == k]
        for j, week in enumerate(ctx.weeks):
            part = mine[mine["week"] == week]
            if len(part) < MIN_WEEK_TEXTS:
                continue
            for i, name in enumerate(names):
                terms = ctx.profile.lexicons[name]
                mat[i, j] = 1000 * part["clean"].apply(lambda s: any(t in s for t in terms)).mean()
        mats[k] = mat
    if all(np.isnan(m).all() for m in mats.values()):
        return
    vmax = np.nanmax([np.nanmax(m) if not np.isnan(m).all() else 0 for m in mats.values()]) or 1
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 1.6 + .5 * len(names) * 2), sharex=True)
    for ax, k in zip(axes, KEYS):
        im = ax.imshow(mats[k], aspect="auto", cmap=HEAT, vmin=0, vmax=vmax)
        ax.set_yticks(range(len(names)), names)
        ax.set_title(ctx.label(k), loc="left")
    axes[-1].set_xticks(range(len(ctx.weeks)), [w.strftime("%m-%d") for w in ctx.weeks], rotation=45)
    axes[-1].set_xlabel("周（周一起）")
    fig.subplots_adjust(right=.88, left=.16, hspace=.4)
    fig.colorbar(im, cax=fig.add_axes([.91, .2, .015, .6]), label="每千条文字中的匹配条数")
    ctx.figure(fig, "lexicon_weekly", "各类词组的逐周出现率", GROUP, f"词表中每一类词在每周每千条文字里的出现率，当周文字不足 {MIN_WEEK_TEXTS} 条时留空；用于看亲昵、问候等表达是从什么时候开始变多的")
