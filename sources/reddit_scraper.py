"""
Reddit scraper WITHOUT API keys.

Important reality check:
- Public *.json endpoints still exist, but are frequently blocked (403) or rate-limited (429)
  for unauthenticated scripts.
- This module tries multiple JSON endpoints + retries/backoff.
- If JSON is blocked, it falls back to RSS (still no keys).

This is not the official Reddit API. OAuth on oauth.reddit.com is the supported reliable route.
"""

from __future__ import annotations

import time
import random
from typing import List, Dict, Optional
from urllib.parse import urlencode

import requests

try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None


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
    "https://www.reddit.com",
    "https://old.reddit.com",
]

RSS_BASES = [
    "https://www.reddit.com",
    "https://old.reddit.com",
]


def _sleep_backoff(attempt: int) -> None:
    base = min(8, 2 ** attempt)
    jitter = random.uniform(0.25, 1.25)
    time.sleep(base + jitter)


def _safe_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _fetch_json_listing(url: str, timeout: int = 15) -> Optional[dict]:
    session = requests.Session()

    for attempt in range(4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)

            if resp.status_code == 429:
                _sleep_backoff(attempt)
                continue

            if resp.status_code == 403:
                _sleep_backoff(attempt)
                return None

            resp.raise_for_status()

            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "json" not in ctype:
                try:
                    return resp.json()
                except Exception:
                    return None

            return resp.json()

        except requests.RequestException:
            _sleep_backoff(attempt)
        except ValueError:
            return None

    return None


def _parse_posts_from_listing(data: dict, subreddit: str) -> List[Dict]:
    posts: List[Dict] = []

    children = (data or {}).get("data", {}).get("children", []) or []
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
    if feedparser is None:
        return []

    posts: List[Dict] = []
    for base in RSS_BASES:
        rss_url = f"{base}/r/{subreddit}/{sort}.rss"
        parsed = feedparser.parse(rss_url)
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
    posts: List[Dict] = []

    sort = (sort or "hot").strip().lower()
    if sort not in {"hot", "new", "top", "rising"}:
        sort = "hot"

    limit = max(1, min(int(limit or 10), 50))

    for sub_name in subreddits:
        sub_name = (sub_name or "").strip()
        if not sub_name:
            continue

        got_any = False

        params = {"limit": limit, "raw_json": 1}
        q = urlencode(params)

        for base in JSON_BASES:
            url = f"{base}/r/{sub_name}/{sort}.json?{q}"
            data = _fetch_json_listing(url=url)
            if data:
                posts.extend(_parse_posts_from_listing(data, sub_name))
                got_any = True
                time.sleep(random.uniform(0.8, 1.4))
                break

        if not got_any:
            rss_posts = _fetch_rss_posts(subreddit=sub_name, sort=sort, limit=limit)
            if rss_posts:
                posts.extend(rss_posts)
                time.sleep(random.uniform(0.8, 1.4))

    return posts
