"""Draw the design flowchart used in the READMEs, in English and Chinese.

    python docs/make_design_figure.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROSE, OLIVE, PEACH, CREAM, BROWN, PAPER = "#A44356", "#536126", "#D29661", "#FAF1DC", "#35291F", "#FFFDF8"
plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"],
                     "font.family": "sans-serif", "axes.unicode_minus": False})

TEXT = {
    "en": {
        "local": "Everything inside this frame stays on your machine",
        "profile": "profile.yaml", "profile_sub": "names · time zones · itinerary · milestones · context · tone · privacy switches",
        "export": "Chat export", "export_sub": "Moect folder\nCSV\nother JSON",
        "ingest": "ingest", "ingest_sub": "one adapter\nper format",
        "table": "message table", "table_sub": "ts · sender\nkind · text",
        "analyses": "analyses", "analyses_sub": "nine groups, each decides\nwhether it applies",
        "groups": "volume · rhythm · timezones\nsessions · language · greetings\nrelationship · calls · itinerary",
        "figures": "27 figures", "tables": "tables (CSV)", "facts": "facts.json", "facts_sub": "every citable number,\nwith id and definition",
        "story": "story", "s1": "1  propose\nstorylines", "s2": "you pick\none", "s3": "2  write with\n{{fact ids}}", "s4": "3  review\nclaims",
        "render": "render", "render_sub": "fill in numbers\ncheck the draft",
        "report": "report", "report_sub": "report.html\nreport.md\ntext + figures",
        "llm": "Language model", "send": "aggregates only\n(no raw messages;\nword lists off by default)", "back": "storylines,\ndraft, review",
        "nomodel": "couplechat run skips the model:\na figure-by-figure report",
        "numbers": "numbers",
    },
    "zh": {
        "local": "框内的一切都留在你的电脑上",
        "profile": "profile.yaml", "profile_sub": "称呼 · 时区 · 行程 · 关系节点 · 背景 · 文风 · 隐私开关",
        "export": "聊天导出", "export_sub": "Moect 文件夹\nCSV\n其他 JSON",
        "ingest": "ingest 接入", "ingest_sub": "每种格式\n一个适配器",
        "table": "统一消息表", "table_sub": "时间 · 发送者\n类型 · 文字",
        "analyses": "analyses 分析", "analyses_sub": "九个功能组，各自判断\n是否适用",
        "groups": "聊天量 · 作息 · 时差\n会话 · 语言 · 问候\n关系阶段 · 通话 · 行程",
        "figures": "27 张图", "tables": "统计表 (CSV)", "facts": "facts.json", "facts_sub": "所有可引用的数字，\n带编号和口径说明",
        "story": "story 叙述", "s1": "1  提出\n故事线", "s2": "你来\n挑一条", "s3": "2  用 {{编号}}\n写正文", "s4": "3  审稿\n核对论断",
        "render": "render 渲染", "render_sub": "填入数字\n检查稿件",
        "report": "报告", "report_sub": "report.html\nreport.md\n文字 + 图件",
        "llm": "大模型", "send": "只发送聚合数字\n（不含原始消息；\n词频默认不发）", "back": "故事线、\n正文、审稿意见",
        "nomodel": "couplechat run 不调用模型：\n直接生成逐图说明的报告",
        "numbers": "数字",
    },
}


def box(ax, x, y, w, h, title, sub="", face=CREAM, edge=BROWN, title_color=BROWN, size=11, sub_size=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2", fc=face, ec=edge, lw=1.3, zorder=2))
    if sub:
        ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="center", fontsize=size, fontweight="bold", color=title_color, zorder=3)
        ax.text(x + w / 2, y + (h - 3.6) / 2, sub, ha="center", va="center", fontsize=sub_size, color=BROWN, zorder=3, linespacing=1.35)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=size, fontweight="bold", color=title_color, zorder=3, linespacing=1.3)


def arrow(ax, a, b, color=BROWN, style="-|>", ls="-", rad=0.0, lw=1.5):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=13, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=4, shrinkA=2, shrinkB=2))


def draw(lang: str, path: Path) -> None:
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(13, 7.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(-13, 62)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # what stays local
    ax.add_patch(Rectangle((1, 3), 98, 58, fc=PAPER, ec=OLIVE, lw=1.4, ls=(0, (6, 4)), zorder=0))
    ax.text(2.5, 59.2, t["local"], fontsize=9.5, color=OLIVE, va="center", fontweight="bold")

    # profile feeds three stages
    box(ax, 19, 50, 56, 6.5, t["profile"], t["profile_sub"], face="white", edge=ROSE, title_color=ROSE)
    # top row: export -> ingest -> table -> analyses -> outputs
    box(ax, 3, 33, 12, 12, t["export"], t["export_sub"], face="white")
    box(ax, 19, 33, 12, 12, t["ingest"], t["ingest_sub"])
    box(ax, 35, 33, 13, 12, t["table"], t["table_sub"])
    box(ax, 52, 29, 23, 16, t["analyses"], t["analyses_sub"] + "\n\n" + t["groups"], sub_size=8)
    box(ax, 80, 41.5, 17, 4.6, t["figures"], face="white", size=10)
    box(ax, 80, 35.3, 17, 4.6, t["tables"], face="white", size=10)
    box(ax, 80, 25, 17, 8.7, t["facts"], t["facts_sub"], face="white", edge=ROSE, title_color=ROSE, sub_size=8)
    arrow(ax, (15, 39), (19, 39))
    arrow(ax, (31, 39), (35, 39))
    arrow(ax, (48, 39), (52, 39))
    for y in (43.8, 37.6, 30.5):
        arrow(ax, (75, min(y, 43)), (80, y))
    arrow(ax, (25, 50), (25, 45), color=ROSE)
    arrow(ax, (63.5, 50), (63.5, 45), color=ROSE)

    # bottom row: story -> render -> report
    box(ax, 19, 8, 45, 15, "", face=CREAM)
    ax.text(21, 20.6, t["story"], fontsize=11, fontweight="bold", color=BROWN, va="center", zorder=3)
    xs = [21, 31.5, 42, 52.5]
    for x, key, face in zip(xs, ("s1", "s2", "s3", "s4"), ("white", PEACH, "white", "white")):
        box(ax, x, 9.6, 9.3, 7.6, t[key], face=face, size=8.6)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a + 9.3, 13.4), (b, 13.4), lw=1.2)
    box(ax, 68, 9.5, 12, 12, t["render"], t["render_sub"])
    box(ax, 84, 9.5, 13, 12, t["report"], t["report_sub"], face="white", edge=OLIVE, title_color=OLIVE)
    arrow(ax, (64, 15.5), (68, 15.5))
    arrow(ax, (80, 15.5), (84, 15.5))
    ax.plot([19, 17, 17], [53, 53, 15.5], color=ROSE, lw=1.5, zorder=4, solid_capstyle="round")   # profile -> story (tone, context)
    arrow(ax, (16.6, 15.5), (19, 15.5), color=ROSE)
    arrow(ax, (82, 25), (60, 23), color=ROSE, rad=0.12)         # facts -> story
    arrow(ax, (86, 25), (76, 21.5), color=ROSE, rad=-0.1)       # facts -> render
    ax.text(79.2, 23.4, t["numbers"], fontsize=8, color=ROSE, ha="center")
    ax.text(82.5, 6, t["nomodel"], fontsize=8.5, color=OLIVE, ha="center", va="center", style="italic", linespacing=1.3)

    # the only thing that leaves the machine
    box(ax, 30, -12, 23, 6.5, t["llm"], face="white", edge=BROWN)
    arrow(ax, (36, 8), (36, -5.5), color=ROSE)
    arrow(ax, (47, -5.5), (47, 8), color=BROWN)
    ax.text(34.8, -1.2, t["send"], fontsize=8, color=ROSE, ha="right", va="center", linespacing=1.3)
    ax.text(48.2, -1.2, t["back"], fontsize=8, color=BROWN, ha="left", va="center", linespacing=1.3)

    fig.savefig(path, dpi=170, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "images"
    out.mkdir(exist_ok=True)
    for lang in TEXT:
        draw(lang, out / f"design.{lang}.png")
        print("wrote", out / f"design.{lang}.png")
