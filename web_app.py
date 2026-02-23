"""
Financial Dashboard Generator
------------------------------
Run with:  streamlit run web_app.py
"""

import base64
import json
import tempfile
from pathlib import Path

import requests
import streamlit as st

from charts import generate_from_data

DATA_FILE = Path("data/dashboard_data.json")

# ── GitHub-backed persistence (used when deployed on Streamlit Cloud) ─────────

def _github_headers():
    return {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}"}

def _github_url():
    repo = st.secrets["GITHUB_REPO"]
    return f"https://api.github.com/repos/{repo}/contents/data/dashboard_data.json"

def _use_github() -> bool:
    return "GITHUB_TOKEN" in st.secrets


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_data() -> dict:
    if _use_github():
        r = requests.get(_github_url(), headers=_github_headers())
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode()
        return json.loads(content)
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data: dict) -> None:
    if _use_github():
        # Fetch current SHA (required by GitHub API to update a file)
        r = requests.get(_github_url(), headers=_github_headers())
        r.raise_for_status()
        sha = r.json()["sha"]
        payload = {
            "message": "Update dashboard data",
            "content": base64.b64encode(
                json.dumps(data, indent=2).encode()
            ).decode(),
            "sha": sha,
        }
        r = requests.put(_github_url(), headers=_github_headers(), json=payload)
        r.raise_for_status()
        return
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def prev(data: dict, section: str, metric: str, year: int) -> float:
    """Return the prior year's value for reference, or 0."""
    return float(data[section][metric].get(str(year - 1), 0) or 0)


def existing_val(data: dict, section: str, metric: str, year: int) -> float:
    """Return the current stored value for this year, or 0."""
    return float(data[section][metric].get(str(year), 0) or 0)


# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_dollars(v: float) -> str:
    return f"${v:,.0f}" if v else "—"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%" if v else "—"


# ── Page ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Financial Dashboard Generator", layout="wide")
st.title("Financial Dashboard Generator")
st.caption("Select a year to add or edit, fill in the figures, then click **Generate PDF**.")

data = load_data()

# Year selector: all existing years + next 5 future years
existing_years = sorted(int(y) for y in data["revenue"]["Membership Dues"])
next_year_default = max(existing_years) + 1
all_years = existing_years + list(range(next_year_default, next_year_default + 5))

year = st.selectbox(
    "Year",
    options=all_years,
    index=len(existing_years),  # default to first new year
)
y = str(year)
py = year - 1  # prior year for reference labels

is_existing = year in existing_years
if is_existing:
    st.info(f"Editing existing data for **{year}**. Current values are pre-filled — change any field and regenerate.")


# ── Revenue ───────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Revenue")
st.caption(f"Prior year ({py}) shown in parentheses for reference.")

rc1, rc2 = st.columns(2)

with rc1:
    dues = st.number_input(
        f"Membership Dues  ({fmt_dollars(prev(data, 'revenue', 'Membership Dues', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Membership Dues', year),
        step=1000.0, format="%.2f")

    donations = st.number_input(
        f"Donations  ({fmt_dollars(prev(data, 'revenue', 'Donations', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Donations', year),
        step=1000.0, format="%.2f")

    supporters = st.number_input(
        f"Strategic Supporters  ({fmt_dollars(prev(data, 'revenue', 'Strategic Supporters', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Strategic Supporters', year),
        step=1000.0, format="%.2f")

    grants = st.number_input(
        f"Grants Awarded  ({fmt_dollars(prev(data, 'revenue', 'Grants Awarded', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Grants Awarded', year),
        step=1000.0, format="%.2f")

with rc2:
    ffs = st.number_input(
        f"Fee-for-Service  ({fmt_dollars(prev(data, 'revenue', 'Fee-for-Service', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Fee-for-Service', year),
        step=1000.0, format="%.2f")

    confrev = st.number_input(
        f"Conference Revenue  ({fmt_dollars(prev(data, 'revenue', 'Conference Revenue', year))})",
        min_value=0.0, value=existing_val(data, 'revenue', 'Conference Revenue', year),
        step=1000.0, format="%.2f")

    prior_unres = data["revenue"]["pct_unrestricted"].get(str(py), 0) or 0
    unres = st.number_input(
        f"% Unrestricted Revenue  ({fmt_pct(prior_unres)})",
        min_value=0.0, max_value=100.0,
        value=existing_val(data, 'revenue', 'pct_unrestricted', year),
        step=0.1, format="%.1f",
        help="Enter as a percentage, e.g. 5.2 for 5.2%")


# ── Expenses ──────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Expenses")
st.caption(f"Prior year ({py}) shown in parentheses for reference.")

ec1, ec2 = st.columns(2)

with ec1:
    prog_exp = st.number_input(
        f"Programming  ({fmt_dollars(prev(data, 'expenses', 'Programming', year))})",
        min_value=0.0, value=existing_val(data, 'expenses', 'Programming', year),
        step=1000.0, format="%.2f")

    personnel = st.number_input(
        f"Personnel  ({fmt_dollars(prev(data, 'expenses', 'Personnel', year))})",
        min_value=0.0, value=existing_val(data, 'expenses', 'Personnel', year),
        step=1000.0, format="%.2f")

with ec2:
    conf_exp = st.number_input(
        f"Conference  ({fmt_dollars(prev(data, 'expenses', 'Conference', year))})",
        min_value=0.0, value=existing_val(data, 'expenses', 'Conference', year),
        step=1000.0, format="%.2f")

    gta = st.number_input(
        f"Grants to Agencies  ({fmt_dollars(prev(data, 'expenses', 'Grants to Agencies', year))})",
        min_value=0.0, value=existing_val(data, 'expenses', 'Grants to Agencies', year),
        step=1000.0, format="%.2f")

st.markdown("**FTE Count**")
prior_fte = data["expenses"]["FTE Count"].get(str(py), 0) or 0
fte_actual = st.number_input(
    f"FTE  ({prior_fte:g} in {py})",
    min_value=0.0, value=existing_val(data, 'expenses', 'FTE Count', year),
    step=0.5, format="%.1f",
    help="Full-time equivalent headcount for this fiscal year")


# ── Functional Expenses ───────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Functional Expenses")
st.caption(
    "Functional expense data is often available 1–2 years after the fiscal year closes "
    "(typically after the audit). Leave at $0 if not yet available — the chart will "
    "only show years with data."
)

func_years_existing = sorted(int(y_) for y_ in data["functional"]["Program"])
func_prev_year = max(func_years_existing)
func_next_year = func_prev_year + 1
fy = str(func_next_year)

st.caption(f"Adding functional data for **{func_next_year}** (last available: {func_prev_year}).")

ff1, ff2 = st.columns(2)

with ff1:
    prog_func = st.number_input(
        f"Program  ({fmt_dollars(float(data['functional']['Program'].get(str(func_prev_year), 0) or 0))}  in {func_prev_year})",
        min_value=0.0, value=float(data['functional']['Program'].get(fy, 0) or 0),
        step=1000.0, format="%.2f")

    mgmt_func = st.number_input(
        f"Management  ({fmt_dollars(float(data['functional']['Management'].get(str(func_prev_year), 0) or 0))}  in {func_prev_year})",
        min_value=0.0, value=float(data['functional']['Management'].get(fy, 0) or 0),
        step=1000.0, format="%.2f")

with ff2:
    fund_func = st.number_input(
        f"Fundraising  ({fmt_dollars(float(data['functional']['Fundraising'].get(str(func_prev_year), 0) or 0))}  in {func_prev_year})",
        min_value=0.0, value=float(data['functional']['Fundraising'].get(fy, 0) or 0),
        step=1000.0, format="%.2f")

    total_budget = st.number_input(
        f"Total Budget  ({fmt_dollars(float(data['functional']['Total Budget'].get(str(func_prev_year), 0) or 0))}  in {func_prev_year})",
        min_value=0.0, value=float(data['functional']['Total Budget'].get(fy, 0) or 0),
        step=1000.0, format="%.2f",
        help="Sum of all functional expense categories")


# ── Cash on Hand ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Cash on Hand")
cash_value = st.text_input(
    "Display value on dashboard card",
    value=data["cash_card"]["value"],
    help='e.g. "18 months" or "21 months"')


# ── Generate ──────────────────────────────────────────────────────────────────

st.markdown("---")

if st.button("Generate PDF", type="primary", use_container_width=True):

    # Update data dict with this year's values
    data["revenue"]["Membership Dues"][y]       = dues
    data["revenue"]["Donations"][y]             = donations
    data["revenue"]["Strategic Supporters"][y]  = supporters
    data["revenue"]["Grants Awarded"][y]        = grants
    data["revenue"]["Fee-for-Service"][y]       = ffs
    data["revenue"]["Conference Revenue"][y]    = confrev
    data["revenue"]["pct_unrestricted"][y]      = unres

    data["expenses"]["Programming"][y]          = prog_exp
    data["expenses"]["Personnel"][y]            = personnel
    data["expenses"]["Conference"][y]           = conf_exp
    data["expenses"]["Grants to Agencies"][y]   = gta
    data["expenses"]["FTE Count"][y]            = fte_actual

    # Only add functional data if any values were entered
    if any(v > 0 for v in [prog_func, mgmt_func, fund_func, total_budget]):
        data["functional"]["Program"][fy]       = prog_func
        data["functional"]["Management"][fy]    = mgmt_func
        data["functional"]["Fundraising"][fy]   = fund_func
        data["functional"]["Total Budget"][fy]  = total_budget

    data["cash_card"]["value"] = cash_value

    # Remove functional years with all-zero values (keeps chart clean)
    func_years_all = sorted(int(k) for k in data["functional"]["Program"])
    for fyr in func_years_all:
        fyrs = str(fyr)
        vals = [
            data["functional"]["Program"].get(fyrs, 0) or 0,
            data["functional"]["Management"].get(fyrs, 0) or 0,
            data["functional"]["Fundraising"].get(fyrs, 0) or 0,
            data["functional"]["Total Budget"].get(fyrs, 0) or 0,
        ]
        if all(v == 0 for v in vals):
            for metric in ("Program", "Management", "Fundraising", "Total Budget"):
                data["functional"][metric].pop(fyrs, None)

    with st.spinner("Generating PDF…"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tmp_path = tf.name

        generate_from_data(data, tmp_path)
        save_data(data)

    all_rev_years = sorted(int(k) for k in data["revenue"]["Membership Dues"])
    filename = f"dashboard_{min(all_rev_years)}_{max(all_rev_years)}.pdf"

    with open(tmp_path, "rb") as f:
        st.download_button(
            label=f"⬇️  Download  {filename}",
            data=f.read(),
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )

    st.success(f"Dashboard generated for FY {min(all_rev_years)}–{max(all_rev_years)}. Data saved.")
