"""Anomaly Detection for Share Link Audit Events.

Rule-based, no AI. Scans `share_audit_events` over a configurable window and
flags suspicious patterns per token. Used by:

  GET  /api/share-links/anomalies?since_hours=24

Severity rules
==============
  RAPID_BURST        : >= 10 successful accesses on a single token within any
                       1-hour rolling window (default; configurable per call)
  MULTIPLE_IPS       : >= 5 distinct IP addresses for same token within 30 min
  POST_REVOKE_SCRAPE : any `share_access_denied` event with reason=revoked
                       AFTER the `share_revoked` event for the same token
                       (means someone is hitting a known-dead link)
  EXPIRED_HAMMERING  : >= 5 access_denied(reason=expired) events on same token
                       within 1 hour (probably a stale link being retried)
  BOT_PATTERN        : a single user-agent string hitting >= 3 distinct tokens
                       within 1 hour (cross-token reconnaissance)

Higher severity = more reasons triggered AND larger counts.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


def _ensure_naive_utc(dt: Any) -> datetime | None:
    """All dt arithmetic uses naive UTC (matches BSON round-trip storage)."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def detect_anomalies(events: list[dict], window_hours: int = 24) -> dict:
    """Group events by token, then run all rule checks.

    `events` is a flat list of `share_audit_events` documents.

    Returns:
        {
          "scanned_events": N,
          "scanned_tokens": K,
          "anomalies": [ { token, share_type, client_name, entity_id, severity, flags: [...] } ],
          "summary": { "high": x, "medium": y, "low": z },
        }
    """
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)

    # Bucket events by token
    by_token: dict[str, list[dict]] = defaultdict(list)
    by_ua_recent: dict[str, set[str]] = defaultdict(set)  # ua -> set of tokens
    for e in events:
        ts = _ensure_naive_utc(e.get("created_at"))
        if not ts or ts < cutoff:
            continue
        token = e.get("share_token")
        if not token:
            continue
        by_token[token].append(e)
        ua = e.get("user_agent")
        if ua and e.get("event_type") in ("share_accessed", "share_access_denied"):
            by_ua_recent[ua].add(token)

    anomalies: list[dict] = []
    summary = {"high": 0, "medium": 0, "low": 0}

    # Bot-pattern UAs (compute once, reference per-anomaly)
    bot_uas = {ua for ua, toks in by_ua_recent.items() if len(toks) >= 3}

    for token, evs in by_token.items():
        evs_sorted = sorted(evs, key=lambda x: _ensure_naive_utc(x.get("created_at")) or datetime.utcnow())
        flags: list[dict] = []

        # Get metadata from the most recent event
        meta = next(
            (e for e in reversed(evs_sorted) if e.get("entity_id")),
            evs_sorted[-1] if evs_sorted else {},
        )
        share_type = meta.get("share_type", "sales_report")
        client_name = meta.get("client_name")
        entity_id = meta.get("entity_id")

        # ────────────────────────────────────────────────────────────
        # Rule 1: RAPID_BURST
        # ────────────────────────────────────────────────────────────
        access_events = [
            e for e in evs_sorted
            if e.get("event_type") == "share_accessed"
            and _ensure_naive_utc(e.get("created_at"))
        ]
        for i in range(len(access_events)):
            window_start = _ensure_naive_utc(access_events[i].get("created_at"))
            window_end = window_start + timedelta(hours=1)
            in_window = [
                e for e in access_events
                if window_start <= _ensure_naive_utc(e.get("created_at")) <= window_end
            ]
            if len(in_window) >= 10:
                flags.append({
                    "type": "rapid_burst",
                    "severity": "high" if len(in_window) >= 20 else "medium",
                    "count": len(in_window),
                    "window_hours": 1,
                    "first_at": window_start.isoformat(),
                    "last_at": _ensure_naive_utc(in_window[-1].get("created_at")).isoformat(),
                })
                break  # one burst flag per token is enough

        # ────────────────────────────────────────────────────────────
        # Rule 2: MULTIPLE_IPS within 30 mins
        # ────────────────────────────────────────────────────────────
        for i in range(len(access_events)):
            window_start = _ensure_naive_utc(access_events[i].get("created_at"))
            window_end = window_start + timedelta(minutes=30)
            ips_in_window = {
                e.get("ip_address") for e in access_events
                if window_start <= _ensure_naive_utc(e.get("created_at")) <= window_end
                and e.get("ip_address")
            }
            if len(ips_in_window) >= 5:
                flags.append({
                    "type": "multiple_ips",
                    "severity": "high" if len(ips_in_window) >= 10 else "medium",
                    "count": len(ips_in_window),
                    "window_minutes": 30,
                    "ips_sample": sorted(ips_in_window)[:10],
                    "first_at": window_start.isoformat(),
                })
                break

        # ────────────────────────────────────────────────────────────
        # Rule 3: POST_REVOKE_SCRAPE — denied access AFTER revoke event
        # ────────────────────────────────────────────────────────────
        revoke_at = None
        denied_after_revoke = []
        for e in evs_sorted:
            if e.get("event_type") == "share_revoked":
                revoke_at = _ensure_naive_utc(e.get("created_at"))
            elif revoke_at and e.get("event_type") == "share_access_denied":
                ts = _ensure_naive_utc(e.get("created_at"))
                if ts and ts > revoke_at:
                    denied_after_revoke.append(e)
        if denied_after_revoke:
            sev = "high" if len(denied_after_revoke) >= 5 else "medium"
            flags.append({
                "type": "post_revoke_scrape",
                "severity": sev,
                "count": len(denied_after_revoke),
                "revoked_at": revoke_at.isoformat() if revoke_at else None,
                "ips_sample": sorted({e.get("ip_address") for e in denied_after_revoke if e.get("ip_address")})[:10],
            })

        # ────────────────────────────────────────────────────────────
        # Rule 4: EXPIRED_HAMMERING — repeated hits on expired link
        # ────────────────────────────────────────────────────────────
        expired_hits = [
            e for e in evs_sorted
            if e.get("event_type") == "share_access_denied"
            and (e.get("details") or {}).get("reason") == "expired"
        ]
        if len(expired_hits) >= 5:
            # Are they within 1-hr window?
            ts_list = sorted([_ensure_naive_utc(e.get("created_at")) for e in expired_hits if e.get("created_at")])
            if ts_list and (ts_list[-1] - ts_list[0]) <= timedelta(hours=1):
                flags.append({
                    "type": "expired_hammering",
                    "severity": "low",
                    "count": len(expired_hits),
                    "first_at": ts_list[0].isoformat(),
                    "last_at": ts_list[-1].isoformat(),
                })

        # ────────────────────────────────────────────────────────────
        # Rule 5: BOT_PATTERN — UA seen across many tokens
        # ────────────────────────────────────────────────────────────
        token_uas = {e.get("user_agent") for e in evs if e.get("user_agent")}
        offending_ua = next((ua for ua in token_uas if ua in bot_uas), None)
        if offending_ua:
            flags.append({
                "type": "bot_pattern",
                "severity": "medium",
                "user_agent": offending_ua[:120],
                "distinct_tokens": len(by_ua_recent[offending_ua]),
            })

        # ────────────────────────────────────────────────────────────
        # Rule 6: IMPOSSIBLE_GEOGRAPHY — two accesses from countries that are
        # physically too far apart in too short a window (e.g. India ↔ USA
        # within 60 seconds = a human cannot teleport).
        # ────────────────────────────────────────────────────────────
        geo_events = [
            e for e in access_events
            if (e.get("details") or {}).get("geo")
        ]
        impossible_pairs = []
        for i in range(len(geo_events)):
            for j in range(i + 1, len(geo_events)):
                a_geo = (geo_events[i].get("details") or {}).get("geo") or {}
                b_geo = (geo_events[j].get("details") or {}).get("geo") or {}
                a_cc = a_geo.get("country_code")
                b_cc = b_geo.get("country_code")
                if not a_cc or not b_cc or a_cc == b_cc:
                    continue
                t1 = _ensure_naive_utc(geo_events[i].get("created_at"))
                t2 = _ensure_naive_utc(geo_events[j].get("created_at"))
                if not t1 or not t2:
                    continue
                gap_sec = abs((t2 - t1).total_seconds())
                if gap_sec <= 300:  # 5-minute window
                    impossible_pairs.append({
                        "from_country": a_cc, "to_country": b_cc,
                        "gap_seconds": int(gap_sec),
                        "first_at": min(t1, t2).isoformat(),
                    })
        if impossible_pairs:
            flags.append({
                "type": "impossible_geo",
                "severity": "high",
                "count": len(impossible_pairs),
                "pairs": impossible_pairs[:5],
            })

        # ────────────────────────────────────────────────────────────
        # Roll up severity
        # ────────────────────────────────────────────────────────────
        if flags:
            severities = [f["severity"] for f in flags]
            overall = "high" if "high" in severities else "medium" if "medium" in severities else "low"
            anomalies.append({
                "token_prefix": (token or "")[:10] + "…",
                "share_token": token,
                "share_type": share_type,
                "client_name": client_name,
                "entity_id": entity_id,
                "severity": overall,
                "flags": flags,
                "first_event_at": _ensure_naive_utc(evs_sorted[0].get("created_at")).isoformat(),
                "last_event_at": _ensure_naive_utc(evs_sorted[-1].get("created_at")).isoformat(),
                "total_events": len(evs_sorted),
            })
            summary[overall] += 1

    anomalies.sort(key=lambda a: ({"high": 0, "medium": 1, "low": 2}[a["severity"]], a["last_event_at"]))
    return {
        "scanned_events": sum(len(v) for v in by_token.values()),
        "scanned_tokens": len(by_token),
        "window_hours": window_hours,
        "anomalies": anomalies,
        "summary": summary,
    }
