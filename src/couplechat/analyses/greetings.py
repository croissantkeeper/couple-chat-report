"""Greetings and wishes: when they are sent on each clock, and how the two people answer each other.

Figures: greeting_clocks, greeting_pairs.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import yaml

from ..plotting import COLOR, HEAT, plt, text_color
from ..prepare import Context
from ..profile import KEYS, ROOT

GROUP = "greetings"
MIN_MATCHES = 10
PAIR_MINUTES = 10
SLEEP = "sleep_wish"


def _wide_night(hours: pd.Series) -> pd.Series:
    return (hours >= 20) | (hours < 6)


def run(ctx: Context) -> None:
    f = ctx.facts
    rules = yaml.safe_load((ROOT / "lexicons" / "greetings.yaml").read_text(encoding="utf-8"))
    patterns = {name: re.compile(rule["pattern"], re.I) for name, rule in rules.items()}
    labels = {name: rule["label"] for name, rule in rules.items()}
    names = list(patterns)
    text = ctx.text.copy()
    for name, rx in patterns.items():
        text[name] = text["clean"].apply(lambda s: bool(rx.search(s)))
    cues = text[text[names].any(axis=1)]
    if len(cues) < MIN_MATCHES:
        f.module(GROUP, False, f"匹配到的问候与祝愿只有 {len(cues)} 条，少于 {MIN_MATCHES} 条")
        return
    f.module(GROUP, True, "按 lexicons/greetings.yaml 的规则匹配；夜间指当地 20 点至次日 6 点；配对只依据时间相邻，不逐条确认语义")
    for name in names:
        for k in KEYS:
            f.add(f"greetings.{name}.count.{k}", int((cues[name] & (cues["sender"] == k)).sum()), f"{ctx.label(k)}发出的{labels[name]}条数", module=GROUP)

    # Direction of sleep wishes, on days when the two clocks differ.
    apart = ctx.shared.get("apart_days", set())
    wishes = cues[cues[SLEEP] & cues["day"].isin(apart)] if SLEEP in names else cues.iloc[0:0]
    direction = {}
    for k in KEYS:
        mine = wishes[wishes["sender"] == k]
        if len(mine) < 5:
            continue
        direction[k] = (100 * float(_wide_night(mine["local_hour"]).mean()), 100 * float(_wide_night(mine["other_hour"]).mean()))
        f.add(f"tz.sleep_wish.count.{k}", len(mine), f"异地期间{ctx.label(k)}发出的睡眠祝愿条数", module=GROUP)
        f.add(f"tz.sleep_wish.in_sender_night.{k}", direction[k][0], f"{ctx.label(k)}的睡眠祝愿落在自己当地夜间的比例", unit="%", module=GROUP)
        f.add(f"tz.sleep_wish.in_receiver_night.{k}", direction[k][1], f"{ctx.label(k)}的睡眠祝愿落在对方当地夜间的比例", unit="%", module=GROUP)

    # Pairs: a cue followed within PAIR_MINUTES by a cue from the other person.
    matrix = np.zeros((len(names), len(names)), int)
    rows = cues[["ts", "sender"] + names].to_dict("records")
    pairs = 0
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if (b["ts"] - a["ts"]).total_seconds() > PAIR_MINUTES * 60:
                break
            if a["sender"] != b["sender"]:
                pairs += 1
                for x, n1 in enumerate(names):
                    for y, n2 in enumerate(names):
                        matrix[x, y] += int(a[n1] and b[n2])
                break
    f.add("greetings.pairs", pairs, f"一方的问候或祝愿在 {PAIR_MINUTES} 分钟内得到对方问候或祝愿的次数", module=GROUP)
    for x, n1 in enumerate(names):
        for y, n2 in enumerate(names):
            if matrix[x, y]:
                f.add(f"greetings.pair.{n1}.{n2}", int(matrix[x, y]), f"先有“{labels[n1]}”、{PAIR_MINUTES} 分钟内对方回以“{labels[n2]}”的次数", module=GROUP)
    _clocks(ctx, cues, names, labels)
    _pairs(ctx, matrix, [labels[n] for n in names], direction)


def _clocks(ctx: Context, cues: pd.DataFrame, names: list[str], labels: dict) -> None:
    cols = 2
    rows = -(-len(names) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 3.4 * rows), sharex=True, squeeze=False)
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    for ax, name in zip(axes.ravel(), names):
        counts = []
        for k in KEYS:
            mine = cues[cues[name] & (cues["sender"] == k)]
            counts.append(len(mine))
            for col, ls, label in (("local_hour", "-", "发送者时钟"), ("other_hour", "--", "接收者时钟")):
                ax.plot(range(24), mine.groupby(col).size().reindex(range(24), fill_value=0), color=COLOR[k], ls=ls, lw=1.6, label=f"{ctx.label(k)}：{label}")
        ax.set(title=f"{labels[name]}｜{ctx.label('A')} {counts[0]} 条，{ctx.label('B')} {counts[1]} 条", ylabel="条数")
        ax.legend(fontsize=6.5)
    for ax in axes[-1]:
        ax.set_xlabel("所示时钟的小时")
        ax.set_xticks(range(0, 24, 3))
    fig.tight_layout()
    ctx.figure(fig, "greeting_clocks", "问候与祝愿在两套时钟下的分布", GROUP, "每类问候按发送者时钟（实线）和接收者时钟（虚线）统计的小时分布；两条线错开说明问候是按对方的时间发的")


def _pairs(ctx: Context, matrix: np.ndarray, names: list[str], direction: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw={"width_ratios": [1.35, 1]})
    vmax = max(1, int(matrix.max()))
    axes[0].imshow(matrix, cmap=HEAT, vmin=0, vmax=vmax)
    axes[0].set_xticks(range(len(names)), names, rotation=25)
    axes[0].set_yticks(range(len(names)), names)
    axes[0].set(xlabel=f"{PAIR_MINUTES} 分钟内对方的回应", ylabel="先发出的", title="问候是怎样被接住的")
    for i in range(len(names)):
        for j in range(len(names)):
            axes[0].text(j, i, str(matrix[i, j]), ha="center", va="center", color=text_color(matrix[i, j], vmax))
    if direction:
        for j, k in enumerate(KEYS):
            if k in direction:
                axes[1].bar(np.arange(2) + (j - .5) * .32, direction[k], width=.32, color=COLOR[k], label=ctx.label(k))
        axes[1].set_xticks(range(2), ["自己的夜间", "对方的夜间"])
        axes[1].set(ylabel="睡眠祝愿落在夜间的比例 (%)", title="晚安是说给谁的夜晚", ylim=(0, 105))
        axes[1].legend()
    else:
        axes[1].axis("off")
    fig.tight_layout()
    ctx.figure(fig, "greeting_pairs", "问候的衔接与晚安的方向", GROUP, "左为先后两句问候的类型配对次数，右为异地期间睡眠祝愿分别落在发送者和接收者夜间的比例")
