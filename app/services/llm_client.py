"""Thin wrapper around LiteLLM so the rest of the app talks to Gemini
behind a single call."""
import json
import os
import re
from typing import Any

import litellm
from app.config import get_settings

settings = get_settings()
os.environ.setdefault("GEMINI_API_KEY", settings.GEMINI_API_KEY)


def sampling_kwargs(temperature: float = 0.4, reasoning_effort: str = "none") -> dict:
    """Sampling/reasoning params to pass to litellm for the configured model.

    Two Gemini-3-specific gotchas this works around:

    1. `temperature`/`top_p`/`top_k` are deprecated on 3.x — sending them is at best
       ignored and at worst rejected, so they're only included for older families.
    2. Gemini 3.x models "think" before answering, and — despite Google's docs
       implying otherwise — thinking tokens are drawn from the *same* max_tokens
       budget as the visible answer, defaulting to a High thinking level. With a
       small max_tokens (fine for a short chat answer on 2.5-era models), thinking
       alone can eat the whole budget, leaving a truncated reply or, worse, an
       empty one. LiteLLM maps `reasoning_effort` to Gemini's `thinking_level` for
       3.x models, so passing "none" here keeps that budget for the answer.
       Callers that want full reasoning (e.g. a hard multi-step task) can pass
       reasoning_effort="high" explicitly.
    """
    model = settings.LLM_MODEL.split("/")[-1]
    is_gemini_3_plus = model.startswith("gemini-3") or model.startswith("gemini-4")
    kwargs: dict = {} if is_gemini_3_plus else {"temperature": temperature}
    if is_gemini_3_plus and reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    return kwargs


def describe_llm_error(exc: Exception) -> str:
    """A short, actionable one-liner for an LLM call failure.

    A bare exception class name (e.g. "NotFoundError") tells the user nothing about
    *why*, and 404s from Gemini are almost always a retired/renamed model rather
    than a transient outage — so surface the model string and the provider message.
    """
    detail = str(exc).strip()
    if len(detail) > 220:
        detail = detail[:220] + "…"
    if isinstance(exc, litellm.NotFoundError) or "404" in detail or "not found" in detail.lower():
        return (
            f"the configured model '{settings.LLM_MODEL}' was rejected by the provider. "
            f"It has most likely been retired or renamed — set LLM_MODEL in .env to a current "
            f"model. Provider said: {detail}"
        )
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def extract_text(response) -> str:
    """Pulls the visible answer text out of a litellm response, never returning None.

    On Gemini 3.x, if reasoning consumes the entire token budget (or a caller
    forgot to cap reasoning_effort), `message.content` can come back None with
    finish_reason "length" instead of an empty string — calling .strip() on that
    directly is what produces a bare "NoneType has no attribute 'strip'" error.
    """
    message = response["choices"][0]["message"]
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if content:
        return content.strip()
    finish_reason = response["choices"][0].get("finish_reason") if isinstance(response["choices"][0], dict) \
        else getattr(response["choices"][0], "finish_reason", None)
    if finish_reason == "length":
        raise RuntimeError(
            "the model used its whole token budget on internal reasoning and returned no "
            "visible answer. Retry, or set LLM_MODEL to a model with lighter default reasoning."
        )
    return ""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def complete_json(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> Any:
    """Calls the configured LLM and parses a strict-JSON response, retrying once on parse failure."""
    last_error = None
    for attempt in range(2):
        response = litellm.completion(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt if attempt == 0 else
                 user_prompt + "\n\nSTRICT REMINDER: Respond with ONLY valid JSON, no prose, no markdown fences."},
            ],
            max_tokens=max_tokens,
            **sampling_kwargs(),
        )
        try:
            raw = extract_text(response)
            return json.loads(_strip_code_fences(raw))
        except (json.JSONDecodeError, RuntimeError) as e:
            last_error = e
            continue
    raise ValueError(f"LLM did not return valid JSON after retries: {last_error}")
