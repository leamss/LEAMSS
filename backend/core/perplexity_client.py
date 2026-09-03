"""Shared Perplexity AI client for LEAMSS.

Centralizes all Perplexity API calls with:
  - SSL verification disabled (fixes CERTIFICATE_VERIFY_FAILED on Windows)
  - Automatic retry on transient errors
  - Proper async client lifecycle management
  - Fallback from sonar-pro to sonar model

Usage:
    from core.perplexity_client import call_perplexity

    result = await call_perplexity(
        prompt="Extract this resume...",
        system_msg="You are a resume parser...",
        model="sonar-pro",
        max_tokens=4000,
    )
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Tuple

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
DEFAULT_MODEL = "sonar-pro"
FALLBACK_MODEL = "sonar"


def _get_api_key() -> str:
    """Read PERPLEXITY_API_KEY from environment."""
    return os.environ.get("PERPLEXITY_API_KEY", "").strip()


def _make_client(timeout: float = 60.0) -> AsyncOpenAI:
    """Create an AsyncOpenAI client pointed at Perplexity with SSL verify disabled."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not configured")

    http_client = httpx.AsyncClient(verify=False, timeout=timeout)
    return AsyncOpenAI(
        api_key=api_key,
        base_url=PERPLEXITY_BASE_URL,
        http_client=http_client,
    )


async def call_perplexity(
    prompt: str,
    system_msg: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4000,
    temperature: float = 0.2,
    timeout: float = 90.0,
) -> Tuple[str, str]:
    """Call Perplexity API with automatic fallback and retry.

    Returns: (response_text, model_used)
    Raises: RuntimeError if all attempts fail.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not configured — set it in backend/.env")

    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    # Perplexity requires max_tokens >= 16
    max_tokens = max(max_tokens, 16)

    models_to_try = [model]
    if model != FALLBACK_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    last_err: Optional[Exception] = None

    for m in models_to_try:
        client = _make_client(timeout=timeout)
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                ),
                timeout=timeout,
            )

            text = response.choices[0].message.content or ""

            # Surface Perplexity citations if available
            citations = getattr(response, "citations", None) or []
            if citations:
                cite_block = "\n\n_Sources (Perplexity web search):_\n" + "\n".join(
                    f"- {c}" for c in citations[:10]
                )
                text = text + cite_block

            label = f"perplexity/{m}"
            logger.info(
                "Perplexity %s succeeded - tokens=%s",
                m,
                getattr(response.usage, "total_tokens", "?"),
            )
            return text, label

        except asyncio.TimeoutError:
            last_err = TimeoutError(f"Perplexity {m} timed out after {timeout}s")
            logger.warning("Perplexity %s timed out after %ss — trying next", m, timeout)
            continue
        except Exception as e:
            last_err = e
            logger.warning("Perplexity %s failed: %s — trying next", m, e)
            continue
        finally:
            await client.close()

    raise RuntimeError(f"All Perplexity models failed. Last error: {type(last_err).__name__}: {last_err}")


def is_configured() -> bool:
    """Returns True if PERPLEXITY_API_KEY is set in env."""
    return bool(_get_api_key())
