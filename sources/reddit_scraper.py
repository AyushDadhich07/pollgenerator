"""
Reddit scraper using PRAW (Python Reddit API Wrapper).
Pulls hot/top/rising posts from specified subreddits.
"""
import praw
from typing import List, Dict


def fetch_reddit_posts(
    client_id: str,
    client_secret: str,
    subreddits: List[str],
    sort: str = "hot",
    limit: int = 10,
) -> List[Dict]:
    """
    Fetch posts from given subreddits.

    Returns list of dicts with: title, subreddit, score, comments, url, selftext
    """
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="CrowdVerse Poll Tool v1.0 (by /u/crowdverse_dev)",
    )

    posts = []
    for sub_name in subreddits:
        try:
            sub = reddit.subreddit(sub_name)
            if sort == "hot":
                submissions = sub.hot(limit=limit)
            elif sort == "top":
                submissions = sub.top("week", limit=limit)
            else:
                submissions = sub.rising(limit=limit)

            for post in submissions:
                # Skip stickied mod posts
                if post.stickied:
                    continue
                posts.append({
                    "title": post.title,
                    "subreddit": sub_name,
                    "score": post.score,
                    "comments": post.num_comments,
                    "url": post.url,
                    "selftext": post.selftext[:300] if post.selftext else "",
                    "flair": post.link_flair_text or "",
                })
        except Exception as e:
            # If subreddit fails (private, banned, etc.) just skip it
            print(f"[reddit_scraper] Skipping r/{sub_name}: {e}")
            continue

    return posts
