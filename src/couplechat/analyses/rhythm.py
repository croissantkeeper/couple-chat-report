"""Daily rhythm on each person's own clock. Works for any couple, same city or not.

Figures: weekday_hour, weekly_hours, hourly_spread, late_night.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..plotting import COLOR, HEAT, PALETTE, WEEKDAYS, plt
from ..prepare import Context, stage_label
from ..profile import KEYS

GROUP = "rhythm"
NIGHT_HOURS = range(0, 6)   # local 00:00-05:59


def run(ctx: Context) -> None:
    ctx.facts.module(GROUP, True, "按各自当地时间统计；深夜指当地 0 点至 6 点，只记录发言时间，不代表实际作息")
    for k in KEYS:
        mine = ctx.text[ctx.text["sender"] == k]
        if len(mine):
            ctx.facts.add(f"rhythm.peak_local_hour.{k}", int(mine["local_hour"].mode().iloc[0]), f"{ctx.label(k)}发文字最多的当地小时", module=GROUP)
    _weekday_hour(ctx)
    _weekly_hours(ctx)
    _hourly_spread(ctx)
    _late_night(ctx)


def _weekday_hour(ctx: Context) -> None:
    mats = {}
    for k in KEYS:
        mine = ctx.text[ctx.text["sender"] == k]
        count = mine.groupby(["weekday", "local_hour"]).size().unstack(fill_value=0).reindex(index=range(7), columns=range(24), fill_value=0)
        n_days = mine.groupby("weekday")["local_day"].nunique().reindex(range(7), fill_value=0).replace(0, np.nan)
        mats[k] = count.div(n_days, axis=0).values
    vmax = np.nanmax([np.nanmax(m) for m in mats.values()]) or 1
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
    for ax, k in zip(axes, KEYS):
        im = ax.imshow(mats[k], aspect="auto", cmap=HEAT, vmin=0, vmax=vmax)
        ax.set_xticks(range(0, 24, 3))
        ax.set_yticks(range(7), [f"周{d}" for d in WEEKDAYS])
        ax.set(title=ctx.label(k), xlabel="本人当地小时")
    fig.subplots_adjust(right=.89, wspace=.18)
    fig.colorbar(im, cax=fig.add_axes([.91, .18, .015, .65]), label="文字条数 / 有发言的当地日")
    ctx.figure(fig, "weekday_hour", "星期与当地小时", GROUP, "两人各自按星期和当地小时的发言强度；用于看工作日与周末、一天中各时段的差别")


def _weekly_hours(ctx: Context) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, max(3.5, .42 * len(ctx.weeks) + 1)))
    mats = {}
    for k in KEYS:
        mine = ctx.text[ctx.text["sender"] == k]
        count = mine.groupby(["week", "local_hour"]).size().unstack(fill_value=0).reindex(index=ctx.weeks, columns=range(24), fill_value=0)
        mats[k] = (100 * count.div(count.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0).values
    vmax = max(m.max() for m in mats.values()) or 1
    changes = _stage_change_days(ctx)
    for ax, k in zip(axes, KEYS):
        im = ax.imshow(mats[k], aspect="auto", cmap=HEAT, vmin=0, vmax=vmax)
        ax.set_xticks(range(0, 24, 3))
        ax.set_yticks(range(len(ctx.weeks)), [w.strftime("%m-%d") for w in ctx.weeks])
        ax.set(title=ctx.label(k), xlabel="本人当地小时", ylabel="周（周一起）")
        for day in changes:
            week = day - dt.timedelta(days=day.weekday())
            if week in ctx.weeks:
                ax.axhline(ctx.weeks.index(week) - .5, ls="--", color=PALETTE["brown"], lw=1)
    fig.subplots_adjust(right=.88, wspace=.3)
    fig.colorbar(im, cax=fig.add_axes([.91, .18, .015, .65]), label="占本人当周文字的比例 (%)")
    ctx.figure(fig, "weekly_hours", "逐周聊天的小时分布", GROUP, "每周文字在一天各小时的占比，虚线为时差变化；用于看聊天时段是否逐渐固定、何时发生平移")


def _stage_change_days(ctx: Context) -> list:
    per_day = ctx.df.groupby("day")["gap"].agg(lambda s: s.mode().iloc[0])
    return [day for day, prev, cur in zip(per_day.index[1:], per_day.values[:-1], per_day.values[1:]) if prev != cur and cur in ctx.stages]


def _hourly_spread(ctx: Context) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
    for ax, k in zip(axes, KEYS):
        mine = ctx.text[ctx.text["sender"] == k]
        days = sorted(set(mine["local_day"]))[1:-1] or sorted(set(mine["local_day"]))
        mat = mine.groupby(["local_day", "local_hour"]).size().unstack(fill_value=0).reindex(index=days, columns=range(24), fill_value=0).values
        q1, med, q3 = np.quantile(mat, [.25, .5, .75], axis=0) if len(mat) else np.zeros((3, 24))
        ax.bar(range(24), mat.mean(axis=0) if len(mat) else np.zeros(24), color=COLOR[k], alpha=.9, label="均值")
        ax.vlines(range(24), q1, q3, color=PALETTE["brown"], lw=1, label="四分位区间")
        ax.scatter(range(24), med, color=PALETTE["brown"], s=10, label="中位数", zorder=3)
        ax.set(title=f"{ctx.label(k)}｜n={len(days)} 个当地日", ylabel="文字条数 / 当地日·小时")
        ax.legend(ncol=3, fontsize=7)
    axes[-1].set_xticks(range(24))
    axes[-1].set_xlabel("本人当地小时")
    fig.tight_layout()
    ctx.figure(fig, "hourly_spread", "各小时的均值、中位数与日际波动", GROUP, "每个当地小时的平均文字量、中位数和四分位区间；均值远高于中位数表示只有部分日子在该时段很密集")


def _late_night(ctx: Context) -> None:
    rows = []
    for gap in ctx.stages:
        for k in KEYS:
            mine = ctx.text[(ctx.text["sender"] == k) & (ctx.text["gap"] == gap)]
            night = mine[mine["local_hour"].isin(NIGHT_HOURS)]
            active, night_days = mine["local_day"].nunique(), night["local_day"].nunique()
            rows.append({"stage": stage_label(gap), "gap": gap, "person": k, "records": len(mine),
                         "night_text_share": 100 * len(night) / max(1, len(mine)), "night_day_share": 100 * night_days / max(1, active)})
    table = pd.DataFrame(rows)
    ctx.table("late_night.csv", table)
    for r in rows:
        tag = f"gap{abs(r['gap']):g}"
        ctx.facts.add(f"rhythm.night_text_share.{tag}.{r['person']}", r["night_text_share"], f"{r['stage']}期间，{ctx.label(r['person'])}的文字发生在当地 0-6 点的比例", unit="%", module=GROUP)
        ctx.facts.add(f"rhythm.night_day_share.{tag}.{r['person']}", r["night_day_share"], f"{r['stage']}期间，{ctx.label(r['person'])}有文字的当地日中出现深夜发言的比例", unit="%", module=GROUP)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.7))
    x = np.arange(len(ctx.stages))
    for ax, key, title in zip(axes, ("night_text_share", "night_day_share"), ("深夜文字占全部文字的比例", "有深夜发言的天数比例")):
        for j, k in enumerate(KEYS):
            vals = table[table["person"] == k][key].values
            ax.bar(x + (j - .5) * .32, vals, width=.32, color=COLOR[k], label=ctx.label(k))
        ax.set_xticks(x, [stage_label(g) for g in ctx.stages])
        ax.set(ylabel="比例 (%)", title=title)
        ax.legend()
    fig.tight_layout()
    ctx.figure(fig, "late_night", "深夜聊天的比例与覆盖天数", GROUP, "按时差阶段比较两人在当地 0-6 点的文字占比，以及有深夜发言的天数占比；两者方向可以不同")
