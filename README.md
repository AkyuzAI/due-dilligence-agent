# 🔍 Due Diligence Agent

An autonomous AI agent that researches any company and generates a structured due diligence report — complete with risk flags, funding data, sentiment analysis, and a confidence score.

Built with GPT-4o, Tavily, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red)
![OpenAI](https://img.shields.io/badge/GPT--4o-powered-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Architecture

```
User Input (company name / URL)
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│                   Orchestrator (GPT-4o)                  │
│  Decides which tools to call, in what order, how many    │
└────────────┬─────────────────────────────────────────────┘
             │  function calling loop (6–16 calls)
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          Research Tools                                    │
│  overview · website scraper · funding · news · negative signals ·          │
│  legal/regulatory · employee signals · competitive landscape               │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │  raw research data
                                     ▼
                           Synthesis (GPT-4o)
                           Pydantic schema enforcement
                                     │
                                     ▼
                          Structured Report JSON
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                    Streamlit UI           PDF Export
```

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/AkyuzAI/due-diligence-agent
cd due-diligence-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up API keys

```bash
cp .env.example .env
# Edit .env and add your keys
```

You need:
- **OpenAI API key** — [platform.openai.com](https://platform.openai.com)
- **Tavily API key** — [tavily.com](https://tavily.com) (free tier: 1,000 searches/month)

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## Report Sections

| Section | What it covers |
|---|---|
| Company Snapshot | Name, industry, HQ, size, business description |
| Business Model | How they make money, who they sell to |
| Funding & Financials | Rounds, investors, valuation, revenue signals |
| Market Position | Competitors, differentiation, moat |
| Risk Flags | Legal, regulatory, reputational — rated High/Medium/Low |
| Sentiment & News | News tone, headlines, employee signals |
| Confidence Score | 0–100 based on data availability |
| Sources | Every claim linked to a source |

---

## Deploy to Streamlit Cloud (free)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets: `OPENAI_API_KEY` and `TAVILY_API_KEY`
5. Deploy — you get a public URL instantly

---

## Research Depth

| Mode | Tool calls | Best for |
|---|---|---|
| Quick | 6 | Fast overview, well-known companies |
| Standard | 10 | Default — balanced speed and depth |
| Deep | 16 | Thorough research, complex companies |

---

## Tech Stack

- **LLM:** GPT-4o (OpenAI function calling)
- **Search:** Tavily API
- **Web scraping:** BeautifulSoup + requests
- **Schema enforcement:** Pydantic v2
- **Frontend:** Streamlit
- **PDF export:** fpdf2
- **Retry logic:** tenacity

---

## Extending

- **Add LangChain memory** to support multi-turn "ask a follow-up" on the report
- **Add a vector store (ChromaDB)** to index previous reports for comparison
- **Add NLP embeddings** on company descriptions for similarity search
- **Expose as MCP tool** so an LLM agent can call it autonomously
- **Add email delivery** — generate and email the PDF to the user

---

## Disclaimer

This tool is for research purposes only. It does not constitute financial, legal, or investment advice. Always verify findings independently before making decisions.

---

Built by [Dylan Akyuz](https://github.com/AkyuzAI)
