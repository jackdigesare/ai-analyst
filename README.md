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

## Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).
