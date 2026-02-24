# ⚡ CrowdVerse Poll Factory

Backend tool for generating controversial prediction polls for the CrowdVerse platform.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
crowdverse/
├── app.py                  # Main Streamlit app
├── requirements.txt
├── sources/
│   ├── reddit_scraper.py   # PRAW-based Reddit scraper
│   ├── news_scraper.py     # NewsAPI scraper
│   └── gnews_scraper.py    # GNews topic scraper
├── llm/
│   └── groq_client.py      # Groq LLM poll generator
└── utils/
    ├── filters.py          # Political content filter
    └── export.py           # CSV/JSON export
```

## API Keys Needed

| API     | Free Tier          | Where to get                      |
|---------|--------------------|-----------------------------------|
| Groq    | 14,400 req/day     | console.groq.com                  |
| Reddit  | 100 req/min        | reddit.com/prefs/apps             |
| NewsAPI | 100 req/day        | newsapi.org                       |
| GNews   | 100 req/day        | gnews.io                          |

## Features

- 🏏 Scrape Reddit India subreddits (r/india, r/Cricket, r/bollywood, etc.)
- 📰 Pull trending India news from NewsAPI and GNews
- 🤖 Generate polls using Groq (llama-3.3-70b-versatile — free, fast)
- 🚫 Auto-filter political content before LLM call
- 🔥 Controversy scoring (1-10)
- ✏️ Edit polls before approving
- 📋 Export approved polls as JSON/CSV
- 📊 Activity logs

## Groq Models Available

- `llama-3.3-70b-versatile` — Best quality (recommended)
- `llama-3.1-8b-instant` — Fastest, good for testing
- `mixtral-8x7b-32768` — Good balance
- `gemma2-9b-it` — Lightweight
