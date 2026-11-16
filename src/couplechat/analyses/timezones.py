"""Long-distance: applies when the two clocks differ on enough days.

Figures: two_clocks, clock_change.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..plotting import COLOR, LINE, plt
from ..prepare import Context, stage_label
from ..profile import KEYS
from .rhythm import _stage_change_days

GROUP = "timezones"
MIN_DAYS = 7
WINDOW = 14


def run(ctx: Context) -> None:
    f = ctx.facts
    per_day = ctx.df.groupby("day")["gap"].agg(lambda s: s.mode().iloc[0])
    apart = per_day[per_day != 0]
    if len(apart) < MIN_DAYS:
        f.module(GROUP, False, f"两人时钟不同的天数为 {len(apart)}，少于 {MIN_DAYS} 天")
        return
    f.module(GROUP, True, f"两人时钟不同的天数为 {len(apart)}；非整点时差按四舍五入对齐")
    ctx.shared["apart_days"] = set(apart.index)
    f.add("tz.days_apart", len(apart), "两人处于不同时区的天数", module=GROUP)
    f.add("tz.offset_hours.mode", float(apart.abs().mode().iloc[0]), "最常见的时差", unit="小时", module=GROUP)
    f.add("tz.offset_hours.distinct", len({abs(float(x)) for x in apart}), "出现过的不同时差个数（夏令时切换会让它大于 1）", module=GROUP)
    text = ctx.text[ctx.text["day"].isin(apart.index)]
    for k in KEYS:
        mine = text[text["sender"] == k]
        if len(mine):
            f.add(f"tz.peak_local_hour.{k}", int(mine["local_hour"].mode().iloc[0]), f"异地期间{ctx.label(k)}发文字最多的当地小时", module=GROUP)
    _two_clocks(ctx)
    _clock_change(ctx)


def _two_clocks(ctx: Context) -> None:
    fig, axes = plt.subplots(len(ctx.stages), 1, figsize=(10, 2.7 * len(ctx.stages)), sharex=True, squeeze=False)
    for ax, gap in zip(axes[:, 0], ctx.stages):
        shift = int(round(gap))
        part = ctx.text[ctx.text["gap"] == gap]
        for k in KEYS:
            mine = part[part["sender"] == k]
            rate = mine.groupby("local_hour").size().reindex(range(24), fill_value=0).values / max(1, mine["local_day"].nunique())
            if k == "B":            # put B's curve on A's clock: the same instant is `shift` hours later for B
                rate = np.roll(rate, -shift)
            ax.plot(range(24), rate, color=COLOR[k], ls=LINE[k], lw=2, label=ctx.label(k))
            if len(mine):
                tag = f"gap{abs(gap):g}"
                ctx.facts.add(f"tz.peak_local_hour.{tag}.{k}", int(mine["local_hour"].mode().iloc[0]), f"{stage_label(gap)}期间{ctx.label(k)}发文字最多的当地小时", module=GROUP)
        ax.set_title(stage_label(gap), pad=26)
        ax.set_ylabel("文字条数 / 当地日")
        ax.grid(alpha=.15)
        top = ax.secondary_xaxis("top")
        top.set_xticks(range(0, 24, 3), [f"{(h + shift) % 24:02}:00" for h in range(0, 24, 3)])
        top.tick_params(labelsize=7, pad=1)
        top.set_xlabel(f"{ctx.label('B')}的当地时间", fontsize=7, labelpad=3)
    axes[0, 0].legend(ncol=2)
    axes[-1, 0].set_xticks(range(0, 24, 3), [f"{h:02}:00" for h in range(0, 24, 3)])
    axes[-1, 0].set_xlabel(f"{ctx.label('A')}的当地时间")
    fig.tight_layout(h_pad=2)
    ctx.figure(fig, "two_clocks", "两套时钟下的同一个聊天窗口", GROUP, "每个时差阶段一栏，下轴是 A 的当地时间、上轴是 B 的当地时间，两条曲线已对齐到同一时刻；用于看两人在各自一天的什么时候相遇")


def _clock_change(ctx: Context) -> None:
    """Compare the two weeks before and after the most recent change of the clock gap (e.g. daylight saving)."""
    changes = _stage_change_days(ctx)
    if not changes:
        return
    change = changes[-1]
    before = (change - dt.timedelta(days=WINDOW), change - dt.timedelta(days=1))
    after = (change + dt.timedelta(days=1), change + dt.timedelta(days=WINDOW))
    if before[0] < ctx.days[0] or after[1] > ctx.days[-1]:
        return
    ctx.facts.add("tz.change.date", str(change), "最近一次时差发生变化的日期", module=GROUP)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.3), sharex=True)
    for row, k in enumerate(KEYS):
        for col, clock in enumerate(KEYS):
            ax = axes[row, col]
            for label, (first, last), ls in (("变化前", before, "-"), ("变化后", after, "--")):
                part = ctx.text[(ctx.text["sender"] == k) & (ctx.text[f"day_{clock}"] >= first) & (ctx.text[f"day_{clock}"] <= last)]
                count = part.groupby(f"hour_{clock}").size().reindex(range(24), fill_value=0)
                share = 100 * count / max(1, count.sum())
                ax.plot(range(24), share, color=COLOR[k], ls=ls, lw=1.8, label=f"{label} (n={int(count.sum())})")
                if k == clock and count.sum():
                    tag = "before" if label == "变化前" else "after"
                    ctx.facts.add(f"tz.change.peak_hour.{tag}.{k}", int(count.idxmax()), f"时差{label}两周，{ctx.label(k)}在自己时钟上发文字最多的小时", module=GROUP)
            ax.set(title=f"{ctx.label(k)}的文字｜按{ctx.label(clock)}的时钟", ylabel="占窗口文字的比例 (%)")
            ax.legend(fontsize=7)
            ax.grid(alpha=.12)
    for ax in axes[-1]:
        ax.set_xlabel("所示时钟的小时")
        ax.set_xticks(range(0, 24, 3))
    fig.tight_layout()
    ctx.figure(fig, "clock_change", "时差变化前后两套时钟下的分布", GROUP, f"时差在 {change} 发生变化，比较前后各 {WINDOW} 天两人文字在两套时钟上的分布；用于看是谁的时钟吸收了这次变化")
