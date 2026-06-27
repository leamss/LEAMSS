"""Sweep B.4.1 — Perplexity Sonar Pro tertiary fallback for AI workflow generation.

Adds a 3rd-tier fallback after Claude Sonnet 4.5 + Claude Haiku 4.5 fail/timeout.
Sonar Pro provides web-search-augmented responses — fresher fee tables, current
policy info, and inline citations. Reads `PERPLEXITY_API_KEY` from env; if not
set, gracefully skips with a structured "not configured" signal.

Per Sir's dispatch (Feb 27, 2026 B.4.1).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


def is_perplexity_configured() -> bool:
    """Returns True if PERPLEXITY_API_KEY is set in env."""
    return bool(os.environ.get("PERPLEXITY_API_KEY", "").strip())


async def call_perplexity_sonar_pro(
    prompt: str,
    system_msg: str = "",
    timeout_seconds: float = 60.0,
) -> Tuple[str, str]:
    """Call Perplexity Sonar Pro for live web-search-augmented response.

    Returns:
        (response_text, model_label) on success.

    Raises:
        RuntimeError if PERPLEXITY_API_KEY missing (caller should treat as skip).
        Exception on API errors / timeout / network — caller logs + tries next layer.

    Notes:
        - Uses OpenAI-compatible AsyncOpenAI client pointed at perplexity.ai
        - Citations are emitted as Sonar's `citations` field; we append them to
          the response text so downstream JSON parser sees them as evidence.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not configured — skipping Perplexity layer")

    # Import here to avoid forcing openai client init at module load
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PERPLEXITY_BASE_URL,
        timeout=timeout_seconds,
    )

    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=PERPLEXITY_MODEL,
                messages=messages,
                stream=False,
            ),
            timeout=timeout_seconds,
        )
    finally:
        await client.close()

    text = response.choices[0].message.content or ""

    # Surface citations if Perplexity returned them
    citations = getattr(response, "citations", None) or []
    if citations:
        cite_block = "\n\n_Sources (Perplexity web search):_\n" + "\n".join(
            f"- {c}" for c in citations[:10]
        )
        text = text + cite_block

    label = f"perplexity/{PERPLEXITY_MODEL}"
    logger.info(
        "Perplexity Sonar Pro succeeded · tokens=%s · citations=%d",
        getattr(response.usage, "total_tokens", "?"),
        len(citations),
    )
    return text, label
