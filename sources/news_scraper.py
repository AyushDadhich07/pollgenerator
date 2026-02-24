"""
NewsAPI scraper — fetches India-specific news articles.
Free tier: 100 requests/day, results up to 1 month old.
Get your key at: newsapi.org
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict


NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def fetch_news_articles(
    api_key: str,
    query: str = "India trending",
    days_back: int = 2,
    page_size: int = 30,
) -> List[Dict]:
    """
    Fetch news articles from NewsAPI.

    Returns list of dicts with: title, description, source, url, published_at
    """
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "apiKey": api_key,
        "q": query,
        "language": "en",
        "sortBy": "popularity",
        "from": from_date,
        "pageSize": page_size,
    }

    resp = requests.get(NEWSAPI_BASE, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI error: {data.get('message', 'Unknown error')}")

    articles = []
    for a in data.get("articles", []):
        if not a.get("title") or a["title"] == "[Removed]":
            continue
        articles.append({
            "title": a.get("title", ""),
            "description": a.get("description", "") or "",
            "source": a.get("source", {}).get("name", "Unknown"),
            "url": a.get("url", ""),
            "published_at": a.get("publishedAt", ""),
        })

    return articles
