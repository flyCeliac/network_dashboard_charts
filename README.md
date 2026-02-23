# Network Financial Dashboard Generator

A web app that lets non-technical staff enter annual financial figures and generate a multi-chart PDF dashboard for board presentations.

**Live site:** [thenetworkdashboard.streamlit.app](https://thenetworkdashboard.streamlit.app)
**GitHub:** [github.com/flyCeliac/network_dashboard_charts](https://github.com/flyCeliac/network_dashboard_charts)

---

## What it does

The app presents a form with all the financial metrics used in the annual board dashboard. The user fills in the numbers for a new fiscal year, optionally selects a year range to display, clicks **Generate PDF**, and downloads a formatted multi-chart PDF.

Every time a PDF is generated, the data is saved back to this repository automatically — so the next person to open the site sees the prior year's figures as reference values in each field.

---

## Using the live site

1. Open [thenetworkdashboard.streamlit.app](https://thenetworkdashboard.streamlit.app)
2. Select the **year** you are adding at the top (defaults to the next new year)
3. Fill in **Revenue**, **Expenses**, **Functional Expenses**, and **Cash on Hand**
   - Prior year values are shown in parentheses next to each field for reference
   - Functional expense data typically lags 1–2 years — leave at $0 if not yet available
4. Use the **year range slider** to choose which years appear on the charts
5. Click **Generate PDF** — a download button will appear
6. To edit a past year, select it from the year dropdown — all fields will pre-fill with stored values

---

## Project structure

```
network_dashboard_charts/
├── web_app.py                  # Streamlit UI — the web form and PDF download
├── charts.py                   # Chart rendering engine (matplotlib)
├── data/
│   └── dashboard_data.json     # All historical financial data (source of truth)
├── requirements.txt            # Python dependencies
├── START.command               # macOS double-click launcher for local use
└── .streamlit/
    └── secrets.toml            # Local secrets (gitignored — never committed)
```

---

## Data format

All data lives in `data/dashboard_data.json`. Each metric is a dictionary keyed by year string:

```json
{
  "revenue": {
    "Membership Dues":       { "2022": 836127.20, "2023": 823118.39, ... },
    "Donations":             { "2022": 114963.79, ... },
    "Strategic Supporters":  { ... },
    "Grants Awarded":        { ... },
    "Fee-for-Service":       { ... },
    "Conference Revenue":    { ... },
    "pct_unrestricted":      { "2022": 3.1, ... }
  },
  "expenses": {
    "Programming":           { ... },
    "Personnel":             { ... },
    "Conference":            { ... },
    "Grants to Agencies":    { ... },
    "FTE Count":             { ... }
  },
  "functional": {
    "Program":               { "2022": 3448867, "2023": 4111765, "2024": 4394829 },
    "Management":            { ... },
    "Fundraising":           { ... },
    "Total Budget":          { ... }
  },
  "cash_card": {
    "headline": "Cash on Hand",
    "value": "18 months"
  }
}
```

**Note on functional expenses:** This data is typically available 1–2 years after the fiscal year closes (post-audit). The form always targets the next year after the last available functional year, independently of the main year selector.

---

## Making changes to the code

### Prerequisites
- Python 3.9+
- A GitHub account with access to this repository
- A personal access token with `repo` scope (for pushing changes)

### Local setup

```bash
git clone https://github.com/flyCeliac/network_dashboard_charts.git
cd network_dashboard_charts
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` with your credentials (this file is gitignored and never committed):

```toml
GITHUB_TOKEN = "ghp_your_personal_access_token"
GITHUB_REPO  = "flyCeliac/network_dashboard_charts"
```

Run locally:

```bash
venv/bin/python3 -m streamlit run web_app.py
```

Or on macOS, double-click `START.command`.

### Deploying changes

After editing code locally:

```bash
git add <changed files>
git commit -m "Description of what changed"
git push
```

Streamlit Cloud detects the push and redeploys automatically — usually within a minute.

---

## Deployment (Streamlit Community Cloud)

The app is hosted on [Streamlit Community Cloud](https://share.streamlit.io) (free tier).

**Secrets** are stored in the Streamlit Cloud dashboard (not in the repository):
- `GITHUB_TOKEN` — personal access token with `repo` scope, used to read and write `dashboard_data.json`
- `GITHUB_REPO` — `flyCeliac/network_dashboard_charts`

When the app is running locally and no secrets are present, it falls back to reading/writing the local JSON file directly.

**To transfer ownership** of the Streamlit deployment to a new maintainer:
1. The new maintainer creates a Streamlit Cloud account and links their GitHub
2. Deploy a new app pointed at this repo (`web_app.py`)
3. Add the secrets above in Advanced settings
4. The old deployment can then be deleted

---

## How the charts work

`charts.py` contains two entry points:

- `generate_from_data(data, out_path)` — used by the web app; takes the data dictionary and renders a PDF to `out_path`
- `main()` — legacy entry point that reads the original CSV file; retained for backwards compatibility

The PDF layout is a 5-row × 4-column matplotlib grid:
- Rows 0–2: Revenue charts (left) and Expense charts (right)
- Row 3: % Unrestricted Revenue, Cash on Hand card, Functional Expenses
- Row 4: Legend strip

When 5 or more years are shown, bar annotations automatically abbreviate (e.g. `$1.72M`, `$836K`) and bars narrow slightly to prevent overlap.

---

## Adding a new metric to the dashboard

1. Add the new metric to `dashboard_data.json` with historical values
2. Add a `st.number_input` field in `web_app.py` under the appropriate section
3. Add the save line inside the `if st.button("Generate PDF")` block
4. Add a `draw_bar` call in `generate_from_data()` inside `charts.py`, wiring up the new data

---

## Original data source

Historical data was extracted from `data/The Network Dashboard 2.17.csv`, which was the source spreadsheet used before this tool was built. The CSV is retained for reference but is no longer used by the app.
