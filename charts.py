import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpecFromSubplotSpec
from pathlib import Path
from typing import List, Optional, Tuple, Dict

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "savefig.facecolor": "white",
})

# ── Paths ─────────────────────────────────────────────────────────────────────
CSV_PATH = Path("data/The Network Dashboard 2.17.csv")
OUT_PATH = Path("out/dashboard_charts_2022_2025.pdf")

# ── Font sizes ────────────────────────────────────────────────────────────────
FONT_ANNOT      = 9   # bar value / growth annotations
FONT_LABEL      = 10  # axis labels, legend
FONT_TITLE      = 11  # subplot titles
FONT_SECTION    = 14  # Revenue / Expenses headers
FONT_SUPT       = 18  # figure suptitle
FONT_CARD_TITLE = 13  # cash-card title
FONT_CARD_VAL   = 16  # cash-card value

# ── Color palettes ────────────────────────────────────────────────────────────
_REV   = "#2C7BB6"   # professional blue — all revenue charts
_UNRES = "#5BA4CF"   # lighter blue — % unrestricted
_EXP   = "#C4763A"   # warm amber — all expense charts
_FTE   = "#9B9BA8"   # neutral grey — FTE
_NAV   = "#1B3A5C"   # dark navy — section headers, cash card

REV_C  = [_REV] * 6 + [_UNRES]
EXP_C  = [_EXP] * 5 + [_FTE]
FUNC_C = ["#2D6A4F", "#52B788", "#95D5B2"]  # program, mgmt, fundraising

# ── Revenue block ─────────────────────────────────────────────────────────────
REV_LABEL_COL = "Unnamed: 1"
REV_YEAR_COLS = ["Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5"]  # 2022-2025
REV_YEARS = [2022, 2023, 2024, 2025]

# ── Expense block ─────────────────────────────────────────────────────────────
EXP_LABEL_COL = "Unnamed: 7"
EXP_YEAR_COLS = ["Unnamed: 8", "Unnamed: 9", "Unnamed: 10", "Unnamed: 11"]  # 2022-2025
EXP_YEARS = [2022, 2023, 2024, 2025]
FTE_YEAR_COLS = ["Unnamed: 8", "Unnamed: 9", "Unnamed: 10", "Unnamed: 11", "Unnamed: 12"]  # 2022-2026
FTE_YEARS = [2022, 2023, 2024, 2025, 2026]

# ── Functional block ──────────────────────────────────────────────────────────
FUNC_LABEL_COL = "Unnamed: 13"
FUNC_YEAR_COLS_ALL = ["Unnamed: 14", "Unnamed: 15", "Unnamed: 16", "Unnamed: 17", "Unnamed: 18"]
FUNC_YEARS = [2022, 2023, 2024]


def parse_money(x) -> Optional[float]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s:
        return None
    if s in {"-", "—", "–", "N/A", "na", "NA"}:
        return None
    s = s.replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_percent(x) -> Optional[float]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1]
    s = s.replace(",", "")
    try:
        return float(s) / 100.0
    except ValueError:
        return None


def find_row_index(df: pd.DataFrame, label_col: str, metric_name: str) -> int:
    match = df[df[label_col] == metric_name]
    if match.empty:
        raise SystemExit(f"Couldn't find '{metric_name}' in column {label_col}")
    return int(match.index[0])


def get_values_row(df: pd.DataFrame, idx: int, year_cols: List[str], parser) -> List[Optional[float]]:
    row = df.loc[idx, year_cols]
    return [parser(v) for v in row.tolist()]


def get_metric_values_and_growth(
    df: pd.DataFrame,
    label_col: str,
    metric_name: str,
    year_cols: List[str],
) -> Tuple[List[float], List[Optional[float]]]:
    """Reads a metric row + next row as Growth (%). Missing values become 0 for charting.
    If growth row is blank, compute it from values.
    """
    idx = find_row_index(df, label_col, metric_name)

    values_raw = get_values_row(df, idx, year_cols, parse_money)
    values = [0.0 if v is None else float(v) for v in values_raw]

    growth: List[Optional[float]] = [None] * len(year_cols)
    if (idx + 1) in df.index:
        growth_raw = get_values_row(df, idx + 1, year_cols, parse_percent)
        growth = growth_raw

    if all(g is None for g in growth):
        computed: List[Optional[float]] = [None]
        for i in range(1, len(values)):
            prev = values[i - 1]
            cur = values[i]
            if prev == 0:
                computed.append(None)
            else:
                computed.append((cur - prev) / prev)
        growth = computed

    return values, growth


def get_metric_percent_values(df: pd.DataFrame, metric_name: str, year_cols: List[str]) -> List[float]:
    idx = find_row_index(df, REV_LABEL_COL, metric_name)
    vals_raw = get_values_row(df, idx, year_cols, parse_percent)
    return [0.0 if v is None else float(v) for v in vals_raw]


def build_year_to_col_map(df: pd.DataFrame, year_cols_all: List[str]) -> Dict[int, str]:
    """Map year -> column name by scanning a few header-like rows for integers."""
    for header_row in [0, 1, 2, 3, 4]:
        if header_row not in df.index:
            continue
        raw = df.loc[header_row, year_cols_all].tolist()
        years: List[Optional[int]] = []
        for v in raw:
            try:
                years.append(int(str(v).strip()))
            except Exception:
                years.append(None)
        mapping = {yr: col for yr, col in zip(years, year_cols_all) if yr is not None}
        if mapping:
            return mapping
    return {}


def nice_ymax(values: List[float], pad: float = 1.22) -> int:
    """Round up to a clean step with 22% headroom for stacked annotations."""
    m = max(values) if values else 0
    m = m * pad
    if m <= 0:
        return 1
    if m <= 50_000:
        step = 5_000
    elif m <= 250_000:
        step = 25_000
    elif m <= 1_000_000:
        step = 100_000
    else:
        step = 500_000
    return int((m + step - 1) // step * step)


def money_fmt(v, _):
    return f"${v:,.0f}"


def pct_fmt(v, _):
    return f"{v * 100:.0f}%"


def style_axis(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)
    ax.grid(axis="y", linewidth=0.5, alpha=0.18, color="#000000")
    ax.set_axisbelow(True)


def _apply_ylabel(ax, label: str, show_ylabel: bool):
    if show_ylabel:
        ax.set_ylabel(label, fontsize=FONT_LABEL)
    else:
        ax.set_ylabel("")
    ax.tick_params(axis="y", labelleft=True)


def _fmt_bar_val(val: float, n_bars: int = 1) -> str:
    """Format dollar value to 3 significant figures."""
    if val >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    elif val >= 100_000:
        return f"${val / 1_000:.0f}K"
    elif val >= 10_000:
        return f"${val / 1_000:.1f}K"
    elif val >= 1_000:
        return f"${val / 1_000:.2f}K"
    else:
        return f"${val:.0f}"


def draw_bar(
    ax,
    title: str,
    years: List[int],
    values: List[float],
    growth: List[Optional[float]],
    y_max: float,
    color: str,
    show_xlabel: bool,
    show_ylabel: bool,
):
    n = len(years)
    bar_width = 0.45 if n >= 5 else 0.55
    ann_fs = FONT_ANNOT - 1 if n >= 5 else FONT_ANNOT

    x = list(range(n))
    bars = ax.bar(x, values, color=color, width=bar_width)

    ax.set_xticks(x, years)
    ax.set_title(title, fontsize=FONT_TITLE)
    ax.set_xlabel("Year" if show_xlabel else "", fontsize=FONT_LABEL)
    _apply_ylabel(ax, "Dollars", show_ylabel)

    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_formatter(FuncFormatter(money_fmt))
    style_axis(ax)

    for i, (bar, val) in enumerate(zip(bars, values)):
        if val > 0:
            ax.annotate(
                _fmt_bar_val(val, n),
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=ann_fs,
                clip_on=False,
            )

        g = growth[i] if i < len(growth) else None
        if i != 0 and g is not None and val > 0:
            ax.annotate(
                f"{g * 100:+.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 17),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=ann_fs,
                color="#555555",
                clip_on=False,
            )


def draw_percent_bar(
    ax,
    title: str,
    years: List[int],
    values: List[float],
    target: float,
    color: str,
    show_xlabel: bool,
    show_ylabel: bool,
):
    x = list(range(len(years)))
    bars = ax.bar(x, values, color=color, width=0.55)

    ax.set_xticks(x, years)
    ax.set_title(title, fontsize=FONT_TITLE)
    ax.set_xlabel("Year" if show_xlabel else "", fontsize=FONT_LABEL)
    _apply_ylabel(ax, "Percent", show_ylabel)

    ax.yaxis.set_major_formatter(FuncFormatter(pct_fmt))
    style_axis(ax)

    ax.set_ylim(0, round(max(values) + 0.02, 2))

    ax.axhline(target, linestyle="--", linewidth=1)
    import matplotlib.transforms as transforms
    blended = transforms.blended_transform_factory(ax.transAxes, ax.transData)
    ax.text(
        1.02,
        target,
        "Target",
        ha="left",
        va="center",
        fontsize=FONT_ANNOT,
        transform=blended,
        clip_on=False,
    )

    for bar, val in zip(bars, values):
        if val > 0:
            ax.annotate(
                f"{val * 100:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=FONT_ANNOT,
                clip_on=False,
            )


def draw_fte_bar(
    ax,
    title: str,
    years: List[int],
    values: List[float],
    color: str,
    show_xlabel: bool,
    show_ylabel: bool,
):
    x = list(range(len(years)))
    bars = ax.bar(x, values, color=color, width=0.55)

    ax.set_xticks(x, years)
    ax.set_title(title, fontsize=FONT_TITLE)
    ax.set_xlabel("Year" if show_xlabel else "", fontsize=FONT_LABEL)
    _apply_ylabel(ax, "FTE", show_ylabel)

    ymax = max(values) * 1.25 if values else 1
    ax.set_ylim(0, ymax if ymax > 0 else 1)
    ax.tick_params(axis="y", labelleft=False)
    style_axis(ax)

    for bar, val in zip(bars, values):
        if val and val > 0:
            ax.annotate(
                f"{val:,.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=FONT_ANNOT,
                clip_on=False,
            )


def draw_functional_pie(
    axes,
    years: List[int],
    program_vals: List[float],
    mgmt_vals: List[float],
    fund_vals: List[float],
):
    inside_colors = ["white", "white", "#1a3c2a"]
    wedges = []
    for ax, year, prog, mgmt, fund in zip(axes, years, program_vals, mgmt_vals, fund_vals):
        total = prog + mgmt + fund
        sizes = [prog, mgmt, fund]

        wedges, _ = ax.pie(
            sizes,
            labels=None,
            colors=FUNC_C,
            startangle=90,
            wedgeprops={"linewidth": 0},
        )

        for i, (wedge, val) in enumerate(zip(wedges, sizes)):
            angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
            cx, cy = math.cos(angle), math.sin(angle)
            pct = val / total if total > 0 else 0

            label = f"{_fmt_bar_val(val)}  {pct * 100:.0f}%" if i == 0 else _fmt_bar_val(val)

            if pct >= 0.10:
                ax.text(
                    cx * 0.62 + 0.15, cy * 0.62, label,
                    ha="center", va="center",
                    fontsize=FONT_ANNOT, fontweight="bold",
                    color=inside_colors[i],
                )
            else:
                ha = "left" if cx >= 0 else "right"
                ax.annotate(
                    label,
                    xy=(cx * 1.02, cy * 1.02),
                    xytext=(cx * 1.45, cy * 1.45),
                    ha=ha, va="center",
                    fontsize=FONT_ANNOT - 1,
                    color="#444444",
                    arrowprops=dict(arrowstyle="-", color="#aaaaaa", lw=0.8),
                    clip_on=False,
                )

        ax.set_title(f"FY {year}", fontsize=FONT_TITLE, y=1.30)

    return wedges, ["Program", "Management", "Fundraising"]


def draw_cash_card(ax, headline: str, value_text: str):
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    cx, cy = 0.03, 0.06
    cw, ch = 0.78, 0.88

    card = FancyBboxPatch(
        (cx, cy), cw, ch,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=0, facecolor=_NAV,
        transform=ax.transAxes, zorder=1,
    )
    ax.add_patch(card)

    # Headline label
    ax.text(
        cx + cw / 2, cy + ch * 0.80,
        headline,
        ha="center", va="center",
        fontsize=FONT_CARD_TITLE, fontweight="bold",
        color="white",
        transform=ax.transAxes, zorder=2,
    )

    # Large value
    ax.text(
        cx + cw / 2, cy + ch * 0.46,
        value_text,
        ha="center", va="center",
        fontsize=30, fontweight="bold",
        color="white",
        transform=ax.transAxes, zorder=2,
    )

    # Subtle divider
    mid_x0 = cx + cw * 0.20
    mid_x1 = cx + cw * 0.80
    mid_y  = cy + ch * 0.30
    ax.plot(
        [mid_x0, mid_x1], [mid_y, mid_y],
        linewidth=0.8, color="white", alpha=0.25,
        transform=ax.transAxes, zorder=2,
    )

    # Caption below divider
    ax.text(
        cx + cw / 2, cy + ch * 0.16,
        "Months of Operating Reserve",
        ha="center", va="center",
        fontsize=FONT_ANNOT, color="white", alpha=0.65,
        transform=ax.transAxes, zorder=2,
    )


def _compute_growth(values: List[float]) -> List[Optional[float]]:
    """Year-over-year growth rates computed from a value series."""
    growth: List[Optional[float]] = [None]
    for i in range(1, len(values)):
        prev, cur = values[i - 1], values[i]
        growth.append(None if prev == 0 else (cur - prev) / prev)
    return growth


def generate_from_data(data: dict, out_path: str) -> None:
    """Generate the dashboard PDF directly from a data dict (dashboard_data.json format)."""

    # ── Revenue ───────────────────────────────────────────────────────────────
    rev = data["revenue"]
    rev_years = sorted(int(y) for y in rev["Membership Dues"])

    def _rv(metric: str) -> List[float]:
        return [float(rev[metric].get(str(y), 0) or 0) for y in rev_years]

    dues_values       = _rv("Membership Dues")
    donations_values  = _rv("Donations")
    supporters_values = _rv("Strategic Supporters")
    grants_values     = _rv("Grants Awarded")
    ffs_values        = _rv("Fee-for-Service")
    confrev_values    = _rv("Conference Revenue")
    unres_values      = [float(rev["pct_unrestricted"].get(str(y), 0) or 0) / 100.0
                         for y in rev_years]

    dues_growth       = _compute_growth(dues_values)
    donations_growth  = _compute_growth(donations_values)
    supporters_growth = _compute_growth(supporters_values)
    grants_growth     = _compute_growth(grants_values)
    ffs_growth        = _compute_growth(ffs_values)
    confrev_growth    = _compute_growth(confrev_values)

    # ── Expenses ──────────────────────────────────────────────────────────────
    exp = data["expenses"]
    exp_years = sorted(int(y) for y in exp["Programming"])

    def _ev(metric: str) -> List[float]:
        return [float(exp[metric].get(str(y), 0) or 0) for y in exp_years]

    prog_values    = _ev("Programming")
    pers_values    = _ev("Personnel")
    confexp_values = _ev("Conference")
    gta_values     = _ev("Grants to Agencies")

    total_exp_values = [a + b + c + d
                        for a, b, c, d in zip(prog_values, pers_values, confexp_values, gta_values)]

    prog_growth       = _compute_growth(prog_values)
    pers_growth       = _compute_growth(pers_values)
    confexp_growth    = _compute_growth(confexp_values)
    gta_growth        = _compute_growth(gta_values)
    total_exp_growth  = _compute_growth(total_exp_values)

    fte_data   = exp["FTE Count"]
    fte_years  = sorted(int(y) for y in fte_data)
    fte_values = [float(fte_data.get(str(y), 0) or 0) for y in fte_years]

    # ── Functional ────────────────────────────────────────────────────────────
    func = data["functional"]
    func_years = sorted(int(y) for y in func["Program"])

    def _fv(metric: str) -> List[float]:
        return [float(func[metric].get(str(y), 0) or 0) for y in func_years]

    program_vals      = _fv("Program")
    mgmt_vals         = _fv("Management")
    fund_vals         = _fv("Fundraising")
    total_budget_vals = _fv("Total Budget")

    program_pct_of_total: List[Optional[float]] = [
        None if t == 0 else p / t
        for p, t in zip(program_vals, total_budget_vals)
    ]

    # ── Cash card ─────────────────────────────────────────────────────────────
    cash = data.get("cash_card", {})
    cash_headline = cash.get("headline", "Cash on Hand")
    cash_value    = cash.get("value", "—")

    # ── Dynamic titles ────────────────────────────────────────────────────────
    year_range = f"FY {min(rev_years)}\u2013{max(rev_years)}"
    func_range = f"FY {min(func_years)}\u2013{max(func_years)}"

    # ── Layout ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(17.6, 17))
    gs = fig.add_gridspec(
        nrows=5, ncols=4,
        width_ratios=[1, 1, 1, 1],
        height_ratios=[1, 1, 1, 1.8, 0.35],
    )

    ax_rev_00 = fig.add_subplot(gs[0, 0]); ax_rev_01 = fig.add_subplot(gs[0, 1])
    ax_rev_10 = fig.add_subplot(gs[1, 0]); ax_rev_11 = fig.add_subplot(gs[1, 1])
    ax_rev_20 = fig.add_subplot(gs[2, 0]); ax_rev_21 = fig.add_subplot(gs[2, 1])
    ax_rev_30 = fig.add_subplot(gs[3, 0])

    ax_exp_00 = fig.add_subplot(gs[0, 2]); ax_exp_01 = fig.add_subplot(gs[0, 3])
    ax_exp_10 = fig.add_subplot(gs[1, 2]); ax_exp_11 = fig.add_subplot(gs[1, 3])
    ax_exp_20 = fig.add_subplot(gs[2, 2]); ax_exp_21 = fig.add_subplot(gs[2, 3])

    ax_cash      = fig.add_subplot(gs[3, 1])
    gs_func = GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[3, 2:4], wspace=0.35)
    ax_func_0 = fig.add_subplot(gs_func[0, 0])
    ax_func_1 = fig.add_subplot(gs_func[0, 1])
    ax_func_2 = fig.add_subplot(gs_func[0, 2])
    ax_blank     = fig.add_subplot(gs[4, 0:2])
    ax_func_meta = fig.add_subplot(gs[4, 2:4])
    ax_blank.axis("off")

    fig.suptitle(f"Financial Dashboard ({year_range})", fontsize=FONT_SUPT, y=0.995)

    header_y = 0.952; header_h = 0.028
    fig.add_artist(Rectangle((0.06, header_y), 0.42, header_h, transform=fig.transFigure, facecolor=_NAV, edgecolor="none", linewidth=0))
    fig.add_artist(Rectangle((0.52, header_y), 0.42, header_h, transform=fig.transFigure, facecolor=_NAV, edgecolor="none", linewidth=0))
    header_center_y = header_y + header_h / 2
    fig.text(0.27, header_center_y, "Revenue",  ha="center", va="center", fontsize=FONT_SECTION, fontweight="bold", color="white")
    fig.text(0.73, header_center_y, "Expenses", ha="center", va="center", fontsize=FONT_SECTION, fontweight="bold", color="white")
    fig.add_artist(Line2D([0.50, 0.50], [0.30, 0.96], transform=fig.transFigure, color="#DEDEDE", linewidth=1.0))

    draw_bar(ax_rev_00, "Membership Dues",      rev_years, dues_values,       dues_growth,       nice_ymax(dues_values),       REV_C[0], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_01, "Donations",            rev_years, donations_values,  donations_growth,  nice_ymax(donations_values),  REV_C[1], show_xlabel=False, show_ylabel=False)
    draw_bar(ax_rev_10, "Strategic Supporters", rev_years, supporters_values, supporters_growth, nice_ymax(supporters_values), REV_C[2], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_11, "Grants Awarded",       rev_years, grants_values,     grants_growth,     nice_ymax(grants_values),     REV_C[3], show_xlabel=False, show_ylabel=False)
    draw_bar(ax_rev_20, "Fee-for-Service",      rev_years, ffs_values,        ffs_growth,        nice_ymax(ffs_values),        REV_C[4], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_21, "Conference Revenue",   rev_years, confrev_values,    confrev_growth,    nice_ymax(confrev_values),    REV_C[5], show_xlabel=False, show_ylabel=False)
    draw_percent_bar(ax_rev_30, "% Unrestricted Revenue", rev_years, unres_values, 0.06, REV_C[6], show_xlabel=True, show_ylabel=True)

    draw_bar(ax_exp_00, "Programming",        exp_years, prog_values,      prog_growth,      nice_ymax(prog_values),      EXP_C[0], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_exp_01, "Personnel",          exp_years, pers_values,      pers_growth,      nice_ymax(pers_values),      EXP_C[1], show_xlabel=False, show_ylabel=False)
    draw_bar(ax_exp_10, "Conference",         exp_years, confexp_values,   confexp_growth,   nice_ymax(confexp_values),   EXP_C[2], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_exp_11, "Grants to Agencies", exp_years, gta_values,       gta_growth,       nice_ymax(gta_values),       EXP_C[3], show_xlabel=False, show_ylabel=False)
    draw_bar(ax_exp_20, "Total Expenses",     exp_years, total_exp_values, total_exp_growth, nice_ymax(total_exp_values), EXP_C[4], show_xlabel=True,  show_ylabel=True)
    draw_fte_bar(ax_exp_21, "FTE Count",      fte_years, fte_values,                                                      EXP_C[5], show_xlabel=True,  show_ylabel=False)

    wedges, legend_labels = draw_functional_pie(
        [ax_func_0, ax_func_1, ax_func_2], func_years, program_vals, mgmt_vals, fund_vals,
    )

    ax_func_meta.axis("off")
    ax_func_meta.text(
        0.5, 0.95, "Functional Expenses",
        ha="center", va="top",
        fontsize=FONT_TITLE, fontweight="bold",
        transform=ax_func_meta.transAxes,
    )
    ax_func_1.legend(
        wedges, legend_labels,
        loc="upper center",
        bbox_to_anchor=(0, -1.2),
        bbox_transform=ax_func_1.transData,
        ncol=3, frameon=False, fontsize=FONT_LABEL,
    )

    draw_cash_card(ax_cash, cash_headline, cash_value)

    plt.tight_layout(rect=[0, 0, 1, 0.945])
    pos = ax_cash.get_position()
    side = min(pos.width, pos.height)
    ax_cash.set_position([pos.x0, pos.y0 + (pos.height - side) / 2, side, side])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="pdf")
    plt.close(fig)


def main():
    df = pd.read_csv(CSV_PATH)

    # Revenue metrics
    dues_values, dues_growth             = get_metric_values_and_growth(df, REV_LABEL_COL, "Membership Dues",      REV_YEAR_COLS)
    donations_values, donations_growth   = get_metric_values_and_growth(df, REV_LABEL_COL, "Donations",            REV_YEAR_COLS)
    supporters_values, supporters_growth = get_metric_values_and_growth(df, REV_LABEL_COL, "Strategic Supporters", REV_YEAR_COLS)
    grants_values, grants_growth         = get_metric_values_and_growth(df, REV_LABEL_COL, "Grants Awarded",       REV_YEAR_COLS)
    ffs_values, ffs_growth               = get_metric_values_and_growth(df, REV_LABEL_COL, "Fee-for-Service",      REV_YEAR_COLS)
    confrev_values, confrev_growth       = get_metric_values_and_growth(df, REV_LABEL_COL, "Conference Revenue",   REV_YEAR_COLS)
    unres_values = get_metric_percent_values(df, "% Unrestricted Revenue", REV_YEAR_COLS)

    # Expense metrics
    prog_values, prog_growth       = get_metric_values_and_growth(df, EXP_LABEL_COL, "Programming",       EXP_YEAR_COLS)
    pers_values, pers_growth       = get_metric_values_and_growth(df, EXP_LABEL_COL, "Personnel",         EXP_YEAR_COLS)
    confexp_values, confexp_growth = get_metric_values_and_growth(df, EXP_LABEL_COL, "Conference",        EXP_YEAR_COLS)
    gta_values, gta_growth         = get_metric_values_and_growth(df, EXP_LABEL_COL, "Grants to Agencies",EXP_YEAR_COLS)

    total_exp_values = [a + b + c + d for a, b, c, d in zip(prog_values, pers_values, confexp_values, gta_values)]
    total_exp_growth: List[Optional[float]] = [None]
    for i in range(1, len(total_exp_values)):
        prev = total_exp_values[i - 1]
        cur = total_exp_values[i]
        total_exp_growth.append(None if prev == 0 else (cur - prev) / prev)

    # FTE count
    fte_idx = find_row_index(df, EXP_LABEL_COL, "FTE Count")
    fte_raw = get_values_row(df, fte_idx, FTE_YEAR_COLS, parse_money)
    fte_values = [0.0 if v is None else float(v) for v in fte_raw]

    # Functional expenses (Program/Management/Fundraising) + Program % of total
    year_map = build_year_to_col_map(df, FUNC_YEAR_COLS_ALL)
    if not year_map:
        raise SystemExit("Could not map Functional Expense columns to years (could not find year headers).")
    func_year_cols = [year_map[y] for y in FUNC_YEARS]

    program_vals, _      = get_metric_values_and_growth(df, FUNC_LABEL_COL, "Program",      func_year_cols)
    mgmt_vals, _         = get_metric_values_and_growth(df, FUNC_LABEL_COL, "Management",   func_year_cols)
    fund_vals, _         = get_metric_values_and_growth(df, FUNC_LABEL_COL, "Fundraising",  func_year_cols)
    total_budget_vals, _ = get_metric_values_and_growth(df, FUNC_LABEL_COL, "Total Budget", func_year_cols)

    program_pct_of_total: List[Optional[float]] = []
    for p, t in zip(program_vals, total_budget_vals):
        program_pct_of_total.append(None if t == 0 else p / t)

    # ── Layout ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(17.6, 17))
    gs = fig.add_gridspec(
        nrows=5,
        ncols=4,
        width_ratios=[1, 1, 1, 1],
        height_ratios=[1, 1, 1, 1.8, 0.35],
    )

    # Revenue axes (left half)
    ax_rev_00 = fig.add_subplot(gs[0, 0])
    ax_rev_01 = fig.add_subplot(gs[0, 1])
    ax_rev_10 = fig.add_subplot(gs[1, 0])
    ax_rev_11 = fig.add_subplot(gs[1, 1])
    ax_rev_20 = fig.add_subplot(gs[2, 0])
    ax_rev_21 = fig.add_subplot(gs[2, 1])
    ax_rev_30 = fig.add_subplot(gs[3, 0])  # % Unrestricted Revenue

    # Expense axes (right half)
    ax_exp_00 = fig.add_subplot(gs[0, 2])
    ax_exp_01 = fig.add_subplot(gs[0, 3])
    ax_exp_10 = fig.add_subplot(gs[1, 2])
    ax_exp_11 = fig.add_subplot(gs[1, 3])
    ax_exp_20 = fig.add_subplot(gs[2, 2])
    ax_exp_21 = fig.add_subplot(gs[2, 3])

    # Row 3: % Unrestricted | Cash on Hand | Functional Expenses
    ax_cash      = fig.add_subplot(gs[3, 1])
    gs_func = GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[3, 2:4], wspace=0.35)
    ax_func_0 = fig.add_subplot(gs_func[0, 0])
    ax_func_1 = fig.add_subplot(gs_func[0, 1])
    ax_func_2 = fig.add_subplot(gs_func[0, 2])

    # Row 4: legend strip (right side only)
    ax_blank     = fig.add_subplot(gs[4, 0:2])
    ax_func_meta = fig.add_subplot(gs[4, 2:4])
    ax_blank.axis("off")

    # ── Titles + section headers ──────────────────────────────────────────────
    fig.suptitle("Financial Dashboard (FY 2022-2025)", fontsize=FONT_SUPT, y=0.995)

    header_y = 0.952
    header_h = 0.028
    fig.add_artist(Rectangle((0.06, header_y), 0.42, header_h, transform=fig.transFigure, facecolor=_NAV, edgecolor="none", linewidth=0))
    fig.add_artist(Rectangle((0.52, header_y), 0.42, header_h, transform=fig.transFigure, facecolor=_NAV, edgecolor="none", linewidth=0))

    header_center_y = header_y + header_h / 2
    fig.text(0.27, header_center_y, "Revenue",  ha="center", va="center", fontsize=FONT_SECTION, fontweight="bold", color="white")
    fig.text(0.73, header_center_y, "Expenses", ha="center", va="center", fontsize=FONT_SECTION, fontweight="bold", color="white")

    fig.add_artist(Line2D([0.50, 0.50], [0.30, 0.96], transform=fig.transFigure, color="#DEDEDE", linewidth=1.0))

    # ── Revenue charts (ylabel only on left chart per row) ────────────────────
    draw_bar(ax_rev_00, "Membership Dues",     REV_YEARS, dues_values,       dues_growth,       nice_ymax(dues_values),       REV_C[0], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_01, "Donations",           REV_YEARS, donations_values,  donations_growth,  nice_ymax(donations_values),  REV_C[1], show_xlabel=False, show_ylabel=False)

    draw_bar(ax_rev_10, "Strategic Supporters",REV_YEARS, supporters_values, supporters_growth, nice_ymax(supporters_values), REV_C[2], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_11, "Grants Awarded",      REV_YEARS, grants_values,     grants_growth,     nice_ymax(grants_values),     REV_C[3], show_xlabel=False, show_ylabel=False)

    draw_bar(ax_rev_20, "Fee-for-Service",     REV_YEARS, ffs_values,        ffs_growth,        nice_ymax(ffs_values),        REV_C[4], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_rev_21, "Conference Revenue",  REV_YEARS, confrev_values,    confrev_growth,    nice_ymax(confrev_values),    REV_C[5], show_xlabel=False, show_ylabel=False)

    draw_percent_bar(ax_rev_30, "% Unrestricted Revenue", REV_YEARS, unres_values, 0.06, REV_C[6], show_xlabel=True, show_ylabel=True)

    # ── Expense charts (ylabel only on left chart per row) ────────────────────
    draw_bar(ax_exp_00, "Programming",        EXP_YEARS, prog_values,      prog_growth,      nice_ymax(prog_values),      EXP_C[0], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_exp_01, "Personnel",          EXP_YEARS, pers_values,      pers_growth,      nice_ymax(pers_values),      EXP_C[1], show_xlabel=False, show_ylabel=False)

    draw_bar(ax_exp_10, "Conference",         EXP_YEARS, confexp_values,   confexp_growth,   nice_ymax(confexp_values),   EXP_C[2], show_xlabel=False, show_ylabel=True)
    draw_bar(ax_exp_11, "Grants to Agencies", EXP_YEARS, gta_values,       gta_growth,       nice_ymax(gta_values),       EXP_C[3], show_xlabel=False, show_ylabel=False)

    draw_bar(ax_exp_20, "Total Expenses",     EXP_YEARS, total_exp_values, total_exp_growth, nice_ymax(total_exp_values), EXP_C[4], show_xlabel=True,  show_ylabel=True)
    draw_fte_bar(ax_exp_21, "FTE Count",      FTE_YEARS, fte_values,                                                      EXP_C[5], show_xlabel=True,  show_ylabel=False)

    # ── Functional expenses ───────────────────────────────────────────────────
    wedges, legend_labels = draw_functional_pie(
        [ax_func_0, ax_func_1, ax_func_2], FUNC_YEARS, program_vals, mgmt_vals, fund_vals,
    )

    ax_func_meta.axis("off")
    ax_func_meta.text(
        0.5, 0.95, "Functional Expenses",
        ha="center", va="top",
        fontsize=FONT_TITLE, fontweight="bold",
        transform=ax_func_meta.transAxes,
    )
    ax_func_1.legend(
        wedges, legend_labels,
        loc="upper center",
        bbox_to_anchor=(0, -1.2),
        bbox_transform=ax_func_1.transData,
        ncol=3, frameon=False, fontsize=FONT_LABEL,
    )

    # ── Cash card ─────────────────────────────────────────────────────────────
    draw_cash_card(ax_cash, "Cash on Hand", "18 months")

    plt.tight_layout(rect=[0, 0, 1, 0.945])
    pos = ax_cash.get_position()
    side = min(pos.width, pos.height)
    ax_cash.set_position([pos.x0, pos.y0 + (pos.height - side) / 2, side, side])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, format="pdf")
    plt.close(fig)

    print(f"Wrote: {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
