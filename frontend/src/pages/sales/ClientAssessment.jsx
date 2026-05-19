/**
 * Smart Sales Helper — Phase 6 v2 Part 3
 * Integrated Client Assessment Workflow
 *
 * Route: /sales/client-assessment
 *
 * 7-step linear workflow combining:
 *   • Step 1: New Assessment (client name)
 *   • Step 2: Profile Capture Approach (direct / occupation finder / resume upload)
 *   • Step 3: Profile Form (with embedded occupation/resume helpers)
 *   • Step 4: Country Selection (specific / top-3 / custom)
 *   • Step 5: Live Calculator (re-uses the deterministic calculator)
 *   • Step 6: Review & Confirm
 *   • Step 7: Results & Actions (Save, Create PA, Generate Checklist, Compare)
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Calculator, Sparkles, User, Heart, Briefcase, GraduationCap, MessageSquare,
  CheckCircle2, AlertCircle, ChevronLeft, ChevronRight, Search, Upload, Wand2,
  FileText, Globe, MapPin, ArrowRight, Send, Save, Loader2, Bot, Trophy, IndianRupee,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STEPS = [
  { id: 1, label: 'Start', icon: User },
  { id: 2, label: 'Approach', icon: Wand2 },
  { id: 3, label: 'Profile', icon: Briefcase },
  { id: 4, label: 'Countries', icon: Globe },
  { id: 5, label: 'Calculator', icon: Calculator },
  { id: 6, label: 'Review', icon: CheckCircle2 },
  { id: 7, label: 'Done', icon: Trophy },
];

const QUALIFICATIONS = [
  { v: 'doctorate', l: 'Doctorate / PhD' },
  { v: 'master', l: "Master's Degree" },
  { v: 'bachelor', l: "Bachelor's Degree" },
  { v: 'diploma', l: 'Diploma' },
  { v: 'trade', l: 'Trade Qualification' },
  { v: 'high_school', l: 'High School' },
];

const MARITAL_OPTIONS = [
  { v: 'single', l: 'Single' },
  { v: 'married', l: 'Married' },
  { v: 'de_facto', l: 'De facto' },
  { v: 'divorced', l: 'Divorced' },
  { v: 'widowed', l: 'Widowed' },
  { v: 'separated', l: 'Separated' },
];

const CONTRIBUTION_OPTIONS = [
  { v: 'skill_assessment', l: 'Spouse Skill Assessment + Work Exp (+10)' },
  { v: 'english_only', l: 'Spouse Competent English Only (+5)' },
  { v: 'non_contributing', l: "Spouse won't contribute (0)" },
  { v: 'australian_pr_citizen', l: 'Spouse is AU PR/Citizen (+10)' },
];

const COUNTRIES = [
  { code: 'AU', name: 'Australia', flag: '🇦🇺' },
  { code: 'CA', name: 'Canada', flag: '🇨🇦' },
  { code: 'NZ', name: 'New Zealand', flag: '🇳🇿' },
];


export default function ClientAssessment() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [step, setStep] = useState(1);
  const [data, setData] = useState({
    client_name: '',
    client_email: '',
    client_phone: '',
    approach: '',  // 'direct' | 'occupation_finder' | 'resume_upload'

    marital_status: '',
    age: '',
    qualification: '',
    ielts_overall: '',
    ielts_listening: '',
    ielts_reading: '',
    ielts_writing: '',
    ielts_speaking: '',
    years_experience_total: '',
    years_experience_australia: '',

    // Occupation
    occupation_country: 'AU',
    occupation_code: '',
    occupation_title: '',
    occupation_body: '',
    occupation_pathway: '',

    // Country selection
    country_mode: 'specific',  // 'specific' | 'top_3' | 'custom'
    specific_country: 'AU',
    visa_subclass: '189',
    custom_countries: ['AU'],

    // Spouse
    spouse_will_migrate: 'yes',
    spouse_contribution: '',
    spouse_age: '',
    spouse_qualification: '',
    spouse_ielts_overall: '',
    spouse_profession: '',

    // AU bonuses
    australian_study_2_years: false,
    naati_accredited: false,
    professional_year_completed: false,
    state_nominated: false,
  });
  const [calcResults, setCalcResults] = useState([]);
  const [calculating, setCalculating] = useState(false);
  const [saved, setSaved] = useState(null);

  const update = (field, val) => setData(d => ({ ...d, [field]: val }));

  const goNext = () => setStep(s => Math.min(7, s + 1));
  const goBack = () => setStep(s => Math.max(1, s - 1));

  // Run calculation on step 5
  useEffect(() => {
    if (step !== 5) return;
    const targets = data.country_mode === 'top_3'
      ? [{ country: 'AU', visa_subclass: data.visa_subclass || '189' }, { country: 'CA' }, { country: 'NZ' }]
      : data.country_mode === 'custom'
      ? data.custom_countries.map(c => ({ country: c, visa_subclass: c === 'AU' ? data.visa_subclass : null }))
      : [{ country: data.specific_country, visa_subclass: data.specific_country === 'AU' ? data.visa_subclass : null }];
    setCalculating(true);
    const profile = buildProfile(data);
    axios.post(`${API}/sales/calculator/calculate-batch`, { profile, targets }, { headers })
      .then(r => setCalcResults(r.data.results || []))
      .catch(e => toast.error(formatApiError(e, 'Calculation failed')))
      .finally(() => setCalculating(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, data.country_mode, data.specific_country, data.visa_subclass, data.custom_countries.join(',')]);

  const saveAssessment = async () => {
    try {
      const targets = data.country_mode === 'top_3'
        ? [{ country: 'AU', visa_subclass: data.visa_subclass || '189' }, { country: 'CA' }, { country: 'NZ' }]
        : data.country_mode === 'custom'
        ? data.custom_countries.map(c => ({ country: c, visa_subclass: c === 'AU' ? data.visa_subclass : null }))
        : [{ country: data.specific_country, visa_subclass: data.specific_country === 'AU' ? data.visa_subclass : null }];
      const r = await axios.post(`${API}/sales/assessments`, {
        client_name: data.client_name || 'Unnamed client',
        client_email: data.client_email,
        client_phone: data.client_phone,
        profile: buildProfile(data),
        occupation: data.occupation_code ? {
          country_code: data.occupation_country,
          code: data.occupation_code,
          title: data.occupation_title,
          assessing_body: data.occupation_body,
          pathway: data.occupation_pathway,
        } : null,
        targets,
      }, { headers });
      setSaved(r.data);
      toast.success('Assessment saved');
      setStep(7);
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    }
  };

  const createPA = async () => {
    if (!saved) return;
    try {
      const r = await axios.post(`${API}/sales/assessments/${saved.id}/create-pa`, {
        target_country_code: saved.best_country_code,
        target_visa_subclass: data.visa_subclass,
        lead_source: 'smart_sales_helper',
      }, { headers });
      toast.success(`PA created: ${r.data.pa_id}`);
      navigate(`/pa/${r.data.pa_id}`);
    } catch (e) {
      toast.error(formatApiError(e, 'PA creation failed'));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="client-assessment-page">
      <div className="max-w-6xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Sparkles className="h-7 w-7 text-indigo-600" />Smart Client Assessment
            </h1>
            <p className="text-sm text-slate-500">Step-by-step workflow · Finder → Profile → Calculator → Action</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => navigate('/sales/occupations')}>Back to Search</Button>
          </div>
        </div>

        {/* Stepper */}
        <Card className="p-3" data-testid="stepper">
          <div className="flex items-center justify-between gap-1">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const active = s.id === step;
              const done = s.id < step;
              return (
                <div key={s.id} className="flex items-center flex-1">
                  <div
                    className={`flex flex-col items-center cursor-pointer ${done ? 'text-emerald-600' : active ? 'text-indigo-700' : 'text-slate-300'}`}
                    onClick={() => done && setStep(s.id)}
                    data-testid={`step-indicator-${s.id}`}
                  >
                    <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center ${
                      done ? 'bg-emerald-100 border-emerald-500'
                      : active ? 'bg-indigo-100 border-indigo-500'
                      : 'bg-white border-slate-200'
                    }`}>
                      {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                    </div>
                    <p className="text-[9px] mt-0.5 font-medium">{s.label}</p>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-1 ${done ? 'bg-emerald-300' : 'bg-slate-200'}`} />
                  )}
                </div>
              );
            })}
          </div>
        </Card>

        {/* STEP CONTENT */}
        <Card className="p-5 min-h-[400px]" data-testid={`step-${step}-content`}>
          {step === 1 && <Step1NewAssessment data={data} update={update} />}
          {step === 2 && <Step2Approach data={data} update={update} />}
          {step === 3 && <Step3Profile data={data} update={update} setData={setData} headers={headers} />}
          {step === 4 && <Step4Countries data={data} update={update} />}
          {step === 5 && <Step5Calculator results={calcResults} calculating={calculating} data={data} />}
          {step === 6 && <Step6Review data={data} results={calcResults} />}
          {step === 7 && <Step7Done saved={saved} createPA={createPA} navigate={navigate} headers={headers} />}
        </Card>

        {/* Navigation */}
        {step < 7 && (
          <div className="flex justify-between" data-testid="step-nav">
            <Button variant="outline" onClick={goBack} disabled={step === 1} data-testid="back-btn">
              <ChevronLeft className="h-4 w-4 mr-1" />Back
            </Button>
            {step < 6 ? (
              <Button onClick={goNext} className="bg-indigo-600 hover:bg-indigo-700" disabled={!canAdvance(step, data)} data-testid="next-btn">
                Next<ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            ) : (
              <Button onClick={saveAssessment} className="bg-emerald-600 hover:bg-emerald-700" data-testid="save-assessment-btn">
                <Save className="h-4 w-4 mr-1" />Save Assessment & Continue
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function canAdvance(step, data) {
  if (step === 1) return !!data.client_name;
  if (step === 2) return !!data.approach;
  if (step === 3) return !!data.marital_status && !!data.age && !!data.qualification;
  if (step === 4) return !!data.country_mode && (data.country_mode !== 'specific' || data.specific_country);
  return true;
}


// ════════════════════════════════════════════════════════════════
// Step 1: New Assessment
// ════════════════════════════════════════════════════════════════
function Step1NewAssessment({ data, update }) {
  return (
    <div className="max-w-xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <User className="h-5 w-5 text-indigo-600" />Start a New Assessment
      </h2>
      <p className="text-sm text-slate-600">Enter the client's basic contact info. You can edit these later.</p>
      <div>
        <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Client Name *</Label>
        <Input value={data.client_name} onChange={e => update('client_name', e.target.value)} placeholder="e.g., Rajesh Kumar" data-testid="ca-client-name" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Email</Label>
          <Input type="email" value={data.client_email} onChange={e => update('client_email', e.target.value)} placeholder="optional" data-testid="ca-client-email" />
        </div>
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Phone</Label>
          <Input value={data.client_phone} onChange={e => update('client_phone', e.target.value)} placeholder="optional" data-testid="ca-client-phone" />
        </div>
      </div>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 2: Choose Approach
// ════════════════════════════════════════════════════════════════
function Step2Approach({ data, update }) {
  const options = [
    { v: 'direct', icon: Briefcase, label: 'I know the profession', desc: 'Fill the form directly with client details' },
    { v: 'occupation_finder', icon: Bot, label: 'Find the best code (AI)', desc: 'Describe the profession in your words → AI suggests top 3-5 codes' },
    { v: 'resume_upload', icon: Upload, label: 'Upload Resume', desc: 'AI extracts profile fields from PDF/DOCX/TXT (10-20 sec)' },
  ];
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Wand2 className="h-5 w-5 text-indigo-600" />How would you like to start?
      </h2>
      <p className="text-sm text-slate-600">Pick the fastest path for this client. You can switch later.</p>
      <div className="space-y-2">
        {options.map(o => {
          const Icon = o.icon;
          return (
            <Card
              key={o.v}
              className={`p-4 cursor-pointer transition ${data.approach === o.v ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50' : 'hover:border-slate-300'}`}
              onClick={() => update('approach', o.v)}
              data-testid={`approach-${o.v}`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`h-6 w-6 ${data.approach === o.v ? 'text-indigo-600' : 'text-slate-400'}`} />
                <div className="flex-1">
                  <p className="font-bold text-sm">{o.label}</p>
                  <p className="text-[11px] text-slate-500">{o.desc}</p>
                </div>
                {data.approach === o.v && <CheckCircle2 className="h-5 w-5 text-indigo-600" />}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 3: Profile Capture (form + embedded AI helpers)
// ════════════════════════════════════════════════════════════════
function Step3Profile({ data, update, setData, headers }) {
  const [showSuggester, setShowSuggester] = useState(false);
  const [showResumeUpload, setShowResumeUpload] = useState(false);

  // Auto-open the chosen helper on first visit
  useEffect(() => {
    if (data.approach === 'occupation_finder' && !data.occupation_code) setShowSuggester(true);
    if (data.approach === 'resume_upload' && !data.age) setShowResumeUpload(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isMarried = data.marital_status === 'married' || data.marital_status === 'de_facto';

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Briefcase className="h-5 w-5 text-indigo-600" />Capture Client Profile
      </h2>

      <div className="flex gap-2 flex-wrap">
        <Button variant="outline" size="sm" onClick={() => setShowSuggester(true)} data-testid="open-suggester">
          <Bot className="h-3.5 w-3.5 mr-1" />AI Occupation Helper
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowResumeUpload(true)} data-testid="open-resume-upload">
          <Upload className="h-3.5 w-3.5 mr-1" />Upload Resume
        </Button>
      </div>

      {data.occupation_code && (
        <Card className="p-3 bg-emerald-50 border-l-4 border-l-emerald-500" data-testid="selected-occ-card">
          <p className="text-[10px] uppercase font-bold text-emerald-700">Selected Occupation</p>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-bold">{data.occupation_code} · {data.occupation_title}</p>
              <p className="text-[10px] text-slate-500">{data.occupation_body} · {data.occupation_pathway}</p>
            </div>
            <Button size="sm" variant="ghost" onClick={() => {
              update('occupation_code', '');
              update('occupation_title', '');
              update('occupation_body', '');
              update('occupation_pathway', '');
            }}>Change</Button>
          </div>
        </Card>
      )}

      {/* Profile fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <FieldWithLabel label="Marital Status *">
          <Select value={data.marital_status} onValueChange={v => update('marital_status', v)}>
            <SelectTrigger data-testid="ca-marital"><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>{MARITAL_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
          </Select>
        </FieldWithLabel>
        <FieldWithLabel label="Age *">
          <Input type="number" value={data.age} onChange={e => update('age', e.target.value)} placeholder="e.g., 32" data-testid="ca-age" />
        </FieldWithLabel>
        <FieldWithLabel label="Highest Qualification *">
          <Select value={data.qualification} onValueChange={v => update('qualification', v)}>
            <SelectTrigger data-testid="ca-qualification"><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
          </Select>
        </FieldWithLabel>
        <FieldWithLabel label="Total Years Experience">
          <Input type="number" step="0.5" value={data.years_experience_total} onChange={e => update('years_experience_total', e.target.value)} data-testid="ca-exp-total" placeholder="6" />
        </FieldWithLabel>
      </div>

      <p className="text-[11px] uppercase font-bold text-slate-500 mt-3 mb-1">IELTS Scores (all 4 bands)</p>
      <div className="grid grid-cols-5 gap-2">
        <FieldWithLabel label="Overall"><Input type="number" step="0.5" value={data.ielts_overall} onChange={e => update('ielts_overall', e.target.value)} placeholder="7.5" data-testid="ca-ielts-overall" /></FieldWithLabel>
        <FieldWithLabel label="L"><Input type="number" step="0.5" value={data.ielts_listening} onChange={e => update('ielts_listening', e.target.value)} placeholder="7.5" data-testid="ca-ielts-listening" /></FieldWithLabel>
        <FieldWithLabel label="R"><Input type="number" step="0.5" value={data.ielts_reading} onChange={e => update('ielts_reading', e.target.value)} placeholder="7.0" data-testid="ca-ielts-reading" /></FieldWithLabel>
        <FieldWithLabel label="W"><Input type="number" step="0.5" value={data.ielts_writing} onChange={e => update('ielts_writing', e.target.value)} placeholder="7.0" data-testid="ca-ielts-writing" /></FieldWithLabel>
        <FieldWithLabel label="S"><Input type="number" step="0.5" value={data.ielts_speaking} onChange={e => update('ielts_speaking', e.target.value)} placeholder="7.5" data-testid="ca-ielts-speaking" /></FieldWithLabel>
      </div>

      {/* Spouse section */}
      {isMarried && (
        <Card className="p-3 bg-pink-50 border-l-4 border-l-pink-400 mt-3">
          <h3 className="text-sm font-bold text-pink-900 mb-2 flex items-center gap-1">
            <Heart className="h-3.5 w-3.5" />Spouse Configuration
          </h3>
          <div className="space-y-2">
            <FieldWithLabel label="Spouse will migrate?">
              <Select value={data.spouse_will_migrate} onValueChange={v => update('spouse_will_migrate', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="yes">Yes — migrating</SelectItem>
                  <SelectItem value="no">No — not migrating</SelectItem>
                </SelectContent>
              </Select>
            </FieldWithLabel>
            {data.spouse_will_migrate === 'yes' && (
              <FieldWithLabel label="Spouse contribution">
                <Select value={data.spouse_contribution} onValueChange={v => update('spouse_contribution', v)}>
                  <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>{CONTRIBUTION_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
                </Select>
              </FieldWithLabel>
            )}
            {data.spouse_contribution && data.spouse_contribution !== 'non_contributing' && data.spouse_contribution !== 'australian_pr_citizen' && (
              <div className="grid grid-cols-3 gap-2">
                <FieldWithLabel label="Age"><Input type="number" value={data.spouse_age} onChange={e => update('spouse_age', e.target.value)} placeholder="30" /></FieldWithLabel>
                <FieldWithLabel label="Edu">
                  <Select value={data.spouse_qualification} onValueChange={v => update('spouse_qualification', v)}>
                    <SelectTrigger><SelectValue placeholder="…" /></SelectTrigger>
                    <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
                  </Select>
                </FieldWithLabel>
                <FieldWithLabel label="IELTS"><Input type="number" step="0.5" value={data.spouse_ielts_overall} onChange={e => update('spouse_ielts_overall', e.target.value)} placeholder="6.5" /></FieldWithLabel>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* AI Suggester Modal */}
      {showSuggester && (
        <SuggesterModal
          onClose={() => setShowSuggester(false)}
          onSelect={(s) => {
            update('occupation_country', s.country_code);
            update('occupation_code', s.code);
            update('occupation_title', s.title);
            update('occupation_body', s.assessing_body);
            update('occupation_pathway', s.pathway);
            setShowSuggester(false);
            toast.success(`Selected ${s.code} ${s.title}`);
          }}
          headers={headers}
        />
      )}

      {/* Resume Upload Modal */}
      {showResumeUpload && (
        <ResumeUploadModal
          onClose={() => setShowResumeUpload(false)}
          onExtracted={(extracted) => {
            // Auto-fill form fields from extracted JSON
            const p = extracted.primary_applicant || {};
            const ed = p.education || {};
            const pf = p.professional || {};
            const lg = (p.language || {}).scores || {};
            setData(d => ({
              ...d,
              age: (p.personal || {}).age || d.age,
              qualification: ed.highest_qualification || d.qualification,
              years_experience_total: pf.years_experience_total || d.years_experience_total,
              ielts_overall: lg.overall || d.ielts_overall,
              ielts_listening: lg.listening || d.ielts_listening,
              ielts_reading: lg.reading || d.ielts_reading,
              ielts_writing: lg.writing || d.ielts_writing,
              ielts_speaking: lg.speaking || d.ielts_speaking,
              marital_status: extracted.marital_status || d.marital_status,
            }));
            setShowResumeUpload(false);
            toast.success('Resume data loaded — please review the fields below');
          }}
          headers={headers}
        />
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 4: Country Selection
// ════════════════════════════════════════════════════════════════
function Step4Countries({ data, update }) {
  const toggleCustom = (code) => {
    const list = data.custom_countries.includes(code)
      ? data.custom_countries.filter(c => c !== code)
      : [...data.custom_countries, code];
    update('custom_countries', list);
  };
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Globe className="h-5 w-5 text-indigo-600" />Country Selection
      </h2>
      <div className="space-y-2">
        {[
          { v: 'specific', label: 'Specific country (deep dive)', desc: 'Pick one country + specific visa subclass' },
          { v: 'top_3', label: 'Top 3 comparison (AU + CA + NZ)', desc: 'Calculate side-by-side across the big 3' },
          { v: 'custom', label: 'Custom selection', desc: 'Pick 2+ countries to compare' },
        ].map(o => (
          <Card key={o.v}
            className={`p-3 cursor-pointer ${data.country_mode === o.v ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50' : ''}`}
            onClick={() => update('country_mode', o.v)}
            data-testid={`country-mode-${o.v}`}>
            <p className="font-bold text-sm">{o.label}</p>
            <p className="text-[11px] text-slate-500">{o.desc}</p>
          </Card>
        ))}
      </div>
      {data.country_mode === 'specific' && (
        <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded">
          <FieldWithLabel label="Country">
            <Select value={data.specific_country} onValueChange={v => update('specific_country', v)}>
              <SelectTrigger data-testid="ca-specific-country"><SelectValue /></SelectTrigger>
              <SelectContent>{COUNTRIES.map(c => <SelectItem key={c.code} value={c.code}>{c.flag} {c.name}</SelectItem>)}</SelectContent>
            </Select>
          </FieldWithLabel>
          {data.specific_country === 'AU' && (
            <FieldWithLabel label="Visa">
              <Select value={data.visa_subclass} onValueChange={v => update('visa_subclass', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="189">Subclass 189</SelectItem>
                  <SelectItem value="190">Subclass 190</SelectItem>
                  <SelectItem value="491">Subclass 491</SelectItem>
                </SelectContent>
              </Select>
            </FieldWithLabel>
          )}
        </div>
      )}
      {data.country_mode === 'custom' && (
        <div className="bg-slate-50 p-3 rounded space-y-1">
          <p className="text-[10px] uppercase font-bold text-slate-500">Pick at least 2 countries</p>
          {COUNTRIES.map(c => (
            <label key={c.code} className="flex items-center gap-2 text-sm">
              <Switch checked={data.custom_countries.includes(c.code)} onCheckedChange={() => toggleCustom(c.code)} />
              {c.flag} {c.name}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 5: Live Calculator (multi-country)
// ════════════════════════════════════════════════════════════════
function Step5Calculator({ results, calculating, data }) {
  return (
    <div>
      <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
        <Calculator className="h-5 w-5 text-indigo-600" />Live Calculation
        {calculating && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
      </h2>
      {!results.length ? (
        <p className="text-sm text-slate-500 italic">Calculating…</p>
      ) : (
        <div className={`grid gap-3 ${results.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'}`} data-testid="calc-results">
          {results.map((r, i) => (
            <Card key={i} className="p-4 border-2 border-indigo-200 bg-gradient-to-br from-white to-indigo-50" data-testid={`result-${r.country_code}`}>
              <div className="flex items-center justify-between mb-2">
                <Badge className="bg-indigo-600 text-white">{r.country_code}</Badge>
                {r.visa_subclass && <Badge variant="outline" className="text-[10px]">Subclass {r.visa_subclass}</Badge>}
              </div>
              <p className="text-4xl font-bold text-indigo-700 text-center my-3">{r.total}</p>
              <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Top Categories</p>
              <div className="space-y-0.5">
                {Object.entries(r.breakdown || {}).slice(0, 6).map(([cat, val]) => (
                  <div key={cat} className="flex items-center justify-between text-[11px]">
                    <span className="capitalize">{cat.replace(/^ca_|^nz_/, '').replace(/_/g, ' ')}</span>
                    <Badge className={(val.points || 0) > 0 ? 'bg-emerald-100 text-emerald-700 text-[9px]' : 'bg-slate-100 text-slate-500 text-[9px]'}>+{val.points || 0}</Badge>
                  </div>
                ))}
              </div>
              <div className="mt-3 space-y-1">
                {Object.entries(r.visa_eligibility || {}).map(([code, v]) => (
                  <div key={code} className={`text-[10px] flex items-center gap-1 ${v.eligible ? 'text-emerald-700' : 'text-slate-500'}`}>
                    {v.eligible ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                    {code} · {v.eligible ? 'ELIGIBLE' : 'NOT YET'}
                  </div>
                ))}
              </div>
              <p className="text-[10px] mt-2 italic text-amber-900">{r.recommendation}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 6: Review
// ════════════════════════════════════════════════════════════════
function Step6Review({ data, results }) {
  const best = useMemo(() => results.length ? results.reduce((a, b) => (a.total > b.total ? a : b)) : null, [results]);
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />Review & Confirm
      </h2>
      <Card className="p-4 bg-slate-50">
        <p className="text-[10px] uppercase font-bold text-slate-500">Client</p>
        <p className="font-bold">{data.client_name}</p>
        <p className="text-xs text-slate-500">{data.client_email || 'no email'} · {data.client_phone || 'no phone'}</p>
      </Card>
      <Card className="p-4">
        <p className="text-[10px] uppercase font-bold text-slate-500">Profile</p>
        <p className="text-xs"><strong>{data.marital_status}</strong> · Age {data.age} · {data.qualification} · IELTS {data.ielts_overall} overall · {data.years_experience_total} yrs exp</p>
      </Card>
      {data.occupation_code && (
        <Card className="p-4 bg-emerald-50">
          <p className="text-[10px] uppercase font-bold text-emerald-700">Occupation</p>
          <p className="font-bold text-sm">{data.occupation_code} · {data.occupation_title}</p>
          <p className="text-[11px] text-slate-500">{data.occupation_body} · {data.occupation_pathway}</p>
        </Card>
      )}
      {best && (
        <Card className="p-4 border-l-4 border-l-indigo-500 bg-indigo-50">
          <p className="text-[10px] uppercase font-bold text-indigo-700">Best Match</p>
          <p className="text-2xl font-bold text-indigo-900">{best.country_code} · {best.total} pts</p>
          <p className="text-[11px] text-indigo-700 italic">{best.recommendation}</p>
        </Card>
      )}
      <Card className="p-3 bg-amber-50 border border-amber-200">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" defaultChecked data-testid="confirm-checkbox" /> I confirm this profile and code match the client's actual situation.
        </label>
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 7: Done — Actions + Checklist + Save & Share
// ════════════════════════════════════════════════════════════════
function Step7Done({ saved, createPA, navigate, headers }) {
  const [checklist, setChecklist] = useState(null);
  const [loadingChecklist, setLoadingChecklist] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareInfo, setShareInfo] = useState(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [expiryDays, setExpiryDays] = useState(30);

  // Auto-fetch checklist on mount
  useEffect(() => {
    if (!saved?.id) return;
    setLoadingChecklist(true);
    axios.get(`${API}/sales/assessments/${saved.id}/checklist`, { headers })
      .then(r => setChecklist(r.data))
      .catch(e => toast.error(formatApiError(e, 'Failed to load checklist')))
      .finally(() => setLoadingChecklist(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saved?.id]);

  const generateShareLink = async () => {
    setShareLoading(true);
    try {
      const r = await axios.post(`${API}/sales/assessments/${saved.id}/share`, { expires_in_days: expiryDays }, { headers });
      setShareInfo(r.data);
      toast.success('Share link generated');
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to generate share link'));
    } finally {
      setShareLoading(false);
    }
  };

  const copyLink = async () => {
    if (!shareInfo?.public_url) return;
    try {
      await navigator.clipboard.writeText(shareInfo.public_url);
      toast.success('Link copied to clipboard');
    } catch {
      toast.error('Copy failed — please select and copy manually');
    }
  };

  const shareOnWhatsapp = () => {
    if (!shareInfo?.public_url) return;
    const msg = `Hi! Here's your eligibility report from LEAMSS:\n\n` +
      `📋 ${saved?.client_name}\n` +
      `🏆 Best country: ${saved?.best_country_code} · Score: ${saved?.best_total} pts\n\n` +
      `📎 Full report (read-only): ${shareInfo.public_url}\n\n` +
      `Reply to this message to schedule a free consultation.`;
    const url = `https://wa.me/?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Group checklist items by category
  const grouped = useMemo(() => {
    if (!checklist?.items) return {};
    return checklist.items.reduce((acc, it) => {
      (acc[it.category] = acc[it.category] || []).push(it);
      return acc;
    }, {});
  }, [checklist]);

  return (
    <div className="max-w-4xl mx-auto space-y-5 py-4" data-testid="step-7-done">
      {/* Header — Success state */}
      <div className="text-center space-y-3">
        <Trophy className="h-14 w-14 text-emerald-500 mx-auto" />
        <h2 className="text-2xl font-bold text-emerald-900">Assessment Complete!</h2>
        <p className="text-sm text-slate-600">ID: <code className="bg-slate-100 px-2 py-0.5 rounded text-xs">{saved?.id}</code></p>
        {saved?.best_country_code && (
          <p className="text-sm">
            Best country: <strong>{saved.best_country_code}</strong> · Score: <strong>{saved.best_total}</strong>
          </p>
        )}
      </div>

      {/* Primary action buttons */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        <Button size="default" className="bg-indigo-600 hover:bg-indigo-700" onClick={createPA} data-testid="create-pa-btn">
          <ArrowRight className="h-4 w-4 mr-1" />Create Pre-Assessment
        </Button>
        <Button size="default" variant="outline" onClick={() => setShareDialogOpen(true)} data-testid="save-share-btn" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
          <Send className="h-4 w-4 mr-1" />Save &amp; Share Report
        </Button>
        <Button size="default" variant="outline" onClick={() => navigate(`/sales/occupations`)} data-testid="back-to-search">
          <Search className="h-4 w-4 mr-1" />Back to Search
        </Button>
        <Button size="default" variant="outline" onClick={() => window.print()} data-testid="export-pdf">
          <FileText className="h-4 w-4 mr-1" />Print / Export PDF
        </Button>
      </div>

      {/* Document Checklist */}
      <Card className="p-4" data-testid="checklist-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />Document Checklist
          </h3>
          {checklist && (
            <div className="flex items-center gap-2 text-[11px]">
              <Badge className="bg-indigo-100 text-indigo-700" data-testid="checklist-total">{checklist.stats.total} items</Badge>
              <Badge className="bg-rose-100 text-rose-700">{checklist.stats.required} required</Badge>
              <Badge className="bg-slate-100 text-slate-600">{checklist.stats.optional} optional</Badge>
            </div>
          )}
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          Rule-based, no AI. Generated from country ({saved?.best_country_code}), occupation, marital status, and pathway.
        </p>
        {loadingChecklist ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />Loading checklist…
          </div>
        ) : !checklist ? (
          <p className="text-xs text-slate-400 italic">No checklist available.</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} data-testid={`checklist-cat-${cat.replace(/\s+/g, '-')}`}>
                <p className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">{cat}</p>
                <ul className="space-y-1">
                  {items.map((it, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs">
                      <div className={`mt-0.5 h-3.5 w-3.5 rounded-full border-2 flex-shrink-0 ${it.required ? 'border-rose-400' : 'border-slate-300'}`}></div>
                      <div className="flex-1">
                        <span className={`${it.required ? 'font-medium text-slate-700' : 'text-slate-500'}`}>{it.name}</span>
                        {it.required && <Badge className="ml-2 bg-rose-50 text-rose-600 text-[9px] py-0">Required</Badge>}
                        {it.fee_native && <span className="ml-2 text-[10px] text-emerald-700 font-mono">{it.fee_native}</span>}
                        {it.note && <p className="text-[10px] text-slate-400 italic mt-0.5">{it.note}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Share Dialog */}
      {shareDialogOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShareDialogOpen(false)} data-testid="share-dialog">
          <Card className="max-w-md w-full bg-white p-5" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-bold flex items-center gap-2 mb-1">
              <Send className="h-5 w-5 text-emerald-600" />Save &amp; Share Report
            </h3>
            <p className="text-[11px] text-slate-500 mb-3">Generate a public read-only link for this assessment.</p>
            {!shareInfo ? (
              <>
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Link Validity</p>
                <div className="grid grid-cols-5 gap-1 mb-3">
                  {[
                    { d: 1, l: '1 day' },
                    { d: 7, l: '7 days' },
                    { d: 30, l: '30 days' },
                    { d: 90, l: '90 days' },
                    { d: 0, l: 'Never' },
                  ].map(o => (
                    <button
                      key={o.d}
                      onClick={() => setExpiryDays(o.d)}
                      className={`p-2 rounded border-2 text-[11px] ${expiryDays === o.d ? 'border-emerald-500 bg-emerald-50 font-bold' : 'border-slate-200 text-slate-600'}`}
                      data-testid={`share-expiry-${o.d}`}
                    >
                      {o.l}
                    </button>
                  ))}
                </div>
                {expiryDays === 0 && (
                  <p className="text-[10px] text-amber-700 bg-amber-50 p-2 rounded mb-3">⚠️ Never-expire links should only be shared with trusted recipients.</p>
                )}
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" size="sm" onClick={() => setShareDialogOpen(false)}>Cancel</Button>
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" disabled={shareLoading} onClick={generateShareLink} data-testid="share-generate-btn">
                    {shareLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Send className="h-3 w-3 mr-1" />}
                    Generate Link
                  </Button>
                </div>
              </>
            ) : (
              <>
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Public Link</p>
                <div className="p-2 bg-slate-50 rounded border text-[11px] break-all font-mono mb-3" data-testid="share-link-output">
                  {shareInfo.public_url}
                </div>
                {shareInfo.expires_at ? (
                  <p className="text-[10px] text-slate-500 mb-3">Expires: {new Date(shareInfo.expires_at).toLocaleString()}</p>
                ) : (
                  <p className="text-[10px] text-amber-700 mb-3">⚠️ Never expires.</p>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <Button size="sm" variant="outline" onClick={copyLink} data-testid="share-copy-btn">
                    <FileText className="h-3 w-3 mr-1" />Copy Link
                  </Button>
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={shareOnWhatsapp} data-testid="share-whatsapp-btn">
                    <MessageSquare className="h-3 w-3 mr-1" />WhatsApp Share
                  </Button>
                </div>
                <Button variant="ghost" size="sm" className="w-full mt-2 text-[11px]" onClick={() => { setShareInfo(null); setShareDialogOpen(false); }}>
                  Done
                </Button>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// AI Occupation Suggester Modal
// ════════════════════════════════════════════════════════════════
function SuggesterModal({ onClose, onSelect, headers }) {
  const [description, setDescription] = useState('');
  const [country, setCountry] = useState('AU');
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const submit = async () => {
    if (description.trim().length < 20) {
      toast.error('Please enter at least 20 characters describing the profession');
      return;
    }
    setLoading(true);
    try {
      const r = await axios.post(`${API}/sales/ai/suggest-occupation`, {
        description, country_codes: [country], max_suggestions: 5,
      }, { headers, timeout: 60000 });
      setSuggestions(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'AI suggestion failed'));
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="suggester-modal">
      <Card className="max-w-2xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-bold flex items-center gap-2 mb-3">
          <Bot className="h-5 w-5 text-indigo-600" />AI Occupation Helper
          <Badge className="bg-amber-100 text-amber-700 text-[9px]">AI suggests — you decide</Badge>
        </h3>
        <p className="text-[11px] text-slate-500 mb-3">
          Describe the client's profession in your own words. The AI will suggest the best matching occupation codes — you verify and pick.
        </p>
        {!suggestions ? (
          <>
            <div className="grid grid-cols-3 gap-2 mb-3">
              {COUNTRIES.map(c => (
                <button key={c.code} onClick={() => setCountry(c.code)}
                  className={`p-2 rounded border-2 text-xs ${country === c.code ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200'}`}>
                  {c.flag} {c.name}
                </button>
              ))}
            </div>
            <Textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={6}
              placeholder="e.g., 8 years in digital marketing, primarily managing social media campaigns, content strategy, and brand positioning for tech companies. Bachelor's in marketing."
              data-testid="suggester-description"
            />
            <p className="text-[10px] text-slate-400 mt-1">Min 20 chars · Be specific about duties, industry, seniority</p>
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={submit} disabled={loading} data-testid="suggester-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading ? 'Analysing…' : 'Find Matching Codes'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-[11px] text-amber-700 italic mb-3 bg-amber-50 p-2 rounded">
              ⚠️ AI suggestions are starting points. Please verify each match by reviewing the code's requirements and discussing with the client.
            </p>
            <div className="space-y-2">
              {(suggestions.suggestions || []).map((s, i) => (
                <Card key={i} className={`p-3 ${s.confidence === 'high' ? 'border-l-4 border-l-emerald-500 bg-emerald-50' : s.confidence === 'medium' ? 'border-l-4 border-l-amber-500 bg-amber-50' : 'border-l-4 border-l-slate-400'}`} data-testid={`suggestion-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-bold">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•'} {s.code} · {s.title}</p>
                    <Badge className={s.confidence === 'high' ? 'bg-emerald-100 text-emerald-700' : s.confidence === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}>
                      {s.confidence?.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-slate-500">{s.assessing_body} · {s.pathway}</p>
                  <p className="text-[11px] mt-1">{s.reasoning}</p>
                  {s.considerations && <p className="text-[10px] mt-1 italic text-slate-600">⚠️ {s.considerations}</p>}
                  <Button size="sm" variant="outline" className="mt-2 text-[10px] h-7" onClick={() => onSelect(s)} data-testid={`select-suggestion-${i}`}>
                    Select this code <ChevronRight className="h-3 w-3 ml-1" />
                  </Button>
                </Card>
              ))}
            </div>
            {suggestions.general_advice && (
              <p className="text-[11px] italic mt-3 text-slate-600 bg-slate-50 p-2 rounded">💡 {suggestions.general_advice}</p>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={() => setSuggestions(null)}>Try Again</Button>
              <Button size="sm" variant="ghost" onClick={onClose}>Close</Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Resume Upload Modal
// ════════════════════════════════════════════════════════════════
function ResumeUploadModal({ onClose, onExtracted, headers }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const inputRef = useRef(null);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/eligibility/profiles/resume-extract`, form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        timeout: 90000,
      });
      setExtracted(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Resume extraction failed'));
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="resume-modal">
      <Card className="max-w-xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-bold flex items-center gap-2 mb-3">
          <Upload className="h-5 w-5 text-indigo-600" />Upload Resume
        </h3>
        {!extracted ? (
          <>
            <p className="text-[11px] text-slate-500 mb-3">PDF, DOCX or TXT · Max 10 MB · AI extracts the profile in 10-20 sec.</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={e => setFile(e.target.files?.[0])}
              className="block w-full text-sm"
              data-testid="resume-file-input"
            />
            {file && (
              <div className="mt-2 p-2 bg-slate-50 rounded text-xs">
                📄 {file.name} ({(file.size / 1024).toFixed(0)} KB)
              </div>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={submit} disabled={!file || loading} data-testid="resume-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading ? 'Extracting…' : 'Parse Resume with AI'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-[11px] text-emerald-700 bg-emerald-50 p-2 rounded mb-3">✅ Resume parsed. Review the data and use it.</p>
            <pre className="bg-slate-50 p-2 rounded text-[10px] max-h-72 overflow-auto">
              {JSON.stringify({
                name: extracted.name,
                primary_applicant: extracted.primary_applicant,
              }, null, 2)}
            </pre>
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={() => setExtracted(null)}>Re-parse</Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => onExtracted(extracted)} data-testid="use-extracted-data">
                <CheckCircle2 className="h-3 w-3 mr-1" />Use This Data
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────
function FieldWithLabel({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] uppercase font-bold text-slate-500 mb-1 block">{label}</Label>
      {children}
    </div>
  );
}


function buildProfile(data) {
  const num = v => (v === '' || v === null || v === undefined) ? null : parseFloat(v);
  const primary = {
    personal: { age: num(data.age) },
    professional: {
      current_profession: data.occupation_title,
      years_experience_total: num(data.years_experience_total),
      years_experience_australia: num(data.years_experience_australia),
    },
    education: { highest_qualification: data.qualification },
    language: {
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
      naati_accredited: data.naati_accredited,
      professional_year_completed: data.professional_year_completed,
      state_nominated: data.state_nominated,
    },
  };

  let spouse = null;
  if ((data.marital_status === 'married' || data.marital_status === 'de_facto') && data.spouse_will_migrate === 'yes') {
    spouse = {
      contribution_type: data.spouse_contribution || 'not_applicable',
      is_applicant_on_visa: true,
      is_australian_pr_or_citizen: data.spouse_contribution === 'australian_pr_citizen',
      personal: { age: num(data.spouse_age) },
      education: { highest_qualification: data.spouse_qualification },
      language: { scores: { overall: num(data.spouse_ielts_overall) } },
    };
  }

  return {
    client_name: data.client_name,
    marital_status: data.marital_status,
    primary_applicant: primary,
    spouse,
  };
}
