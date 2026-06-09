/**
 * Admin — Visa Pathways Editor
 * Edit the source data that powers BOTH the public Visa Compare tool and the
 * eligibility scoring engine (single source of truth → visa_pathways collection).
 * Fields: requirements (age/education/funds), fees, timeline, competitiveness,
 * job-offer requirement, benefits/drawbacks.
 */
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Save, Loader2, Map, RotateCcw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FLAG = { Canada: '🇨🇦', Australia: '🇦🇺', 'New Zealand': '🇳🇿', 'United Kingdom': '🇬🇧', Germany: '🇩🇪', 'United States': '🇺🇸' };

const Field = ({ label, children, hint }) => (
  <div>
    <label className="text-xs font-medium text-slate-600 block mb-1">{label}</label>
    {children}
    {hint && <p className="text-[11px] text-slate-400 mt-0.5">{hint}</p>}
  </div>
);

export default function VisaPathwaysEditor() {
  const navigate = useNavigate();
  const [list, setList] = useState([]);
  const [active, setActive] = useState(null);   // slug currently editing
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmReseed, setConfirmReseed] = useState(false);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/visa-compare/pathways`);
      setList(r.data.pathways || []);
      if (r.data.pathways?.length) selectPathway(r.data.pathways[0]);
    } catch (e) { toast.error('Failed to load pathways'); }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); }, [load]);

  const selectPathway = (p) => {
    setActive(p.slug);
    setForm({
      ...p,
      key_benefits: (p.key_benefits || []).join('\n'),
      key_drawbacks: (p.key_drawbacks || []).join('\n'),
    });
  };

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        name: form.name, country: form.country, category: form.category,
        min_age: Number(form.min_age), max_age: Number(form.max_age),
        min_education: form.min_education, min_work_exp_years: Number(form.min_work_exp_years),
        language_required: form.language_required, min_funds_inr: Number(form.min_funds_inr),
        govt_fee_inr: Number(form.govt_fee_inr), leamss_fee_inr: Number(form.leamss_fee_inr),
        timeline_months: form.timeline_months,
        competitiveness: Number(form.competitiveness), requires_job_offer: !!form.requires_job_offer,
        post_arrival_jobs: form.post_arrival_jobs, rank: Number(form.rank),
        is_active: form.is_active !== false,
        key_benefits: form.key_benefits.split('\n').map(s => s.trim()).filter(Boolean),
        key_drawbacks: form.key_drawbacks.split('\n').map(s => s.trim()).filter(Boolean),
      };
      await axios.put(`${API}/visa-compare/pathways/${form.slug}`, payload, { headers });
      toast.success(`${form.name} saved — live on /start & scoring`);
      const r = await axios.get(`${API}/visa-compare/pathways`);
      setList(r.data.pathways || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    }
    setSaving(false);
  };

  const reseed = async () => {
    if (!confirmReseed) { setConfirmReseed(true); setTimeout(() => setConfirmReseed(false), 4000); return; }
    setConfirmReseed(false);
    try {
      await axios.post(`${API}/visa-compare/reseed`, {}, { headers });
      toast.success('Reseeded default pathways');
      load();
    } catch (e) { toast.error('Reseed failed'); }
  };

  if (loading || !form) {
    return <div className="flex items-center justify-center h-screen text-slate-500"><Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading…</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="visa-pathways-editor">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn"><ArrowLeft className="h-4 w-4 mr-1.5" /> Admin</Button>
          <div className="flex items-center gap-2">
            <Map className="h-5 w-5 text-emerald-700" />
            <div>
              <h1 className="font-bold text-slate-900 leading-tight">Visa Pathways Editor</h1>
              <p className="text-xs text-slate-500">Powers Visa Compare + eligibility scoring (single source of truth)</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={reseed} data-testid="reseed-btn" className={confirmReseed ? 'border-red-400 text-red-600' : ''}>
            <RotateCcw className="h-4 w-4 mr-1.5" /> {confirmReseed ? 'Click again to reseed' : 'Reseed defaults'}
          </Button>
          <Button size="sm" onClick={save} disabled={saving} className="bg-emerald-700 hover:bg-emerald-800 text-white" data-testid="save-btn">
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <Save className="h-4 w-4 mr-1.5" />} Save
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
        {/* List */}
        <div className="space-y-2" data-testid="pathway-list">
          {list.map(p => (
            <button
              key={p.slug}
              onClick={() => selectPathway(p)}
              className={`w-full text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${active === p.slug ? 'bg-emerald-50 border-emerald-300' : 'bg-white border-slate-200 hover:bg-slate-50'}`}
              data-testid={`pathway-item-${p.slug}`}
            >
              <span className="font-medium text-slate-800">{FLAG[p.country] || ''} {p.name}</span>
              <div className="flex gap-1.5 mt-1">
                <Badge variant="outline" className="text-[10px]">comp {p.competitiveness ?? '—'}</Badge>
                {p.requires_job_offer && <Badge className="text-[10px] bg-amber-100 text-amber-700">needs offer</Badge>}
                {p.is_active === false && <Badge className="text-[10px] bg-slate-200 text-slate-600">hidden</Badge>}
              </div>
            </button>
          ))}
        </div>

        {/* Editor */}
        <Card className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">{FLAG[form.country] || ''} {form.name}</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Active</span>
              <Switch checked={form.is_active !== false} onCheckedChange={(v) => set('is_active', v)} data-testid="toggle-active" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Program Name"><Input value={form.name} onChange={(e) => set('name', e.target.value)} data-testid="f-name" /></Field>
            <Field label="Country"><Input value={form.country} onChange={(e) => set('country', e.target.value)} data-testid="f-country" /></Field>
            <Field label="Category"><Input value={form.category} onChange={(e) => set('category', e.target.value)} /></Field>
            <Field label="Timeline (months)" hint="Free text e.g. 8-14"><Input value={form.timeline_months} onChange={(e) => set('timeline_months', e.target.value)} data-testid="f-timeline" /></Field>
          </div>

          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-2">Eligibility Requirements</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Field label="Min Age"><Input type="number" value={form.min_age} onChange={(e) => set('min_age', e.target.value)} /></Field>
            <Field label="Max Age"><Input type="number" value={form.max_age} onChange={(e) => set('max_age', e.target.value)} data-testid="f-max-age" /></Field>
            <Field label="Min Work Exp (yrs)"><Input type="number" value={form.min_work_exp_years} onChange={(e) => set('min_work_exp_years', e.target.value)} /></Field>
            <Field label="Min Funds (₹)"><Input type="number" value={form.min_funds_inr} onChange={(e) => set('min_funds_inr', e.target.value)} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Min Education"><Input value={form.min_education} onChange={(e) => set('min_education', e.target.value)} /></Field>
            <Field label="Language Required"><Input value={form.language_required} onChange={(e) => set('language_required', e.target.value)} /></Field>
          </div>

          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-2">Scoring Controls</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-end">
            <Field label="Competitiveness (0-100)" hint="Higher = harder to win"><Input type="number" min="0" max="100" value={form.competitiveness ?? 0} onChange={(e) => set('competitiveness', e.target.value)} data-testid="f-competitiveness" /></Field>
            <div className="flex items-center gap-2 pb-2">
              <Switch checked={!!form.requires_job_offer} onCheckedChange={(v) => set('requires_job_offer', v)} data-testid="f-requires-offer" />
              <span className="text-sm text-slate-600">Requires job offer</span>
            </div>
            <Field label="Display Rank"><Input type="number" value={form.rank} onChange={(e) => set('rank', e.target.value)} /></Field>
          </div>

          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-2">Fees</p>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Govt Fee (₹)"><Input type="number" value={form.govt_fee_inr} onChange={(e) => set('govt_fee_inr', e.target.value)} /></Field>
            <Field label="LEAMSS Fee (₹)"><Input type="number" value={form.leamss_fee_inr} onChange={(e) => set('leamss_fee_inr', e.target.value)} /></Field>
          </div>

          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-2">Content (one per line)</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Key Benefits"><Textarea rows={4} value={form.key_benefits} onChange={(e) => set('key_benefits', e.target.value)} data-testid="f-benefits" /></Field>
            <Field label="Key Drawbacks"><Textarea rows={4} value={form.key_drawbacks} onChange={(e) => set('key_drawbacks', e.target.value)} /></Field>
          </div>
          <Field label="Post-Arrival Jobs"><Textarea rows={2} value={form.post_arrival_jobs} onChange={(e) => set('post_arrival_jobs', e.target.value)} /></Field>
        </Card>
      </main>
    </div>
  );
}
