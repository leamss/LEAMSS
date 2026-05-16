/**
 * Format an axios error into a human-readable string.
 * Handles both:
 *   - String detail: "Profile not found"
 *   - FastAPI validation array: [{type, loc, msg, input, ctx}, ...]
 *   - Plain message
 */
export function formatApiError(e, fallback = 'Request failed') {
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => {
      const loc = Array.isArray(d?.loc) ? d.loc.slice(1).join('.') : '';
      return `${loc ? loc + ': ' : ''}${d?.msg || JSON.stringify(d)}`;
    }).join(' · ');
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return e?.message || fallback;
}

/**
 * Strip empty strings from nested object so Pydantic Optional[float|int] won't reject them.
 * Use this on wizard payloads before POST/PATCH.
 */
export function pruneEmpty(obj) {
  if (obj === null || obj === undefined) return obj;
  if (Array.isArray(obj)) return obj.map(pruneEmpty).filter(v => v !== undefined);
  if (typeof obj !== 'object') return obj;
  const cleaned = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v === '' || v === undefined) continue;
    if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      const sub = pruneEmpty(v);
      if (Object.keys(sub).length > 0) cleaned[k] = sub;
    } else if (Array.isArray(v)) {
      cleaned[k] = v.map(pruneEmpty);
    } else {
      cleaned[k] = v;
    }
  }
  return cleaned;
}
