"""Relationship timeline: phases between the milestones in the profile, and a recent-versus-before comparison.

Figures: phase_timeline (needs milestones), recent_comparison (needs enough days).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..plotting import COLOR, PALETTE, plt
from ..prepare import Context
from ..profile import KEYS

GROUP = "relationship"
WINDOW = 14


def _rate(text: pd.DataFrame, terms: list[str]) -> float:
    return 1000 * float(text["clean"].apply(lambda s: any(t in s for t in terms)).mean()) if len(text) else 0.0


def run(ctx: Context) -> None:
    f = ctx.facts
    if not ctx.profile.milestones:
        f.module("phases", False, "profile 中没有提供关系节点")
    else:
        phases = ctx.profile.phases(ctx.days[0], ctx.days[-1])
        f.module("phases", True, f"按 {len(phases)} 个阶段划分；节点在短期内相继发生时，无法分离各自的影响")
        f.meta["phases"] = [{"key": p["key"], "label": p["label"], "first": str(p["first"]), "last": str(p["last"])} for p in phases]
        sessions = ctx.shared.get("sessions")
        affection = ctx.profile.lexicons.get("affection", [])
        for p in phases:
            part = ctx.daily[(ctx.daily.index >= p["first"]) & (ctx.daily.index <= p["last"])]["total"]
            where = f"“{p['label']}”阶段"
            f.add(f"phase.{p['key']}.days", len(part), f"{where}的天数", module="phases")
            f.add(f"phase.{p['key']}.daily_median", float(part.median()), f"{where}每日文字条数中位数", module="phases")
            f.add(f"phase.{p['key']}.daily_mean", float(part.mean()), f"{where}每日文字条数均值", module="phases")
            f.add(f"phase.{p['key']}.active_share", 100 * float((part > 0).mean()), f"{where}有文字的天数比例", unit="%", module="phases")
            if sessions is not None:
                s = sessions[(sessions["day"] >= p["first"]) & (sessions["day"] <= p["last"]) & sessions["both"]]
                f.add(f"phase.{p['key']}.sessions_per_day", len(s) / max(1, len(part)), f"{where}平均每天的双人会话数", module="phases")
                if len(s):
                    f.add(f"phase.{p['key']}.session_span_median_min", float(s["duration_min"].median()), f"{where}双人会话跨度中位数", unit="分钟", module="phases")
            text = ctx.text[(ctx.text["day"] >= p["first"]) & (ctx.text["day"] <= p["last"])]
            for k in KEYS:
                p[f"affection_{k}"] = _rate(text[text["sender"] == k], affection)
                f.add(f"phase.{p['key']}.affection_per_1000.{k}", p[f"affection_{k}"], f"{where}{ctx.label(k)}每千条文字中含亲昵词的条数", module="phases")
        _phase_timeline(ctx, phases)
    _recent(ctx)


def _phase_timeline(ctx: Context, phases: list[dict]) -> None:
    x = pd.to_datetime(ctx.days)
    total = pd.Series(ctx.daily["total"].values, index=x)
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7), gridspec_kw={"height_ratios": [1.3, 1]})
    ax = axes[0]
    ax.plot(x, total, color="#987D68", lw=.9, label="每日文字")
    ax.plot(x, total.rolling(7, center=True, min_periods=7).mean(), color=PALETTE["rose"], lw=2.2, label="7日平均")
    for i, m in enumerate(ctx.profile.milestones):
        when = pd.Timestamp(str(m["date"]))
        ax.axvline(when, color=PALETTE["brown"], ls=":", lw=1.1)
        ax.annotate(f"{when:%m.%d} {m['label']}", (when, .93 - .16 * (i % 3)), xycoords=("data", "axes fraction"), xytext=(6, 0),
                    textcoords="offset points", fontsize=9, bbox={"facecolor": "white", "edgecolor": "none", "alpha": .85})
    ax.set(ylabel="文字条数 / 天", title="关系节点与每日聊天量")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=.15)
    ax = axes[1]
    pos = np.arange(len(phases))
    for j, k in enumerate(KEYS):
        ax.bar(pos + (j - .5) * .33, [p[f"affection_{k}"] for p in phases], width=.33, color=COLOR[k], label=ctx.label(k))
    ax.set_xticks(pos, [f"{p['label']}\n{(p['last'] - p['first']).days + 1} 天" for p in phases])
    ax.set(ylabel="亲昵词匹配 / 千条文字", title="同一词表下，亲昵表达的阶段变化")
    ax.legend()
    ax.grid(axis="y", alpha=.15)
    fig.tight_layout(h_pad=2)
    ctx.figure(fig, "phase_timeline", "关系时间线与亲昵表达的阶段变化", GROUP, "上为每日文字量与关系节点，下为各阶段两人每千条文字中的亲昵词条数；用于讲关系是怎样发展的")


def _windows(ctx: Context):
    custom = ctx.profile.story.get("compare_windows")
    if custom:
        return [(dt.date.fromisoformat(str(a)), dt.date.fromisoformat(str(b))) for a, b in custom]
    inner = ctx.inner_days()
    if len(inner) < 2 * WINDOW + 7:
        return None
    last = inner[-1]
    return [(last - dt.timedelta(days=2 * WINDOW - 1), last - dt.timedelta(days=WINDOW)), (last - dt.timedelta(days=WINDOW - 1), last)]


def _recent(ctx: Context) -> None:
    f = ctx.facts
    windows = _windows(ctx)
    if not windows:
        f.module("recent", False, f"观察窗口不足以取出两个 {WINDOW} 天的对照窗口")
        return
    f.module("recent", True, "比较两个等长窗口；两周的波动不足以说明长期趋势")
    f.meta["recent_windows"] = [{"first": str(a), "last": str(b)} for a, b in windows]
    sessions = ctx.shared.get("sessions")
    affection = ctx.profile.lexicons.get("affection", [])
    stats = []
    for tag, (first, last) in zip(("before", "recent"), windows):
        label = f"{first:%m.%d}—{last:%m.%d}"
        days = ctx.daily[(ctx.daily.index >= first) & (ctx.daily.index <= last)]
        text = ctx.text[(ctx.text["day"] >= first) & (ctx.text["day"] <= last)]
        row = {"label": label, "daily_median": float(days["total"].median()), "span": 0.0, "per_day": 0.0}
        f.add(f"recent.{tag}.text", len(text), f"{label} 的文字条数", module="recent")
        f.add(f"recent.{tag}.chars", int(text["chars"].sum()), f"{label} 的文字总字符数", module="recent")
        f.add(f"recent.{tag}.days_with_text", int((days["total"] > 0).sum()), f"{label} 有文字的天数", module="recent")
        f.add(f"recent.{tag}.daily_median", row["daily_median"], f"{label} 每日文字条数中位数", module="recent")
        f.add(f"recent.{tag}.calls", int(((ctx.df["kind"] == "call") & (ctx.df["day"] >= first) & (ctx.df["day"] <= last)).sum()), f"{label} 的通话事件数", module="recent")
        if sessions is not None:
            s = sessions[(sessions["day"] >= first) & (sessions["day"] <= last)]
            two = s[s["both"]]
            row["span"] = float(two["duration_min"].median()) if len(two) else 0.0
            row["per_day"] = len(two) / max(1, len(days))
            f.add(f"recent.{tag}.sessions_two_person", len(two), f"{label} 的双人会话数", module="recent")
            f.add(f"recent.{tag}.session_span_median_min", row["span"], f"{label} 双人会话跨度中位数", unit="分钟", module="recent")
            f.add(f"recent.{tag}.start_share.A", 100 * float((s["initiator"] == "A").mean()) if len(s) else 0.0, f"{label} 由{ctx.label('A')}开启的会话比例", unit="%", module="recent")
        for k in KEYS:
            mine = text[text["sender"] == k]
            f.add(f"recent.{tag}.chars.{k}", int(mine["chars"].sum()), f"{label} {ctx.label(k)}的文字字符数", module="recent")
            f.add(f"recent.{tag}.affection_per_1000.{k}", _rate(mine, affection), f"{label} {ctx.label(k)}每千条文字中含亲昵词的条数", module="recent")
        stats.append(row)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7))
    for ax, key, title in zip(axes, ("daily_median", "span", "per_day"), ("典型日文字量", "双人会话跨度中位数 / 分钟", "双人会话数 / 天")):
        vals = [r[key] for r in stats]
        top = max(vals) or 1
        ax.bar([0, 1], vals, color=[PALETTE["rose"], PALETTE["olive"]], width=.55)
        ax.set_xticks([0, 1], [r["label"] for r in stats], rotation=15)
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, top * 1.25)
        for i, v in enumerate(vals):
            ax.text(i, v + top * .035, f"{v:.1f}", ha="center")
        ax.grid(axis="y", alpha=.15)
    fig.tight_layout()
    ctx.figure(fig, "recent_comparison", "等长窗口中的聊天规模与联系频率", GROUP, "最近两个等长窗口的典型日文字量、会话跨度和每天会话数；用于讲“最近的节奏”")
