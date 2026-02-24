"""
Political content filter — removes lines containing political keywords
before sending to the LLM, so it doesn't generate political polls.
"""
import re

# Keywords that flag political content
POLITICAL_KEYWORDS = [
    # Parties
    "bjp", "congress", "aap", "bsp", "sp ", "tmc", "ncp", "rjd", "jdu", "shiv sena",
    "ysrcp", "tdp", "dmk", "aiadmk", "brs", "telangana rashtra",
    # Politicians (keep general)
    "modi", "rahul gandhi", "kejriwal", "mamata", "yogi", "cm ", "pm ", "mp ",
    "chief minister", "prime minister", "minister", "lok sabha", "rajya sabha",
    "parliament", "mla", "member of parliament",
    # Political events
    "election", "vote", "voting", "ballot", "constituency", "exit poll",
    "manifesto", "coalition", "government policy", "budget 20",
    "gst rate", "income tax slab",
    # Sensitive geopolitical
    "kashmir", "article 370", "ram mandir", "citizenship", "caa", "nrc",
    "uniform civil code", "ucc", "reservation quota", "obc", "sc st",
]

# Compiled regex for speed
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
