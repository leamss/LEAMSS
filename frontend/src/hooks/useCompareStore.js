/**
 * Phase 18.5 — Compare Store (sessionStorage-backed, max 3 pins).
 *
 * Lightweight hook used by:
 *   - OccupationDetail (Add to Compare button)
 *   - CompareBar (floating chip strip)
 *   - ComparePage (`/sales/compare`)
 *
 * Storage key: `leamss_compare_v1`
 * Shape: { items: [{ country_code, code, title }] }
 *
 * Why sessionStorage (not localStorage / Redux)?
 *   - Session-scoped is exactly the right lifetime for a "research in this tab" flow
 *   - No bloat, no rehydration concerns, no global state library
 *   - Cross-tab independence preferred per Sir's brief
 *
 * The hook broadcasts changes via a `storage` event proxy + a custom event
 * (`leamss-compare-changed`) so multiple mounted components stay in sync.
 */
import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'leamss_compare_v1';
const MAX_PINS = 3;
const CHANGE_EVENT = 'leamss-compare-changed';

function readFromStorage() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.items)) return [];
    return parsed.items
      .filter((it) => it && it.country_code && it.code)
      .slice(0, MAX_PINS)
      .map((it) => ({
        country_code: String(it.country_code).toUpperCase(),
        code: String(it.code),
        title: typeof it.title === 'string' ? it.title : '',
      }));
  } catch {
    return [];
  }
}

function writeToStorage(items) {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ items }));
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: { count: items.length } }));
  } catch {
    /* ignore quota / private-mode errors */
  }
}

export function useCompareStore() {
  const [items, setItems] = useState(() => readFromStorage());

  useEffect(() => {
    const refresh = () => setItems(readFromStorage());
    window.addEventListener(CHANGE_EVENT, refresh);
    window.addEventListener('storage', (e) => {
      if (e.key === STORAGE_KEY) refresh();
    });
    return () => {
      window.removeEventListener(CHANGE_EVENT, refresh);
    };
  }, []);

  const keyOf = (it) => `${(it.country_code || '').toUpperCase()}|${it.code}`;

  const has = useCallback((it) => {
    const k = keyOf(it);
    return items.some((x) => keyOf(x) === k);
  }, [items]);

  const add = useCallback((it) => {
    if (!it || !it.country_code || !it.code) return { ok: false, reason: 'invalid' };
    const k = keyOf(it);
    if (items.some((x) => keyOf(x) === k)) {
      return { ok: false, reason: 'duplicate' };
    }
    if (items.length >= MAX_PINS) {
      return { ok: false, reason: 'limit', max: MAX_PINS };
    }
    const next = [...items, {
      country_code: String(it.country_code).toUpperCase(),
      code: String(it.code),
      title: it.title || '',
    }];
    setItems(next);
    writeToStorage(next);
    return { ok: true, count: next.length };
  }, [items]);

  const remove = useCallback((it) => {
    if (!it) return;
    const k = keyOf(it);
    const next = items.filter((x) => keyOf(x) !== k);
    setItems(next);
    writeToStorage(next);
  }, [items]);

  const toggle = useCallback((it) => {
    if (has(it)) {
      remove(it);
      return { ok: true, action: 'removed' };
    }
    const r = add(it);
    return { ...r, action: r.ok ? 'added' : 'noop' };
  }, [add, has, remove]);

  const clear = useCallback(() => {
    setItems([]);
    writeToStorage([]);
  }, []);

  return {
    items,
    count: items.length,
    max: MAX_PINS,
    isFull: items.length >= MAX_PINS,
    has,
    add,
    remove,
    toggle,
    clear,
  };
}

export const COMPARE_STORAGE_KEY = STORAGE_KEY;
export const COMPARE_MAX_PINS = MAX_PINS;
