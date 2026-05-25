/**
 * Smart Sales Helper — Phase 6 v2 Part 3
 * Integrated Client Assessment Workflow (orchestrator).
 *
 * Route: /sales/client-assessment
 *
 * 7-step linear workflow combining:
 *   • Step 1: New Assessment (client name)              — steps/Step1Start.jsx
 *   • Step 2: Profile Capture Approach                  — steps/Step2Approach.jsx
 *   • Step 3: Profile Form + AI helpers                 — steps/Step3Profile.jsx
 *   • Step 4: Country Selection                         — steps/Step4Countries.jsx
 *   • Step 5: Live Calculator                           — steps/Step5Calculator.jsx
 *   • Step 6: Review & Confirm                          — steps/Step6Review.jsx
 *   • Step 7: Results & Actions + Checklist + Share    — steps/Step7Done.jsx
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2, ChevronLeft, ChevronRight, Save, Sparkles,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';
import { STEPS, API } from './lib/constants';
import { buildProfile, buildTargets, dataFromAssessment } from './lib/buildProfile';

import Step1Start from './steps/Step1Start';
import Step2Approach from './steps/Step2Approach';
import Step3Profile from './steps/Step3Profile';
import Step4Countries from './steps/Step4Countries';
import Step5Calculator from './steps/Step5Calculator';
import Step6CostEstimator from './steps/Step6CostEstimator';
import Step6Review from './steps/Step6Review';
import Step7Done from './steps/Step7Done';


const INITIAL_DATA = {
  client_name: '',
  client_email: '',
  client_phone: '',
  approach: '',
  // Profile
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
  country_mode: 'specific',
  specific_country: 'AU',
  visa_subclass: '189',
  custom_countries: ['AU'],
  // Spouse
  spouse_will_migrate: 'yes',
  spouse_contribution: '',
  spouse_age: '',
  spouse_qualification: '',
  spouse_ielts_overall: '',
  spouse_ielts_listening: '',
  spouse_ielts_reading: '',
  spouse_ielts_writing: '',
  spouse_ielts_speaking: '',
  spouse_profession: '',
  spouse_years_experience: '',
  // AU bonuses — Phase 6.8.4
  australian_study_2_years: false,
  specialist_education_stem_au: false,
  professional_year_completed: false,
  naati_accredited: false,
  regional_study_au: false,
  state_nominated: false,
  state_code: '',
  // CA extras — Phase 6.8.4
  canadian_work_years: '',
  provincial_nomination: false,
  job_offer_noc_00: false,
  job_offer_noc_0_a_b: false,
  canadian_education_3plus_years: false,
  canadian_education_1_2_years: false,
  sibling_in_canada: false,
  french_proficiency_clb_7: false,
  // NZ extras — Phase 6.8.4
  nz_skilled_employment_current: false,
  nz_job_offer: false,
  regional_employment_nz: false,
};

// Phase 6.8.4 — fields that, when changed on Step 5, must trigger live recalc.
const FACTOR_FIELDS = [
  'years_experience_australia', 'canadian_work_years',
  'australian_study_2_years', 'specialist_education_stem_au', 'professional_year_completed',
  'naati_accredited', 'regional_study_au', 'state_nominated', 'state_code',
  'provincial_nomination', 'job_offer_noc_00', 'job_offer_noc_0_a_b',
  'canadian_education_3plus_years', 'canadian_education_1_2_years',
  'sibling_in_canada', 'french_proficiency_clb_7',
  'nz_skilled_employment_current', 'nz_job_offer', 'regional_employment_nz',
];


export default function ClientAssessment() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [step, setStep] = useState(1);
  const [data, setData] = useState(INITIAL_DATA);
  const [calcResults, setCalcResults] = useState([]);
  const [calculating, setCalculating] = useState(false);
  const [saved, setSaved] = useState(null);
  const [creatingPA, setCreatingPA] = useState(false);
  // Phase 6.8.5 — Resume / Continue flow: when set, Save will PUT instead of POST
  const [editingId, setEditingId] = useState(null);

  // Phase 6.8.5 — Hydrate from sessionStorage on first mount.
  // MyAssessments sets `resume_assessment` with the full assessment doc, we
  // inverse-map it and jump straight to Step 5 (Calculator).
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('resume_assessment');
      if (!raw) return;
      const a = JSON.parse(raw);
      sessionStorage.removeItem('resume_assessment');
      if (!a || !a.id) return;
      setData(dataFromAssessment(a, INITIAL_DATA));
      setEditingId(a.id);
      setSaved(a);
      setStep(5);
      toast.success(`Resumed: ${a.client_name || a.id}`);
    } catch (e) {
      console.warn('Resume hydrate failed', e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = (field, val) => setData(d => ({ ...d, [field]: val }));
  const goNext = () => setStep(s => Math.min(8, s + 1));
  const goBack = () => setStep(s => Math.max(1, s - 1));

  // Phase 6.8.4 — Build a stable hash of all factor inputs so the recalc effect
  // also re-runs when Step 5's Additional Factors are toggled.
  const factorHash = useMemo(
    () => FACTOR_FIELDS.map(k => `${k}:${data[k] ?? ''}`).join('|'),
    [data],
  );

  // Run calculation on step 5. Debounced so rapid toggles don't spam the API.
  useEffect(() => {
    if (step !== 5) return;
    setCalculating(true);
    const t = setTimeout(() => {
      axios.post(
        `${API}/sales/calculator/calculate-batch`,
        { profile: buildProfile(data), targets: buildTargets(data) },
        { headers },
      )
        .then(r => setCalcResults(r.data.results || []))
        .catch(e => toast.error(formatApiError(e, 'Calculation failed')))
        .finally(() => setCalculating(false));
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, data.country_mode, data.specific_country, data.visa_subclass, data.custom_countries.join(','), factorHash, headers]);

  const saveAssessment = async () => {
    try {
      const payload = {
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
        targets: buildTargets(data),
      };
      let r;
      if (editingId) {
        // Phase 6.8.5/6.8.6 — already-saved doc → PUT (no duplicate ever).
        r = await axios.put(`${API}/sales/assessments/${editingId}`, payload, { headers });
        const sync = r.data && r.data.pa_sync;
        if (sync && sync.updated) {
          toast.success(
            `Assessment updated · PA ${sync.pa_number || sync.pa_id?.slice(0, 8)} synced (${sync.old_score} → ${sync.new_score})`,
            { duration: 7000 },
          );
        } else {
          toast.success('Assessment updated');
        }
      } else {
        r = await axios.post(`${API}/sales/assessments`, payload, { headers });
        // ─── Phase 6.8.6 Bug Fix #1 ─── lock the id so subsequent Saves in the
        // same wizard session become PUTs (no duplicate SAH-... ids).
        if (r.data?.id) setEditingId(r.data.id);
        toast.success('Assessment saved');
      }
      setSaved(r.data);
      setStep(8);
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    }
  };

  const createPA = async (partnerId = null) => {
    if (!saved || creatingPA) return;
    setCreatingPA(true);
    try {
      const body = {
        target_country_code: saved.best_country_code,
        target_visa_subclass: data.visa_subclass,
        lead_source: 'smart_sales_helper',
      };
      if (partnerId) body.partner_id = partnerId;
      const r = await axios.post(`${API}/sales/assessments/${saved.id}/create-pa`, body, { headers });
      const paId = r.data.pa_id;
      const paNumber = r.data.pa_number;
      const alreadyLinked = r.data.already_linked;
      // Phase 6.8.6 — immediately reflect the link so the Step 7 UI swaps to
      // the "Linked PA" indicator (prevents accidental double-click duplicate).
      setSaved(s => ({ ...s, linked_pa_id: paId, linked_pa_partner_id: r.data.partner_id }));
      // Detect user role to choose the right dashboard for the "Open Dashboard" action
      let dashRoute = '/admin';
      try {
        const me = JSON.parse(localStorage.getItem('user') || '{}');
        const role = me.rbac_role || me.role;
        if (role === 'partner') dashRoute = '/partner';
        else if (role === 'case_manager') dashRoute = '/case-manager';
        else if (['sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head'].includes(role)) dashRoute = '/sales/dashboard';
      } catch { /* ignore */ }
      toast.success(
        alreadyLinked ? `Already linked to ${paNumber || paId}` : `Pre-Assessment created: ${paNumber || paId}`,
        {
          duration: 8000,
          description: r.data.partner_name ? `Assigned to ${r.data.partner_name}. View it in the Pipeline.` : 'View it in your Pre-Assessments Pipeline.',
          action: { label: 'Open Dashboard', onClick: () => navigate(dashRoute) },
        },
      );
    } catch (e) {
      toast.error(formatApiError(e, 'PA creation failed'));
    } finally {
      setCreatingPA(false);
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
              {editingId && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold" data-testid="editing-badge">
                  Editing · {editingId}
                </span>
              )}
            </h1>
            <p className="text-sm text-slate-500">Step-by-step workflow · Finder → Profile → Calculator → Action</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => navigate('/sales/my-assessments')} data-testid="open-my-assessments">My Assessments</Button>
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
          {step === 1 && <Step1Start data={data} update={update} />}
          {step === 2 && <Step2Approach data={data} update={update} />}
          {step === 3 && <Step3Profile data={data} update={update} setData={setData} headers={headers} />}
          {step === 4 && <Step4Countries data={data} update={update} />}
          {step === 5 && <Step5Calculator results={calcResults} calculating={calculating} data={data} update={update} />}
          {step === 6 && <Step6CostEstimator data={data} setData={setData} saved={saved} headers={headers} />}
          {step === 7 && <Step6Review data={data} results={calcResults} />}
          {step === 8 && <Step7Done saved={saved} createPA={createPA} navigate={navigate} headers={headers} creatingPA={creatingPA} />}
        </Card>

        {/* Navigation */}
        {step < 8 && (
          <div className="flex justify-between" data-testid="step-nav">
            <Button variant="outline" onClick={goBack} disabled={step === 1} data-testid="back-btn">
              <ChevronLeft className="h-4 w-4 mr-1" />Back
            </Button>
            {step < 7 ? (
              <Button onClick={goNext} className="bg-indigo-600 hover:bg-indigo-700" disabled={!canAdvance(step, data)} data-testid="next-btn">
                Next<ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            ) : (
              <Button onClick={saveAssessment} className="bg-emerald-600 hover:bg-emerald-700" data-testid="save-assessment-btn">
                <Save className="h-4 w-4 mr-1" />{editingId ? 'Update Assessment' : 'Save Assessment & Continue'}
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
