/**
 * Smart Sales Helper — Phase 6 v2 Part 2
 * Eligibility Calculator (Rule-Based, NO LLM)
 *
 * Route: /sales/calculator
 *
 * Two-pane UI:
 *   • LEFT: Profile form (7 steps, conditional spouse, conditional state nomination)
 *   • RIGHT: Live points breakdown + visa eligibility + recommendation
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, Calculator, Sparkles, User, Heart, Briefcase, GraduationCap, MessageSquare,
  CheckCircle2, AlertCircle, XCircle, Search, Globe, MapPin, Trophy, Loader2,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MARITAL_OPTIONS = [
  { v: 'single', l: 'Single' },
  { v: 'married', l: 'Married' },
  { v: 'de_facto', l: 'De facto' },
  { v: 'separated', l: 'Separated' },
  { v: 'divorced', l: 'Divorced' },
  { v: 'widowed', l: 'Widowed' },
];

const QUALIFICATIONS = [
  { v: 'doctorate', l: 'Doctorate / PhD' },
  { v: 'master', l: "Master's Degree" },
  { v: 'bachelor', l: "Bachelor's Degree" },
  { v: 'diploma', l: 'Diploma' },
  { v: 'trade', l: 'Trade Qualification' },
  { v: 'high_school', l: 'High School' },
];

const CONTRIBUTION_OPTIONS = [
  { v: 'skill_assessment', l: 'Spouse Skill Assessment + Work Exp (+10)' },
  { v: 'english_only', l: 'Spouse Competent English Only (+5)' },
  { v: 'non_contributing', l: "Spouse won't contribute (0)" },
  { v: 'australian_pr_citizen', l: 'Spouse is AU PR/Citizen (+10)' },
];

const AU_VISAS = [
  { v: '189', l: 'Subclass 189 (Independent Skilled)' },
  { v: '190', l: 'Subclass 190 (State Nominated)' },
  { v: '491', l: 'Subclass 491 (Regional Provisional)' },
];

const AU_STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'];


export default function EligibilityCalculator() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [data, setData] = useState({
    client_name: '',
    marital_status: '',
    spouse_will_migrate: 'yes',
    spouse_contribution: '',
    country: 'AU',
    visa_subclass: '189',
    occupation_code: '',
    occupation_title: '',
    occupation_body: '',
    occupation_pathway: '',

    // Primary
    age: '',
    ielts_overall: '',
    ielts_listening: '',
    ielts_reading: '',
    ielts_writing: '',
    ielts_speaking: '',
    years_experience_total: '',
    years_experience_australia: '',
    years_experience_canada: '',
    qualification: '',
    australian_study_2_years: false,
    specialist_education_stem_au: false,
    professional_year_completed: false,
    naati_accredited: false,
    regional_study_au: false,

    // State nomination (AU)
    state_nominated: false,
    state_code: '',

    // Spouse
    spouse_age: '',
    spouse_ielts_overall: '',
    spouse_ielts_listening: '',
    spouse_ielts_reading: '',
    spouse_ielts_writing: '',
    spouse_ielts_speaking: '',
    spouse_qualification: '',
    spouse_profession: '',
    spouse_years_experience: '',

    // Canada-specific
    canadian_work_years: '',
    provincial_nomination: false,
    job_offer_noc_00: false,
    job_offer_noc_0_a_b: false,
    canadian_education_3plus_years: false,
    canadian_education_1_2_years: false,
    sibling_in_canada: false,
    french_proficiency_clb_7: false,

    // NZ-specific
    nz_skilled_employment_current: false,
    nz_job_offer: false,
    regional_employment_nz: false,
  });
  const [result, setResult] = useState(null);
  const [calculating, setCalculating] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const update = (field, val) => setData(d => ({ ...d, [field]: val }));

  // Build the profile shape that the backend expects
  const profile = useMemo(() => buildProfile(data), [data]);

  const runCalculation = useCallback(async () => {
    setCalculating(true);
    try {
      const r = await axios.post(`${API}/sales/calculator/calculate`, {
        profile,
        country: data.country,
        visa_subclass: data.visa_subclass,
      }, { headers });
      setResult(r.data);
    } catch (e) {
      console.warn('Calc error', e);
    } finally { setCalculating(false); }
  }, [profile, data.country, data.visa_subclass, headers]);

  // Live calculation — debounced. Re-runs whenever runCalculation ref changes
  // (i.e., whenever profile, country, visa_subclass, or headers change).
  useEffect(() => {
    if (!data.age && !data.qualification) return;
    const t = setTimeout(() => runCalculation(), 300);
    return () => clearTimeout(t);
  }, [runCalculation, data.age, data.qualification]);

  const isMarried = data.marital_status === 'married' || data.marital_status === 'de_facto';
  const spouseSection = isMarried && data.spouse_will_migrate === 'yes' && data.spouse_contribution !== 'non_contributing';

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="calculator-page">
      <div className="max-w-7xl mx-auto space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate('/sales/occupations')}>
              <ArrowLeft className="h-4 w-4 mr-1" />Occupations
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Calculator className="h-7 w-7 text-indigo-600" />Eligibility Calculator
              </h1>
              <p className="text-sm text-slate-500">100% deterministic · Official rules · Live calc · NO LLM</p>
            </div>
          </div>
          <Badge className="bg-emerald-100 text-emerald-700">
            <Sparkles className="h-3 w-3 mr-1" />Rule-Based · Real-time
          </Badge>
        </div>

        {/* Two-pane layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* LEFT PANE: Form (3 cols) */}
          <div className="lg:col-span-3 space-y-3" data-testid="form-pane">
            {/* STEP 1: Quick Setup */}
            <Card className="p-4" data-testid="step-1-setup">
              <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                <span className="w-5 h-5 bg-indigo-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold">1</span>
                Quick Setup
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Field label="Client Name">
                  <Input value={data.client_name} onChange={e => update('client_name', e.target.value)} placeholder="e.g., Rajesh Kumar" data-testid="client-name" />
                </Field>
                <Field label="Marital Status *">
                  <Select value={data.marital_status} onValueChange={v => update('marital_status', v)}>
                    <SelectTrigger data-testid="marital-status"><SelectValue placeholder="Select…" /></SelectTrigger>
                    <SelectContent>{MARITAL_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
                  </Select>
                </Field>
              </div>
            </Card>

            {/* STEP 2: Spouse Configuration (conditional) */}
            {isMarried && (
              <Card className="p-4 border-l-4 border-l-pink-400" data-testid="step-2-spouse-config">
                <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                  <span className="w-5 h-5 bg-pink-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold">2</span>
                  <Heart className="h-3.5 w-3.5 text-pink-500" />Spouse Configuration
                </h2>
                <div className="space-y-3">
                  <Field label="Will spouse be included on visa application?">
                    <Select value={data.spouse_will_migrate} onValueChange={v => update('spouse_will_migrate', v)}>
                      <SelectTrigger data-testid="spouse-will-migrate"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="yes">Yes — Spouse migrating with you</SelectItem>
                        <SelectItem value="no">No — Spouse not migrating</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                  {data.spouse_will_migrate === 'yes' && (
                    <Field label="What will spouse contribute to your points?">
                      <Select value={data.spouse_contribution} onValueChange={v => update('spouse_contribution', v)}>
                        <SelectTrigger data-testid="spouse-contribution"><SelectValue placeholder="Select contribution type…" /></SelectTrigger>
                        <SelectContent>{CONTRIBUTION_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
                      </Select>
                    </Field>
                  )}
                </div>
              </Card>
            )}

            {/* STEP 3: Country + Visa */}
            <Card className="p-4" data-testid="step-3-country">
              <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                <span className="w-5 h-5 bg-indigo-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold">3</span>
                <Globe className="h-3.5 w-3.5 text-indigo-600" />Country + Visa
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Field label="Country">
                  <Select value={data.country} onValueChange={v => { update('country', v); if (v !== 'AU') update('visa_subclass', ''); }}>
                    <SelectTrigger data-testid="country-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="AU">🇦🇺 Australia</SelectItem>
                      <SelectItem value="CA">🇨🇦 Canada</SelectItem>
                      <SelectItem value="NZ">🇳🇿 New Zealand</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                {data.country === 'AU' && (
                  <Field label="Visa Subclass">
                    <Select value={data.visa_subclass} onValueChange={v => update('visa_subclass', v)}>
                      <SelectTrigger data-testid="visa-subclass"><SelectValue /></SelectTrigger>
                      <SelectContent>{AU_VISAS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
                    </Select>
                  </Field>
                )}
              </div>
            </Card>

            {/* STEP 4: Occupation Code */}
            <Card className="p-4" data-testid="step-4-occupation">
              <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                <span className="w-5 h-5 bg-indigo-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold">4</span>
                <Briefcase className="h-3.5 w-3.5 text-indigo-600" />Occupation Code
              </h2>
              {data.occupation_code ? (
                <div className="bg-emerald-50 border border-emerald-200 p-3 rounded flex items-center justify-between">
                  <div>
                    <p className="text-xs font-mono font-bold text-emerald-900" data-testid="selected-occupation-code">{data.occupation_code}</p>
                    <p className="text-sm font-bold">{data.occupation_title}</p>
                    <p className="text-[10px] text-slate-500">{data.occupation_body} · {data.occupation_pathway}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => {
                    update('occupation_code', ''); update('occupation_title', ''); update('occupation_body', ''); update('occupation_pathway', '');
                  }} data-testid="change-occupation">Change</Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Button variant="outline" size="sm" onClick={() => setSearchOpen(true)} className="w-full" data-testid="search-occupation-btn">
                    <Search className="h-3.5 w-3.5 mr-1" />Search Occupation
                  </Button>
                  <p className="text-[10px] text-slate-500 italic">Optional — code doesn't affect points calculation but helps verify visa eligibility.</p>
                </div>
              )}
              {searchOpen && (
                <OccupationSearchModal
                  country={data.country}
                  onSelect={(occ) => {
                    update('occupation_code', occ.code);
                    update('occupation_title', occ.title);
                    update('occupation_body', occ.assessing_body);
                    update('occupation_pathway', occ.pathway);
                    setSearchOpen(false);
                  }}
                  onClose={() => setSearchOpen(false)}
                />
              )}
            </Card>

            {/* STEP 5: Primary Applicant */}
            <Card className="p-4 border-l-4 border-l-indigo-500" data-testid="step-5-primary">
              <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                <span className="w-5 h-5 bg-indigo-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold">5</span>
                <User className="h-3.5 w-3.5 text-indigo-600" />PRIMARY APPLICANT
                <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">All visa decisions based on this</Badge>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Field label="Age *">
                  <Input type="number" value={data.age} onChange={e => update('age', e.target.value)} placeholder="e.g., 32" data-testid="age" />
                </Field>
                <Field label="Highest Education *">
                  <Select value={data.qualification} onValueChange={v => update('qualification', v)}>
                    <SelectTrigger data-testid="qualification"><SelectValue placeholder="Select…" /></SelectTrigger>
                    <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
                  </Select>
                </Field>
              </div>

              <p className="text-[11px] uppercase font-bold text-slate-500 mt-3 mb-1">IELTS Scores (all 4 bands minimum)</p>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                <Field label="Overall"><Input type="number" step="0.5" value={data.ielts_overall} onChange={e => update('ielts_overall', e.target.value)} data-testid="ielts-overall" placeholder="7.5" /></Field>
                <Field label="L"><Input type="number" step="0.5" value={data.ielts_listening} onChange={e => update('ielts_listening', e.target.value)} placeholder="7.5" data-testid="ielts-l" /></Field>
                <Field label="R"><Input type="number" step="0.5" value={data.ielts_reading} onChange={e => update('ielts_reading', e.target.value)} placeholder="7.0" data-testid="ielts-r" /></Field>
                <Field label="W"><Input type="number" step="0.5" value={data.ielts_writing} onChange={e => update('ielts_writing', e.target.value)} placeholder="7.0" data-testid="ielts-w" /></Field>
                <Field label="S"><Input type="number" step="0.5" value={data.ielts_speaking} onChange={e => update('ielts_speaking', e.target.value)} placeholder="7.5" data-testid="ielts-s" /></Field>
              </div>

              <p className="text-[11px] uppercase font-bold text-slate-500 mt-3 mb-1">Experience (in nominated occupation)</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Field label="Total Years"><Input type="number" step="0.5" value={data.years_experience_total} onChange={e => update('years_experience_total', e.target.value)} placeholder="6" data-testid="exp-total" /></Field>
                {data.country === 'AU' && (
                  <Field label="In Australia"><Input type="number" step="0.5" value={data.years_experience_australia} onChange={e => update('years_experience_australia', e.target.value)} placeholder="0" data-testid="exp-au" /></Field>
                )}
                {data.country === 'CA' && (
                  <Field label="In Canada"><Input type="number" step="0.5" value={data.canadian_work_years} onChange={e => update('canadian_work_years', e.target.value)} placeholder="0" data-testid="exp-ca" /></Field>
                )}
              </div>

              {/* AU-specific bonuses */}
              {data.country === 'AU' && (
                <div className="mt-3 space-y-2 bg-blue-50 p-3 rounded">
                  <p className="text-[11px] uppercase font-bold text-blue-700">AU Bonus Points (check all that apply)</p>
                  <BonusToggle checked={data.australian_study_2_years} onChange={v => update('australian_study_2_years', v)} label="Australian Study Requirement (2+ years AU study)" pts={5} testid="bonus-au-study" />
                  <BonusToggle checked={data.specialist_education_stem_au} onChange={v => update('specialist_education_stem_au', v)} label="Specialist Education (STEM Master's/PhD at AU institution)" pts={10} testid="bonus-stem" />
                  <BonusToggle checked={data.professional_year_completed} onChange={v => update('professional_year_completed', v)} label="Professional Year Programme (PY) completed" pts={5} testid="bonus-py" />
                  <BonusToggle checked={data.naati_accredited} onChange={v => update('naati_accredited', v)} label="NAATI Accredited (Paraprofessional+)" pts={5} testid="bonus-naati" />
                  <BonusToggle checked={data.regional_study_au} onChange={v => update('regional_study_au', v)} label="Regional Study (in regional Australia)" pts={5} testid="bonus-regional" />
                </div>
              )}

              {/* AU state nomination */}
              {data.country === 'AU' && (data.visa_subclass === '190' || data.visa_subclass === '491') && (
                <div className="mt-3 bg-amber-50 p-3 rounded space-y-2">
                  <p className="text-[11px] uppercase font-bold text-amber-700">State / Territory Nomination ({data.visa_subclass})</p>
                  <BonusToggle checked={data.state_nominated} onChange={v => update('state_nominated', v)}
                    label={data.visa_subclass === '190' ? 'Nominated by a state/territory (+5 pts)' : 'Sponsored for regional 491 (+15 pts)'}
                    pts={data.visa_subclass === '190' ? 5 : 15} testid="bonus-state-nominated" />
                  {data.state_nominated && (
                    <Select value={data.state_code} onValueChange={v => update('state_code', v)}>
                      <SelectTrigger className="h-7 text-xs" data-testid="state-code"><SelectValue placeholder="Select state…" /></SelectTrigger>
                      <SelectContent>{AU_STATES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                    </Select>
                  )}
                </div>
              )}

              {/* Canada bonuses */}
              {data.country === 'CA' && (
                <div className="mt-3 space-y-2 bg-red-50 p-3 rounded">
                  <p className="text-[11px] uppercase font-bold text-red-700">Canada Additional Points</p>
                  <BonusToggle checked={data.provincial_nomination} onChange={v => update('provincial_nomination', v)} label="Provincial Nomination (PNP)" pts={600} testid="bonus-pnp" />
                  <BonusToggle checked={data.job_offer_noc_00} onChange={v => update('job_offer_noc_00', v)} label="Valid job offer (NOC 00 — senior management)" pts={200} testid="bonus-noc-00" />
                  <BonusToggle checked={data.job_offer_noc_0_a_b} onChange={v => update('job_offer_noc_0_a_b', v)} label="Valid job offer (NOC 0/A/B)" pts={50} testid="bonus-noc-0ab" />
                  <BonusToggle checked={data.canadian_education_3plus_years} onChange={v => update('canadian_education_3plus_years', v)} label="Canadian post-secondary (3+ years)" pts={30} testid="bonus-ca-edu-3" />
                  <BonusToggle checked={data.canadian_education_1_2_years} onChange={v => update('canadian_education_1_2_years', v)} label="Canadian post-secondary (1-2 years)" pts={15} testid="bonus-ca-edu-12" />
                  <BonusToggle checked={data.sibling_in_canada} onChange={v => update('sibling_in_canada', v)} label="Sibling in Canada (Citizen/PR)" pts={15} testid="bonus-sibling" />
                  <BonusToggle checked={data.french_proficiency_clb_7} onChange={v => update('french_proficiency_clb_7', v)} label="French proficiency CLB 7+" pts={50} testid="bonus-french" />
                </div>
              )}

              {/* NZ bonuses */}
              {data.country === 'NZ' && (
                <div className="mt-3 space-y-2 bg-emerald-50 p-3 rounded">
                  <p className="text-[11px] uppercase font-bold text-emerald-700">NZ Additional Factors</p>
                  <BonusToggle checked={data.nz_skilled_employment_current} onChange={v => update('nz_skilled_employment_current', v)} label="Currently in skilled employment in NZ" pts={50} testid="bonus-nz-current" />
                  <BonusToggle checked={data.nz_job_offer} onChange={v => update('nz_job_offer', v)} label="Valid skilled job offer in NZ" pts={30} testid="bonus-nz-offer" />
                  <BonusToggle checked={data.regional_employment_nz} onChange={v => update('regional_employment_nz', v)} label="Job in regional NZ (outside Auckland)" pts={30} testid="bonus-nz-regional" />
                </div>
              )}
            </Card>

            {/* STEP 6: Spouse Details (conditional) */}
            {spouseSection && (
              <Card className="p-4 border-l-4 border-l-pink-400" data-testid="step-6-spouse-details">
                <h2 className="text-sm font-bold flex items-center gap-2 mb-3">
                  <span className="w-5 h-5 bg-pink-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold">6</span>
                  <User className="h-3.5 w-3.5 text-pink-500" />SPOUSE INFORMATION
                  <Badge className="bg-pink-100 text-pink-700 text-[9px]">Used ONLY for partner points</Badge>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Field label="Spouse Age"><Input type="number" value={data.spouse_age} onChange={e => update('spouse_age', e.target.value)} data-testid="spouse-age" placeholder="30" /></Field>
                  <Field label="Spouse Education">
                    <Select value={data.spouse_qualification} onValueChange={v => update('spouse_qualification', v)}>
                      <SelectTrigger data-testid="spouse-qualification"><SelectValue placeholder="Select…" /></SelectTrigger>
                      <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
                    </Select>
                  </Field>
                </div>
                {data.spouse_contribution === 'skill_assessment' && (
                  <>
                    <Field label="Spouse Profession">
                      <Input value={data.spouse_profession} onChange={e => update('spouse_profession', e.target.value)} placeholder="e.g., Data Analyst" data-testid="spouse-profession" />
                    </Field>
                    <Field label="Spouse Years Experience">
                      <Input type="number" step="0.5" value={data.spouse_years_experience} onChange={e => update('spouse_years_experience', e.target.value)} data-testid="spouse-exp" placeholder="5" />
                    </Field>
                  </>
                )}
                {(data.spouse_contribution === 'skill_assessment' || data.spouse_contribution === 'english_only') && (
                  <>
                    <p className="text-[11px] uppercase font-bold text-slate-500 mt-3 mb-1">Spouse IELTS</p>
                    <div className="grid grid-cols-5 gap-2">
                      <Field label="Overall"><Input type="number" step="0.5" value={data.spouse_ielts_overall} onChange={e => update('spouse_ielts_overall', e.target.value)} data-testid="spouse-ielts-overall" placeholder="6.5" /></Field>
                      <Field label="L"><Input type="number" step="0.5" value={data.spouse_ielts_listening} onChange={e => update('spouse_ielts_listening', e.target.value)} placeholder="6.5" /></Field>
                      <Field label="R"><Input type="number" step="0.5" value={data.spouse_ielts_reading} onChange={e => update('spouse_ielts_reading', e.target.value)} placeholder="6.5" /></Field>
                      <Field label="W"><Input type="number" step="0.5" value={data.spouse_ielts_writing} onChange={e => update('spouse_ielts_writing', e.target.value)} placeholder="6.0" /></Field>
                      <Field label="S"><Input type="number" step="0.5" value={data.spouse_ielts_speaking} onChange={e => update('spouse_ielts_speaking', e.target.value)} placeholder="6.5" /></Field>
                    </div>
                  </>
                )}
              </Card>
            )}
          </div>

          {/* RIGHT PANE: Live Calculator */}
          <div className="lg:col-span-2 lg:sticky lg:top-3 self-start" data-testid="result-pane">
            <ResultsPane result={result} calculating={calculating} country={data.country} visaSubclass={data.visa_subclass} />
          </div>
        </div>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Live Results Pane
// ─────────────────────────────────────────────────────────────────
function ResultsPane({ result, calculating, country, visaSubclass }) {
  if (!result) {
    return (
      <Card className="p-6 text-center" data-testid="results-empty">
        <Calculator className="h-10 w-10 mx-auto mb-2 text-slate-300" />
        <p className="text-sm font-bold text-slate-600">Start filling the form</p>
        <p className="text-[11px] text-slate-400 mt-1">Your points will calculate in real time here.</p>
      </Card>
    );
  }
  const total = result.total || 0;
  const entries = Object.entries(result.breakdown || {});
  return (
    <Card className="p-4 bg-gradient-to-br from-indigo-50 to-white border-2 border-indigo-200" data-testid="results-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold flex items-center gap-1">
          <Trophy className="h-4 w-4 text-indigo-600" />Live Calculation
        </h3>
        {calculating && <Loader2 className="h-3 w-3 animate-spin text-indigo-500" />}
      </div>

      {/* Total Score Hero */}
      <div className="text-center py-4 bg-white rounded-lg border mb-3">
        <p className="text-[10px] uppercase font-bold text-slate-500">Total Points</p>
        <p className="text-5xl font-bold text-indigo-700" data-testid="total-points">{total}</p>
        <p className="text-[11px] text-slate-500 mt-1">{country} {country === 'AU' ? `Subclass ${visaSubclass}` : country === 'CA' ? 'CRS Score' : 'SMC Points'}</p>
      </div>

      {/* Breakdown */}
      <div className="space-y-1 mb-3">
        <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Breakdown</p>
        {entries.length === 0 ? (
          <p className="text-[11px] italic text-slate-400">No categories matched yet</p>
        ) : entries.map(([cat, val]) => (
          <div key={cat} className={`flex items-center justify-between text-xs p-2 rounded ${cat === 'partner' ? 'bg-pink-50' : 'bg-white border'}`} data-testid={`breakdown-${cat}`}>
            <div className="flex-1 min-w-0">
              <p className="font-medium capitalize">{cat.replace(/^ca_/, '').replace(/^nz_/, '').replace(/_/g, ' ')}</p>
              {val.note && <p className="text-[9px] text-slate-500 italic line-clamp-1">{val.note}</p>}
              {!val.note && val.bucket && <p className="text-[9px] text-slate-500">{val.bucket.replace(/_/g, ' ')}</p>}
            </div>
            <Badge className={(val.points || 0) > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>+{val.points || 0}</Badge>
          </div>
        ))}
      </div>

      {/* Visa Eligibility */}
      {result.visa_eligibility && (
        <div className="space-y-1 mb-3">
          <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Visa Eligibility</p>
          {Object.entries(result.visa_eligibility).map(([code, v]) => (
            <div key={code} className={`p-2 rounded border ${v.eligible ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`} data-testid={`visa-${code}`}>
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold flex items-center gap-1">
                  {v.eligible ? <CheckCircle2 className="h-3 w-3 text-emerald-600" /> : <XCircle className="h-3 w-3 text-rose-500" />}
                  {code}
                </p>
                <Badge className={v.eligible ? 'bg-emerald-100 text-emerald-700 text-[9px]' : 'bg-rose-100 text-rose-700 text-[9px]'}>
                  {v.eligible ? 'ELIGIBLE' : 'NOT YET'}
                </Badge>
              </div>
              <p className="text-[10px] text-slate-600 mt-0.5">Min {String(v.min_required)} · Your {v.your_score}{v.gap > 0 ? ` · Gap ${v.gap}` : ''}</p>
              {v.notes && <p className="text-[9px] text-slate-500 mt-0.5 italic">{v.notes}</p>}
            </div>
          ))}
        </div>
      )}

      {/* Recommendation */}
      {result.recommendation && (
        <div className="bg-amber-50 border-l-4 border-l-amber-500 p-2 rounded" data-testid="recommendation">
          <p className="text-[10px] uppercase font-bold text-amber-700 mb-0.5 flex items-center gap-1">
            <Sparkles className="h-3 w-3" />Recommendation
          </p>
          <p className="text-[11px] text-amber-900">{result.recommendation}</p>
        </div>
      )}
    </Card>
  );
}


// ─────────────────────────────────────────────────────────────────
// Occupation Search Modal (lightweight, integrates with sales/occupations)
// ─────────────────────────────────────────────────────────────────
function OccupationSearchModal({ country, onSelect, onClose }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  useEffect(() => {
    if (!q || q.length < 2) { setResults([]); return; }
    const t = setTimeout(() => {
      const params = new URLSearchParams({ q, limit: '8' });
      params.append('country', country);
      axios.get(`${API}/sales/occupations/search?${params}`, { headers })
        .then(r => setResults(r.data.items || []))
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, country, headers]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="occupation-search-modal">
      <Card className="max-w-xl w-full bg-white p-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 mb-3">
          <Search className="h-4 w-4 text-indigo-600" />
          <Input autoFocus placeholder="Search by code, title, alternative title…" value={q} onChange={e => setQ(e.target.value)} className="flex-1" data-testid="modal-search-input" />
          <Button variant="ghost" size="sm" onClick={onClose}><XCircle className="h-4 w-4" /></Button>
        </div>
        <div className="max-h-80 overflow-y-auto space-y-1">
          {results.length === 0 ? (
            <p className="text-xs text-slate-400 italic text-center py-4">{q.length < 2 ? 'Type at least 2 characters' : 'No results — try different keywords'}</p>
          ) : results.map(r => (
            <button
              key={r.code}
              onClick={() => onSelect(r)}
              className="w-full text-left p-2 hover:bg-indigo-50 rounded border"
              data-testid={`modal-result-${r.code}`}
            >
              <p className="text-xs font-bold">{r.code} · {r.title}</p>
              <p className="text-[10px] text-slate-500">{r.assessing_body || '-'} · {r.pathway || '-'} · {r.confidence}% match</p>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────
function Field({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] text-slate-600 mb-1 block uppercase font-bold">{label}</Label>
      {children}
    </div>
  );
}

function BonusToggle({ checked, onChange, label, pts, testid }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Switch checked={checked} onCheckedChange={onChange} data-testid={testid} />
      <span className="flex-1">{label}</span>
      <Badge className={checked ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>+{pts}</Badge>
    </div>
  );
}


function buildProfile(data) {
  const num = v => (v === '' || v === null || v === undefined) ? null : parseFloat(v);
  const primary = {
    personal: { age: num(data.age) },
    professional: {
      current_profession: data.occupation_title,
      designation: data.occupation_title,
      years_experience_total: num(data.years_experience_total),
      years_experience_australia: num(data.years_experience_australia),
    },
    education: { highest_qualification: data.qualification },
    language: {
      test_completed: !!(data.ielts_overall),
      scores: {
        overall: num(data.ielts_overall),
        listening: num(data.ielts_listening),
        reading: num(data.ielts_reading),
        writing: num(data.ielts_writing),
        speaking: num(data.ielts_speaking),
      },
    },
    au_extras: {
      australian_study_2_years: data.australian_study_2_years,
      specialist_education_stem_au: data.specialist_education_stem_au,
      professional_year_completed: data.professional_year_completed,
      naati_accredited: data.naati_accredited,
      regional_study_au: data.regional_study_au,
      state_nominated: data.state_nominated,
    },
    ca_extras: {
      canadian_work_years: num(data.canadian_work_years),
      provincial_nomination: data.provincial_nomination,
      job_offer_noc_00: data.job_offer_noc_00,
      job_offer_noc_0_a_b: data.job_offer_noc_0_a_b,
      canadian_education_3plus_years: data.canadian_education_3plus_years,
      canadian_education_1_2_years: data.canadian_education_1_2_years,
      sibling_in_canada: data.sibling_in_canada,
      french_proficiency_clb_7: data.french_proficiency_clb_7,
    },
    nz_extras: {
      nz_skilled_employment_current: data.nz_skilled_employment_current,
      nz_job_offer: data.nz_job_offer,
      regional_employment_nz: data.regional_employment_nz,
    },
  };

  let spouse = null;
  if ((data.marital_status === 'married' || data.marital_status === 'de_facto') && data.spouse_will_migrate === 'yes') {
    spouse = {
      contribution_type: data.spouse_contribution || 'not_applicable',
      is_applicant_on_visa: true,
      is_australian_pr_or_citizen: data.spouse_contribution === 'australian_pr_citizen',
      personal: { age: num(data.spouse_age) },
      professional: { current_profession: data.spouse_profession, years_experience_total: num(data.spouse_years_experience) },
      education: { highest_qualification: data.spouse_qualification },
      language: {
        scores: {
          overall: num(data.spouse_ielts_overall),
          listening: num(data.spouse_ielts_listening),
          reading: num(data.spouse_ielts_reading),
          writing: num(data.spouse_ielts_writing),
          speaking: num(data.spouse_ielts_speaking),
        },
      },
    };
  } else if (data.marital_status === 'married' || data.marital_status === 'de_facto') {
    spouse = { is_applicant_on_visa: false, contribution_type: 'australian_pr_citizen' === data.spouse_contribution ? 'australian_pr_citizen' : 'not_applicable' };
  }

  return {
    client_name: data.client_name,
    marital_status: data.marital_status,
    primary_applicant: primary,
    spouse,
  };
}
