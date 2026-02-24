"""
GNews API scraper — topic-based India news.
Free tier: 100 requests/day, top 10 articles per request.
Get your key at: gnews.io
"""
import requests
from typing import List, Dict


GNEWS_BASE = "https://gnews.io/api/v4/top-headlines"


def fetch_gnews_articles(
    api_key: str,
    topic: str = "general",
    max_results: int = 10,
) -> List[Dict]:
    """
    Fetch top headlines from GNews for India.

    topic options: general, business, technology, entertainment, sports, science, health
    Returns list of dicts with: title, description, source, url, published_at
    """
    params = {
        "token": api_key,
        "lang": "en",
        "country": "in",
        "topic": topic,
        "max": max_results,
    }

    resp = requests.get(GNEWS_BASE, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    articles = []
    for a in data.get("articles", []):
        articles.append({
            "title": a.get("title", ""),
            "description": a.get("description", "") or "",
            "source": a.get("source", {}).get("name", "Unknown"),
            "url": a.get("url", ""),
            "published_at": a.get("publishedAt", ""),
        })

    return articles
