"""Compass AI: a lightweight contextual assistant.

Two capabilities, both scoped to "what the user is currently learning"
(a course/module title + short description passed in by the client as `context`):

1. get_quick_suggestions(context) -> 3 short candidate questions the learner
   could tap instead of typing (shown above the chat input, before they've
   typed anything).
2. answer_question(context, question) -> a short (<= ~40 words) answer to
   whatever the learner actually asked, grounded ONLY in the module content
   passed in as `context` (the real study_material for the module the
   learner has open -- see learning.js). If the content doesn't cover the
   question, the model says so honestly instead of inventing an answer.

Both go through the same LiteLLM/Gemini wrapper used by the quiz pipeline
(`app/services/llm_client.py`), so no second LLM integration is introduced.
If the LLM call fails (e.g. GEMINI_API_KEY not set), callers get a clear,
honest fallback message instead of a fabricated answer.
"""
import logging
from typing import List, Optional

import litellm

from app.config import get_settings
from app.services.llm_client import complete_json, sampling_kwargs, describe_llm_error, extract_text
from app.services.privacy import scrub

settings = get_settings()
logger = logging.getLogger(__name__)

MAX_ANSWER_WORDS = 40
MAX_HISTORY_TURNS = 6  # keeps the prompt small while still allowing follow-up questions

SUGGEST_SYSTEM_PROMPT = """You generate short quick-reply suggestions for a learning assistant
called Compass AI, used by MoSPI (Indian government statistics) officials while they study a
course module. Given the current module context, respond with ONLY a JSON object of the form
{"suggestions": ["...", "...", "..."]} containing exactly 3 short (under 8 words each) candidate
questions a learner on this exact module would plausibly want to ask. No prose, no markdown fences."""

ASK_SYSTEM_PROMPT = f"""You are Compass AI, a contextual learning assistant embedded in a course
page for MoSPI (Indian government statistics) officials on the iGOT Karmayogi platform. You will be
given the study material for the module the learner is currently on, and what they just asked.
Answer using ONLY the module content provided below as context. If that content does not cover what
they're asking, say so briefly in one sentence and suggest they check the next module or ask their
trainer -- do not fill the gap with outside knowledge.
Keep the answer very short and direct — strictly under {MAX_ANSWER_WORDS} words, no filler, no
restating the question, plain text only (no markdown headers or bullet lists unless truly necessary).
"""


def get_quick_suggestions(context: str) -> List[str]:
    try:
        result = complete_json(SUGGEST_SYSTEM_PROMPT, f"Current module: {context}", max_tokens=400)
        suggestions = result.get("suggestions") if isinstance(result, dict) else None
        if isinstance(suggestions, list) and suggestions:
            return [str(s).strip() for s in suggestions[:3] if str(s).strip()]
    except Exception as e:
        # Logged rather than swallowed: the chips degrade gracefully, so without this a
        # misconfigured model looks like "it works" until /ask fails too.
        logger.warning("Compass AI suggestions fell back to defaults - %s", describe_llm_error(e))
    # Fallback: generic, still module-aware, no LLM required.
    return [
        f"Give me a quick summary of {context}",
        "What's a common mistake here?",
        "Quiz me on this",
    ]


def answer_question(context: str, question: str, history: Optional[List[str]] = None) -> str:
    if not settings.GEMINI_API_KEY:
        return (
            "Compass AI isn't fully set up yet — add a GEMINI_API_KEY in your .env to enable "
            "live answers. For now: try rereading the module content above, or ask your "
            "facilitator."
        )
    try:
        # Scrub obvious PII before anything reaches the third-party LLM call.
        context = scrub(context)
        question = scrub(question)
        messages = [{"role": "system", "content": ASK_SYSTEM_PROMPT}]
        # `history` is a flat alternating list of prior turns (user, assistant, user, ...)
        # so follow-ups like "what about the second one?" resolve instead of losing context.
        trimmed = list(history or [])
        if len(trimmed) > MAX_HISTORY_TURNS:
            # trim on an even boundary so the window still opens on a user turn
            trimmed = trimmed[-(MAX_HISTORY_TURNS - MAX_HISTORY_TURNS % 2):]
        for index, turn in enumerate(trimmed):
            messages.append({"role": "user" if index % 2 == 0 else "assistant", "content": scrub(str(turn))})
        messages.append(
            {"role": "user", "content": f"We are teaching: {context}\n\nThe learner asked: {question}"}
        )
        response = litellm.completion(
            model=settings.LLM_MODEL,
            messages=messages,
            # 40 words of visible answer is small, but on Gemini 3.x the thinking
            # budget is drawn from this same number (see sampling_kwargs) — give it
            # headroom even with reasoning turned down, rather than tuning this to
            # the bare minimum for the old non-reasoning 2.x models.
            max_tokens=500,
            **sampling_kwargs(),
        )
        text = extract_text(response)
        return text or "I couldn't generate an answer for that just now — try rephrasing your question."
    except Exception as e:
        return f"Compass AI couldn't answer that — {describe_llm_error(e)}"
