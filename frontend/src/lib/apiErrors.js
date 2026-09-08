import React from 'react';
import { toast } from 'sonner';

/**
 * Format an axios error, validation error, object, or string into a human-readable string.
 * Handles:
 *   - String detail: "Profile not found"
 *   - FastAPI/Pydantic validation array: [{type, loc, msg, input, ctx, url}, ...]
 *   - FastAPI single validation object: {type, loc, msg, input, url}
 *   - Plain error objects or messages
 *   - React elements (passes through unchanged)
 */
export function formatApiError(e, fallback = 'Request failed') {
  if (e === null || e === undefined) return fallback;
  if (typeof e === 'string') return e;
  if (typeof e === 'number' || typeof e === 'boolean') return String(e);
  if (React.isValidElement(e)) return e;

  // Extract detail from Axios error, response object, or direct object
  const rawDetail = e?.response?.data?.detail ?? e?.data?.detail ?? e?.detail ?? e;

  if (typeof rawDetail === 'string') return rawDetail;

  if (Array.isArray(rawDetail)) {
    const formatted = rawDetail
      .map(d => {
        if (typeof d === 'string') return d;
        if (typeof d === 'object' && d !== null) {
          const loc = Array.isArray(d?.loc) ? d.loc.filter(l => l !== 'body').join('.') : '';
          const msg = d?.msg || d?.message || (typeof d === 'object' ? JSON.stringify(d) : String(d));
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(d);
      })
      .filter(Boolean)
      .join(' · ');
    return formatted || fallback;
  }

  if (typeof rawDetail === 'object' && rawDetail !== null) {
    if (rawDetail.msg) {
      const loc = Array.isArray(rawDetail.loc) ? rawDetail.loc.filter(l => l !== 'body').join('.') : '';
      return loc ? `${loc}: ${rawDetail.msg}` : rawDetail.msg;
    }
    if (rawDetail.message) return String(rawDetail.message);
    if (rawDetail.error) return typeof rawDetail.error === 'string' ? rawDetail.error : JSON.stringify(rawDetail.error);
    if (rawDetail.description) return String(rawDetail.description);

    // If it's an Axios Error object itself
    if (e?.response?.data?.message) return String(e.response.data.message);
    if (e?.message) return String(e.message);

    try {
      return JSON.stringify(rawDetail);
    } catch {
      return fallback;
    }
  }

  return e?.message || fallback;
}

/**
 * Patch sonner's toast methods globally so that passing any object, array, or Axios error
 * never causes React child invalid object crashes.
 */
export function initGlobalToastSanitizer() {
  if (typeof window === 'undefined') return;
  if (window.__toast_sanitizer_initialized__) return;
  window.__toast_sanitizer_initialized__ = true;

  const sanitizeArg = (arg) => {
    if (arg === null || arg === undefined) return arg;
    if (typeof arg === 'string' || typeof arg === 'number' || typeof arg === 'boolean') return arg;
    if (React.isValidElement(arg)) return arg;
    return formatApiError(arg);
  };

  const originalToast = toast;
  const methods = ['error', 'success', 'info', 'warning', 'message', 'loading'];

  methods.forEach(method => {
    if (typeof originalToast[method] === 'function') {
      const orig = originalToast[method].bind(originalToast);
      originalToast[method] = (message, data) => {
        return orig(sanitizeArg(message), data);
      };
    }
  });
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

