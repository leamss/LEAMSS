"""IP Geolocation lookup with caching.

Strategy (env-configurable, no hard dependencies):
  1. If GEOIP_DB_PATH points to a MaxMind GeoLite2 .mmdb file → use geoip2 lib.
  2. Else if IPGEO_API_URL is set → use that endpoint (defaults to ip-api.com).
  3. Else → public ip-api.com free tier (no key required).

Results cached in `ip_geo_cache` Mongo collection for 24h to avoid rate-limits.
Private/local IPs return None gracefully (skip geo logic).
"""
import ipaddress
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

from core.database import db

ip_geo_cache = db["ip_geo_cache"]
_CACHE_TTL_HOURS = 24

# Optional MaxMind reader (lazy-loaded)
_maxmind_reader = None


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local
    except ValueError:
        return True


def _try_maxmind(ip: str) -> Optional[dict]:
    """Try the MaxMind GeoLite2 reader if env var configured."""
    global _maxmind_reader
    db_path = os.environ.get("GEOIP_DB_PATH")
    if not db_path or not os.path.exists(db_path):
        return None
    if _maxmind_reader is None:
        try:
            import geoip2.database  # type: ignore
            _maxmind_reader = geoip2.database.Reader(db_path)
        except Exception:
            return None
    try:
        r = _maxmind_reader.city(ip)
        return {
            "ip": ip,
            "country_code": r.country.iso_code,
            "country": r.country.name,
            "region": r.subdivisions.most_specific.name if r.subdivisions else None,
            "city": r.city.name,
            "latitude": r.location.latitude,
            "longitude": r.location.longitude,
            "source": "maxmind",
        }
    except Exception:
        return None


async def _try_public_api(ip: str) -> Optional[dict]:
    """Fall back to ip-api.com free tier — 45 reqs/min, no API key."""
    api_url = os.environ.get("IPGEO_API_URL", "http://ip-api.com/json/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{api_url}{ip}")
            if r.status_code != 200:
                return None
            d = r.json()
            if d.get("status") != "success":
                return None
            return {
                "ip": ip,
                "country_code": d.get("countryCode"),
                "country": d.get("country"),
                "region": d.get("regionName"),
                "city": d.get("city"),
                "latitude": d.get("lat"),
                "longitude": d.get("lon"),
                "source": "ip-api.com",
            }
    except Exception:
        return None


async def lookup_ip(ip: Optional[str]) -> Optional[dict]:
    """Return geo info for an IP. None for private/invalid or lookup failure.

    Cached in Mongo for 24 hours.
    """
    if not ip or _is_private_ip(ip):
        return None

    # 1) Cache hit?
    cached = await ip_geo_cache.find_one({"ip": ip}, {"_id": 0})
    if cached:
        cached_at = cached.get("cached_at")
        if cached_at and (datetime.utcnow() - cached_at) < timedelta(hours=_CACHE_TTL_HOURS):
            return cached.get("geo")

    # 2) MaxMind?
    geo = _try_maxmind(ip)

    # 3) Public API fallback
    if not geo:
        geo = await _try_public_api(ip)

    # 4) Cache (even None — to avoid re-querying failed IPs for 1h)
    cache_doc = {
        "ip": ip,
        "geo": geo,
        "cached_at": datetime.utcnow(),
    }
    await ip_geo_cache.replace_one({"ip": ip}, cache_doc, upsert=True)
    return geo


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points (km)."""
    import math
    R = 6371.0  # Earth radius km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
