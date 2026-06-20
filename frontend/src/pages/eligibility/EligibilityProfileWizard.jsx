/**
 * Phase 6.7 — Smart Profile Wizard with Conditional Spouse Logic
 *
 * Steps:
 *   1. Marital Status (FIRST per Phase 6.7 spec)
 *   2. Search Mode
 *   3. Primary Applicant — Personal
 *   4. Primary Applicant — Profession & Education
 *   5. Primary Applicant — Language
 *   6. Spouse Section  (CONDITIONAL — only shown when married/de_facto)
 *   7. Dependents + Preferences + Extras
 *   8. Review & Submit
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
  MessageSquare, Heart, Users as UsersIcon, ClipboardList, CheckCircle2,
  Plus, Trash2, Loader2, Layers, Compass, Star, User, Info, Upload,
} from 'lucide-react';

import { formatApiError, pruneEmpty } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MARITAL_OPTIONS = [
  { v: 'single', l: 'Single', sub: 'Never married' },
  { v: 'married', l: 'Married', sub: 'Living with spouse' },
  { v: 'de_facto', l: 'De facto / Partnership', sub: 'Living together >12 months' },
  { v: 'separated', l: 'Separated', sub: 'Legally separated' },
  { v: 'divorced', l: 'Divorced', sub: 'Legally divorced' },
  { v: 'widowed', l: 'Widowed', sub: 'Spouse passed away' },
];

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

const SPOUSE_CONTRIBUTION_OPTIONS = [
  {
    v: 'skill_assessment',
    l: 'Skill Assessment + Work Experience',
    pts: '+10',
    desc: 'Spouse has positive skill assessment, work exp, under 45, competent English',
  },
  {
    v: 'english_only',
    l: 'English Exam Only',
    pts: '+5',
    desc: 'Spouse has Competent English (IELTS 6+) — no skill assessment needed',
  },
  {
    v: 'non_contributing',
    l: 'Spouse Will Not Contribute',
    pts: '0',
    desc: 'Spouse will be on visa but not contributing to points',
  },
  {
    v: 'australian_pr_citizen',
    l: 'Spouse is Australian PR / Citizen',
    pts: '+10',
    desc: 'Spouse already has Australian permanent residency or citizenship',
  },
];

const STEPS = [
  { key: 'marital', label: 'Relationship', icon: Heart },
  { key: 'mode', label: 'Search Mode', icon: Target },
  { key: 'primary_personal', label: 'Primary · Personal', icon: User },
  { key: 'primary_prof_edu', label: 'Primary · Career', icon: Briefcase },
  { key: 'primary_language', label: 'Primary · Language', icon: MessageSquare },
  { key: 'spouse', label: 'Spouse', icon: UsersIcon, conditionalMarital: true },
  { key: 'dependents_extras', label: 'Dependents & Extras', icon: ClipboardList },
  { key: 'review', label: 'Review', icon: CheckCircle2 },
];


function emptyProfile() {
  return {
    name: '', email: '', phone: '',
    pa_id: null,
    marital_status: '',
    schema_version: 2,
    primary_applicant: {
      personal: {
        full_name: '', date_of_birth: '', gender: '', nationality: 'Indian',
        current_country: 'India', current_city: '',
      },
      professional: {
        current_profession: '', designation: '', years_experience_total: 0, years_in_current_role: 0,
        industry: '', employer_name: '', salary_inr_per_annum: '', has_managerial_experience: false,
      },
      education: {
        highest_qualification: '', field_of_study: '', institution: '', country: 'India', year_completed: '',
      },
      language: {
        primary_test: 'IELTS', test_completed: false, test_date: '',
        scores: { overall: '', listening: '', reading: '', writing: '', speaking: '' },
        target_score: '',
      },
      work_history: [],
    },
    spouse: null,
    dependents: [],
    preferences: {
      timeline_months: 12, preferred_countries: [], avoiding_countries: [],
      priority: 'quality_of_life',
      search_mode: 'top_3', specific_country: '', custom_countries: [],
    },
    additional_factors: {
      has_relative_in_target_country: false, relative_relationship: '',
      has_job_offer: false, state_preference: '',
      medical_concerns: '', criminal_record: false,
    },
    status: 'draft',
  };
}


function emptySpouse() {
  return {
    is_applicant_on_visa: true,
    contribution_type: 'skill_assessment',
    is_australian_pr_or_citizen: false,
    personal: { full_name: '', date_of_birth: '', age: null, nationality: '' },
    professional: { current_profession: '', years_experience_total: 0 },
    education: { highest_qualification: '', field_of_study: '' },
    language: { primary_test: 'IELTS', test_completed: false, scores: { overall: '', listening: '', reading: '', writing: '', speaking: '' } },
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
  const [resumeBusy, setResumeBusy] = useState(false);
  const resumeInputRef = useRef(null);
  const lastAutoSavedSnapshot = useRef(null);

  // Phase 6.7 Part 2 — handle in-wizard resume upload (replaces or pre-fills the current form)
  const handleResumeUpload = async (file) => {
    if (!file) return;
    const ok = ['.pdf', '.docx', '.txt'].some(ext => file.name.toLowerCase().endsWith(ext));
    if (!ok) { toast.error('Only PDF, DOCX, or TXT files allowed'); return; }
    if (file.size > 10 * 1024 * 1024) { toast.error('File too large — max 10 MB'); return; }
    setResumeBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/eligibility/profiles/resume-extract`, form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        timeout: 90000,
      });
      // Deep-merge AI-extracted data into the existing form (preserves user-entered fields)
      setData(d => deepMerge(d, r.data));
      toast.success('Resume extracted — please review the auto-filled fields below');
    } catch (e) {
      toast.error(formatApiError(e, 'Resume extraction failed'));
    } finally {
      setResumeBusy(false);
      if (resumeInputRef.current) resumeInputRef.current.value = '';
    }
  };

  useEffect(() => {
    (async () => {
      try {
        if (profileId) {
          const r = await axios.get(`${API}/eligibility/profiles/${profileId}`, { headers });
          // Merge loaded data with empty defaults so all sections exist
          setData(d => deepMerge(emptyProfile(), r.data));
          setCurrentProfileId(profileId);
        } else if (prefillPaId) {
          const r = await axios.post(`${API}/eligibility/profiles/prefill-from-pa/${prefillPaId}`, {}, { headers });
          setData(d => deepMerge(emptyProfile(), r.data));
        } else {
          // Phase 6.7 Part 2 — resume-upload prefill via sessionStorage
          const sourceParam = searchParams.get('source');
          if (sourceParam === 'resume') {
            const raw = sessionStorage.getItem('eligibility_resume_prefill');
            if (raw) {
              try {
                const parsed = JSON.parse(raw);
                setData(d => deepMerge(emptyProfile(), parsed));
                toast.success('Resume data loaded — please review and complete');
              } catch (_) { /* ignore */ }
              sessionStorage.removeItem('eligibility_resume_prefill');
            }
          }
        }
      } catch (e) {
        toast.error(formatApiError(e, 'Failed to load profile'));
      } finally { setLoading(false); }
    })();
  }, [profileId, prefillPaId, headers, searchParams]);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/eligibility/kb/countries`, { headers });
        setCountries((r.data.items || []).filter(c => c.is_active));
      } catch (_) {}
    })();
  }, [headers]);

  // Filter out conditional spouse step when applicable
  const activeSteps = useMemo(() => {
    return STEPS.filter(s => !s.conditionalMarital || isSpouseRequired(data.marital_status));
  }, [data.marital_status]);

  // Auto-save every 30s
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
    if (!data.name) return;
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
    } catch (_) { /* silent */ }
    finally { setSaving(false); }
  }, [data, currentProfileId, saving, headers]);

  const saveManual = useCallback(async () => {
    if (!data.name) { toast.error('Name is required'); return; }
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
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  }, [data, currentProfileId, headers]);

  const submitAndAnalyse = async () => {
    if (!data.name) { toast.error('Primary applicant name is required'); return; }
    if (!data.marital_status) { toast.error('Please select marital status (Step 1)'); return; }
    setSaving(true);
    try {
      const cleaned = { ...pruneEmpty(data), status: 'complete' };
      let pid = currentProfileId;
      if (pid) {
        await axios.patch(`${API}/eligibility/profiles/${pid}`, cleaned, { headers });
      } else {
        const r = await axios.post(`${API}/eligibility/profiles`, cleaned, { headers });
        pid = r.data.id;
        setCurrentProfileId(pid);
      }
      toast.success('Profile saved — opening Smart Sales Helper');
      navigate(`/sales/occupations`);
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  // Helpers
  const setRoot = (field, val) => setData(d => ({ ...d, [field]: val }));
  const setPrimaryField = (section, field, val) =>
    setData(d => ({
      ...d,
      primary_applicant: {
        ...d.primary_applicant,
        [section]: { ...(d.primary_applicant[section] || {}), [field]: val },
      },
    }));
  const setSpouseField = (section, field, val) =>
    setData(d => ({
      ...d,
      spouse: {
        ...(d.spouse || emptySpouse()),
        [section]: { ...((d.spouse || emptySpouse())[section] || {}), [field]: val },
      },
    }));
  const setSpouseRoot = (field, val) =>
    setData(d => ({ ...d, spouse: { ...(d.spouse || emptySpouse()), [field]: val } }));
  const setPrefField = (field, val) =>
    setData(d => ({ ...d, preferences: { ...d.preferences, [field]: val } }));

  // Mutual exclusion: changing marital_status to single/divorced/widowed/separated clears spouse
  const setMaritalStatus = (val) => {
    setData(d => {
      const next = { ...d, marital_status: val };
      if (!isSpouseRequired(val)) next.spouse = null;
      else if (!next.spouse) next.spouse = emptySpouse();
      return next;
    });
  };

  // Step validation
  const canProceed = useMemo(() => {
    const sKey = activeSteps[step]?.key;
    switch (sKey) {
      case 'marital': return !!data.marital_status;
      case 'mode': {
        const m = data.preferences?.search_mode;
        if (!m) return false;
        if (m === 'specific') return !!data.preferences?.specific_country;
        if (m === 'custom') return (data.preferences?.custom_countries?.length || 0) >= 2;
        return true;
      }
      case 'primary_personal':
        return !!data.name && !!data.primary_applicant?.personal?.date_of_birth;
      case 'primary_prof_edu':
        return !!data.primary_applicant?.professional?.current_profession
            && !!data.primary_applicant?.education?.highest_qualification;
      case 'primary_language': return true;
      case 'spouse': {
        if (!isSpouseRequired(data.marital_status)) return true;
        if (!data.spouse) return false;
        // Need contribution type and a name
        return !!data.spouse.contribution_type;
      }
      case 'dependents_extras': return true;
      default: return true;
    }
  }, [step, data, activeSteps]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">Loading profile…</div>;
  }

  const currentStep = activeSteps[step];
  const StepIcon = currentStep?.icon || Sparkles;

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
              <p className="text-xs uppercase text-slate-400 tracking-wide">AI Eligibility · v6.7</p>
              <h1 className="text-base font-bold">
                <StepIcon className="inline h-4 w-4 mr-1 text-leamss-teal-600" />
                Step {step + 1} of {activeSteps.length}: {currentStep?.label}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {saving && <span className="text-[11px] text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Saving…</span>}
            {currentProfileId && <Badge className="bg-slate-100 text-slate-600 text-[10px]">{currentProfileId}</Badge>}
            <input
              ref={resumeInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => handleResumeUpload(e.target.files?.[0])}
              data-testid="wizard-resume-input"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => resumeInputRef.current?.click()}
              disabled={resumeBusy}
              data-testid="wizard-upload-resume"
              title="Upload a resume → AI auto-fills the form"
            >
              {resumeBusy ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Upload className="h-3.5 w-3.5 mr-1" />}
              {resumeBusy ? 'Extracting…' : 'Upload Resume'}
            </Button>
            <Button variant="outline" size="sm" onClick={saveManual} disabled={saving} data-testid="wizard-save-now">
              <Save className="h-3.5 w-3.5 mr-1" />Save Draft
            </Button>
          </div>
        </div>
        <div className="max-w-5xl mx-auto px-6 pb-3 flex items-center gap-1.5">
          {activeSteps.map((s, i) => (
            <button
              key={s.key}
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              className={`flex-1 h-1.5 rounded transition ${
                i === step ? 'bg-leamss-teal-600' : i < step ? 'bg-leamss-teal-300 cursor-pointer hover:bg-leamss-teal-400' : 'bg-slate-200'
              }`}
              title={s.label}
              data-testid={`progress-dot-${i}`}
            />
          ))}
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {currentStep?.key === 'marital' && <StepMarital data={data} setMarital={setMaritalStatus} setRoot={setRoot} />}
        {currentStep?.key === 'mode' && <StepMode data={data} setPref={setPrefField} countries={countries} />}
        {currentStep?.key === 'primary_personal' && <StepPrimaryPersonal data={data} setRoot={setRoot} setField={setPrimaryField} />}
        {currentStep?.key === 'primary_prof_edu' && <StepPrimaryProfEdu data={data} setField={setPrimaryField} />}
        {currentStep?.key === 'primary_language' && <StepPrimaryLanguage data={data} setField={setPrimaryField} />}
        {currentStep?.key === 'spouse' && <StepSpouse data={data} setSpouseField={setSpouseField} setSpouseRoot={setSpouseRoot} />}
        {currentStep?.key === 'dependents_extras' && <StepDependentsExtras data={data} setRoot={setRoot} setPref={setPrefField} setField={setPrimaryField} />}
        {currentStep?.key === 'review' && <StepReview data={data} countries={countries} onJump={setStep} activeSteps={activeSteps} />}

        <Card className="p-3 flex items-center justify-between sticky bottom-2 shadow-lg">
          <Button variant="outline" onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0} data-testid="step-prev">
            <ArrowLeft className="h-4 w-4 mr-1" />Previous
          </Button>
          <div className="text-xs text-slate-500">{step + 1} / {activeSteps.length}</div>
          {step < activeSteps.length - 1 ? (
            <Button
              onClick={() => setStep(s => Math.min(activeSteps.length - 1, s + 1))}
              disabled={!canProceed}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700"
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


// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────
function isSpouseRequired(marital_status) {
  return marital_status === 'married' || marital_status === 'de_facto';
}

function deepMerge(target, source) {
  if (!source) return target;
  const out = { ...target };
  for (const k of Object.keys(source)) {
    const sv = source[k];
    if (sv === null || sv === undefined) continue;
    if (typeof sv === 'object' && !Array.isArray(sv) && typeof target[k] === 'object' && target[k] !== null) {
      out[k] = deepMerge(target[k], sv);
    } else {
      out[k] = sv;
    }
  }
  return out;
}


// ──────────────────────────────────────────────────────────────
// Step Components
// ──────────────────────────────────────────────────────────────
function StepMarital({ data, setMarital, setRoot }) {
  return (
    <Card className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2"><Heart className="h-5 w-5 text-rose-500" />Relationship Status</h2>
        <p className="text-xs text-slate-500">This drives the entire form — spouse fields are conditionally shown.</p>
      </div>
      <div>
        <Label className="text-xs font-bold">Primary Applicant Name *</Label>
        <Input value={data.name} onChange={e => setRoot('name', e.target.value)} placeholder="e.g., Rohit Sharma" data-testid="primary-name" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {MARITAL_OPTIONS.map(opt => {
          const active = data.marital_status === opt.v;
          return (
            <button
              key={opt.v}
              type="button"
              onClick={() => setMarital(opt.v)}
              className={`text-left p-3 rounded-lg border-2 transition ${
                active ? 'border-rose-500 bg-rose-50' : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
              data-testid={`marital-${opt.v}`}
            >
              <p className="font-bold text-sm">{opt.l}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">{opt.sub}</p>
            </button>
          );
        })}
      </div>
      {isSpouseRequired(data.marital_status) && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800 flex items-start gap-2">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>You&apos;ll capture spouse details in a dedicated step later. The system tracks spouse separately from the primary applicant.</span>
        </div>
      )}
      {data.marital_status && !isSpouseRequired(data.marital_status) && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 flex items-start gap-2">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>Single applicant — spouse fields will be skipped. Single applicants automatically receive <strong>+10 partner skill points</strong> in Australia.</span>
        </div>
      )}
    </Card>
  );
}


function StepMode({ data, setPref, countries }) {
  const mode = data.preferences?.search_mode || 'top_3';
  const specific = data.preferences?.specific_country || '';
  const custom = data.preferences?.custom_countries || [];
  const toggleCustom = (code) => {
    let next = custom.includes(code) ? custom.filter(c => c !== code) : [...custom, code];
    if (next.length > 5) next = next.slice(0, 5);
    setPref('custom_countries', next);
  };
  return (
    <Card className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold">Search Strategy</h2>
        <p className="text-xs text-slate-500">Choose how the AI will analyse eligibility.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SEARCH_MODES.map(m => {
          const Icon = m.icon;
          const active = mode === m.value;
          return (
            <button
              key={m.value}
              onClick={() => setPref('search_mode', m.value)}
              className={`text-left p-4 rounded-lg border-2 transition relative ${
                active ? `border-${m.color}-500 bg-${m.color}-50` : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
              data-testid={`mode-${m.value}`}
            >
              {m.recommended && <Badge className={`absolute -top-2 right-3 bg-${m.color}-600 text-white text-[9px]`}>RECOMMENDED</Badge>}
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
          <Select value={specific} onValueChange={v => setPref('specific_country', v)}>
            <SelectTrigger data-testid="specific-country-select"><SelectValue placeholder="Pick a country" /></SelectTrigger>
            <SelectContent>
              {countries.map(c => <SelectItem key={c.country_code} value={c.country_code}>{c.country_flag_emoji} {c.country}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      )}
      {mode === 'custom' && (
        <div className="border-t pt-3" data-testid="custom-mode-picker">
          <Label className="text-xs font-bold mb-2 block">Pick 2–5 countries</Label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {countries.map(c => {
              const selected = custom.includes(c.country_code);
              return (
                <button
                  key={c.country_code}
                  onClick={() => toggleCustom(c.country_code)}
                  className={`px-3 py-2 rounded border text-sm font-medium transition ${
                    selected ? 'border-leamss-teal-500 bg-leamss-teal-50 text-leamss-teal-900' : 'border-slate-200 bg-white hover:border-slate-300'
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


function StepPrimaryPersonal({ data, setRoot, setField }) {
  const personal = data.primary_applicant?.personal || {};
  const dob = personal.date_of_birth;
  const age = useMemo(() => {
    if (!dob) return null;
    try {
      const d = new Date(dob); const t = new Date();
      let a = t.getFullYear() - d.getFullYear();
      if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--;
      return a;
    } catch { return null; }
  }, [dob]);

  return (
    <Card className="p-6 space-y-4">
      <div className="bg-leamss-teal-50 border border-leamss-teal-200 rounded p-3">
        <p className="text-[11px] uppercase font-bold text-leamss-teal-700 flex items-center gap-1"><User className="h-3.5 w-3.5" />Primary Applicant</p>
        <p className="text-xs text-leamss-teal-800 mt-1">All fields below describe the <strong>primary applicant</strong> — the person whose ANZSCO code will be matched and whose eligibility is calculated.</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2"><Label className="text-xs font-bold">Full Name *</Label><Input value={data.name} onChange={e => setRoot('name', e.target.value)} data-testid="primary-fullname" /></div>
        <div><Label className="text-xs font-bold">Email</Label><Input type="email" value={data.email || ''} onChange={e => setRoot('email', e.target.value)} data-testid="primary-email" /></div>
        <div><Label className="text-xs font-bold">Phone</Label><Input value={data.phone || ''} onChange={e => setRoot('phone', e.target.value)} data-testid="primary-phone" /></div>
        <div>
          <Label className="text-xs font-bold">Date of Birth *</Label>
          <Input type="date" value={dob || ''} onChange={e => setField('personal', 'date_of_birth', e.target.value)} data-testid="primary-dob" />
          {age !== null && <p className="text-[10px] text-emerald-600 mt-0.5">Age: <strong>{age}</strong></p>}
        </div>
        <div>
          <Label className="text-xs font-bold">Gender</Label>
          <Select value={personal.gender || ''} onValueChange={v => setField('personal', 'gender', v)}>
            <SelectTrigger data-testid="primary-gender"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="male">Male</SelectItem>
              <SelectItem value="female">Female</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs font-bold">Current Country</Label><Input value={personal.current_country || ''} onChange={e => setField('personal', 'current_country', e.target.value)} data-testid="primary-country" /></div>
        <div><Label className="text-xs font-bold">Current City</Label><Input value={personal.current_city || ''} onChange={e => setField('personal', 'current_city', e.target.value)} data-testid="primary-city" /></div>
        <div><Label className="text-xs font-bold">Nationality</Label><Input value={personal.nationality || ''} onChange={e => setField('personal', 'nationality', e.target.value)} data-testid="primary-nationality" /></div>
      </div>
    </Card>
  );
}


function StepPrimaryProfEdu({ data, setField }) {
  const prof = data.primary_applicant?.professional || {};
  const edu = data.primary_applicant?.education || {};
  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <div className="bg-leamss-teal-50 border border-leamss-teal-200 rounded p-3">
          <p className="text-[11px] uppercase font-bold text-leamss-teal-700 flex items-center gap-1"><Briefcase className="h-3.5 w-3.5" />Primary · Profession</p>
          <p className="text-xs text-leamss-teal-800 mt-1">Use the <strong>current</strong> profession — what you DO now, not what you studied. AI will match ANZSCO code from your current role + recent work history.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Label className="text-xs font-bold">Current Profession *</Label><Input value={prof.current_profession || ''} onChange={e => setField('professional', 'current_profession', e.target.value)} placeholder="e.g., Marketing Specialist (current role, not past degree)" data-testid="prof-current-profession" /></div>
          <div><Label className="text-xs font-bold">Designation</Label><Input value={prof.designation || ''} onChange={e => setField('professional', 'designation', e.target.value)} data-testid="prof-designation" /></div>
          <div><Label className="text-xs font-bold">Industry</Label><Input value={prof.industry || ''} onChange={e => setField('professional', 'industry', e.target.value)} data-testid="prof-industry" /></div>
          <div><Label className="text-xs font-bold">Total Years Experience</Label><Input type="number" min={0} step={0.5} value={prof.years_experience_total ?? 0} onChange={e => setField('professional', 'years_experience_total', Number(e.target.value))} data-testid="prof-yoe-total" /></div>
          <div><Label className="text-xs font-bold">Years in Current Role</Label><Input type="number" min={0} step={0.5} value={prof.years_in_current_role ?? 0} onChange={e => setField('professional', 'years_in_current_role', Number(e.target.value))} data-testid="prof-yoe-current" /></div>
          <div><Label className="text-xs font-bold">Current Employer</Label><Input value={prof.employer_name || ''} onChange={e => setField('professional', 'employer_name', e.target.value)} data-testid="prof-employer" /></div>
          <div><Label className="text-xs font-bold">Annual Salary (₹)</Label><Input type="number" min={0} value={prof.salary_inr_per_annum || ''} onChange={e => setField('professional', 'salary_inr_per_annum', e.target.value === '' ? null : Number(e.target.value))} data-testid="prof-salary" /></div>
          <div className="col-span-2 flex items-center gap-2 pt-1">
            <Switch checked={!!prof.has_managerial_experience} onCheckedChange={v => setField('professional', 'has_managerial_experience', v)} data-testid="prof-managerial" />
            <Label className="text-xs">Have managerial / team-lead experience</Label>
          </div>
        </div>
      </Card>

      <Card className="p-6 space-y-3">
        <div className="bg-sky-50 border border-sky-200 rounded p-3">
          <p className="text-[11px] uppercase font-bold text-sky-700 flex items-center gap-1"><GraduationCap className="h-3.5 w-3.5" />Primary · Education</p>
          <p className="text-xs text-sky-800 mt-1">Highest qualification drives education points and skill body matching (NOT occupation code — that uses current profession).</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-bold">Highest Qualification *</Label>
            <Select value={edu.highest_qualification || ''} onValueChange={v => setField('education', 'highest_qualification', v)}>
              <SelectTrigger data-testid="edu-qualification"><SelectValue placeholder="Pick highest" /></SelectTrigger>
              <SelectContent>
                {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div><Label className="text-xs font-bold">Field of Study</Label><Input value={edu.field_of_study || ''} onChange={e => setField('education', 'field_of_study', e.target.value)} placeholder="e.g., Veterinary Science (past degree)" data-testid="edu-field" /></div>
          <div><Label className="text-xs font-bold">Institution</Label><Input value={edu.institution || ''} onChange={e => setField('education', 'institution', e.target.value)} data-testid="edu-institution" /></div>
          <div><Label className="text-xs font-bold">Country</Label><Input value={edu.country || ''} onChange={e => setField('education', 'country', e.target.value)} data-testid="edu-country" /></div>
          <div><Label className="text-xs font-bold">Year Completed</Label><Input type="number" min={1950} max={new Date().getFullYear()} value={edu.year_completed || ''} onChange={e => setField('education', 'year_completed', e.target.value === '' ? null : Number(e.target.value))} data-testid="edu-year" /></div>
        </div>
      </Card>
    </div>
  );
}


function StepPrimaryLanguage({ data, setField }) {
  const lp = data.primary_applicant?.language || {};
  const setScore = (band, val) => setField('language', 'scores', { ...(lp.scores || {}), [band]: val === '' ? '' : Number(val) });
  return (
    <Card className="p-6 space-y-4">
      <div className="bg-amber-50 border border-amber-200 rounded p-3">
        <p className="text-[11px] uppercase font-bold text-amber-700 flex items-center gap-1"><MessageSquare className="h-3.5 w-3.5" />Primary · Language</p>
        <p className="text-xs text-amber-800 mt-1">English proficiency — applied per-band. Required for visa eligibility AND points scoring.</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs font-bold">Primary Test</Label>
          <Select value={lp.primary_test || 'IELTS'} onValueChange={v => setField('language', 'primary_test', v)}>
            <SelectTrigger data-testid="lang-test"><SelectValue /></SelectTrigger>
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
          <Switch checked={!!lp.test_completed} onCheckedChange={v => setField('language', 'test_completed', v)} data-testid="lang-completed" />
          <Label className="text-xs">Test already completed</Label>
        </div>
        {lp.test_completed && (
          <>
            <div><Label className="text-xs font-bold">Test Date</Label><Input type="date" value={lp.test_date || ''} onChange={e => setField('language', 'test_date', e.target.value)} data-testid="lang-date" /></div>
            <div className="col-span-2 grid grid-cols-5 gap-2 mt-2">
              {['overall', 'listening', 'reading', 'writing', 'speaking'].map(b => (
                <div key={b}>
                  <Label className="text-[10px] uppercase">{b}</Label>
                  <Input type="number" step={0.5} min={0} max={9}
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
            <Input value={lp.target_score || ''} onChange={e => setField('language', 'target_score', e.target.value)} placeholder="e.g., IELTS 7.0 each band" data-testid="lang-target" />
          </div>
        )}
      </div>
    </Card>
  );
}


function StepSpouse({ data, setSpouseField, setSpouseRoot }) {
  const spouse = data.spouse || emptySpouse();
  const contribution = spouse.contribution_type || 'skill_assessment';
  const isOnVisa = spouse.is_applicant_on_visa;

  const setContrib = (v) => setSpouseRoot('contribution_type', v);

  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <div className="bg-leamss-orange-50 border border-leamss-orange-200 rounded p-3">
          <p className="text-[11px] uppercase font-bold text-leamss-orange-700 flex items-center gap-1"><UsersIcon className="h-3.5 w-3.5" />Spouse Information</p>
          <p className="text-xs text-leamss-orange-800 mt-1">Spouse data is tracked <strong>separately</strong> from primary applicant. Spouse contribution determines partner skill points — only relevant fields will be shown below.</p>
        </div>

        {/* Q1: Will spouse be on visa application? */}
        <div>
          <Label className="text-xs font-bold mb-2 block">Will your spouse be on the visa application?</Label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setSpouseRoot('is_applicant_on_visa', true)}
              className={`p-3 rounded border-2 text-sm transition ${isOnVisa ? 'border-leamss-orange-500 bg-leamss-orange-50 font-bold' : 'border-slate-200 bg-white'}`}
              data-testid="spouse-on-visa-yes"
            >
              ✅ Yes — Spouse will be included
            </button>
            <button
              type="button"
              onClick={() => { setSpouseRoot('is_applicant_on_visa', false); setSpouseRoot('contribution_type', 'not_applicable'); }}
              className={`p-3 rounded border-2 text-sm transition ${!isOnVisa ? 'border-leamss-orange-500 bg-leamss-orange-50 font-bold' : 'border-slate-200 bg-white'}`}
              data-testid="spouse-on-visa-no"
            >
              ❌ No — Spouse will not migrate
            </button>
          </div>
        </div>

        {/* Q2: Contribution type */}
        {isOnVisa && (
          <div>
            <Label className="text-xs font-bold mb-2 block">What will spouse contribute to your application?</Label>
            <div className="space-y-2">
              {SPOUSE_CONTRIBUTION_OPTIONS.map(opt => (
                <button
                  key={opt.v}
                  type="button"
                  onClick={() => setContrib(opt.v)}
                  className={`w-full text-left p-3 rounded border-2 transition ${
                    contribution === opt.v ? 'border-leamss-orange-500 bg-leamss-orange-50' : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                  data-testid={`spouse-contrib-${opt.v}`}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-bold text-sm">{opt.l}</p>
                    <Badge className={opt.pts === '0' ? 'bg-slate-100 text-slate-600' : 'bg-emerald-100 text-emerald-700'}>{opt.pts} pts</Badge>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-0.5">{opt.desc}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Basic spouse identity (always shown if on visa OR migrating) */}
        <div className="border-t pt-3 grid grid-cols-2 gap-3">
          <div className="col-span-2"><Label className="text-xs font-bold">Spouse Full Name</Label><Input value={spouse.personal?.full_name || ''} onChange={e => setSpouseField('personal', 'full_name', e.target.value)} data-testid="spouse-name" /></div>
          <div><Label className="text-xs font-bold">Spouse Date of Birth</Label><Input type="date" value={spouse.personal?.date_of_birth || ''} onChange={e => setSpouseField('personal', 'date_of_birth', e.target.value)} data-testid="spouse-dob" /></div>
          <div><Label className="text-xs font-bold">Spouse Nationality</Label><Input value={spouse.personal?.nationality || ''} onChange={e => setSpouseField('personal', 'nationality', e.target.value)} data-testid="spouse-nationality" /></div>
        </div>

        {/* Conditional spouse fields based on contribution_type */}
        {isOnVisa && contribution === 'skill_assessment' && (
          <div className="border-t pt-3 space-y-3" data-testid="spouse-skill-fields">
            <p className="text-xs font-bold text-leamss-orange-700">Spouse Skill Details (for +10 partner skill points)</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2"><Label className="text-xs">Spouse Current Profession</Label><Input value={spouse.professional?.current_profession || ''} onChange={e => setSpouseField('professional', 'current_profession', e.target.value)} placeholder="e.g., Registered Nurse" data-testid="spouse-profession" /></div>
              <div><Label className="text-xs">Spouse Years Experience</Label><Input type="number" min={0} value={spouse.professional?.years_experience_total ?? 0} onChange={e => setSpouseField('professional', 'years_experience_total', Number(e.target.value))} data-testid="spouse-yoe" /></div>
              <div>
                <Label className="text-xs">Spouse Qualification</Label>
                <Select value={spouse.education?.highest_qualification || ''} onValueChange={v => setSpouseField('education', 'highest_qualification', v)}>
                  <SelectTrigger data-testid="spouse-qualification"><SelectValue placeholder="—" /></SelectTrigger>
                  <SelectContent>
                    {QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Spouse IELTS Overall</Label><Input type="number" step={0.5} min={0} max={9} value={spouse.language?.scores?.overall ?? ''} onChange={e => setSpouseField('language', 'scores', { ...(spouse.language?.scores || {}), overall: e.target.value === '' ? '' : Number(e.target.value) })} placeholder="6.0+" data-testid="spouse-ielts" /></div>
            </div>
          </div>
        )}

        {isOnVisa && contribution === 'english_only' && (
          <div className="border-t pt-3 space-y-3" data-testid="spouse-english-fields">
            <p className="text-xs font-bold text-leamss-orange-700">Spouse English Details (for +5 partner skill points)</p>
            <p className="text-[11px] text-slate-500">Only English proficiency is required — no skill assessment needed.</p>
            <div className="grid grid-cols-5 gap-2">
              {['overall', 'listening', 'reading', 'writing', 'speaking'].map(b => (
                <div key={b}>
                  <Label className="text-[10px] uppercase">{b}</Label>
                  <Input type="number" step={0.5} min={0} max={9} value={spouse.language?.scores?.[b] ?? ''} onChange={e => setSpouseField('language', 'scores', { ...(spouse.language?.scores || {}), [b]: e.target.value === '' ? '' : Number(e.target.value) })} data-testid={`spouse-eng-${b}`} />
                </div>
              ))}
            </div>
          </div>
        )}

        {isOnVisa && contribution === 'australian_pr_citizen' && (
          <div className="border-t pt-3 space-y-2 bg-emerald-50 p-3 rounded" data-testid="spouse-pr-fields">
            <p className="text-xs font-bold text-emerald-800">Spouse PR / Citizenship Details (for +10 partner skill points)</p>
            <div className="grid grid-cols-1 gap-2">
              <div className="flex items-center gap-2">
                <Switch checked={!!spouse.is_australian_pr_or_citizen} onCheckedChange={v => setSpouseRoot('is_australian_pr_or_citizen', v)} data-testid="spouse-is-pr" />
                <Label className="text-xs">I confirm spouse holds Australian PR or Citizenship</Label>
              </div>
            </div>
          </div>
        )}

        {isOnVisa && contribution === 'non_contributing' && (
          <div className="border-t pt-3 bg-slate-50 p-3 rounded text-xs text-slate-600" data-testid="spouse-noncontrib-info">
            Spouse will be on visa but no skill/English assessment is being done — <strong>0 partner skill points</strong>. Only basic identity captured above.
          </div>
        )}

        {!isOnVisa && (
          <div className="border-t pt-3 bg-amber-50 p-3 rounded text-xs text-amber-800" data-testid="spouse-not-migrating-info">
            Spouse is <strong>not migrating</strong>. Marital status remains <strong>{data.marital_status}</strong>. Partner skill points: <strong>0</strong>.
          </div>
        )}
      </Card>
    </div>
  );
}


function StepDependentsExtras({ data, setRoot, setPref, setField }) {
  const dependents = data.dependents || [];
  const addDep = () => setRoot('dependents', [...dependents, { role: 'child', age: '' }]);
  const removeDep = (i) => setRoot('dependents', dependents.filter((_, idx) => idx !== i));
  const updDep = (i, k, v) => setRoot('dependents', dependents.map((d, idx) => idx === i ? { ...d, [k]: v } : d));

  return (
    <div className="space-y-4">
      <Card className="p-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold flex items-center gap-2"><UsersIcon className="h-5 w-5 text-rose-500" />Dependents</h2>
          <Button size="sm" variant="outline" onClick={addDep} data-testid="dep-add"><Plus className="h-4 w-4 mr-1" />Add</Button>
        </div>
        {dependents.length === 0 ? (
          <p className="text-xs italic text-slate-400 text-center py-3">No dependents added.</p>
        ) : dependents.map((d, i) => (
          <Card key={i} className="p-3 bg-slate-50 grid grid-cols-3 gap-2" data-testid={`dep-${i}`}>
            <div>
              <Label className="text-[10px]">Role</Label>
              <Select value={d.role || 'child'} onValueChange={v => updDep(i, 'role', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="child">Child</SelectItem>
                  <SelectItem value="parent">Parent</SelectItem>
                  <SelectItem value="sibling">Sibling</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label className="text-[10px]">Age</Label><Input type="number" min={0} value={d.age ?? ''} onChange={e => updDep(i, 'age', e.target.value === '' ? '' : Number(e.target.value))} /></div>
            <div className="flex items-end"><Button variant="outline" size="sm" className="h-9 w-9 p-0 text-rose-600" onClick={() => removeDep(i)}><Trash2 className="h-3 w-3" /></Button></div>
          </Card>
        ))}
      </Card>

      <Card className="p-6 space-y-3">
        <h2 className="text-lg font-bold flex items-center gap-2"><Sparkles className="h-5 w-5 text-leamss-orange-600" />Preferences & Extras</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-bold">Timeline (months)</Label>
            <Select value={String(data.preferences?.timeline_months || 12)} onValueChange={v => setPref('timeline_months', Number(v))}>
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
            <Label className="text-xs font-bold">Priority</Label>
            <Select value={data.preferences?.priority || ''} onValueChange={v => setPref('priority', v)}>
              <SelectTrigger data-testid="pref-priority"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="speed">Fastest pathway</SelectItem>
                <SelectItem value="cost">Lowest cost</SelectItem>
                <SelectItem value="quality_of_life">Quality of life</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.has_relative_in_target_country} onCheckedChange={v => setField('additional_factors', 'has_relative_in_target_country', v)} data-testid="extra-relative" />
            <Label className="text-xs">Relative in target country (PR/Citizen)</Label>
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.has_job_offer} onCheckedChange={v => setField('additional_factors', 'has_job_offer', v)} data-testid="extra-job-offer" />
            <Label className="text-xs">Have a job offer from target country</Label>
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <Switch checked={!!data.additional_factors?.criminal_record} onCheckedChange={v => setField('additional_factors', 'criminal_record', v)} data-testid="extra-criminal" />
            <Label className="text-xs">Any criminal record / pending case?</Label>
          </div>
        </div>
      </Card>
    </div>
  );
}


function StepReview({ data, countries, onJump, activeSteps }) {
  const modeLabel = SEARCH_MODES.find(m => m.value === data.preferences?.search_mode)?.label || '—';
  const maritalLabel = MARITAL_OPTIONS.find(m => m.v === data.marital_status)?.l || '—';
  const spouseContrib = SPOUSE_CONTRIBUTION_OPTIONS.find(o => o.v === data.spouse?.contribution_type);
  const specificName = countries.find(c => c.country_code === data.preferences?.specific_country)?.country;
  const stepKeyToIndex = (k) => activeSteps.findIndex(s => s.key === k);

  return (
    <Card className="p-6 space-y-4">
      <div className="text-center">
        <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-2" />
        <h2 className="text-xl font-bold">Ready to analyse</h2>
        <p className="text-xs text-slate-500">Verify primary + spouse separation is correct before running AI.</p>
      </div>

      <Card className="p-4 bg-leamss-teal-50 border-leamss-teal-200">
        <p className="text-[10px] uppercase font-bold text-leamss-teal-700 mb-1">Relationship & Strategy</p>
        <p className="text-sm"><strong>{maritalLabel}</strong> · {modeLabel}{data.preferences?.search_mode === 'specific' && specificName && ` · ${specificName}`}</p>
      </Card>

      <ReviewCard label="Primary Applicant" color="indigo" onEdit={() => onJump(stepKeyToIndex('primary_personal'))}>
        <Field label="Name" value={data.name} />
        <Field label="DOB / Age" value={`${data.primary_applicant?.personal?.date_of_birth || '—'}${data.primary_applicant?.personal?.age ? ` (${data.primary_applicant.personal.age})` : ''}`} />
        <Field label="Current Profession" value={data.primary_applicant?.professional?.current_profession} />
        <Field label="Years Experience" value={data.primary_applicant?.professional?.years_experience_total} />
        <Field label="Highest Education" value={QUALIFICATIONS.find(q => q.v === data.primary_applicant?.education?.highest_qualification)?.l} />
        <Field label="Field of Study" value={data.primary_applicant?.education?.field_of_study} />
        <Field label="IELTS Overall" value={data.primary_applicant?.language?.scores?.overall || '—'} />
        <Field label="English Tested" value={data.primary_applicant?.language?.test_completed ? 'Yes' : 'No'} />
      </ReviewCard>

      {isSpouseRequired(data.marital_status) && data.spouse && (
        <ReviewCard label="Spouse" color="purple" onEdit={() => onJump(stepKeyToIndex('spouse'))}>
          <Field label="On Visa?" value={data.spouse.is_applicant_on_visa ? 'Yes' : 'No'} />
          <Field label="Contribution" value={spouseContrib?.l || data.spouse.contribution_type} />
          <Field label="Points Impact" value={spouseContrib?.pts || '0'} />
          <Field label="Spouse Name" value={data.spouse.personal?.full_name} />
          {data.spouse.contribution_type === 'skill_assessment' && (
            <>
              <Field label="Spouse Profession" value={data.spouse.professional?.current_profession} />
              <Field label="Spouse Qualification" value={QUALIFICATIONS.find(q => q.v === data.spouse?.education?.highest_qualification)?.l} />
              <Field label="Spouse IELTS" value={data.spouse.language?.scores?.overall || '—'} />
            </>
          )}
        </ReviewCard>
      )}

      {!isSpouseRequired(data.marital_status) && (
        <Card className="p-3 bg-emerald-50 border border-emerald-200">
          <p className="text-[10px] uppercase font-bold text-emerald-700">Spouse Section</p>
          <p className="text-xs text-emerald-800">Skipped — primary applicant is <strong>{maritalLabel.toLowerCase()}</strong>. Automatic <strong>+10 partner skill points</strong> applied.</p>
        </Card>
      )}

      {(data.dependents || []).length > 0 && (
        <ReviewCard label={`Dependents (${data.dependents.length})`} color="rose" onEdit={() => onJump(stepKeyToIndex('dependents_extras'))}>
          {data.dependents.map((d, i) => (
            <Field key={i} label={d.role} value={`${d.age || '?'} yrs`} />
          ))}
        </ReviewCard>
      )}

      <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        <p className="font-bold mb-1">What happens next?</p>
        <ul className="text-[11px] space-y-0.5 ml-4 list-disc">
          <li>Profile saved with new <strong>Phase 6.7 structure</strong> — primary and spouse tracked separately</li>
          <li>AI analyses <strong>primary applicant</strong> for ANZSCO matching (based on current profession, not past qualification)</li>
          <li>Partner skill points calculated correctly: <strong>{spouseContrib?.pts || (isSpouseRequired(data.marital_status) ? '0' : '+10 (single applicant)')}</strong></li>
        </ul>
      </div>
    </Card>
  );
}


function ReviewCard({ label, color = 'indigo', onEdit, children }) {
  const colorMap = { indigo: 'border-l-leamss-teal-500', purple: 'border-l-leamss-orange-500', rose: 'border-l-rose-500' };
  return (
    <Card className={`p-3 border-l-4 ${colorMap[color] || colorMap.indigo}`}>
      <div className="flex items-center justify-between mb-1">
        <p className={`text-[10px] uppercase font-bold text-${color}-700`}>{label}</p>
        <Button size="sm" variant="ghost" className={`h-6 text-[10px] px-2 text-${color}-600`} onClick={onEdit}>Edit</Button>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">{children}</div>
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
