/**
 * Smart Sales Helper — Phase 18.2 rewire + UI/UX overhaul
 *
 * Route: /sales/occupations/:countryCode/:code
 *
 * Reads admin-verified data from the new `/api/sales/occupations/{cc}/{code}`
 * shape (Phase 18.2 backend): every tab is now powered by `occupation_master.*`
 * — not legacy `country_rules` — so Smart Sales sees exactly what admin
 * verifies, immediately.
 *
 * Tabs: Overview · Skill Assessment · Visa Pathways · Documents · Similar · Sample Cases
 *
 * LEAMSS brand colours:
 *   Forest Green #1F4D44 (primary), Burnt Orange #D4633F (accent),
 *   Warm White #FAFAF7 (background), Emerald-600 (verified / required),
 *   Amber-500 (recommended primary pathway).
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, ExternalLink, FileText, CheckCircle2, MapPin, Building2, Calendar,
  Sparkles, Globe, GitCompare, Loader2, ChevronRight, TrendingUp,
  Star, Briefcase, BookOpen, Layers, Clock, IndianRupee, ShieldCheck,
  ChevronDown, Phone, FileDown, AlertTriangle, Pin,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia' },
  CA: { flag: '🇨🇦', name: 'Canada' },
  NZ: { flag: '🇳🇿', name: 'New Zealand' },
};

const BRAND = {
  forest: '#1F4D44',
  forestDark: '#173B34',
  burnt: '#D4633F',
  warm: '#FAFAF7',
  cream: '#F5F2EC',
};

const STATE_NAME = {
  NSW: 'New South Wales', VIC: 'Victoria', QLD: 'Queensland', SA: 'South Australia',
  WA: 'Western Australia', TAS: 'Tasmania', NT: 'Northern Territory', ACT: 'ACT',
  ON: 'Ontario', BC: 'British Columbia', AB: 'Alberta', QC: 'Quebec', MB: 'Manitoba',
};

export default function OccupationDetail() {
  const { countryCode, code } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('overview');

  useEffect(() => {
    setLoading(true);
    axios
      .get(`${API}/sales/occupations/${countryCode}/${code}`, { headers })
      .then((r) => {
        setData(r.data);
        const t = (r.data?.overview?.title || '') + ' — LEAMSS Occupation Atlas';
        if (typeof document !== 'undefined') document.title = t;
      })
      .catch((e) => {
        toast.error(formatApiError(e, 'Could not load occupation detail'));
        navigate('/sales/occupations');
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countryCode, code]);

  if (loading) return <SkeletonDetail />;
  if (!data) return null;

  const meta = COUNTRY_META[(countryCode || '').toUpperCase()] || { flag: '🌐', name: countryCode };
  const ov = data.overview || {};
  const sa = data.skill_assessment || {};
  const vp = data.visa_pathways || [];
  const docs = data.documents || { items: [], total: 0, by_category: {} };
  const similar = data.similar || [];
  const cases = data.sample_cases || [];
  const vm = data.verification_meta || {};

  return (
    <div className="min-h-screen" style={{ background: BRAND.warm }} data-testid="sales-occupation-detail">
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print-card { break-inside: avoid; box-shadow: none !important; border: 1px solid #ccc !important; }
        }
      `}</style>

      {/* ─── HEADER ─────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between mb-3 no-print">
            <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900" data-testid="sales-back-btn">
              <ArrowLeft className="h-4 w-4" />Back to results
            </button>
            <Button variant="outline" size="sm" className="text-[#D4633F] border-[#D4633F] hover:bg-[#D4633F] hover:text-white" data-testid="sales-add-to-compare">
              <GitCompare className="h-3.5 w-3.5 mr-1" />Add to Compare
            </Button>
          </div>

          <div className="flex items-start gap-4 flex-wrap">
            {/* Code badge — filled forest green */}
            <div className="flex-shrink-0 px-4 py-3 rounded-lg text-white font-mono font-bold text-xl tracking-wide shadow"
                 style={{ background: BRAND.forest }} data-testid="sales-code-badge">
              {ov.code || code || '—'}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-2xl">{meta.flag}</span>
                <span className="text-sm font-medium text-slate-600">{meta.name}</span>
                <span className="text-slate-300">·</span>
                <span className="text-sm text-slate-500 uppercase tracking-wide">{ov.group || 'Occupation'}</span>
                {vm.is_verified && <VerificationBadge daysSince={vm.days_since_verified} />}
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold leading-tight" style={{ color: BRAND.forestDark, fontFamily: 'Georgia, serif' }} data-testid="sales-occupation-title">
                {ov.title || 'Untitled Occupation'}
              </h1>
              <div className="flex items-center gap-2 text-[12px] text-slate-500 mt-1.5 flex-wrap">
                {vm.verified_by_name && (
                  <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-emerald-600" />Verified by <strong className="text-slate-700">{vm.verified_by_name}</strong></span>
                )}
                {vm.verified_at && <><span>·</span><span>{relativeTime(vm.verified_at)}</span></>}
                {vm.source_reference && (
                  <>
                    <span>·</span>
                    <a href={vm.source_reference} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-indigo-600 hover:underline" data-testid="sales-source-link">
                      Source <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </>
                )}
                {ov.pathway && <><span>·</span><Badge className="bg-emerald-100 text-emerald-700 text-[10px] font-semibold">{ov.pathway}</Badge></>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── TABS ───────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList
            className="bg-white border border-slate-200 rounded-full p-1 mb-6 inline-flex w-auto h-auto gap-1 overflow-x-auto max-w-full"
            data-testid="sales-tabs"
          >
            <PillTab value="overview" label="Overview" />
            <PillTab value="skill"    label="Skill Assessment" tone={sa.has_data ? 'default' : 'muted'} />
            <PillTab value="visas"    label="Visa Pathways" count={vp.length} />
            <PillTab value="docs"     label="Documents" count={docs.total} />
            <PillTab value="similar"  label="Similar" count={similar.length} />
            <PillTab value="cases"    label="Sample Cases" count={cases.length} />
          </TabsList>

          <TabsContent value="overview"><OverviewTab ov={ov} /></TabsContent>
          <TabsContent value="skill"><SkillAssessmentTab sa={sa} /></TabsContent>
          <TabsContent value="visas"><VisaPathwaysTab pathways={vp} /></TabsContent>
          <TabsContent value="docs"><DocumentsTab docs={docs} /></TabsContent>
          <TabsContent value="similar"><SimilarTab similar={similar} onClick={(s) => navigate(`/sales/occupations/${s.country_code}/${s.code}`)} /></TabsContent>
          <TabsContent value="cases"><SampleCasesTab cases={cases} /></TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Header pieces
   ════════════════════════════════════════════════════════════════ */
function VerificationBadge({ daysSince }) {
  let tone = 'bg-emerald-100 text-emerald-700';
  let label = 'Verified';
  if (daysSince == null) {
    tone = 'bg-slate-100 text-slate-600';
    label = 'Verified';
  } else if (daysSince > 90) {
    tone = 'bg-rose-100 text-rose-700';
    label = `Re-verify due (${daysSince}d)`;
  } else if (daysSince > 30) {
    tone = 'bg-amber-100 text-amber-700';
    label = `Verified ${daysSince}d ago`;
  } else if (daysSince > 0) {
    label = `Verified ${daysSince}d ago`;
  } else {
    label = 'Verified today';
  }
  return <Badge className={`${tone} text-[10px] font-semibold`} data-testid="sales-verified-badge"><ShieldCheck className="h-2.5 w-2.5 mr-0.5" />{label}</Badge>;
}

function relativeTime(iso) {
  if (!iso) return '';
  const then = new Date(iso); const now = new Date();
  const mins = Math.round((now - then) / 60000);
  if (mins < 60) return `${mins}m ago`;
  if (mins < 1440) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / 1440)}d ago`;
}

function PillTab({ value, label, count, tone = 'default' }) {
  return (
    <TabsTrigger
      value={value}
      className="rounded-full px-4 py-1.5 text-[12px] data-[state=active]:text-white data-[state=active]:shadow"
      style={{
        '--tw-active-bg': BRAND.forest,
      }}
      data-testid={`sales-tab-${value}`}
    >
      <span className="inline-flex items-center gap-1.5">
        {label}
        {count != null && (
          <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full px-1.5 text-[10px] bg-slate-100 text-slate-600 data-[state=active]:bg-white/20">
            {count}
          </span>
        )}
        {tone === 'muted' && <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title="Admin verification incomplete" />}
      </span>
    </TabsTrigger>
  );
}

/* ════════════════════════════════════════════════════════════════
   Tab 1 — OVERVIEW
   ════════════════════════════════════════════════════════════════ */
function OverviewTab({ ov }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="sales-tab-content-overview">
      <Card className="p-5 lg:col-span-2 print-card">
        <SectionTitle icon={<BookOpen className="h-4 w-4" />}>Description</SectionTitle>
        {ov.description ? (
          <p className="text-[14px] leading-relaxed text-slate-700 mt-2" style={{ fontFamily: 'Georgia, serif' }}>{ov.description}</p>
        ) : (
          <EmptyHint>No description on file — admin can add via Verification Hub.</EmptyHint>
        )}

        <SectionTitle icon={<Briefcase className="h-4 w-4" />} className="mt-5">Typical Tasks ({(ov.typical_tasks || []).length})</SectionTitle>
        {(ov.typical_tasks || []).length === 0 ? <EmptyHint>No tasks listed.</EmptyHint> : (
          <ol className="mt-2 space-y-1.5">
            {ov.typical_tasks.map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-slate-700">
                <span className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 mt-0.5 rounded-full text-[10px] font-semibold" style={{ background: BRAND.cream, color: BRAND.forest }}>{i + 1}</span>
                <span>{t}</span>
              </li>
            ))}
          </ol>
        )}

        {(ov.alternative_titles || []).length > 0 && (
          <>
            <SectionTitle className="mt-5">Also known as</SectionTitle>
            <div className="flex flex-wrap gap-1 mt-2">
              {ov.alternative_titles.slice(0, 12).map((a) => <Badge key={a} className="bg-slate-100 text-slate-700 text-[10px]">{a}</Badge>)}
              {ov.alternative_titles.length > 12 && <Badge className="bg-slate-50 text-slate-400 text-[10px]">+ {ov.alternative_titles.length - 12} more</Badge>}
            </div>
          </>
        )}
      </Card>

      <div className="space-y-4">
        <Card className="p-5 print-card" style={{ background: BRAND.cream + '50' }}>
          <SectionTitle icon={<ShieldCheck className="h-4 w-4" />}>Qualification Rules</SectionTitle>
          {ov.qualification_rules ? (
            <p className="text-[13px] leading-relaxed text-slate-700 mt-2 whitespace-pre-wrap">{ov.qualification_rules}</p>
          ) : (
            <EmptyHint>Not yet documented.</EmptyHint>
          )}
        </Card>

        {ov.state_demand && Object.keys(ov.state_demand).length > 0 && (
          <Card className="p-5 print-card">
            <SectionTitle icon={<MapPin className="h-4 w-4" />}>State / Territory Demand</SectionTitle>
            <div className="grid grid-cols-2 gap-1.5 mt-2">
              {Object.entries(ov.state_demand).map(([st, demand]) => (
                <div key={st} className="flex items-center justify-between text-[11px] px-2 py-1 rounded bg-slate-50">
                  <span title={STATE_NAME[st] || st} className="font-medium text-slate-700">{st}</span>
                  <DemandBadge value={demand} />
                </div>
              ))}
            </div>
          </Card>
        )}

        {ov.salary_range && (
          <Card className="p-5 print-card">
            <SectionTitle icon={<IndianRupee className="h-4 w-4" />}>Salary Range</SectionTitle>
            <p className="text-[14px] font-semibold text-slate-800 mt-2">
              {ov.salary_range.min && ov.salary_range.max ? `${ov.salary_range.currency || ''} ${ov.salary_range.min.toLocaleString()} – ${ov.salary_range.max.toLocaleString()}` : '—'}
            </p>
          </Card>
        )}
      </div>

      {(ov.custom_sections || []).length > 0 && (
        <div className="lg:col-span-3 space-y-2">
          <SectionTitle icon={<FileText className="h-4 w-4" />}>Additional Notes</SectionTitle>
          {ov.custom_sections.map((s, i) => <CustomSectionCard key={s.id || i} s={s} />)}
        </div>
      )}
    </div>
  );
}

function CustomSectionCard({ s }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="overflow-hidden print-card" data-testid="sales-custom-section">
      <button type="button" onClick={() => setOpen(!open)} className="w-full p-3 text-left flex items-center justify-between hover:bg-slate-50">
        <span className="font-medium text-[13px] text-slate-800">{s.title}</span>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-slate-100">
          {s.body_markdown && <p className="text-[13px] text-slate-700 whitespace-pre-wrap mt-2">{s.body_markdown}</p>}
          {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" className="text-[11px] text-indigo-600 inline-flex items-center gap-0.5 mt-1">{s.source_url} <ExternalLink className="h-2.5 w-2.5" /></a>}
        </div>
      )}
    </Card>
  );
}

function DemandBadge({ value }) {
  const v = (value || '').toString().toLowerCase().replace(/\s/g, '_');
  const map = {
    very_high: { c: 'bg-emerald-600 text-white', l: 'Very High' },
    high: { c: 'bg-emerald-100 text-emerald-700', l: 'High' },
    medium: { c: 'bg-amber-100 text-amber-700', l: 'Medium' },
    low: { c: 'bg-slate-100 text-slate-500', l: 'Low' },
    none: { c: 'bg-slate-50 text-slate-400', l: '—' },
  };
  const m = map[v] || { c: 'bg-slate-100 text-slate-500', l: value || '—' };
  return <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${m.c}`}>{m.l}</span>;
}

/* ════════════════════════════════════════════════════════════════
   Tab 2 — SKILL ASSESSMENT
   ════════════════════════════════════════════════════════════════ */
function SkillAssessmentTab({ sa }) {
  if (!sa.has_data) {
    return (
      <Card className="p-8 text-center print-card" data-testid="sales-skill-assessment-empty">
        <AlertTriangle className="h-10 w-10 mx-auto text-amber-400 mb-2" />
        <h3 className="text-base font-semibold text-slate-700">Admin verification pending</h3>
        <p className="text-[13px] text-slate-500 mt-1 max-w-md mx-auto">Assessing-body details for this occupation haven&apos;t been published yet. Once admin completes verification, this section will populate automatically.</p>
        <Button className="mt-4 text-white" style={{ background: BRAND.burnt }} data-testid="sales-request-verification" onClick={() => toast.success('Verification request logged', { description: 'Admin will be notified.' })}>
          Request Verification
        </Button>
      </Card>
    );
  }
  return (
    <div className="space-y-4" data-testid="sales-skill-assessment-card">
      <Card className="p-5 print-card" style={{ background: BRAND.cream + '40', borderColor: BRAND.forest + '30' }}>
        <div className="flex items-start gap-4 flex-wrap">
          <div className="w-12 h-12 rounded-lg flex items-center justify-center text-white flex-shrink-0" style={{ background: BRAND.forest }}>
            <Building2 className="h-6 w-6" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-slate-900" style={{ fontFamily: 'Georgia, serif' }}>{sa.body_name}</h2>
            {sa.body_url && (
              <a href={sa.body_url} target="_blank" rel="noreferrer" className="text-[12px] text-indigo-600 hover:underline inline-flex items-center gap-0.5 mt-0.5" data-testid="sales-skill-body-url">
                {sa.body_url} <ExternalLink className="h-2.5 w-2.5" />
              </a>
            )}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="sales-skill-metric-strip">
        <Metric icon={<Clock className="h-5 w-5" />} label="Processing Time" value={sa.processing_time_weeks ? `${sa.processing_time_weeks} weeks` : '—'} />
        <Metric icon={<IndianRupee className="h-5 w-5" />} label="Assessment Fee" value={sa.fee_native ? `${sa.fee_currency || ''} ${Number(sa.fee_native).toLocaleString()}` : '—'} />
        <Metric icon={<Phone className="h-5 w-5" />} label="Contact" value={sa.contact_details || '—'} small />
      </div>

      {sa.rules_summary && (
        <Card className="p-5 print-card">
          <SectionTitle icon={<BookOpen className="h-4 w-4" />}>Assessment Rules Summary</SectionTitle>
          <p className="text-[13px] leading-relaxed text-slate-700 mt-2 whitespace-pre-wrap">{sa.rules_summary}</p>
        </Card>
      )}
    </div>
  );
}

function Metric({ icon, label, value, small }) {
  return (
    <Card className="p-4 print-card">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">
        <span style={{ color: BRAND.forest }}>{icon}</span>{label}
      </div>
      <p className={`font-semibold text-slate-800 ${small ? 'text-[12px]' : 'text-base'}`}>{value}</p>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════
   Tab 3 — VISA PATHWAYS
   ════════════════════════════════════════════════════════════════ */
function VisaPathwaysTab({ pathways }) {
  if (!pathways || pathways.length === 0) {
    return <EmptyCard testid="sales-visas-empty">No visa pathways listed for this code.</EmptyCard>;
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="sales-tab-content-visas">
      {pathways.map((v) => <VisaPathwayCard key={v.subclass} v={v} />)}
    </div>
  );
}

function VisaPathwayCard({ v }) {
  const recommended = v.is_recommended;
  return (
    <Card
      className={`p-4 print-card transition ${recommended ? 'ring-2 ring-amber-400 shadow-lg' : 'hover:shadow-md'}`}
      data-testid={`sales-visa-${v.subclass}`}
    >
      <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="px-2 py-1 rounded font-mono font-bold text-white text-sm" style={{ background: recommended ? '#F59E0B' : BRAND.forest }}>
            {v.subclass}
          </div>
          {recommended && <Badge className="bg-amber-500 text-white text-[10px] font-semibold" data-testid="sales-recommended-badge"><Star className="h-2.5 w-2.5 mr-0.5 fill-current" />Recommended Primary Pathway</Badge>}
          {v.eligible && !recommended && <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Eligible</Badge>}
        </div>
        {v.pathway_type && <Badge className="bg-slate-100 text-slate-600 text-[10px]">{v.pathway_type}</Badge>}
      </div>
      <h3 className="font-semibold text-[13px] text-slate-800">{v.name}</h3>
      <div className="grid grid-cols-2 gap-2 mt-3 text-[11px]">
        {v.points_minimum != null && v.points_minimum > 0 && <Stat label="Points min." value={v.points_minimum} />}
        {v.age_limit && <Stat label="Age limit" value={`< ${v.age_limit}`} />}
        {v.english_minimum && <Stat label="English" value={v.english_minimum} />}
        {v.experience_required && <Stat label="Experience" value={String(v.experience_required).slice(0, 20)} />}
        {v.fee_inr && <Stat label="Govt Fee" value={`₹${Number(v.fee_inr).toLocaleString()}`} />}
        {v.processing_time_months && <Stat label="Processing" value={`${v.processing_time_months} mo`} />}
      </div>
    </Card>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-slate-50 px-2 py-1 rounded">
      <div className="text-[9px] uppercase text-slate-400">{label}</div>
      <div className="text-[12px] font-semibold text-slate-700">{value}</div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Tab 4 — DOCUMENTS (per-occupation, country-filtered)
   ════════════════════════════════════════════════════════════════ */
function DocumentsTab({ docs }) {
  const byCat = useMemo(() => {
    const out = {};
    (docs.items || []).forEach((d) => {
      const c = d.category || 'Other';
      if (!out[c]) out[c] = [];
      out[c].push(d);
    });
    return out;
  }, [docs]);
  const cats = Object.keys(byCat);

  if (!cats.length) {
    return <EmptyCard testid="sales-docs-empty">No documents curated for this occupation yet.</EmptyCard>;
  }

  return (
    <div className="space-y-3" data-testid="sales-tab-content-docs">
      <div className="flex justify-between items-center no-print">
        <p className="text-[12px] text-slate-500">{docs.total} documents · per-occupation curated · country-filtered</p>
        <Button variant="outline" size="sm" onClick={() => window.print()} data-testid="sales-export-docs-pdf">
          <FileDown className="h-3 w-3 mr-1" />Export Checklist (PDF)
        </Button>
      </div>
      {cats.map((c) => <DocCategorySection key={c} category={c} items={byCat[c]} />)}
    </div>
  );
}

function DocCategorySection({ category, items }) {
  const [open, setOpen] = useState(true);
  return (
    <Card className="overflow-hidden print-card" data-testid={`sales-doc-category-${category}`}>
      <button type="button" onClick={() => setOpen(!open)} className="w-full p-3 text-left flex items-center justify-between hover:bg-slate-50">
        <span className="font-semibold text-[13px]" style={{ color: BRAND.forest }}>{category} <span className="text-slate-400 font-normal">({items.length})</span></span>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-slate-100">
          <ul className="mt-2 space-y-1">
            {items.map((d, i) => (
              <li key={d.id || i} className="flex items-start gap-2 text-[12px] py-1" data-testid={`sales-doc-item-${d.id || i}`}>
                {d.required ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-slate-300 flex-shrink-0 mt-0.5" />
                )}
                <span className="text-slate-700 flex-1">{d.name}</span>
                <div className="flex gap-1">
                  {d.country_override && <Badge className="bg-blue-100 text-blue-700 text-[9px]">{d.country_override}-only</Badge>}
                  <Badge className={`text-[9px] ${d.required ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{d.required ? 'Required' : 'Optional'}</Badge>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════
   Tab 5 — SIMILAR (override pinned first)
   ════════════════════════════════════════════════════════════════ */
function SimilarTab({ similar, onClick }) {
  if (!similar || similar.length === 0) {
    return <EmptyCard testid="sales-similar-empty">No similar codes yet.</EmptyCard>;
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="sales-tab-content-similar">
      {similar.map((s) => (
        <Card
          key={`${s.country_code}-${s.code}`}
          onClick={() => onClick(s)}
          className={`p-3 cursor-pointer transition hover:shadow-md print-card ${s.is_override ? 'border-amber-300 bg-amber-50/30' : ''}`}
          data-testid={`sales-similar-${s.country_code}-${s.code}`}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="text-lg">{COUNTRY_META[s.country_code]?.flag || '🌐'}</span>
              <span className="font-mono font-bold text-[13px]" style={{ color: BRAND.forest }}>{s.code}</span>
            </div>
            {s.is_override ? (
              <Badge className="bg-amber-400 text-white text-[9px]" data-testid="sales-similar-override-pin"><Pin className="h-2.5 w-2.5 mr-0.5 fill-current" />Pinned</Badge>
            ) : (
              <span className="text-[9px] text-slate-400">{s.similarity_score}% match</span>
            )}
          </div>
          <h4 className="text-[13px] font-medium text-slate-800 line-clamp-2">{s.title}</h4>
          <div className="flex items-center gap-1 mt-2 flex-wrap">
            {s.pathway && <Badge className="bg-slate-100 text-slate-600 text-[9px]">{s.pathway}</Badge>}
            {s.assessing_body && <span className="text-[10px] text-slate-500 truncate">{s.assessing_body}</span>}
          </div>
        </Card>
      ))}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Tab 6 — SAMPLE CASES
   ════════════════════════════════════════════════════════════════ */
function SampleCasesTab({ cases }) {
  if (!cases || cases.length === 0) {
    return (
      <Card className="p-10 text-center print-card" data-testid="sales-cases-empty">
        <BookOpen className="h-10 w-10 mx-auto text-slate-300 mb-3" />
        <h3 className="font-semibold text-slate-700">No anonymised cases shared yet</h3>
        <p className="text-[12px] text-slate-500 mt-1">Admin can publish success stories via the Verification Hub. Once added, they&apos;ll appear here for sales reference.</p>
      </Card>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="sales-tab-content-cases">
      {cases.map((c, i) => <SampleCaseCard key={c.id || i} c={c} />)}
    </div>
  );
}

function SampleCaseCard({ c }) {
  const outcomeColor = ((c.outcome || '').toLowerCase().includes('grant') || (c.outcome || '').toLowerCase().includes('approv'))
    ? 'bg-emerald-100 text-emerald-700'
    : (c.outcome || '').toLowerCase().includes('refus')
      ? 'bg-rose-100 text-rose-700'
      : 'bg-slate-100 text-slate-600';
  return (
    <Card className="p-4 print-card" data-testid="sales-sample-case">
      <div className="flex items-start justify-between mb-2 gap-2">
        <div>
          <p className="text-[11px] uppercase text-slate-500 mb-0.5">
            {c.client_age && <>Age {c.client_age} · </>}
            {c.visa_subclass && <>Visa {c.visa_subclass}</>}
          </p>
          <h4 className="font-semibold text-[13px] text-slate-800 line-clamp-2">{c.profile_summary || 'Anonymised client case'}</h4>
        </div>
        {c.outcome && <Badge className={`text-[10px] font-semibold ${outcomeColor}`}>{c.outcome}</Badge>}
      </div>
      <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-2">
        {c.timeline_months != null && <span className="inline-flex items-center gap-0.5"><Clock className="h-3 w-3" />{c.timeline_months} months</span>}
        {c.notes && <span className="line-clamp-1">· {c.notes}</span>}
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════
   Small helpers
   ════════════════════════════════════════════════════════════════ */
function SectionTitle({ icon, children, className = '' }) {
  return (
    <h3 className={`flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide ${className}`} style={{ color: BRAND.forest }}>
      {icon}{children}
    </h3>
  );
}

function EmptyHint({ children }) {
  return <p className="text-[12px] text-slate-400 italic mt-2">{children}</p>;
}

function EmptyCard({ children, testid }) {
  return (
    <Card className="p-8 text-center print-card" data-testid={testid}>
      <p className="text-[13px] text-slate-500">{children}</p>
    </Card>
  );
}

function SkeletonDetail() {
  return (
    <div className="min-h-screen" style={{ background: BRAND.warm }}>
      <div className="border-b border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-start gap-4">
            <div className="w-24 h-14 rounded-lg animate-pulse" style={{ background: BRAND.cream }} />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-32 bg-slate-100 rounded animate-pulse" />
              <div className="h-7 w-72 bg-slate-200 rounded animate-pulse" />
              <div className="h-3 w-56 bg-slate-100 rounded animate-pulse" />
            </div>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="h-8 w-96 bg-slate-100 rounded-full animate-pulse mb-6" />
        <div className="grid grid-cols-3 gap-4">
          <div className="h-64 bg-white rounded-lg animate-pulse col-span-2" />
          <div className="h-64 bg-white rounded-lg animate-pulse" />
        </div>
      </div>
    </div>
  );
}
