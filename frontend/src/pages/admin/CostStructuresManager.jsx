/**
 * Phase 4C.2 — Product Cost Structures Manager.
 * Visual editor for allocations + success bonuses + live calculator.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Calculator, Plus, Edit, Copy, Trash2, Sparkles, IndianRupee, Lock, Flag, TrendingUp, Trophy, X } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const COUNTRY_FLAG = { Canada: '🇨🇦', Australia: '🇦🇺', USA: '🇺🇸', UK: '🇬🇧', Germany: '🇩🇪', India: '🇮🇳' };

const StructureEditor = ({ open, onClose, structure, categories, onSaved }) => {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && structure) {
      setForm({
        ...structure,
        cost_allocations: structure.cost_allocations || [],
        success_bonuses: structure.success_bonuses || [],
      });
    } else if (open) {
      setForm({
        product_name: '', country: '', visa_type: '',
        service_price: 100000, government_fees: 0,
        cost_allocations: [],
        success_bonuses: [],
      });
    }
  }, [open, structure]);

  const liveBreakdown = useMemo(() => {
    if (!form) return null;
    const sp = parseFloat(form.service_price) || 0;
    let req = 0, opt = 0;
    const items = (form.cost_allocations || []).map(a => {
      const amt = (a.payment_type === 'percentage') ? sp * (parseFloat(a.amount) || 0) / 100 : (parseFloat(a.amount) || 0);
      if (a.is_optional) opt += amt; else req += amt;
      return { ...a, calc: amt };
    });
    const margin = Math.max(0, sp - req);
    return { items, required: req, optional: opt, margin, margin_pct: sp > 0 ? (margin / sp * 100) : 0 };
  }, [form]);

  if (!form) return null;

  const addAllocation = () => setForm({ ...form, cost_allocations: [...form.cost_allocations, { vendor_category: '', payment_type: 'flat', amount: 0, base: 'service_price', label: '', is_active: true, is_optional: false, auto_assign: true }] });
  const updateAllocation = (i, patch) => setForm({ ...form, cost_allocations: form.cost_allocations.map((a, idx) => idx === i ? { ...a, ...patch } : a) });
  const removeAllocation = (i) => setForm({ ...form, cost_allocations: form.cost_allocations.filter((_, idx) => idx !== i) });

  const addBonus = () => setForm({ ...form, success_bonuses: [...form.success_bonuses, { milestone: 'visa_approved', vendor_category: '', bonus_amount: 0, label: '' }] });
  const updateBonus = (i, patch) => setForm({ ...form, success_bonuses: form.success_bonuses.map((b, idx) => idx === i ? { ...b, ...patch } : b) });
  const removeBonus = (i) => setForm({ ...form, success_bonuses: form.success_bonuses.filter((_, idx) => idx !== i) });

  const handleSave = async () => {
    if (!form.product_name) { toast.error('Product name required'); return; }
    if ((form.service_price || 0) < 0) { toast.error('Service price must be ≥ 0'); return; }
    const invalid = (form.cost_allocations || []).find(a => !a.vendor_category);
    if (invalid) { toast.error('All allocations must have a vendor category'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const payload = {
        ...form,
        service_price: parseFloat(form.service_price) || 0,
        government_fees: parseFloat(form.government_fees) || 0,
        cost_allocations: form.cost_allocations.map(a => ({ ...a, amount: parseFloat(a.amount) || 0 })),
        success_bonuses: form.success_bonuses.map(b => ({ ...b, bonus_amount: parseFloat(b.bonus_amount) || 0 })),
      };
      if (structure?.id) {
        await axios.patch(`${API}/products/cost-structures/${structure.id}`, payload, { headers });
        toast.success('Cost structure updated');
      } else {
        await axios.post(`${API}/products/cost-structures`, payload, { headers });
        toast.success('Cost structure created');
      }
      onSaved();
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[88vh] overflow-y-auto" data-testid="structure-editor">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-leamss-teal-600" />
            {structure?.id ? 'Edit Cost Structure' : 'New Cost Structure'}
            {structure?.is_system && <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[10px] ml-2"><Lock className="h-3 w-3 mr-0.5 inline" />System</Badge>}
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <div><Label className="text-xs font-bold">Product Name *</Label><Input value={form.product_name} onChange={e => setForm({ ...form, product_name: e.target.value })} data-testid="cs-name" /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label className="text-xs font-bold">Country</Label><Input value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} data-testid="cs-country" /></div>
              <div><Label className="text-xs font-bold">Visa Type</Label><Input value={form.visa_type} onChange={e => setForm({ ...form, visa_type: e.target.value })} data-testid="cs-visa-type" /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label className="text-xs font-bold">Service Price (₹)</Label><Input type="number" value={form.service_price} onChange={e => setForm({ ...form, service_price: e.target.value })} data-testid="cs-service-price" /></div>
              <div><Label className="text-xs font-bold">Govt Fees (passthrough)</Label><Input type="number" value={form.government_fees} onChange={e => setForm({ ...form, government_fees: e.target.value })} data-testid="cs-govt-fees" /></div>
            </div>
          </div>

          {/* Live calculator */}
          <Card className="p-3 bg-gradient-to-br from-emerald-50 to-blue-50 border-emerald-200">
            <p className="text-xs font-bold uppercase text-emerald-800 mb-2 flex items-center gap-1"><TrendingUp className="h-3.5 w-3.5" /> Live Margin Preview</p>
            <p className="text-xs text-slate-700">Service Price: <strong>{formatINR(form.service_price)}</strong></p>
            <p className="text-xs text-slate-700">Govt Fees (passthrough): <strong>{formatINR(form.government_fees)}</strong></p>
            <p className="text-xs text-rose-700 mt-1">Required Costs: <strong>−{formatINR(liveBreakdown?.required)}</strong></p>
            <p className="text-xs text-amber-700">Optional Costs: <strong>−{formatINR(liveBreakdown?.optional)}</strong> (if applied)</p>
            <div className="border-t border-emerald-300 mt-2 pt-2">
              <p className="text-sm font-bold text-emerald-700">Margin: {formatINR(liveBreakdown?.margin)} <span className="text-xs">({liveBreakdown?.margin_pct?.toFixed(1)}%)</span></p>
            </div>
          </Card>
        </div>

        {/* Allocations */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-bold text-slate-800 flex items-center gap-1.5"><IndianRupee className="h-4 w-4" />Cost Allocations</h3>
            <Button size="sm" variant="outline" onClick={addAllocation} data-testid="add-allocation"><Plus className="h-3.5 w-3.5 mr-1" />Add</Button>
          </div>
          <div className="space-y-2" data-testid="allocations-list">
            {form.cost_allocations.length === 0 && <p className="text-xs text-slate-400 italic p-3 text-center">No allocations yet</p>}
            {form.cost_allocations.map((a, i) => (
              <Card key={i} className={`p-3 ${a.is_optional ? 'bg-amber-50/50 border-amber-200' : 'bg-slate-50/50 border-slate-200'}`} data-testid={`alloc-${i}`}>
                <div className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-3">
                    <Select value={a.vendor_category} onValueChange={v => updateAllocation(i, { vendor_category: v, label: categories.find(c => c.key === v)?.name || a.label })}>
                      <SelectTrigger className="h-9 text-xs" data-testid={`alloc-cat-${i}`}><SelectValue placeholder="Category" /></SelectTrigger>
                      <SelectContent>{categories.map(c => <SelectItem key={c.key} value={c.key}>{c.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2">
                    <Select value={a.payment_type} onValueChange={v => updateAllocation(i, { payment_type: v })}>
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="flat">Flat ₹</SelectItem>
                        <SelectItem value="percentage">%</SelectItem>
                        <SelectItem value="per_document">/doc</SelectItem>
                        <SelectItem value="hourly">/hr</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2"><Input type="number" value={a.amount} onChange={e => updateAllocation(i, { amount: e.target.value })} className="h-9 text-xs" placeholder="Amount" data-testid={`alloc-amount-${i}`} /></div>
                  <div className="col-span-2"><Input value={a.label || ''} onChange={e => updateAllocation(i, { label: e.target.value })} className="h-9 text-xs" placeholder="Label" /></div>
                  <div className="col-span-2 flex items-center gap-1 text-[11px]">
                    <input type="checkbox" checked={a.is_optional} onChange={e => updateAllocation(i, { is_optional: e.target.checked })} data-testid={`alloc-optional-${i}`} />
                    <span>Optional</span>
                  </div>
                  <div className="col-span-1 text-right">
                    <Button size="sm" variant="ghost" onClick={() => removeAllocation(i)} className="h-8 w-8 p-0 text-rose-600 hover:bg-rose-50"><X className="h-4 w-4" /></Button>
                  </div>
                </div>
                <div className="mt-1 text-[11px] text-slate-600 text-right">= <strong>{formatINR(liveBreakdown?.items[i]?.calc || 0)}</strong></div>
              </Card>
            ))}
          </div>
        </div>

        {/* Success Bonuses */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-bold text-slate-800 flex items-center gap-1.5"><Trophy className="h-4 w-4 text-amber-600" />Success Bonuses (on Visa Approved)</h3>
            <Button size="sm" variant="outline" onClick={addBonus} data-testid="add-bonus"><Plus className="h-3.5 w-3.5 mr-1" />Add</Button>
          </div>
          <div className="space-y-2" data-testid="bonuses-list">
            {form.success_bonuses.length === 0 && <p className="text-xs text-slate-400 italic p-3 text-center">No bonuses yet</p>}
            {form.success_bonuses.map((b, i) => (
              <Card key={i} className="p-3 bg-amber-50/30 border-amber-200" data-testid={`bonus-${i}`}>
                <div className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-3">
                    <Select value={b.vendor_category} onValueChange={v => updateBonus(i, { vendor_category: v })}>
                      <SelectTrigger className="h-9 text-xs" data-testid={`bonus-cat-${i}`}><SelectValue placeholder="Category" /></SelectTrigger>
                      <SelectContent>{categories.map(c => <SelectItem key={c.key} value={c.key}>{c.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-3"><Input type="number" value={b.bonus_amount} onChange={e => updateBonus(i, { bonus_amount: e.target.value })} className="h-9 text-xs" placeholder="Amount (₹)" data-testid={`bonus-amount-${i}`} /></div>
                  <div className="col-span-5"><Input value={b.label || ''} onChange={e => updateBonus(i, { label: e.target.value })} className="h-9 text-xs" placeholder="Label" /></div>
                  <div className="col-span-1 text-right">
                    <Button size="sm" variant="ghost" onClick={() => removeBonus(i)} className="h-8 w-8 p-0 text-rose-600 hover:bg-rose-50"><X className="h-4 w-4" /></Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-cs">{saving ? 'Saving…' : (structure?.id ? 'Update' : 'Create')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


const TestCalculator = ({ structure, onClose }) => {
  const [price, setPrice] = useState(structure?.service_price || 100000);
  const [includeOptional, setIncludeOptional] = useState(true);
  const [includeBonuses, setIncludeBonuses] = useState(true);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/products/cost-structures/${structure.id}/preview`,
        { service_price: parseFloat(price), include_optional: includeOptional, include_bonuses: includeBonuses },
        { headers: { Authorization: `Bearer ${token}` } });
      setResult(r.data);
    } catch (e) { toast.error('Preview failed'); } finally { setLoading(false); }
  };
  useEffect(() => { run(); /* eslint-disable-next-line */ }, []);

  return (
    <Dialog open={!!structure} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl" data-testid="test-calc-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Calculator className="h-5 w-5 text-emerald-600" />Test Calculator — {structure?.product_name}</DialogTitle></DialogHeader>
        <div className="flex items-end gap-2">
          <div className="flex-1"><Label className="text-xs font-bold">Service Price (₹)</Label><Input type="number" value={price} onChange={e => setPrice(e.target.value)} data-testid="calc-price" /></div>
          <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeOptional} onChange={e => setIncludeOptional(e.target.checked)} />Optional</label>
          <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeBonuses} onChange={e => setIncludeBonuses(e.target.checked)} />Bonuses</label>
          <Button onClick={run} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700" data-testid="run-calc">{loading ? '…' : 'Calculate'}</Button>
        </div>
        {result && (
          <div className="mt-3 space-y-2" data-testid="calc-result">
            <div className="bg-slate-50 rounded p-3">
              <p className="text-xs font-bold uppercase text-slate-600 mb-1">Per-Allocation Breakdown</p>
              <table className="w-full text-sm">
                <thead><tr className="border-b text-xs text-slate-500"><th className="text-left pb-1">Label</th><th className="text-right pb-1">Type</th><th className="text-right pb-1">Amount</th></tr></thead>
                <tbody>
                  {result.breakdown.map((b, i) => (
                    <tr key={i} className="border-b last:border-b-0">
                      <td className="py-1">{b.label} {b.is_optional && <span className="text-[10px] text-amber-600">(opt)</span>}</td>
                      <td className="py-1 text-right text-xs text-slate-500">{b.payment_type}</td>
                      <td className="py-1 text-right font-bold">{formatINR(b.calculated_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Card className="p-3 bg-emerald-50 border-emerald-200">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <p>Required: <strong>{formatINR(result.totals.required_costs)}</strong></p>
                <p>Optional: <strong>{formatINR(result.totals.optional_costs)}</strong></p>
                <p>Total Costs: <strong>{formatINR(result.totals.total_costs)}</strong></p>
                <p className="text-emerald-800">Margin: <strong>{formatINR(result.totals.margin)} ({result.totals.margin_percentage}%)</strong></p>
              </div>
              {result.totals.bonus_potential > 0 && <p className="text-xs text-amber-700 mt-2">+{formatINR(result.totals.bonus_potential)} potential bonuses on visa approval</p>}
            </Card>
          </div>
        )}
        <DialogFooter><Button variant="outline" onClick={onClose}>Close</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


export default function CostStructuresManager() {
  const navigate = useNavigate();
  const [structures, setStructures] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [testing, setTesting] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [sRes, cRes] = await Promise.all([
        axios.get(`${API}/products/cost-structures`, { headers }),
        axios.get(`${API}/vendors/categories`, { headers }),
      ]);
      setStructures(sRes.data.structures || []);
      setCategories(cRes.data.categories || []);
    } catch (e) { toast.error('Load failed'); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const clone = async (s) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/products/cost-structures/${s.id}/clone`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Cloned ${s.product_name}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Clone failed'); }
  };

  const remove = async (s) => {
    if (s.is_system) { toast.error('System structures cannot be deleted'); return; }
    if (!window.confirm(`Soft-delete ${s.product_name}?`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/products/cost-structures/${s.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Deleted');
      load();
    } catch (e) { toast.error('Delete failed'); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="cost-structures-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Calculator className="h-7 w-7 text-leamss-teal-600" />Product Cost Structures</h1>
              <p className="text-sm text-slate-500 mt-1">Define how revenue is split among vendors per product</p>
            </div>
          </div>
          <Button onClick={() => setCreating(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="add-cs-btn"><Plus className="h-4 w-4 mr-1.5" />New Cost Structure</Button>
        </div>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="structures-grid">
            {structures.map(s => (
              <Card key={s.id} className="p-5 hover:shadow-lg transition" data-testid={`cs-card-${s.id}`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-slate-800 flex items-center gap-1.5">
                      <span className="text-xl">{COUNTRY_FLAG[s.country] || '🌐'}</span>
                      {s.product_name}
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">{s.country} {s.visa_type && `· ${s.visa_type}`}</p>
                  </div>
                  {s.is_system && <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[10px]"><Lock className="h-3 w-3 mr-0.5 inline" />System</Badge>}
                </div>
                <div className="bg-slate-50 rounded p-2.5 my-3 space-y-1 text-xs">
                  <p className="text-slate-700">Service Price: <strong className="text-slate-900">{formatINR(s.service_price)}</strong></p>
                  <p className="text-slate-700">Govt Fees: <strong>{formatINR(s.government_fees)}</strong></p>
                  <p className="text-rose-700">Typical Costs: <strong>−{formatINR(s.computed?.total_costs_typical || 0)}</strong></p>
                  <p className="text-emerald-700 pt-1 border-t border-slate-200">Margin: <strong>{formatINR(s.computed?.expected_margin || 0)} ({s.computed?.expected_margin_percentage || 0}%)</strong></p>
                </div>
                <div className="text-[11px] text-slate-500 mb-3">
                  <span className="font-bold">{(s.cost_allocations || []).length}</span> allocation{(s.cost_allocations || []).length !== 1 ? 's' : ''} ·
                  <span className="ml-1.5"><Trophy className="h-3 w-3 inline text-amber-500" /> {(s.success_bonuses || []).length} bonus{(s.success_bonuses || []).length !== 1 ? 'es' : ''}</span>
                </div>
                <div className="flex gap-1.5">
                  <Button size="sm" variant="outline" onClick={() => setEditing(s)} className="flex-1" data-testid={`edit-cs-${s.id}`}><Edit className="h-3.5 w-3.5 mr-1" />Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => setTesting(s)} data-testid={`test-cs-${s.id}`}><Calculator className="h-3.5 w-3.5 mr-1" />Test</Button>
                  <Button size="sm" variant="ghost" onClick={() => clone(s)} title="Clone" data-testid={`clone-cs-${s.id}`}><Copy className="h-3.5 w-3.5" /></Button>
                  {!s.is_system && <Button size="sm" variant="ghost" className="text-rose-600" onClick={() => remove(s)} data-testid={`del-cs-${s.id}`}><Trash2 className="h-3.5 w-3.5" /></Button>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <StructureEditor open={creating || !!editing} structure={editing} categories={categories} onClose={() => { setCreating(false); setEditing(null); }} onSaved={load} />
      {testing && <TestCalculator structure={testing} onClose={() => setTesting(null)} />}
    </div>
  );
}
