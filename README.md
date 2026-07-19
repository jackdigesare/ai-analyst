# AI Analyst

Streamlit app that profiles CSV/Excel data and uses Gemini for insights and follow-up Q&A.

**Live demo:** [data-analyst-ai-assistant.streamlit.app](https://data-analyst-ai-assistant.streamlit.app/)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set a Gemini API key as `GEMINI_API_KEY` (or in `.streamlit/secrets.toml`).

## Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).
