# Phase 20.6 — Brand Spot-Audit Inventory (Jun 19, 2026)

## G1 — Codebase-wide scan results
- **Total files with non-brand colors**: 257
- **indigo-***: 91 files
- **purple-***: 55 files
- **violet-***: 18 files
- **blue-* (deep)**: 93 files

## G2 — Token mapping strategy (applied uniformly)

| Old Tailwind class | New leamss token |
|---|---|
| `bg-indigo-50` / `bg-indigo-100` | `bg-leamss-teal_50` |
| `bg-indigo-200` (light tint) | `bg-leamss-teal_50` |
| `bg-indigo-500` / `bg-indigo-600` / `bg-indigo-700` | `bg-leamss-teal` |
| `text-indigo-600` / `text-indigo-700` / `text-indigo-800` / `text-indigo-900` | `text-leamss-teal` |
| `border-indigo-200` / `border-indigo-300` / `border-l-indigo-500` | `border-leamss-teal` / `border-l-leamss-teal` |
| `hover:bg-indigo-700` | `hover:bg-leamss-teal/90` |
| `from-indigo-500 to-purple-500` (gradients) | `from-leamss-teal to-leamss-orange` |
| `bg-purple-100` / `text-purple-700` | `bg-leamss-orange_50` / `text-leamss-orange` |
| `bg-purple-500` / `bg-purple-600` | `bg-leamss-orange` |
| `bg-blue-50/30` / `bg-blue-100` | `bg-leamss-teal_50` |
| `text-blue-600` / `text-blue-700` / `text-blue-800` | `text-leamss-teal` |
| `border-l-blue-400` / `border-l-blue-500` | `border-l-leamss-teal` |
| `bg-violet-50` / `border-l-violet-500` | `bg-leamss-orange_50` / `border-l-leamss-orange` |
| `bg-red-* / text-red-*` (destructive) | `bg-leamss-red` / `text-leamss-red` |

**KEEP AS-IS:** `bg-slate-*`, `border-slate-*`, `text-slate-*` (neutral grays), `bg-white`, `bg-emerald-*` (success), `bg-amber-*` (warning), `bg-rose-*` (alert variant), `text-zinc-*`, `border-gray-*`.

## G3 — Priority files (~64 occurrences to replace)

| File | Indigo/Purple/Blue count |
|---|---|
| `pages/Login.jsx` | 3 |
| `pages/AIWorkflowBuilder.jsx` | 6 |
| `pages/admin/VerificationHub.jsx` | 18 |
| `pages/admin/AuthoritiesAdmin.jsx` | 2 |
| `components/admin/AuthorityHealthCard.jsx` | 5 |
| `components/admin/RecentImportsPanel.jsx` | 4 |
| `pages/admin/ProductsManager.jsx` | 19 |
| `pages/admin/DataImportHub.jsx` | 2 |
| `pages/sales/OccupationDetail.jsx` | 5 |
| **TOTAL** | **64** |

## Non-priority files (deferred to Phase 20.6.1 if Sir requests)
- 248 other files with indigo/purple/blue usages — many are public-facing pages (Atlas SSR, partner share links, mobile companion) that don't show in primary admin/sales/portal flows.

## Approach
Sed-based bulk replacement with token map. Each file rewritten via `mcp_search_replace` keyed on common Tailwind class patterns. Manual review of edge cases (e.g., gradients require ordered replacement).
