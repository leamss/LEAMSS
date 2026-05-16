/**
 * Phase 6.2 — Smart Profile Form (multi-step wizard).
 *
 * URL: /eligibility/new-assessment
 * URL: /eligibility/edit/:profileId  (resume draft)
 *
 * Steps:
 *   1. Search Mode (Specific / Top 3 / Custom / Top 5)
 *   2. Basic Info  (DOB, gender, location)
 *   3. Professional + Education
 *   4. Language Proficiency
 *   5. Family + Finances + Preferences
 *   6. Work History + Additional Factors
 *   7. Review & Submit
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  ArrowLeft, ArrowRight, Save, Sparkles, Target, Globe, Briefcase, GraduationCap,
  MessageSquare, Users as UsersIcon, DollarSign, ClipboardList, CheckCircle2,
  Plus, Trash2, Loader2, Layers, Compass, Star, Search as SearchIcon,
} from 'lucide-react';

import { formatApiError, pruneEmpty } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SEARCH_MODES = [
  { value: 'specific', label: 'Specific Country', desc: 'Deep analysis for one country', icon: Target, color: 'indigo' },
  { value: 'top_3', label: 'Best Match (Top 3)', desc: 'AU + CA + NZ rapid comparison · Default', icon: Star, color: 'emerald', recommended: true },
  { value: 'custom', label: 'Custom Selection', desc: 'Pick 2–5 countries to compare', icon: Layers, color: 'amber' },
  { value: 'top_5', label: 'Comprehensive (Top 5)', desc: 'AU + CA + NZ + UK + US', icon: Compass, color: 'rose' },
];

const QUALIFICATIONS = [
  { v: 'doctorate', l: 'Doctorate / PhD' },
  { v: 'master', l: "Master's Degree" },
  { v: 'bachelor', l: "Bachelor's Degree" },
  { v: 'diploma', l: 'Diploma / Associate' },
  { v: 'trade', l: 'Trade Qualification' },
  { v: 'high_school', l: 'High School' },
];

const STEPS = [
  { key: 'mode', label: 'Search Mode', icon: Target },
  { key: 'basic', label: 'Basic Info', icon: Globe },
  { key: 'prof_edu', label: 'Profession & Education', icon: Briefcase },
  { key: 'language', label: 'Language', icon: MessageSquare },
  { key: 'family_fin', label: 'Family & Finances', icon: UsersIcon },
  { key: 'work_more', label: 'Work History & Extras', icon: ClipboardList },
  { key: 'review', label: 'Review & Submit', icon: CheckCircle2 },
];


function emptyProfile() {
  return {
    name: '', email: '', phone: '',
    pa_id: null,
    basic_info: {
      date_of_birth: '', gender: '', marital_status: '', dependents_count: 0,
      current_country: 'India', current_city: '', nationality: 'Indian',
    },
    professional: {
      current_profession: '', designation: '', years_experience_total: 0, years_in_current_role: 0,
      industry: '', employer_name: '', salary_inr_per_annum: '', has_managerial_experience: false,
    },
    education: {
      highest_qualification: '', field_of_study: '', institution: '', country: 'India',
      year_completed: '',
    },
    language_proficiency: {
      primary_test: 'IELTS', test_completed: false, test_date: '',
      scores: { overall: '', listening: '', reading: '', writing: '', speaking: '' },
      target_score: '',
    },
    family: {
      spouse_present: false, spouse_education: '', spouse_profession: '', spouse_language: '',
      children_count: 0, children_ages: [],
    },
    finances: {
      annual_household_income: '', savings_inr: '', budget_for_immigration_inr: '',
      able_to_show_funds: false,
    },
    preferences: {
      timeline_months: 12, preferred_countries: [], avoiding_countries: [],
      family_relocation: true, priority: 'quality_of_life',
      search_mode: 'top_3', specific_country: '', custom_countries: [],
    },
    work_history: [],
    additional_factors: {
      has_relative_in_target_country: false, relative_relationship: '',
      has_job_offer: false, state_preference: '',
      medical_concerns: '', criminal_record: false,
    },
    status: 'draft',
  };
}


export default function EligibilityProfileWizard() {
  const navigate = useNavigate();
  const { profileId } = useParams();
  const [searchParams] = useSearchParams();
  const prefillPaId = searchParams.get('pa_id');

  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [data, setData] = useState(emptyProfile());
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!!profileId);
  const [saving, setSaving] = useState(false);
  const [currentProfileId, setCurrentProfileId] = useState(profileId || null);
  const [countries, setCountries] = useState([]);
  const lastAutoSavedSnapshot = useRef(null);

  // Initial load: from existing profile or pre-fill from PA
  useEffect(() => {
    (async () => {
      try {
        if (profileId) {
          const r = await axios.get(`${API}/eligibility/profiles/${profileId}`, { headers });
          setData({ ...emptyProfile(), ...r.data });
          setCurrentProfileId(profileId);
        } else if (prefillPaId) {
          const r = await axios.post(`${API}/eligibility/profiles/prefill-from-pa/${prefillPaId}`, {}, { headers });
          setData({ ...emptyProfile(), ...r.data });
        }
      } catch (e) {
        toast.error(formatApiError(e, 'Failed to load profile'));
      } finally { setLoading(false); }
    })();
  }, [profileId, prefillPaId, headers]);

  // Load active countries (for mode selection)
  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/eligibility/kb/countries`, { headers });
        setCountries((r.data.items || []).filter(c => c.is_active));
      } catch (_) {}
    })();
  }, [headers]);

  // Auto-save (every 30s) — only after step 1 + when something has changed
  useEffect(() => {
    const interval = setInterval(() => {
      if (step === 0 || saving) return;
      const snapshot = JSON.stringify(data);
      if (snapshot === lastAutoSavedSnapshot.current) return;
      autoSave(snapshot);
    }, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, step, saving, currentProfileId]);

  const autoSave = useCallback(async (snapshotJson) => {
    if (saving) return;
    if (!data.name) return;  // need a name minimum
    setSaving(true);
    try {
      const cleaned = pruneEmpty(data);
      if (currentProfileId) {
        await axios.patch(`${API}/eligibility/profiles/${currentProfileId}`, cleaned, { headers });
      } else {
        const r = await axios.post(`${API}/eligibility/profiles`, { ...cleaned, status: 'draft' }, { headers });
        setCurrentProfileId(r.data.id);
        toast.success('Draft saved', { duration: 1500 });
      }
      lastAutoSavedSnapshot.current = snapshotJson || JSON.stringify(data);
    } catch (e) { /* silent — user can manually save */ }
    finally { setSaving(false); }
  }, [data, currentProfileId, saving, headers]);

  const saveManual = useCallback(async () => {
    if (!data.name) { toast.error('Name is required'); return false; }
    setSaving(true);
    try {
      const cleaned = pruneEmpty(data);
      if (currentProfileId) {
        await axios.patch(`${API}/eligibility/profiles/${currentProfileId}`, cleaned, { headers });
      } else {
        const r = await axios.post(`${API}/eligibility/profiles`, { ...cleaned, status: 'draft' }, { headers });
        setCurrentProfileId(r.data.id);
      }
      toast.success('Saved');
      lastAutoSavedSnapshot.current = JSON.stringify(data);
      return true;
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
      return false;
    } finally { setSaving(false); }
  }, [data, currentProfileId, headers]);

  const setField = (section, field, val) => {
    setData(d => ({ ...d, [section]: { ...(d[section] || {}), [field]: val } }));
  };
  const setRoot = (field, val) => setData(d => ({ ...d, [field]: val }));

  const submitAndAnalyse = async () => {
    if (!data.name) { toast.error('Name is required'); return; }
    setSaving(true);
    try {
      const payload = { ...pruneEmpty(data), status: 'complete' };
      let pid = currentProfileId;
      if (pid) {
        await axios.patch(`${API}/eligibility/profiles/${pid}`, payload, { headers });
      } else {
        const r = await axios.post(`${API}/eligibility/profiles`, payload, { headers });
        pid = r.data.id;
        setCurrentProfileId(pid);
      }
      toast.success('Profile saved — starting AI analysis…');
      navigate(`/eligibility/profile/${pid}/assess`);
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  // Step validation
  const canProceed = useMemo(() => {
    switch (step) {
      case 0: {
        const m = data.preferences?.search_mode;
        if (!m) return false;
        if (m === 'specific') return !!data.preferences?.specific_country;
        if (m === 'custom') return (data.preferences?.custom_countries?.length || 0) >= 2;
        return true;
      }
      case 1: return !!data.name && !!data.basic_info?.date_of_birth;
      case 2: return !!data.professional?.current_profession && !!data.education?.highest_qualification;
      case 3: return true;  // language is optional
      case 4: return true;
      case 5: return true;
      default: return true;
    }
  }, [step, data]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">Loading profile…</div>;
  }

  const StepIcon = STEPS[step].icon;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="eligibility-wizard">
      {/* Top bar */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(-1)} data-testid="wizard-back-page">
              <ArrowLeft className="h-4 w-4 mr-1" />Exit
            </Button>
            <div>
              <p className="text-xs uppercase text-slate-400 tracking-wide">AI Eligibility · New Assessment</p>
              <h1 className="text-base font-bold">
                <StepIcon className="inline h-4 w-4 mr-1 text-indigo-600" />
                Step {step + 1} of {STEPS.length}: {STEPS[step].label}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {saving && <span className="text-[11px] text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Saving…</span>}
            {currentProfileId && <Badge className="bg-slate-100 text-slate-600 text-[10px]">{currentProfileId}</Badge>}
            <Button variant="outline" size="sm" onClick={saveManual} disabled={saving} data-testid="wizard-save-now">
              <Save className="h-3.5 w-3.5 mr-1" />Save Draft
            </Button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="max-w-5xl mx-auto px-6 pb-3 flex items-center gap-1.5">
          {STEPS.map((s, i) => (
            <button
              key={s.key}
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              className={`flex-1 h-1.5 rounded transition ${
                i === step ? 'bg-indigo-600' : i < step ? 'bg-indigo-300 cursor-pointer hover:bg-indigo-400' : 'bg-slate-200'
              }`}
              title={s.label}
              data-testid={`progress-dot-${i}`}
            />
          ))}
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {step === 0 && <StepMode data={data} setField={setField} countries={countries} />}
        {step === 1 && <StepBasic data={data} setRoot={setRoot} setField={setField} />}
        {step === 2 && <StepProfessionEducation data={data} setField={setField} />}
        {step === 3 && <StepLanguage data={data} setField={setField} />}
        {step === 4 && <StepFamilyFinances data={data} setField={setField} />}
        {step === 5 && <StepWorkExtras data={data} setRoot={setRoot} setField={setField} />}
        {step === 6 && <StepReview data={data} countries={countries} onJump={setStep} />}

        {/* Footer Nav */}
        <Card className="p-3 flex items-center justify-between sticky bottom-2 shadow-lg">
          <Button variant="outline" onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0} data-testid="step-prev">
            <ArrowLeft className="h-4 w-4 mr-1" />Previous
          </Button>
          <div className="text-xs text-slate-500">{step + 1} / {STEPS.length}</div>
          {step < STEPS.length - 1 ? (
            <Button
              onClick={() => setStep(s => Math.min(STEPS.length - 1, s + 1))}
              disabled={!canProceed}
              className="bg-indigo-600 hover:bg-indigo-700"
              data-testid="step-next"
            >
              Next<ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button onClick={submitAndAnalyse} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="submit-analyse">
              <Sparkles className="h-4 w-4 mr-1" />
              {saving ? 'Saving…' : 'Save & Run Analysis'}
            </Button>
          )}
        </Card>
      </div>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 0: Search Mode
// ════════════════════════════════════════════════════════════════
function StepMode({ data, setField, countries }) {
  const mode = data.preferences?.search_mode || 'top_3';
  const specific = data.preferences?.specific_country || '';
  const custom = data.preferences?.custom_countries || [];

  const toggleCustom = (code) => {
    let next = custom.includes(code) ? custom.filter(c => c !== code) : [...custom, code];
    if (next.length > 5) next = next.slice(0, 5);  // cap at 5
    setField('preferences', 'custom_countries', next);
  };

  return (
    <Card className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold">How would you like to search?</h2>
        <p className="text-xs text-slate-500">Pick a strategy. You can always re-run with different settings later.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SEARCH_MODES.map(m => {
          const Icon = m.icon;
          const active = mode === m.value;
          return (
            <button
              key={m.value}
              onClick={() => setField('preferences', 'search_mode', m.value)}
              className={`text-left p-4 rounded-lg border-2 transition relative ${
                active ? `border-${m.color}-500 bg-${m.color}-50` : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
              data-testid={`mode-${m.value}`}
            >
              {m.recommended && (
                <Badge className={`absolute -top-2 right-3 bg-${m.color}-600 text-white text-[9px]`}>RECOMMENDED</Badge>
              )}
              <Icon className={`h-5 w-5 mb-2 text-${m.color}-600`} />
              <p className="font-bold text-sm">{m.label}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">{m.desc}</p>
            </button>
          );
        })}
      </div>

      {mode === 'specific' && (
        <div className="border-t pt-3" data-testid="specific-mode-picker">
          <Label className="text-xs font-bold mb-1 block">Which country?</Label>
          <Select value={specific} onValueChange={v => setField('preferences', 'specific_country', v)}>
            <SelectTrigger data-testid="specific-country-select"><SelectValue placeholder="Pick a country" /></SelectTrigger>
            <SelectContent>
              {countries.map(c => (
                <SelectItem key={c.country_code} value={c.country_code}>{c.country_flag_emoji} {c.country}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[11px] text-slate-500 mt-1">Tip: if you&apos;re ineligible for this country, our engine will suggest 2–3 alternatives.</p>
        </div>
      )}

      {mode === 'custom' && (
        <div className="border-t pt-3" data-testid="custom-mode-picker">
          <Label className="text-xs font-bold mb-2 block">Pick 2–5 countries to compare</Label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {countries.map(c => {
              const selected = custom.includes(c.country_code);
              return (
                <button
                  key={c.country_code}
                  onClick={() => toggleCustom(c.country_code)}
                  className={`px-3 py-2 rounded border text-sm font-medium transition ${
                    selected ? 'border-indigo-500 bg-indigo-50 text-indigo-900' : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                  data-testid={`custom-toggle-${c.country_code}`}
                >
                  {c.country_flag_emoji} {c.country}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Selected: <strong>{custom.length}</strong> {custom.length < 2 && '· need at least 2'}</p>
        </div>
      )}
    </Card>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 1: Basic Info
// ════════════════════════════════════════════════════════════════
function StepBasic({ data, setRoot, setField }) {
  const dob = data.basic_info?.date_of_birth;
  const age = useMemo(() => {
    if (!dob) return null;
    try {
      const d = new Date(dob);
      const t = new Date();
      let a = t.getFullYear() - d.getFullYear();
      if ((t.getMonth(), t.getDate()) < (d.getMonth(), d.getDate())) a--;
      return a;
    } catch { return null; }
  }, [dob]);

  return (
    <Card className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold">Basic Information</h2>
        <p className="text-xs text-slate-500">Personal details — needed for age/family eligibility calculations.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2"><Label className="text-xs font-bold">Full Name *</Label><Input value={data.name} onChange={e => setRoot('name', e.target.value)} placeholder="e.g., Rohit Sharma" data-testid="basic-name" /></div>
        <div><Label className="text-xs font-bold">Email</Label><Input type="email" value={data.email || ''} onChange={e => setRoot('email', e.target.value)} placeholder="rohit@example.com" data-testid="basic-email" /></div>
        <div><Label className="text-xs font-bold">Phone</Label><Input value={data.phone || ''} onChange={e => setRoot('phone', e.target.value)} placeholder="+91 9..." data-testid="basic-phone" /></div>
        <div>
          <Label className="text-xs font-bold">Date of Birth *</Label>
          <Input type="date" value={dob || ''} onChange={e => setField('basic_info', 'date_of_birth', e.target.value)} data-testid="basic-dob" />
          {age !== null && <p className="text-[10px] text-emerald-600 mt-0.5">Age: <strong>{age}</strong></p>}
        </div>
        <div>
          <Label className="text-xs font-bold">Gender</Label>
          <Select value={data.basic_info?.gender || ''} onValueChange={v => setField('basic_info', 'gender', v)}>
            <SelectTrigger data-testid="basic-gender"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="male">Male</SelectItem>
              <SelectItem value="female">Female</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs font-bold">Marital Status</Label>
          <Select value={data.basic_info?.marital_status || ''} onValueChange={v => setField('basic_info', 'marital_status', v)}>
            <SelectTrigger data-testid="basic-marital"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="single">Single</SelectItem>
              <SelectItem value="married">Married</SelectItem>
              <SelectItem value="divorced">Divorced</SelectItem>
              <SelectItem value="widowed">Widowed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs font-bold">Dependents</Label><Input type="number" min={0} value={data.basic_info?.dependents_count ?? 0} onChange={e => setField('basic_info', 'dependents_count', Number(e.target.value))} data-testid="basic-dependents" /></div>
        <div><Label className="text-xs font-bold">Current Country</Label><Input value={data.basic_info?.current_country || ''} onChange={e => setField('basic_info', 'current_country', e.target.value)} placeholder="India" data-testid="basic-country" /></div>
        <div><Label className="text-xs font-bold">Current City</Label><Input value={data.basic_info?.current_city || ''} onChange={e => setField('basic_info', 'current_city', e.target.value)} placeholder="Mumbai" data-testid="basic-city" /></div>
        <div><Label className="text-xs font-bold">Nationality</Label><Input value={data.basic_info?.nationality || ''} onChange={e => setField('basic_info', 'nationality', e.target.value)} placeholder="Indian" data-testid="basic-nationality" /></div>
      </div>
    </Card>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 2: Profession + Education
// ════════════════════════════════════════════════════════════════
function StepProfessionEducation({ data, setField }) {
  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2"><Briefcase className="h-5 w-5 text-emerald-600" />Professional Details</h2>
          <p className="text-xs text-slate-500">Used to identify your ANZSCO/NOC code and eligible visa pathways.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Label className="text-xs font-bold">Current Profession *</Label><Input value={data.professional?.current_profession || ''} onChange={e => setField('professional', 'current_profession', e.target.value)} placeholder="e.g., Software Engineer" data-testid="prof-profession" /></div>
          <div><Label className="text-xs font-bold">Designation</Label><Input value={data.professional?.designation || ''} onChange={e => setField('professional', 'designation', e.target.value)} placeholder="Sr. Engineer" data-testid="prof-designation" /></div>
          <div><Label className="text-xs font-bold">Industry</Label><Input value={data.professional?.industry || ''} onChange={e => setField('professional', 'industry', e.target.value)} placeholder="IT / Software" data-testid="prof-industry" /></div>
          <div><Label className="text-xs font-bold">Total Years of Experience</Label><Input type="number" min={0} step={0.5} value={data.professional?.years_experience_total ?? 0} onChange={e => setField('professional', 'years_experience_total', Number(e.target.value))} data-testid="prof-yoe-total" /></div>
          <div><Label className="text-xs font-bold">Years in Current Role</Label><Input type="number" min={0} step={0.5} value={data.professional?.years_in_current_role ?? 0} onChange={e => setField('professional', 'years_in_current_role', Number(e.target.value))} data-testid="prof-yoe-current" /></div>
          <div><Label className="text-xs font-bold">Current Employer</Label><Input value={data.professional?.employer_name || ''} onChange={e => setField('professional', 'employer_name', e.target.value)} data-testid="prof-employer" /></div>
          <div><Label className="text-xs font-bold">Annual Salary (₹)</Label><Input type="number" min={0} value={data.professional?.salary_inr_per_annum || ''} onChange={e => setField('professional', 'salary_inr_per_annum', e.target.value === '' ? null : Number(e.target.value))} placeholder="2500000" data-testid="prof-salary" /></div>
          <div className="col-span-2 flex items-center gap-2 pt-1">
            <Switch checked={!!data.professional?.has_managerial_experience} onCheckedChange={v => setField('professional', 'has_managerial_experience', v)} data-testid="prof-managerial" />
            <Label className="text-xs">Have managerial / team-lead experience</Label>
          </div>
        </div>
      </Card>

      <Card className="p-6 space-y-3">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2"><GraduationCap className="h-5 w-5 text-sky-600" />Education</h2>
          <p className="text-xs text-slate-500">Highest qualification drives skill-assessment + points scoring.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-bold">Highest Qualification *</Label>
            <Select value={data.education?.highest_qualification || ''} onValueChange={v => setField('education', 'highest_qualification', v)}>
              <SelectTrigger data-testid="edu-qualification"><SelectValue placeholder="Pick highest" /></SelectTrigger>
              <SelectContent>
                {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div><Label className="text-xs font-bold">Field of Study</Label><Input value={data.education?.field_of_study || ''} onChange={e => setField('education', 'field_of_study', e.target.value)} placeholder="Computer Science" data-testid="edu-field" /></div>
          <div><Label className="text-xs font-bold">Institution</Label><Input value={data.education?.institution || ''} onChange={e => setField('education', 'institution', e.target.value)} placeholder="IIT Delhi" data-testid="edu-institution" /></div>
          <div><Label className="text-xs font-bold">Country</Label><Input value={data.education?.country || ''} onChange={e => setField('education', 'country', e.target.value)} placeholder="India" data-testid="edu-country" /></div>
          <div><Label className="text-xs font-bold">Year Completed</Label><Input type="number" min={1950} max={new Date().getFullYear()} value={data.education?.year_completed || ''} onChange={e => setField('education', 'year_completed', e.target.value === '' ? null : Number(e.target.value))} data-testid="edu-year" /></div>
        </div>
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 3: Language
// ════════════════════════════════════════════════════════════════
function StepLanguage({ data, setField }) {
  const lp = data.language_proficiency || {};
  const setScore = (band, val) => setField('language_proficiency', 'scores', {
    ...(lp.scores || {}), [band]: val === '' ? '' : Number(val),
  });

  return (
    <Card className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2"><MessageSquare className="h-5 w-5 text-amber-600" />Language Proficiency</h2>
        <p className="text-xs text-slate-500">Skip this if you haven&apos;t taken a test yet — we&apos;ll factor in your target score.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs font-bold">Primary Test</Label>
          <Select value={lp.primary_test || ''} onValueChange={v => setField('language_proficiency', 'primary_test', v)}>
            <SelectTrigger data-testid="lang-test"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="IELTS">IELTS (General / Academic)</SelectItem>
              <SelectItem value="PTE">PTE Academic</SelectItem>
              <SelectItem value="TOEFL">TOEFL iBT</SelectItem>
              <SelectItem value="CELPIP">CELPIP (Canada)</SelectItem>
              <SelectItem value="none">Haven&apos;t taken yet</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2 pt-5">
          <Switch checked={!!lp.test_completed} onCheckedChange={v => setField('language_proficiency', 'test_completed', v)} data-testid="lang-completed" />
          <Label className="text-xs">Test already completed</Label>
        </div>
        {lp.test_completed && (
          <>
            <div><Label className="text-xs font-bold">Test Date</Label><Input type="date" value={lp.test_date || ''} onChange={e => setField('language_proficiency', 'test_date', e.target.value)} data-testid="lang-date" /></div>
            <div className="col-span-2 grid grid-cols-5 gap-2 mt-2">
              {['overall', 'listening', 'reading', 'writing', 'speaking'].map(b => (
                <div key={b}>
                  <Label className="text-[10px] uppercase">{b}</Label>
                  <Input
                    type="number"
                    step={0.5}
                    min={0}
                    max={9}
                    value={lp.scores?.[b] ?? ''}
                    onChange={e => setScore(b, e.target.value)}
                    placeholder="0–9"
                    data-testid={`lang-score-${b}`}
                  />
                </div>
              ))}
            </div>
          </>
        )}
        {!lp.test_completed && (
          <div className="col-span-2">
            <Label className="text-xs font-bold">Target Score (optional)</Label>
            <Input value={lp.target_score || ''} onChange={e => setField('language_proficiency', 'target_score', e.target.value)} placeholder="e.g., IELTS 7.0 each band" data-testid="lang-target" />
          </div>
        )}
      </div>
    </Card>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 4: Family + Finances + Preferences
// ════════════════════════════════════════════════════════════════
function StepFamilyFinances({ data, setField }) {
  const fam = data.family || {};
  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <h2 className="text-lg font-bold flex items-center gap-2"><UsersIcon className="h-5 w-5 text-rose-600" />Family</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 flex items-center gap-2">
            <Switch checked={!!fam.spouse_present} onCheckedChange={v => setField('family', 'spouse_present', v)} data-testid="fam-spouse-switch" />
            <Label className="text-xs">Spouse / Partner</Label>
          </div>
          {fam.spouse_present && (
            <>
              <div><Label className="text-xs font-bold">Spouse Education</Label>
                <Select value={fam.spouse_education || ''} onValueChange={v => setField('family', 'spouse_education', v)}>
                  <SelectTrigger data-testid="fam-spouse-edu"><SelectValue placeholder="—" /></SelectTrigger>
                  <SelectContent>
                    {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs font-bold">Spouse Profession</Label><Input value={fam.spouse_profession || ''} onChange={e => setField('family', 'spouse_profession', e.target.value)} data-testid="fam-spouse-prof" /></div>
              <div><Label className="text-xs font-bold">Spouse English Level</Label>
                <Select value={fam.spouse_language || ''} onValueChange={v => setField('family', 'spouse_language', v)}>
                  <SelectTrigger data-testid="fam-spouse-lang"><SelectValue placeholder="—" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="competent">Competent (IELTS 6 / PTE 50)</SelectItem>
                    <SelectItem value="proficient">Proficient (IELTS 7 / PTE 65)</SelectItem>
                    <SelectItem value="superior">Superior (IELTS 8 / PTE 79)</SelectItem>
                    <SelectItem value="none">Below competent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
          <div><Label className="text-xs font-bold">Children Count</Label><Input type="number" min={0} value={fam.children_count ?? 0} onChange={e => setField('family', 'children_count', Number(e.target.value))} data-testid="fam-children" /></div>
        </div>
      </Card>

      <Card className="p-6 space-y-3">
        <h2 className="text-lg font-bold flex items-center gap-2"><DollarSign className="h-5 w-5 text-emerald-600" />Finances</h2>
        <p className="text-xs text-slate-500">Used to gauge proof-of-funds requirements. Optional.</p>
        <div className="grid grid-cols-2 gap-3">
          <div><Label className="text-xs font-bold">Annual Household Income (₹)</Label><Input type="number" min={0} value={data.finances?.annual_household_income || ''} onChange={e => setField('finances', 'annual_household_income', e.target.value === '' ? null : Number(e.target.value))} data-testid="fin-income" /></div>
          <div><Label className="text-xs font-bold">Savings (₹)</Label><Input type="number" min={0} value={data.finances?.savings_inr || ''} onChange={e => setField('finances', 'savings_inr', e.target.value === '' ? null : Number(e.target.value))} data-testid="fin-savings" /></div>
          <div><Label className="text-xs font-bold">Immigration Budget (₹)</Label><Input type="number" min={0} value={data.finances?.budget_for_immigration_inr || ''} onChange={e => setField('finances', 'budget_for_immigration_inr', e.target.value === '' ? null : Number(e.target.value))} data-testid="fin-budget" /></div>
          <div className="flex items-center gap-2 pt-5">
            <Switch checked={!!data.finances?.able_to_show_funds} onCheckedChange={v => setField('finances', 'able_to_show_funds', v)} data-testid="fin-show-funds" />
            <Label className="text-xs">Can show proof-of-funds</Label>
          </div>
        </div>
      </Card>

      <Card className="p-6 space-y-3">
        <h2 className="text-lg font-bold flex items-center gap-2"><Sparkles className="h-5 w-5 text-purple-600" />Preferences</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-bold">Timeline (months)</Label>
            <Select value={String(data.preferences?.timeline_months || 12)} onValueChange={v => setField('preferences', 'timeline_months', Number(v))}>
              <SelectTrigger data-testid="pref-timeline"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="6">6 months</SelectItem>
                <SelectItem value="12">12 months</SelectItem>
                <SelectItem value="18">18 months</SelectItem>
                <SelectItem value="24">24+ months</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-bold">Primary Priority</Label>
            <Select value={data.preferences?.priority || ''} onValueChange={v => setField('preferences', 'priority', v)}>
              <SelectTrigger data-testid="pref-priority"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="speed">Fastest pathway</SelectItem>
                <SelectItem value="cost">Lowest cost</SelectItem>
                <SelectItem value="quality_of_life">Quality of life</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <Switch checked={!!data.preferences?.family_relocation} onCheckedChange={v => setField('preferences', 'family_relocation', v)} data-testid="pref-family-reloc" />
            <Label className="text-xs">Family relocating together</Label>
          </div>
        </div>
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 5: Work History + Additional Factors
// ════════════════════════════════════════════════════════════════
function StepWorkExtras({ data, setRoot, setField }) {
  const history = data.work_history || [];
  const addEntry = () => setRoot('work_history', [...history, { employer: '', designation: '', start_date: '', end_date: '', country: '', duties: '', can_provide_reference: true }]);
  const removeEntry = (i) => setRoot('work_history', history.filter((_, idx) => idx !== i));
  const updateEntry = (i, k, v) => setRoot('work_history', history.map((h, idx) => idx === i ? { ...h, [k]: v } : h));

  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold flex items-center gap-2"><ClipboardList className="h-5 w-5 text-indigo-600" />Work History</h2>
          <Button size="sm" variant="outline" onClick={addEntry} data-testid="wh-add">
            <Plus className="h-4 w-4 mr-1" />Add Entry
          </Button>
        </div>
        <p className="text-xs text-slate-500">Add past employers (most recent first). Skill assessments require ≥3 years detailed history typically.</p>
        {history.length === 0 ? (
          <p className="text-xs italic text-slate-400 text-center py-4">No work history added yet.</p>
        ) : history.map((h, i) => (
          <Card key={i} className="p-3 bg-slate-50 space-y-2" data-testid={`wh-entry-${i}`}>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[11px] font-bold text-slate-600">Entry {i + 1}</p>
              <Button size="sm" variant="outline" className="h-6 w-6 p-0 text-rose-600" onClick={() => removeEntry(i)}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label className="text-[10px]">Employer</Label><Input value={h.employer || ''} onChange={e => updateEntry(i, 'employer', e.target.value)} /></div>
              <div><Label className="text-[10px]">Designation</Label><Input value={h.designation || ''} onChange={e => updateEntry(i, 'designation', e.target.value)} /></div>
              <div><Label className="text-[10px]">Start Date</Label><Input type="date" value={h.start_date || ''} onChange={e => updateEntry(i, 'start_date', e.target.value)} /></div>
              <div><Label className="text-[10px]">End Date (blank = present)</Label><Input type="date" value={h.end_date || ''} onChange={e => updateEntry(i, 'end_date', e.target.value)} /></div>
              <div><Label className="text-[10px]">Country</Label><Input value={h.country || ''} onChange={e => updateEntry(i, 'country', e.target.value)} /></div>
              <div className="flex items-center gap-2 pt-4">
                <Switch checked={!!h.can_provide_reference} onCheckedChange={v => updateEntry(i, 'can_provide_reference', v)} />
                <Label className="text-[10px]">Can provide reference letter</Label>
              </div>
              <div className="col-span-2"><Label className="text-[10px]">Roles & Responsibilities</Label><Textarea value={h.duties || ''} onChange={e => updateEntry(i, 'duties', e.target.value)} rows={2} placeholder="• Designed REST APIs..." /></div>
            </div>
          </Card>
        ))}
      </Card>

      <Card className="p-6 space-y-3">
        <h2 className="text-lg font-bold flex items-center gap-2"><Sparkles className="h-5 w-5 text-purple-600" />Additional Factors</h2>
        <p className="text-xs text-slate-500">These can dramatically affect eligibility — disclose openly.</p>
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.has_relative_in_target_country} onCheckedChange={v => setField('additional_factors', 'has_relative_in_target_country', v)} data-testid="extra-relative" />
            <Label className="text-xs">Relative in target country (citizen / PR)</Label>
          </div>
          {data.additional_factors?.has_relative_in_target_country && (
            <Input value={data.additional_factors?.relative_relationship || ''} onChange={e => setField('additional_factors', 'relative_relationship', e.target.value)} placeholder="Brother / Sister / Parent / Spouse..." data-testid="extra-relative-rel" />
          )}
          <div className="flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.has_job_offer} onCheckedChange={v => setField('additional_factors', 'has_job_offer', v)} data-testid="extra-job-offer" />
            <Label className="text-xs">Have a job offer from target country</Label>
          </div>
          <div>
            <Label className="text-xs font-bold">State Preference (optional)</Label>
            <Input value={data.additional_factors?.state_preference || ''} onChange={e => setField('additional_factors', 'state_preference', e.target.value)} placeholder="NSW / VIC / Ontario / BC..." data-testid="extra-state" />
          </div>
          <div>
            <Label className="text-xs font-bold">Medical Concerns</Label>
            <Textarea value={data.additional_factors?.medical_concerns || ''} onChange={e => setField('additional_factors', 'medical_concerns', e.target.value)} rows={2} placeholder="Any condition requiring ongoing treatment?" data-testid="extra-medical" />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.criminal_record} onCheckedChange={v => setField('additional_factors', 'criminal_record', v)} data-testid="extra-criminal" />
            <Label className="text-xs">Any criminal record / pending case?</Label>
          </div>
        </div>
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Step 6: Review & Submit
// ════════════════════════════════════════════════════════════════
function StepReview({ data, countries, onJump }) {
  const SECTIONS = [
    { key: 'mode', label: 'Search Mode', step: 0 },
    { key: 'basic', label: 'Basic Info', step: 1 },
    { key: 'prof', label: 'Profession & Education', step: 2 },
    { key: 'lang', label: 'Language', step: 3 },
    { key: 'family', label: 'Family & Finances', step: 4 },
    { key: 'work', label: 'Work & Extras', step: 5 },
  ];

  const modeLabel = SEARCH_MODES.find(m => m.value === data.preferences?.search_mode)?.label || '—';
  const specificName = countries.find(c => c.country_code === data.preferences?.specific_country)?.country;

  return (
    <Card className="p-6 space-y-4">
      <div className="text-center">
        <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-2" />
        <h2 className="text-xl font-bold">Ready to analyse</h2>
        <p className="text-xs text-slate-500">Verify everything is correct. You can jump back to any section.</p>
      </div>

      <Card className="p-4 bg-indigo-50 border-indigo-200">
        <p className="text-[10px] uppercase font-bold text-indigo-700 mb-1">Search Strategy</p>
        <p className="text-sm">
          {modeLabel}
          {data.preferences?.search_mode === 'specific' && specificName && <span className="text-indigo-700"> · {specificName}</span>}
          {data.preferences?.search_mode === 'custom' && data.preferences?.custom_countries?.length > 0 && (
            <span className="text-indigo-700"> · {data.preferences.custom_countries.join(', ')}</span>
          )}
        </p>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SECTIONS.map(s => (
          <ReviewCard key={s.key} label={s.label} onEdit={() => onJump(s.step)}>
            {s.key === 'basic' && (
              <>
                <Field label="Name" value={data.name} />
                <Field label="Email" value={data.email} />
                <Field label="Phone" value={data.phone} />
                <Field label="DOB" value={data.basic_info?.date_of_birth} />
                <Field label="Country" value={data.basic_info?.current_country} />
                <Field label="Marital" value={data.basic_info?.marital_status} />
              </>
            )}
            {s.key === 'prof' && (
              <>
                <Field label="Profession" value={data.professional?.current_profession} />
                <Field label="Designation" value={data.professional?.designation} />
                <Field label="Years XP" value={data.professional?.years_experience_total} />
                <Field label="Education" value={QUALIFICATIONS.find(q => q.v === data.education?.highest_qualification)?.l} />
                <Field label="Field" value={data.education?.field_of_study} />
                <Field label="Year" value={data.education?.year_completed} />
              </>
            )}
            {s.key === 'lang' && (
              <>
                <Field label="Test" value={data.language_proficiency?.primary_test} />
                <Field label="Completed?" value={data.language_proficiency?.test_completed ? 'Yes' : 'No'} />
                {data.language_proficiency?.test_completed && (
                  <Field label="Overall" value={data.language_proficiency?.scores?.overall} />
                )}
              </>
            )}
            {s.key === 'family' && (
              <>
                <Field label="Spouse" value={data.family?.spouse_present ? 'Yes' : 'No'} />
                <Field label="Children" value={data.family?.children_count} />
                <Field label="Income" value={data.finances?.annual_household_income ? `₹${data.finances.annual_household_income.toLocaleString('en-IN')}` : '—'} />
                <Field label="Savings" value={data.finances?.savings_inr ? `₹${data.finances.savings_inr.toLocaleString('en-IN')}` : '—'} />
              </>
            )}
            {s.key === 'work' && (
              <>
                <Field label="Work Entries" value={(data.work_history || []).length} />
                <Field label="Relative Abroad" value={data.additional_factors?.has_relative_in_target_country ? 'Yes' : 'No'} />
                <Field label="Job Offer" value={data.additional_factors?.has_job_offer ? 'Yes' : 'No'} />
              </>
            )}
            {s.key === 'mode' && (
              <Field label="Mode" value={modeLabel} />
            )}
          </ReviewCard>
        ))}
      </div>

      <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        <p className="font-bold mb-1">What happens next?</p>
        <ul className="text-[11px] space-y-0.5 ml-4 list-disc">
          <li>Profile saved as <strong>Complete</strong></li>
          <li>(Phase 6.3) AI engine analyses against selected countries</li>
          <li>(Phase 6.4) You see best-match country, visa, skill body, points breakdown, success probability</li>
        </ul>
      </div>
    </Card>
  );
}


function ReviewCard({ label, onEdit, children }) {
  return (
    <Card className="p-3 bg-white">
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] uppercase font-bold text-slate-500">{label}</p>
        <Button size="sm" variant="ghost" className="h-6 text-[10px] px-2 text-indigo-600" onClick={onEdit}>Edit</Button>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        {children}
      </div>
    </Card>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <p className="text-[9px] text-slate-400 uppercase">{label}</p>
      <p className="font-medium text-slate-800 truncate">{value || '—'}</p>
    </div>
  );
}
