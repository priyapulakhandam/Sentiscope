import os
import time
import logging
from typing import Dict, Optional, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================================================
# 🔑 ENV + LOGGING
# ============================================================
load_dotenv()
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Google SDK looks for GEMINI_API_KEY by default
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found. Set it in your .env file.")

# ============================================================
# 🔹 CLIENT CONFIG
# ============================================================
client = genai.Client(api_key=GEMINI_API_KEY)

# ✅ same model you used successfully
MODEL_NAME = "models/gemini-2.5-flash"

# ============================================================
# 🔹 RETRY LOGIC
# ============================================================
def generate_with_retry(
    prompt: str,
    system_instruction: str,
    retries: int = 5,
    base_delay: float = 2.0,
    temperature: float = 0.4,
    max_tokens: int = 300,
):
    """
    Retries on 503 (overload) and 429 (rate limit) using exponential backoff.
    """
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text.strip()

        except Exception as e:
            err = str(e).upper()
            is_transient = any(x in err for x in ["503", "OVERLOADED", "UNAVAILABLE", "429", "LIMIT"])

            if is_transient and attempt < retries:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"{MODEL_NAME} overloaded/rate-limited. Retry {attempt}/{retries} in {delay:.1f}s...")
                time.sleep(delay)
                continue

            raise  # real failure or last attempt

# ============================================================
# 🔹 MAIN REWRITE LOGIC
# ============================================================
def rewrite_text(
    text: str,
    tone: str = "polite",
    clarity_issues: Optional[List[str]] = None
) -> Dict:
    if not text or not text.strip():
        return {"rewritten_text": "", "success": False}

    # ✅ Tone mapping (kept, but aligned with same rewrite format)
    tone_map = {
        "harsh": "Professional and calm. Remove anger/blame.",
        "firm": "Professional and firm. Keep urgency. Do not soften too much.",
        "polite": "Professional and polite.",
        "neutral": "Professional and neutral."
    }
    tone_instruction = tone_map.get(tone, tone_map["polite"])

    # Optional clarity constraints
    clarity_instr = ""
    if clarity_issues:
        clarity_instr = "Also fix these clarity issues: " + ", ".join(clarity_issues) + "."

    # ✅ Same system behavior
    system_instruction = (
        "You are a senior business communication expert. "
        "Rewrite emails to be professional, polite, and concise. "
        "Use active voice and a clear call-to-action. "
        "Never add new facts or explanations. "
        "Return only the rewritten email."
    )

    # ✅ SAME PROMPT STYLE YOU TESTED (short, 2 lines, urgency preserved)
    user_prompt = f"""
Rewrite this message professionally.
Keep it under 2 lines.
Keep the urgency and firmness of the original message.
Do not make it too soft.
{clarity_instr}
Tone guidance: {tone_instruction}

Message: "{text}"
""".strip()

    try:
        rewritten = generate_with_retry(
            prompt=user_prompt,
            system_instruction=system_instruction,
            retries=5,
            base_delay=2.0,
            temperature=0.4,
            max_tokens=3000
        )

        return {
            "rewritten_text": rewritten,
            "success": True,
            "model": MODEL_NAME
        }

    except Exception as e:
        logger.error(f"Gemini Rewrite failed: {e}")
        return {
            "rewritten_text": "Error: Unable to process request.",
            "success": False,
            "model": MODEL_NAME
        }
