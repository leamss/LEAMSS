/**
 * Smart Sales Helper — Phase 10.8
 * Side-by-Side Occupation Comparison (rich Atlas data + best-fit highlight)
 *
 * Route: /sales/occupations/compare
 *
 * Reads `compare_ids` from sessionStorage (set by OccupationSearch.jsx OR by
 * AtlasAutoSuggestModal's "Compare All" button). Calls POST /api/sales/occupations/compare
 * which returns 2-5 occupation cards enriched with full Phase 10 atlas data
 * (TEER · EE eligibility · PNPs · IRCC Cutoffs · Regional Pilots · Quebec · State Noms).
 *
 * Best-fit candidate (highest backend score) shown with green 🏆 ribbon + glow.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Trophy, GitCompare, Loader2, Search, MapPin, FileText,
  CheckCircle2, XCircle, ShieldCheck, Award, Stethoscope, Microscope,
  Hammer, BookOpen, Plane, Users, Shield as ShieldIcon, Languages, Sparkles,
  TrendingUp,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia', label: 'ANZSCO' },
  CA: { flag: '🇨🇦', name: 'Canada',     label: 'NOC' },
  NZ: { flag: '🇳🇿', name: 'New Zealand', label: 'ANZSCO' },
};

const C = {
  teal: '#0F766E', tealDeep: '#115E59', tealWash: '#F0FDFA', tealWash2: '#CCFBF1',
  orange: '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED',
  gold: '#D4A017', goldWash: '#FEF3C7', goldLight: '#FBBF24',
  ink: '#1F2937', body: '#475569', muted: '#94A3B8',
  border: '#E5E7EB', card: '#FFFFFF',
  emerald: '#059669', emeraldWash: '#D1FAE5',
};

const CAT_META = {
  french_language:        { icon: Languages,   label: 'French' },
  healthcare:             { icon: Stethoscope, label: 'Healthcare' },
  stem:                   { icon: Microscope,  label: 'STEM' },
  trade:                  { icon: Hammer,      label: 'Trade' },
  education:              { icon: BookOpen,    label: 'Education' },
  transport:              { icon: Plane,       label: 'Transport' },
  physicians_ca_exp:      { icon: Stethoscope, label: 'Physicians-CA' },
  senior_managers_ca_exp: { icon: Users,       label: 'Sr Mgr-CA' },
  researchers_ca_exp:     { icon: Microscope,  label: 'Researchers-CA' },
  military_recruits:      { icon: ShieldIcon,  label: 'Military' },
};


export default function OccupationCompare() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const raw = sessionStorage.getItem('compare_ids');
    let ids = [];
    try { ids = JSON.parse(raw || '[]'); } catch { ids = []; }
    if (!Array.isArray(ids) || ids.length < 2) {
      setLoading(false);
      setError('Pick at least 2 occupation codes first');
      return;
    }
    const payload = {
      items: ids.map(id => {
        const [country_code, code] = String(id).split(':');
        return { country_code, code };
      }),
    };
    axios.post(`${API}/sales/occupations/compare`, payload, { headers })
      .then(r => setItems(r.data.items || []))
      .catch(e => {
        setError(formatApiError(e, 'Compare failed'));
        toast.error(formatApiError(e, 'Compare failed'));
      })
      .finally(() => setLoading(false));
  }, [headers]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ color: C.muted }} data-testid="compare-loading">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading rich comparison…
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div className="min-h-screen p-6" style={{ background: '#F8FAFC' }} data-testid="compare-error-state">
        <Card className="max-w-2xl mx-auto p-10 text-center">
          <Search className="h-12 w-12 mx-auto mb-3" style={{ color: C.muted, opacity: 0.4 }} />
          <p className="font-medium" style={{ color: C.ink }}>{error || 'Nothing to compare yet'}</p>
          <p className="text-xs mt-1" style={{ color: C.muted }}>
            Search occupations or use AI Atlas Auto-Suggest, then pick 2-5 codes to compare.
          </p>
          <Button className="mt-4" onClick={() => navigate('/sales/occupations')} data-testid="back-to-search">
            <ArrowLeft className="h-4 w-4 mr-1" />Back to Search
          </Button>
        </Card>
      </div>
    );
  }

  const bestItem = items.find(it => it.best_fit);

  return (
    <div className="min-h-screen p-5" style={{ background: '#F8FAFC' }} data-testid="compare-page">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate('/sales/occupations')} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" />Search
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>
                <GitCompare className="h-7 w-7" style={{ color: C.orange }} />Compare Programs Side-by-Side
              </h1>
              <p className="text-sm" style={{ color: C.body }}>
                {items.length} codes · Best-fit auto-highlighted using rich Atlas scoring
              </p>
            </div>
          </div>
          {bestItem && (
            <div className="rounded-lg p-3 flex items-center gap-3" style={{
              background: C.emeraldWash, border: `1px solid ${C.emerald}`,
              boxShadow: '0 4px 12px rgba(5,150,105,0.15)',
            }} data-testid="best-fit-banner">
              <Trophy className="h-6 w-6" style={{ color: C.emerald }} />
              <div>
                <p className="text-[10px] uppercase font-bold tracking-widest" style={{ color: C.emerald, letterSpacing: '0.12em' }}>
                  Best Fit (Score {bestItem.best_fit_score})
                </p>
                <p className="text-sm font-bold" style={{ color: C.ink }}>
                  {COUNTRY_META[bestItem.country_code]?.flag} {bestItem.code} · {bestItem.title}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Card grid */}
        <div className={`grid gap-3 grid-cols-1 ${
          items.length === 2 ? 'md:grid-cols-2' :
          items.length === 3 ? 'md:grid-cols-3' :
          items.length === 4 ? 'md:grid-cols-2 lg:grid-cols-4' :
          'md:grid-cols-2 lg:grid-cols-5'
        }`} data-testid="compare-cards">
          {items.map(it => <CompareCard key={`${it.country_code}-${it.code}`} item={it} />)}
        </div>

        {/* Comparison Table */}
        <Card className="p-4 overflow-x-auto" data-testid="compare-table">
          <h2 className="text-sm font-bold flex items-center gap-2 mb-3 px-1" style={{ color: C.tealDeep }}>
            <FileText className="h-4 w-4" style={{ color: C.orange }} />Detailed Comparison Table
          </h2>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b" style={{ background: '#F1F5F9' }}>
                <th className="text-left p-2 font-bold w-44" style={{ color: C.ink }}>Attribute</th>
                {items.map(it => (
                  <th key={`th-${it.country_code}-${it.code}`} className="text-left p-2 font-bold min-w-[180px]"
                      style={{ color: it.best_fit ? C.emerald : C.ink }}>
                    {(COUNTRY_META[it.country_code] || {}).flag} {it.code}
                    {it.best_fit && <Trophy className="h-3 w-3 inline ml-1" style={{ color: C.emerald }} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Title" items={items} render={it => <span className="font-semibold">{it.title}</span>} />
              <Row label="Classification" items={items} render={it => <span>{it.atlas?.classification_version || '—'}</span>} />
              <Row label="Skill / TEER" items={items} render={it => {
                const t = it.atlas?.teer_category;
                const s = it.skill_level;
                if (t !== undefined && t !== null) return <span>TEER {t} · {it.atlas?.teer_label || '—'}</span>;
                if (s !== undefined && s !== null) return <span>Skill Level {s}</span>;
                return <span style={{ color: C.muted }}>—</span>;
              }} />
              <Row label="In Demand?" items={items} render={it => it.in_demand
                ? <CheckCircle2 className="h-4 w-4" style={{ color: C.emerald }} />
                : <XCircle className="h-4 w-4" style={{ color: C.muted }} />} />

              {/* CA-specific rows */}
              {items.some(it => it.country_code === 'CA') && (
                <>
                  <SectionHeader label="🇨🇦 IRCC Federal Programs" />
                  <Row label="FSWP" items={items} render={it => <EligIcon v={it.atlas?.ee_eligibility?.fswp_eligible} />} />
                  <Row label="CEC" items={items} render={it => <EligIcon v={it.atlas?.ee_eligibility?.cec_eligible} />} />
                  <Row label="FSTP (Trades)" items={items} render={it => <EligIcon v={it.atlas?.ee_eligibility?.fstp_eligible} />} />
                  <Row label="Categories" items={items} render={it => {
                    const cats = it.atlas?.ee_eligibility?.categories || [];
                    return cats.length > 0
                      ? <div className="flex flex-wrap gap-0.5">{cats.map(c => {
                          const m = CAT_META[c];
                          if (!m) return null;
                          const Ic = m.icon;
                          return <span key={c} className="text-[9px] px-1 py-0.5 rounded flex items-center gap-0.5"
                                       style={{ background: C.tealWash2, color: C.tealDeep }}>
                            <Ic className="h-2.5 w-2.5" />{m.label}
                          </span>;
                        })}</div>
                      : <span style={{ color: C.muted }}>—</span>;
                  }} />
                  <Row label="PNPs Eligible" items={items} render={it => {
                    const pnps = it.atlas?.pnp_eligibility || [];
                    return pnps.length > 0
                      ? <div className="flex flex-wrap gap-0.5">{pnps.slice(0, 8).map(p =>
                          <span key={p.pnp_id} className="text-[9px] font-mono font-bold px-1 py-0.5 rounded"
                                style={{ background: C.tealWash, color: C.tealDeep }}>{p.province_code}</span>
                        )}<span className="text-[9px]" style={{ color: C.muted }}>({pnps.length})</span></div>
                      : <span style={{ color: C.muted }}>—</span>;
                  }} />
                  <Row label="Regional Pilots" items={items} render={it => {
                    const pilots = it.atlas?.regional_pilot_eligibility || [];
                    const counts = pilots.reduce((acc, p) => { acc[p.pilot] = (acc[p.pilot] || 0) + 1; return acc; }, {});
                    return Object.keys(counts).length > 0
                      ? <div className="flex flex-wrap gap-0.5">
                          {Object.entries(counts).map(([k, n]) =>
                            <span key={k} className="text-[9px] font-bold px-1 py-0.5 rounded"
                                  style={{ background: C.orangeWash, color: C.orangeDeep }}>{k.toUpperCase()}·{n}</span>
                          )}
                        </div>
                      : <span style={{ color: C.muted }}>—</span>;
                  }} />
                  <Row label="Quebec PSTQ" items={items} render={it => {
                    const qe = it.atlas?.quebec_eligibility || {};
                    if (!qe.eligible) return <span style={{ color: C.muted }}>—</span>;
                    return <div className="flex flex-wrap gap-0.5">
                      {(qe.sections || []).map(s =>
                        <span key={s.section_id} className="text-[9px] px-1 py-0.5 rounded font-bold"
                              style={{ background: s.priority ? C.gold : C.goldWash, color: s.priority ? '#fff' : C.orangeDeep }}>
                          {s.priority && '⭐'}{s.section_id.replace('pstq_', '').toUpperCase()}
                        </span>
                      )}
                    </div>;
                  }} />
                  <Row label="Latest CRS Cutoff (best category)" items={items} render={it => {
                    const cutoffs = it.atlas?.ircc_round_cutoffs?.cutoffs_by_category || {};
                    const allVals = Object.values(cutoffs).filter(c => c.latest_crs_min !== null && c.latest_crs_min !== undefined);
                    if (allVals.length === 0) return <span style={{ color: C.muted }}>—</span>;
                    const minCut = Math.min(...allVals.map(c => c.latest_crs_min));
                    return <span className="font-bold" style={{ color: C.orangeDeep }}>{minCut}+</span>;
                  }} />
                </>
              )}

              {/* AU-specific rows */}
              {items.some(it => it.country_code === 'AU') && (
                <>
                  <SectionHeader label="🇦🇺 Australia Specifics" />
                  <Row label="Skill Body" items={items} render={it => it.atlas?.assessing_authority?.name
                    ? <span>{it.atlas.assessing_authority.name}</span>
                    : it.assessing_body
                    ? <span>{it.assessing_body}</span>
                    : <span style={{ color: C.muted }}>—</span>} />
                  <Row label="SkillSelect Tier" items={items} render={it => {
                    const tier = it.atlas?.skillselect_tier;
                    return tier
                      ? <Badge style={{ background: C.tealWash2, color: C.tealDeep, fontSize: 9 }}>
                          {String(tier).replace('_', ' ').toUpperCase()}
                        </Badge>
                      : <span style={{ color: C.muted }}>—</span>;
                  }} />
                  <Row label="State Nominations" items={items} render={it => {
                    const states = it.atlas?.state_nomination || {};
                    const active = Object.keys(states).filter(k => states[k]);
                    return active.length > 0
                      ? <div className="flex flex-wrap gap-0.5">{active.map(st =>
                          <span key={st} className="text-[9px] font-mono font-bold px-1 py-0.5 rounded"
                                style={{ background: C.tealWash, color: C.tealDeep }}>{st}</span>
                        )}</div>
                      : <span style={{ color: C.muted }}>—</span>;
                  }} />
                  <Row label="Min Invitation Points" items={items} render={it => {
                    const mp = it.atlas?.min_invitation_points || {};
                    if (!mp.sc189_standard && !mp.sc491_family_sponsored) return <span style={{ color: C.muted }}>—</span>;
                    return <span className="text-[10px]">189: {mp.sc189_standard || '—'} / 491: {mp.sc491_family_sponsored || '—'}</span>;
                  }} />
                  <Row label="DAMA + ILA" items={items} render={it => {
                    const d = (it.atlas?.dama_eligibility || []).length;
                    const i = (it.atlas?.ila_eligibility || []).length;
                    if (!d && !i) return <span style={{ color: C.muted }}>—</span>;
                    return <span className="text-[10px]">DAMA: {d} · ILA: {i}</span>;
                  }} />
                </>
              )}

              {/* Common cost/process rows */}
              <SectionHeader label="📊 Cost / Process" />
              <Row label="Min Points Required" items={items} render={it => it.min_points_required ?? <span style={{ color: C.muted }}>—</span>} />
              <Row label="Age Limit" items={items} render={it => it.age_limit ? `${it.age_limit} yrs` : <span style={{ color: C.muted }}>—</span>} />
              <Row label="Body Fee" items={items} render={it => it.body_fee_native ?? <span style={{ color: C.muted }}>—</span>} />
              <Row label="Processing (weeks)" items={items} render={it => it.body_processing_weeks ?? <span style={{ color: C.muted }}>—</span>} />

              {/* Score */}
              <SectionHeader label="🏆 Best-Fit Score" />
              <Row label="Score" items={items} render={it => (
                <div className="flex items-center gap-1">
                  <span className="font-bold" style={{ color: it.best_fit ? C.emerald : C.body }}>
                    {it.best_fit_score}
                  </span>
                  {it.best_fit && <Trophy className="h-3 w-3" style={{ color: C.emerald }} />}
                </div>
              )} />
            </tbody>
          </table>
        </Card>

        <p className="text-[10px] text-center italic" style={{ color: C.muted }}>
          Best-fit auto-computed from in-demand · TEER label · federal/state eligibility · PNPs/states count ·
          Regional Pilots · Quebec sections · SkillSelect Tier 1 bonus.
        </p>
      </div>
    </div>
  );
}


function CompareCard({ item }) {
  const cm = COUNTRY_META[item.country_code] || {};
  const a = item.atlas || {};
  const ee = a.ee_eligibility || {};
  const isBest = item.best_fit;
  return (
    <Card className="p-3 relative" style={{
      borderTopWidth: 4,
      borderTopColor: isBest ? C.emerald : item.country_code === 'CA' ? '#DC2626' : item.country_code === 'AU' ? '#1D4ED8' : '#059669',
      boxShadow: isBest ? '0 8px 24px rgba(5,150,105,0.25)' : '0 1px 3px rgba(0,0,0,0.05)',
    }} data-testid={`compare-card-${item.code}`}>
      {isBest && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1"
             style={{ background: C.emerald, color: '#fff' }} data-testid={`compare-best-${item.code}`}>
          <Trophy className="h-3 w-3" />Best Fit
        </div>
      )}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xl">{cm.flag}</span>
        <div>
          <span className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
            {cm.label} {item.code}
          </span>
        </div>
      </div>
      <p className="text-sm font-bold mb-2" style={{ color: C.ink, fontFamily: "'Playfair Display', serif" }}>
        {item.title}
      </p>

      {/* TEER / Skill Level */}
      {a.teer_label && (
        <Badge style={{ background: C.tealWash2, color: C.tealDeep, fontSize: 9 }}>
          <Award className="h-2.5 w-2.5 mr-1" />TEER {a.teer_category} · {a.teer_label}
        </Badge>
      )}
      {!a.teer_label && item.skill_level !== undefined && (
        <Badge style={{ background: C.tealWash2, color: C.tealDeep, fontSize: 9 }}>
          <Award className="h-2.5 w-2.5 mr-1" />Skill Level {item.skill_level}
        </Badge>
      )}

      {/* Federal Programs */}
      {item.country_code === 'CA' && (
        <div className="mt-2 grid grid-cols-3 gap-1">
          {['fswp', 'cec', 'fstp'].map(p => (
            <div key={p} className="text-center text-[9px] p-1 rounded" style={{
              background: ee[`${p}_eligible`] ? C.tealWash2 : '#fff',
              border: `1px solid ${ee[`${p}_eligible`] ? C.teal : C.border}`,
              color: ee[`${p}_eligible`] ? C.tealDeep : C.muted,
            }}>
              {ee[`${p}_eligible`] ? <CheckCircle2 className="h-3 w-3 mx-auto" /> : <XCircle className="h-3 w-3 mx-auto" />}
              <p className="font-bold mt-0.5">{p.toUpperCase()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Score footer */}
      <div className="mt-3 pt-2 border-t flex items-center justify-between" style={{ borderColor: C.border }}>
        <span className="text-[9px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.08em' }}>
          Best-Fit Score
        </span>
        <span className="text-lg font-bold" style={{ color: isBest ? C.emerald : C.body, fontFamily: "'Playfair Display', serif" }}>
          {item.best_fit_score}
        </span>
      </div>

      {/* Quick stats line */}
      <div className="mt-1 flex flex-wrap gap-1 text-[9px]" style={{ color: C.body }}>
        {item.country_code === 'CA' && (
          <>
            <span>PNPs: <b>{(a.pnp_eligibility || []).length}</b></span>
            <span>·</span>
            <span>Cats: <b>{(ee.categories || []).length}</b></span>
            <span>·</span>
            <span>Pilots: <b>{(a.regional_pilot_eligibility || []).length}</b></span>
            {a.quebec_eligibility?.eligible && <><span>·</span><span style={{ color: C.orangeDeep }}>QC ✓</span></>}
          </>
        )}
        {item.country_code === 'AU' && (
          <>
            <span>Visas: <b>{item.eligible_visas_count}</b></span>
            <span>·</span>
            <span>States: <b>{Object.keys(a.state_nomination || {}).filter(k => (a.state_nomination || {})[k]).length}</b></span>
            {a.skillselect_tier && <><span>·</span><span><b>{String(a.skillselect_tier).replace('_', ' ').toUpperCase()}</b></span></>}
          </>
        )}
      </div>
    </Card>
  );
}


function SectionHeader({ label }) {
  return (
    <tr style={{ background: C.tealWash }}>
      <td colSpan={20} className="px-2 py-1 text-[10px] uppercase font-bold tracking-wider"
          style={{ color: C.tealDeep, letterSpacing: '0.1em' }}>
        {label}
      </td>
    </tr>
  );
}

function Row({ label, items, render }) {
  return (
    <tr className="border-b" style={{ borderColor: C.border }}>
      <td className="p-2 font-medium" style={{ color: C.body, background: '#FAFBFC' }}>{label}</td>
      {items.map(it => (
        <td key={`cell-${it.country_code}-${it.code}-${label}`} className="p-2 align-top"
            style={{ background: it.best_fit ? '#F0FDF4' : '#fff' }}>
          {render(it)}
        </td>
      ))}
    </tr>
  );
}

function EligIcon({ v }) {
  if (v === true) return <CheckCircle2 className="h-4 w-4" style={{ color: C.emerald }} />;
  if (v === false) return <XCircle className="h-4 w-4" style={{ color: C.muted }} />;
  return <span style={{ color: C.muted }}>—</span>;
}
