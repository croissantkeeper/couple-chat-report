"""Volume and balance: how much was said, when, by whom, and in which media.

Figures: daily_trend, monthly_distribution, weekly_share, calendar, message_types, length_and_balance.
"""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from ..plotting import COLOR, HEAT, LINE, PALETTE, WEEKDAYS, ecdf, plt, text_color
from ..prepare import Context
from ..profile import KEYS

GROUP = "volume"
KIND_LABEL = {"text": "文字", "quote": "引用回复", "sticker": "表情包", "image": "图片", "voice": "语音", "video": "视频", "call": "通话事件", "other": "其他"}


def run(ctx: Context) -> None:
    f, df, text, daily = ctx.facts, ctx.df, ctx.text, ctx.daily
    f.module(GROUP, True, "适用于任何两人聊天")
    f.meta.update({"first_day": str(ctx.days[0]), "last_day": str(ctx.days[-1]),
                   "labels": {k: ctx.label(k) for k in KEYS}, "session_gap_minutes": ctx.profile.session_gap_minutes})
    f.add("volume.records", len(df), "全部消息记录数（含表情、图片、通话等）")
    f.add("volume.text", len(text), "文字消息条数（含引用回复）")
    f.add("days.calendar", len(ctx.days), "观察窗口覆盖的日历天数")
    f.add("days.with_text", int((daily["total"] > 0).sum()), "有文字消息的天数")
    f.add("daily.median", float(daily["total"].median()), "每日文字条数的中位数（含没有文字的日子）")
    f.add("daily.peak.value", int(daily["total"].max()), "单日文字条数的最大值")
    f.add("daily.peak.date", str(daily["total"].idxmax()), "文字条数最多的那一天")
    for k in KEYS:
        mine, name = text[text["sender"] == k], ctx.label(k)
        f.add(f"volume.text.{k}", len(mine), f"{name}的文字消息条数")
        f.add(f"volume.chars.{k}", int(mine["chars"].sum()), f"{name}的文字总字符数（不含空白）")
        f.add(f"length.median.{k}", float(mine["chars"].median()) if len(mine) else 0.0, f"{name}单条文字的字符数中位数")
        f.add(f"volume.records.share.{k}", 100 * float((df["sender"] == k).mean()), f"{name}占全部记录的比例", unit="%")
        f.add(f"volume.text.share.{k}", 100 * len(mine) / max(1, len(text)), f"{name}占文字消息的比例", unit="%")
        total = max(1, int((df["sender"] == k).sum()))
        for kind in ("sticker", "image", "quote", "voice"):
            n = int(((df["sender"] == k) & (df["kind"] == kind)).sum())
            f.add(f"media.{kind}.{k}", n, f"{name}发出的{KIND_LABEL[kind]}条数")
            f.add(f"media.{kind}.share.{k}", 100 * n / total, f"{KIND_LABEL[kind]}占{name}全部记录的比例", unit="%")
    a, b = f.facts["volume.chars.A"]["value"], f.facts["volume.chars.B"]["value"]
    f.add("volume.chars.diff", abs(a - b), "两人文字总字符数之差的绝对值")
    f.add("volume.chars.diff_share", 100 * abs(a - b) / max(1, a + b), "字符数之差占两人总字符数的比例", unit="%")

    out = daily.reset_index().rename(columns={"index": "day"})
    ctx.table("daily_counts.csv", out)
    _daily_trend(ctx)
    _monthly(ctx)
    _weekly_share(ctx)
    _calendar(ctx)
    _message_types(ctx)
    _length_and_balance(ctx)


def _daily_trend(ctx: Context) -> None:
    x = pd.to_datetime(ctx.days)
    total = pd.Series(ctx.daily["total"].values, index=x)
    fig, ax = plt.subplots(figsize=(10.5, 3.5))
    ax.plot(x, total, color="#987D68", lw=1, label="每日文字")
    ax.plot(x, total.rolling(7, center=True, min_periods=7).mean(), color=PALETTE["rose"], lw=2, label="7日居中平均")
    for m in ctx.profile.milestones:
        ax.axvline(pd.Timestamp(str(m["date"])), color=PALETTE["brown"], lw=.9, ls=":")
        ax.text(pd.Timestamp(str(m["date"])), 1.01, m["label"], transform=ax.get_xaxis_transform(), fontsize=8, ha="center")
    ax.set(ylabel="文字条数 / 天")
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=.15)
    ctx.figure(fig, "daily_trend", "每日文字量与7日均线", GROUP, "整个窗口内每天的文字条数和7日居中平均，竖线为关系节点；用于看整体趋势")


def _monthly(ctx: Context) -> None:
    inner = ctx.daily.loc[ctx.inner_days(), "total"]
    months = sorted({d.strftime("%Y-%m") for d in inner.index})
    rows = []
    fig, ax = plt.subplots(figsize=(max(5, 1.8 * len(months)), 3.3))
    for i, m in enumerate(months):
        v = inner[[d.strftime("%Y-%m") == m for d in inner.index]].values
        q1, med, q3 = np.quantile(v, [.25, .5, .75])
        ax.vlines(i, q1, q3, color=PALETTE["rose"], lw=2)
        ax.scatter(i, med, color=PALETTE["rose"], zorder=3)
        ax.scatter(i, v.mean(), marker="D", facecolors="none", edgecolors=PALETTE["olive"], zorder=3)
        rows.append({"month": m, "days": len(v), "median": med, "q1": q1, "q3": q3, "mean": v.mean()})
        tag = m.replace("-", "_")
        ctx.facts.add(f"monthly.{tag}.median", float(med), f"{m} 每日文字条数中位数（不含导出首尾日）", module=GROUP)
        ctx.facts.add(f"monthly.{tag}.mean", float(v.mean()), f"{m} 每日文字条数均值（不含导出首尾日）", module=GROUP)
    ax.set_xticks(range(len(months)), [f"{r['month']}\nn={r['days']}" for r in rows])
    ax.set(ylabel="文字条数 / 天", xlim=(-.6, len(months) - .4))
    ax.grid(axis="y", alpha=.15)
    ax.set_title("圆点：中位数｜竖线：四分位区间｜菱形：均值", fontsize=8, fontweight="normal", loc="left")
    ctx.table("monthly_distribution.csv", pd.DataFrame(rows))
    ctx.figure(fig, "monthly_distribution", "各月典型日的聊天量", GROUP, "每个月每日文字条数的中位数、四分位区间和均值；均值明显高于中位数说明被少数高峰日拉动")


def _weekly_share(ctx: Context) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 5.3), sharex=True)
    idx = range(len(ctx.weeks))
    for ax, frame, title in zip(axes, (ctx.text, ctx.df), ("文字消息", "全部记录")):
        counts = frame.groupby(["week", "sender"]).size().unstack(fill_value=0).reindex(ctx.weeks, fill_value=0).reindex(columns=list(KEYS), fill_value=0)
        total = counts.sum(axis=1)
        share = (100 * counts["A"] / total.where(total > 0)).fillna(0)
        ax.bar(idx, share, color=COLOR["A"], label=ctx.label("A"))
        ax.bar(idx, (100 - share).where(total > 0, 0), bottom=share, color=COLOR["B"], label=ctx.label("B"))
        ax.axhline(50, color="white", lw=.8, ls="--")
        for i, n in enumerate(total):
            ax.text(i, 102, str(int(n)), ha="center", fontsize=6)
        ax.set(ylim=(0, 110), ylabel="占比 (%)", title=title)
    axes[0].legend(ncol=2, loc="lower left", frameon=True, facecolor="white", framealpha=1)
    axes[1].set_xticks(list(idx), [w.strftime("%m-%d") for w in ctx.weeks], rotation=45)
    axes[1].set_xlabel("周（周一起）")
    ctx.figure(fig, "weekly_share", "双方逐周占比", GROUP, "每周两人在文字和全部记录中的占比，柱顶为当周总量；用于看谁说得多是否逐周轮换")


def _calendar(ctx: Context) -> None:
    daily = ctx.daily["total"]
    months = sorted({(d.year, d.month) for d in ctx.days})
    cols = min(2, len(months))
    rows = -(-len(months) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 3.7 * rows), squeeze=False)
    vmax = max(1, int(daily.max()))
    im = None
    for ax in axes.ravel()[len(months):]:
        ax.axis("off")
    for ax, (year, month) in zip(axes.ravel(), months):
        grid = calendar.monthcalendar(year, month)
        mat = np.full((len(grid), 7), np.nan)
        for i, line in enumerate(grid):
            for j, day in enumerate(line):
                date = pd.Timestamp(year, month, day).date() if day else None
                if date in daily.index:
                    mat[i, j] = daily[date]
        im = ax.imshow(mat, cmap=HEAT, vmin=0, vmax=vmax, aspect="auto")
        for i, line in enumerate(grid):
            for j, day in enumerate(line):
                if not day:
                    continue
                if np.isfinite(mat[i, j]):
                    color = text_color(mat[i, j], vmax)
                    ax.text(j - .42, i - .25, str(day), fontsize=7, color=color)
                    ax.text(j + .4, i + .28, str(int(mat[i, j])), ha="right", fontsize=8, color=color)
                else:
                    ax.text(j, i, str(day), ha="center", color=PALETTE["peach"], fontsize=7)
        ax.set_xticks(range(7), WEEKDAYS)
        ax.set_yticks([])
        ax.set_title(f"{year}年{month}月")
        ax.set_xticks(np.arange(-.5, 7, 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(grid), 1), minor=True)
        ax.grid(which="minor", color="white", lw=2)
        ax.tick_params(which="both", length=0)
    fig.subplots_adjust(right=.88, hspace=.3, wspace=.15)
    fig.colorbar(im, cax=fig.add_axes([.91, .2, .018, .6])).set_label("文字条数 / 天")
    ctx.figure(fig, "calendar", "聊天日历", GROUP, "按月历排列的每日文字条数；用于定位密集和稀疏的日子")


def _message_types(ctx: Context) -> None:
    kinds = list(KIND_LABEL)
    colors = [PALETTE[c] for c in ("brown", "olive", "rose", "peach", "cream", "olive", "rose", "cream")]
    hatches = {"voice": "..", "video": "//", "call": "xx", "other": "++"}
    counts = ctx.df.groupby(["sender", "kind"]).size().unstack(fill_value=0).reindex(index=list(KEYS), columns=kinds, fill_value=0)
    share = 100 * counts.div(counts.sum(axis=1).replace(0, 1), axis=0)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    left = np.zeros(2)
    names = [ctx.label(k) for k in KEYS]
    for kind, color in zip(kinds, colors):
        val = share[kind].values
        ax.barh(names, val, left=left, color=color, label=KIND_LABEL[kind], edgecolor="white", linewidth=.8, hatch=hatches.get(kind, ""))
        for i, v in enumerate(val):
            if v > 5:
                dark = color in (PALETTE["brown"], PALETTE["olive"], PALETTE["rose"])
                ax.text(left[i] + v / 2, i, f"{v:.1f}%", ha="center", va="center", fontsize=8, color="white" if dark else PALETTE["brown"])
        left += val
    ax.set(xlim=(0, 100), xlabel="占各自全部记录的比例 (%)")
    ax.legend(ncol=4, bbox_to_anchor=(.5, -.3), loc="upper center", fontsize=8)
    ctx.table("message_types.csv", counts.reset_index())
    ctx.figure(fig, "message_types", "双方的消息类型构成", GROUP, "文字、引用回复、表情包、图片等在各自全部记录中的占比；用于比较两人的表达媒介")


def _length_and_balance(ctx: Context) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7))
    for k in KEYS:
        ecdf(axes[0], ctx.text.loc[ctx.text["sender"] == k, "chars"], color=COLOR[k], ls=LINE[k], lw=1.8, label=ctx.label(k))
    axes[0].set(xscale="symlog", xlabel="单条文字的字符数", ylabel="累计比例", title="单条长度")
    axes[0].legend()
    chars = ctx.text.groupby(["day", "sender"])["chars"].sum().unstack(fill_value=0).reindex(ctx.days, fill_value=0).reindex(columns=list(KEYS), fill_value=0)
    axes[1].scatter(chars["A"], chars["B"], s=16, alpha=.55, color=PALETTE["rose"])
    lim = max(1, chars.values.max())
    axes[1].plot([0, lim], [0, lim], ls="--", lw=.8, color=PALETTE["brown"])
    axes[1].set(xlabel=f"{ctx.label('A')}：当天字符数", ylabel=f"{ctx.label('B')}：当天字符数", title="每天两人各写了多少")
    fig.tight_layout()
    ctx.figure(fig, "length_and_balance", "单条长度与每日字数对照", GROUP, "左为单条文字长度的累计分布，右为每天两人字符数的散点（虚线表示相等）；用于看谁句子长、两人字数是否对称")
