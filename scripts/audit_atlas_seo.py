"""Audit script: dump meta_description for top-N codes per country and
report uniqueness + length stats. Output CSV is written to /tmp.

Run:
    python /app/scripts/audit_atlas_seo.py [--n 100]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
import sys
import time
from collections import Counter
from typing import Dict, List, Tuple

import httpx

DEFAULT_API = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
COUNTRIES = ["AU", "CA", "NZ"]
DEFAULT_OUT = "/tmp/atlas_seo_audit.csv"


def fetch_codes(api: str, country: str, n: int) -> List[dict]:
    """Pull first N verified codes per country via public list endpoint."""
    r = httpx.get(f"{api}/public-atlas/{country.lower()}/list", params={"limit": n}, timeout=20)
    r.raise_for_status()
    items = r.json().get("items") or []
    return items[:n]


def fetch_meta(api: str, country: str, code: str) -> Tuple[str, int, str]:
    r = httpx.get(f"{api}/public-atlas/{country.lower()}/{code}", timeout=15)
    if r.status_code != 200:
        return ("", 0, f"HTTP {r.status_code}")
    seo = (r.json().get("seo") or {})
    m = seo.get("meta_description") or ""
    return (m, len(m), "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    rows: List[Dict[str, str]] = []
    counts_per_country: Dict[str, int] = {}
    errs = 0
    t0 = time.time()

    for country in COUNTRIES:
        try:
            items = fetch_codes(args.api, country, args.n)
        except Exception as e:
            print(f"ERROR fetching {country} list: {e}")
            return 2
        counts_per_country[country] = len(items)
        print(f"→ {country}: fetched {len(items)} codes")
        for it in items:
            code = it.get("code") or ""
            title = it.get("title") or ""
            m, ln, err = fetch_meta(args.api, country, code)
            if err:
                errs += 1
                continue
            rows.append({
                "country": country,
                "code": code,
                "title": title,
                "length": str(ln),
                "meta": m,
            })

    if errs:
        print(f"⚠ {errs} fetch errors")

    # Stats
    metas = [r["meta"] for r in rows]
    lengths = [int(r["length"]) for r in rows]
    unique = set(metas)
    duplicates_pairs: List[Tuple[str, str, str]] = []
    seen: Dict[str, Tuple[str, str]] = {}
    for r in rows:
        key = r["meta"]
        if key in seen:
            duplicates_pairs.append((seen[key][0] + "/" + seen[key][1], r["country"] + "/" + r["code"], key))
        else:
            seen[key] = (r["country"], r["code"])

    over_200 = [r for r in rows if int(r["length"]) > 200]

    # Artefact patterns
    bad_patterns = {
        "None_token":      re.compile(r"\bNone\b"),
        "empty_parens":    re.compile(r"\(\s*\)"),
        "empty_brackets":  re.compile(r"\[\s*\]"),
        "double_comma":    re.compile(r",\s*,"),
        "double_space":    re.compile(r"  +"),
        "space_punct":     re.compile(r"\s+[.,;]"),
    }
    artefact_counts = {k: sum(1 for r in rows if p.search(r["meta"])) for k, p in bad_patterns.items()}

    # Write CSV
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["country", "code", "title", "length", "meta"])
        w.writeheader()
        w.writerows(rows)

    # Report
    print("")
    print("============================================================")
    print(" Atlas SEO Audit · Phase 16.7")
    print("============================================================")
    print(f"  API base           : {args.api}")
    print(f"  CSV out            : {args.out}")
    print(f"  Sampled (req)      : {args.n} per country × {len(COUNTRIES)} = {args.n * len(COUNTRIES)}")
    print(f"  Sampled (actual)   : {len(rows)}")
    for c in COUNTRIES:
        print(f"      {c}: {counts_per_country.get(c, 0)} codes")
    print("")
    print("─── Uniqueness ───")
    print(f"  Unique descriptions : {len(unique)} / {len(rows)}")
    print(f"  Duplicates found    : {len(duplicates_pairs)}")
    if duplicates_pairs:
        for a, b, m in duplicates_pairs[:5]:
            print(f"      {a}  ≡  {b}")
            print(f"        meta = {m[:120]}…")
    print("")
    print("─── Length stats (chars) ───")
    if lengths:
        print(f"  min / median / mean / p95 / max : "
              f"{min(lengths)} / {statistics.median(lengths):.0f} / "
              f"{statistics.mean(lengths):.0f} / "
              f"{int(statistics.quantiles(lengths, n=20)[18])} / {max(lengths)}")
        print(f"  > 200 chars         : {len(over_200)}  (must be 0)")
        print(f"  < 120 chars         : {sum(1 for l in lengths if l < 120)}")
    print("")
    print("─── Artefacts (must all be 0) ───")
    for name, ct in artefact_counts.items():
        flag = "✓" if ct == 0 else "✗"
        print(f"  {flag} {name:18s}: {ct}")
    print("")
    print(f"  Elapsed: {time.time() - t0:.1f}s")

    # Exit code: 0 if clean, 1 if any failure
    ok = (
        len(unique) == len(rows)
        and not over_200
        and all(v == 0 for v in artefact_counts.values())
    )
    print("\n", "✅ PASS" if ok else "❌ FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
