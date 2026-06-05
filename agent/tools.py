"""
Research tools available to the agent.
Each tool is independently testable — run this file directly to test any tool.
"""

from __future__ import annotations
import os, json, requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL     = "https://api.tavily.com/search"


# ── Low-level Tavily caller ────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def _tavily(query: str, search_depth: str = "basic", max_results: int = 8) -> list[dict]:
    """
    Returns list of {title, url, content, score} dicts.
    Raises on API error after retries.
    """
    if not TAVILY_API_KEY:
        raise EnvironmentError("TAVILY_API_KEY not set in environment.")

    resp = requests.post(
        TAVILY_URL,
        json={
            "api_key":      TAVILY_API_KEY,
            "query":        query,
            "search_depth": search_depth,
            "max_results":  max_results,
            "include_answer": False,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _format_results(results: list[dict]) -> str:
    """Convert Tavily results to a clean string the LLM can read."""
    if not results:
        return "No results found."
    parts = []
    for r in results:
        parts.append(
            f"SOURCE: {r.get('url', 'unknown')}\n"
            f"TITLE:  {r.get('title', '')}\n"
            f"CONTENT: {r.get('content', '')[:600]}\n"
        )
    return "\n---\n".join(parts)


# ── Tool 1: General company overview ──────────────────────────────────────

def search_company_overview(company: str) -> str:
    """Broad overview — what the company does, founding, leadership, size."""
    results = _tavily(
        f"{company} company overview founding CEO employees industry",
        search_depth="advanced",
        max_results=8,
    )
    return _format_results(results)


# ── Tool 2: Website scraper ────────────────────────────────────────────────

def scrape_company_website(url: str) -> str:
    """
    Fetch and parse a company's website.
    Extracts text from homepage + /about if available.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    collected = []

    for path in ["", "/about", "/about-us", "/company"]:
        try:
            full_url = url.rstrip("/") + path
            r = requests.get(full_url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            # Remove nav, footer, scripts
            for tag in soup(["nav", "footer", "script", "style", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            # Trim to 1500 chars per page
            collected.append(f"URL: {full_url}\n{text[:1500]}")
        except Exception as e:
            collected.append(f"URL: {url + path} — failed to fetch: {e}")

    return "\n\n---\n\n".join(collected) if collected else "Could not scrape website."


# ── Tool 3: Funding & financials ───────────────────────────────────────────

def search_funding_financials(company: str) -> str:
    """Funding rounds, investors, valuation, revenue signals."""
    results = _tavily(
        f"{company} funding round valuation investors Series revenue Crunchbase PitchBook",
        search_depth="advanced",
        max_results=8,
    )
    return _format_results(results)


# ── Tool 4: News search ────────────────────────────────────────────────────

def search_news(company: str) -> str:
    """Recent news — positive AND negative. Last 18 months focus."""
    results = _tavily(
        f"{company} news 2024 2025",
        search_depth="advanced",
        max_results=10,
    )
    return _format_results(results)


# ── Tool 5: Negative signals ───────────────────────────────────────────────

def search_negative_signals(company: str) -> str:
    """Lawsuits, scandals, layoffs, regulatory actions, customer complaints."""
    results = _tavily(
        f"{company} lawsuit scandal layoffs regulatory fine FTC SEC complaint fraud controversy",
        search_depth="advanced",
        max_results=8,
    )
    return _format_results(results)


# ── Tool 6: Legal & regulatory ────────────────────────────────────────────

def search_legal_regulatory(company: str) -> str:
    """Government records, SEC filings, court cases, compliance issues."""
    results = _tavily(
        f"{company} SEC filing court case regulatory action government contract compliance",
        search_depth="advanced",
        max_results=8,
    )
    return _format_results(results)


# ── Tool 7: LinkedIn / employee signals ───────────────────────────────────

def search_employee_signals(company: str) -> str:
    """
    Headcount, hiring vs. layoffs, culture signals.
    Uses Tavily to surface LinkedIn and Glassdoor public data.
    """
    results = _tavily(
        f"{company} employees headcount hiring layoffs Glassdoor culture review LinkedIn",
        search_depth="basic",
        max_results=6,
    )
    return _format_results(results)


# ── Tool 8: Competitive landscape ─────────────────────────────────────────

def search_competitive_landscape(company: str) -> str:
    """Who are the competitors, how does this company compare."""
    results = _tavily(
        f"{company} competitors alternatives market share vs comparison",
        search_depth="basic",
        max_results=6,
    )
    return _format_results(results)


# ── OpenAI function schemas ────────────────────────────────────────────────
# These are fed to GPT-4o so it can decide which tools to call.

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_company_overview",
            "description": "General company overview: what they do, founders, CEO, employee count, history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name or domain."}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_company_website",
            "description": "Scrape the company's own website for ground-truth information about products, mission, and team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL including https://"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_funding_financials",
            "description": "Find funding rounds, investors, valuation, and revenue signals from Crunchbase, PitchBook, press releases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Find recent news about the company from the last 18 months.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_negative_signals",
            "description": "Search specifically for lawsuits, scandals, layoffs, regulatory actions, fraud, or customer complaints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_legal_regulatory",
            "description": "Find SEC filings, court cases, government contracts, or compliance/regulatory issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_employee_signals",
            "description": "Find headcount, hiring trends, layoffs, Glassdoor reviews, and employee culture signals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_competitive_landscape",
            "description": "Find key competitors, market positioning, and how this company compares to alternatives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"}
                },
                "required": ["company"],
            },
        },
    },
]

# Map tool name → function
TOOL_REGISTRY: dict[str, callable] = {
    "search_company_overview":     search_company_overview,
    "scrape_company_website":      scrape_company_website,
    "search_funding_financials":   search_funding_financials,
    "search_news":                 search_news,
    "search_negative_signals":     search_negative_signals,
    "search_legal_regulatory":     search_legal_regulatory,
    "search_employee_signals":     search_employee_signals,
    "search_competitive_landscape":search_competitive_landscape,
}


# ── Manual test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    print("=== Overview ===")
    print(search_company_overview(company))
    print("\n=== Funding ===")
    print(search_funding_financials(company))
