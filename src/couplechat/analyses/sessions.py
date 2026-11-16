"""Conversation sessions: who starts, how long they last, how quickly each person picks up.

Figures: session_shape, session_starts, reply_rhythm, all_gaps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..plotting import COLOR, LINE, PALETTE, ecdf, plt
from ..prepare import Context, stage_label
from ..profile import KEYS

GROUP = "sessions"
STAGE_COLORS = [PALETTE["brown"], PALETTE["rose"], PALETTE["olive"], PALETTE["peach"]]


def build_sessions(df: pd.DataFrame, gap_minutes: int) -> pd.DataFrame:
    pause = df["ts"].diff().dt.total_seconds().div(60)
    sid = (pause.isna() | (pause > gap_minutes)).cumsum()
    switch = (df["sender"] != df["sender"].shift()) & (sid == sid.shift())
    g = df.groupby(sid)
    out = pd.DataFrame({
        "start": g["ts"].min(), "end": g["ts"].max(), "records": g.size(),
        "switches": switch.groupby(sid).sum(), "both": g["sender"].nunique() > 1,
        "initiator": g["sender"].first(), "init_hour": g["local_hour"].first(),
        "gap": g["gap"].first(), "day": g["day"].first(),
    })
    out["duration_min"] = (out["end"] - out["start"]).dt.total_seconds() / 60
    out["boundary"] = False
    out.iloc[[0, -1], out.columns.get_loc("boundary")] = True   # first and last may be cut off by the export
    return out


def run(ctx: Context) -> None:
    f, minutes = ctx.facts, ctx.profile.session_gap_minutes
    f.module(GROUP, True, f"相邻消息间隔超过 {minutes} 分钟算新会话；时长是首末消息的跨度，包含中途停顿；接话间隔只是发送时间差，不含已读状态")
    sessions = build_sessions(ctx.df, minutes)
    ctx.shared["sessions"] = sessions
    ctx.table("sessions.csv", sessions.reset_index(drop=True))
    use = sessions[~sessions["boundary"]] if len(sessions) > 2 else sessions
    paired = use[use["both"]]
    f.add("sessions.count", len(sessions), "会话数")
    f.add("sessions.two_person", int(sessions["both"].sum()), "两人都发了消息的会话数")
    f.add("sessions.span_median_min", float(paired["duration_min"].median()) if len(paired) else 0.0, "双人会话首末消息跨度的中位数", unit="分钟")
    f.add("sessions.records_median", float(paired["records"].median()) if len(paired) else 0.0, "双人会话记录数的中位数")
    f.add("sessions.switches_median", float(paired["switches"].median()) if len(paired) else 0.0, "双人会话中说话人切换次数的中位数")
    for k in KEYS:
        f.add(f"sessions.start_share.{k}", 100 * float((use["initiator"] == k).mean()), f"由{ctx.label(k)}发出首条消息的会话比例", unit="%")
    for alt in (30, 60, 120):   # is the "who starts" result sensitive to the threshold?
        s = build_sessions(ctx.df, alt)
        s = s[~s["boundary"]] if len(s) > 2 else s
        f.add(f"sessions.sensitivity.gap{alt}.start_share.A", 100 * float((s["initiator"] == "A").mean()), f"阈值改为 {alt} 分钟时，由{ctx.label('A')}开启的会话比例", unit="%", module=GROUP)

    # reply gaps: time from the other person's message to mine
    df = ctx.df
    prev = df.shift()
    other = df["sender"] != prev["sender"]
    gaps = pd.DataFrame({"responder": df["sender"], "seconds": (df["ts"] - prev["ts"]).dt.total_seconds(),
                         "same_session": df["session"] == prev["session"], "apart": df["gap"] != 0,
                         "night": _hour_at_previous(df) < 6})[other & prev["ts"].notna()]
    ctx.shared["reply_gaps"] = gaps
    inside = gaps[gaps["same_session"]]
    for k in KEYS:
        mine = inside[inside["responder"] == k]
        f.add(f"reply.median_sec.{k}", float(mine["seconds"].median()) if len(mine) else 0.0, f"会话内{ctx.label(k)}接话的时间间隔中位数", unit="秒")
        night = mine[mine["night"]]
        if len(night) >= 20:
            f.add(f"reply.median_sec.night.{k}", float(night["seconds"].median()), f"对方消息发出时{ctx.label(k)}处于当地 0-6 点的情况下，会话内接话间隔的中位数", unit="秒", module=GROUP)
        f.add(f"reply.over_1h_share.{k}", 100 * float((gaps.loc[gaps["responder"] == k, "seconds"] > 3600).mean()) if (gaps["responder"] == k).any() else 0.0,
              f"包含跨会话的间隔在内，{ctx.label(k)}超过一小时才接话的比例", unit="%", module=GROUP)
    _session_shape(ctx, paired)
    _session_starts(ctx, use)
    _reply_rhythm(ctx, inside)
    _all_gaps(ctx, gaps)


def _hour_at_previous(df: pd.DataFrame) -> pd.Series:
    """The responder's own local hour at the moment the previous message was sent."""
    prev_a, prev_b = df["hour_A"].shift(), df["hour_B"].shift()
    return prev_a.where(df["sender"] == "A", prev_b)


def _session_shape(ctx: Context, paired: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, key, label in zip(axes, ("duration_min", "records", "switches"), ("跨度（分钟）", "每段记录数", "说话人切换次数")):
        for gap, color in zip(ctx.stages, STAGE_COLORS):
            part = paired[paired["gap"] == gap]
            ecdf(ax, part[key], color=color, lw=1.6, label=f"{stage_label(gap)} (n={len(part)})")
        ax.set(xscale="symlog", xlabel=label, ylabel="累计比例")
    for gap in ctx.stages:
        part = paired[paired["gap"] == gap]
        if len(part):
            ctx.facts.add(f"sessions.span_median_min.gap{abs(gap):g}", float(part["duration_min"].median()), f"{stage_label(gap)}期间双人会话跨度的中位数", unit="分钟", module=GROUP)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    ctx.figure(fig, "session_shape", "会话的跨度、消息规模与往返次数", GROUP, "双人会话的时长、记录数、切换次数的累计分布，按时差阶段分线；曲线越靠右表示会话越长、往返越多")


def _session_starts(ctx: Context, use: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.7))
    x = np.arange(len(ctx.stages))
    for j, k in enumerate(KEYS):
        vals = []
        for gap in ctx.stages:
            part = use[use["gap"] == gap]
            share = 100 * float((part["initiator"] == k).mean()) if len(part) else 0.0
            vals.append(share)
            if len(part):
                ctx.facts.add(f"sessions.start_share.gap{abs(gap):g}.{k}", share, f"{stage_label(gap)}期间由{ctx.label(k)}开启的会话比例", unit="%", module=GROUP)
        axes[0].bar(x + (j - .5) * .32, vals, width=.32, color=COLOR[k], label=ctx.label(k))
        hours = use[use["initiator"] == k].groupby("init_hour").size().reindex(range(24), fill_value=0)
        axes[1].plot(range(24), 100 * hours / max(1, hours.sum()), color=COLOR[k], ls=LINE[k], lw=1.8, label=ctx.label(k))
    axes[0].set_xticks(x, [stage_label(g) for g in ctx.stages])
    axes[0].set(ylabel="占会话开启的比例 (%)", title="谁先开口")
    axes[1].set(xlabel="发起者的当地小时", ylabel="占本人发起的比例 (%)", title="通常在什么时间开口")
    axes[1].set_xticks(range(0, 24, 3))
    for ax in axes:
        ax.legend()
    fig.tight_layout()
    ctx.figure(fig, "session_starts", "谁先联系谁，以及通常在什么时间", GROUP, "左为各阶段两人开启会话的比例，右为各自发起会话的当地小时分布")


def _reply_rhythm(ctx: Context, inside: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.7))
    for ax, night in zip(axes, (False, True)):
        for k in KEYS:
            v = inside[(inside["responder"] == k) & (inside["night"] == night)]["seconds"]
            ecdf(ax, v, color=COLOR[k], ls=LINE[k], lw=1.8, label=f"{ctx.label(k)} (n={len(v)})")
        ax.set(xscale="symlog", xlabel="相邻两人消息的间隔（秒）", ylabel="累计比例", title="接话者当地 " + ("0-6 点" if night else "6-24 点"))
        ax.legend(fontsize=8)
    fig.tight_layout()
    ctx.figure(fig, "reply_rhythm", "进入对话后双方的接续节奏", GROUP, "同一会话内，从对方发出消息到本人发出下一条的间隔分布，按接话者当时是否处于深夜分栏")


def _all_gaps(ctx: Context, gaps: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.7))
    for ax, night in zip(axes, (False, True)):
        for k in KEYS:
            v = gaps[(gaps["responder"] == k) & (gaps["night"] == night)]["seconds"] / 3600
            ecdf(ax, v, color=COLOR[k], ls=LINE[k], lw=1.8, label=ctx.label(k))
        ax.set_xscale("symlog", linthresh=1 / 3600)
        ax.set_xticks([0, 1 / 3600, 1 / 60, 1, 6, 24], ["0", "1秒", "1分钟", "1小时", "6小时", "1天"])
        ax.set(xlabel="相邻两人消息的间隔", ylabel="累计比例", title="接话者当地 " + ("0-6 点" if night else "6-24 点"))
        ax.legend()
    fig.tight_layout()
    ctx.figure(fig, "all_gaps", "包含会话间隔的完整等待分布", GROUP, "不按会话截断的全部说话人切换间隔；同一人连发时从最后一条算起，所以长等待可能被掩盖")
