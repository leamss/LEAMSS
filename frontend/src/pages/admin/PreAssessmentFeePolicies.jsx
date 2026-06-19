/**
 * Phase 20.3 — Pre-Assessment Fee Policies admin page.
 *
 * Lists active policies, allows admin CRUD with diff-audit preview.
 * Resolver test panel at top — admin can simulate "what fee will be charged?"
 */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Plus, Edit2, Trash2, RefreshCw, Calculator, X, Save, AlertTriangle, History, CheckCircle2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const COUNTRIES = ['AU', 'CA', 'NZ', 'UK', 'USA', 'IN', 'GLOBAL'];
const VISA_CATEGORIES = ['PR', 'WORK', 'STUDY', 'TOURIST', 'VISITOR', 'BUSINESS', 'INVESTMENT', 'DEPENDENT', 'ANY'];

function DiffPreviewModal({ policyId, diff, onConfirm, onCancel, saving }) {
  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4" data-testid="diff-preview-modal">
      <Card className="w-full max-w-2xl p-5 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2 text-leamss-orange">
              <AlertTriangle className="h-5 w-5" /> Diff-Preview — Fee Change Impact
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Yeh edit save karne se pehle dekh lijiye Sir — kitne active Pre-Assessments affect honge.
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onCancel}><X className="h-4 w-4" /></Button>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-4">
          <Card className="p-3 bg-leamss-teal_50 border border-leamss-teal/30">
            <p className="text-xs text-slate-600">Old Fee</p>
            <p className="text-xl font-bold text-leamss-teal">₹{diff.old_fee?.toLocaleString()}</p>
          </Card>
          <Card className="p-3 bg-leamss-orange_50 border border-leamss-orange/30">
            <p className="text-xs text-slate-600">New Fee</p>
            <p className="text-xl font-bold text-leamss-orange">₹{diff.new_fee?.toLocaleString()}</p>
          </Card>
          <Card className={`p-3 ${diff.fee_delta_inr >= 0 ? 'bg-leamss-orange_50 border-leamss-orange/30' : 'bg-leamss-red_50 border-leamss-red/30'} border`}>
            <p className="text-xs text-slate-600">Delta</p>
            <p className={`text-xl font-bold ${diff.fee_delta_inr >= 0 ? 'text-leamss-orange' : 'text-leamss-red'}`}>
              {diff.fee_delta_inr >= 0 ? '+' : ''}₹{Math.abs(diff.fee_delta_inr).toLocaleString()} ({diff.fee_delta_pct >= 0 ? '+' : ''}{diff.fee_delta_pct}%)
            </p>
          </Card>
        </div>

        <Card className="p-3 mb-3 bg-slate-50">
          <p className="text-xs font-bold text-slate-700 mb-2">
            Affected Pre-Assessments (last {diff.lookback_days} days):
          </p>
          <div className="grid grid-cols-4 gap-2 text-center">
            <div>
              <p className="text-2xl font-bold text-leamss-teal" data-testid="diff-affected-count">{diff.affected_pas_count}</p>
              <p className="text-[10px] text-slate-500">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-leamss-orange" data-testid="diff-unpaid-count">{diff.unpaid_count}</p>
              <p className="text-[10px] text-slate-500">Unpaid (safe)</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-leamss-red" data-testid="diff-paid-count">{diff.paid_count}</p>
              <p className="text-[10px] text-slate-500">Already Paid</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-600">{diff.in_progress_count}</p>
              <p className="text-[10px] text-slate-500">In-Progress</p>
            </div>
          </div>
        </Card>

        {diff.warnings && diff.warnings.length > 0 && (
          <Card className="p-3 mb-3 bg-leamss-red_50 border-leamss-red/30 border">
            <p className="text-xs font-bold text-leamss-red mb-1 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" /> Warnings
            </p>
            <ul className="text-xs text-leamss-red space-y-1">
              {diff.warnings.map((w, i) => <li key={i}>• {w}</li>)}
            </ul>
          </Card>
        )}

        {diff.sample_pas && diff.sample_pas.length > 0 && (
          <Card className="p-3 mb-3 max-h-48 overflow-y-auto">
            <p className="text-xs font-bold text-slate-700 mb-2">Sample PAs (top 5):</p>
            <table className="w-full text-xs">
              <thead className="text-[10px] uppercase text-slate-500">
                <tr><th className="text-left">Client</th><th className="text-left">Stage</th><th className="text-right">Current Fee</th></tr>
              </thead>
              <tbody>
                {diff.sample_pas.map((pa, i) => (
                  <tr key={i} className="border-t">
                    <td className="py-1">{pa.client_name}</td>
                    <td className="py-1"><Badge variant="outline" className="text-[10px]">{pa.stage}</Badge></td>
                    <td className="py-1 text-right font-mono">₹{pa.current_fee?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        <p className="text-[11px] text-slate-500 italic mb-3">
          Note: Save sirf policy ko update karega — existing PAs ke stored fees automatically nahi change honge.
          Existing PAs ko update karne ke liye policy save hone ke baad "Apply Retroactively" button use karein.
        </p>

        <div className="flex justify-end gap-2 pt-3 border-t">
          <Button variant="outline" onClick={onCancel} data-testid="diff-cancel-btn">Cancel</Button>
          <Button onClick={onConfirm} disabled={saving} className="bg-leamss-teal hover:bg-leamss-teal/90" data-testid="diff-confirm-btn">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1" />Confirm & Save Policy
          </Button>
        </div>
      </Card>
    </div>
  );
}


function RetroactiveApplyModal({ policy, onClose, onApplied }) {
  const [reason, setReason] = useState('');
  const [unpaidOnly, setUnpaidOnly] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const apply = async () => {
    if (reason.trim().length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    setSubmitting(true);
    try {
      const r = await axios.post(
        `${API}/pre-assessment-fee-policies/${policy.id}/apply-retroactive`,
        { reason: reason.trim(), affect_unpaid_only: unpaidOnly, lookback_days: 90 },
        auth(),
      );
      toast.success(`Updated ${r.data.updated_count} PAs · revocable 24h · batch ${r.data.batch_id?.slice(0, 16)}…`);
      onApplied();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Apply failed');
    }
    setSubmitting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4" data-testid="retroactive-modal">
      <Card className="w-full max-w-lg p-5">
        <div className="flex justify-between mb-3">
          <h3 className="text-lg font-bold text-leamss-orange flex items-center gap-2">
            <History className="h-5 w-5" />Apply Retroactively
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <Card className="p-3 mb-3 bg-leamss-teal_50">
          <p className="text-xs text-slate-700">
            Policy: <span className="font-bold">{policy.policy_name}</span><br/>
            {policy.country_code} · {policy.visa_category} · <span className="font-bold text-leamss-teal">₹{policy.fee_inr?.toLocaleString()}</span>
          </p>
        </Card>

        <div className="mb-3">
          <Label className="text-xs font-bold mb-1 block">Mode</Label>
          <div className="space-y-2">
            <label className="flex items-start gap-2 text-xs cursor-pointer p-2 border rounded hover:bg-leamss-teal_50">
              <input type="radio" checked={unpaidOnly} onChange={() => setUnpaidOnly(true)} data-testid="retro-mode-unpaid" className="mt-0.5" />
              <span>
                <span className="font-bold text-leamss-teal">Unpaid only (recommended)</span><br/>
                <span className="text-slate-600">Sirf 'new' + 'payment_pending' stage PAs update honge. Safe + non-disruptive.</span>
              </span>
            </label>
            <label className="flex items-start gap-2 text-xs cursor-pointer p-2 border rounded hover:bg-leamss-red_50">
              <input type="radio" checked={!unpaidOnly} onChange={() => setUnpaidOnly(false)} data-testid="retro-mode-all" className="mt-0.5" />
              <span>
                <span className="font-bold text-leamss-red">Force all (dangerous)</span><br/>
                <span className="text-slate-600">Paid PAs bhi update honge — billing reconciliation manually karni padegi.</span>
              </span>
            </label>
          </div>
        </div>

        <div className="mb-3">
          <Label className="text-xs font-bold">Reason (min 10 chars, audit-logged)</Label>
          <textarea
            rows={3}
            className="w-full border rounded p-2 text-sm mt-1"
            value={reason} onChange={e => setReason(e.target.value)}
            placeholder="e.g., Q3 2026 pricing review — aligning AU PR PA fee with new VFS cost"
            data-testid="retro-reason"
          />
          <p className="text-[10px] text-slate-500 mt-1">{reason.length} / 500 chars</p>
        </div>

        <Card className="p-2 mb-3 bg-leamss-orange_50 border-leamss-orange/30">
          <p className="text-[11px] text-leamss-orange flex items-center gap-1">
            <RefreshCw className="h-3 w-3" />Yeh action 24h ke andar revocable hai via Phase 19.6 import_batches.
          </p>
        </Card>

        <div className="flex justify-end gap-2 pt-3 border-t">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={apply} disabled={submitting || reason.trim().length < 10}
            className="bg-leamss-orange hover:bg-leamss-orange/90" data-testid="retro-apply-btn">
            <History className="h-3.5 w-3.5 mr-1" />Apply Now
          </Button>
        </div>
      </Card>
    </div>
  );
}


function PolicyModal({ initial, onClose, onSaved }) {
  const isEdit = !!initial?.id;
  const [form, setForm] = useState({
    country_code: 'AU', visa_category: 'PR', fee_inr: 5100,
    policy_name: '', rationale: '',
    ...(initial || {}),
  });
  const [saving, setSaving] = useState(false);
  const [diff, setDiff] = useState(null);
  const [checking, setChecking] = useState(false);

  const doSave = async () => {
    setSaving(true);
    try {
      if (isEdit) {
        await axios.patch(`${API}/pre-assessment-fee-policies/${initial.id}`, form, auth());
        toast.success('Policy updated');
      } else {
        await axios.post(`${API}/pre-assessment-fee-policies`, form, auth());
        toast.success('Policy created');
      }
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    }
    setSaving(false);
    setDiff(null);
  };

  const save = async () => {
    // Phase 20.3+ Diff-Preview: only when EDITING an existing policy AND fee_inr changed
    if (isEdit && Number(form.fee_inr) !== Number(initial.fee_inr)) {
      setChecking(true);
      try {
        const r = await axios.post(
          `${API}/pre-assessment-fee-policies/${initial.id}/diff-preview`,
          { fee_inr: Number(form.fee_inr), lookback_days: 90 },
          auth(),
        );
        if (r.data.requires_diff_modal && r.data.affected_pas_count >= 1) {
          // Show diff modal — user must confirm
          setDiff(r.data);
          setChecking(false);
          return;
        }
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Diff check failed');
        setChecking(false);
        return;
      }
      setChecking(false);
    }
    // No diff modal needed → save directly
    doSave();
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="fee-policy-modal">
      <Card className="w-full max-w-lg p-5">
        <div className="flex justify-between mb-3">
          <h3 className="text-lg font-bold">{isEdit ? 'Edit Fee Policy' : 'New Fee Policy'}</h3>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-bold">Country Code</Label>
            <Select value={form.country_code} onValueChange={v => setForm({...form, country_code: v})}>
              <SelectTrigger data-testid="modal-country"><SelectValue /></SelectTrigger>
              <SelectContent>
                {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-bold">Visa Category</Label>
            <Select value={form.visa_category} onValueChange={v => setForm({...form, visa_category: v})}>
              <SelectTrigger data-testid="modal-visa-category"><SelectValue /></SelectTrigger>
              <SelectContent>
                {VISA_CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-bold">Fee (₹ INR)</Label>
            <Input type="number" value={form.fee_inr} onChange={e => setForm({...form, fee_inr: Number(e.target.value)})} data-testid="modal-fee" />
          </div>
          <div className="col-span-2">
            <Label className="text-xs font-bold">Policy Name</Label>
            <Input value={form.policy_name} onChange={e => setForm({...form, policy_name: e.target.value})} placeholder="e.g., AU PR Standard 2026" data-testid="modal-policy-name" />
          </div>
          <div className="col-span-2">
            <Label className="text-xs font-bold">Rationale</Label>
            <textarea
              rows={3} className="w-full border rounded p-2 text-sm"
              value={form.rationale} onChange={e => setForm({...form, rationale: e.target.value})}
              placeholder="Admin note explaining why this fee level"
              data-testid="modal-rationale"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4 pt-3 border-t">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving || checking || !form.policy_name} className="bg-leamss-teal hover:bg-leamss-teal/90" data-testid="modal-save-btn">
            {checking ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
            {checking ? 'Checking impact…' : (isEdit ? 'Update' : 'Create')}
          </Button>
        </div>
      </Card>
      {diff && (
        <DiffPreviewModal
          policyId={initial.id}
          diff={diff}
          saving={saving}
          onCancel={() => setDiff(null)}
          onConfirm={doSave}
        />
      )}
    </div>
  );
}

function ResolverTestPanel() {
  const [country, setCountry] = useState('AU');
  const [visa, setVisa] = useState('PR');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const test = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/pre-assessment-fee-policies/resolve?country=${country}&visa_category=${visa}`, auth());
      setResult(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Resolve failed');
    }
    setLoading(false);
  };

  return (
    <Card className="p-4 bg-leamss-orange_50 border border-leamss-orange/30" data-testid="resolver-test-panel">
      <h3 className="text-sm font-bold text-leamss-orange flex items-center gap-2 mb-3">
        <Calculator className="h-4 w-4" /> Resolver Test — "What fee will be charged?"
      </h3>
      <div className="flex flex-wrap gap-2 items-end">
        <div>
          <Label className="text-xs font-bold">Country</Label>
          <Select value={country} onValueChange={setCountry}>
            <SelectTrigger className="w-24" data-testid="resolver-country"><SelectValue /></SelectTrigger>
            <SelectContent>{COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs font-bold">Visa Category</Label>
          <Select value={visa} onValueChange={setVisa}>
            <SelectTrigger className="w-32" data-testid="resolver-visa"><SelectValue /></SelectTrigger>
            <SelectContent>{VISA_CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <Button onClick={test} disabled={loading} className="bg-leamss-orange hover:bg-leamss-orange/90" data-testid="resolver-test-btn">
          {loading ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Calculator className="h-3.5 w-3.5 mr-1" />}
          Resolve
        </Button>
        {result && (
          <div className="ml-auto bg-white rounded p-2 border" data-testid="resolver-result">
            <p className="text-xs text-slate-500">Resolved Fee:</p>
            <p className="text-lg font-bold text-leamss-teal">₹{result.amount?.toLocaleString()}</p>
            <Badge className={`text-[10px] ${result.source === 'country_visa_policy' ? 'bg-leamss-teal' : result.source === 'global_fallback' ? 'bg-leamss-orange' : 'bg-leamss-red'} text-white`}>
              {result.source}
            </Badge>
            {result.policy_name && <p className="text-[10px] text-slate-500 mt-1">{result.policy_name}</p>}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function PreAssessmentFeePolicies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [retroModal, setRetroModal] = useState(null);
  const [includeDeprecated, setIncludeDeprecated] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/pre-assessment-fee-policies?include_deprecated=${includeDeprecated}`, auth());
      setPolicies(r.data.items || []);
    } catch (e) {
      toast.error('Failed to load policies');
    }
    setLoading(false);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [includeDeprecated]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Deprecate policy "${name}"?`)) return;
    try {
      await axios.delete(`${API}/pre-assessment-fee-policies/${id}`, auth());
      toast.success('Policy deprecated');
      load();
    } catch (e) { toast.error('Delete failed'); }
  };

  const handleSeed = async () => {
    if (!window.confirm('Seed 6 initial policies (AU/CA/NZ PR + AU Study + CA Work + GLOBAL fallback)? Idempotent — safe to re-run.')) return;
    try {
      const r = await axios.post(`${API}/pre-assessment-fee-policies/seed`, {}, auth());
      toast.success(`Created ${r.data.count_created} · skipped ${r.data.count_skipped} (already existed)`);
      load();
    } catch (e) { toast.error('Seed failed'); }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4" data-testid="fee-policies-page">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-leamss-teal">Pre-Assessment Fee Policies</h1>
          <p className="text-sm text-slate-600 mt-1">Phase 20.3 · Per country + visa fee policies with 3-tier resolver fallback</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSeed} data-testid="seed-btn">Seed Defaults</Button>
          <Button onClick={() => setModal({})} className="bg-leamss-teal hover:bg-leamss-teal/90" data-testid="fee-policy-create-btn">
            <Plus className="h-4 w-4 mr-1" />New Policy
          </Button>
        </div>
      </header>

      <ResolverTestPanel />

      <Card className="p-3" data-testid="policies-table-card">
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={includeDeprecated} onChange={e => setIncludeDeprecated(e.target.checked)} data-testid="include-deprecated-toggle" />
            Show deprecated
          </label>
          <p className="text-xs text-slate-500">{policies.length} polic{policies.length === 1 ? 'y' : 'ies'}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase text-slate-500 border-b">
              <tr>
                <th className="text-left p-2">Country</th>
                <th className="text-left p-2">Visa</th>
                <th className="text-right p-2">Fee (₹)</th>
                <th className="text-left p-2">Policy Name</th>
                <th className="text-left p-2">Status</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={6} className="p-4 text-center text-slate-500">Loading…</td></tr>}
              {!loading && policies.length === 0 && <tr><td colSpan={6} className="p-4 text-center text-slate-500">No policies. Click "Seed Defaults" to start.</td></tr>}
              {policies.map(p => (
                <tr key={p.id} className="border-b hover:bg-leamss-teal_50" data-testid={`fee-policy-row-${p.id}`}>
                  <td className="p-2 font-mono font-bold">{p.country_code}</td>
                  <td className="p-2"><Badge variant="outline" className="text-leamss-orange border-leamss-orange">{p.visa_category}</Badge></td>
                  <td className="p-2 text-right font-bold text-leamss-teal">₹{p.fee_inr?.toLocaleString()}</td>
                  <td className="p-2 text-xs">{p.policy_name}</td>
                  <td className="p-2">
                    <Badge className={p.status === 'active' ? 'bg-leamss-teal text-white' : 'bg-slate-300 text-slate-700'}>
                      {p.status}
                    </Badge>
                  </td>
                  <td className="p-2 text-right">
                    <Button size="sm" variant="ghost" onClick={() => setModal(p)} data-testid={`fee-policy-edit-${p.id}`}>
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    {p.status === 'active' && (
                      <Button size="sm" variant="ghost" onClick={() => setRetroModal(p)} data-testid={`fee-policy-retro-${p.id}`} title="Apply Retroactively">
                        <History className="h-3.5 w-3.5 text-leamss-orange" />
                      </Button>
                    )}
                    {p.status === 'active' && (
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(p.id, p.policy_name)} data-testid={`fee-policy-archive-${p.id}`}>
                        <Trash2 className="h-3.5 w-3.5 text-leamss-red" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {modal !== null && (
        <PolicyModal initial={modal} onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} />
      )}
      {retroModal !== null && (
        <RetroactiveApplyModal
          policy={retroModal}
          onClose={() => setRetroModal(null)}
          onApplied={() => { setRetroModal(null); load(); }}
        />
      )}
    </div>
  );
}
