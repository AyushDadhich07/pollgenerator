"""
Reddit scraper using public JSON API — zero auth required.
Just appends .json to Reddit URLs. Works for all public subreddits.
"""
import requests
import time
from typing import List, Dict

HEADERS = {"User-Agent": "CrowdVerse-PollTool/1.0"}


def fetch_reddit_posts(
    client_id: str,        # ignored, kept for compatibility
    client_secret: str,    # ignored, kept for compatibility
    subreddits: List[str],
    sort: str = "hot",
    limit: int = 10,
) -> List[Dict]:
    """
    Fetch posts using Reddit's public .json endpoint.
    No API key or app registration needed.
    """
    posts = []

    for sub_name in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub_name}/{sort}.json?limit={limit}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            for item in data["data"]["children"]:
                post = item["data"]
                if post.get("stickied"):
                    continue
                posts.append({
                    "title": post.get("title", ""),
                    "subreddit": sub_name,
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "url": post.get("url", ""),
                    "selftext": post.get("selftext", "")[:300],
                    "flair": post.get("link_flair_text", "") or "",
                })

            time.sleep(1)  # be polite, avoid rate limiting

        except Exception as e:
            print(f"[reddit_scraper] Skipping r/{sub_name}: {e}")
            continue

    return posts
