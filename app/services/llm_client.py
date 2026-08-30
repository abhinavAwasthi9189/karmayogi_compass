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
            temperature=0.4,
        )
        raw = response["choices"][0]["message"]["content"]
        try:
            return json.loads(_strip_code_fences(raw))
        except json.JSONDecodeError as e:
            last_error = e
            continue
    raise ValueError(f"LLM did not return valid JSON after retries: {last_error}")
