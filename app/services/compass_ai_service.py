"""Compass AI: a lightweight contextual assistant.

Two capabilities, both scoped to "what the user is currently learning"
(a course/module title + short description passed in by the client as `context`):

1. get_quick_suggestions(context) -> 3 short candidate questions the learner
   could tap instead of typing (shown above the chat input, before they've
   typed anything).
2. answer_question(context, question) -> a short (<= ~60 words) grounded
   answer to whatever the learner actually asked.

Both go through the same LiteLLM/Gemini wrapper used by the quiz pipeline
(`app/services/llm_client.py`), so no second LLM integration is introduced.
If the LLM call fails (e.g. GEMINI_API_KEY not set), callers get a clear,
honest fallback message instead of a fabricated answer.
"""
from typing import List
import litellm

from app.config import get_settings
from app.services.llm_client import complete_json

settings = get_settings()

MAX_ANSWER_WORDS = 60

SUGGEST_SYSTEM_PROMPT = """You generate short quick-reply suggestions for a learning assistant
called Compass AI, used by MoSPI (Indian government statistics) officials while they study a
course module. Given the current module context, respond with ONLY a JSON object of the form
{"suggestions": ["...", "...", "..."]} containing exactly 3 short (under 8 words each) candidate
questions a learner on this exact module would plausibly want to ask. No prose, no markdown fences."""

ASK_SYSTEM_PROMPT = f"""You are Compass AI, a contextual learning assistant embedded in a course
page for MoSPI (Indian government statistics) officials on the iGOT Karmayogi platform. Answer the
learner's question using ONLY the module context given to you. Keep the answer short and direct —
strictly under {MAX_ANSWER_WORDS} words, no filler, no restating the question, plain text only
(no markdown headers or bullet lists unless truly necessary)."""


def get_quick_suggestions(context: str) -> List[str]:
    try:
        result = complete_json(SUGGEST_SYSTEM_PROMPT, f"Current module: {context}", max_tokens=200)
        suggestions = result.get("suggestions") if isinstance(result, dict) else None
        if isinstance(suggestions, list) and suggestions:
            return [str(s).strip() for s in suggestions[:3] if str(s).strip()]
    except Exception:
        pass
    # Fallback: generic, still module-aware, no LLM required.
    return [
        f"Give me a quick summary of {context}",
        "What's a common mistake here?",
        "Quiz me on this",
    ]


def answer_question(context: str, question: str) -> str:
    if not settings.GEMINI_API_KEY:
        return (
            "Compass AI isn't fully set up yet — add a GEMINI_API_KEY in your .env to enable "
            "live answers. For now: try rereading the module content above, or ask your "
            "facilitator."
        )
    try:
        response = litellm.completion(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": ASK_SYSTEM_PROMPT},
                {"role": "user", "content": f"Module context: {context}\n\nLearner question: {question}"},
            ],
            max_tokens=180,
            temperature=0.4,
        )
        text = response["choices"][0]["message"]["content"].strip()
        return text or "I couldn't generate an answer for that just now — try rephrasing your question."
    except Exception as e:
        return f"Compass AI couldn't reach the model just now ({type(e).__name__}). Please try again in a moment."
