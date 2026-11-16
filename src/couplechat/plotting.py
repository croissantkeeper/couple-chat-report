"""Shared figure style: one warm palette, A is rose with solid lines, B is olive with dashed lines."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

PALETTE = {"cream": "#FAF1DC", "rose": "#A44356", "peach": "#D29661", "olive": "#536126", "brown": "#35291F"}
COLOR = {"A": PALETTE["rose"], "B": PALETTE["olive"]}
LINE = {"A": "-", "B": "--"}
HEAT = LinearSegmentedColormap.from_list("warm", [PALETTE[k] for k in ("cream", "peach", "rose", "brown")])
BANDS = ["#E9DCC4", "#F2C9A8", "#D9C7D0", "#C9D3B3", "#CFDCE3", "#E8D3B0"]
CJK_FONTS = ["Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", "SimHei"]
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

plt.rcParams.update({
    "font.sans-serif": CJK_FONTS + ["DejaVu Sans"], "font.family": "sans-serif", "font.size": 9,
    "axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.edgecolor": PALETTE["brown"], "axes.labelcolor": PALETTE["brown"],
    "text.color": PALETTE["brown"], "xtick.color": PALETTE["brown"], "ytick.color": PALETTE["brown"],
    "figure.facecolor": "white", "savefig.facecolor": "white", "legend.frameon": False,
})


def text_color(value: float, vmax: float) -> str:
    """White on dark heat-map cells, brown on light ones."""
    r, g, b = HEAT(value / vmax if vmax else 0)[:3]
    return "white" if .2126 * r + .7152 * g + .0722 * b < .55 else PALETTE["brown"]


def ecdf(ax, values, **kwargs) -> None:
    v = np.sort(np.asarray(values, dtype=float))
    if len(v):
        ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", **kwargs)


def cjk_font_path() -> str | None:
    from matplotlib import font_manager
    for name in CJK_FONTS:
        try:
            return font_manager.findfont(font_manager.FontProperties(family=name), fallback_to_default=False)
        except ValueError:
            continue
    return None
