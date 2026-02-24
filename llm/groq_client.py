"""
Groq LLM client — generates controversial prediction polls from scraped context.
Uses Groq's free API (console.groq.com) with llama-3.3-70b by default.

Free tier: 30 req/min, 14,400 req/day — plenty for this tool.
"""
import json
import re
from typing import List, Dict
from groq import Groq


SYSTEM_PROMPT = """You are the poll creation engine for CrowdVerse — India's premier prediction market platform.

Your job: given trending Indian content, generate CONTROVERSIAL, specific, time-bound YES/NO prediction polls.

STRICT RULES:
1. NO political content — no parties, politicians, elections, government policy, ministers
2. India-centric topics only — relevant to Indian users
3. Polls must be genuinely controversial — reasonable people should disagree
4. Must be verifiable and resolvable — clear outcome by a specific date
5. Keep it binary YES or NO — no ambiguity in the resolution
6. Each poll must be DIFFERENT from the others in topic and angle

Categories allowed: Cricket, Bollywood, Crypto, Economy, Sports, Technology, Social Issues, Entertainment, Business

Return ONLY a valid JSON array. No markdown, no explanation, no preamble."""

USER_TEMPLATE = """Based on these trending posts from {subreddit_label}:

{context}

Generate exactly {n_polls} controversial prediction polls for CrowdVerse.

Return JSON array only:
[
  {{
    "question": "Will [specific thing] happen by [specific date]?",
    "category": "one of the allowed categories",
    "resolution": "Exact condition that resolves this YES or NO (be specific)",
    "deadline": "Month DD, YYYY format",
    "controversy_score": <integer 1-10 how divisive this is>,
    "token_pool": <suggested starting pool, integer between 500-10000>,
    "tags": ["tag1", "tag2", "tag3"],
    "why_controversial": "One sentence on why people genuinely disagree on this",
    "yes_argument": "Strongest case for YES outcome",
    "no_argument": "Strongest case for NO outcome"
  }}
]

Make sure controversy_score reflects actual divisiveness. IPL match winner = 7. Rohit Sharma retirement = 9."""


def generate_polls_from_context(
    api_key: str,
    model: str,
    context: str,
    n_polls: int = 8,
    categories: List[str] = None,
    source_label: str = "Unknown",
) -> List[Dict]:
    """
    Call Groq API to generate polls from scraped context.
    Returns list of poll dicts with all fields populated.
    """
    client = Groq(api_key=api_key)

    prompt = USER_TEMPLATE.format(
        context=context[:6000],  # Groq context window is large but we cap for speed
        n_polls=n_polls,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,  # Higher = more creative/diverse polls
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

    return polls
