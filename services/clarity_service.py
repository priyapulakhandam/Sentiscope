import re
from typing import Dict, Any, List
import textstat
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# ==============================
# 🔹 CONFIG
# ==============================

VAGUE_WORDS = {
    "things", "stuff", "something", "somehow", "various",
    "etc", "maybe", "kind of", "sort of", "a bit"
}

CALL_TO_ACTION_VERBS = {
    "please", "request", "need", "require", "could you",
    "send", "provide", "update", "confirm", "fix"
}

PASSIVE_PATTERNS = [
    r"\bwas\s+\w+ed\b",
    r"\bwere\s+\w+ed\b",
    r"\bis\s+\w+ed\b",
    r"\bhas\s+been\s+\w+ed\b",
]

# ==============================
# 🔹 UTILS
# ==============================

def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]

# ==============================
# 🔹 MAIN ANALYZER
# ==============================

def analyze_clarity(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            "clarity_score": 0,
            "issues": ["No text provided"],
            "summary": "No content to analyze."
        }

    issues = []
    sentences = split_sentences(text)
    sentence_count = len(sentences)
    word_count = len(text.split())

    # ---------- Sentence length ----------
    long_sentences = [s for s in sentences if len(s.split()) > 25]
    if long_sentences:
        issues.append("Some sentences are too long and hard to follow.")

    # ---------- Paragraph length ----------
    if word_count > 180:
        issues.append("Message is too long. Consider shortening it.")

    # ---------- Readability ----------
    try:
        readability = textstat.flesch_reading_ease(text)
    except:
        readability = 50  # fallback

    if readability < 50:
        issues.append("Text is difficult to read. Use simpler sentences.")

    # ---------- Vague language ----------
    vague_hits = [w for w in VAGUE_WORDS if w in text.lower()]
    if vague_hits:
        issues.append("Vague wording detected. Be more specific.")

    # ---------- Passive voice ----------
    passive_hits = any(
        re.search(p, text.lower()) for p in PASSIVE_PATTERNS
    )
    if passive_hits:
        issues.append("Passive voice reduces clarity. Use active voice.")

    # ---------- Call to action ----------
    if not any(v in text.lower() for v in CALL_TO_ACTION_VERBS):
        issues.append("No clear action or request stated.")

    # ==============================
    # 🔹 CLARITY SCORE (0–100)
    # ==============================

    score = 100

    score -= len(long_sentences) * 5
    score -= max(0, (word_count - 150) // 20) * 5
    score -= max(0, (50 - readability))
    score -= len(vague_hits) * 5
    # 1. Make passive less punitive (it's normal in business)
    if passive_hits:
        score -= 5          # instead of 10
        issues.append("Passive voice detected. Consider active voice where possible (optional).")

    # 2. Soften length penalty – many good emails are 200+ words
    if word_count > 250:    # raise threshold
        issues.append("Message is quite long. Consider breaking into bullet points.")
        score -= max(0, (word_count - 200) // 30) * 5   # gentler curve

    # 3. Add bonus for good readability
    if readability >= 65:
        score += 5
        score = min(100, score)

    # 4. Improve vague detection – only penalize if >1 or very strong ones
    if len(vague_hits) >= 2 or "things" in vague_hits or "stuff" in vague_hits:
        issues.append("Vague wording detected. Be more specific.")
        score -= len(vague_hits) * 4   # lighter penalty

    # 5. Short aggressive messages (new rule)
    if word_count < 10 and not any(v in text.lower() for v in ["please", "could", "would"]):
        issues.append("Message too short and abrupt.")
        score -= 25
    score = max(0, min(100, int(score)))

    return {
        "clarity_score": score,
        "issues": issues,
        "summary": (
            "Clear and easy to understand."
            if score >= 75
            else "Message could be clearer."
        )
    }
