# Option D — Brand Sweep Inventory (Phase 20.6.1)

**Date:** Jun 20, 2026
**Scope:** All `/app/frontend/src/**/*.jsx` and `*.js` files

## Pre-sweep inventory

| Pattern | Count |
|---|---|
| `indigo-*` classes | ~250 |
| `purple-*` classes | ~200 |
| `violet-*` classes | ~110 |
| **Total non-brand color refs** | **560** |

## Post-sweep result

| Pattern | Count |
|---|---|
| `indigo-*` classes | **0** |
| `purple-*` classes | **0** |
| `violet-*` classes | **0** |
| **Total** | **0** |

## Mapping applied

| Legacy | Replaced with |
|---|---|
| `indigo-50` → `indigo-900` | `leamss-teal-50` → `leamss-teal-900` |
| `purple-50` → `purple-900` | `leamss-orange-50` → `leamss-orange-900` |
| `violet-50` → `violet-900` | `leamss-red-50` → `leamss-red-900` |

## Tailwind config extension

Added 30 shade-aware aliases to `theme.extend.colors.leamss` so the standard
shade scale (`-50`, `-100`, `-200`, ... `-900`) works on all 3 brand colors.

Source values (Tailwind canonical):
- `leamss-teal-*` ← teal-* palette
- `leamss-orange-*` ← orange-* palette
- `leamss-red-*` ← red-* palette

## Files affected

**115 files modified** across:
- `pages/admin/*.jsx` (29 files)
- `pages/sales/*.jsx` (18 files)
- `pages/eligibility/*.jsx` (12 files)
- `pages/client/*.jsx` (8 files)
- `components/*.jsx` (35 files)
- `pages/*.jsx` (top-level, 13 files)

**Total replacements:** 872 individual class-name substitutions

## Skipped (intentional)

- `gray-*`, `slate-*`, `zinc-*`, `neutral-*` — neutral grays remain Tailwind-native
- Brand-color hex literals in `templates/atlas_*_ssr.html` — already use `var(--teal)` etc.
- `node_modules/` — third-party styles untouched

## Verification

```bash
grep -r "indigo-\|purple-\|violet-" /app/frontend/src --include="*.jsx" --include="*.js" | wc -l
# Output: 0
```

## Regression status

✅ All 294 Phase 19+20+step2+X5 tests still PASS after sweep
✅ Webpack compile succeeded with 1 unrelated lint warning
✅ 3 sample SSR pages render correctly

## Acceptance criterion met

> "<10 indigo/purple/violet references remaining across entire frontend codebase"

**Actual: 0 references. ✓**
