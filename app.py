import streamlit as st
import json
import os
import time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from sources.reddit_scraper import fetch_reddit_posts
from sources.news_scraper import fetch_news_articles
from sources.gnews_scraper import fetch_gnews_articles
from llm.groq_client import generate_polls_from_context
from utils.filters import filter_political_content
from utils.export import export_polls_to_csv, export_polls_to_json

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CrowdVerse Poll Factory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0d0d0d; color: #e5e5e5; }
    section[data-testid="stSidebar"] { display: none; }
    #MainMenu, footer, header { visibility: hidden; }

    .main-header {
        background: linear-gradient(135deg, #1a1a1a, #111);
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .brand {
        font-family: 'Space Mono', monospace;
        font-size: 26px;
        font-weight: 700;
        background: linear-gradient(90deg, #ff6b00, #ff0050);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle { font-family: 'Space Mono', monospace; font-size: 10px; color: #555; letter-spacing: 3px; margin-top: 2px; }

    .poll-card {
        background: #111;
        border: 1px solid #222;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 14px;
    }
    .poll-card:hover { border-color: #333; }
    .poll-card-genz {
        background: #0f0a1a;
        border: 1px solid #2a1a3a;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 14px;
    }
    .poll-card-genz:hover { border-color: #3a1a5a; }
    .approved-card {
        background: #0d1a12;
        border: 1px solid #1a3a1a;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .config-box {
        background: #111;
        border: 1px solid #1f1f1f;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .genz-mode-banner {
        background: linear-gradient(135deg, #1a0a2a, #0a0a1a);
        border: 1px solid #6b21a8;
        border-radius: 10px;
        padding: 12px 20px;
        margin-bottom: 16px;
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        color: #a855f7;
        letter-spacing: 1px;
    }
    .tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        margin-right: 6px;
        font-family: 'Space Mono', monospace;
    }
    .vibe-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-right: 4px;
        font-family: 'Space Mono', monospace;
    }
    .controversy-high { color: #ff0050; font-weight: 700; font-family: 'Space Mono', monospace; }
    .controversy-med  { color: #ff6b00; font-weight: 700; font-family: 'Space Mono', monospace; }
    .controversy-low  { color: #f59e0b; font-weight: 700; font-family: 'Space Mono', monospace; }

    .source-badge {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 5px;
        padding: 4px 10px;
        font-size: 11px;
        color: #666;
        font-family: 'Space Mono', monospace;
    }
    .section-label {
        font-family: 'Space Mono', monospace;
        font-size: 10px;
        color: #ff6b00;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    div[data-testid="stButton"] button {
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        letter-spacing: 1px;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #ff6b00, #ff0050);
        border: none;
        color: white;
    }
    .log-entry {
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        color: #555;
        padding: 4px 0;
        border-bottom: 1px solid #1a1a1a;
    }
    .log-entry.recent { color: #e5e5e5; }
    .argument-yes { background: #0d1a0d; border: 1px solid #1a3a1a; border-radius: 6px; padding: 12px; margin: 4px 0; font-size: 13px; }
    .argument-no  { background: #1a0d0d; border: 1px solid #3a1a1a; border-radius: 6px; padding: 12px; margin: 4px 0; font-size: 13px; }
    .resolution-box { background: #0f0f1a; border: 1px solid #1f1f3a; border-radius: 6px; padding: 12px; margin: 4px 0; font-size: 13px; }

    .stTabs [data-baseweb="tab-list"] { background: #111; border-bottom: 1px solid #222; gap: 0; }
    .stTabs [data-baseweb="tab"] { font-family: 'Space Mono', monospace; font-size: 11px; letter-spacing: 2px; color: #555; padding: 12px 20px; }
    .stTabs [aria-selected="true"] { color: #ff6b00 !important; border-bottom-color: #ff6b00 !important; }
    hr { border-color: #1f1f1f; }

    .subreddit-chip {
        display: inline-block;
        background: #1a1a2a;
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 10px;
        color: #7c7cff;
        margin: 2px;
        font-family: 'Space Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
for _k, _v in {
    "pending_polls": [],
    "approved_polls": [],
    "activity_log": [],
    "last_scraped_posts": {},
    "genz_mode": False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.activity_log.insert(0, f"[{ts}] {msg}")
    st.session_state.activity_log = st.session_state.activity_log[:50]


# ── Constants ─────────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "Cricket":               "#10b981",
    "Bollywood":             "#f59e0b",
    "Crypto":                "#8b5cf6",
    "Economy":               "#3b82f6",
    "Sports":                "#06b6d4",
    "Technology":            "#64748b",
    "Social Issues":         "#ec4899",
    "Entertainment":         "#f97316",
    "Business":              "#14b8a6",
    "Dating & Relationships": "#ff6b9d",
    "Gaming":                "#22d3ee",
    "Career & Campus":       "#a3e635",
    "Pop Culture":           "#f472b6",
}
CATEGORIES = list(CATEGORY_COLORS.keys())
GROQ_MODEL = "llama-3.3-70b-versatile"

GROQ_KEY    = os.getenv("GROQ_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
GNEWS_KEY   = os.getenv("GNEWS_KEY", "")

# ── All available subreddits organised by theme ───────────────────────────────
SUBREDDIT_OPTIONS = {
    # Original / core
    "🏏 Cricket & Sports":    ["Cricket", "ipl", "IndianSports", "FantasyPowerPlay11"],
    "🎬 Entertainment":       ["bollywood", "bollywoodmemes", "IndianCinema", "desimemes", "BollyBlindsNGossip"],
    "💰 Finance & Crypto":    ["IndianStreetBets", "CryptoCurrencyIndia", "IndiaInvestments", "IndianStockMarket"],
    "🛠️ Tech & Startups":     ["IndiaTech", "startups", "Entrepreneur", "developersIndia", "IndianGaming"],
    "🔥 GenZ Controversy":    ["AskIndia", "india", "UnitedStatesOfIndia", "TwoXIndia", "IndiaSocial"],
    "💘 Dating & Life":       ["RelationshipIndia", "Arrangedmarriage", "ForeverAloneIndia", "DatingAppsIndia"],
    "🎓 Career & Campus":     ["Indian_Academia", "cscareerquestionsIN", "CATpreparation", "UPSC"],
}
ALL_SUBREDDITS = [sub for group in SUBREDDIT_OPTIONS.values() for sub in group]

DEFAULT_SUBREDDITS = ["AskIndia", "Cricket", "bollywood", "IndianStreetBets", "RelationshipIndia", "IndiaTech", "BollyBlindsNGossip"]

VIBE_COLORS = {
    "Spicy":  ("#ff0050", "#1a0010"),
    "Drama":  ("#f59e0b", "#1a1000"),
    "Clout":  ("#8b5cf6", "#10081a"),
    "Grind":  ("#10b981", "#001a10"),
    "Cope":   ("#64748b", "#0a0f14"),
    "Wild":   ("#06b6d4", "#00141a"),
    "Tea":    ("#f97316", "#1a0a00"),
}


def vibe_badge(vibe: str) -> str:
    color, bg = VIBE_COLORS.get(vibe, ("#888", "#111"))
    return f'<span class="vibe-tag" style="background:{bg};color:{color};border:1px solid {color}44">{vibe.upper()}</span>'


# ── Header ────────────────────────────────────────────────────────────────────
high_heat = len([p for p in st.session_state.pending_polls if p.get("controversy_score", 0) >= 8])
genz_count = len([p for p in st.session_state.pending_polls if p.get("genz_mode")])
st.markdown(f"""
<div class="main-header">
  <div>
    <div class="brand">⚡ CrowdVerse</div>
    <div class="subtitle">POLL FACTORY — INTERNAL TOOL</div>
  </div>
  <div style="display:flex; gap:28px; font-family: Space Mono, monospace;">
    <div style="text-align:center">
      <div style="font-size:22px; font-weight:700; color:#ff6b00">{len(st.session_state.pending_polls)}</div>
      <div style="font-size:9px; color:#555; letter-spacing:1px">PENDING</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:22px; font-weight:700; color:#10b981">{len(st.session_state.approved_polls)}</div>
      <div style="font-size:9px; color:#555; letter-spacing:1px">APPROVED</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:22px; font-weight:700; color:#ff0050">{high_heat}</div>
      <div style="font-size:9px; color:#555; letter-spacing:1px">🔥 HIGH HEAT</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:22px; font-weight:700; color:#a855f7">{genz_count}</div>
      <div style="font-size:9px; color:#555; letter-spacing:1px">⚡ GEN Z</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_gen, tab_review, tab_approved, tab_logs = st.tabs([
    "01 // GENERATE",
    f"02 // REVIEW  ({len(st.session_state.pending_polls)})",
    f"03 // APPROVED  ({len(st.session_state.approved_polls)})",
    "04 // LOGS",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERATE
# ═════════════════════════════════════════════════════════════════════════════
with tab_gen:

    # ── Gen Z Mode Toggle ─────────────────────────────────────────────────────
    gz_col, _ = st.columns([2, 5])
    with gz_col:
        genz_mode = st.toggle(
            "⚡ Gen Z Mode (Max Controversy)",
            value=st.session_state.genz_mode,
            help="Cranks up the prompt aggression for spicier, more culture-war-y polls. Uses a higher LLM temperature.",
        )
        st.session_state.genz_mode = genz_mode

    if genz_mode:
        st.markdown(
            '<div class="genz-mode-banner">🔥 GEN Z MODE ON — Prompts are maximally aggressive. Expect hot takes, drama, and unhinged predictions. Temperature: 0.97</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">SELECT SOURCE</div>', unsafe_allow_html=True)
    source_choice = st.radio(
        "source", ["🏏  Reddit India", "📰  NewsAPI", "🌐  GNews", "✍️  Manual Topic"],
        horizontal=True, label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="config-box">', unsafe_allow_html=True)

    if "Reddit" in source_choice:
        st.markdown('<div class="section-label">REDDIT CONFIG</div>', unsafe_allow_html=True)

        # Theme-based quick selects
        st.caption("Quick theme presets:")
        preset_cols = st.columns(len(SUBREDDIT_OPTIONS))
        selected_preset_subs = set()
        for i, (theme, subs) in enumerate(SUBREDDIT_OPTIONS.items()):
            with preset_cols[i]:
                if st.button(theme, use_container_width=True, key=f"preset_{i}"):
                    selected_preset_subs.update(subs)

        rc1, rc2, rc3 = st.columns([3, 1, 1])
        with rc1:
            subreddits = st.multiselect(
                "Subreddits",
                ALL_SUBREDDITS,
                default=list(selected_preset_subs) if selected_preset_subs else DEFAULT_SUBREDDITS,
                help="Mix subreddits across themes for more diverse polls. GenZ controversy subreddits (AskIndia, RelationshipIndia, BollyBlindsNGossip) produce the spiciest content.",
            )
        with rc2:
            reddit_sort = st.selectbox("Sort", ["hot", "top", "rising"])
        with rc3:
            reddit_limit = st.slider("Posts/sub", 5, 25, 10)

        # Show subreddit theme info
        if subreddits:
            st.markdown("**Selected subreddits:**")
            badge_html = " ".join([f'<span class="subreddit-chip">r/{s}</span>' for s in subreddits])
            st.markdown(badge_html, unsafe_allow_html=True)

    elif "NewsAPI" in source_choice:
        st.markdown('<div class="section-label">NEWSAPI CONFIG</div>', unsafe_allow_html=True)
        na1, na2 = st.columns([3, 1])
        with na1:
            news_query = st.text_input("Search query", value="India trending 2025")
        with na2:
            news_days = st.slider("Days back", 1, 7, 2)

    elif "GNews" in source_choice:
        st.markdown('<div class="section-label">GNEWS CONFIG</div>', unsafe_allow_html=True)
        gnews_topic = st.selectbox(
            "Topic", ["general", "business", "technology", "entertainment", "sports", "science", "health"],
        )

    else:
        st.markdown('<div class="section-label">MANUAL INPUT</div>', unsafe_allow_html=True)
        manual_topic = st.text_area(
            "Topic / context",
            placeholder="e.g. IPL 2025 mega auction — Rohit Sharma unsold, Virat retention controversy...",
            height=100,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Generation settings inline
    st.markdown('<div class="section-label">GENERATION SETTINGS</div>', unsafe_allow_html=True)
    gs1, gs2, gs3, gs4 = st.columns(4)
    with gs1:
        polls_per_source = st.slider("Polls to generate", 4, 16, 8)
    with gs2:
        min_controversy = st.slider(
            "Min controversy score", 1, 10, 7,
            help="Polls scoring below this are discarded. GenZ-relevant polls should be 7+."
        )
    with gs3:
        cat_filter_gen = st.multiselect("Restrict to categories", CATEGORIES, placeholder="All categories")
    with gs4:
        vibe_filter = st.multiselect(
            "Filter by vibe",
            ["Spicy", "Drama", "Clout", "Grind", "Cope", "Wild", "Tea"],
            placeholder="All vibes",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    generate_btn = st.button("⚡  GENERATE POLLS", type="primary", use_container_width=True)

    if generate_btn:
        missing = []
        if not GROQ_KEY:
            missing.append("GROQ_API_KEY")
        if "NewsAPI" in source_choice and not NEWSAPI_KEY:
            missing.append("NEWSAPI_KEY")
        if "GNews" in source_choice and not GNEWS_KEY:
            missing.append("GNEWS_KEY")

        if missing:
            st.error(f"⚠️ Missing secrets: {', '.join(missing)} — add to Streamlit Cloud secrets or .env file")
        else:
            progress = st.progress(0, text="Initializing...")
            status = st.empty()
            raw_items = []

            try:
                if "Reddit" in source_choice:
                    status.info("🔄 Scraping Reddit posts...")
                    add_log(f"Scraping Reddit: {', '.join(subreddits)} | GenZ Mode: {genz_mode}")

                    polls_per_sub = max(1, polls_per_source // len(subreddits))
                    all_new_polls = []

                    for sub_idx, sub_name in enumerate(subreddits):
                        progress.progress(
                            10 + int(40 * sub_idx / len(subreddits)),
                            text=f"Scraping r/{sub_name}..."
                        )
                        status.info(f"🔄 Scraping r/{sub_name}...")

                        sub_posts = fetch_reddit_posts(None, None, [sub_name], reddit_sort, reddit_limit)
                        st.session_state.last_scraped_posts[sub_name] = sub_posts or []
                        if not sub_posts:
                            add_log(f"⚠️ No posts from r/{sub_name}, skipping")
                            continue

                        sub_raw_items = [
                            f"{p['title']} · ⬆️{p['score']} 💬{p['comments']}"
                            for p in sub_posts
                        ]
                        context_text = "\n".join([
                            f"- {p['title']} (score:{p['score']}, comments:{p['comments']}, flair:{p['flair']})\n  {p['selftext']}"
                            for p in sub_posts
                        ])
                        source_label = f"Reddit · r/{sub_name}"

                        context_text = filter_political_content(context_text)

                        progress.progress(
                            10 + int(40 * (sub_idx + 0.5) / len(subreddits)),
                            text=f"Generating polls for r/{sub_name}..."
                        )
                        status.info(f"🤖 Generating {polls_per_sub} polls from r/{sub_name}... {'⚡ Gen Z Mode' if genz_mode else ''}")

                        allowed_cats = cat_filter_gen if cat_filter_gen else CATEGORIES
                        sub_polls = generate_polls_from_context(
                            api_key=GROQ_KEY,
                            model=GROQ_MODEL,
                            context=context_text,
                            n_polls=polls_per_sub,
                            categories=allowed_cats,
                            source_label=source_label,
                            genz_mode=genz_mode,
                        )

                        for p in sub_polls:
                            p["source_items"] = sub_raw_items
                            p["subreddit"] = sub_name

                        add_log(f"r/{sub_name}: {len(sub_polls)} polls generated from {len(sub_posts)} posts")
                        all_new_polls.extend(sub_polls)

                    # Apply filters
                    filtered = [
                        p for p in all_new_polls
                        if p.get("controversy_score", 0) >= min_controversy
                        and (not cat_filter_gen or p.get("category") in cat_filter_gen)
                        and (not vibe_filter or p.get("vibe") in vibe_filter)
                    ]
                    discarded = len(all_new_polls) - len(filtered)
                    st.session_state.pending_polls.extend(filtered)
                    add_log(f"✅ {len(filtered)} polls added, {discarded} discarded (score/vibe filter)")

                    progress.progress(100, text="Done!")
                    status.success(f"✅ {len(filtered)} polls ready — head to REVIEW tab!")
                    time.sleep(1.5)
                    status.empty()
                    progress.empty()
                    st.rerun()

                elif "NewsAPI" in source_choice:
                    status.info("🔄 Fetching from NewsAPI...")
                    add_log(f"NewsAPI query: '{news_query}'")
                    articles = fetch_news_articles(NEWSAPI_KEY, news_query, news_days)
                    raw_items = [f"{a['source']}: {a['title']}" for a in articles]
                    context_text = "\n".join([
                        f"- {a['title']} ({a['source']}, {a['published_at'][:10]}): {a['description']}"
                        for a in articles
                    ])
                    source_label = f"NewsAPI · {news_query}"
                    add_log(f"Fetched {len(articles)} articles")
                    progress.progress(30, text=f"Got {len(articles)} articles...")

                    status.info(f"🤖 Generating polls... {'⚡ Gen Z Mode' if genz_mode else ''}")
                    context_text = filter_political_content(context_text)
                    allowed_cats = cat_filter_gen if cat_filter_gen else CATEGORIES
                    new_polls = generate_polls_from_context(
                        api_key=GROQ_KEY, model=GROQ_MODEL, context=context_text,
                        n_polls=polls_per_source, categories=allowed_cats,
                        source_label=source_label, genz_mode=genz_mode,
                    )
                    for p in new_polls:
                        p["source_items"] = raw_items
                    filtered = [
                        p for p in new_polls
                        if p.get("controversy_score", 0) >= min_controversy
                        and (not cat_filter_gen or p.get("category") in cat_filter_gen)
                        and (not vibe_filter or p.get("vibe") in vibe_filter)
                    ]
                    st.session_state.pending_polls.extend(filtered)
                    add_log(f"✅ {len(filtered)} polls added from NewsAPI")
                    progress.progress(100, text="Done!")
                    status.success(f"✅ {len(filtered)} polls ready!")
                    time.sleep(1.5)
                    status.empty()
                    progress.empty()
                    st.rerun()

                elif "GNews" in source_choice:
                    status.info("🔄 Fetching from GNews...")
                    add_log(f"GNews topic: {gnews_topic}")
                    articles = fetch_gnews_articles(GNEWS_KEY, gnews_topic)
                    raw_items = [f"{a['source']}: {a['title']}" for a in articles]
                    context_text = "\n".join([
                        f"- {a['title']} ({a['source']}, {a['published_at'][:10]}): {a['description']}"
                        for a in articles
                    ])
                    source_label = f"GNews · {gnews_topic}"
                    add_log(f"Fetched {len(articles)} articles")
                    progress.progress(30, text=f"Got {len(articles)} articles...")

                    status.info(f"🤖 Generating polls... {'⚡ Gen Z Mode' if genz_mode else ''}")
                    context_text = filter_political_content(context_text)
                    allowed_cats = cat_filter_gen if cat_filter_gen else CATEGORIES
                    new_polls = generate_polls_from_context(
                        api_key=GROQ_KEY, model=GROQ_MODEL, context=context_text,
                        n_polls=polls_per_source, categories=allowed_cats,
                        source_label=source_label, genz_mode=genz_mode,
                    )
                    for p in new_polls:
                        p["source_items"] = raw_items
                    filtered = [
                        p for p in new_polls
                        if p.get("controversy_score", 0) >= min_controversy
                        and (not cat_filter_gen or p.get("category") in cat_filter_gen)
                        and (not vibe_filter or p.get("vibe") in vibe_filter)
                    ]
                    st.session_state.pending_polls.extend(filtered)
                    add_log(f"✅ {len(filtered)} polls added from GNews")
                    progress.progress(100, text="Done!")
                    status.success(f"✅ {len(filtered)} polls ready!")
                    time.sleep(1.5)
                    status.empty()
                    progress.empty()
                    st.rerun()

                else:
                    raw_items = [manual_topic]
                    context_text = filter_political_content(manual_topic)
                    source_label = "Manual Input"
                    progress.progress(30, text="Using manual input...")
                    add_log("Manual topic input used")

                    status.info(f"🤖 Generating polls... {'⚡ Gen Z Mode' if genz_mode else ''}")
                    allowed_cats = cat_filter_gen if cat_filter_gen else CATEGORIES
                    new_polls = generate_polls_from_context(
                        api_key=GROQ_KEY, model=GROQ_MODEL, context=context_text,
                        n_polls=polls_per_source, categories=allowed_cats,
                        source_label=source_label, genz_mode=genz_mode,
                    )
                    for p in new_polls:
                        p["source_items"] = raw_items
                    filtered = [
                        p for p in new_polls
                        if p.get("controversy_score", 0) >= min_controversy
                        and (not cat_filter_gen or p.get("category") in cat_filter_gen)
                        and (not vibe_filter or p.get("vibe") in vibe_filter)
                    ]
                    st.session_state.pending_polls.extend(filtered)
                    add_log(f"✅ {len(filtered)} polls added from manual input")
                    progress.progress(100, text="Done!")
                    status.success(f"✅ {len(filtered)} polls ready!")
                    time.sleep(1.5)
                    status.empty()
                    progress.empty()
                    st.rerun()

            except Exception as e:
                status.error(f"❌ {str(e)}")
                add_log(f"❌ Error: {str(e)}")
                progress.empty()


    # ── Inspect last scraped Reddit titles ─────────────────────────────────────
    if st.session_state.get("last_scraped_posts"):
        with st.expander("🧾 Last scraped Reddit post titles", expanded=False):
            for _sub, _posts in st.session_state.last_scraped_posts.items():
                st.markdown(f"**r/{_sub}** — {len(_posts)} posts")
                for _p in _posts:
                    _t = (_p.get("title") or "").strip()
                    _u = (_p.get("url") or "").strip()
                    if not _t:
                        continue
                    if _u:
                        st.markdown(f"- [{_t}]({_u})")
                    else:
                        st.markdown(f"- {_t}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — REVIEW
# ═════════════════════════════════════════════════════════════════════════════
with tab_review:
    pending = st.session_state.pending_polls

    if not pending:
        st.markdown("""
        <div style="text-align:center; padding:80px 0; color:#333">
          <div style="font-size:52px">📭</div>
          <div style="font-family:Space Mono,monospace; font-size:11px; letter-spacing:2px; margin-top:14px; color:#444">
            NO POLLS TO REVIEW — GENERATE SOME FIRST
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        fc1, fc2, fc3 = st.columns([2, 2, 3])
        with fc1:
            cat_filter = st.selectbox("Filter category", ["All"] + CATEGORIES, key="review_cat_filter")
        with fc2:
            score_filter = st.selectbox("Min score", ["All", "7+", "8+", "9+", "10"], key="review_score_filter")
        with fc3:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption(f"{len(pending)} polls pending")

        min_score_map = {"All": 0, "7+": 7, "8+": 8, "9+": 9, "10": 10}
        min_score_val = min_score_map.get(score_filter, 0)

        display_polls = [
            (i, p) for i, p in enumerate(pending)
            if (cat_filter == "All" or p.get("category") == cat_filter)
            and p.get("controversy_score", 0) >= min_score_val
        ]

        st.markdown("---")
        to_approve, to_reject = [], []

        for orig_idx, poll in display_polls:
            cat       = poll.get("category", "Unknown")
            cat_color = CATEGORY_COLORS.get(cat, "#555")
            score     = poll.get("controversy_score", 5)
            pid       = poll.get("id", str(orig_idx))
            score_cls = "controversy-high" if score >= 8 else "controversy-med" if score >= 6 else "controversy-low"
            is_genz   = poll.get("genz_mode", False)
            vibe      = poll.get("vibe", "")

            card_class = "poll-card-genz" if is_genz else "poll-card"

            with st.container():
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                h1, h2, h3 = st.columns([5, 1, 1])
                with h1:
                    _sub = poll.get("subreddit")
                    subreddit_tag = ""
                    if _sub:
                        subreddit_tag = (
                            f'<span class="tag" style="margin-left:6px;background:#0ea5e922;color:#0ea5e9;border:1px solid #0ea5e955">r/{_sub}</span>'
                        )
                    genz_tag = '<span class="tag" style="background:#6b21a822;color:#a855f7;border:1px solid #6b21a855">⚡ GENZ</span>' if is_genz else ""
                    vibe_html = vibe_badge(vibe) if vibe else ""

                    st.markdown(
                        f'<span class="tag" style="background:{cat_color}22;color:{cat_color};border:1px solid {cat_color}55">{cat.upper()}</span>'
                        f'{subreddit_tag}{genz_tag}{vibe_html}'
                        f'<span class="source-badge">{poll.get("source","?")}</span>',
                        unsafe_allow_html=True
                    )
                with h2:
                    st.markdown(f'<span class="{score_cls}">🔥 {score}/10</span>', unsafe_allow_html=True)
                with h3:
                    st.markdown(
                        f'<span style="color:#8b5cf6;font-family:Space Mono,monospace;font-size:12px">⚡ {poll.get("token_pool",1000):,}</span>',
                        unsafe_allow_html=True
                    )

                st.markdown(f"**{poll.get('question', 'N/A')}**")
                st.caption(f"📅 {poll.get('deadline','?')}  ·  {poll.get('why_controversial','')}")

                tags = poll.get("tags", [])
                if tags:
                    st.markdown("  ".join([f"`#{t}`" for t in tags]))

                source_items = poll.get("source_items", [])
                if source_items:
                    with st.expander(f"📰 Source data used ({len(source_items)} items)"):
                        for item in source_items:
                            st.markdown(
                                f'<div style="font-size:11px;color:#555;padding:3px 0;border-bottom:1px solid #1a1a1a;font-family:Space Mono,monospace">• {item}</div>',
                                unsafe_allow_html=True
                            )

                with st.expander("📊 YES / NO arguments & resolution"):
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown(
                            '<div class="argument-yes"><div style="font-size:10px;color:#10b981;letter-spacing:1px;margin-bottom:6px;font-family:Space Mono,monospace">✅ YES CASE</div>'
                            + poll.get("yes_argument", "") + '</div>',
                            unsafe_allow_html=True
                        )
                    with d2:
                        st.markdown(
                            '<div class="argument-no"><div style="font-size:10px;color:#ff6b6b;letter-spacing:1px;margin-bottom:6px;font-family:Space Mono,monospace">❌ NO CASE</div>'
                            + poll.get("no_argument", "") + '</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown(
                        '<div class="resolution-box"><div style="font-size:10px;color:#8b5cf6;letter-spacing:1px;margin-bottom:6px;font-family:Space Mono,monospace">🎯 RESOLUTION</div>'
                        + poll.get("resolution", "") + '</div>',
                        unsafe_allow_html=True
                    )

                with st.expander("✏️ Edit"):
                    new_q = st.text_input("Question", value=poll.get("question", ""), key=f"q_{pid}")
                    e1, e2, e3, e4 = st.columns(4)
                    with e1:
                        new_cat = st.selectbox("Category", CATEGORIES,
                                               index=CATEGORIES.index(cat) if cat in CATEGORIES else 0,
                                               key=f"cat_{pid}")
                    with e2:
                        new_dl = st.text_input("Deadline", value=poll.get("deadline", ""), key=f"editdl_{pid}")
                    with e3:
                        new_pool = st.number_input("Token Pool", value=int(poll.get("token_pool", 1000)),
                                                   step=500, key=f"pool_{pid}")
                    with e4:
                        new_score = st.number_input("Controversy Score", value=int(poll.get("controversy_score", 5)),
                                                    min_value=1, max_value=10, key=f"score_{pid}")
                    new_res = st.text_area("Resolution Condition", value=poll.get("resolution", ""), key=f"res_{pid}")
                    if st.button("💾 Save", key=f"save_{pid}"):
                        st.session_state.pending_polls[orig_idx].update({
                            "question": new_q, "category": new_cat,
                            "deadline": new_dl, "token_pool": new_pool,
                            "resolution": new_res, "controversy_score": new_score,
                        })
                        st.success("Saved!")
                        st.rerun()

                a1, a2, a3 = st.columns([3, 1, 1])
                with a1:
                    if st.button("✓  APPROVE", key=f"approve_{pid}", type="primary", use_container_width=True):
                        to_approve.append(orig_idx)
                with a2:
                    if st.button("🗑  REJECT", key=f"reject_{pid}", use_container_width=True):
                        to_reject.append(orig_idx)
                with a3:
                    st.download_button(
                        "📋 JSON", json.dumps(poll, indent=2),
                        f"poll_{pid}.json", use_container_width=True, key=f"jsonbtn_{pid}"
                    )

                st.markdown("</div>", unsafe_allow_html=True)

        for idx in sorted(set(to_approve), reverse=True):
            p = st.session_state.pending_polls[idx]
            p["approved_at"] = datetime.now().isoformat()
            st.session_state.approved_polls.append(p)
            st.session_state.pending_polls.pop(idx)
            add_log(f"✅ Approved: {p.get('question','')[:60]}...")
        for idx in sorted(set(to_reject), reverse=True):
            p = st.session_state.pending_polls[idx]
            st.session_state.pending_polls.pop(idx)
            add_log(f"🗑️ Rejected: {p.get('question','')[:60]}...")
        if to_approve or to_reject:
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — APPROVED
# ═════════════════════════════════════════════════════════════════════════════
with tab_approved:
    approved = st.session_state.approved_polls

    if not approved:
        st.markdown("""
        <div style="text-align:center; padding:80px 0">
          <div style="font-size:52px">✅</div>
          <div style="font-family:Space Mono,monospace; font-size:11px; letter-spacing:2px; margin-top:14px; color:#444">
            NO APPROVED POLLS YET
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-label">EXPORT</div>', unsafe_allow_html=True)
        ex1, ex2, ex3 = st.columns([1, 1, 4])
        with ex1:
            st.download_button(
                "📄 Download CSV", export_polls_to_csv(approved),
                "crowdverse_polls.csv", "text/csv", use_container_width=True,
            )
        with ex2:
            st.download_button(
                "📋 Download JSON", export_polls_to_json(approved),
                "crowdverse_polls.json", "application/json", use_container_width=True,
            )

        st.markdown("---")

        af1, af2 = st.columns([2, 2])
        with af1:
            approved_cat_filter = st.selectbox("Filter", ["All"] + CATEGORIES, key="approved_cat_filter")
        with af2:
            approved_vibe_filter = st.selectbox(
                "Filter by vibe", ["All", "Spicy", "Drama", "Clout", "Grind", "Cope", "Wild", "Tea"],
                key="approved_vibe_filter"
            )

        display_approved = [
            p for p in approved
            if (approved_cat_filter == "All" or p.get("category") == approved_cat_filter)
            and (approved_vibe_filter == "All" or p.get("vibe") == approved_vibe_filter)
        ]

        # Analytics summary
        if display_approved:
            avg_score = sum(p.get("controversy_score", 5) for p in display_approved) / len(display_approved)
            genz_pct = 100 * sum(1 for p in display_approved if p.get("genz_mode")) / len(display_approved)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Approved", len(display_approved))
            m2.metric("Avg Controversy", f"{avg_score:.1f}/10")
            m3.metric("Gen Z Mode %", f"{genz_pct:.0f}%")
            m4.metric("High Heat (8+)", sum(1 for p in display_approved if p.get("controversy_score", 0) >= 8))

        st.markdown("---")

        df_data = [{
            "Category":  p.get("category", ""),
            "Question":  p.get("question", "")[:85] + ("..." if len(p.get("question", "")) > 85 else ""),
            "🔥 Score":  p.get("controversy_score", ""),
            "Vibe":      p.get("vibe", ""),
            "⚡ Tokens": f'{p.get("token_pool", 0):,}',
            "Deadline":  p.get("deadline", ""),
            "Gen Z":     "⚡" if p.get("genz_mode") else "",
            "Approved":  p.get("approved_at", "")[:10],
        } for p in display_approved]
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

        st.markdown("---")

        for poll in display_approved:
            cat = poll.get("category", "?")
            cat_color = CATEGORY_COLORS.get(cat, "#555")
            vibe = poll.get("vibe", "")
            vibe_html = vibe_badge(vibe) if vibe else ""
            genz_badge = '<span style="color:#a855f7;font-size:10px;font-family:Space Mono,monospace">⚡ GENZ</span>' if poll.get("genz_mode") else ""
            st.markdown(f"""
<div class="approved-card">
  <span class="tag" style="background:{cat_color}22;color:{cat_color};border:1px solid {cat_color}44">{cat.upper()}</span>
  {vibe_html}{genz_badge}
  <span style="font-size:10px;color:#10b981;margin-left:8px;font-family:Space Mono,monospace">
    ● APPROVED {poll.get("approved_at","")[:10]}
  </span>
  <div style="margin-top:10px;font-weight:600;font-size:14px">{poll.get("question","")}</div>
  <div style="font-size:11px;color:#555;margin-top:5px;font-family:Space Mono,monospace">
    📅 {poll.get("deadline","?")} &nbsp;·&nbsp; ⚡ {poll.get("token_pool",0):,} tokens &nbsp;·&nbsp; 🔥 {poll.get("controversy_score","?")}/10
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🗑️ Clear All Approved"):
            st.session_state.approved_polls = []
            add_log("Cleared approved polls list")
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — LOGS
# ═════════════════════════════════════════════════════════════════════════════
with tab_logs:
    st.markdown('<div class="section-label">ACTIVITY LOG</div>', unsafe_allow_html=True)
    if not st.session_state.activity_log:
        st.markdown('<div style="color:#444;font-family:Space Mono,monospace;font-size:12px">No activity yet.</div>', unsafe_allow_html=True)
    else:
        for i, entry in enumerate(st.session_state.activity_log):
            cls = "recent" if i == 0 else ""
            st.markdown(f'<div class="log-entry {cls}">{entry}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Clear Log"):
        st.session_state.activity_log = []
        st.rerun()
