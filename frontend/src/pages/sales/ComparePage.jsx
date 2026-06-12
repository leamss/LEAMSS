/**
 * Phase 18.5 — Compare Page (`/sales/compare`).
 *
 * Calls `POST /api/sales/compare` with the pinned codes from sessionStorage
 * and renders a 3-column data grid + summary narrative.
 *
 * Empty state: friendly nudge to pin occupations from the search.
 * 1-pin state: backend already returns a "pin another" narrative.
 *
 * Rows rendered (each tagged with `compare-row-<key>`):
 *   - title
 *   - verification
 *   - skill_body
 *   - recommended_visa
 *   - eligible_visas
 *   - documents
 *   - similar
 *   - sample_cases
 *   - outcomes
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, GitCompare, ShieldCheck, Building2, FileText, Layers, Briefcase,
  AlertCircle, X, Sparkles, Loader2, Plane,
} from 'lucide-react';
import { useCompareStore } from '@/hooks/useCompareStore';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Phase 18.6 — Dev-only crash trigger used by the regression suite to verify
 * the global ErrorBoundary catches render errors in production routes.
 *
 * Activated ONLY when the page mounts with `localStorage.__leamss_force_crash__`
 * set matching the page's scope. Throws on EVERY render attempt so React's
 * concurrent recovery cannot bypass the boundary. The flag persists until the
 * boundary's "Reload page" button is pressed (which clears it before reload).
 *
 * Zero impact in normal sessions — the flag is never set by the app itself.
 */
function DevCrashTrigger({ scope }) {
  if (typeof window === 'undefined') return null;
  let flag = '';
  try { flag = window.localStorage.getItem('__leamss_force_crash__') || ''; } catch { /* ignore */ }
  if (flag && flag === scope) {
    throw new Error(`Phase 18.6 ErrorBoundary smoke-test crash (scope=${scope})`);
  }
  return null;
}

const BRAND = {
  forest: '#1F4D44',
  forestDark: '#173B34',
  burnt: '#D4633F',
  warm: '#FAFAF7',
  cream: '#F5F2EC',
};

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia' },
  CA: { flag: '🇨🇦', name: 'Canada' },
  NZ: { flag: '🇳🇿', name: 'New Zealand' },
};

export default function ComparePage() {
  const { items, count, max, remove, clear } = useCompareStore();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (count === 0) {
      setData(null);
      return;
    }
    setLoading(true);
    setError('');
    axios
      .post(`${API}/sales/compare`, { codes: items.map(({ country_code, code }) => ({ country_code, code })) }, { headers })
      .then((r) => setData(r.data))
      .catch((e) => {
        const msg = formatApiError(e, 'Could not load comparison');
        setError(msg);
        toast.error(msg);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map((it) => `${it.country_code}-${it.code}`).join(',')]);

  const occupations = data?.occupations || [];
  const notFound = data?.not_found || [];
  const narrative = data?.summary_narrative || '';

  return (
    <div className="min-h-screen" style={{ background: BRAND.warm }} data-testid="compare-page">
      <DevCrashTrigger scope="sales" />
      <div className="border-b border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-2" data-testid="compare-back-btn">
                <ArrowLeft className="h-4 w-4" />Back
              </button>
              <div className="flex items-center gap-2 flex-wrap">
                <GitCompare className="h-5 w-5" style={{ color: BRAND.forest }} />
                <h1 className="text-xl font-bold" style={{ color: BRAND.forestDark, fontFamily: 'Georgia, serif' }}>
                  Compare Occupations
                </h1>
                <Badge className="bg-slate-100 text-slate-700 text-[10px]" data-testid="compare-count">{count}/{max} pinned</Badge>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => navigate('/sales/occupations')} data-testid="compare-add-more-btn">
                Pin more
              </Button>
              {count > 0 && (
                <Button variant="ghost" size="sm" onClick={clear} className="text-slate-600" data-testid="compare-clear-all-btn">
                  Clear all
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {count === 0 && <EmptyState navigate={navigate} />}

        {loading && (
          <Card className="p-8 text-center text-slate-500" data-testid="compare-loading">
            <Loader2 className="h-5 w-5 mx-auto animate-spin mb-2" />
            <p className="text-sm">Loading comparison…</p>
          </Card>
        )}

        {!loading && error && (
          <Card className="p-6 border-l-4 border-l-rose-500 bg-rose-50/30 text-rose-800 text-sm" data-testid="compare-error">
            <AlertCircle className="h-4 w-4 inline mr-2" />
            {error}
          </Card>
        )}

        {!loading && !error && data && (
          <>
            {notFound.length > 0 && (
              <Card className="p-3 mb-3 border-l-4 border-l-amber-500 bg-amber-50/30 text-amber-900 text-[12px]" data-testid="compare-not-found">
                <AlertCircle className="h-3.5 w-3.5 inline mr-1" />
                Skipped — not found in atlas: {notFound.map((nf) => `${nf.country_code}-${nf.code}`).join(', ')}
              </Card>
            )}

            {narrative && (
              <Card
                className="p-4 mb-4 border-l-4"
                style={{ borderLeftColor: BRAND.burnt, background: '#FFF6F1' }}
                data-testid="compare-summary-narrative"
              >
                <div className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 mt-0.5 shrink-0" style={{ color: BRAND.burnt }} />
                  <div>
                    <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-0.5">Summary</p>
                    <p className="text-[13px] leading-relaxed text-slate-800" style={{ fontFamily: 'Georgia, serif' }}>{narrative}</p>
                  </div>
                </div>
              </Card>
            )}

            <Grid occupations={occupations} onRemove={remove} navigate={navigate} />
          </>
        )}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Empty state
   ════════════════════════════════════════════════════════════════ */
function EmptyState({ navigate }) {
  return (
    <Card className="p-10 text-center" data-testid="compare-empty">
      <GitCompare className="h-10 w-10 mx-auto mb-3 text-slate-300" />
      <h2 className="text-lg font-bold text-slate-700 mb-1">Nothing pinned yet</h2>
      <p className="text-[13px] text-slate-500 max-w-md mx-auto mb-4">
        Pin up to 3 occupations from the Smart Sales Helper search results, then return here to view a side-by-side comparison with a server-generated summary.
      </p>
      <Button
        onClick={() => navigate('/sales/occupations')}
        className="text-white"
        style={{ background: BRAND.burnt }}
        data-testid="compare-empty-cta"
      >
        Browse occupations
      </Button>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════
   Grid — 3-column data table
   ════════════════════════════════════════════════════════════════ */
function Grid({ occupations, onRemove, navigate }) {
  if (occupations.length === 0) return null;

  const cols = occupations.length;
  const gridStyle = { display: 'grid', gridTemplateColumns: `180px repeat(${cols}, minmax(220px, 1fr))`, gap: '0.5rem' };

  const Row = ({ rowKey, label, render, testidOverride }) => (
    <div className="contents" data-testid={testidOverride || `compare-row-${rowKey}`}>
      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 py-2 pr-2 flex items-center sticky left-0 bg-white border-r border-slate-100">
        {label}
      </div>
      {occupations.map((o) => (
        <div key={`${o.country_code}-${o.code}`} className="py-2 px-2 border-b border-slate-100">
          {render(o)}
        </div>
      ))}
    </div>
  );

  return (
    <Card className="overflow-x-auto" data-testid="compare-grid">
      <div className="min-w-fit" style={gridStyle}>
        {/* Header row */}
        <div className="sticky left-0 bg-white z-10 border-b border-slate-200 py-3 pr-2"></div>
        {occupations.map((o) => {
          const meta = COUNTRY_META[o.country_code] || { flag: '🌐', name: o.country_code };
          return (
            <div key={`${o.country_code}-${o.code}-h`} className="py-3 px-2 border-b border-slate-200 relative" data-testid={`compare-col-${o.country_code}-${o.code}`}>
              <button
                type="button"
                onClick={() => onRemove(o)}
                className="absolute top-2 right-2 rounded-full hover:bg-slate-100 p-1 text-slate-400 hover:text-slate-700"
                aria-label="Remove from comparison"
                data-testid={`compare-col-remove-${o.country_code}-${o.code}`}
              >
                <X className="h-3 w-3" />
              </button>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">{meta.flag}</span>
                <Badge className="bg-slate-100 text-slate-700 font-mono text-[10px]">{o.country_code}-{o.code}</Badge>
                {o.verification_meta?.is_verified && (
                  <Badge className="bg-emerald-100 text-emerald-700 text-[9px]"><ShieldCheck className="h-2.5 w-2.5 mr-0.5" />Verified</Badge>
                )}
              </div>
              <Link
                to={`/sales/occupations/${o.country_code}/${o.code}`}
                className="block text-[13px] font-semibold text-slate-800 hover:text-[#D4633F] line-clamp-2 leading-tight"
                style={{ fontFamily: 'Georgia, serif' }}
                data-testid={`compare-col-title-${o.country_code}-${o.code}`}
              >
                {o.title || '—'}
              </Link>
            </div>
          );
        })}

        {/* Verification */}
        <Row
          rowKey="verification"
          label="Verification"
          render={(o) => (
            <div className="text-[11px] text-slate-700">
              {o.verification_meta?.is_verified ? (
                <div className="flex flex-col gap-0.5">
                  <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-emerald-600" />Verified</span>
                  {o.verification_meta?.verified_by_name && <span className="text-slate-500">by <strong>{o.verification_meta.verified_by_name}</strong></span>}
                  {o.verification_meta?.days_since_verified != null && <span className="text-slate-500">{o.verification_meta.days_since_verified}d ago</span>}
                </div>
              ) : <span className="text-slate-400">Not verified</span>}
            </div>
          )}
        />

        {/* Skill body — testid required by Sir */}
        <Row
          rowKey="skill-body"
          testidOverride="compare-row-skill-body"
          label="Skill Body"
          render={(o) => (
            o.skill_body ? (
              <div className="text-[11px]">
                <div className="flex items-center gap-1 font-semibold text-slate-800"><Building2 className="h-3 w-3" />{o.skill_body.name}</div>
                <div className="text-slate-500 mt-0.5">
                  {o.skill_body.processing_time_weeks != null && <span>{o.skill_body.processing_time_weeks}wk · </span>}
                  {o.skill_body.fee_native != null && <span>{o.skill_body.fee_native}{o.skill_body.fee_currency ? ` ${o.skill_body.fee_currency}` : ''}</span>}
                </div>
              </div>
            ) : <span className="text-slate-400 text-[11px]">—</span>
          )}
        />

        {/* Recommended visa */}
        <Row
          rowKey="recommended-visa"
          label="Recommended Visa"
          render={(o) => (
            o.recommended_visa ? (
              <div className="text-[11px]">
                <Badge className="bg-amber-100 text-amber-800 font-mono"><Plane className="h-2.5 w-2.5 mr-0.5" />{o.recommended_visa.subclass}</Badge>
                {o.recommended_visa.name && o.recommended_visa.name !== o.recommended_visa.subclass && (
                  <p className="text-slate-500 mt-0.5">{o.recommended_visa.name}</p>
                )}
              </div>
            ) : <span className="text-slate-400 text-[11px]">—</span>
          )}
        />

        {/* Eligible visas */}
        <Row
          rowKey="eligible-visas"
          label={`Eligible Visas`}
          render={(o) => (
            (o.eligible_visas || []).length === 0
              ? <span className="text-slate-400 text-[11px]">—</span>
              : <div className="flex flex-wrap gap-1">{o.eligible_visas.map((v) => <Badge key={v} className="bg-slate-100 text-slate-700 text-[10px] font-mono">{v}</Badge>)}</div>
          )}
        />

        {/* Documents */}
        <Row
          rowKey="documents"
          label="Documents"
          render={(o) => (
            <div className="text-[11px]">
              <div className="font-semibold text-slate-800 flex items-center gap-1"><FileText className="h-3 w-3" />{o.required_documents_total || 0} required</div>
              {(o.doc_categories_top3 || []).length > 0 && (
                <div className="flex flex-wrap gap-0.5 mt-0.5">
                  {o.doc_categories_top3.map((c) => <Badge key={c} className="bg-slate-50 text-slate-600 text-[9px]">{c}</Badge>)}
                </div>
              )}
            </div>
          )}
        />

        {/* Similar */}
        <Row
          rowKey="similar"
          label="Similar codes"
          render={(o) => (
            (o.similar_count || 0) === 0
              ? <span className="text-slate-400 text-[11px]">—</span>
              : (
                <div className="text-[11px]">
                  <span className="font-semibold text-slate-800 flex items-center gap-1"><Layers className="h-3 w-3" />{o.similar_count}</span>
                  {(o.similar_top2 || []).length > 0 && (
                    <div className="flex flex-wrap gap-0.5 mt-0.5">
                      {o.similar_top2.map((s) => <Badge key={s} className="bg-slate-50 text-slate-600 text-[9px] font-mono">{s}</Badge>)}
                    </div>
                  )}
                </div>
              )
          )}
        />

        {/* Sample cases */}
        <Row
          rowKey="sample-cases"
          label="Sample Cases"
          render={(o) => (
            <div className="text-[11px]">
              <span className="font-semibold text-slate-800 flex items-center gap-1"><Briefcase className="h-3 w-3" />{o.sample_cases_count || 0}</span>
            </div>
          )}
        />

        {/* Outcome distribution */}
        <Row
          rowKey="outcomes"
          label="Outcomes"
          render={(o) => {
            const od = o.outcome_distribution || {};
            const total = (od.approved || 0) + (od.refused || 0) + (od.withdrawn || 0) + (od.pending || 0);
            if (!total) return <span className="text-slate-400 text-[11px]">—</span>;
            return (
              <div className="flex flex-wrap gap-1 text-[10px]">
                {od.approved > 0 && <Badge className="bg-emerald-100 text-emerald-700">✓ {od.approved}</Badge>}
                {od.refused > 0 && <Badge className="bg-rose-100 text-rose-700">✗ {od.refused}</Badge>}
                {od.withdrawn > 0 && <Badge className="bg-slate-100 text-slate-600">↩ {od.withdrawn}</Badge>}
                {od.pending > 0 && <Badge className="bg-amber-100 text-amber-700">⋯ {od.pending}</Badge>}
              </div>
            );
          }}
        />
      </div>
    </Card>
  );
}
