"""
Groq LLM client — generates controversial prediction polls from scraped context.
Uses Groq's free API (console.groq.com) with llama-3.3-70b by default.

Free tier: 30 req/min, 14,400 req/day — plenty for this tool.
"""
import json
import re
from typing import List, Dict
from groq import Groq


SYSTEM_PROMPT = """You are the poll creation engine for CrowdVerse — India's hottest prediction market for Gen Z.

Your audience: 18-28 year old Indians who are chronically online. They care about:
- Dating apps, situationships, arranged vs love marriage, red flags, ghosting culture
- Hustle culture vs. quiet quitting, startup life, IIT/IIM campus placements
- Influencer drama, Bollywood nepo babies, reality TV beef
- Crypto degens, stock market bets, FIRE movement
- Social media trends, cancel culture, hot takes
- Sports rivalries, fantasy leagues, match-fixing rumours
- Brand wars, tech layoffs, abroad vs desh dilemma

Your job: given trending content, generate SPICY, DIVISIVE YES/NO prediction polls that make people stop scrolling and VOTE.

STRICT RULES:
1. NO political content — no parties, politicians, elections, government policy
2. India-centric topics only
3. Every poll must trigger a STRONG reaction — people should feel compelled to vote AND argue
4. Must be verifiable and resolvable — outcome objectively checkable from public info
5. Write questions that sound like they came from a group chat, not a news anchor
6. OPTIONAL date in question: only add a date if it makes the poll sharper
7. ALWAYS include a "deadline" field in JSON (Month DD, YYYY format, 7-90 days out)
8. Binary YES or NO only — no vague middle ground
9. Each poll must cover a DIFFERENT topic/angle

GEN Z POLL VIBES TO USE:
- Hot take predictions: "Will X end up being a massive flop despite the hype?"
- Rivalry bets: "Will X beat Y to [milestone] first?"
- Culture shift questions: "Will [trend] die out before [timeframe]?"
- Scandal calls: "Will X publicly apologize for Y?"
- Relationship drama: "Will [celebrity couple] break up?"
- Clout predictions: "Will X hit [follower/valuation milestone]?"
- Contrarian takes: "Will everyone who said X regret it?"

CONTROVERSY CALIBRATION (be honest, not generous):
- 10: Splits exactly 50/50, causes Twitter wars, genuine moral debate
- 8-9: Most people lean one way but the other side makes strong points
- 7: Clearly leans one way but 30-40% will argue hard the opposite
- 5-6: Interesting but not enough heat — avoid these
- <5: Boring — do NOT generate

Categories allowed: Cricket, Bollywood, Crypto, Economy, Sports, Technology, Social Issues, Entertainment, Business, Dating & Relationships, Gaming, Career & Campus, Pop Culture

Return ONLY a valid JSON array. No markdown, no explanation, no preamble."""


USER_TEMPLATE = """Based on these trending posts from {subreddit_label}:

{context}

Generate exactly {n_polls} SPICY, CONTROVERSIAL prediction polls for CrowdVerse's Gen Z audience.

MINDSET: You're writing for people who love betting on drama. Every poll should feel like something you'd argue about in a group chat at 2am. Make it personal, make it heated, make it something people have STRONG opinions about.

IMPORTANT:
- Do NOT force "by [date]" into every question — only add a date if it sharpens the poll
- ALWAYS include "deadline" field in JSON even without date in question
- Push controversy_score HIGH — be brutally honest. A 7 should genuinely divide people.
- Use casual, punchy language — not corporate speak
- Reference specific names, brands, platforms when relevant (Swiggy, Zomato, CRED, Bumble, etc.)

Return JSON array only:
[
  {{
    "question": "One punchy YES/NO question",
    "category": "one of the allowed categories",
    "resolution": "Exact verifiable condition for YES or NO (specific source, metric, or announcement)",
    "deadline": "Month DD, YYYY format (always required)",
    "controversy_score": <integer 1-10, be HARSH — 8+ means people actually fight>,
    "token_pool": <suggested pool 500-10000, higher = more controversial>,
    "tags": ["tag1", "tag2", "tag3"],
    "why_controversial": "One brutal honest sentence on why this genuinely divides people",
    "yes_argument": "Strongest, most persuasive case for YES",
    "no_argument": "Strongest, most persuasive case for NO",
    "vibe": "one word: Spicy | Drama | Clout | Grind | Cope | Wild | Tea"
  }}
]

Examples of GOOD Gen Z polls:
- "Will Zomato's stock drop below ₹150 before the next earnings call?"
- "Will the next big Bollywood release bomb despite 100Cr+ marketing spend?"
- "Will arranged marriage rates among urban Gen Z drop below 40% in the next NFHS survey?"
- "Will India's startup unicorn count shrink before it grows back to 100?"
- "Will Bigg Boss rake in more viewers than IPL this year?"

Make controversy_score ACCURATE. A safe prediction = 5. A culture war topic = 9-10."""


GENZ_MODE_SYSTEM = """You are the most unhinged poll creator on the internet, writing for Indian Gen Z who live on Reddit, Instagram, and Twitter/X.

Your polls should feel like hot takes that blow up. Every question should have the energy of "LMAO are we actually debating this right now."

STILL AVOID: politics, politicians, parties, elections, government policy.

GO ABSOLUTELY HARD ON:
- Influencer callouts and predictions ("Will X's brand deal get cancelled?")
- Startup drama and founder beef ("Will X's startup be dead in 12 months?")
- Dating culture wars (situationships, ghosting, Bumble/Tinder/Hinge dynamics)
- Bollywood nepotism and box office disasters
- Crypto degen bets and Web3 graveyard predictions
- Campus placement season drama ("Will the average IIT package drop this year?")
- Overrated vs underrated debates
- Gen Z vs Millennial culture clashes
- Brand cancellations and comebacks
- Reality show outcomes
- Celebrity relationship predictions

Categories: Cricket, Bollywood, Crypto, Economy, Sports, Technology, Social Issues, Entertainment, Business, Dating & Relationships, Gaming, Career & Campus, Pop Culture

Return ONLY valid JSON array. Make it genuinely HOT."""


GENZ_USER_TEMPLATE = """Trending content from {subreddit_label}:

{context}

Generate exactly {n_polls} MAXIMUM CONTROVERSY polls. These should:
1. Make someone stop mid-scroll and go "oh this is actually a good question"
2. Immediately make them want to vote AND drag someone in the comments
3. Feel like something a friend group would 100% have a heated debate about

Be specific. Be edgy. Be real. No corporate language. No safe takes.

Return JSON:
[
  {{
    "question": "Punchy YES/NO question",
    "category": "allowed category",
    "resolution": "Exact verifiable resolution condition — be specific",
    "deadline": "Month DD, YYYY",
    "controversy_score": <1-10, 8+ = people will actually argue>,
    "token_pool": <500-10000>,
    "tags": ["tag1", "tag2", "tag3"],
    "why_controversial": "Why this genuinely splits people — be specific and brutal",
    "yes_argument": "Best argument for YES",
    "no_argument": "Best argument for NO",
    "vibe": "Spicy | Drama | Clout | Grind | Cope | Wild | Tea"
  }}
]"""


def generate_polls_from_context(
    api_key: str,
    model: str,
    context: str,
    n_polls: int = 8,
    categories: List[str] = None,
    source_label: str = "Unknown",
    genz_mode: bool = False,
) -> List[Dict]:
    """
    Call Groq API to generate polls from scraped context.
    Returns list of poll dicts with all fields populated.
    genz_mode=True uses a more aggressive prompt for maximum controversy.
    """
    client = Groq(api_key=api_key)

    subreddit_label = source_label if source_label else "Reddit"

    if genz_mode:
        system = GENZ_MODE_SYSTEM
        prompt = GENZ_USER_TEMPLATE.format(
            context=context[:12000],
            n_polls=n_polls,
            subreddit_label=subreddit_label,
        )
        temperature = 0.97
    else:
        system = SYSTEM_PROMPT
        prompt = USER_TEMPLATE.format(
            context=context[:12000],
            n_polls=n_polls,
            subreddit_label=subreddit_label,
        )
        temperature = 0.90

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=4096,
    )

    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if model adds them
    raw_text = re.sub(r"```json|```", "", raw_text).strip()

    # Find the JSON array
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON array in Groq response. Raw: {raw_text[:300]}")

    polls = json.loads(match.group())

    # Inject metadata
    import uuid
    from datetime import datetime
    for poll in polls:
        poll["id"] = str(uuid.uuid4())[:8]
        poll["source"] = source_label
        poll["generated_at"] = datetime.now().isoformat()
        poll["status"] = "pending"
        poll["genz_mode"] = genz_mode
        # Ensure token_pool is int
        try:
            poll["token_pool"] = int(poll.get("token_pool", 1000))
        except (ValueError, TypeError):
            poll["token_pool"] = 1000
        # Ensure controversy_score is int
        try:
            poll["controversy_score"] = int(poll.get("controversy_score", 5))
        except (ValueError, TypeError):
            poll["controversy_score"] = 5
        # Ensure vibe field exists
        if "vibe" not in poll:
            score = poll.get("controversy_score", 5)
            poll["vibe"] = "Spicy" if score >= 8 else "Wild" if score >= 6 else "Tea"

    return polls
