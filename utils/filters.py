"""
Political content filter — removes lines containing political keywords
before sending to the LLM, so it doesn't generate political polls.
"""
import re

# Keywords that flag overtly political content
# NOTE: Kept tight — we want to allow social/cultural controversy but block party politics
POLITICAL_KEYWORDS = [
    # Parties
    "bjp", "congress", "aap", "bsp", "tmc", "ncp", "rjd", "jdu", "shiv sena",
    "ysrcp", "tdp", "dmk", "aiadmk", "brs", "telangana rashtra",
    # Politicians
    "modi", "rahul gandhi", "kejriwal", "mamata", "yogi adityanath",
    "chief minister", "prime minister",
    "lok sabha", "rajya sabha", "parliament",
    "member of parliament", "mla",
    # Electoral
    "election", "ballot", "exit poll", "manifesto", "constituency",
    "government policy", "budget 20", "gst rate", "income tax slab",
    # Sensitive geopolitical
    "article 370", "citizenship amendment", "uniform civil code",
    "reservation quota",
]

# NOTE: We intentionally do NOT filter:
# - "cm " (could be centimetres), "pm " (could be evening time), "mp " (could be megapixels)
# - Kashmir (can appear in non-political travel/culture context)
# - "minister" alone (too broad — blocks business/entertainment content)
# - Caste system (important social issue GenZ discusses)
# - "sc st" — too broad, blocks legitimate social discussion

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in POLITICAL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def filter_political_content(text: str) -> str:
    """
    Filter out lines from the context that contain political keywords.
    Returns cleaned text safe to send to LLM for non-political poll generation.
    """
    lines = text.split("\n")
    clean_lines = []
    removed = 0

    for line in lines:
        if _PATTERN.search(line):
            removed += 1
        else:
            clean_lines.append(line)

    result = "\n".join(clean_lines)

    if removed > 0:
        result += f"\n\n[Note: {removed} politically-sensitive items were filtered out. Generate polls only on non-political topics from above.]"

    return result


def is_political(text: str) -> bool:
    """Check if a single string contains political content."""
    return bool(_PATTERN.search(text))
