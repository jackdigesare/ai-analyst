# AI Analyst

Streamlit app that profiles CSV/Excel data and uses Gemini for insights and follow-up Q&A.

**Live demo:** [ai-analyst-assistants.streamlit.app](https://ai-analyst-assistants.streamlit.app/)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set a Gemini API key as `GEMINI_API_KEY` (or in `.streamlit/secrets.toml`).

Uploads are limited to 10 MB, 250,000 rows, and 500 columns; expanded XLSX
archives are capped at 50 MB. The app profiles files locally, then sends column
names, data types, aggregate statistics, and chat messages to Google Gemini only
after the user consents. Raw spreadsheet rows are not sent to Gemini.

## Deployment security

Each deployment uses one server-side Gemini API key. The app does not
authenticate users or enforce per-user/IP rate limits, so protect public
deployments with hosting-level authentication, an allowlist, or infrastructure
rate limiting. Configure provider quotas or budget alerts as an additional
safeguard. Per-session limits alone are not an abuse control because clients can
start new sessions.

## Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).
