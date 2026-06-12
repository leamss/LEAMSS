/**
 * Phase 18.5 — Floating Compare Bar.
 *
 * Renders at the bottom of every Sales / Atlas page when the user has pinned
 * 1+ occupations. Auto-hides on `/sales/compare` itself.
 *
 * Looks: low-profile pill strip, brand forest-green chip backgrounds,
 * burnt-orange "Compare Now" button.
 */
import { useLocation, useNavigate } from 'react-router-dom';
import { X, GitCompare, ChevronRight } from 'lucide-react';
import { useCompareStore } from '@/hooks/useCompareStore';
import { Button } from '@/components/ui/button';

const BRAND = {
  forest: '#1F4D44',
  forestDark: '#173B34',
  burnt: '#D4633F',
};

export default function CompareBar() {
  const { items, count, max, remove, clear } = useCompareStore();
  const navigate = useNavigate();
  const location = useLocation();

  // Auto-hide on the compare page itself
  if (location.pathname.startsWith('/sales/compare')) return null;
  if (count === 0) return null;

  return (
    <div
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 max-w-3xl w-[calc(100%-2rem)]"
      data-testid="compare-bar"
    >
      <div
        className="rounded-full shadow-2xl border border-slate-200 bg-white px-3 py-2 flex items-center gap-2 overflow-hidden"
        style={{ boxShadow: '0 10px 40px rgba(31, 77, 68, 0.18)' }}
      >
        <div className="flex items-center gap-1.5 shrink-0">
          <GitCompare className="h-4 w-4" style={{ color: BRAND.forest }} />
          <span className="text-[11px] font-semibold text-slate-700" data-testid="compare-bar-count">
            {count}/{max}
          </span>
        </div>

        <div className="flex items-center gap-1.5 flex-1 overflow-x-auto py-1 px-1">
          {items.map((it) => (
            <div
              key={`${it.country_code}-${it.code}`}
              className="flex items-center gap-1 rounded-full pl-2 pr-1 py-0.5 text-white text-[11px] font-mono shrink-0"
              style={{ background: BRAND.forest }}
              data-testid={`compare-bar-chip-${it.country_code}-${it.code}`}
            >
              <span>{it.country_code}-{it.code}</span>
              <button
                type="button"
                onClick={() => remove(it)}
                className="rounded-full hover:bg-white/20 p-0.5 transition"
                aria-label={`Remove ${it.country_code}-${it.code}`}
                data-testid={`compare-bar-remove-${it.country_code}-${it.code}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={clear}
          className="text-[10px] text-slate-500 hover:text-slate-700 shrink-0 px-2 py-1"
          data-testid="compare-bar-clear-btn"
        >
          Clear
        </button>

        <Button
          size="sm"
          onClick={() => navigate('/sales/compare')}
          className="rounded-full text-white hover:opacity-90 shrink-0 h-8 px-3 text-[12px]"
          style={{ background: BRAND.burnt }}
          data-testid="compare-now-btn"
          disabled={count < 1}
        >
          Compare Now <ChevronRight className="h-3 w-3 ml-0.5" />
        </Button>
      </div>
    </div>
  );
}
