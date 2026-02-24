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
FONT_ANNOT      = 9
FONT_LABEL      = 10
FONT_TITLE      = 11
FONT_SECTION    = 14
FONT_SUPT       = 18
FONT_CARD_TITLE = 13
FONT_CARD_VAL   = 16

# ── Color palettes ────────────────────────────────────────────────────────────
_REV   = "#2C7BB6"   # professional blue — revenue
_UNRES = "#5BA4CF"   # lighter blue — % unrestricted
_EXP   = "#C4763A"   # warm amber — expenses
_FTE   = "#9B9BA8"   # neutral grey — FTE
_NAV   = "#1B3A5C"   # dark navy — cash card

# ── Legacy CSV constants (used by main() only) ────────────────────────────────
REV_LABEL_COL = "Unnamed: 1"
REV_YEAR_COLS = ["Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5"]
REV_YEARS = [2022, 2023, 2024, 2025]
EXP_LABEL_COL = "Unnamed: 7"
EXP_YEAR_COLS = ["Unnamed: 8", "Unnamed: 9", "Unnamed: 10", "Unnamed: 11"]
EXP_YEARS = [2022, 2023, 2024, 2025]
FTE_YEAR_COLS = ["Unnamed: 8", "Unnamed: 9", "Unnamed: 10", "Unnamed: 11", "Unnamed: 12"]
FTE_YEARS = [2022, 2023, 2024, 2025, 2026]


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
    return [parser(v) for v in df.loc[idx, year_cols].tolist()]


def get_metric_values_and_growth(
    df: pd.DataFrame, label_col: str, metric_name: str, year_cols: List[str],
) -> Tuple[List[float], List[Optional[float]]]:
    idx = find_row_index(df, label_col, metric_name)
    values = [0.0 if v is None else float(v)
              for v in get_values_row(df, idx, year_cols, parse_money)]
    growth: List[Optional[float]] = [None] * len(year_cols)
    if (idx + 1) in df.index:
        growth = get_values_row(df, idx + 1, year_cols, parse_percent)
    if all(g is None for g in growth):
        computed: List[Optional[float]] = [None]
        for i in range(1, len(values)):
            prev, cur = values[i - 1], values[i]
            computed.append(None if prev == 0 else (cur - prev) / prev)
        growth = computed
    return values, growth


def get_metric_percent_values(df: pd.DataFrame, metric_name: str, year_cols: List[str]) -> List[float]:
    idx = find_row_index(df, REV_LABEL_COL, metric_name)
    return [0.0 if v is None else float(v)
            for v in get_values_row(df, idx, year_cols, parse_percent)]


def nice_ymax(values: List[float], pad: float = 1.22) -> int:
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
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold")
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
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=ann_fs, clip_on=False,
            )
        g = growth[i] if i < len(growth) else None
        if i != 0 and g is not None and val > 0:
            ax.annotate(
                f"{g * 100:+.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 17), textcoords="offset points",
                ha="center", va="bottom", fontsize=ann_fs,
                color="#555555", clip_on=False,
            )


def draw_percent_bar(
    ax,
    title: str,
    years: List[int],
    values: List[float],
    target: Optional[float],
    color: str,
    show_xlabel: bool,
    show_ylabel: bool,
):
    x = list(range(len(years)))
    bars = ax.bar(x, values, color=color, width=0.55)
    ax.set_xticks(x, years)
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold")
    ax.set_xlabel("Year" if show_xlabel else "", fontsize=FONT_LABEL)
    _apply_ylabel(ax, "Percent", show_ylabel)
    ax.yaxis.set_major_formatter(FuncFormatter(pct_fmt))
    style_axis(ax)
    ax.set_ylim(0, round(max(values) + 0.02, 2))
    if target is not None:
        ax.axhline(target, linestyle="--", linewidth=1)
        import matplotlib.transforms as transforms
        blended = transforms.blended_transform_factory(ax.transAxes, ax.transData)
        ax.text(1.02, target, "Target", ha="left", va="center",
                fontsize=FONT_ANNOT, transform=blended, clip_on=False)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.annotate(
                f"{val * 100:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=FONT_ANNOT, clip_on=False,
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
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold")
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
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=FONT_ANNOT, clip_on=False,
            )


def draw_grouped_bar(
    ax,
    title: str,
    years: List[int],
    values_a: List[float],
    values_b: List[float],
    label_a: str = "Revenue",
    label_b: str = "Expenses",
    color_a: Optional[str] = None,
    color_b: Optional[str] = None,
):
    """Side-by-side bars for two related metrics per year."""
    if color_a is None:
        color_a = _REV
    if color_b is None:
        color_b = _EXP
    n = len(years)
    x = list(range(n))
    bar_width = 0.35
    ann_fs = FONT_ANNOT - 1 if n >= 5 else FONT_ANNOT
    x_a = [xi - bar_width / 2 for xi in x]
    x_b = [xi + bar_width / 2 for xi in x]
    bars_a = ax.bar(x_a, values_a, width=bar_width, color=color_a, label=label_a)
    bars_b = ax.bar(x_b, values_b, width=bar_width, color=color_b, label=label_b)
    ax.set_xticks(x, years)
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold")
    ax.set_xlabel("Year", fontsize=FONT_LABEL)
    ax.set_ylabel("Dollars", fontsize=FONT_LABEL)
    all_vals = [v for v in values_a + values_b if v > 0]
    ax.set_ylim(0, nice_ymax(all_vals) if all_vals else 1)
    ax.yaxis.set_major_formatter(FuncFormatter(money_fmt))
    style_axis(ax)
    for bar, val in zip(bars_a, values_a):
        if val > 0:
            ax.annotate(_fmt_bar_val(val),
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=ann_fs, clip_on=False)
    for bar, val in zip(bars_b, values_b):
        if val > 0:
            ax.annotate(_fmt_bar_val(val),
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=ann_fs, clip_on=False)
    ax.legend(loc="upper left", frameon=False, fontsize=FONT_LABEL)


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
            sizes, labels=None,
            colors=["#2D6A4F", "#52B788", "#95D5B2"],
            startangle=90, wedgeprops={"linewidth": 0},
        )
        for i, (wedge, val) in enumerate(zip(wedges, sizes)):
            angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
            cx, cy = math.cos(angle), math.sin(angle)
            pct = val / total if total > 0 else 0
            label = f"{_fmt_bar_val(val)}  {pct * 100:.0f}%" if i == 0 else _fmt_bar_val(val)
            if pct >= 0.10:
                ax.text(cx * 0.62 + 0.15, cy * 0.62, label,
                    ha="center", va="center",
                    fontsize=FONT_ANNOT, fontweight="bold",
                    color=inside_colors[i])
            else:
                ha = "left" if cx >= 0 else "right"
                ax.annotate(label,
                    xy=(cx * 1.02, cy * 1.02), xytext=(cx * 1.45, cy * 1.45),
                    ha=ha, va="center", fontsize=FONT_ANNOT - 1, color="#444444",
                    arrowprops=dict(arrowstyle="-", color="#aaaaaa", lw=0.8),
                    clip_on=False)
        ax.set_title(f"FY {year}", fontsize=FONT_TITLE, fontweight="bold", y=1.30)
    return wedges, ["Program", "Management", "Fundraising"]


def draw_cash_card(ax, headline: str, value_text: str):
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    cx, cy = 0.03, 0.06
    cw, ch = 0.78, 0.88
    ax.add_patch(FancyBboxPatch(
        (cx, cy), cw, ch,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=0, facecolor=_NAV,
        transform=ax.transAxes, zorder=1,
    ))
    ax.text(cx + cw / 2, cy + ch * 0.80, headline,
        ha="center", va="center",
        fontsize=FONT_CARD_TITLE, fontweight="bold", color="white",
        transform=ax.transAxes, zorder=2)
    ax.text(cx + cw / 2, cy + ch * 0.46, value_text,
        ha="center", va="center",
        fontsize=30, fontweight="bold", color="white",
        transform=ax.transAxes, zorder=2)
    ax.plot(
        [cx + cw * 0.20, cx + cw * 0.80], [cy + ch * 0.30, cy + ch * 0.30],
        linewidth=0.8, color="white", alpha=0.25,
        transform=ax.transAxes, zorder=2,
    )
    ax.text(cx + cw / 2, cy + ch * 0.16, "Months of Operating Reserve",
        ha="center", va="center",
        fontsize=FONT_ANNOT, color="white", alpha=0.65,
        transform=ax.transAxes, zorder=2)


def _compute_growth(values: List[float]) -> List[Optional[float]]:
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

    dues_values      = _rv("Membership Dues")
    donations_values = _rv("Donations")
    confrev_values   = _rv("Conference Revenue")
    unres_values     = [float(rev["pct_unrestricted"].get(str(y), 0) or 0) / 100.0
                        for y in rev_years]

    dues_growth      = _compute_growth(dues_values)
    donations_growth = _compute_growth(donations_values)

    # ── Expenses ──────────────────────────────────────────────────────────────
    exp = data["expenses"]
    exp_years = sorted(int(y) for y in exp["Programming"])

    def _ev(metric: str) -> List[float]:
        return [float(exp[metric].get(str(y), 0) or 0) for y in exp_years]

    prog_values    = _ev("Programming")
    pers_values    = _ev("Personnel")
    confexp_values = _ev("Conference")
    gta_values     = _ev("Grants to Agencies")

    fte_data   = exp["FTE Count"]
    fte_years  = sorted(int(y) for y in fte_data)
    fte_values = [float(fte_data.get(str(y), 0) or 0) for y in fte_years]

    # ── Functional ────────────────────────────────────────────────────────────
    func = data["functional"]
    func_years = sorted(int(y) for y in func["Program"])

    def _fv(metric: str) -> List[float]:
        return [float(func[metric].get(str(y), 0) or 0) for y in func_years]

    program_vals = _fv("Program")
    mgmt_vals    = _fv("Management")
    fund_vals    = _fv("Fundraising")

    # ── Cash card ─────────────────────────────────────────────────────────────
    cash = data.get("cash_card", {})
    cash_headline = cash.get("headline", "Cash on Hand")
    cash_value    = cash.get("value", "—")

    year_range = f"FY {min(rev_years)}\u2013{max(rev_years)}"

    # ── Layout ────────────────────────────────────────────────────────────────
    # Row 0: Cash on Hand | Membership Dues | Donations | % Unrestricted Revenue
    # Row 1: FTE Count | Conference Revenue & Expenses (3 cols)
    # Row 2: Functional Expenses pies (full width)
    # Row 3: footer
    fig = plt.figure(figsize=(17.6, 15))
    gs = fig.add_gridspec(
        nrows=4, ncols=4,
        width_ratios=[1, 1, 1, 1],
        height_ratios=[1.2, 1.2, 1.8, 0.3],
    )

    ax_cash  = fig.add_subplot(gs[0, 0])
    ax_dues  = fig.add_subplot(gs[0, 1])
    ax_don   = fig.add_subplot(gs[0, 2])
    ax_unres = fig.add_subplot(gs[0, 3])
    ax_fte   = fig.add_subplot(gs[1, 0])
    ax_conf  = fig.add_subplot(gs[1, 1:4])

    n_func = len(func_years)
    gs_func = GridSpecFromSubplotSpec(1, n_func, subplot_spec=gs[2, :], wspace=0.35)
    func_axes = [fig.add_subplot(gs_func[0, i]) for i in range(n_func)]

    ax_footer = fig.add_subplot(gs[3, :])
    ax_footer.axis("off")

    fig.suptitle(f"Financial Dashboard ({year_range})", fontsize=FONT_SUPT, y=0.995)

    draw_cash_card(ax_cash, cash_headline, cash_value)
    draw_bar(ax_dues, "Membership Dues",  rev_years, dues_values,      dues_growth,      nice_ymax(dues_values),      _REV, show_xlabel=True, show_ylabel=True)
    draw_bar(ax_don,  "Donations",        rev_years, donations_values, donations_growth, nice_ymax(donations_values), _REV, show_xlabel=True, show_ylabel=True)
    draw_percent_bar(ax_unres, "% Unrestricted Revenue", rev_years, unres_values, 0.06, _UNRES, show_xlabel=True, show_ylabel=True)
    draw_fte_bar(ax_fte, "FTE Count", fte_years, fte_values, _FTE, show_xlabel=True, show_ylabel=False)
    draw_grouped_bar(ax_conf, "Conference Revenue & Expenses",
                     rev_years, confrev_values, confexp_values,
                     label_a="Revenue", label_b="Expenses")

    wedges, legend_labels = draw_functional_pie(
        func_axes, func_years, program_vals, mgmt_vals, fund_vals,
    )
    mid = len(func_axes) // 2
    func_axes[mid].text(0.5, 1.58, "Functional Expenses",
        ha="center", va="bottom",
        fontsize=FONT_TITLE, fontweight="bold",
        transform=func_axes[mid].transAxes, clip_on=False)
    func_axes[mid].legend(wedges, legend_labels,
        loc="upper center",
        bbox_to_anchor=(0, -1.48),
        bbox_transform=func_axes[mid].transData,
        ncol=3, frameon=False, fontsize=FONT_LABEL)

    plt.tight_layout(rect=[0, 0, 1, 0.96], h_pad=3.0)
    pos = ax_cash.get_position()
    side = min(pos.width, pos.height)
    ax_cash.set_position([
        pos.x0 + (pos.width - side) / 2,
        pos.y0 + (pos.height - side) / 2,
        side, side,
    ])

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="pdf")
    plt.close(fig)


def main():
    df = pd.read_csv(CSV_PATH)

    dues_values, dues_growth         = get_metric_values_and_growth(df, REV_LABEL_COL, "Membership Dues",    REV_YEAR_COLS)
    donations_values, donations_growth = get_metric_values_and_growth(df, REV_LABEL_COL, "Donations",          REV_YEAR_COLS)
    confrev_values, _                = get_metric_values_and_growth(df, REV_LABEL_COL, "Conference Revenue", REV_YEAR_COLS)
    unres_values = get_metric_percent_values(df, "% Unrestricted Revenue", REV_YEAR_COLS)

    prog_values, _    = get_metric_values_and_growth(df, EXP_LABEL_COL, "Programming",        EXP_YEAR_COLS)
    pers_values, _    = get_metric_values_and_growth(df, EXP_LABEL_COL, "Personnel",          EXP_YEAR_COLS)
    confexp_values, _ = get_metric_values_and_growth(df, EXP_LABEL_COL, "Conference",         EXP_YEAR_COLS)
    gta_values, _     = get_metric_values_and_growth(df, EXP_LABEL_COL, "Grants to Agencies", EXP_YEAR_COLS)

    fte_idx    = find_row_index(df, EXP_LABEL_COL, "FTE Count")
    fte_values = [0.0 if v is None else float(v)
                  for v in get_values_row(df, fte_idx, FTE_YEAR_COLS, parse_money)]

    _FUNC_LABEL_COL    = "Unnamed: 13"
    _FUNC_YEAR_COLS_ALL = ["Unnamed: 14", "Unnamed: 15", "Unnamed: 16", "Unnamed: 17", "Unnamed: 18"]
    _FUNC_YEARS        = [2022, 2023, 2024]
    year_map = build_year_to_col_map(df, _FUNC_YEAR_COLS_ALL)
    func_year_cols = [year_map[y] for y in _FUNC_YEARS]
    program_vals, _ = get_metric_values_and_growth(df, _FUNC_LABEL_COL, "Program",     func_year_cols)
    mgmt_vals, _    = get_metric_values_and_growth(df, _FUNC_LABEL_COL, "Management",  func_year_cols)
    fund_vals, _    = get_metric_values_and_growth(df, _FUNC_LABEL_COL, "Fundraising", func_year_cols)

    cash_headline = "Cash on Hand"
    cash_value    = "18 months"

    fig = plt.figure(figsize=(17.6, 15))
    gs = fig.add_gridspec(
        nrows=4, ncols=4,
        width_ratios=[1, 1, 1, 1],
        height_ratios=[1.2, 1.2, 1.8, 0.3],
    )

    ax_cash  = fig.add_subplot(gs[0, 0])
    ax_dues  = fig.add_subplot(gs[0, 1])
    ax_don   = fig.add_subplot(gs[0, 2])
    ax_unres = fig.add_subplot(gs[0, 3])
    ax_fte   = fig.add_subplot(gs[1, 0])
    ax_conf  = fig.add_subplot(gs[1, 1:4])

    gs_func = GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[2, :], wspace=0.35)
    func_axes = [fig.add_subplot(gs_func[0, i]) for i in range(3)]

    ax_footer = fig.add_subplot(gs[3, :])
    ax_footer.axis("off")

    fig.suptitle("Financial Dashboard (FY 2022-2025)", fontsize=FONT_SUPT, y=0.995)

    draw_cash_card(ax_cash, cash_headline, cash_value)
    draw_bar(ax_dues, "Membership Dues",  REV_YEARS, dues_values,      dues_growth,      nice_ymax(dues_values),      _REV, show_xlabel=True, show_ylabel=True)
    draw_bar(ax_don,  "Donations",        REV_YEARS, donations_values, donations_growth, nice_ymax(donations_values), _REV, show_xlabel=True, show_ylabel=True)
    draw_percent_bar(ax_unres, "% Unrestricted Revenue", REV_YEARS, unres_values, 0.06, _UNRES, show_xlabel=True, show_ylabel=True)
    draw_fte_bar(ax_fte, "FTE Count", FTE_YEARS, fte_values, _FTE, show_xlabel=True, show_ylabel=False)
    draw_grouped_bar(ax_conf, "Conference Revenue & Expenses",
                     REV_YEARS, confrev_values, confexp_values,
                     label_a="Revenue", label_b="Expenses")

    wedges, legend_labels = draw_functional_pie(
        func_axes, _FUNC_YEARS, program_vals, mgmt_vals, fund_vals,
    )
    func_axes[1].text(0.5, 1.58, "Functional Expenses",
        ha="center", va="bottom", fontsize=FONT_TITLE, fontweight="bold",
        transform=func_axes[1].transAxes, clip_on=False)
    func_axes[1].legend(wedges, legend_labels,
        loc="upper center", bbox_to_anchor=(0, -1.48),
        bbox_transform=func_axes[1].transData,
        ncol=3, frameon=False, fontsize=FONT_LABEL)

    plt.tight_layout(rect=[0, 0, 1, 0.96], h_pad=3.0)
    pos = ax_cash.get_position()
    side = min(pos.width, pos.height)
    ax_cash.set_position([
        pos.x0 + (pos.width - side) / 2,
        pos.y0 + (pos.height - side) / 2,
        side, side,
    ])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, format="pdf")
    plt.close(fig)

    print(f"Wrote: {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
