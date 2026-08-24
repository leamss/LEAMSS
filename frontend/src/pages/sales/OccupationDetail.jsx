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
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

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
          <Button variant="outline" size="sm" onClick={() => navigate('/sales/occupations')}>
            <ArrowLeft className="h-4 w-4 mr-1" />Search
          </Button>
          <div className="flex gap-2">
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
        <Card className={`p-6 ${meta.color} border-l-4`} data-testid="overview-hero">
          <div className="flex items-start gap-3 flex-wrap">
            <div className="text-4xl">{meta.flag}</div>
            <div className="flex-1 min-w-[200px]">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className="bg-white text-slate-700 border text-[11px] font-mono" data-testid="detail-code">
                  {data.country_code === 'AU' ? 'ANZSCO' : data.country_code === 'CA' ? 'NOC' : 'NZ ANZSCO'} {overview.code}
                </Badge>
                {overview.skill_level && (
                  <Badge className="bg-white text-slate-700 border text-[10px]">Skill Level {overview.skill_level}</Badge>
                )}
                {overview.pathway && (
                  <Badge className="bg-indigo-100 text-indigo-700 text-[10px]">{overview.pathway}</Badge>
                )}
                {overview.in_demand && (
                  <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">
                    <TrendingUp className="h-2.5 w-2.5 mr-0.5" />In Demand
                  </Badge>
                )}
              </div>
              <h1 className="text-2xl font-bold mt-2" data-testid="detail-title">{overview.title}</h1>
              <p className="text-sm text-slate-600 mt-1">{overview.group}</p>
              {overview.alternative_titles && overview.alternative_titles.length > 0 && (
                <p className="text-[11px] text-slate-500 italic mt-2">
                  <strong>Also known as:</strong> {overview.alternative_titles.join(' · ')}
                </p>
              )}
            </div>
          </div>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="space-y-3">
          <TabsList className="bg-white border w-full justify-start flex-wrap h-auto py-1">
            <TabsTrigger value="overview" data-testid="tab-overview"><Star className="h-3 w-3 mr-1" />Overview</TabsTrigger>
            <TabsTrigger value="skill" data-testid="tab-skill"><Award className="h-3 w-3 mr-1" />Skill Assessment</TabsTrigger>
            <TabsTrigger value="visas" data-testid="tab-visas"><Globe className="h-3 w-3 mr-1" />Visa Pathways ({visas.length})</TabsTrigger>
            <TabsTrigger value="docs" data-testid="tab-docs"><FileText className="h-3 w-3 mr-1" />Documents ({checklist.total_docs || 0})</TabsTrigger>
            <TabsTrigger value="similar" data-testid="tab-similar"><Layers className="h-3 w-3 mr-1" />Similar ({similar.length})</TabsTrigger>
            <TabsTrigger value="cases" data-testid="tab-cases"><BookOpen className="h-3 w-3 mr-1" />Sample Cases</TabsTrigger>
          </TabsList>

          {/* TAB 1: OVERVIEW */}
          <TabsContent value="overview" className="space-y-3">
            <Card className="p-5" data-testid="overview-tasks">
              <h3 className="text-sm font-bold mb-2 flex items-center gap-1"><Briefcase className="h-4 w-4 text-indigo-600" />Typical Tasks</h3>
              <ul className="space-y-1.5">
                {(overview.typical_tasks || []).map((t, i) => (
                  <li key={i} className="text-xs flex items-start gap-2">
                    <CheckCircle2 className="h-3 w-3 text-emerald-500 mt-0.5 flex-shrink-0" />{t}
                  </li>
                ))}
              </ul>
            </Card>

            {Object.keys(overview.state_demand || {}).length > 0 && (
              <Card className="p-5" data-testid="overview-state-demand">
                <h3 className="text-sm font-bold mb-3 flex items-center gap-1"><MapPin className="h-4 w-4 text-indigo-600" />State / Province Demand</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {Object.entries(overview.state_demand)
                    .filter(([, d]) => typeof d === 'string' && d)
                    .map(([st, d]) => {
                    const isHigh = d === 'very_high' || d === 'high';
                    return (
                      <div key={st} className={`p-2 rounded border ${isHigh ? 'bg-emerald-50 border-emerald-200' : d === 'medium' ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'}`}>
                        <p className="text-[10px] uppercase font-bold text-slate-500">{st}</p>
                        <p className="text-xs font-bold capitalize">{d.replace('_', ' ')}</p>
                        <p className="text-[9px] text-slate-400">{STATE_NAME[st] || ''}</p>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}
          </TabsContent>

          {/* TAB 2: SKILL ASSESSMENT */}
          <TabsContent value="skill">
            {skill ? (
              <Card className="p-5 bg-amber-50 border-l-4 border-l-amber-500" data-testid="skill-tab-card">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <Award className="h-5 w-5 text-amber-600" />
                  {skill.name}
                  {skill.full_name && <span className="text-xs text-slate-500 font-normal">({skill.full_name})</span>}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  <div className="bg-white p-3 rounded border">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Official Fee</p>
                    {skill.fee_native?.label ? (
                      <>
                        <p className="text-base font-bold text-emerald-700" data-testid="skill-fee-native">
                          {skill.fee_native.currency} {skill.fee_native.standard}
                        </p>
                        <p className="text-[10px] text-slate-600 mt-1 leading-snug">{skill.fee_native.label}</p>
                      </>
                    ) : (
                      <p className="text-base font-bold">₹{((skill.assessment_fee_inr || 0) / 1000).toFixed(0)}K <span className="text-[9px] text-slate-400">(est.)</span></p>
                    )}
                  </div>
                  <div className="bg-white p-3 rounded border">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Processing Time</p>
                    <p className="text-base font-bold flex items-center gap-1">
                      <Clock className="h-4 w-4 text-amber-600" />
                      {skill.processing_time_weeks || '?'} weeks
                    </p>
                  </div>
                </div>
                {skill.website && (
                  <a href={skill.website} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline mt-3 inline-flex items-center gap-1" data-testid="skill-website-link">
                    {skill.website.replace(/^https?:\/\//, '')} <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {skill.documents_required?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-[11px] uppercase font-bold text-slate-500 mb-2">Documents Required for Skill Assessment</p>
                    <ul className="space-y-1">
                      {skill.documents_required.map((d, i) => (
                        <li key={i} className="text-xs flex items-start gap-2">
                          <FileText className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />{d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {skill.criteria_general && Object.keys(skill.criteria_general).length > 0 && (
                  <div className="mt-4 bg-white p-3 rounded border">
                    <p className="text-[11px] uppercase font-bold text-slate-500 mb-2">Eligibility Criteria</p>
                    <ul className="text-xs space-y-0.5">
                      {Object.entries(skill.criteria_general).map(([k, v]) => (
                        <li key={k}><strong className="capitalize">{k.replace(/_/g, ' ')}:</strong> {String(v)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            ) : (
              <Card className="p-6 text-center text-slate-400" data-testid="no-skill-body">
                <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                <p className="text-sm">No assessing body data on file for this code.</p>
              </Card>
            )}
          </TabsContent>

          {/* TAB 3: VISA PATHWAYS */}
          <TabsContent value="visas">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="visa-pathways-grid">
              {visas.length === 0 ? (
                <Card className="p-6 text-center text-slate-400 col-span-2">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                  No visa pathways linked to this code yet.
                </Card>
              ) : visas.map(v => (
                <Card key={v.code} className="p-4 hover:shadow-md transition" data-testid={`visa-card-${v.code}`}>
                  <div className="flex items-center justify-between mb-2">
                    <Badge className="bg-indigo-100 text-indigo-700 font-mono text-[10px]">{v.code}</Badge>
                    <Badge variant="outline" className="text-[9px]">{v.pathway_type || v.type}</Badge>
                  </div>
                  <h4 className="font-bold text-sm">{v.name}</h4>
                  {v.description && <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{v.description}</p>}
                  <div className="grid grid-cols-2 gap-2 mt-3 text-[11px]">
                    {v.age_limit && <div><span className="text-slate-500">Max Age:</span> <strong>{v.age_limit}</strong></div>}
                    {v.points_minimum !== undefined && v.points_minimum !== null && (
                      <div><span className="text-slate-500">Min Points:</span> <strong>{v.points_minimum}</strong></div>
                    )}
                    {v.experience_minimum_years !== undefined && v.experience_minimum_years !== null && (
                      <div><span className="text-slate-500">Min Exp:</span> <strong>{v.experience_minimum_years}+ yrs</strong></div>
                    )}
                    {v.processing_time_months && (
                      <div><span className="text-slate-500">Time:</span> <strong>{v.processing_time_months} mo</strong></div>
                    )}
                  </div>
                  {v.fee_inr && (
                    <p className="text-[10px] text-slate-500 mt-2">Govt fee: ₹{(v.fee_inr / 100000).toFixed(1)}L</p>
                  )}
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* TAB 4: DOCUMENTS */}
          <TabsContent value="docs">
            <Card className="p-5" data-testid="docs-tab">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold flex items-center gap-1">
                  <FileText className="h-4 w-4 text-indigo-600" />
                  Document Checklist — {checklist.total_docs} items
                </h3>
                <Button size="sm" variant="outline" className="text-[11px]" onClick={() => {
                  toast.info('PDF export coming in Part 3 (workflow integration)');
                }} data-testid="export-checklist-btn">
                  <FileText className="h-3 w-3 mr-1" />Export PDF
                </Button>
              </div>
              <div className="space-y-3">
                {(checklist.categories || []).map(cat => (
                  <div key={cat.name} className="bg-white p-3 rounded border" data-testid={`doc-category-${cat.name.replace(/\s/g, '-').toLowerCase()}`}>
                    <p className="text-xs uppercase font-bold text-slate-500 mb-2">{cat.name} ({cat.docs.length})</p>
                    <ul className="space-y-1">
                      {cat.docs.map((d, i) => (
                        <li key={i} className="text-xs flex items-start gap-2">
                          <CheckCircle2 className={`h-3 w-3 mt-0.5 flex-shrink-0 ${d.required ? 'text-emerald-500' : 'text-slate-300'}`} />
                          {d.name}
                          {!d.required && <Badge className="bg-slate-100 text-slate-500 text-[8px] ml-1">Optional</Badge>}
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
                  className="p-3 cursor-pointer hover:shadow-md transition"
                  onClick={() => navigate(`/sales/occupations/${data.country_code}/${s.code}`)}
                  data-testid={`similar-card-${s.code}`}
                >
                  <Badge className="bg-white border text-[10px] font-mono">{s.code}</Badge>
                  <h4 className="text-sm font-bold mt-2">{s.title}</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">{s.group}</p>
                  <div className="flex items-center gap-1 mt-2 flex-wrap">
                    {s.pathway && <Badge variant="outline" className="text-[9px]">{s.pathway}</Badge>}
                    {s.assessing_body && <Badge variant="outline" className="text-[9px]">{s.assessing_body}</Badge>}
                    <Badge className="bg-indigo-100 text-indigo-700 text-[9px] ml-auto">{s.similarity_score}% similar</Badge>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* TAB 6: SAMPLE CASES (placeholder for future) */}
          <TabsContent value="cases">
            <Card className="p-8 text-center text-slate-400" data-testid="sample-cases-placeholder">
              <BookOpen className="h-10 w-10 mx-auto mb-2" />
              <p className="text-sm font-medium">Sample success cases coming soon</p>
              <p className="text-xs mt-1">Real client success stories for this occupation will appear here.</p>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
