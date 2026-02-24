"""
Reddit scraper WITHOUT API keys.

Reality check (2024–2026):
- The public *.json endpoints still exist, but are frequently blocked (403) or rate-limited (429).
- This module tries multiple endpoints + uses retries/backoff.
- If JSON endpoints are blocked, it falls back to RSS (still no keys).

Notes:
- This is NOT the official Reddit API. For reliability, OAuth on oauth.reddit.com is the supported route.
"""

from __future__ import annotations

import time
import random
from typing import List, Dict, Optional
from urllib.parse import urlencode

import requests

# Optional dependency (recommended fallback)
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None


# Use a *realistic* UA. Generic bot UAs often get blocked faster.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


JSON_BASES = [
    # Sometimes www.reddit.com blocks while old.reddit.com works (and vice versa)
    "https://www.reddit.com",
    "https://old.reddit.com",
]

RSS_BASES = [
    "https://www.reddit.com",
    "https://old.reddit.com",
]


def _sleep_backoff(attempt: int) -> None:
    # Exponential backoff + jitter
    base = min(8, 2 ** attempt)
    jitter = random.uniform(0.25, 1.25)
    time.sleep(base + jitter)


def _safe_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _fetch_json_listing(url: str, timeout: int = 15) -> Optional[dict]:
    """
    Fetch a Reddit listing JSON with retries.
    Returns parsed JSON dict or None.
    """
    session = requests.Session()

    for attempt in range(4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)

            # Common failure modes:
            # 403 = blocked; 429 = rate limited
            if resp.status_code == 429:
                _sleep_backoff(attempt)
                continue

            if resp.status_code == 403:
                # Blocked: no point hammering quickly; backoff and then give up
                _sleep_backoff(attempt)
                return None

            resp.raise_for_status()

            # Some block pages return HTML despite status 200; guard by content-type and JSON parse
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "json" not in ctype:
                # Try parsing anyway; if it fails, treat as blocked/invalid
                try:
                    return resp.json()
                except Exception:
                    return None

            return resp.json()

        except requests.RequestException:
            _sleep_backoff(attempt)
        except ValueError:
            # JSON parse error
            return None

    return None


def _parse_posts_from_listing(data: dict, subreddit: str) -> List[Dict]:
    posts: List[Dict] = []

    try:
        children = data.get("data", {}).get("children", [])
    except Exception:
        return posts

    for item in children:
        post = (item or {}).get("data", {}) or {}
        if post.get("stickied"):
            continue

        posts.append(
            {
                "title": post.get("title", "") or "",
                "subreddit": subreddit,
                "score": _safe_int(post.get("score", 0), 0),
                "comments": _safe_int(post.get("num_comments", 0), 0),
                "url": post.get("url", "") or "",
                "selftext": (post.get("selftext", "") or "")[:300],
                "flair": post.get("link_flair_text", "") or "",
            }
        )

    return posts


def _fetch_rss_posts(subreddit: str, sort: str, limit: int) -> List[Dict]:
    """
    RSS fallback (no keys). This is less rich than JSON:
    - scores/comments often not available
    - content may be truncated/sanitized
    """
    if feedparser is None:
        return []

    # Reddit RSS patterns: /r/{sub}/.rss or /r/{sub}/{sort}.rss
    # In practice, /r/{sub}/{sort}.rss is commonly used.
    posts: List[Dict] = []

    for base in RSS_BASES:
        rss_url = f"{base}/r/{subreddit}/{sort}.rss"
        parsed = feedparser.parse(rss_url)

        # If blocked/invalid, parsed.bozo may be true; still try entries if present
        entries = getattr(parsed, "entries", None) or []
        if not entries:
            continue

        for e in entries[:limit]:
            title = getattr(e, "title", "") or ""
            link = getattr(e, "link", "") or ""
            summary = getattr(e, "summary", "") or ""

            posts.append(
                {
                    "title": title,
                    "subreddit": subreddit,
                    "score": 0,
                    "comments": 0,
                    "url": link,
                    "selftext": summary[:300],
                    "flair": "",
                }
            )

        if posts:
            break

    return posts


def fetch_reddit_posts(
    client_id: str,        # ignored, kept for compatibility
    client_secret: str,    # ignored, kept for compatibility
    subreddits: List[str],
    sort: str = "hot",
    limit: int = 10,
) -> List[Dict]:
    """
    Fetch posts using unauthenticated endpoints.
    Strategy:
      1) Try JSON listings from multiple bases with raw_json=1
      2) If JSON blocked, fall back to RSS (if feedparser installed)

    Returns list of normalized posts dicts.
    """
    posts: List[Dict] = []
    sort = (sort or "hot").strip().lower()
    if sort not in {"hot", "new", "top", "rising"}:
        sort = "hot"

    # keep limits sane
    limit = max(1, min(int(limit or 10), 50))

    for sub_name in subreddits:
        sub_name = (sub_name or "").strip()
        if not sub_name:
            continue

        got_any = False

        # --- JSON attempts ---
        params = {"limit": limit, "raw_json": 1}
        q = urlencode(params)

        for base in JSON_BASES:
            url = f"{base}/r/{sub_name}/{sort}.json?{q}"
            data = _fetch_json_listing(url=url)

            if data:
                posts.extend(_parse_posts_from_listing(data, sub_name))
                got_any = True
                # polite delay to reduce 429 risk
                time.sleep(random.uniform(0.8, 1.4))
                break

        # --- RSS fallback ---
        if not got_any:
            rss_posts = _fetch_rss_posts(subreddit=sub_name, sort=sort, limit=limit)
            if rss_posts:
                posts.extend(rss_posts)
                # polite delay
                time.sleep(random.uniform(0.8, 1.4))
            else:
                print(
                    f"[reddit_scraper] r/{sub_name} yielded no posts "
                    f"(JSON blocked/rate-limited and RSS unavailable/blocked)."
                )

    return posts
