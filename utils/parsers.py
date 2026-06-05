"""
Utility helpers — URL normalisation, text cleaning, caching key generation.
"""

import re
import hashlib


def normalise_url(url_or_name: str) -> tuple[str, str]:
    """
    Given either a company name ("Stripe") or a URL ("https://stripe.com"),
    return (company_name, url).
    company_name is used for searches; url is used for web scraping.
    """
    url_or_name = url_or_name.strip()

    if url_or_name.startswith("http"):
        # It's a URL — derive company name from domain
        domain = re.sub(r"https?://", "", url_or_name).split("/")[0]
        domain = re.sub(r"^www\.", "", domain)
        name   = domain.split(".")[0].capitalize()
        return name, url_or_name

    # It's a company name — best-guess the URL
    slug = url_or_name.lower().replace(" ", "")
    url  = f"https://www.{slug}.com"
    return url_or_name, url


def cache_key(company: str, depth: str) -> str:
    """Stable cache key for st.cache_data."""
    raw = f"{company.lower().strip()}:{depth}"
    return hashlib.md5(raw.encode()).hexdigest()


def truncate(text: str, max_len: int = 300) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def risk_colour(level: str) -> str:
    """Return Streamlit-compatible colour string for a risk level."""
    return {
        "High":   "#e63946",
        "Medium": "#f4a261",
        "Low":    "#52b788",
        "None":   "#adb5bd",
    }.get(level, "#adb5bd")


def sentiment_emoji(sentiment: str) -> str:
    return {
        "Positive": "🟢",
        "Neutral":  "🟡",
        "Negative": "🔴",
        "Mixed":    "🟠",
    }.get(sentiment, "⚪")
