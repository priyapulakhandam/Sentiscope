import os
import re
import joblib
from typing import Dict, Any

# =============================================================================
# 🔹 PATHS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.join(BASE_DIR, "..", "ml")

# =============================================================================
# 🔹 LOAD MODELS (SAFE)
# =============================================================================

business_model = None
business_vectorizer = None
complaint_model = None
complaint_vectorizer = None

try:
    business_model = joblib.load(os.path.join(ML_DIR, "tone_model.pkl"))
    business_vectorizer = joblib.load(os.path.join(ML_DIR, "vectorizer.pkl"))
except Exception as e:
    print("⚠️ Business model load failed:", e)

try:
    complaint_model = joblib.load(os.path.join(ML_DIR, "complaint_tone_model.pkl"))
    complaint_vectorizer = joblib.load(os.path.join(ML_DIR, "complaint_vectorizer.pkl"))
except Exception as e:
    print("⚠️ Complaint model load failed:", e)

# =============================================================================
# 🔹 RULE-BASED SAFETY NET (KEEP THIS)
# =============================================================================

ACCUSATORY_PATTERNS = [
    r"\bwhy\s+(haven't|have not|didn't|did not)\s+you\b",
    r"\bthis\s+is\s+unacceptable\b",
    r"\byou\s+should\s+have\b",
    r"\bwhy\s+wasn't\b",
    r"\bwhy\s+isn't\b",
]

COMMANDING_PATTERNS = [
    r"\bsend\s+(this|it)\s+now\b",
    r"\bdo\s+this\s+immediately\b",
]

POLITE_MARKERS = {
    "please", "could you", "would you", "kindly",
    "thank you", "thanks", "appreciate", "grateful"
}

APOLOGY_MARKERS = {
    "sorry", "apologize", "apologies", "regret"
}

URGENT_WORDS = {
    "urgent", "asap", "immediately", "deadline"
}

NEGATIVE_KEYWORDS = {
    "unacceptable", "disappointed", "failure",
    "problem", "issue", "delay", "no response"
}

# =============================================================================
# 🔹 RULE ANALYSIS
# =============================================================================

def rule_based_tone(text: str) -> Dict[str, Any]:
    t = text.lower()

    has_accusatory = any(re.search(p, t) for p in ACCUSATORY_PATTERNS)
    has_commanding = any(re.search(p, t) for p in COMMANDING_PATTERNS)
    has_polite = any(p in t for p in POLITE_MARKERS)
    has_apology = any(p in t for p in APOLOGY_MARKERS)
    has_urgent = any(p in t for p in URGENT_WORDS)
    has_negative = any(p in t for p in NEGATIVE_KEYWORDS)

    if has_accusatory:
        label = "harsh"
        reason = "contains accusatory language"
    elif has_negative and not has_polite:
        label = "harsh"
        reason = "negative wording without softening"
    elif has_commanding and not has_polite:
        label = "firm"
        reason = "commanding language"
    elif has_polite or has_apology:
        label = "polite"
        reason = "polite or apologetic phrasing"
    else:
        label = "neutral"
        reason = "factual language"

    style_tags = []
    if has_accusatory: style_tags.append("accusatory")
    if has_commanding: style_tags.append("commanding")
    if has_polite: style_tags.append("polite")
    if has_apology: style_tags.append("apologetic")
    if has_urgent: style_tags.append("urgent")

    return {
        "label": label,
        "confidence": 0.7,
        "style_tags": style_tags,
        "explanation": f"Tone classified as {label} because it {reason}."
    }

# =============================================================================
# 🔹 EMAIL TYPE ROUTER
# =============================================================================

def is_customer_support_email(text: str) -> bool:
    t = text.lower()
    keywords = [
        "support", "help", "issue", "problem", "error",
        "not working", "failed", "urgent", "asap",
        "delay", "no response", "complaint"
    ]
    return any(k in t for k in keywords)

# =============================================================================
# 🔹 SAFE ML HELPERS
# =============================================================================

def safe_ml_predict(model, vectorizer, text):
    if model is None or vectorizer is None:
        return None, 0.0

    try:
        X = vectorizer.transform([text])
        pred = model.predict(X)[0]
        prob = max(model.predict_proba(X)[0])
        return pred, round(float(prob), 2)
    except Exception as e:
        print("⚠️ ML prediction failed:", e)
        return None, 0.0

# =============================================================================
# 🔹 FINAL ANALYSIS PIPELINE
# =============================================================================

def analyze_tone(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            "label": "neutral",
            "confidence": 0.0,
            "style_tags": [],
            "explanation": "No text provided.",
            "needs_rewrite": False,
            "recommended_tone": {
                "name": "Neutral",
                "emoji": "😐",
                "note": "Add content to analyze."
            }
        }

    # 1️⃣ RULES FIRST (SAFETY)
    rule = rule_based_tone(text)
    rule_label = rule["label"]

    # 2️⃣ ROUTE EMAIL TYPE
    is_complaint = is_customer_support_email(text)

    # 3️⃣ ML (SAFE)
    if is_complaint:
        ml_label, ml_conf = safe_ml_predict(
            complaint_model, complaint_vectorizer, text
        )
        model_used = "customer_support"
    else:
        ml_label, ml_conf = safe_ml_predict(
            business_model, business_vectorizer, text
        )
        model_used = "business_email"

    # 4️⃣ DECISION LOGIC
    final_label = ml_label or rule_label

    if rule_label == "harsh":
        final_label = "harsh"
    elif rule_label == "polite" and final_label == "neutral":
        final_label = "polite"

    if final_label == "firm":
        final_label = "neutral"

    confidence = max(ml_conf, rule["confidence"])
    needs_rewrite = final_label == "harsh"

    recommended = (
        {
            "name": "Professional & Polite",
            "emoji": "😊🙏",
            "note": "Rewrite to remove blame and sound respectful."
        }
        if needs_rewrite
        else {
            "name": final_label.capitalize(),
            "emoji": "✓",
            "note": "Tone is appropriate."
        }
    )

    return {
        "label": final_label,
        "confidence": round(confidence, 2),
        "style_tags": rule["style_tags"],
        "explanation": rule["explanation"],
        "needs_rewrite": needs_rewrite,
        "recommended_tone": recommended,
        "model_used": model_used
    }
