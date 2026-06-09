import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, ArrowRight, CheckCircle2, AlertTriangle, Globe, RefreshCw, Share2 } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_COLOR = {
  strong: 'bg-emerald-500',
  moderate: 'bg-blue-500',
  weak: 'bg-amber-500',
  unlikely: 'bg-rose-500',
};
const TIER_TEXT = {
  strong: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  moderate: 'text-blue-700 bg-blue-50 border-blue-200',
  weak: 'text-amber-700 bg-amber-50 border-amber-200',
  unlikely: 'text-rose-700 bg-rose-50 border-rose-200',
};

export default function EligibilityCheck() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1=form, 2=loading, 3=results
  const [form, setForm] = useState({
    full_name: '', email: '', mobile: '', age: 28, education: 'Bachelor',
    work_experience_years: 3, occupation: '', english_score: 'IELTS 6.5',
    family_savings_inr: '', has_job_offer: false,
    spouse_education: '', children_count: 0, preferred_countries: [],
    consent_to_contact: true,
  });
  const [result, setResult] = useState(null);

  const toggleCountry = (c) => {
    const s = new Set(form.preferred_countries);
    s.has(c) ? s.delete(c) : s.add(c);
    setForm({ ...form, preferred_countries: [...s] });
  };

  const submit = async () => {
    if (!form.full_name || !form.occupation) {
      toast.error('Name aur occupation toh dijiye!');
      return;
    }
    setStep(2);
    try {
      const payload = {
        ...form,
        email: form.email?.trim() ? form.email.trim() : null,
        mobile: form.mobile?.trim() ? form.mobile.trim() : null,
        spouse_education: form.spouse_education?.trim() ? form.spouse_education.trim() : null,
        age: parseInt(form.age) || 28,
        work_experience_years: parseFloat(form.work_experience_years) || 0,
        family_savings_inr: form.family_savings_inr ? parseFloat(form.family_savings_inr) : null,
        children_count: parseInt(form.children_count) || 0,
        preferred_countries: form.preferred_countries.length ? form.preferred_countries : null,
      };
      const r = await axios.post(`${API}/eligibility/score`, payload);
      setResult(r.data);
      setStep(3);
    } catch (e) {
      toast.error(formatApiError(e, 'Scoring failed — try again'));
      setStep(1);
    }
  };

  const shareResult = () => {
    if (!result) return;
    const url = `${window.location.origin}/eligibility/result/${result.score_id}`;
    navigator.clipboard.writeText(url);
    toast.success('Shareable link copied!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#2a777a] to-[#1d5658] flex items-center justify-center">
              <Globe className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-bold text-slate-800">LEAMSS Immigration</p>
              <p className="text-[11px] text-slate-500">AI Eligibility Pre-Score</p>
            </div>
          </div>
          <Badge className="bg-amber-100 text-amber-700 border-amber-200 hidden sm:inline-flex">
            <Sparkles className="h-3 w-3 mr-1" /> 90 seconds · 100% free
          </Badge>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {step === 1 && (
          <div className="space-y-6" data-testid="eligibility-form">
            <div className="text-center max-w-2xl mx-auto">
              <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3">
                Check Your Visa Eligibility in 90 Seconds
              </h1>
              <p className="text-slate-600">
                Powered by Claude Sonnet AI — get an honest scorecard across 8 popular pathways.
                <span className="font-semibold text-emerald-700"> No spam, no calls until you ask.</span>
              </p>
            </div>

            <Card className="p-6 sm:p-8 max-w-3xl mx-auto shadow-lg">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Full Name *</label>
                  <Input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="As per passport" data-testid="elig-name" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Email</label>
                  <Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="rahul@example.com" data-testid="elig-email" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">WhatsApp Number</label>
                  <Input value={form.mobile} onChange={e => setForm({ ...form, mobile: e.target.value })} placeholder="+91-XXXXXXXXXX" data-testid="elig-mobile" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Age *</label>
                  <Input type="number" value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} min="18" max="70" data-testid="elig-age" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Highest Education *</label>
                  <select value={form.education} onChange={e => setForm({ ...form, education: e.target.value })}
                    className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm" data-testid="elig-education">
                    <option>Diploma</option>
                    <option>Bachelor</option>
                    <option>Master</option>
                    <option>PhD</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Work Experience (years) *</label>
                  <Input type="number" step="0.5" value={form.work_experience_years} onChange={e => setForm({ ...form, work_experience_years: e.target.value })} min="0" data-testid="elig-experience" />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-sm font-medium text-slate-700 block mb-1">Occupation / Job Title *</label>
                  <Input value={form.occupation} onChange={e => setForm({ ...form, occupation: e.target.value })} placeholder="e.g. Senior Software Engineer / Civil Engineer / Registered Nurse" data-testid="elig-occupation" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">English Test Score</label>
                  <Input value={form.english_score} onChange={e => setForm({ ...form, english_score: e.target.value })} placeholder="IELTS 7.5 / PTE 65 / Not taken" data-testid="elig-english" />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 block mb-1">Available Family Savings (₹)</label>
                  <Input type="number" value={form.family_savings_inr} onChange={e => setForm({ ...form, family_savings_inr: e.target.value })} placeholder="1500000" data-testid="elig-savings" />
                </div>
                <div className="sm:col-span-2">
                  <p className="text-sm font-medium text-slate-700 mb-2">Preferred Countries (optional)</p>
                  <div className="flex gap-2 flex-wrap">
                    {['Canada', 'Australia', 'UK', 'Germany', 'USA', 'New Zealand'].map(c => (
                      <button key={c} type="button" onClick={() => toggleCountry(c)}
                        className={`px-3 py-1 rounded-full text-xs border ${form.preferred_countries.includes(c) ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'}`}
                        data-testid={`elig-country-${c.toLowerCase()}`}>
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="sm:col-span-2 flex items-start gap-2 text-sm text-slate-600 mt-2">
                  <input type="checkbox" checked={form.has_job_offer} onChange={e => setForm({ ...form, has_job_offer: e.target.checked })} className="mt-0.5" data-testid="elig-job-offer" />
                  <span>I already have a job offer in one of the target countries</span>
                </label>
                <label className="sm:col-span-2 flex items-start gap-2 text-sm text-slate-600">
                  <input type="checkbox" checked={form.consent_to_contact} onChange={e => setForm({ ...form, consent_to_contact: e.target.checked })} className="mt-0.5" data-testid="elig-consent" />
                  <span>I'd like a LEAMSS expert to contact me with personalised guidance based on my score (no obligation)</span>
                </label>
              </div>
              <Button onClick={submit} className="w-full mt-6 bg-gradient-to-r from-[#2a777a] to-[#1d5658] hover:from-[#1d5658] hover:to-[#143f41] text-white text-base h-12" data-testid="elig-submit">
                <Sparkles className="h-4 w-4 mr-2" /> Score My Eligibility — Free
              </Button>
            </Card>
          </div>
        )}

        {step === 2 && (
          <div className="text-center py-20" data-testid="eligibility-loading">
            <div className="inline-flex flex-col items-center gap-4">
              <RefreshCw className="h-12 w-12 text-[#2a777a] animate-spin" />
              <p className="text-lg font-semibold text-slate-700">AI scoring your profile across 8 pathways…</p>
              <p className="text-sm text-slate-500">Usually takes 8-15 seconds</p>
            </div>
          </div>
        )}

        {step === 3 && result && (
          <div className="space-y-5" data-testid="eligibility-results">
            <div className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl p-6 shadow-lg">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-emerald-100 text-sm">Your top recommendation</p>
                  <h2 className="text-2xl sm:text-3xl font-bold mt-1">
                    {result.pathways?.[result.top_recommendation]?.score && `${result.pathways[result.top_recommendation].score}% — `}
                    {result.top_recommendation?.replace(/_/g, ' ').toUpperCase()}
                  </h2>
                  <p className="text-emerald-50 text-sm mt-2 max-w-2xl">{result.overall_summary}</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={shareResult} className="bg-white/10 border-white/30 text-white hover:bg-white/20" data-testid="elig-share">
                    <Share2 className="h-4 w-4 mr-1" /> Share
                  </Button>
                </div>
              </div>
              {result.lead_captured && (
                <div className="mt-4 inline-flex items-center gap-2 bg-white/15 rounded-full px-3 py-1 text-xs">
                  <CheckCircle2 className="h-3.5 w-3.5" /> A LEAMSS expert will reach out within 24 hours
                </div>
              )}
            </div>

            <div className="grid sm:grid-cols-2 gap-3">
              {Object.entries(result.pathways || {})
                .sort(([, a], [, b]) => (b.score || 0) - (a.score || 0))
                .map(([slug, p]) => (
                  <Card key={slug} className="p-4 border-l-4" style={{ borderLeftColor: ({strong:'#10b981',moderate:'#3b82f6',weak:'#f59e0b',unlikely:'#f43f5e'}[p.tier]) || '#94a3b8' }} data-testid={`elig-pathway-${slug}`}>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm leading-tight">{slug.replace(/_/g, ' ').toUpperCase()}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">Timeline: {p.estimated_timeline}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-bold text-slate-800">{p.score}<span className="text-sm text-slate-400">%</span></p>
                        <Badge className={`${TIER_TEXT[p.tier] || ''} text-[10px] capitalize`}>{p.tier}</Badge>
                      </div>
                    </div>
                    {/* Score bar */}
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-3">
                      <div className={`h-full ${TIER_COLOR[p.tier] || 'bg-slate-400'}`} style={{ width: `${p.score}%` }}></div>
                    </div>
                    {p.key_strengths?.length > 0 && (
                      <div className="mb-2">
                        <p className="text-[11px] font-semibold text-emerald-700 mb-1">✓ Strengths</p>
                        <ul className="text-[11px] text-slate-600 space-y-0.5 ml-3">
                          {p.key_strengths.map((s, i) => <li key={i} className="list-disc">{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.gaps_to_fix?.length > 0 && (
                      <div className="mb-2">
                        <p className="text-[11px] font-semibold text-amber-700 mb-1">⚠ Gaps to fix</p>
                        <ul className="text-[11px] text-slate-600 space-y-0.5 ml-3">
                          {p.gaps_to_fix.map((s, i) => <li key={i} className="list-disc">{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.notes && <p className="text-[11px] text-slate-500 italic mt-2 pt-2 border-t border-slate-100">{p.notes}</p>}
                  </Card>
                ))}
            </div>

            <Card className="p-5 bg-amber-50 border-amber-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-amber-900 text-sm">Disclaimer</p>
                  <p className="text-[11px] text-amber-700 mt-1">
                    This AI score is an indicative assessment based on the information provided. Final eligibility depends on
                    document verification, language test results, skills assessments, and current immigration policy at the time of application.
                    For a definitive evaluation, book a free 30-min consultation.
                  </p>
                </div>
              </div>
            </Card>

            <div className="flex justify-center gap-3 pt-2">
              <Button variant="outline" onClick={() => { setResult(null); setStep(1); }}>Re-score</Button>
              <Button onClick={() => navigate('/visa-compare')} className="bg-[#2a777a] hover:bg-[#1d5658] text-white" data-testid="elig-compare">
                Compare Top Pathways <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
