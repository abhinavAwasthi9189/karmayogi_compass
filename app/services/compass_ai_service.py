"""Compass AI: a lightweight contextual assistant.

Two capabilities, both scoped to "what the user is currently learning"
(a course/module title + short description passed in by the client as `context`):

1. get_quick_suggestions(context) -> 3 short candidate questions the learner
   could tap instead of typing (shown above the chat input, before they've
   typed anything).
2. answer_question(context, question) -> a short (<= ~40 words) answer to
   whatever the learner actually asked, using Gemini's own knowledge. The
   `context` tells the model what topic is being taught -- it is NOT a hard
   boundary the model must stay inside, so it doesn't hedge or refuse just
   because the passed-in description is brief.

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

MAX_ANSWER_WORDS = 40

SUGGEST_SYSTEM_PROMPT = """You generate short quick-reply suggestions for a learning assistant
called Compass AI, used by MoSPI (Indian government statistics) officials while they study a
course module. Given the current module context, respond with ONLY a JSON object of the form
{"suggestions": ["...", "...", "..."]} containing exactly 3 short (under 8 words each) candidate
questions a learner on this exact module would plausibly want to ask. No prose, no markdown fences."""

ASK_SYSTEM_PROMPT = f"""You are Compass AI, a contextual learning assistant embedded in a course
page for MoSPI (Indian government statistics) officials on the iGOT Karmayogi platform. You will be
told what topic/module the learner is currently studying, and what they just asked. Answer the
question properly and correctly using your own general knowledge — the module topic is background
to tell you what they're learning, not a restriction on what you're allowed to say. Never say things
like "the context doesn't specify" or refuse to answer because the topic description was brief;
just answer the question well, the way a good tutor would.
Keep the answer very short and direct — strictly under {MAX_ANSWER_WORDS} words, no filler, no
restating the question, plain text only (no markdown headers or bullet lists unless truly necessary)."""


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
                {"role": "user", "content": f"We are teaching: {context}\n\nThe learner asked: {question}"},
            ],
            max_tokens=120,
            temperature=0.4,
        )
        text = response["choices"][0]["message"]["content"].strip()
        return text or "I couldn't generate an answer for that just now — try rephrasing your question."
    except Exception as e:
        return f"Compass AI couldn't reach the model just now ({type(e).__name__}). Please try again in a moment."
