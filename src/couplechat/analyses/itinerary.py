"""Itinerary: applies when someone's profile lists more than one location segment.

Figure: itinerary.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from ..plotting import BANDS, PALETTE, plt
from ..prepare import Context
from ..profile import KEYS

GROUP = "itinerary"


def run(ctx: Context) -> None:
    f = ctx.facts
    movers = [k for k in KEYS if len(ctx.profile.people[k].locations) > 1]
    if not movers:
        f.module(GROUP, False, "profile 中没有人填写多段行程")
        return
    f.module(GROUP, True, "行程由当事人提供；各段长短不一，天数很少的段只适合描述，不适合比较")
    calls = ctx.df[ctx.df["kind"] == "call"].groupby("day").size().reindex(ctx.days, fill_value=0)
    daily = ctx.daily["total"]
    segments, meta = [], []
    for k in movers:
        for i, seg in enumerate(ctx.profile.people[k].locations, 1):
            part = daily[(daily.index >= seg.first) & (daily.index <= seg.last)]
            if part.empty:
                continue
            base, where = f"itinerary.{k}.seg{i}", f"{ctx.label(k)}在{seg.city}（{seg.first} 至 {seg.last}）"
            median, per_day = float(part.median()), float(calls[part.index].sum() / len(part))
            f.add(f"{base}.days", len(part), f"{where}期间落在观察窗口内的天数", module=GROUP)
            f.add(f"{base}.daily_median", median, f"{where}期间每日文字条数中位数", module=GROUP)
            f.add(f"{base}.calls_per_day", per_day, f"{where}期间日均通话事件数", module=GROUP)
            segments.append({"person": k, "city": seg.city, "first": max(seg.first, ctx.days[0]), "last": min(seg.last, ctx.days[-1]), "days": len(part), "median": median, "calls": per_day})
            meta.append({"person": k, "segment": i, "city": seg.city, "first": str(seg.first), "last": str(seg.last)})
    f.meta["itinerary"] = meta
    for rank, (day, n) in enumerate(daily.nlargest(3).items(), 1):
        where = "；".join(f"{ctx.label(k)}在{s.city}" for k in KEYS if (s := ctx.profile.people[k].segment_on(day)))
        f.add(f"itinerary.peak{rank}", int(n), f"文字量第 {rank} 高的一天（{day}）的条数；当天{where or '无行程记录'}", module=GROUP)
    ctx.table("itinerary_segments.csv", pd.DataFrame(segments))
    _figure(ctx, movers, segments, calls)


def _figure(ctx: Context, movers: list[str], segments: list[dict], calls: pd.Series) -> None:
    cities = list(dict.fromkeys(s["city"] for s in segments))
    color = {c: BANDS[i % len(BANDS)] for i, c in enumerate(cities)}
    x = pd.to_datetime(ctx.days)
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.8), gridspec_kw={"height_ratios": [1.35, 1]})
    ax = axes[0]
    lane = 1 / len(movers)       # one horizontal lane of background colour per person who moved
    for s in segments:
        row = movers.index(s["person"])
        ax.axvspan(pd.Timestamp(s["first"]) - pd.Timedelta(hours=12), pd.Timestamp(s["last"]) + pd.Timedelta(hours=12),
                   ymin=1 - (row + 1) * lane, ymax=1 - row * lane, color=color[s["city"]], alpha=.8, lw=0)
    ax.bar(x, ctx.daily["total"].values, color=PALETTE["brown"], width=.8, alpha=.8)
    ax.set(ylabel="文字条数 / 天", xlim=(x[0] - pd.Timedelta(days=1), x[-1] + pd.Timedelta(days=1)))
    handles = [Patch(color=color[c], label=c) for c in cities] + [Patch(color=PALETTE["brown"], alpha=.8, label="每日文字")]
    if calls.sum():
        twin = ax.twinx()
        twin.plot(x, calls.values, color=PALETTE["rose"], lw=1.3, marker="o", ms=2.4)
        twin.set_ylabel("通话事件", color=PALETTE["rose"])
        twin.set_ylim(0, max(1, calls.max()) * 2.2)
        twin.spines["top"].set_visible(False)
        twin.tick_params(axis="y", length=0)
        handles.append(Line2D([], [], color=PALETTE["rose"], marker="o", ms=3, label="通话事件"))
    title = "行程与每日聊天量"
    if len(movers) > 1:
        title += "（背景上半为" + ctx.label(movers[0]) + "，下半为" + ctx.label(movers[1]) + "）"
    ax.set_title(title)
    ax.legend(handles=handles, ncol=min(7, len(handles)), fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.1))
    ax = axes[1]
    pos = np.arange(len(segments))
    ax.bar(pos, [s["median"] for s in segments], color=[color[s["city"]] for s in segments], edgecolor=PALETTE["brown"], lw=.6, width=.62)
    top = max(s["median"] for s in segments) or 1
    for i, s in enumerate(segments):
        ax.text(i, s["median"] + top * .03, f"{s['median']:.0f}", ha="center", fontsize=8)
    ax.set_xticks(pos, [f"{ctx.label(s['person'])}·{s['city']}\n{s['first']:%m.%d}—{s['last']:%m.%d}\nn={s['days']}" for s in segments], fontsize=7.5)
    ax.set(ylabel="典型日文字量（中位数）", ylim=(0, top * 1.3), title="各行程段的典型日文字量")
    fig.tight_layout(h_pad=2.4)
    ctx.figure(fig, "itinerary", "行程与聊天量", GROUP, "背景色为所在城市，柱为每日文字，折线为通话事件；下图为各行程段的典型日文字量；用于看聊天量是否随地点起伏")
