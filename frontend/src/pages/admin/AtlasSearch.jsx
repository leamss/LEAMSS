/**
 * Phase 9 — LEAMSS Migration Atlas · Search UI
 *
 * Single-page application for LEAMSS Sales/Partner/Admin to search the
 * 932 AU 6-digit ANZSCO occupations across 4 modes:
 *   1) Code / Title
 *   2) Multisearch (compare up to 8 occupations)
 *   3) By State / Territory
 *   4) By Task (semantic)
 *
 * Click an occupation card → detail drawer with full profile + siblings.
 *
 * Inspired by anzscosearch.com — powered by LEAMSS data.
 *
 * Route: /admin/atlas/search
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Search, MapPin, Briefcase, Layers, Globe2, FileText, Loader2,
  X, ChevronRight, Building2, DollarSign, Users, Sparkles, ListChecks,
  Download, ArrowRight, BookOpen,
} from 'lucide-react';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose,
} from '@/components/ui/sheet';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// LEAMSS brand palette
const C = {
  bg:          '#FAFAF9', card: '#FFFFFF', border: '#E5E7EB', borderSoft: '#F1F5F9',
  ink:         '#1F2937', body: '#475569', muted: '#94A3B8',
  teal:        '#0F766E', tealDeep: '#115E59', tealDark: '#134E4A',
  tealWash:    '#F0FDFA', tealWash2: '#CCFBF1',
  orange:      '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED', orangeWash2: '#FFEDD5',
  red:         '#D32F2F', redWash:    '#FEE2E2',
  gold:        '#D4A017', goldLight:  '#FBBF24', goldWash:   '#FEF3C7',
};

const STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'];

const MODE_DEF = [
  { key: 'code_title', label: 'Code / Title',  icon: Search,    desc: 'Search by ANZSCO code or job title' },
  { key: 'multi',      label: 'Multisearch',   icon: Layers,    desc: 'Compare 2-8 occupations side-by-side' },
  { key: 'state',      label: 'By State',      icon: MapPin,    desc: 'Browse occupations by state demand' },
  { key: 'task',       label: 'By Task',       icon: Briefcase, desc: 'Semantic search across job tasks' },
];

export default function AtlasSearch() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('code_title');
  const [q, setQ] = useState('');
  const [stateFilter, setStateFilter] = useState('NSW');
  const [multiCodes, setMultiCodes] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCode, setSelectedCode] = useState(null);
  const [detail, setDetail] = useState(null);

  const headers = useMemo(() => {
    const t = localStorage.getItem('token');
    return t ? { Authorization: `Bearer ${t}` } : {};
  }, []);

  const runSearch = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ mode, limit: '60' });
      if (mode === 'code_title' || mode === 'task') {
        if (q) params.set('q', q); else { setResults([]); setLoading(false); return; }
      } else if (mode === 'state') {
        params.set('state', stateFilter);
      } else if (mode === 'multi') {
        if (multiCodes.length === 0) { setResults([]); setLoading(false); return; }
        params.set('codes', multiCodes.join(','));
      }
      const r = await axios.get(`${API}/anz-intel/search?${params}`, { headers });
      setResults(r.data.items || []);
    } catch (e) { console.error('search', e); }
    setLoading(false);
  }, [mode, q, stateFilter, multiCodes, headers]);

  // Auto-search on mode change or filter change
  useEffect(() => {
    if (mode === 'state' || (mode === 'code_title' && !q)) runSearch();
    if (mode === 'multi' && multiCodes.length > 0) runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, stateFilter]);

  // Debounced search on q change (code_title / task modes)
  useEffect(() => {
    if (mode === 'code_title' || mode === 'task') {
      const t = setTimeout(() => runSearch(), 350);
      return () => clearTimeout(t);
    }
  }, [q, mode, runSearch]);

  // Detail fetcher
  useEffect(() => {
    if (!selectedCode) { setDetail(null); return; }
    (async () => {
      try {
        const r = await axios.get(`${API}/anz-intel/occupation/${selectedCode}`, { headers });
        setDetail(r.data);
      } catch (e) { console.error('detail', e); }
    })();
  }, [selectedCode, headers]);

  const toggleMultiCode = (code) => {
    setMultiCodes(prev => prev.includes(code)
      ? prev.filter(c => c !== code)
      : prev.length < 8 ? [...prev, code] : prev);
  };

  return (
    <div className="min-h-screen p-6 lg:p-10" style={{ background: C.bg, fontFamily: "'Manrope', sans-serif" }} data-testid="atlas-search-root">
      {/* HEADER */}
      <header className="mb-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.orange, letterSpacing: '0.14em' }}>
              Phase 9 · LEAMSS Migration Atlas
            </p>
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: C.tealDark, fontFamily: "'Playfair Display', serif" }}>
              Occupation Search
            </h1>
            <p className="text-sm mt-1" style={{ color: C.body }}>
              <strong>932</strong> Australian occupations · ABS ANZSCO Feb 2026 · refreshes weekly
            </p>
          </div>
          <button
            onClick={() => navigate('/admin/anz-intel/audit')}
            className="px-3 py-2 rounded-md text-xs font-bold flex items-center gap-2 border transition-colors"
            style={{ background: C.card, color: C.body, borderColor: C.border }}
            data-testid="atlas-back-to-audit"
          >
            <BookOpen className="h-3.5 w-3.5" />Coverage Audit
          </button>
        </div>
      </header>

      {/* MODE TABS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="atlas-search-modes">
        {MODE_DEF.map(m => (
          <button
            key={m.key}
            onClick={() => { setMode(m.key); setResults([]); setQ(''); }}
            className="text-left p-4 rounded-xl border transition-all hover:shadow-md"
            style={{
              background:  mode === m.key ? C.tealWash : C.card,
              borderColor: mode === m.key ? C.teal : C.border,
              boxShadow:   mode === m.key ? `0 0 0 3px ${C.tealWash2}` : 'none',
            }}
            data-testid={`atlas-mode-${m.key}`}
          >
            <m.icon className="h-5 w-5 mb-2" style={{ color: mode === m.key ? C.teal : C.muted }} />
            <p className="font-bold text-sm" style={{ color: mode === m.key ? C.tealDeep : C.ink }}>{m.label}</p>
            <p className="text-[10px] mt-1" style={{ color: C.muted }}>{m.desc}</p>
          </button>
        ))}
      </div>

      {/* MODE-SPECIFIC INPUT */}
      <div className="mb-6">
        {(mode === 'code_title' || mode === 'task') && (
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={mode === 'code_title' ? 'Type code (eg 261313) or title (eg Software Engineer)…' : 'Describe a task (eg "developing software", "patient care")…'}
              className="w-full pl-10 pr-4 py-3 rounded-lg border text-base outline-none focus:ring-2"
              style={{ background: C.card, borderColor: C.border, color: C.ink, '--tw-ring-color': C.teal }}
              data-testid="atlas-search-input"
            />
          </div>
        )}
        {mode === 'state' && (
          <div className="flex gap-2 flex-wrap" data-testid="atlas-state-tabs">
            {STATES.map(s => (
              <button
                key={s}
                onClick={() => setStateFilter(s)}
                className="px-4 py-2 rounded-md font-bold text-sm border transition-all"
                style={{
                  background:  stateFilter === s ? C.teal : C.card,
                  borderColor: stateFilter === s ? C.teal : C.border,
                  color:       stateFilter === s ? '#fff' : C.body,
                }}
                data-testid={`atlas-state-${s}`}
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {mode === 'multi' && (
          <div className="p-4 rounded-lg border" style={{ background: C.orangeWash, borderColor: C.orangeWash2 }}>
            <p className="text-sm font-bold" style={{ color: C.orangeDeep }}>
              {multiCodes.length === 0
                ? 'Add codes for comparison: use "Code / Title" mode → click "+ Compare" on each card.'
                : `${multiCodes.length} occupation(s) selected — see comparison below.`}
            </p>
            {multiCodes.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {multiCodes.map(c => (
                  <span key={c} className="text-xs px-2 py-1 rounded font-mono font-bold flex items-center gap-1"
                        style={{ background: C.card, color: C.tealDeep, border: `1px solid ${C.tealWash2}` }}>
                    {c}
                    <X className="h-3 w-3 cursor-pointer" onClick={() => toggleMultiCode(c)} />
                  </span>
                ))}
                <button onClick={() => setMultiCodes([])} className="text-xs underline" style={{ color: C.red }}>Clear all</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* RESULTS */}
      <div data-testid="atlas-results">
        {loading && <p className="flex items-center gap-2 text-sm" style={{ color: C.muted }}><Loader2 className="h-4 w-4 animate-spin" />Searching…</p>}
        {!loading && results.length === 0 && (
          <div className="text-center py-12 rounded-xl border" style={{ background: C.card, borderColor: C.border }}>
            <Globe2 className="h-10 w-10 mx-auto mb-3" style={{ color: C.muted }} />
            <p className="text-sm" style={{ color: C.body }}>
              {mode === 'code_title' && !q && 'Start typing to search 932 AU occupations…'}
              {mode === 'task' && !q && 'Describe a task to find matching occupations…'}
              {mode === 'multi' && multiCodes.length === 0 && 'No codes selected. Add via Code / Title mode.'}
              {(q && mode !== 'state' && mode !== 'multi') && 'No results — try a different keyword.'}
              {mode === 'state' && 'No results for this state.'}
              {mode === 'multi' && multiCodes.length > 0 && 'No results.'}
            </p>
          </div>
        )}
        {!loading && results.length > 0 && (
          <>
            <p className="text-xs mb-3" style={{ color: C.muted }}>
              Showing <strong style={{ color: C.ink }}>{results.length}</strong> occupations
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {results.map(r => (
                <OccupationCard
                  key={r.code}
                  r={r}
                  selected={multiCodes.includes(r.code)}
                  onSelect={() => setSelectedCode(r.code)}
                  onToggleCompare={() => toggleMultiCode(r.code)}
                  mode={mode}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* DETAIL DRAWER */}
      <Sheet open={!!selectedCode} onOpenChange={(o) => !o && setSelectedCode(null)}>
        <SheetContent className="w-full sm:max-w-2xl p-0 overflow-y-auto" style={{ background: C.card }} data-testid="atlas-detail-drawer">
          {selectedCode && detail && <OccupationDetail detail={detail} onClose={() => setSelectedCode(null)} />}
        </SheetContent>
      </Sheet>
    </div>
  );
}

// ─── Occupation card ────────────────────────────────────────────────────────
function OccupationCard({ r, selected, onSelect, onToggleCompare, mode }) {
  return (
    <div
      onClick={onSelect}
      className="rounded-xl border p-4 transition-all cursor-pointer hover:shadow-md flex flex-col gap-3"
      style={{ background: C.card, borderColor: selected ? C.teal : C.border, boxShadow: selected ? `0 0 0 2px ${C.tealWash2}` : 'none' }}
      data-testid={`atlas-card-${r.code}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-mono text-xs font-bold" style={{ color: C.tealDeep }}>{r.code}</p>
          <h3 className="font-bold text-sm leading-tight" style={{ color: C.ink }}>{r.title}</h3>
        </div>
        <span
          className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0"
          style={{
            background: r.status === 'verified' ? C.tealWash2 : r.status === 'draft' ? C.orangeWash2 : C.borderSoft,
            color:      r.status === 'verified' ? C.tealDeep : r.status === 'draft' ? C.orangeDeep : C.muted,
          }}
        >
          {r.status === 'imported_skeleton' ? 'skeleton' : r.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-[10px] uppercase tracking-wider font-bold mb-0.5" style={{ color: C.muted }}>Workforce</p>
          <p className="font-bold" style={{ color: C.ink }}>{r.employed ? r.employed.toLocaleString() : '—'}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider font-bold mb-0.5" style={{ color: C.muted }}>Skill Body</p>
          <p className="font-bold truncate" style={{ color: C.ink }}>{r.assessing_authority || '—'}</p>
        </div>
      </div>

      {r.top_states.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider font-bold mb-1" style={{ color: C.muted }}>Top States</p>
          <div className="flex gap-1 flex-wrap">
            {r.top_states.map(s => (
              <span key={s.state} className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                    style={{ background: C.tealWash, color: C.tealDeep, border: `1px solid ${C.tealWash2}` }}>
                {s.state} {s.pct}%
              </span>
            ))}
          </div>
        </div>
      )}

      {r.eligible_visas.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider font-bold mb-1" style={{ color: C.muted }}>Eligible Visas</p>
          <div className="flex gap-1 flex-wrap">
            {r.eligible_visas.map(v => (
              <span key={v} className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                    style={{ background: C.goldWash, color: C.orangeDeep, border: `1px solid ${C.goldLight}` }}>
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: C.borderSoft }}>
        <button
          onClick={(e) => { e.stopPropagation(); onToggleCompare(); }}
          className="text-xs font-bold flex items-center gap-1"
          style={{ color: selected ? C.red : C.teal }}
          data-testid={`atlas-compare-toggle-${r.code}`}
        >
          {selected ? '− Remove from compare' : '+ Compare'}
        </button>
        <span className="text-xs font-bold flex items-center gap-1" style={{ color: C.teal }}>
          View <ChevronRight className="h-3 w-3" />
        </span>
      </div>
    </div>
  );
}

// ─── Detail drawer ──────────────────────────────────────────────────────────
function OccupationDetail({ detail, onClose }) {
  const o = detail.occupation || {};
  const ap = o.anzsco_profile || {};
  const aa = o.assessing_authority || {};
  const vp = o.visa_pathways || {};
  const visas = vp.visa_eligibility || [];
  const stateDist = o.state_distribution || {};
  const tasks = o.tasks || [];
  const industries = o.industries_ranked || [];
  const sortedStates = Object.entries(stateDist)
    .filter(([, v]) => typeof v === 'number')
    .sort((a, b) => b[1] - a[1]);

  const downloadPdf = () => {
    const token = localStorage.getItem('token');
    fetch(`${API}/anz-intel/occupation/${o.code}/infosheet.pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `LEAMSS_ANZSCO_${o.code}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  return (
    <>
      <SheetHeader className="px-6 py-4 border-b" style={{ borderColor: C.border, background: C.tealDark, color: '#fff' }}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="font-mono text-xs font-bold" style={{ color: C.goldLight }}>{o.code} · ANZSCO {o.classification_version || '1.3'}</p>
            <SheetTitle className="text-2xl font-bold tracking-tight mt-1" style={{ color: '#fff', fontFamily: "'Playfair Display', serif" }}>
              {o.title}
            </SheetTitle>
            <SheetDescription className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.7)' }}>
              Skill Level {o.skill_level || '—'} · Status: {o.status} · Parent group: {detail.parent_4digit}
            </SheetDescription>
          </div>
          <SheetClose className="p-1 rounded hover:bg-white/10" onClick={onClose}>
            <X className="h-5 w-5" style={{ color: '#fff' }} />
          </SheetClose>
        </div>
      </SheetHeader>

      <div className="p-6 space-y-6">
        {/* CTA row */}
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={downloadPdf}
            className="px-4 py-2 rounded-md font-bold text-sm flex items-center gap-2 shadow-sm"
            style={{ background: C.teal, color: '#fff' }}
            data-testid="atlas-detail-pdf-btn"
          >
            <Download className="h-4 w-4" />Download Infosheet PDF
          </button>
          <button
            onClick={() => window.location.href = `/sales/client-assessment?occupation_code=${o.code}`}
            className="px-4 py-2 rounded-md font-bold text-sm flex items-center gap-2 border"
            style={{ background: C.card, color: C.body, borderColor: C.border }}
            data-testid="atlas-detail-wizard-btn"
          >
            Use in Smart Sales Helper <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Stat tiles */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <Tile icon={Users}      label="Workforce"     value={ap.employed_count ? ap.employed_count.toLocaleString() : '—'} sub="employed" />
          <Tile icon={DollarSign} label="Median Weekly" value={ap.median_weekly_earnings_aud ? `AUD ${ap.median_weekly_earnings_aud.toLocaleString()}` : '—'} sub="all employees" />
          <Tile icon={Building2}  label="Assessing Body" value={aa.name || '—'} sub={(aa.url || '')} />
        </div>

        {/* Tasks */}
        {tasks.length > 0 && (
          <Section title="Key Job Tasks" count={tasks.length}>
            <ul className="space-y-1">
              {tasks.slice(0, 10).map((t, i) => (
                <li key={i} className="text-sm flex items-start gap-2" style={{ color: C.body }}>
                  <span style={{ color: C.teal, fontWeight: 800 }}>→</span><span>{t}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* States */}
        {sortedStates.length > 0 && (
          <Section title="State Distribution (employment %)" count={sortedStates.length}>
            <div className="space-y-1">
              {sortedStates.slice(0, 8).map(([s, pct]) => (
                <div key={s} className="flex items-center gap-3">
                  <span className="w-12 text-xs font-bold" style={{ color: C.tealDeep }}>{s}</span>
                  <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ background: C.borderSoft }}>
                    <div style={{ width: `${Math.min(100, pct * 2.5)}%`, height: '100%', background: C.teal }} />
                  </div>
                  <span className="w-10 text-right text-xs font-bold font-mono" style={{ color: C.body }}>{pct}%</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Visa pathways */}
        {visas.length > 0 && (
          <Section title="Visa Eligibility" count={visas.length}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: C.tealWash, borderBottom: `1px solid ${C.tealWash2}` }}>
                  <th className="text-left px-2 py-1.5 font-bold" style={{ color: C.tealDeep }}>Subclass</th>
                  <th className="text-left px-2 py-1.5 font-bold" style={{ color: C.tealDeep }}>Eligible</th>
                  <th className="text-left px-2 py-1.5 font-bold" style={{ color: C.tealDeep }}>List</th>
                  <th className="text-left px-2 py-1.5 font-bold" style={{ color: C.tealDeep }}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {visas.map((v, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.borderSoft}` }}>
                    <td className="px-2 py-1.5 font-mono font-bold" style={{ color: C.ink }}>{v.visa_subclass}</td>
                    <td className="px-2 py-1.5">
                      <span style={{ color: v.eligible ? C.teal : C.red, fontWeight: 800 }}>{v.eligible ? '✓' : '✗'}</span>
                    </td>
                    <td className="px-2 py-1.5" style={{ color: C.body }}>{v.list || '—'}</td>
                    <td className="px-2 py-1.5" style={{ color: C.muted }}>{(v.notes || '').slice(0, 80)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* Industries */}
        {industries.length > 0 && (
          <Section title="Top Industries" count={industries.length}>
            <ol className="text-sm space-y-1" style={{ color: C.body }}>
              {industries.slice(0, 6).map((i, idx) => (
                <li key={i} className="flex gap-2">
                  <span className="font-bold" style={{ color: C.orangeDeep }}>{idx + 1}.</span>{i}
                </li>
              ))}
            </ol>
          </Section>
        )}

        {/* Siblings */}
        {detail.siblings.length > 0 && (
          <Section title={`Related occupations (parent ${detail.parent_4digit})`} count={detail.siblings.length}>
            <div className="space-y-1">
              {detail.siblings.map(s => (
                <div key={s.code} className="flex items-center justify-between p-2 rounded" style={{ background: C.bg }}>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs" style={{ color: C.tealDeep }}>{s.code}</span>
                    <span className="text-sm" style={{ color: C.ink }}>{s.title}</span>
                  </div>
                  <span className="text-xs" style={{ color: C.muted }}>{s.employed ? `${s.employed.toLocaleString()} employed` : ''}</span>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
    </>
  );
}

function Tile({ icon: Icon, label, value, sub }) {
  return (
    <div className="rounded-lg p-3 border" style={{ background: C.tealWash, borderColor: C.tealWash2 }}>
      <Icon className="h-4 w-4 mb-1" style={{ color: C.teal }} />
      <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: C.tealDeep }}>{label}</p>
      <p className="text-base font-bold mt-0.5" style={{ color: C.ink }}>{value}</p>
      {sub && <p className="text-[10px] mt-0.5 truncate" style={{ color: C.muted }}>{sub}</p>}
    </div>
  );
}

function Section({ title, count, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider font-bold mb-2 flex items-center gap-2" style={{ color: C.orange, letterSpacing: '0.06em' }}>
        <ListChecks className="h-3.5 w-3.5" />{title}
        {count !== undefined && <span style={{ color: C.muted, fontWeight: 700 }}>({count})</span>}
      </p>
      {children}
    </div>
  );
}
