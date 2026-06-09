/**
 * Admin — Eligibility Scoring Rules
 * Controls the transparent, deterministic scoring engine that powers the public
 * /start eligibility quiz. Admins edit factor weights, tier thresholds, the age
 * curve and the experience buffer. Saved to kb_settings (eligibility_scoring_rules).
 */
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Save, RotateCcw, Sliders, Loader2, Info } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FACTOR_HELP = {
  age: 'Younger applicants score higher. Full marks up to the "ideal age", tapering to the pathway age limit.',
  education: "Compared against each pathway's minimum education.",
  experience: 'Full marks above (pathway minimum + buffer years).',
  english: 'IELTS/PTE/CLB parsed and compared to the pathway requirement.',
  job_offer: 'Awarded when the applicant has a job offer abroad.',
  occupation: 'Boost when the occupation matches a verified in-demand list.',
  funds: 'Compared against the settlement funds the pathway expects.',
};

export default function EligibilityScoringRules() {
  const navigate = useNavigate();
  const [rules, setRules] = useState(null);
  const [source, setSource] = useState('defaults');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/eligibility/scoring-rules`, { headers });
      setRules(r.data.rules);
      setSource(r.data.source);
    } catch (e) {
      toast.error('Failed to load scoring rules');
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); }, [load]);

  const setFactorWeight = (key, val) => {
    setRules(prev => ({
      ...prev,
      factors: { ...prev.factors, [key]: { ...prev.factors[key], weight: Number(val) || 0 } },
    }));
  };
  const setTier = (key, val) => setRules(prev => ({ ...prev, tiers: { ...prev.tiers, [key]: Number(val) || 0 } }));
  const setCurve = (key, val) => setRules(prev => ({ ...prev, age_curve: { ...prev.age_curve, [key]: Number(val) || 0 } }));

  const totalWeight = rules ? Object.values(rules.factors).reduce((s, f) => s + (Number(f.weight) || 0), 0) : 0;

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/eligibility/scoring-rules`, {
        factors: rules.factors,
        tiers: rules.tiers,
        age_curve: rules.age_curve,
        experience_buffer_years: rules.experience_buffer_years,
        competitiveness_penalty_max: rules.competitiveness_penalty_max,
        no_offer_penalty: rules.no_offer_penalty,
      }, { headers });
      toast.success('Scoring rules saved — live immediately');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    }
    setSaving(false);
  };

  const [confirmReset, setConfirmReset] = useState(false);

  const reset = async () => {
    if (!confirmReset) { setConfirmReset(true); setTimeout(() => setConfirmReset(false), 4000); return; }
    setConfirmReset(false);
    try {
      await axios.post(`${API}/eligibility/scoring-rules/reset`, {}, { headers });
      toast.success('Reverted to default scoring rules');
      load();
    } catch (e) {
      toast.error('Reset failed');
    }
  };

  if (loading || !rules) {
    return <div className="flex items-center justify-center h-screen text-slate-500"><Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading…</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="eligibility-scoring-rules">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn"><ArrowLeft className="h-4 w-4 mr-1.5" /> Admin</Button>
          <div className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-emerald-700" />
            <div>
              <h1 className="font-bold text-slate-900 leading-tight">Eligibility Scoring Rules</h1>
              <p className="text-xs text-slate-500">Controls the public /start eligibility quiz score</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={source === 'db_override' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}>
            {source === 'db_override' ? '✏️ Custom (DB override)' : '🔒 Default rules'}
          </Badge>
          <Button variant="outline" size="sm" onClick={reset} data-testid="reset-btn" className={confirmReset ? 'border-red-400 text-red-600' : ''}><RotateCcw className="h-4 w-4 mr-1.5" /> {confirmReset ? 'Click again to confirm' : 'Reset'}</Button>
          <Button size="sm" onClick={save} disabled={saving} className="bg-emerald-700 hover:bg-emerald-800 text-white" data-testid="save-btn">
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <Save className="h-4 w-4 mr-1.5" />} Save
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-6">
        <Card className="p-4 bg-blue-50 border-blue-200 flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <p className="text-sm text-blue-900">
            Each factor's <b>weight</b> is the maximum points it contributes. Scores are normalised to 0-100 against the total
            weight, so you don't need them to sum to 100. Pathway requirements (age limit, min education, funds, etc.) come from
            the <b>Visa Compare</b> data — a single source of truth.
          </p>
        </Card>

        {/* Factor weights */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-800">Factor Weights</h3>
            <Badge variant="outline" className="text-xs">Total weight: {totalWeight}</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(rules.factors).map(([key, f]) => (
              <div key={key} className="border border-slate-200 rounded-lg p-3" data-testid={`factor-row-${key}`}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">{f.label || key}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 max-w-xs">{FACTOR_HELP[key]}</p>
                  </div>
                  <Input
                    type="number" min="0" max="100"
                    value={f.weight}
                    onChange={(e) => setFactorWeight(key, e.target.value)}
                    className="w-20 text-center"
                    data-testid={`factor-weight-${key}`}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Tier thresholds */}
        <Card className="p-6">
          <h3 className="font-semibold text-slate-800 mb-1">Tier Thresholds</h3>
          <p className="text-xs text-slate-500 mb-4">Score (0-100) at/above each value gets that tier. Below "Needs work" = Unlikely.</p>
          <div className="grid grid-cols-3 gap-4">
            {[['strong', 'Strong match'], ['moderate', 'Moderate match'], ['weak', 'Needs work']].map(([key, label]) => (
              <div key={key}>
                <label className="text-sm text-slate-600 block mb-1">{label}</label>
                <Input type="number" min="0" max="100" value={rules.tiers[key]} onChange={(e) => setTier(key, e.target.value)} data-testid={`tier-${key}`} />
              </div>
            ))}
          </div>
        </Card>

        {/* Age curve + experience buffer */}
        <Card className="p-6">
          <h3 className="font-semibold text-slate-800 mb-4">Advanced</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm text-slate-600 block mb-1">Ideal age (full marks ≤)</label>
              <Input type="number" min="18" max="60" value={rules.age_curve?.optimal_max ?? 32} onChange={(e) => setCurve('optimal_max', e.target.value)} data-testid="curve-optimal" />
            </div>
            <div>
              <label className="text-sm text-slate-600 block mb-1">Age floor ratio (0-1 at limit)</label>
              <Input type="number" step="0.05" min="0" max="1" value={rules.age_curve?.floor_ratio ?? 0.3} onChange={(e) => setCurve('floor_ratio', e.target.value)} data-testid="curve-floor" />
            </div>
            <div>
              <label className="text-sm text-slate-600 block mb-1">Experience buffer (yrs for full marks)</label>
              <Input type="number" min="0" max="10" value={rules.experience_buffer_years ?? 3} onChange={(e) => setRules(prev => ({ ...prev, experience_buffer_years: Number(e.target.value) || 0 }))} data-testid="exp-buffer" />
            </div>
            <div>
              <label className="text-sm text-slate-600 block mb-1">Max competitiveness penalty (pts)</label>
              <Input type="number" min="0" max="50" value={rules.competitiveness_penalty_max ?? 22} onChange={(e) => setRules(prev => ({ ...prev, competitiveness_penalty_max: Number(e.target.value) || 0 }))} data-testid="comp-penalty" />
              <p className="text-[11px] text-slate-400 mt-1">Deducted for a 100/100 competitiveness pathway (e.g. USA EB2-NIW).</p>
            </div>
            <div>
              <label className="text-sm text-slate-600 block mb-1">No-offer penalty (0-1)</label>
              <Input type="number" step="0.05" min="0" max="1" value={rules.no_offer_penalty ?? 0.5} onChange={(e) => setRules(prev => ({ ...prev, no_offer_penalty: Number(e.target.value) || 0 }))} data-testid="no-offer-penalty" />
              <p className="text-[11px] text-slate-400 mt-1">Score × (1 − this) when a pathway needs a job offer and there is none (UK/Germany).</p>
            </div>
          </div>
        </Card>
      </main>
    </div>
  );
}
