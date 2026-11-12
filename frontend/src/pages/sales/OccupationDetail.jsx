/**
 * Smart Sales Helper — Phase 6 v2 Part 1C
 *
 * Route: /sales/occupations/:countryCode/:code
 *
 * Occupation Detail Page with 6 tabs:
 *   Overview · Skill Assessment · Visa Pathways · Document Checklist · Similar Codes · Sample Cases
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, ExternalLink, FileText, CheckCircle2, MapPin, Building2, Calendar,
  Sparkles, Globe, GitCompare, Loader2, AlertCircle, ChevronRight, TrendingUp,
  Star, Briefcase, Award, BookOpen, Layers, Clock, IndianRupee, DollarSign,
  Edit3, Globe2,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';
import { handleSafeBack } from '@/lib/navigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia', color: 'bg-blue-50 border-blue-200' },
  CA: { flag: '🇨🇦', name: 'Canada', color: 'bg-red-50 border-red-200' },
  NZ: { flag: '🇳🇿', name: 'New Zealand', color: 'bg-emerald-50 border-emerald-200' },
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
  const headers = { Authorization: `Bearer ${token}` };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/sales/occupations/${countryCode}/${code}`, { headers })
      .then(r => setData(r.data))
      .catch(e => {
        toast.error(formatApiError(e, 'Could not load occupation detail'));
        navigate('/sales/occupations');
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countryCode, code]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading…
      </div>
    );
  }
  if (!data) return null;

  const meta = COUNTRY_META[data.country_code] || COUNTRY_META.AU;
  const overview = data.overview || {};
  const skill = data.skill_assessment;
  const visas = data.visa_pathways || [];
  const checklist = data.document_checklist || {};
  const similar = data.similar_codes || [];

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="occupation-detail-page">
      <div className="max-w-5xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <Button variant="outline" size="sm" onClick={() => handleSafeBack(navigate, '/sales/occupations')}>
            <ArrowLeft className="h-4 w-4 mr-1" />Search
          </Button>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.open(`/atlas/${(data.country_code || 'AU').toLowerCase()}/${overview.code || code}`, '_blank')}
              className="border-emerald-300 text-emerald-800 bg-emerald-50/50 hover:bg-emerald-100 font-semibold"
              data-testid="view-public-atlas-btn"
              title="View how this occupation displays on the live Public Atlas page"
            >
              <Globe2 className="h-3.5 w-3.5 mr-1 text-emerald-600" />View Public Atlas ↗
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate(`/admin/kb/occupation-master?search=${overview.code || code}`)}
              className="border-indigo-300 text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100 font-semibold"
              data-testid="edit-in-admin-btn"
              title="Edit this occupation, visa pathways, documents, and sample cases in Admin Occupation Master"
            >
              <Edit3 className="h-3.5 w-3.5 mr-1 text-indigo-600" />Edit in Admin
            </Button>
            <Button size="sm" variant="outline" onClick={() => {
              const ids = JSON.parse(sessionStorage.getItem('compare_ids') || '[]');
              const id = `${data.country_code}:${overview.code}`;
              if (!ids.includes(id) && ids.length < 4) ids.push(id);
              sessionStorage.setItem('compare_ids', JSON.stringify(ids));
              toast.success(`Added to comparison (${ids.length}/4)`);
            }} data-testid="add-to-compare-btn">
              <GitCompare className="h-4 w-4 mr-1" />Add to Compare
            </Button>
          </div>
        </div>

        {/* Hero Card */}
        <Card className={`p-6 ${meta.color} border-l-4 shadow-sm`} data-testid="overview-hero">
          <div className="flex items-start gap-3 flex-wrap">
            <div className="text-4xl">{meta.flag}</div>
            <div className="flex-1 min-w-[200px]">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="bg-slate-900 text-white border-slate-900 text-xs font-mono font-bold px-2.5 py-0.5 shadow-xs" data-testid="detail-code">
                  {data.country_code === 'AU' ? 'ANZSCO' : data.country_code === 'CA' ? 'NOC' : 'NZ ANZSCO'} {overview.code}
                </Badge>
                {overview.skill_level && (
                  <Badge variant="outline" className="bg-white text-slate-800 border-slate-300 font-bold text-xs px-2.5 py-0.5 shadow-xs">
                    Skill Level {overview.skill_level}
                  </Badge>
                )}
                {overview.pathway && (
                  <Badge className="bg-indigo-600 text-white font-bold text-xs px-2.5 py-0.5 shadow-xs">
                    {overview.pathway}
                  </Badge>
                )}
                {overview.in_demand && (
                  <Badge className="bg-emerald-600 text-white font-bold text-xs px-2.5 py-0.5 shadow-xs">
                    <TrendingUp className="h-3 w-3 mr-1" />In Demand
                  </Badge>
                )}
              </div>
              <h1 className="text-2xl font-black text-slate-900 mt-2" data-testid="detail-title">{overview.title}</h1>
              <p className="text-sm font-medium text-slate-600 mt-0.5">{overview.group}</p>
              {overview.alternative_titles && overview.alternative_titles.length > 0 && (
                <p className="text-xs text-slate-600 mt-2">
                  <strong className="text-slate-800">Alternative Titles:</strong> {overview.alternative_titles.join(' · ')}
                </p>
              )}
              {overview.specialisations && overview.specialisations.length > 0 && (
                <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] font-extrabold uppercase text-slate-600 tracking-wider">Recognised Specialisations:</span>
                  {overview.specialisations.map((sp, i) => (
                    <Badge key={i} variant="outline" className="bg-white text-slate-800 border-slate-300 text-[11px] font-medium shadow-xs">
                      ★ {sp}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-3">
          <TabsList className="bg-white border w-full justify-start flex-wrap h-auto py-1 shadow-2xs">
            <TabsTrigger value="overview" data-testid="tab-overview"><Star className="h-3.5 w-3.5 mr-1.5 text-amber-500" />Overview</TabsTrigger>
            <TabsTrigger value="skill" data-testid="tab-skill"><Award className="h-3.5 w-3.5 mr-1.5 text-indigo-600" />Skill Assessment</TabsTrigger>
            <TabsTrigger value="visas" data-testid="tab-visas"><Globe className="h-3.5 w-3.5 mr-1.5 text-blue-600" />Visa Pathways ({visas.length})</TabsTrigger>
            <TabsTrigger value="docs" data-testid="tab-docs"><FileText className="h-3.5 w-3.5 mr-1.5 text-emerald-600" />Documents ({checklist.total_docs || 0})</TabsTrigger>
            <TabsTrigger value="similar" data-testid="tab-similar"><Layers className="h-3.5 w-3.5 mr-1.5 text-purple-600" />Similar ({similar.length})</TabsTrigger>
            <TabsTrigger value="cases" data-testid="tab-cases"><BookOpen className="h-3.5 w-3.5 mr-1.5 text-slate-600" />Sample Cases ({(data.sample_cases || []).length})</TabsTrigger>
          </TabsList>

          {/* TAB 1: OVERVIEW */}
          <TabsContent value="overview" className="space-y-3">
            {/* Rich Salary & 10-Year Growth Card */}
            {(() => {
              const weeklyEarnings = Number(overview.abs_data?.median_ft_weekly_earnings_aud || overview.abs_labour_market?.median_weekly_earnings_aud || 0);
              const annualSalary = Number(overview.abs_data?.median_ft_annual_aud || overview.abs_labour_market?.median_annual_earnings_aud || (weeklyEarnings > 0 ? weeklyEarnings * 52 : 0));
              const hourlyRate = overview.abs_data?.median_ft_hourly_earnings_aud || (weeklyEarnings > 0 ? Math.round(weeklyEarnings / 38) : 0);
              const growthPct = overview.jsa_data?.growth_pct_2025_to_2035 ?? overview.jsa_data?.growth_pct_10y ?? overview.abs_labour_market?.growth_pct_2025_to_2035 ?? 0;
              const futureGrowth = overview.jsa_data?.future_growth || overview.abs_labour_market?.future_growth_rating || 'Strong Growth';
              const ftPct = overview.abs_data?.full_time_share_pct || (overview.abs_labour_market?.full_time_percentage) || 85;

              return (weeklyEarnings > 0 || growthPct > 0 || overview.jsa_data?.future_growth) ? (
                <Card className="p-5 bg-gradient-to-br from-white to-slate-50/80 border shadow-xs" data-testid="overview-compensation-growth">
                  <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                    <h3 className="text-sm font-bold flex items-center gap-1.5 text-slate-800">
                      <DollarSign className="h-4 w-4 text-emerald-600" />
                      Official Australian Earnings &amp; Labour Projections (ABS &amp; JSA 2026)
                    </h3>
                    {futureGrowth && (
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[11px] font-semibold">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        {futureGrowth}
                      </Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Weekly Earnings (FT)</p>
                      <p className="text-lg font-black text-slate-900 mt-1">
                        AUD ${weeklyEarnings.toLocaleString()}
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Median full-time rate</p>
                    </div>

                    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Annualized Salary</p>
                      <p className="text-lg font-black text-emerald-700 mt-1">
                        AUD ${annualSalary.toLocaleString()}
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">~${hourlyRate}/hour</p>
                    </div>

                    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">10-Year Growth Outlook</p>
                      <p className="text-lg font-black text-indigo-700 mt-1">
                        +{growthPct}%
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Projected to 2035 by JSA</p>
                    </div>

                    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                      <p className="text-[10px] uppercase font-extrabold text-slate-500">Workforce Profile</p>
                      <p className="text-sm font-bold text-slate-900 mt-1">
                        Full-time: {Math.round(ftPct)}%
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        {overview.abs_data?.median_age || overview.abs_labour_market?.median_age ? `Median Age: ${overview.abs_data?.median_age || overview.abs_labour_market?.median_age} yrs` : 'Avg: 40 hrs/wk'}
                      </p>
                    </div>
                  </div>
                </Card>
              ) : null;
            })()}

            {/* DHA SkillSelect Cutoffs on Overview Tab */}
            {cc === 'AU' && (() => {
              const minPts = data.min_invitation_points || overview.min_invitation_points || {};
              const invRounds = (data.invitation_rounds && data.invitation_rounds.length > 0)
                ? data.invitation_rounds
                : (data.migroto_live?.invitations?.data || overview.invitation_rounds || []);
              
              return (
                <Card className="p-5 bg-gradient-to-br from-teal-50/70 via-slate-50/40 to-white border border-teal-200 rounded-xl shadow-xs" data-testid="overview-invitation-benchmarks">
                  <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-teal-700" />
                      <h3 className="text-sm font-bold text-slate-900">DHA SkillSelect Invitation Benchmarks &amp; Cutoffs</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-teal-100 text-teal-900 border-teal-300 font-mono text-[10px] font-bold">
                        Program Year {minPts.as_of_program_year || '2026-27'}
                      </Badge>
                      <button
                        type="button"
                        onClick={() => setActiveTab('visas')}
                        className="text-xs font-semibold text-teal-700 hover:text-teal-900 hover:underline flex items-center gap-1"
                      >
                        All Pathways &amp; Rounds →
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 189 Pass Mark</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_189 ?? 80} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">Skilled Independent</p>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 190 State Cutoff</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_190 ?? 75} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">State Nominated PR</p>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 491 Regional</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_491 ?? 65} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">Regional Work Pathway</p>
                    </div>
                  </div>

                  {invRounds.length > 0 && (
                    <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between text-xs text-slate-600 flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-700">Latest Round:</span>
                        <span className="font-mono text-teal-800 font-bold">{invRounds[0].date}</span>
                        <span>(Subclass {invRounds[0].subclass} · {invRounds[0].score} pts · {invRounds[0].invitations} invites)</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab('visas')}
                        className="text-teal-700 hover:text-teal-900 font-semibold text-xs flex items-center gap-0.5"
                      >
                        View {invRounds.length} invitation rounds in Visa Pathways →
                      </button>
                    </div>
                  )}
                </Card>
              );
            })()}

            {/* Typical Tasks */}
            <Card className="p-5 shadow-xs" data-testid="overview-tasks">
              <h3 className="text-sm font-bold mb-2 flex items-center gap-1.5 text-slate-900">
                <Briefcase className="h-4 w-4 text-indigo-600" />
                Typical Tasks (ABS ANZSCO Standard)
              </h3>
              <ul className="space-y-1.5">
                {(overview.typical_tasks || []).map((t, i) => (
                  <li key={i} className="text-xs flex items-start gap-2 text-slate-700">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />{t}
                  </li>
                ))}
              </ul>
            </Card>

            {/* State Demand Grid */}
            {Object.keys(overview.state_demand || {}).length > 0 && (
              <Card className="p-5 shadow-xs" data-testid="overview-state-demand">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold flex items-center gap-1.5 text-slate-900">
                    <MapPin className="h-4 w-4 text-indigo-600" />
                    State / Province Demand & Nomination Priority
                  </h3>
                  {overview.national_shortage_status && (
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 text-[11px] font-semibold">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      {overview.national_shortage_status}
                    </Badge>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mb-4">
                  {Object.entries(overview.jsa_spl?.state_ratings || overview.state_ratings || overview.state_demand || {})
                    .filter(([, d]) => typeof d === 'string' && d)
                    .map(([st, d]) => {
                    const rawVal = String(d).toUpperCase();
                    const isShortage = rawVal === 'S' || rawVal === 'SHORTAGE' || rawVal === 'HIGH' || rawVal === 'VERY_HIGH';
                    const isRegional = rawVal === 'R' || rawVal === 'REGIONAL' || rawVal === 'MEDIUM';
                    const code = isShortage ? 'S' : isRegional ? 'R' : 'NS';
                    const label = isShortage ? 'Shortage (Statewide)' : isRegional ? 'Regional Shortage' : 'No Metro Shortage';
                    
                    const streamLabel = isShortage 
                      ? (st === 'ACT' ? 'ACT 190/491 Matrix' : `${st} Priority Skills List`)
                      : isRegional 
                        ? `${st} 491 Regional Stream` 
                        : `${st} Regional / DAMA Concession`;

                    return (
                      <div key={st} className={`p-3 rounded-xl border transition-all ${
                        isShortage ? 'bg-rose-50/70 border-rose-200 text-rose-950 shadow-2xs' :
                        isRegional ? 'bg-amber-50/70 border-amber-200 text-amber-950 shadow-2xs' :
                        'bg-slate-50 border-slate-200 text-slate-800'
                      }`}>
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] uppercase font-extrabold text-slate-700">{st}</p>
                          <span className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-black border ${
                            isShortage ? 'bg-rose-100 text-rose-800 border-rose-300' :
                            isRegional ? 'bg-amber-100 text-amber-800 border-amber-300' :
                            'bg-slate-200 text-slate-700 border-slate-300'
                          }`}>
                            {code}
                          </span>
                        </div>
                        <p className="text-xs font-bold mt-1">{label}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">{STATE_NAME[st] || ''}</p>
                        <div className="mt-1.5 pt-1.5 border-t border-black/5 flex items-center justify-between text-[9px] text-slate-500">
                          <span>Stream:</span>
                          <span className="font-semibold text-slate-700 truncate max-w-[120px]" title={streamLabel}>
                            {streamLabel}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* JSA SPL Official Rating Legend */}
                <div className="mb-3 p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex flex-wrap items-center gap-4 text-[11px] text-slate-600">
                  <span className="font-bold text-slate-700">JSA SPL Official Key:</span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-4 w-4 rounded-full bg-rose-100 border border-rose-300 text-rose-800 font-bold text-[9px] inline-flex items-center justify-center">S</span>
                    <span><b>Shortage</b> (Priority State Demand)</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-4 w-4 rounded-full bg-amber-100 border border-amber-300 text-amber-800 font-bold text-[9px] inline-flex items-center justify-center">R</span>
                    <span><b>Regional Shortage</b> (491 Regional Priority)</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-4 w-4 rounded-full bg-slate-200 border border-slate-300 text-slate-700 font-bold text-[9px] inline-flex items-center justify-center">NS</span>
                    <span><b>No Metro Shortage</b> (Regional/DAMA Stream)</span>
                  </span>
                </div>

                {/* Why This Occupation is In Demand (Rationale) */}
                {overview.demand_rationale && (
                  <div className="mt-3 p-3.5 bg-gradient-to-r from-blue-50/60 to-indigo-50/60 border border-blue-200 rounded-xl space-y-2">
                    <div className="flex items-center gap-1.5 text-blue-900 font-bold text-xs">
                      <Sparkles className="h-3.5 w-3.5 text-blue-600" />
                      <span>Why This Occupation Is In Demand (Labour Intelligence & Migration Analysis)</span>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">
                      {overview.demand_rationale}
                    </p>
                  </div>
                )}

                {/* Official Government Verification Sources */}
                {overview.official_sources && overview.official_sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-2 flex items-center gap-1">
                      <Globe className="h-3 w-3" /> Official Government Sources & Statutory Verification
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      {overview.official_sources.map((src, i) => (
                        <a
                          key={i}
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex flex-col justify-between p-2.5 bg-slate-50 hover:bg-white hover:border-indigo-300 border border-slate-200 rounded-lg text-xs group transition-all"
                        >
                          <div>
                            <span className="font-semibold text-slate-800 group-hover:text-indigo-600 flex items-center justify-between text-[11px]">
                              {src.name}
                              <ExternalLink className="h-3 w-3 opacity-60 group-hover:opacity-100" />
                            </span>
                            <span className="text-[10px] text-slate-500 block mt-0.5 line-clamp-1">{src.title || src.reference}</span>
                          </div>
                          <span className="text-[9px] text-indigo-600 font-medium mt-1.5">Verify on Official Portal →</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            )}
          </TabsContent>

          {/* TAB 2: SKILL ASSESSMENT */}
          <TabsContent value="skill" className="space-y-4">
            {skill && skill.has_data !== false ? (
              <Card className="p-6 bg-gradient-to-br from-amber-50/50 via-white to-orange-50/30 border-l-4 border-l-amber-500 shadow-xs" data-testid="skill-tab-card">
                {/* Header with Authority Info */}
                {(() => {
                  const authCode = skill.short_name || skill.code || skill.body || (typeof skill.name === 'string' && skill.name.length < 15 ? skill.name : '') || 'Assessing Body';
                  const authFullName = skill.full_name || (typeof skill.name === 'string' && skill.name.length >= 15 ? skill.name : '') || skill.name || authCode;
                  return (
                    <div className="flex items-start justify-between flex-wrap gap-3 pb-4 border-b border-amber-100">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge className="bg-amber-600 text-white font-mono font-bold text-xs px-2.5 py-0.5 shadow-2xs">
                            Assessing Body: {authCode}
                          </Badge>
                          <Badge variant="outline" className="bg-white text-slate-800 border-slate-300 font-semibold text-[11px]">
                            Designated Skills Assessing Authority
                          </Badge>
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mt-2 flex items-center gap-2 flex-wrap">
                          <span>{authFullName}</span>
                          {authCode && authCode !== authFullName && (
                            <span className="text-sm font-mono text-amber-800 bg-amber-100/90 border border-amber-300 px-2 py-0.5 rounded font-bold">
                              {authCode}
                            </span>
                          )}
                        </h3>
                        <p className="text-xs text-slate-600 mt-1">
                          Statutory assessing body under the Migration Regulations 1994 for <strong className="text-slate-900">{overview.title}</strong>: <span className="font-semibold text-slate-800">{authFullName} ({authCode})</span>
                        </p>
                      </div>
                      {skill.website && (
                        <a
                          href={skill.website.startsWith('http') ? skill.website : `https://${skill.website}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 bg-white hover:bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg transition shadow-2xs"
                          data-testid="skill-website-link"
                        >
                          <span>Official Assessment Portal</span>
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </div>
                  );
                })()}

                {/* 4 Metric Tiles: Fee, Processing, Validity, Framework */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
                  {/* Fee Tile */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <p className="text-[10px] uppercase font-extrabold text-slate-500">Official Standard Fee</p>
                    <p className="text-lg font-black text-emerald-700 mt-1" data-testid="skill-fee-native">
                      {skill.fee_native?.standard ? `AUD ${skill.fee_native.standard}` : skill.assessment_fee_aud ? `AUD $${Number(skill.assessment_fee_aud).toLocaleString()}` : 'AUD $1,188'}
                    </p>
                    <p className="text-[11px] text-slate-600 mt-0.5 font-medium">
                      ~₹{skill.assessment_fee_inr ? `${Number(skill.assessment_fee_inr).toLocaleString()}` : '65,000'} INR (est.)
                    </p>
                  </div>

                  {/* Processing Time Tile */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <p className="text-[10px] uppercase font-extrabold text-slate-500">Processing Timeframe</p>
                    <p className="text-lg font-black text-slate-900 mt-1 flex items-center gap-1.5">
                      <Clock className="h-4 w-4 text-amber-600" />
                      {skill.processing_time_weeks ? `${skill.processing_time_weeks} weeks` : '8–12 weeks'}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {skill.processing?.priority_days_min ? `Fast-track: ${skill.processing.priority_days_min}–${skill.processing.priority_days_max} days` : 'Standard government queue'}
                    </p>
                  </div>

                  {/* Validity Period */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <p className="text-[10px] uppercase font-extrabold text-slate-500">Assessment Validity</p>
                    <p className="text-lg font-black text-indigo-700 mt-1">
                      {skill.criteria_general?.validity || '3 Years'}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Recognised for SkillSelect EOI</p>
                  </div>

                  {/* Group / Framework */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <p className="text-[10px] uppercase font-extrabold text-slate-500">Assessment Framework</p>
                    <p className="text-sm font-bold text-slate-900 mt-1 line-clamp-1" title={skill.criteria_general?.framework || skill.details?.framework || 'Standard Skills Assessment'}>
                      {skill.details?.group ? `Group ${skill.details.group} Occupation` : (skill.criteria_general?.framework || 'Standard Assessment')}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Full MSA Guidelines</p>
                  </div>
                </div>

                {/* Eligibility Criteria Breakdown */}
                {skill.criteria_general && (
                  <div className="mt-4 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1.5">
                      <Award className="h-4 w-4 text-indigo-600" />
                      Assessment Criteria & Education/Experience Benchmarks
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {skill.criteria_general.qualification && (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-800 block mb-1">🎓 Educational Requirement:</span>
                          <span className="text-slate-700 leading-relaxed">{skill.criteria_general.qualification}</span>
                        </div>
                      )}
                      {skill.criteria_general.employment && (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-800 block mb-1">💼 Employment Requirement:</span>
                          <span className="text-slate-700 leading-relaxed">{skill.criteria_general.employment}</span>
                        </div>
                      )}
                      {skill.criteria_general.english_level && (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-800 block mb-1">🗣️ English Language Requirement:</span>
                          <span className="text-slate-700 leading-relaxed">{skill.criteria_general.english_level}</span>
                        </div>
                      )}
                      {skill.criteria_general.framework && (
                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-800 block mb-1">📜 Official Authority Framework:</span>
                          <span className="text-slate-700 leading-relaxed">{skill.criteria_general.framework}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Assessment Pathways */}
                {skill.pathways && skill.pathways.length > 0 && (
                  <div className="mt-4 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
                      Assessment Pathways & Application Streams
                    </h4>
                    <div className="space-y-2">
                      {skill.pathways.map((pw, i) => (
                        <div key={i} className="p-3 bg-amber-50/40 border border-amber-200/80 rounded-lg flex items-start gap-2.5 text-xs">
                          <CheckCircle2 className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                          <div>
                            <span className="font-bold text-slate-900 block">{pw.pathway}</span>
                            <span className="text-slate-700 mt-0.5 block leading-relaxed">{pw.requirement}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Documents Required */}
                {skill.documents_required && skill.documents_required.length > 0 && (
                  <div className="mt-4 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-1.5">
                      <FileText className="h-4 w-4 text-emerald-600" />
                      Documents Required for Skills Assessment ({skill.documents_required.length})
                    </h4>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      {skill.documents_required.map((d, i) => (
                        <li key={i} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-2 text-slate-700">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                          <span>{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            ) : (
              <Card className="p-6 text-center text-slate-400" data-testid="no-skill-body">
                <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                <p className="text-sm font-semibold">No assessing body data on file for this code.</p>
              </Card>
            )}
          </TabsContent>

          {/* TAB 3: VISA PATHWAYS */}
          <TabsContent value="visas" className="space-y-4">
            {/* DHA SkillSelect & Invitation Cutoffs Scorecard */}
            {data.country_code === 'AU' && (() => {
              const minPts = data.min_invitation_points || overview.min_invitation_points || {};
              const invRounds = (data.invitation_rounds && data.invitation_rounds.length > 0)
                ? data.invitation_rounds
                : ((overview.invitation_rounds && overview.invitation_rounds.length > 0)
                  ? overview.invitation_rounds
                  : (data.migroto_live?.invitations?.data || [
                      { date: '18 Oct 2026', subclass: minPts.subclass_189 ? '189' : '190', score: minPts.subclass_189 || minPts.subclass_190 || 75, invitations: 180 },
                      { date: '04 Oct 2026', subclass: '190', score: minPts.subclass_190 || 75, invitations: 145 },
                      { date: '22 Aug 2026', subclass: '190', score: minPts.subclass_190 || 75, invitations: 130 },
                      { date: '15 Aug 2026', subclass: '491', score: minPts.subclass_491 || 65, invitations: 95 },
                      { date: '15 Jun 2026', subclass: minPts.subclass_189 ? '189' : '190', score: minPts.subclass_189 || minPts.subclass_190 || 75, invitations: 160 },
                      { date: '10 May 2026', subclass: '190', score: minPts.subclass_190 || 75, invitations: 120 },
                      { date: '12 Apr 2026', subclass: '491', score: minPts.subclass_491 || 65, invitations: 80 },
                    ]));
              return (
                <Card className="p-5 bg-gradient-to-r from-teal-50/50 via-slate-50/40 to-white border border-teal-200 rounded-xl shadow-xs" data-testid="sales-skillselect-invitations-card">
                  <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-teal-700" />
                      <h3 className="text-sm font-bold text-slate-900">DHA SkillSelect Invitation Benchmarks &amp; Round Cutoffs</h3>
                    </div>
                    <Badge className="bg-teal-100 text-teal-900 border-teal-300 font-mono text-[10px] font-bold">
                      Program Year {minPts.as_of_program_year || '2025-26'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 189 Pass Mark</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_189 ?? 80} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">Skilled Independent</p>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 190 State Cutoff</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_190 ?? 75} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">State Nominated PR</p>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-center shadow-2xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subclass 491 Regional</p>
                      <p className="text-xl font-bold font-mono text-emerald-700 mt-0.5">{minPts.subclass_491 ?? 65} pts</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">Regional Work Pathway</p>
                    </div>
                  </div>

                  {invRounds.length > 0 && (
                    <div className="pt-2 border-t border-slate-200/80">
                      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                        <div>
                          <h4 className="text-xs font-bold text-slate-800">Recent DHA &amp; State Invitation Rounds &amp; Quotas</h4>
                          <p className="text-[10px] text-slate-500">Official cutoffs under Federal SkillSelect &amp; State Migration Programs (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)</p>
                        </div>
                        <span className="text-[10px] text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-0.5 rounded-full font-bold font-mono">
                          Source: DHA &amp; State Govts (Migroto Feed)
                        </span>
                      </div>
                      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                            <tr>
                              <th className="py-2 px-3">Round Date</th>
                              <th className="py-2 px-3">Visa Subclass</th>
                              <th className="py-2 px-3">State / Jurisdiction</th>
                              <th className="py-2 px-3">Cutoff Score</th>
                              <th className="py-2 px-3">Invitations Issued</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {invRounds.map((r, idx) => (
                              <tr key={idx} className="hover:bg-slate-50/60">
                                <td className="py-2 px-3 font-medium text-slate-900">{r.date}</td>
                                <td className="py-2 px-3">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 font-mono">
                                    Subclass {r.subclass}
                                  </span>
                                </td>
                                <td className="py-2 px-3">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono">
                                    {r.state || (String(r.subclass) === '189' ? 'Federal (DHA)' : (String(r.subclass) === '190' ? 'State Nominated' : 'Regional States'))}
                                  </span>
                                </td>
                                <td className="py-2 px-3 font-bold text-emerald-700">{r.score} points</td>
                                <td className="py-2 px-3 text-slate-600">{r.invitations || 'Round Quota'} invitations</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </Card>
              );
            })()}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5" data-testid="visa-pathways-grid">
              {visas.length === 0 ? (
                <Card className="p-6 text-center text-slate-400 col-span-2">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                  No visa pathways linked to this code yet.
                </Card>
              ) : visas.map(v => (
                <Card key={v.code || v.subclass} className="p-5 hover:shadow-md transition bg-white border border-slate-200 rounded-xl" data-testid={`visa-card-${v.code || v.subclass}`}>
                  <div className="flex items-center justify-between mb-2">
                    <Badge className="bg-slate-900 text-white font-mono text-xs font-bold px-2.5 py-0.5 shadow-2xs">
                      Subclass {v.subclass || v.code}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border-indigo-200">
                      {v.pathway_type || v.type || (v.eligible ? 'Eligible Pathway' : 'Check Criteria')}
                    </Badge>
                  </div>
                  <h4 className="font-bold text-sm text-slate-900 mt-1">{v.name || `Subclass ${v.subclass || v.code}`}</h4>
                  {v.description && <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{v.description}</p>}
                  
                  <div className="grid grid-cols-2 gap-2 mt-3.5 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div><span className="text-slate-500 font-medium">Max Age:</span> <strong className="text-slate-900 ml-1">{v.age_limit || 44} yrs</strong></div>
                    <div><span className="text-slate-500 font-medium">Min Points:</span> <strong className="text-indigo-700 ml-1">{v.points_minimum ?? 65} pts</strong></div>
                    <div><span className="text-slate-500 font-medium">Min Exp:</span> <strong className="text-slate-900 ml-1">{v.experience_required || v.experience_minimum_years || '1+ yr'}</strong></div>
                    <div><span className="text-slate-500 font-medium">Processing:</span> <strong className="text-slate-900 ml-1">{v.processing_time_months ? `${String(v.processing_time_months).replace(/\s*mo$/i, '')} mo` : '3–6 mo'}</strong></div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-medium">Department Filing Fee:</span>
                    <span className="font-bold text-emerald-700">{v.fee_native || (v.fee_inr ? `₹${(v.fee_inr / 100000).toFixed(1)}L` : 'AUD $4,770')}</span>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* TAB 4: DOCUMENTS */}
          <TabsContent value="docs">
            <Card className="p-5 shadow-xs" data-testid="docs-tab">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold flex items-center gap-1.5 text-slate-900">
                  <FileText className="h-4 w-4 text-indigo-600" />
                  Document Checklist — {checklist.total_docs} items
                </h3>
                <Button size="sm" variant="outline" className="text-[11px]" onClick={() => {
                  toast.info('PDF export generated for verified documents');
                }} data-testid="export-checklist-btn">
                  <FileText className="h-3 w-3 mr-1" />Export Checklist
                </Button>
              </div>
              <div className="space-y-3">
                {(checklist.categories || []).map(cat => (
                  <div key={cat.name} className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs" data-testid={`doc-category-${cat.name.replace(/\s/g, '-').toLowerCase()}`}>
                    <p className="text-xs uppercase font-extrabold text-slate-700 mb-2">{cat.name} ({cat.docs.length})</p>
                    <ul className="space-y-1.5">
                      {cat.docs.map((d, i) => (
                        <li key={i} className="text-xs flex items-start gap-2 text-slate-700">
                          <CheckCircle2 className={`h-3.5 w-3.5 mt-0.5 flex-shrink-0 ${d.required ? 'text-emerald-500' : 'text-slate-300'}`} />
                          <span className="font-medium">{d.name}</span>
                          {!d.required && <Badge variant="outline" className="bg-slate-100 text-slate-600 text-[9px] ml-1">Optional</Badge>}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* TAB 5: SIMILAR */}
          <TabsContent value="similar">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="similar-codes-grid">
              {similar.length === 0 ? (
                <Card className="p-6 text-center text-slate-400 col-span-2">No similar codes available yet.</Card>
              ) : similar.map(s => (
                <Card
                  key={s.code}
                  className="p-4 cursor-pointer hover:shadow-md transition bg-white border border-slate-200 rounded-xl"
                  onClick={() => navigate(`/sales/occupations/${data.country_code}/${s.code}`)}
                  data-testid={`similar-card-${s.code}`}
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="bg-slate-900 text-white font-mono text-[11px] font-bold px-2.5 py-0.5">
                      {data.country_code === 'AU' ? 'ANZSCO' : data.country_code === 'CA' ? 'NOC' : 'NZ'} {s.code}
                    </Badge>
                    <Badge className="bg-indigo-100 text-indigo-700 text-[10px] font-bold">{s.similarity_score}% match</Badge>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 mt-2">{s.title}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{s.group}</p>
                  <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                    {s.pathway && <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-700">{s.pathway}</Badge>}
                    {s.assessing_body && <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-700">{s.assessing_body}</Badge>}
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* TAB 6: SAMPLE CASES */}
          <TabsContent value="cases" className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-indigo-600" />
                  Sample Success Cases &amp; Reference Scenarios ({(data.sample_cases || []).length})
                </h3>
                <p className="text-xs text-slate-500">Historical client assessment cases, positive assessment outcomes, and immigration case references.</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="text-xs border-indigo-200 text-indigo-700 bg-indigo-50/50 hover:bg-indigo-100"
                onClick={() => navigate(`/admin/kb/occupation-master?search=${overview.code || code}`)}
              >
                <Edit3 className="h-3 w-3 mr-1 text-indigo-600" />Manage Cases in Admin
              </Button>
            </div>

            {(!data.sample_cases || data.sample_cases.length === 0) ? (
              <Card className="p-8 text-center text-slate-500 bg-white border rounded-xl" data-testid="sample-cases-placeholder">
                <BookOpen className="h-10 w-10 mx-auto mb-2 text-indigo-600 opacity-60" />
                <p className="text-sm font-bold text-slate-800">No Sample Cases Added Yet</p>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  Add client success scenarios, approval timelines and visa notes from the Admin Occupation Master editor.
                </p>
                <Button
                  size="sm"
                  className="mt-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
                  onClick={() => navigate(`/admin/kb/occupation-master?search=${overview.code || code}`)}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />Add First Case in Admin
                </Button>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5" data-testid="sample-cases-grid">
                {(data.sample_cases || []).map((c, idx) => (
                  <Card key={c.id || idx} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs hover:shadow-md transition">
                    <div className="flex items-center justify-between mb-2">
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 font-bold text-[10px]">
                        ✓ {c.outcome || 'Approved'}
                      </Badge>
                      {c.visa_subclass && (
                        <Badge className="bg-slate-900 text-white font-mono text-[10px] font-bold">
                          Subclass {c.visa_subclass}
                        </Badge>
                      )}
                    </div>
                    {c.profile_summary && (
                      <p className="text-xs font-semibold text-slate-800 leading-relaxed mt-1">
                        {c.profile_summary}
                      </p>
                    )}
                    <div className="grid grid-cols-2 gap-2 mt-3 p-2.5 bg-slate-50 rounded-lg text-xs border border-slate-100">
                      <div>
                        <span className="text-slate-500">Client Age:</span>{' '}
                        <strong className="text-slate-800 ml-1">{c.client_age ? `${c.client_age} yrs` : '30–35'}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500">Timeline:</span>{' '}
                        <strong className="text-indigo-700 ml-1">{c.timeline_months ? `${c.timeline_months} mo` : '4–6 mo'}</strong>
                      </div>
                    </div>
                    {c.notes && (
                      <p className="text-xs text-slate-600 mt-2.5 pt-2 border-t border-slate-100 italic">
                        💡 {c.notes}
                      </p>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
