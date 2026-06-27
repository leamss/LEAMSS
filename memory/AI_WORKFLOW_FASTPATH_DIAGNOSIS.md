# 🔴 AI Workflow Builder — Fastpath Miss Diagnosis (Sir's CRITICAL Bug)

**Date:** Feb 27, 2026
**Status:** Root cause identified. NO code changes applied — awaiting Sir's alignment.
**Trigger:** Sir's screenshot shows AI generation progress (30%, "Calling Claude Sonnet 4.5...", 60-180s wait) instead of <200ms fastpath response despite 24 verified workflows seeded.

---

## 🔍 The Click Flow Sir Took (Reproduced)

```
1. Sir opens /admin/ai-workflow (AIWorkflowBuilder.jsx)
2. Sir clicks country card (e.g., "Australia")
   → Frontend calls POST /api/ai-workflow/visa-categories  body={country: "Australia"}
3. Backend /visa-categories builds country_key = "Australia".lower().replace(" ", "_") = "australia"
   → Looks up COUNTRY_REFERENCES["australia"] = {"pr": "...", "visitor": "...", ...}
   → Returns categories with name = svc_key.replace("_"," ").title() = "Pr", "Visitor", "Work", "Student", "Partner"
   → Possibly AI-enrichment overwrites with names like "Subclass 189 - Skilled Independent"
4. Sir sees 5 cards. Clicks one (e.g., "Pr" or "Subclass 189")
   → Frontend calls generateWorkflow(vc.name)
   → POST /api/ai-workflow/generate  body={country: "Australia", service_type: "Pr"}    ← TITLE-CASED!
5. Backend /generate calls find_verified_workflow("Australia", "Pr")
6. MongoDB query:
   {
     status: "verified",
     country_name: {$regex: "^Australia$", $options: "i"},  ← MATCHES (case-insensitive)
     service_type: "Pr"                                     ← FAILS (case-sensitive equality)
   }
7. Returns None (no document where service_type="Pr"). Seed has service_type="pr".
8. Backend falls through to AI path → job_id UUID created → progress bar starts → 60-180s wait
9. Eventually 429 / budget exceeded / timeout → Sir's screenshot
```

---

## 🔴 5 Smoking Guns Found

### Smoking Gun #1 — Case-sensitive `service_type` equality (PRIMARY ROOT CAUSE)
**File:** `backend/routers/country_workflows.py:585-589`
```python
q = {
  "status": "verified",
  "country_name": {"$regex": f"^{country_name}$", "$options": "i"},  # case-insensitive
  "service_type": service_type,  # ← EXACT EQUALITY, case-sensitive
}
```
**Reality:** Frontend sends `"Pr"` (title-cased via `.title()` at `ai_workflow_builder.py:368`), backend has `"pr"` stored. No match.

**Live curl proof:**
```
POST /api/ai-workflow/generate {country: "Australia", service_type: "Pr"}
  → source: <missing>   status: queued   job_id: 9c5ef0f3 (UUID = AI path)
POST /api/ai-workflow/generate {country: "Australia", service_type: "pr"}
  → source: seeded_verified   job_id: seeded-00141652  (fastpath HIT)
```

### Smoking Gun #2 — UK has ZERO categories returned (high-severity)
**File:** `ai_workflow_builder.py:62` declares COUNTRY_REFERENCES["uk"], but `ai_workflow_builder.py:349` computes `country_key = "United Kingdom".lower().replace(" ", "_") = "united_kingdom"`.
- `COUNTRY_REFERENCES["united_kingdom"]` DOESN'T EXIST → returns 0 hardcoded categories
- AI enrichment may save the day if budget OK; otherwise Sir sees empty UK list

**Live curl proof:**
```
POST /api/ai-workflow/visa-categories {country: "United Kingdom"}
  → Categories returned: 0
```

### Smoking Gun #3 — service_type vocabulary mismatch when AI enrichment fires
When `/visa-categories` AI enrichment succeeds, names returned look like:
- "Subclass 189 - Skilled Independent"
- "Express Entry - Federal Skilled Worker"
- "Skilled Worker Visa (Tier 2 General)"
- "Innovator Founder Visa"

Frontend sends these verbatim as `service_type`. Seed has `service_type` in fixed vocab: `pr|work|student|visitor|partner`. **Zero overlap.** Even if Sir clicks the perfect Subclass 189, fastpath misses.

**Live curl proof:**
```
POST /api/ai-workflow/generate {country: "Australia", service_type: "Subclass 189 - Skilled Independent"}
  → source: <missing>   status: queued (AI path)
```

### Smoking Gun #4 — Missing `partner` service_type in NZ and UK COUNTRY_REFERENCES
- NZ COUNTRY_REFERENCES has only: `visitor, pr, work, student` — NO `partner`
- UK COUNTRY_REFERENCES has: `visitor, work, student, family` — `family` not `partner`

So even Sir clicking NZ Partner-Resident or UK Spouse-Family from the dropdown is impossible (the category doesn't appear in the dropdown unless AI enrichment provides it). And if AI does provide a Partner option, see Smoking Gun #3.

### Smoking Gun #5 — country_code ("UK"/"AU"/"CA"/"NZ") not accepted as input
**Earlier tester report explicitly noted:** `"UK" alias does NOT route to seeded_verified`.
The lookup matches only on full `country_name`. If any client (mobile app, future admin filter, third-party API) sends ISO code "UK", it misses. Our seed has both `country_code="UK"` AND `country_name="United Kingdom"` — but lookup only checks `country_name`.

---

## 🎯 Concrete 3-Step Fix Plan (estimated 25-30 min total)

### Fix 1 — `find_verified_workflow()` becomes liberal in inputs (PRIMARY FIX)
**File:** `backend/routers/country_workflows.py`
**Change:** Accept country as name OR code OR alias, and service_type as case-insensitive canonical OR fuzzy-mapped.

```python
COUNTRY_ALIASES = {
    "australia": "AU", "au": "AU",
    "canada": "CA", "ca": "CA",
    "new zealand": "NZ", "nz": "NZ",
    "united kingdom": "UK", "uk": "UK", "britain": "UK", "great britain": "UK",
}

SERVICE_TYPE_CANONICAL = {
    # canonical -> canonical
    "pr": "pr", "work": "work", "student": "student", "visitor": "visitor", "partner": "partner",
    # title-cased variants
    "Pr": "pr", "Work": "work", "Student": "student", "Visitor": "visitor", "Partner": "partner",
    # synonyms
    "permanent residency": "pr", "permanent residence": "pr", "immigration": "pr",
    "family": "partner", "spouse": "partner", "spouse/family": "partner",
    # rich AI-returned names — fuzzy-match by keyword
    # (we'll do this via Python regex on lowercased input)
}

async def find_verified_workflow(country: str, service_type: str, subclass_id: Optional[str] = None):
    # Resolve country: try alias map, fallback to as-is + case-insensitive name match
    cc = COUNTRY_ALIASES.get((country or "").lower().strip())
    # Resolve service_type: canonical or fuzzy match
    svc_lower = (service_type or "").lower().strip()
    svc = SERVICE_TYPE_CANONICAL.get(svc_lower) or SERVICE_TYPE_CANONICAL.get(service_type)
    if not svc:
        # Fuzzy keyword scan
        if any(k in svc_lower for k in ["skilled", "express entry", "pnp", "smc", "green list", "innovator", "visa worker"]):
            svc = "work" if "worker" in svc_lower or "skilled work" in svc_lower or "innovator" in svc_lower else "pr"
        elif any(k in svc_lower for k in ["student", "study", "tier 4", "cas"]):
            svc = "student"
        elif any(k in svc_lower for k in ["visitor", "tourist", "trv", "visit"]):
            svc = "visitor"
        elif any(k in svc_lower for k in ["partner", "spouse", "family", "marriage"]):
            svc = "partner"
    # Build query: prefer country_code if alias resolved, else country_name regex
    q = {"status": "verified", "service_type": svc}
    if cc:
        q["country_code"] = cc
    else:
        q["country_name"] = {"$regex": f"^{re.escape(country)}$", "$options": "i"}
    # ... rest as before, with subclass_id fallback
```

**Test:** `POST /generate {country: "Australia", service_type: "Pr"}` → fastpath hit. Same for "AU", "australia", "United Kingdom"+"family", etc.

### Fix 2 — Update `COUNTRY_REFERENCES` for UK + NZ to cover all our seed service_types
**File:** `backend/routers/ai_workflow_builder.py:48-105`
**Change:**
- Add `"united_kingdom": COUNTRY_REFERENCES["uk"]` alias (or rename "uk" → "united_kingdom" and add reverse alias)
- Add `"partner"` key to NZ and UK with appropriate reference text
- Keep `"family"` for UK as a synonym

This ensures `/visa-categories` UI returns categories for UK/NZ correctly even WITHOUT AI enrichment.

### Fix 3 — `/visa-categories` returns canonical `service_type` in response (DEFENSE-IN-DEPTH)
**File:** `backend/routers/ai_workflow_builder.py:343-399`
**Change:** Add a `service_type` field to each returned category (alongside `name`/`category`):
```python
categories.append({
    "id": f"{country_key}_{svc_key}",
    "name": svc_key.replace("_", " ").title(),
    "category": svc_key,
    "service_type": svc_key,  # ← NEW: canonical for /generate
    ...
})
```

Then update `AIWorkflowBuilder.jsx:97-98` to send `vc.service_type || vc.category || vc.name`:
```js
service_type: visaName?.service_type || visaName?.category || visaName?.name || visaName
```
This is a small frontend tweak ensuring frontend always sends the canonical token.

---

## 🚨 Severity Assessment

| Issue | Severity | Impact |
|-------|----------|--------|
| #1 case mismatch | 🔴 CRITICAL | 100% of Sir's clicks miss fastpath unless he types exact lowercase service_type |
| #2 UK 0 categories | 🔴 CRITICAL | UK section unusable from `/visa-categories` without AI |
| #3 vocabulary mismatch | 🔴 HIGH | When AI enrichment runs, AI category names always miss fastpath |
| #4 missing partner/family | 🟡 HIGH | Partner workflows for NZ/UK invisible in standard UI flow |
| #5 country_code alias | 🟢 MEDIUM | Future-proofing; current frontend uses name not code |

---

## 📋 Files to Touch (after Sir's approval)

1. `/app/backend/routers/country_workflows.py` — `find_verified_workflow()` rewrite (Fix 1)
2. `/app/backend/routers/ai_workflow_builder.py` — `COUNTRY_REFERENCES` patch + `/visa-categories` response shape (Fix 2 + Fix 3a)
3. `/app/frontend/src/pages/AIWorkflowBuilder.jsx` — use `service_type` field instead of `name` (Fix 3b)

**Estimated total time:** 25-30 min for the fix + 10 min for verification across all 24 seeded workflows.

---

## ✋ Awaiting Sir's Alignment

**Before code changes, I need Sir's approval on:**
1. Scope — apply all 3 fixes together (recommended) OR just Fix 1 as a hotfix?
2. Should `find_verified_workflow()` fuzzy-match be conservative (only exact canonical synonyms) or aggressive (keyword-based fallback)?
3. Should the AI-enrichment of `/visa-categories` be DISABLED for our 4 seeded countries (AU/CA/NZ/UK) to ensure canonical names dominate? This would also save LLM budget.

Sir's frustration is fully understood and the diagnosis is owned. No fluff. Standing by for direction. 🙏
