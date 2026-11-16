"""Calls: applies when the export contains call events.

Figure: calls_weekly.
"""
from __future__ import annotations

from ..plotting import COLOR, plt
from ..prepare import Context
from ..profile import KEYS

GROUP = "calls"


def run(ctx: Context) -> None:
    f = ctx.facts
    calls = ctx.df[ctx.df["kind"] == "call"]
    if calls.empty:
        f.module(GROUP, False, "导出中没有通话事件")
        return
    f.module(GROUP, True, "导出通常只有通话事件的时间戳，没有时长和接通状态；不要据此推算通话次数或总时长")
    f.add("calls.events", len(calls), "通话事件记录数（不等于已接通次数）", module=GROUP)
    f.add("calls.days", int(calls["day"].nunique()), "有通话事件的天数", module=GROUP)
    f.add("calls.per_day", len(calls) / max(1, len(ctx.days)), "平均每天的通话事件数", module=GROUP)
    for k in KEYS:
        f.add(f"calls.events.{k}", int((calls["sender"] == k).sum()), f"记在{ctx.label(k)}名下的通话事件数（是否等于拨出方取决于导出工具）", module=GROUP)
    weekly = calls.groupby(["week", "sender"]).size().unstack(fill_value=0).reindex(ctx.weeks, fill_value=0).reindex(columns=list(KEYS), fill_value=0)
    fig, ax = plt.subplots(figsize=(10.5, 3.4))
    idx = range(len(ctx.weeks))
    ax.bar(idx, weekly["A"], color=COLOR["A"], width=.7, label=f"记在{ctx.label('A')}名下")
    ax.bar(idx, weekly["B"], bottom=weekly["A"], color=COLOR["B"], width=.7, label=f"记在{ctx.label('B')}名下")
    total = weekly.sum(axis=1)
    for i, v in enumerate(total):
        ax.text(i, v + max(total) * .02, str(int(v)), ha="center", fontsize=8)
    ax.set_xticks(list(idx), [w.strftime("%m-%d") for w in ctx.weeks], rotation=45)
    ax.set(ylabel="通话事件记录数", xlabel="周（周一起）", ylim=(0, max(total) * 1.2))
    ax.legend()
    ctx.figure(fig, "calls_weekly", "通话事件的逐周分布", GROUP, "每周的通话事件记录数，按记在谁名下分色；文字之外的陪伴有多少发生在电话里")
