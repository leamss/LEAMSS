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
  GitMerge, ArrowRight,
} from 'lucide-react';

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

  useEffect(() => { fetchAll(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [statusFilter, searchTxt]);

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
      {activeTab === 'scrapers' && <ScrapersTab headers={headers} />}
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
              Aap "Refresh" karke baad me result verify kar sakte hain.
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
function ScrapersTab({ headers }) {
  const [scrapers, setScrapers] = useState([]);
  const [dryRun, setDryRun] = useState(null);
  const [running, setRunning] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  useEffect(() => {
    axios.get(`${API}/anz-intel/scrapers/list`, { headers })
      .then(r => setScrapers(r.data.scrapers || []))
      .catch(e => console.error('scrapers/list', e));
  }, [headers]);

  const runDry = async () => {
    setRunning(true); setDryRun(null); setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/scrapers/home-affairs/run?dry_run=true`, {}, { headers });
      setDryRun(r.data);
    } catch (e) {
      setDryRun({ error: e.response?.data?.detail || String(e) });
    }
    setRunning(false);
  };

  const runCommit = async () => {
    if (!window.confirm(`Sir, confirm — Home Affairs scraper se ${dryRun?.ha_codes_with_changes} records enrich honge (assessing authority + visa eligibility + MLTSSL/STSOL/ROL). Existing verified records preserved. Proceed?`)) return;
    setRunning(true); setCommitResult(null);
    try {
      const r = await axios.post(`${API}/anz-intel/scrapers/home-affairs/run?dry_run=false`, {}, { headers });
      setCommitResult(r.data);
    } catch (e) {
      setCommitResult({ error: e.response?.data?.detail || String(e) });
    }
    setRunning(false);
  };

  return (
    <div data-testid="anz-audit-scrapers-tab">
      <div className="mb-4 p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
        <p className="text-sm font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
          <Sparkles className="h-4 w-4" />Step 4 — Live Scrapers (Slow &amp; Careful)
        </p>
        <p className="text-xs mt-1" style={{ color: C.body }}>
          Har scraper run karne se pehle <b>DRY-RUN preview</b> dikhega. Aap dekhke confirm kar sakte hain,
          fir actual commit hoga. Verified records kabhi auto-overwrite nahi honge.
        </p>
      </div>

      {/* Scrapers list */}
      <div className="space-y-4 mb-6">
        {scrapers.map(s => (
          <div key={s.id} className="rounded-xl border p-4" style={{ background: C.card, borderColor: C.border }} data-testid={`scraper-${s.id}`}>
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-bold text-base" style={{ color: C.ink }}>{s.name}</h3>
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded"
                        style={{
                          background: s.status === 'ready' ? C.tealWash2 : C.orangeWash2,
                          color:      s.status === 'ready' ? C.tealDeep : C.orangeDeep,
                        }}>
                    {s.status}
                  </span>
                </div>
                <a href={s.source_url} target="_blank" rel="noreferrer" className="text-xs underline" style={{ color: C.teal }}>
                  {s.source_url}
                </a>
                <ul className="mt-2 space-y-0.5 text-xs" style={{ color: C.body }}>
                  {s.what_it_provides.map((w, i) => (
                    <li key={i}>→ {w}</li>
                  ))}
                </ul>
                {s.note && <p className="mt-2 text-xs italic" style={{ color: C.orangeDeep }}>{s.note}</p>}
              </div>
              {s.status === 'ready' && s.id === 'home_affairs' && (
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={runDry}
                    disabled={running}
                    className="px-3 py-1.5 rounded-md text-xs font-bold border flex items-center gap-1.5 transition-colors"
                    style={{ background: C.card, color: C.teal, borderColor: C.teal }}
                    data-testid={`scraper-${s.id}-dry-run-btn`}
                  >
                    {running && !dryRun ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                    Dry-Run Preview
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Dry-run preview */}
      {dryRun && !dryRun.error && (
        <div className="rounded-xl border p-5 mb-4" style={{ background: C.card, borderColor: C.tealWash2 }} data-testid="ha-dry-run-result">
          <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.orangeDeep, letterSpacing: '0.08em' }}>Dry-Run Preview · Home Affairs</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <PreviewStat icon={Database}     label="Fetched"               value={dryRun.fetched_records} tone="teal" />
            <PreviewStat icon={ArrowRight}   label="Will Update"           value={dryRun.ha_codes_with_changes} tone="gold" />
            <PreviewStat icon={CheckCircle2} label="Verified preserved"    value={dryRun.skipped_verified} tone="teal" />
            <PreviewStat icon={AlertTriangle} label="HA codes not in DB"    value={dryRun.ha_codes_not_in_db} tone="orange" />
          </div>
          {dryRun.sample_updates?.length > 0 && (
            <div>
              <p className="text-xs font-bold mb-2" style={{ color: C.tealDeep }}>Sample updates (first 8):</p>
              <div className="space-y-1">
                {dryRun.sample_updates.map(u => (
                  <div key={u.code} className="text-xs flex flex-wrap gap-2 items-baseline">
                    <span className="font-mono font-bold" style={{ color: C.tealDeep }}>{u.code}</span>
                    <span style={{ color: C.ink }}>{u.title}</span>
                    <span style={{ color: C.muted }}>· fields:</span>
                    {u.updated_fields.map(f => (
                      <span key={f} className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                            style={{ background: C.goldWash, color: C.orangeDeep }}>{f}</span>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="mt-4 pt-4 border-t" style={{ borderColor: C.border }}>
            <button
              onClick={runCommit}
              disabled={running || dryRun.ha_codes_with_changes === 0}
              className="px-5 py-2.5 rounded-md font-bold text-sm flex items-center gap-2 shadow-sm disabled:opacity-50"
              style={{ background: C.teal, color: '#fff' }}
              data-testid="ha-commit-btn"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {running ? 'Committing…' : `Commit — Update ${dryRun.ha_codes_with_changes} records`}
            </button>
          </div>
        </div>
      )}
      {dryRun?.error && (
        <div className="p-4 rounded-lg mb-4" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>❌ Dry-run failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{dryRun.error}</p>
        </div>
      )}

      {/* Commit result */}
      {commitResult && !commitResult.error && (
        <div className="p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }} data-testid="ha-commit-result">
          <p className="text-base font-bold flex items-center gap-2" style={{ color: C.tealDeep }}>
            <CheckCircle2 className="h-5 w-5" />Scrape complete!
          </p>
          <ul className="mt-3 text-sm space-y-1" style={{ color: C.body }}>
            <li><strong>{commitResult.ha_codes_with_changes}</strong> records updated with Home Affairs data</li>
            <li><strong>{commitResult.skipped_verified}</strong> verified records preserved (no overwrite)</li>
            <li><strong>{commitResult.ha_codes_not_in_db}</strong> Home Affairs codes not yet in LEAMSS DB</li>
            <li className="text-xs mt-2" style={{ color: C.muted }}>Source: {commitResult.source_url}</li>
            <li className="text-xs" style={{ color: C.muted }}>Ran at: {commitResult.ran_at}</li>
          </ul>
        </div>
      )}
      {commitResult?.error && (
        <div className="p-4 rounded-lg" style={{ background: C.redWash, border: '1px solid #FCA5A5' }}>
          <p className="text-sm font-bold" style={{ color: C.red }}>❌ Commit failed</p>
          <p className="text-xs mt-1" style={{ color: C.body }}>{commitResult.error}</p>
        </div>
      )}
    </div>
  );
}
