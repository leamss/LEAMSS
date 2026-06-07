/**
 * Phase 9 — LEAMSS Migration Atlas · Audit + Merge Dashboard
 *
 * READ-ONLY audit + Step 3 data merge tool. Visualises the exact coverage
 * gap between 1,236 anzsco_4digit_master records and 79 AU occupation_master
 * detail entries, and lets admin commit a safe merge (dry-run preview first).
 *
 * Inspired by anzscosearch.com — but powered by LEAMSS data.
 *
 * Route: /admin/anz-intel/audit  (legacy URL kept; UI now reads "Migration Atlas")
 */
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  Database, AlertTriangle, CheckCircle2, FileText, MapPin, Briefcase,
  Building2, Award, Globe2, Layers, Sparkles, RefreshCw, Search, Loader2,
  GitMerge, ArrowRight, Sliders,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// LEAMSS brand palette (no blue/indigo)
const C = {
  bg:          '#FAFAF9', card: '#FFFFFF', border: '#E5E7EB', borderSoft: '#F1F5F9',
  ink:         '#1F2937', body: '#475569', muted: '#94A3B8',
  teal:        '#0F766E', tealDeep: '#115E59', tealDark: '#134E4A',
  tealWash:    '#F0FDFA', tealWash2: '#CCFBF1',
  orange:      '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED', orangeWash2: '#FFEDD5',
  red:         '#D32F2F', redWash:    '#FEE2E2',
  gold:        '#D4A017', goldLight:  '#FBBF24', goldWash:   '#FEF3C7',
};

// Coverage colour scale (red = bad, gold = partial, teal = good)
function coverageColor(pct) {
  if (pct >= 80) return { bg: C.tealWash2, fg: C.tealDeep, border: C.teal };
  if (pct >= 50) return { bg: C.goldWash,   fg: C.orangeDeep, border: C.gold };
  if (pct >= 20) return { bg: C.orangeWash, fg: C.orangeDeep, border: C.orange };
  return { bg: C.redWash, fg: C.red, border: C.red };
}

export default function AnzIntelAudit() {
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [orphans, setOrphans] = useState([]);
  const [mergePreview, setMergePreview] = useState(null);
  const [mergeRunning, setMergeRunning] = useState(false);
  const [mergeResult, setMergeResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTxt, setSearchTxt] = useState('');
  const [activeTab, setActiveTab] = useState('coverage');

  const headers = useMemo(() => {
    const t = localStorage.getItem('token');
    return t ? { Authorization: `Bearer ${t}` } : {};
  }, []);

  const fetchAll = async () => {
    setRefreshing(true);
    try {
      const params = new URLSearchParams({ country: 'AU', limit: '200' });
      if (statusFilter !== 'all') params.set('only_status', statusFilter);
      if (searchTxt) params.set('search', searchTxt);

      const [s, r, o, mp] = await Promise.all([
        axios.get(`${API}/anz-intel/audit-summary`, { headers }),
        axios.get(`${API}/anz-intel/audit-rows?${params}`, { headers }),
        axios.get(`${API}/anz-intel/orphans-4digit?limit=50`, { headers }),
        axios.get(`${API}/anz-intel/merge-preview`, { headers }),
      ]);
      setSummary(s.data);
      setRows(r.data.items || []);
      setOrphans(o.data.items || []);
      setMergePreview(mp.data);
    } catch (e) { console.error('audit fetch', e); }
    setRefreshing(false);
    setLoading(false);
  };

  const runMerge = async () => {
    if (!window.confirm('Sir, confirm karein — ye action 853 naye 6-digit records add karega aur 25 existing ko enrich karega. Proceed?')) return;
    setMergeRunning(true);
    setMergeResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/merge-commit?confirm=YES-MERGE`, {}, { headers });
      setMergeResult(r.data);
      // Refresh all stats after merge
      await fetchAll();
    } catch (e) {
      setMergeResult({ error: e.response?.data?.detail || String(e) });
    }
    setMergeRunning(false);
  };

  useEffect(() => { fetchAll(); }, [statusFilter, searchTxt]); // eslint-disable-line

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: C.bg }}>
        <Loader2 className="h-8 w-8 animate-spin" style={{ color: C.teal }} />
      </div>
    );
  }

  const totals = summary?.totals || {};
  const fieldCoverage = summary?.field_coverage_au || [];
  const trackedFields = rows[0]?.coverage ? Object.keys(rows[0].coverage) : [];

  return (
    <div className="min-h-screen p-6 lg:p-10" style={{ background: C.bg, fontFamily: "'Manrope', sans-serif" }} data-testid="anz-audit-root">
      {/* ─── HEADER ─── */}
      <header className="mb-8">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.orange, letterSpacing: '0.14em' }}>
              Phase 9 · LEAMSS Migration Atlas
            </p>
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: C.tealDark, fontFamily: "'Playfair Display', serif" }}>
              Coverage Audit &amp; Data Merge
            </h1>
            <p className="text-sm mt-2 max-w-2xl" style={{ color: C.body }}>
              Step 1: read-only diagnostic. Step 2: safely merge anzsco_4digit_master → occupation_master.
              Reference benchmark:{' '}
              <a href="https://www.anzscosearch.com/search/" target="_blank" rel="noreferrer" style={{ color: C.teal, textDecoration: 'underline' }}>
                anzscosearch.com
              </a>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/admin/calculator-rules"
              className="px-3 py-2 rounded-md text-xs font-bold flex items-center gap-2 transition-colors"
              style={{ background: C.teal, color: '#fff' }}
              data-testid="anz-audit-rules-link"
            >
              <Sliders className="h-3.5 w-3.5" />Calculator Rules Editor
            </a>
            <button
              onClick={fetchAll}
              disabled={refreshing}
              className="px-3 py-2 rounded-md text-xs font-bold flex items-center gap-2 transition-colors"
              style={{ background: C.card, color: C.body, border: `1px solid ${C.border}` }}
              data-testid="anz-audit-refresh"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />Refresh
            </button>
          </div>
        </div>
      </header>

      {/* ─── HERO STATS ─── */}
      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8" data-testid="anz-audit-hero-stats">
        <HeroStat icon={Database}      label="ANZSCO 4-digit Groups" value={totals.anzsco_4digit_groups} sub="from jobsandskills.gov.au" tone="teal" />
        <HeroStat icon={Layers}        label="AU 6-digit Records"    value={totals.occupation_master_au_total} sub="in occupation_master" tone="teal" />
        <HeroStat icon={CheckCircle2}  label="Verified by Admin"     value={totals.occupation_master_au_verified} sub={`of ${totals.occupation_master_au_total}`} tone="gold" />
        <HeroStat icon={FileText}      label="Drafts (unverified)"   value={totals.occupation_master_au_draft} sub="need verification" tone="orange" />
        <HeroStat icon={CheckCircle2}  label="4-digit with Child"    value={totals['4digit_groups_with_child']} sub="have at least one 6-digit" tone="teal" />
        <HeroStat icon={AlertTriangle} label="4-digit ORPHANED"      value={totals['4digit_groups_without_child']} sub="have zero 6-digit children" tone="red" />
      </section>

      {/* ─── TABS ─── */}
      <nav className="flex gap-1 mb-6 border-b flex-wrap" style={{ borderColor: C.border }} data-testid="anz-audit-tabs">
        {[
          { key: 'coverage',  label: 'Field Coverage',  icon: Award },
          { key: 'rows',      label: 'Per-Occupation Heatmap', icon: Layers },
          { key: 'orphans',   label: 'Orphan 4-digit Groups',  icon: AlertTriangle },
          { key: 'merge',     label: 'Step 3 — Data Merge', icon: GitMerge },
          { key: 'scrapers',  label: 'Step 4 — Scrapers',  icon: Sparkles },
          { key: 'tools',     label: 'Step 5 — Manual Tools (CSV + AI Extract)', icon: FileText },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className="px-4 py-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors -mb-px"
            style={{
              borderColor: activeTab === t.key ? C.teal : 'transparent',
              color:       activeTab === t.key ? C.tealDeep : C.muted,
            }}
            data-testid={`anz-audit-tab-${t.key}`}
          >
            <t.icon className="h-4 w-4" />{t.label}
          </button>
        ))}
      </nav>

      {/* ─── TAB CONTENT ─── */}
      {activeTab === 'coverage' && <CoverageTab fields={fieldCoverage} totalCodes={totals.occupation_master_au_total} />}
      {activeTab === 'rows'     && (
        <HeatmapTab
          rows={rows} trackedFields={trackedFields}
          statusFilter={statusFilter} setStatusFilter={setStatusFilter}
          searchTxt={searchTxt} setSearchTxt={setSearchTxt}
          coverageLabels={summary?.field_coverage_au || []}
        />
      )}
      {activeTab === 'orphans'  && <OrphansTab orphans={orphans} />}
      {activeTab === 'merge'    && (
        <MergeTab preview={mergePreview} running={mergeRunning} result={mergeResult} onRun={runMerge} />
      )}
      {activeTab === 'scrapers' && <ScrapersTab headers={headers} onAfterCommit={fetchAll} />}
      {activeTab === 'tools'    && <ManualToolsTab headers={headers} onAfterCommit={fetchAll} />}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
function HeroStat({ icon: Icon, label, value, sub, tone }) {
  const palette = {
    teal:   { bg: C.tealWash,   bd: C.tealWash2,  fg: C.tealDeep,   ico: C.teal },
    gold:   { bg: C.goldWash,   bd: C.goldLight,  fg: C.orangeDeep, ico: C.gold },
    orange: { bg: C.orangeWash, bd: C.orangeWash2,fg: C.orangeDeep, ico: C.orange },
    red:    { bg: C.redWash,    bd: '#FCA5A5',    fg: C.red,        ico: C.red },
  }[tone || 'teal'];
  return (
    <div className="rounded-xl p-4 border" style={{ background: palette.bg, borderColor: palette.bd }}>
      <Icon className="h-4 w-4 mb-2" style={{ color: palette.ico }} />
      <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: palette.fg, letterSpacing: '0.08em' }}>{label}</p>
      <p className="text-3xl font-bold mt-1" style={{ color: palette.fg, fontFamily: "'Playfair Display', serif" }}>
        {(value ?? '—').toLocaleString?.() || value}
      </p>
      {sub && <p className="text-[10px] mt-1" style={{ color: palette.fg, opacity: 0.7 }}>{sub}</p>}
    </div>
  );
}

function CoverageTab({ fields, totalCodes }) {
  return (
    <div className="rounded-xl border bg-white p-1" style={{ borderColor: C.border }} data-testid="anz-audit-coverage-tab">
      <table className="w-full">
        <thead>
          <tr style={{ background: C.tealWash, borderBottom: `2px solid ${C.tealWash2}` }}>
            <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider" style={{ color: C.tealDeep, letterSpacing: '0.08em' }}>Field</th>
            <th className="text-right px-4 py-3 text-[10px] font-bold uppercase tracking-wider" style={{ color: C.tealDeep }}>Coverage</th>
            <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider w-1/2" style={{ color: C.tealDeep }}>Progress · {totalCodes} AU codes total</th>
            <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider" style={{ color: C.tealDeep }}>Source (when we scrape)</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f, idx) => {
            const col = coverageColor(f.pct_present);
            return (
              <tr key={f.field} style={{ borderBottom: `1px solid ${C.borderSoft}`, background: idx % 2 ? C.bg : C.card }}>
                <td className="px-4 py-3 text-sm font-semibold" style={{ color: C.ink }}>{f.label}</td>
                <td className="px-4 py-3 text-right text-sm font-bold" style={{ color: col.fg, fontFamily: 'monospace' }}>
                  {f.count_present} / {f.count_present + f.count_missing}
                  <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded" style={{ background: col.bg, color: col.fg }}>{f.pct_present}%</span>
                </td>
                <td className="px-4 py-3">
                  <div className="h-3 rounded-full overflow-hidden" style={{ background: C.borderSoft }}>
                    <div style={{ width: `${f.pct_present}%`, height: '100%', background: col.border, transition: 'width 0.5s' }} />
                  </div>
                </td>
                <td className="px-4 py-3 text-xs" style={{ color: C.muted }}>{f.source_hint}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function HeatmapTab({ rows, trackedFields, statusFilter, setStatusFilter, searchTxt, setSearchTxt, coverageLabels }) {
  const fieldLabel = (f) => (coverageLabels.find(x => x.field === f)?.label) || f;
  return (
    <div data-testid="anz-audit-heatmap-tab">
      {/* Filter row */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative">
          <Search className="h-3 w-3 absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
          <input
            value={searchTxt}
            onChange={(e) => setSearchTxt(e.target.value)}
            placeholder="Search by code or title…"
            className="pl-7 pr-3 py-1.5 rounded-md border text-xs outline-none w-64"
            style={{ background: C.card, borderColor: C.border, color: C.ink }}
            data-testid="anz-audit-search"
          />
        </div>
        {['all', 'verified', 'draft'].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className="px-3 py-1.5 rounded-md text-xs font-bold capitalize transition-colors border"
            style={{
              background:  statusFilter === s ? C.tealWash : C.card,
              borderColor: statusFilter === s ? C.teal : C.border,
              color:       statusFilter === s ? C.tealDeep : C.body,
            }}
            data-testid={`anz-audit-status-${s}`}
          >
            {s}
          </button>
        ))}
        <p className="text-xs ml-auto" style={{ color: C.muted }}>
          Showing <strong style={{ color: C.ink }}>{rows.length}</strong> records
        </p>
      </div>
      {/* Heatmap grid */}
      <div className="rounded-xl border overflow-x-auto bg-white" style={{ borderColor: C.border }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: C.tealWash, borderBottom: `2px solid ${C.tealWash2}` }}>
              <th className="text-left px-3 py-2 font-bold whitespace-nowrap" style={{ color: C.tealDeep }}>Code</th>
              <th className="text-left px-3 py-2 font-bold" style={{ color: C.tealDeep }}>Title</th>
              <th className="text-left px-2 py-2 font-bold" style={{ color: C.tealDeep }}>Status</th>
              <th className="text-right px-2 py-2 font-bold" style={{ color: C.tealDeep }}>Cov%</th>
              {trackedFields.map(f => (
                <th key={f} className="text-center px-1 py-2 font-bold whitespace-nowrap" style={{ color: C.tealDeep }} title={fieldLabel(f)}>
                  {fieldLabel(f).split(' ').map(w => w[0]).join('').slice(0, 3)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => {
              const col = coverageColor(r.coverage_pct);
              return (
                <tr key={r.code} style={{ borderBottom: `1px solid ${C.borderSoft}`, background: idx % 2 ? C.bg : C.card }} data-testid={`anz-audit-row-${r.code}`}>
                  <td className="px-3 py-2 font-mono font-bold" style={{ color: C.tealDeep }}>{r.code}</td>
                  <td className="px-3 py-2" style={{ color: C.ink }}>{r.title}</td>
                  <td className="px-2 py-2">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase"
                          style={{
                            background: r.status === 'verified' ? C.tealWash2 : r.status === 'draft' ? C.orangeWash2 : C.borderSoft,
                            color:      r.status === 'verified' ? C.tealDeep : r.status === 'draft' ? C.orangeDeep : C.muted,
                          }}>
                      {r.status}
                    </span>
                  </td>
                  <td className="text-right px-2 py-2 font-bold font-mono" style={{ color: col.fg }}>{r.coverage_pct}%</td>
                  {trackedFields.map(f => (
                    <td key={f} className="text-center px-1 py-2" title={fieldLabel(f)}>
                      {r.coverage[f]
                        ? <span style={{ color: C.teal, fontWeight: 800 }}>✓</span>
                        : <span style={{ color: C.red, fontWeight: 800 }}>✗</span>}
                    </td>
                  ))}
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr><td colSpan={trackedFields.length + 4} className="text-center py-8" style={{ color: C.muted }}>No records match filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        <p style={{ color: C.muted }}>Column abbreviations:</p>
        {trackedFields.map(f => (
          <span key={f} style={{ color: C.body }}>
            <strong style={{ color: C.tealDeep, fontFamily: 'monospace' }}>{fieldLabel(f).split(' ').map(w => w[0]).join('').slice(0, 3)}</strong>
            {' = '}{fieldLabel(f)}
          </span>
        ))}
      </div>
    </div>
  );
}

function OrphansTab({ orphans }) {
  return (
    <div data-testid="anz-audit-orphans-tab">
      <div className="mb-4 p-4 rounded-lg" style={{ background: C.orangeWash, border: `1px solid ${C.orangeWash2}` }}>
        <p className="text-sm font-bold" style={{ color: C.orangeDeep }}>
          🔴 {orphans.length} ANZSCO 4-digit groups have NO 6-digit child in occupation_master
        </p>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Sorted by largest workforce — these are the highest-value codes to enrich first.
        </p>
      </div>
      <div className="rounded-xl border overflow-x-auto bg-white" style={{ borderColor: C.border }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: C.tealWash, borderBottom: `2px solid ${C.tealWash2}` }}>
              <th className="text-left px-3 py-2 font-bold" style={{ color: C.tealDeep }}>4-digit Code</th>
              <th className="text-left px-3 py-2 font-bold" style={{ color: C.tealDeep }}>Title (ABS ANZSCO)</th>
              <th className="text-right px-3 py-2 font-bold" style={{ color: C.tealDeep }}>Workforce</th>
              <th className="text-right px-3 py-2 font-bold" style={{ color: C.tealDeep }}>Median Weekly (AUD)</th>
            </tr>
          </thead>
          <tbody>
            {orphans.map((o, idx) => (
              <tr key={o.code} style={{ borderBottom: `1px solid ${C.borderSoft}`, background: idx % 2 ? C.bg : C.card }} data-testid={`anz-audit-orphan-${o.code}`}>
                <td className="px-3 py-2 font-mono font-bold" style={{ color: C.tealDeep }}>{o.code}</td>
                <td className="px-3 py-2" style={{ color: C.ink }}>{o.title}</td>
                <td className="text-right px-3 py-2 font-mono" style={{ color: C.body }}>{o.employed ? o.employed.toLocaleString() : '—'}</td>
                <td className="text-right px-3 py-2 font-mono" style={{ color: C.body }}>{o.median_weekly_aud ? `$${o.median_weekly_aud.toLocaleString()}` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MergeTab({ preview, running, result, onRun }) {
  if (!preview) return <p style={{ color: C.muted }}>Loading merge preview…</p>;
  const s = preview.summary || {};

  return (
    <div data-testid="anz-audit-merge-tab">
      <div className="mb-4 p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
        <p className="text-sm font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
          <GitMerge className="h-4 w-4" />Step 3 — Safe Data Merge (DRY-RUN preview below)
        </p>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Yeh operation <code style={{ background: '#fff', padding: '1px 4px', borderRadius: 3 }}>anzsco_4digit_master</code> ke 6-digit codes ko{' '}
          <code style={{ background: '#fff', padding: '1px 4px', borderRadius: 3 }}>occupation_master</code> me sync karega.
          Existing records overwrite NAHI honge — sirf missing fields enrich honge.
          Test artifacts (32) untouched rahenge.
        </p>
      </div>

      {/* Preview cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="anz-merge-preview-stats">
        <PreviewStat icon={CheckCircle2}   label="Pehle se present"     value={s.existing_6digit_in_master} tone="teal" />
        <PreviewStat icon={Database}        label="ANZSCO master me total" value={s.available_in_anzsco_master} tone="teal" />
        <PreviewStat icon={Sparkles}        label="Naye banenge"          value={s.will_create_new} tone="gold" />
        <PreviewStat icon={ArrowRight}      label="Enrich honge"          value={s.will_enrich_existing} tone="orange" />
      </div>

      {/* Inherited fields list */}
      <div className="mb-6 p-4 rounded-lg bg-white border" style={{ borderColor: C.border }}>
        <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: C.tealDeep, letterSpacing: '0.08em' }}>
          Inherited from 4-digit parent
        </p>
        <div className="flex flex-wrap gap-2">
          {(s.fields_inherited_from_4digit_parent || []).map(f => (
            <span key={f} className="text-xs px-2 py-1 rounded font-mono" style={{ background: C.tealWash, color: C.tealDeep, border: `1px solid ${C.tealWash2}` }}>
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Sample creates & enriches */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <SampleList title={`First 8 NEW records (${s.will_create_new} total)`} items={preview.sample_creates} tone="gold" />
        <SampleList title={`First 8 enriched (${s.will_enrich_existing} total)`} items={preview.sample_enriches} tone="orange" />
      </div>

      {/* Run merge button + result */}
      <div className="p-4 rounded-lg border" style={{ background: C.card, borderColor: C.border }}>
        {!result && (
          <>
            <p className="text-sm font-bold mb-2" style={{ color: C.ink }}>Ready to commit?</p>
            <p className="text-xs mb-4" style={{ color: C.body }}>
              ⚠️ Yeh action database me actual write karega. Existing data preserved rahega.
              Aap &ldquo;Refresh&rdquo; karke baad me result verify kar sakte hain.
            </p>
            <button
              onClick={onRun}
              disabled={running}
              className="px-5 py-2.5 rounded-md font-bold text-sm flex items-center gap-2 shadow-sm transition-all hover:shadow-md disabled:opacity-50"
              style={{ background: C.teal, color: '#fff' }}
              data-testid="anz-merge-run-btn"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitMerge className="h-4 w-4" />}
              {running ? 'Merging…' : `Run Merge — Add ${s.will_create_new} new, Enrich ${s.will_enrich_existing}`}
            </button>
          </>
        )}
        {result && !result.error && (
          <div className="p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="anz-merge-result-success">
            <p className="text-base font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
              <CheckCircle2 className="h-5 w-5" />Merge complete!
            </p>
            <ul className="mt-3 text-sm space-y-1" style={{ color: C.body }}>
              <li><strong>{result.created}</strong> new records created</li>
              <li><strong>{result.enriched}</strong> existing records enriched</li>
              <li><strong>{result.total_processed}</strong> total processed</li>
              <li className="text-xs mt-2" style={{ color: C.muted }}>Committed at: {result.committed_at}</li>
            </ul>
          </div>
        )}
        {result?.error && (
          <div className="p-4 rounded-lg" style={{ background: C.redWash, border: `1px solid #FCA5A5` }} data-testid="anz-merge-result-error">
            <p className="text-sm font-bold" style={{ color: C.red }}>❌ Merge failed</p>
            <p className="text-xs mt-1" style={{ color: C.body }}>{result.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function PreviewStat({ icon: Icon, label, value, tone }) {
  const palette = {
    teal:   { bg: C.tealWash,   bd: C.tealWash2,  fg: C.tealDeep,   ico: C.teal },
    gold:   { bg: C.goldWash,   bd: C.goldLight,  fg: C.orangeDeep, ico: C.gold },
    orange: { bg: C.orangeWash, bd: C.orangeWash2,fg: C.orangeDeep, ico: C.orange },
  }[tone || 'teal'];
  return (
    <div className="rounded-xl p-4 border" style={{ background: palette.bg, borderColor: palette.bd }}>
      <Icon className="h-4 w-4 mb-2" style={{ color: palette.ico }} />
      <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: palette.fg, letterSpacing: '0.08em' }}>{label}</p>
      <p className="text-2xl font-bold mt-1" style={{ color: palette.fg, fontFamily: "'Playfair Display', serif" }}>{value ?? '—'}</p>
    </div>
  );
}

function SampleList({ title, items, tone }) {
  const fg = tone === 'gold' ? C.orangeDeep : tone === 'orange' ? C.orangeDeep : C.tealDeep;
  return (
    <div className="rounded-lg border p-3" style={{ background: C.card, borderColor: C.border }}>
      <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: fg, letterSpacing: '0.06em' }}>{title}</p>
      <div className="space-y-1">
        {(items || []).map(it => (
          <div key={it.code} className="flex items-baseline gap-2 text-xs" style={{ color: C.body }}>
            <span className="font-mono font-bold" style={{ color: C.tealDeep }}>{it.code}</span>
            <span>{it.title}</span>
          </div>
        ))}
        {(!items || items.length === 0) && <p className="text-xs" style={{ color: C.muted }}>None.</p>}
      </div>
    </div>
  );
}

// ─── Step 4 — Scrapers Tab ──────────────────────────────────────────────────
function ScrapersTab({ headers, onAfterCommit }) {
  const [scrapers, setScrapers] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [dryRunByScraper, setDryRunByScraper] = useState({});
  const [running, setRunning] = useState(false);
  const [commitResultByScraper, setCommitResultByScraper] = useState({});

  useEffect(() => {
    axios.get(`${API}/anz-intel/scrapers/list`, { headers })
      .then(r => setScrapers(r.data.scrapers || []))
      .catch(e => console.error('scrapers/list', e));
  }, [headers]);

  const runEndpointForId = (id) => {
    const mapping = {
      home_affairs:          '/anz-intel/scrapers/home-affairs/run',
      state_nominations:     '/anz-intel/scrapers/state-nominations/run',
      skillselect_tiers:     '/anz-intel/scrapers/skillselect-tiers/run',
      vetassess_groups:      '/anz-intel/scrapers/vetassess-groups/run',
      min_invitation_points: '/anz-intel/scrapers/min-invitation-points/run',
      dama:                  '/anz-intel/scrapers/dama/run',
      ila:                   '/anz-intel/scrapers/ila/run',
    };
    return mapping[id];
  };

  const runDry = async (id) => {
    setActiveId(id);
    setRunning(true);
    setDryRunByScraper(prev => ({ ...prev, [id]: null }));
    setCommitResultByScraper(prev => ({ ...prev, [id]: null }));
    try {
      const ep = runEndpointForId(id);
      const r = await axios.post(`${API}${ep}?dry_run=true`, {}, { headers });
      setDryRunByScraper(prev => ({ ...prev, [id]: r.data }));
    } catch (e) {
      setDryRunByScraper(prev => ({ ...prev, [id]: { error: e.response?.data?.detail || String(e) } }));
    }
    setRunning(false);
  };

  const runCommit = async (id) => {
    const dry = dryRunByScraper[id];
    if (!dry) return;
    const commitMsgMap = {
      home_affairs:          `${dry.ha_codes_with_changes} records enrich honge`,
      state_nominations:     `${dry.counts?.total_unique_docs_touched} records me state nomination data add hoga (NSW + QLD)`,
      skillselect_tiers:     `${dry.to_update} records me SkillSelect Tier (1-4) assign hoga`,
      vetassess_groups:      `${dry.to_update} records me VETASSESS Group (A-F) seed hoga`,
      min_invitation_points: `${dry.counts?.tier_1_codes_tagged} priority-tier records me invitation cutoffs tag honge`,
      dama:                  `${dry.counts?.occupations_tagged} occupations ko ${dry.total_damas} DAMAs ke saath tag karenge`,
      ila:                   `${dry.counts?.occupations_tagged} occupations ko ${dry.total_ilas} Industry Labour Agreements ke saath tag karenge`,
    };
    if (!window.confirm(`Sir, confirm — ${commitMsgMap[id]}. Existing verified records preserved rahenge. Proceed?`)) return;

    setActiveId(id);
    setRunning(true);
    setCommitResultByScraper(prev => ({ ...prev, [id]: null }));
    try {
      const ep = runEndpointForId(id);
      const r = await axios.post(`${API}${ep}?dry_run=false`, {}, { headers });
      setCommitResultByScraper(prev => ({ ...prev, [id]: r.data }));
      if (onAfterCommit) await onAfterCommit();
    } catch (e) {
      setCommitResultByScraper(prev => ({ ...prev, [id]: { error: e.response?.data?.detail || String(e) } }));
    }
    setRunning(false);
  };

  return (
    <div data-testid="anz-audit-scrapers-tab">
      <div className="mb-4 p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
        <p className="text-sm font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
          <Sparkles className="h-4 w-4" />Step 4 — Live Scrapers &amp; Classifiers
        </p>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Har scraper run karne se pehle <b>DRY-RUN preview</b> dikhega. Aap dekhke confirm kar sakte hain,
          fir actual commit hoga. Verified records kabhi auto-overwrite nahi honge.
        </p>
      </div>

      {/* Scrapers list */}
      <div className="space-y-4 mb-6">
        {scrapers.map(s => {
          const dry = dryRunByScraper[s.id];
          const commit = commitResultByScraper[s.id];
          const isActive = activeId === s.id;
          return (
            <div key={s.id} className="rounded-xl border p-4" style={{ background: C.card, borderColor: C.border }} data-testid={`scraper-${s.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-bold text-base" style={{ color: C.ink }}>{s.name}</h3>
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded"
                          style={{
                            background: s.status === 'ready' ? C.tealWash2 : C.orangeWash2,
                            color:      s.status === 'ready' ? C.tealDeep : C.orangeDeep,
                          }}>
                      {s.status}
                    </span>
                  </div>
                  {s.source_url?.startsWith('http') ? (
                    <a href={s.source_url} target="_blank" rel="noreferrer" className="text-xs underline" style={{ color: C.teal }}>
                      {s.source_url}
                    </a>
                  ) : (
                    <span className="text-xs italic" style={{ color: C.muted }}>{s.source_url}</span>
                  )}
                  <ul className="mt-2 space-y-0.5 text-xs" style={{ color: C.body }}>
                    {s.what_it_provides.map((w, i) => (
                      <li key={i}>→ {w}</li>
                    ))}
                  </ul>
                  {s.note && <p className="mt-2 text-xs italic" style={{ color: C.orangeDeep }}>{s.note}</p>}
                </div>
                {s.status === 'ready' && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => runDry(s.id)}
                      disabled={running}
                      className="px-3 py-1.5 rounded-md text-xs font-bold border flex items-center gap-1.5 transition-colors disabled:opacity-50"
                      style={{ background: C.card, color: C.teal, borderColor: C.teal }}
                      data-testid={`scraper-${s.id}-dry-run-btn`}
                    >
                      {running && isActive && !dry ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                      Dry-Run Preview
                    </button>
                  </div>
                )}
              </div>

              {/* Per-scraper dry-run + commit result */}
              {dry && !dry.error && (
                <ScraperDryRunPreview
                  id={s.id}
                  dry={dry}
                  running={running && isActive}
                  onCommit={() => runCommit(s.id)}
                />
              )}
              {dry?.error && (
                <div className="mt-4 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
                  <p className="text-sm font-bold" style={{ color: C.red }}>Dry-run failed</p>
                  <p className="text-xs mt-1" style={{ color: C.body }}>{dry.error}</p>
                </div>
              )}
              {commit && !commit.error && (
                <div className="mt-4 p-3 rounded-md" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid={`scraper-${s.id}-commit-result`}>
                  <p className="text-sm font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
                    <CheckCircle2 className="h-4 w-4" />Commit complete — data persisted to database
                  </p>
                  <p className="text-xs mt-1" style={{ color: C.muted }}>Run &ldquo;Refresh&rdquo; up top OR click any tab to see updated coverage bars.</p>
                </div>
              )}
              {commit?.error && (
                <div className="mt-4 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
                  <p className="text-sm font-bold" style={{ color: C.red }}>Commit failed</p>
                  <p className="text-xs mt-1" style={{ color: C.body }}>{commit.error}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Per-scraper dry-run preview that renders different stats based on scraper id
function ScraperDryRunPreview({ id, dry, running, onCommit }) {
  let stats;
  let samples = null;
  let commitLabel = 'Commit';

  if (id === 'home_affairs') {
    stats = [
      { icon: Database,      label: 'Fetched',            value: dry.fetched_records, tone: 'teal' },
      { icon: ArrowRight,    label: 'Will Update',        value: dry.ha_codes_with_changes, tone: 'gold' },
      { icon: CheckCircle2,  label: 'Verified preserved', value: dry.skipped_verified, tone: 'teal' },
      { icon: AlertTriangle, label: 'HA codes not in DB', value: dry.ha_codes_not_in_db, tone: 'orange' },
    ];
    commitLabel = `Commit — Update ${dry.ha_codes_with_changes} records`;
    samples = dry.sample_updates;
  } else if (id === 'state_nominations') {
    const c = dry.counts || {};
    stats = [
      { icon: Database,    label: 'NSW unit groups',     value: c.nsw_4digit_unit_groups_scraped, tone: 'teal' },
      { icon: Database,    label: 'QLD codes scraped',   value: c.qld_6digit_codes_scraped, tone: 'teal' },
      { icon: ArrowRight,  label: 'NSW updates',         value: c.nsw_records_updated, tone: 'gold' },
      { icon: ArrowRight,  label: 'QLD updates',         value: c.qld_records_updated, tone: 'gold' },
    ];
    commitLabel = `Commit — Update ${c.total_unique_docs_touched} records`;
    samples = (dry.sample_updates || []).map(u => ({
      code: u.code,
      title: u.title,
      updated_fields: u.states_added,
    }));
  } else if (id === 'skillselect_tiers') {
    const t = dry.tier_distribution || {};
    stats = [
      { icon: Award,       label: 'Tier 1 (Health/Edu)', value: t.tier_1, tone: 'teal' },
      { icon: Award,       label: 'Tier 2 (CSOL)',        value: t.tier_2, tone: 'teal' },
      { icon: Award,       label: 'Tier 3 (MLTSSL/Reg)', value: t.tier_3, tone: 'gold' },
      { icon: Award,       label: 'Tier 4 (Other)',      value: t.tier_4, tone: 'orange' },
    ];
    commitLabel = `Commit — Assign tier to ${dry.to_update} records`;
    // Combine samples from all tiers
    const bag = dry.sample_by_tier || {};
    samples = [...(bag.tier_1 || []).map(x => ({ ...x, updated_fields: ['tier_1'] })),
               ...(bag.tier_2 || []).slice(0, 2).map(x => ({ ...x, updated_fields: ['tier_2'] })),
               ...(bag.tier_3 || []).slice(0, 2).map(x => ({ ...x, updated_fields: ['tier_3'] })),
               ...(bag.tier_4 || []).slice(0, 2).map(x => ({ ...x, updated_fields: ['tier_4'] }))].slice(0, 8);
  } else if (id === 'vetassess_groups') {
    const g = dry.by_group || {};
    stats = [
      { icon: Award,       label: 'Group A',  value: g.A, tone: 'teal' },
      { icon: Award,       label: 'Group B',  value: g.B, tone: 'teal' },
      { icon: Award,       label: 'Group C+D',value: (g.C || 0) + (g.D || 0), tone: 'gold' },
      { icon: Award,       label: 'Group E+F',value: (g.E || 0) + (g.F || 0), tone: 'orange' },
    ];
    commitLabel = `Commit — Seed ${dry.to_update} records`;
    samples = (dry.sample_updates || []).map(u => ({
      code: u.code, title: u.title, updated_fields: [u.group],
    }));
  } else if (id === 'min_invitation_points') {
    const c = dry.counts || {};
    const cuts = dry.global_cutoffs || {};
    stats = [
      { icon: Award, label: '189 min (standard)',          value: cuts['189']?.min_points,                  tone: 'teal' },
      { icon: Award, label: '189 priority (Health/Edu)',   value: cuts['189_priority_health']?.min_points,  tone: 'gold' },
      { icon: Award, label: '491 family-sponsored',        value: cuts['491_family']?.min_points,           tone: 'gold' },
      { icon: ArrowRight, label: 'Tier 1+2 records tagged',value: c.tier_1_codes_tagged,                    tone: 'teal' },
    ];
    commitLabel = `Commit — Tag ${c.tier_1_codes_tagged} priority records`;
    samples = (dry.sample_updates || []).map(u => ({
      code: u.code, title: u.title, updated_fields: [`${u.tier}: ${u.min_189}pts`],
    }));
  } else if (id === 'dama') {
    const c = dry.counts || {};
    stats = [
      { icon: Database,    label: 'Total DAMAs',             value: dry.total_damas,         tone: 'teal' },
      { icon: ArrowRight,  label: 'Occupations to tag',      value: c.occupations_tagged,    tone: 'gold' },
      { icon: CheckCircle2, label: 'Verified preserved',     value: c.skipped_verified,      tone: 'teal' },
      { icon: AlertTriangle, label: 'Codes not in DB',       value: c.no_match_in_db,        tone: 'orange' },
    ];
    commitLabel = `Commit — Tag ${c.occupations_tagged} records`;
    samples = (dry.damas || []).slice(0, 6).map(d => ({
      code: d.id, title: d.region, updated_fields: [d.state, `until ${d.valid_until}`],
    }));
  } else if (id === 'ila') {
    const c = dry.counts || {};
    stats = [
      { icon: Database,    label: 'Total industries',        value: dry.total_ilas,          tone: 'teal' },
      { icon: ArrowRight,  label: 'Occupations to tag',      value: c.occupations_tagged,    tone: 'gold' },
      { icon: CheckCircle2, label: 'Verified preserved',     value: c.skipped_verified,      tone: 'teal' },
      { icon: AlertTriangle, label: 'Codes not in DB',       value: c.no_match_in_db,        tone: 'orange' },
    ];
    commitLabel = `Commit — Tag ${c.occupations_tagged} records`;
    samples = (dry.ilas || []).map(i => ({
      code: i.id, title: i.industry, updated_fields: [`${i.occupations_count} occupations`],
    }));
  }

  return (
    <div className="mt-4 rounded-md border p-3" style={{ background: C.bg, borderColor: C.tealWash2 }} data-testid={`scraper-${id}-dry-run-result`}>
      <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.orangeDeep, letterSpacing: '0.08em' }}>Dry-Run Preview</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        {stats?.map((s, i) => (
          <PreviewStat key={i} icon={s.icon} label={s.label} value={s.value} tone={s.tone} />
        ))}
      </div>
      {samples?.length > 0 && (
        <div>
          <p className="text-xs font-bold mb-2" style={{ color: C.tealDeep }}>Sample updates (first 8):</p>
          <div className="space-y-1">
            {samples.slice(0, 8).map((u, i) => (
              <div key={u.code + '-' + i} className="text-xs flex flex-wrap gap-2 items-baseline">
                <span className="font-mono font-bold" style={{ color: C.tealDeep }}>{u.code}</span>
                <span style={{ color: C.ink }}>{u.title}</span>
                <span style={{ color: C.muted }}>·</span>
                {(u.updated_fields || []).map(f => (
                  <span key={f} className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                        style={{ background: C.goldWash, color: C.orangeDeep }}>{f}</span>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="mt-3 pt-3 border-t" style={{ borderColor: C.border }}>
        <button
          onClick={onCommit}
          disabled={running}
          className="px-4 py-2 rounded-md font-bold text-xs flex items-center gap-2 shadow-sm disabled:opacity-50"
          style={{ background: C.teal, color: '#fff' }}
          data-testid={`scraper-${id}-commit-btn`}
        >
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {running ? 'Committing…' : commitLabel}
        </button>
      </div>
    </div>
  );
}


// ─── Step 5 — Manual Tools Tab (CSV Upload + AI Paste-Extract) ───────────────
function ManualToolsTab({ headers, onAfterCommit }) {
  return (
    <div className="space-y-6" data-testid="anz-audit-tools-tab">
      <div className="p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
        <p className="text-sm font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
          <FileText className="h-4 w-4" />Step 5 — Manual Tools for VIC · SA · ACT · NT · TAS · WA (sites that don&apos;t scrape)
        </p>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          In states ki nomination lists JS-driven hain ya scraping block karti hain. Aap official site se data copy karke
          neeche AI Paste-Extract me daal sakte hain, ya CSV file upload kar sakte hain.
          AI Claude Sonnet 4.6 ka use karke structured JSON nikalega — preview dekhke aap commit kar sakte hain.
        </p>
      </div>

      <CsvUploadCard headers={headers} onAfterCommit={onAfterCommit} />
      <AiExtractCard headers={headers} onAfterCommit={onAfterCommit} />
      <BulkStateExtractCard headers={headers} onAfterCommit={onAfterCommit} />
      <DamaIlaPdfCard headers={headers} onAfterCommit={onAfterCommit} />
    </div>
  );
}

function CsvUploadCard({ headers, onAfterCommit }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [overwrite, setOverwrite] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const downloadTemplate = async () => {
    try {
      const r = await axios.get(`${API}/anz-intel/bulk-upload-csv/template`, {
        headers, responseType: 'blob',
      });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'leamss_atlas_vetassess_template.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('Failed to download template: ' + (e.response?.data?.detail || e.message));
    }
  };

  const onFileChange = (e) => {
    setFile(e.target.files?.[0] || null);
    setPreview(null);
    setCommitResult(null);
  };

  const runPreview = async () => {
    if (!file) return;
    setLoadingPreview(true);
    setPreview(null);
    setCommitResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/anz-intel/bulk-upload-csv/preview`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setPreview(r.data);
    } catch (e) {
      setPreview({ error: e.response?.data?.detail || String(e) });
    }
    setLoadingPreview(false);
  };

  const runCommit = async () => {
    if (!file) return;
    if (!window.confirm(`Sir, confirm — ${preview?.matched_in_db || 0} records me data inject hoga. Proceed?`)) return;
    setCommitting(true);
    setCommitResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/anz-intel/bulk-upload-csv/commit?overwrite=${overwrite}`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setCommitResult(r.data);
      if (onAfterCommit) await onAfterCommit();
    } catch (e) {
      setCommitResult({ error: e.response?.data?.detail || String(e) });
    }
    setCommitting(false);
  };

  return (
    <div className="rounded-xl border bg-white p-4" style={{ borderColor: C.border }} data-testid="csv-upload-card">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2" style={{ color: C.ink }}>
            <FileText className="h-4 w-4" style={{ color: C.teal }} />Bulk CSV Upload
          </h3>
          <p className="text-xs mt-1" style={{ color: C.body }}>
            VETASSESS Group A-F, assessing body, criteria — sab ek baar me 1000+ records add kar sakte hain.
          </p>
        </div>
        <button
          onClick={downloadTemplate}
          className="px-3 py-1.5 rounded-md text-xs font-bold border"
          style={{ background: C.card, color: C.teal, borderColor: C.teal }}
          data-testid="csv-download-template"
        >
          Download Template CSV
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={onFileChange}
          className="text-xs"
          data-testid="csv-file-input"
        />
        <button
          onClick={runPreview}
          disabled={!file || loadingPreview}
          className="px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: C.teal, color: '#fff' }}
          data-testid="csv-preview-btn"
        >
          {loadingPreview ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          Preview
        </button>
        <label className="text-xs flex items-center gap-1.5" style={{ color: C.body }}>
          <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} data-testid="csv-overwrite" />
          Overwrite existing values (default: only fill empty)
        </label>
      </div>

      {preview && !preview.error && (
        <div className="mt-4 p-3 rounded-md" style={{ background: C.bg, border: `1px solid ${C.tealWash2}` }} data-testid="csv-preview-result">
          <p className="text-xs font-bold uppercase mb-2" style={{ color: C.tealDeep }}>Preview Summary</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <PreviewStat icon={Database}     label="Total rows"      value={preview.total_rows} tone="teal" />
            <PreviewStat icon={CheckCircle2} label="Valid"            value={preview.valid_rows} tone="teal" />
            <PreviewStat icon={ArrowRight}   label="Matched in DB"   value={preview.matched_in_db} tone="gold" />
            <PreviewStat icon={AlertTriangle} label="Unmatched codes" value={(preview.unmatched_codes || []).length} tone="orange" />
          </div>
          {preview.invalid_rows?.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs font-bold cursor-pointer" style={{ color: C.red }}>
                {preview.invalid_rows.length} invalid rows
              </summary>
              <ul className="text-[10px] mt-1 ml-4 list-disc" style={{ color: C.body }}>
                {preview.invalid_rows.slice(0, 8).map((r, i) => (
                  <li key={i}>Row {r.row}: {r.reason} (code: <code>{r.code || '—'}</code>)</li>
                ))}
              </ul>
            </details>
          )}
          <button
            onClick={runCommit}
            disabled={committing || preview.matched_in_db === 0}
            className="mt-3 px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
            style={{ background: C.teal, color: '#fff' }}
            data-testid="csv-commit-btn"
          >
            {committing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Commit — Update {preview.matched_in_db} records
          </button>
        </div>
      )}
      {preview?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Preview failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{preview.error}</p>
        </div>
      )}
      {commitResult && !commitResult.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="csv-commit-result">
          <p className="text-sm font-bold" style={{ color: C.tealDeep }}>
            <CheckCircle2 className="h-4 w-4 inline mr-1" />Commit complete · {commitResult.updated} updated · {commitResult.skipped_verified} verified preserved · {commitResult.skipped_unknown_code} unknown codes skipped
          </p>
        </div>
      )}
      {commitResult?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Commit failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{commitResult.error}</p>
        </div>
      )}
    </div>
  );
}

function AiExtractCard({ headers, onAfterCommit }) {
  const [code, setCode] = useState('');
  const [rawText, setRawText] = useState('');
  const [intent, setIntent] = useState('vetassess_group');
  const [previewing, setPreviewing] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [overwrite, setOverwrite] = useState(false);

  const runPreview = async () => {
    if (!code || !rawText) return;
    setPreviewing(true);
    setExtracted(null);
    setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/ai-extract/preview`, {
        code: code.trim(), raw_text: rawText.trim(), intent,
      }, { headers });
      setExtracted(r.data);
    } catch (e) {
      setExtracted({ error: e.response?.data?.detail || String(e) });
    }
    setPreviewing(false);
  };

  const runCommit = async () => {
    if (!extracted?.extracted) return;
    if (!window.confirm(`Sir, confirm — code ${code} me ${intent} data inject hoga. Proceed?`)) return;
    setCommitting(true);
    setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/ai-extract/commit`, {
        code: code.trim(), intent, extracted: extracted.extracted, overwrite,
      }, { headers });
      setCommitResult(r.data);
      if (onAfterCommit) await onAfterCommit();
    } catch (e) {
      setCommitResult({ error: e.response?.data?.detail || String(e) });
    }
    setCommitting(false);
  };

  return (
    <div className="rounded-xl border bg-white p-4" style={{ borderColor: C.border }} data-testid="ai-extract-card">
      <div className="mb-3">
        <h3 className="text-base font-bold flex items-center gap-2" style={{ color: C.ink }}>
          <Sparkles className="h-4 w-4" style={{ color: C.gold }} />AI Paste-Extract (Claude Sonnet 4.6)
        </h3>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Official migration site se text copy karke yahaan paste karein. AI structured JSON nikalega — Group A-F, ACS rules, ya state nomination eligibility.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div>
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>6-digit ANZSCO Code</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g., 261313"
            className="w-full px-3 py-2 rounded border text-sm font-mono"
            style={{ borderColor: C.border }}
            data-testid="ai-extract-code"
          />
        </div>
        <div className="md:col-span-2">
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Extraction Intent</label>
          <select
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: C.border }}
            data-testid="ai-extract-intent"
          >
            <option value="vetassess_group">VETASSESS Group A-F (qualification + experience)</option>
            <option value="acs_rules">ACS classification rules (ICT Major/Minor/Non-ICT)</option>
            <option value="state_nomination">State nomination (190/491 eligibility + demand)</option>
          </select>
        </div>
      </div>

      <div className="mb-3">
        <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Raw Text (paste from official site)</label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Paste content here — e.g. VETASSESS occupation criteria, NSW skills list entry, ACS skill assessment guide…"
          className="w-full px-3 py-2 rounded border text-xs font-mono"
          style={{ borderColor: C.border, minHeight: 140 }}
          data-testid="ai-extract-raw-text"
        />
        <p className="text-[10px] mt-1" style={{ color: C.muted }}>{rawText.length} chars · max 8000 sent to AI</p>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={runPreview}
          disabled={!code || !rawText || previewing}
          className="px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
          style={{ background: C.teal, color: '#fff' }}
          data-testid="ai-extract-preview-btn"
        >
          {previewing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {previewing ? 'AI working…' : 'AI Extract Preview'}
        </button>
        <label className="text-xs flex items-center gap-1.5" style={{ color: C.body }}>
          <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} data-testid="ai-overwrite" />
          Overwrite verified records
        </label>
      </div>

      {extracted && !extracted.error && (
        <div className="mt-4 p-3 rounded-md" style={{ background: C.bg, border: `1px solid ${C.tealWash2}` }} data-testid="ai-extract-result">
          <p className="text-xs font-bold uppercase mb-2" style={{ color: C.tealDeep }}>
            AI Extracted Data · {extracted.intent}
          </p>
          <pre className="text-[11px] p-3 rounded overflow-x-auto" style={{ background: '#fff', color: C.ink, border: `1px solid ${C.border}` }}>
{JSON.stringify(extracted.extracted, null, 2)}
          </pre>
          <button
            onClick={runCommit}
            disabled={committing}
            className="mt-3 px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
            style={{ background: C.teal, color: '#fff' }}
            data-testid="ai-extract-commit-btn"
          >
            {committing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Commit to {code}
          </button>
        </div>
      )}
      {extracted?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>AI extraction failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{extracted.error}</p>
        </div>
      )}
      {commitResult && !commitResult.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="ai-extract-commit-result">
          <p className="text-sm font-bold" style={{ color: C.tealDeep }}>
            <CheckCircle2 className="h-4 w-4 inline mr-1" />
            Saved to {commitResult.code} · fields: {(commitResult.updated_fields || []).join(', ')}
          </p>
        </div>
      )}
      {commitResult?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Commit failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{commitResult.error}</p>
        </div>
      )}
    </div>
  );
}


// ─── Phase 9.6 — Bulk State Nomination AI Extract (VIC/SA/ACT/NT/TAS/WA) ─────
function BulkStateExtractCard({ headers, onAfterCommit }) {
  const [state, setState] = useState('VIC');
  const [sourceUrl, setSourceUrl] = useState('');
  const [rawText, setRawText] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  const runPreview = async () => {
    if (!state || !rawText) return;
    setPreviewing(true); setPreview(null); setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/ai-extract-state-bulk/preview`, {
        state, source_url: sourceUrl, raw_text: rawText,
      }, { headers });
      setPreview(r.data);
    } catch (e) {
      setPreview({ error: e.response?.data?.detail || String(e) });
    }
    setPreviewing(false);
  };

  const runCommit = async () => {
    if (!preview?.records?.length) return;
    if (!window.confirm(`Sir, confirm — ${state} state nomination tag honga ${preview.matched_count} matched records par. Proceed?`)) return;
    setCommitting(true); setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/ai-extract-state-bulk/commit`, {
        state, source_url: sourceUrl, records: preview.records,
      }, { headers });
      setCommitResult(r.data);
      if (onAfterCommit) await onAfterCommit();
    } catch (e) {
      setCommitResult({ error: e.response?.data?.detail || String(e) });
    }
    setCommitting(false);
  };

  return (
    <div className="rounded-xl border bg-white p-4" style={{ borderColor: C.border }} data-testid="bulk-state-extract-card">
      <div className="mb-3">
        <h3 className="text-base font-bold flex items-center gap-2" style={{ color: C.ink }}>
          <Sparkles className="h-4 w-4" style={{ color: C.gold }} />
          Bulk State Nomination AI Extract (VIC · SA · ACT · NT · TAS · WA)
        </h3>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Aap official state migration site (VIC / SA / ACT / NT / TAS / WA) ka content paste karein.
          AI saare occupations + 190/491 eligibility extract karke matched records par tag kar dega — including 4-digit unit-group expansion.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div>
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>State</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm font-mono"
            style={{ borderColor: C.border }}
            data-testid="bulk-state-select"
          >
            {['VIC', 'SA', 'ACT', 'NT', 'TAS', 'WA', 'NSW', 'QLD'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Official Source URL (for audit)</label>
          <input
            type="text"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://liveinmelbourne.vic.gov.au/migrate"
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: C.border }}
            data-testid="bulk-state-source"
          />
        </div>
      </div>

      <div className="mb-3">
        <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Raw text from official site</label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Paste the full occupation list page content here (e.g., 'Software Engineer 261313 - eligible for 190 and 491 - high demand...')"
          className="w-full px-3 py-2 rounded border text-xs font-mono"
          style={{ borderColor: C.border, minHeight: 160 }}
          data-testid="bulk-state-raw"
        />
        <p className="text-[10px] mt-1" style={{ color: C.muted }}>{rawText.length} chars · max 12000 sent to AI</p>
      </div>

      <button
        onClick={runPreview}
        disabled={!rawText || previewing}
        className="px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
        style={{ background: C.teal, color: '#fff' }}
        data-testid="bulk-state-preview-btn"
      >
        {previewing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
        {previewing ? 'AI extracting…' : 'AI Extract Preview'}
      </button>

      {preview && !preview.error && (
        <div className="mt-4 p-3 rounded-md" style={{ background: C.bg, border: `1px solid ${C.tealWash2}` }} data-testid="bulk-state-preview-result">
          <p className="text-xs font-bold uppercase mb-2" style={{ color: C.tealDeep }}>Bulk Extract Preview · {preview.state}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <PreviewStat icon={Database}      label="Total extracted"      value={preview.total_extracted} tone="teal" />
            <PreviewStat icon={CheckCircle2}  label="Matched in DB"         value={preview.matched_count}   tone="gold" />
            <PreviewStat icon={AlertTriangle} label="Unmatched"             value={preview.unmatched_count} tone="orange" />
            <PreviewStat icon={ArrowRight}    label="4-digit expansions"    value={preview.unit_group_expansions?.length || 0} tone="teal" />
          </div>
          {preview.records?.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-bold" style={{ color: C.tealDeep }}>Matched records (first 10):</p>
              {preview.records.slice(0, 10).map((r, i) => (
                <div key={i} className="text-xs flex flex-wrap gap-2 items-baseline">
                  <span className="font-mono font-bold" style={{ color: C.tealDeep }}>
                    {r.matched_code || r.matched_unit_group}
                  </span>
                  <span style={{ color: C.ink }}>{r.title}</span>
                  {r.sc190 && <Badge style={{ background: C.tealWash2, color: C.tealDeep, fontSize: 9 }}>190</Badge>}
                  {r.sc491 && <Badge style={{ background: C.goldWash, color: C.orangeDeep, fontSize: 9 }}>491</Badge>}
                  {r.demand && <span className="text-[10px]" style={{ color: C.muted }}>· {r.demand}</span>}
                  {r.match_type === '4_digit_expanded' && <span className="text-[10px]" style={{ color: C.orange }}>· expand to {r.child_count}</span>}
                </div>
              ))}
            </div>
          )}
          <button
            onClick={runCommit}
            disabled={committing || preview.matched_count === 0}
            className="mt-3 px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
            style={{ background: C.teal, color: '#fff' }}
            data-testid="bulk-state-commit-btn"
          >
            {committing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Commit — Tag {preview.matched_count} records with {state} nomination
          </button>
        </div>
      )}
      {preview?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Preview failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{preview.error}</p>
        </div>
      )}
      {commitResult && !commitResult.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="bulk-state-commit-result">
          <p className="text-sm font-bold" style={{ color: C.tealDeep }}>
            <CheckCircle2 className="h-4 w-4 inline mr-1" />
            {commitResult.updates_6_digit_exact} exact + {commitResult.updates_4_digit_expanded} via 4-digit expansion · {commitResult.skipped_verified} verified preserved
          </p>
        </div>
      )}
    </div>
  );
}


// ─── Phase 9.6 — DAMA / ILA PDF Upload ──────────────────────────────────────
function DamaIlaPdfCard({ headers, onAfterCommit }) {
  const [targetType, setTargetType] = useState('dama');
  const [targetId, setTargetId] = useState('nt');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState({});
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  const damaOptions = [
    { id: 'nt', name: 'NT — Northern Territory' },
    { id: 'goldfields', name: 'WA — Goldfields' },
    { id: 'fnq', name: 'QLD — Far North Queensland' },
    { id: 'east_kimberley', name: 'WA — East Kimberley' },
    { id: 'pilbara', name: 'WA — Pilbara' },
    { id: 'sw_wa', name: 'WA — South West' },
    { id: 'orana_nsw', name: 'NSW — Orana' },
    { id: 'adelaide_tech', name: 'SA — Adelaide Tech & Innovation' },
    { id: 'sa_regional', name: 'SA — Regional' },
    { id: 'townsville', name: 'QLD — Townsville' },
    { id: 'hobart_city', name: 'TAS — Hobart City' },
    { id: 'great_south_coast', name: 'VIC — Great South Coast' },
    { id: 'aerotropolis', name: 'NSW — Western Sydney Aerotropolis' },
  ];
  const ilaOptions = [
    { id: 'restaurant', name: 'Restaurant (Premium Dining)' },
    { id: 'meat', name: 'Meat Industry' },
    { id: 'aged_care', name: 'Aged Care' },
    { id: 'fishing', name: 'Fishing' },
  ];
  const opts = targetType === 'dama' ? damaOptions : ilaOptions;

  const runPreview = async () => {
    if (!file) return;
    setPreviewing(true); setPreview(null); setCommitResult(null); setSelectedCodes({});
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await axios.post(
        `${API}/anz-intel/dama-pdf/preview?target_id=${targetId}&target_type=${targetType}`,
        fd, { headers: { ...headers, 'Content-Type': 'multipart/form-data' } }
      );
      setPreview(r.data);
      // Pre-select all NOT already tagged
      const initial = {};
      for (const m of (r.data.matched_in_db || [])) {
        initial[m.code] = !m.already_tagged_with_target;
      }
      setSelectedCodes(initial);
    } catch (e) {
      setPreview({ error: e.response?.data?.detail || String(e) });
    }
    setPreviewing(false);
  };

  const runCommit = async () => {
    const codes = Object.entries(selectedCodes).filter(([_, v]) => v).map(([k]) => k);
    if (!codes.length) return;
    if (!window.confirm(`Sir, confirm — ${codes.length} codes ko ${targetType.toUpperCase()} "${targetId}" se tag karein. Proceed?`)) return;
    setCommitting(true); setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/dama-pdf/commit`, {
        target_id: targetId, target_type: targetType, codes,
        source: preview?.filename || 'uploaded.pdf',
      }, { headers });
      setCommitResult(r.data);
      if (onAfterCommit) await onAfterCommit();
    } catch (e) {
      setCommitResult({ error: e.response?.data?.detail || String(e) });
    }
    setCommitting(false);
  };

  return (
    <div className="rounded-xl border bg-white p-4" style={{ borderColor: C.border }} data-testid="dama-ila-pdf-card">
      <div className="mb-3">
        <h3 className="text-base font-bold flex items-center gap-2" style={{ color: C.ink }}>
          <FileText className="h-4 w-4" style={{ color: C.teal }} />DAMA · ILA PDF Upload &amp; Extract
        </h3>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Official DAMA / ILA PDF agreement upload karein. PDF se 6-digit ANZSCO codes extract honge.
          Aap preview dekhke select karein, fir matched DAMA / ILA ke saath tag kar dein.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div>
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Type</label>
          <select
            value={targetType}
            onChange={(e) => { setTargetType(e.target.value); setTargetId(e.target.value === 'dama' ? 'nt' : 'restaurant'); }}
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: C.border }}
            data-testid="dama-ila-type"
          >
            <option value="dama">DAMA (13 options)</option>
            <option value="ila">ILA (4 industries)</option>
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>{targetType.toUpperCase()} Agreement</label>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: C.border }}
            data-testid="dama-ila-target-id"
          >
            {opts.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap mb-2">
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-xs"
          data-testid="dama-ila-file"
        />
        <button
          onClick={runPreview}
          disabled={!file || previewing}
          className="px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: C.teal, color: '#fff' }}
          data-testid="dama-ila-preview-btn"
        >
          {previewing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          Extract Codes
        </button>
      </div>

      {preview && !preview.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.bg, border: `1px solid ${C.tealWash2}` }} data-testid="dama-ila-preview-result">
          <p className="text-xs font-bold uppercase mb-2" style={{ color: C.tealDeep }}>PDF Preview · {preview.target_type}/{preview.target_id}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <PreviewStat icon={Database}      label="PDF pages"            value={preview.pdf_pages} tone="teal" />
            <PreviewStat icon={Database}      label="Codes extracted"      value={preview.total_codes_extracted} tone="teal" />
            <PreviewStat icon={CheckCircle2}  label="Matched in DB"        value={preview.matched_in_db?.length || 0} tone="gold" />
            <PreviewStat icon={AlertTriangle} label="Unmatched codes"      value={preview.unmatched_codes?.length || 0} tone="orange" />
          </div>
          {preview.matched_in_db?.length > 0 && (
            <div className="space-y-1 max-h-72 overflow-y-auto p-2 rounded" style={{ background: '#fff' }}>
              {preview.matched_in_db.map((m, i) => (
                <label key={i} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 p-1 rounded" data-testid={`dama-ila-code-${m.code}`}>
                  <input
                    type="checkbox"
                    checked={!!selectedCodes[m.code]}
                    onChange={(e) => setSelectedCodes(prev => ({ ...prev, [m.code]: e.target.checked }))}
                  />
                  <span className="font-mono font-bold" style={{ color: C.tealDeep }}>{m.code}</span>
                  <span style={{ color: C.ink }}>{m.title}</span>
                  {m.already_tagged_with_target && (
                    <Badge style={{ background: C.goldWash, color: C.orangeDeep, fontSize: 9 }}>already tagged</Badge>
                  )}
                  {m.status === 'verified' && (
                    <Badge style={{ background: C.redWash, color: C.red, fontSize: 9 }}>verified (skip)</Badge>
                  )}
                </label>
              ))}
            </div>
          )}
          <button
            onClick={runCommit}
            disabled={committing || Object.values(selectedCodes).every(v => !v)}
            className="mt-3 px-4 py-2 rounded-md text-xs font-bold flex items-center gap-2 disabled:opacity-50"
            style={{ background: C.teal, color: '#fff' }}
            data-testid="dama-ila-commit-btn"
          >
            {committing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Tag {Object.values(selectedCodes).filter(v => v).length} selected codes
          </button>
        </div>
      )}
      {preview?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Preview failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{preview.error}</p>
        </div>
      )}
      {commitResult && !commitResult.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="dama-ila-commit-result">
          <p className="text-sm font-bold" style={{ color: C.tealDeep }}>
            <CheckCircle2 className="h-4 w-4 inline mr-1" />
            Tagged {commitResult.updated} records · {commitResult.skipped_verified} verified preserved
          </p>
        </div>
      )}
      {commitResult?.error && (
        <div className="mt-3 p-3 rounded-md" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>Commit failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{commitResult.error}</p>
        </div>
      )}
    </div>
  );
}
