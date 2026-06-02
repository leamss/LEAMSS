/**
 * Phase 9 — ANZSCO Intelligence Audit Dashboard
 *
 * READ-ONLY admin page that visualizes the EXACT coverage gap between
 * the 1,236 anzsco_4digit_master records and the 79 AU occupation_master
 * detail entries.
 *
 * Inspired by anzscosearch.com — but powered by LEAMSS data.
 *
 * Route: /admin/anz-intel/audit
 */
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  Database, AlertTriangle, CheckCircle2, FileText, MapPin, Briefcase,
  Building2, Award, Globe2, Layers, Sparkles, RefreshCw, Search, Loader2,
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

      const [s, r, o] = await Promise.all([
        axios.get(`${API}/anz-intel/audit-summary`, { headers }),
        axios.get(`${API}/anz-intel/audit-rows?${params}`, { headers }),
        axios.get(`${API}/anz-intel/orphans-4digit?limit=50`, { headers }),
      ]);
      setSummary(s.data);
      setRows(r.data.items || []);
      setOrphans(o.data.items || []);
    } catch (e) { console.error('audit fetch', e); }
    setRefreshing(false);
    setLoading(false);
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
              Phase 9 · ANZSCO Intelligence
            </p>
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: C.tealDark, fontFamily: "'Playfair Display', serif" }}>
              Coverage Audit Dashboard
            </h1>
            <p className="text-sm mt-2 max-w-2xl" style={{ color: C.body }}>
              Read-only diagnostic: kahan kya data hai, kya missing hai, scrapers kahan se laayenge. Reference benchmark:{' '}
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
      <nav className="flex gap-1 mb-6 border-b" style={{ borderColor: C.border }} data-testid="anz-audit-tabs">
        {[
          { key: 'coverage',  label: 'Field Coverage',  icon: Award },
          { key: 'rows',      label: 'Per-Occupation Heatmap', icon: Layers },
          { key: 'orphans',   label: 'Orphan 4-digit Groups',  icon: AlertTriangle },
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
