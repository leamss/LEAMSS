"""Phase 19.10 — Currency conversion service.

Converts AUD / NZD / CAD → INR for sales display.

Source priority:
  1. `currency_rates` Mongo collection (admin-editable, audited)
  2. Env vars (fallback) — AUD_INR_RATE, NZD_INR_RATE, CAD_INR_RATE
  3. Hardcoded sane defaults (last-resort)

In-memory cache TTL = 300s to avoid hot-path Mongo reads.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

CURRENCY_COLLECTION = "currency_rates"

# Sane defaults (Feb 2026 approximate rates)
_DEFAULTS = {
    "AUD_INR": 55.5,
    "NZD_INR": 51.0,
    "CAD_INR": 62.5,
}

# In-process cache: {pair: (expires_at, rate)}
_CACHE: Dict[str, tuple] = {}
_TTL_SECONDS = 300


def _env_rate(pair: str) -> float:
    env_key = f"{pair}_RATE"
    raw = os.environ.get(env_key)
    if raw:
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    return _DEFAULTS.get(pair, 0.0)


async def get_rate(db: AsyncIOMotorDatabase, pair: str) -> Dict[str, Any]:
    """Get FX rate for a currency pair (e.g. "AUD_INR")."""
    pair = pair.upper()
    now = time.time()
    cached = _CACHE.get(pair)
    if cached and cached[0] > now:
        return {"pair": pair, "rate": cached[1], "source": "cache"}

    # Check DB first
    doc = await db[CURRENCY_COLLECTION].find_one({"pair": pair})
    if doc and doc.get("rate"):
        rate = float(doc["rate"])
        _CACHE[pair] = (now + _TTL_SECONDS, rate)
        return {"pair": pair, "rate": rate, "source": "db",
                "last_updated": doc.get("last_updated"),
                "updated_by": doc.get("updated_by")}

    # Fallback to env
    rate = _env_rate(pair)
    _CACHE[pair] = (now + _TTL_SECONDS, rate)
    return {"pair": pair, "rate": rate, "source": "env_fallback"}


async def get_all_rates(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Return all 3 conversion rates with source attribution."""
    rates = {}
    for pair in ("AUD_INR", "NZD_INR", "CAD_INR"):
        rates[pair] = await get_rate(db, pair)
    return {
        "rates": rates,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def set_rate(
    db: AsyncIOMotorDatabase, pair: str, rate: float, user_id: str, user_name: str = "",
) -> Dict[str, Any]:
    """Admin: update FX rate. Returns previous + new for audit."""
    pair = pair.upper()
    if pair not in ("AUD_INR", "NZD_INR", "CAD_INR"):
        raise ValueError(f"Unsupported currency pair: {pair}")
    if rate <= 0 or rate > 1000:
        raise ValueError(f"Rate {rate} out of plausible range (0-1000)")

    existing = await db[CURRENCY_COLLECTION].find_one({"pair": pair})
    prev_rate = existing.get("rate") if existing else None

    now = datetime.now(timezone.utc)
    await db[CURRENCY_COLLECTION].update_one(
        {"pair": pair},
        {"$set": {
            "pair": pair, "rate": rate,
            "last_updated": now, "updated_by": user_id, "updated_by_name": user_name,
        }},
        upsert=True,
    )
    # Bust cache
    _CACHE.pop(pair, None)
    return {"pair": pair, "previous_rate": prev_rate, "new_rate": rate,
            "updated_at": now.isoformat()}


def convert(amount: Optional[float], pair_rate: float) -> Optional[int]:
    """Convert `amount` using `pair_rate` (e.g. AUD * 55.5 → INR).

    Returns rounded integer (INR rupees), None if amount is None.
    """
    if amount is None or pair_rate <= 0:
        return None
    try:
        return int(round(float(amount) * pair_rate))
    except (ValueError, TypeError):
        return None


def format_inr(amount_inr: Optional[int]) -> Optional[str]:
    """Format INR rupees as compact human string (e.g. 73,21,000 → ₹73.2L)."""
    if amount_inr is None:
        return None
    if amount_inr >= 10_000_000:  # 1 Crore
        return f"₹{amount_inr / 10_000_000:.1f}Cr"
    if amount_inr >= 100_000:  # 1 Lakh
        return f"₹{amount_inr / 100_000:.1f}L"
    if amount_inr >= 1_000:
        return f"₹{amount_inr / 1_000:.1f}K"
    return f"₹{amount_inr}"
