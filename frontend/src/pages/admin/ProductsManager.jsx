/**
 * Phase 4C UNIFIED — Products Manager (Admin)
 *
 * One screen. One source of truth. Products carry:
 *   - Identity:        name, country, visa_type, category, description
 *   - Pricing:         service_price (base_fee)
 *   - Cost Structure:  cost_allocations[], success_bonuses[]
 *   - Workflow:        workflow_steps[] (existing AI Workflow Builder field)
 *
 * UI: Master list with Product cards → click → split-screen detail with TABS
 *   [Overview] · [Cost & Allocations] · [Success Bonuses] · [Preview Calculator] · [Workflow Steps]
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
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  ArrowLeft, Plus, Search, Package, Sparkles, IndianRupee, Trophy, Calculator,
  Layers, Trash2, Save, Edit, Globe, Briefcase, TrendingUp, AlertCircle, CheckCircle2,
  Workflow as WorkflowIcon
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const VENDOR_CATS = [
  { key: 'sales_commission', label: 'Sales Commission', internal: true, color: 'emerald' },
  { key: 'case_manager',     label: 'Case Manager',     internal: true, color: 'blue' },
  { key: 'tutor',            label: 'Tutor (IELTS/PTE)',           color: 'amber' },
  { key: 'lawyer',           label: 'Lawyer',                       color: 'purple' },
  { key: 'translator',       label: 'Translator',                   color: 'rose' },
  { key: 'consultant',       label: 'Consultant',                   color: 'cyan' },
  { key: 'medical_examiner', label: 'Medical Examiner',             color: 'orange' },
  { key: 'courier',          label: 'Courier',                      color: 'slate' },
  { key: 'other',            label: 'Other',                        color: 'slate' },
];

const catColor = (key) => (VENDOR_CATS.find(c => c.key === key) || {}).color || 'slate';


// ═══════════════════════════════════════════════════════════════════════
// MASTER LIST (left pane)
// ═══════════════════════════════════════════════════════════════════════
function ProductCard({ product, selected, onSelect }) {
  const cs = (product.cost_allocations || []).length;
  const margin = product.computed?.expected_margin || 0;
  const marginPct = product.computed?.expected_margin_pct || 0;
  const hasCost = cs > 0;

  return (
    <button
      onClick={() => onSelect(product)}
      className={`w-full text-left rounded-xl p-4 transition border-2 ${
        selected ? 'border-indigo-500 bg-indigo-50/40 shadow-md' : 'border-slate-200 hover:border-indigo-300 bg-white'
      }`}
      data-testid={`product-card-${product.id}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-slate-800 truncate">{product.name}</h3>
          <div className="flex gap-1 mt-1 flex-wrap">
            {product.country && <Badge className="bg-slate-100 text-slate-600 text-[10px] gap-1"><Globe className="h-2.5 w-2.5" />{product.country}</Badge>}
            {product.visa_type && <Badge className="bg-purple-100 text-purple-700 text-[10px]">{product.visa_type}</Badge>}
            {product.status === 'inactive' && <Badge className="bg-rose-100 text-rose-700 text-[10px]">Inactive</Badge>}
          </div>
        </div>
        {hasCost ? (
          <Badge className="bg-emerald-100 text-emerald-700 text-[10px] shrink-0"><CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />Costed</Badge>
        ) : (
          <Badge className="bg-amber-100 text-amber-700 text-[10px] shrink-0"><AlertCircle className="h-2.5 w-2.5 mr-0.5" />No cost</Badge>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
        <div>
          <p className="text-[9px] uppercase text-slate-400 font-bold">Price</p>
          <p className="font-bold text-slate-800">{formatINR(product.service_price || product.base_fee)}</p>
        </div>
        <div>
          <p className="text-[9px] uppercase text-slate-400 font-bold">Margin</p>
          <p className={`font-bold ${margin > 0 ? 'text-emerald-700' : 'text-slate-400'}`}>{margin ? formatINR(margin) : '—'}</p>
        </div>
        <div>
          <p className="text-[9px] uppercase text-slate-400 font-bold">Margin %</p>
          <p className={`font-bold ${marginPct > 50 ? 'text-emerald-700' : marginPct > 0 ? 'text-amber-700' : 'text-slate-400'}`}>{marginPct ? `${marginPct}%` : '—'}</p>
        </div>
      </div>
    </button>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// EDIT: Cost Allocations tab
// ═══════════════════════════════════════════════════════════════════════
function AllocationsEditor({ product, allocations, onChange }) {
  const total = useMemo(() => {
    const sp = parseFloat(product?.service_price || product?.base_fee || 0);
    return allocations.reduce((acc, a) => {
      if (a.is_optional) return acc;
      if (a.payment_type === 'percentage') return acc + (sp * (parseFloat(a.rate) || 0) / 100);
      return acc + (parseFloat(a.amount) || 0);
    }, 0);
  }, [allocations, product]);

  const addRow = () => {
    onChange([...allocations, {
      vendor_category: 'tutor',
      label: 'New Allocation',
      payment_type: 'flat',
      amount: 0,
      rate: 0,
      is_optional: false,
    }]);
  };
  const updateRow = (i, patch) => {
    const next = [...allocations];
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };
  const removeRow = (i) => {
    onChange(allocations.filter((_, idx) => idx !== i));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2"><Layers className="h-4 w-4 text-indigo-500" />Cost Allocations</h3>
        <Button size="sm" onClick={addRow} variant="outline" data-testid="add-allocation"><Plus className="h-3.5 w-3.5 mr-1" />Add</Button>
      </div>
      {allocations.length === 0 ? (
        <Card className="p-8 text-center bg-slate-50">
          <Layers className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No allocations yet. Add one to define vendor cost splits.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {allocations.map((a, i) => {
            const c = catColor(a.vendor_category);
            return (
              <Card key={i} className={`p-3 border-l-4 border-${c}-400`} data-testid={`alloc-row-${i}`}>
                <div className="grid grid-cols-12 gap-2 items-center">
                  <Input className="col-span-3 h-8" value={a.label || ''} onChange={e => updateRow(i, { label: e.target.value })} placeholder="Label" data-testid={`alloc-label-${i}`} />
                  <Select value={a.vendor_category} onValueChange={v => updateRow(i, { vendor_category: v })}>
                    <SelectTrigger className="col-span-2 h-8 text-xs" data-testid={`alloc-cat-${i}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {VENDOR_CATS.map(c => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Select value={a.payment_type || 'flat'} onValueChange={v => updateRow(i, { payment_type: v })}>
                    <SelectTrigger className="col-span-2 h-8 text-xs" data-testid={`alloc-type-${i}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="flat">Flat ₹</SelectItem>
                      <SelectItem value="percentage">% of price</SelectItem>
                    </SelectContent>
                  </Select>
                  {a.payment_type === 'percentage' ? (
                    <Input type="number" className="col-span-2 h-8" value={a.rate || ''} onChange={e => updateRow(i, { rate: e.target.value })} placeholder="%" data-testid={`alloc-rate-${i}`} />
                  ) : (
                    <Input type="number" className="col-span-2 h-8" value={a.amount || ''} onChange={e => updateRow(i, { amount: e.target.value })} placeholder="₹" data-testid={`alloc-amount-${i}`} />
                  )}
                  <div className="col-span-2 flex items-center gap-1 text-[11px]">
                    <input type="checkbox" checked={!!a.is_optional} onChange={e => updateRow(i, { is_optional: e.target.checked })} data-testid={`alloc-optional-${i}`} />
                    Optional
                  </div>
                  <Button size="sm" variant="ghost" className="col-span-1 text-rose-500 hover:bg-rose-50 h-8" onClick={() => removeRow(i)} data-testid={`alloc-del-${i}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
      <Card className="p-3 bg-gradient-to-br from-indigo-50 to-emerald-50 mt-3">
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-slate-500">Service Price</p>
            <p className="text-base font-bold text-slate-800">{formatINR(product?.service_price || product?.base_fee || 0)}</p>
          </div>
          <div>
            <p className="text-slate-500">Total Cost (non-optional)</p>
            <p className="text-base font-bold text-rose-700">{formatINR(total)}</p>
          </div>
          <div>
            <p className="text-slate-500">Expected Margin</p>
            <p className="text-base font-bold text-emerald-700">{formatINR((parseFloat(product?.service_price || product?.base_fee || 0)) - total)}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// EDIT: Success Bonuses tab
// ═══════════════════════════════════════════════════════════════════════
function BonusesEditor({ bonuses, onChange }) {
  const addRow = () => onChange([...bonuses, { vendor_category: 'tutor', label: 'New Bonus', amount: 0 }]);
  const updateRow = (i, patch) => {
    const next = [...bonuses];
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };
  const removeRow = (i) => onChange(bonuses.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2"><Trophy className="h-4 w-4 text-amber-500" />Success Bonuses</h3>
        <Button size="sm" onClick={addRow} variant="outline" data-testid="add-bonus"><Plus className="h-3.5 w-3.5 mr-1" />Add</Button>
      </div>
      <p className="text-xs text-slate-500 italic">Triggered when admin marks the case as Visa-Approved. One-time additional payout on top of base allocations.</p>
      {bonuses.length === 0 ? (
        <Card className="p-8 text-center bg-slate-50">
          <Trophy className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No success bonuses configured.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {bonuses.map((b, i) => {
            const c = catColor(b.vendor_category);
            return (
              <Card key={i} className={`p-3 border-l-4 border-${c}-400`} data-testid={`bonus-row-${i}`}>
                <div className="grid grid-cols-12 gap-2 items-center">
                  <Input className="col-span-5 h-8" value={b.label || ''} onChange={e => updateRow(i, { label: e.target.value })} placeholder="Label" data-testid={`bonus-label-${i}`} />
                  <Select value={b.vendor_category} onValueChange={v => updateRow(i, { vendor_category: v })}>
                    <SelectTrigger className="col-span-4 h-8 text-xs" data-testid={`bonus-cat-${i}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {VENDOR_CATS.map(c => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Input type="number" className="col-span-2 h-8" value={b.amount || ''} onChange={e => updateRow(i, { amount: e.target.value })} placeholder="₹" data-testid={`bonus-amount-${i}`} />
                  <Button size="sm" variant="ghost" className="col-span-1 text-rose-500 hover:bg-rose-50 h-8" onClick={() => removeRow(i)} data-testid={`bonus-del-${i}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// PREVIEW CALCULATOR tab
// ═══════════════════════════════════════════════════════════════════════
function PreviewCalculator({ product }) {
  const [price, setPrice] = useState(product?.service_price || product?.base_fee || 0);
  const [visa, setVisa] = useState(false);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/products/${product.id}/preview`,
        { service_price: parseFloat(price), visa_approved: visa },
        { headers: { Authorization: `Bearer ${token}` } });
      setResult(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Preview failed'); }
    finally { setBusy(false); }
  };
  useEffect(() => { run(); /* eslint-disable-next-line */ }, [product?.id]);

  return (
    <div className="space-y-4">
      <Card className="p-4 bg-slate-50">
        <h3 className="text-sm font-bold mb-3 flex items-center gap-2"><Calculator className="h-4 w-4 text-indigo-500" />Test Calculator</h3>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label className="text-xs">Hypothetical Sale Price (₹)</Label>
            <Input type="number" value={price} onChange={e => setPrice(e.target.value)} data-testid="calc-price" />
          </div>
          <div className="flex items-end gap-2">
            <label className="flex items-center gap-2 text-sm pb-2">
              <input type="checkbox" checked={visa} onChange={e => setVisa(e.target.checked)} data-testid="calc-visa" />
              <Trophy className="h-3.5 w-3.5 text-amber-500" /> Apply success bonuses
            </label>
          </div>
          <div className="flex items-end">
            <Button onClick={run} disabled={busy} className="w-full bg-indigo-600 hover:bg-indigo-700" data-testid="run-calc"><Calculator className="h-4 w-4 mr-1.5" />Compute</Button>
          </div>
        </div>
      </Card>
      {result && (
        <Card className="p-4" data-testid="calc-result">
          <h4 className="text-sm font-bold mb-3">Allocation Breakdown</h4>
          <div className="space-y-1.5">
            {result.rows.map((r, i) => (
              <div key={i} className={`flex items-center justify-between p-2 rounded ${r.is_optional ? 'bg-slate-50' : 'bg-emerald-50'} text-sm`}>
                <span className="flex items-center gap-2">
                  <Badge className={`bg-${catColor(r.vendor_category)}-100 text-${catColor(r.vendor_category)}-700 text-[10px]`}>{r.vendor_category}</Badge>
                  <strong>{r.label}</strong>
                  {r.is_optional && <span className="text-[10px] text-slate-400">(optional)</span>}
                  {r.bonus_amount > 0 && <span className="text-[10px] text-amber-700">+ {formatINR(r.bonus_amount)} bonus</span>}
                </span>
                <strong className="text-slate-800">{formatINR(r.total_amount)}</strong>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t text-sm">
            <div className="bg-slate-100 rounded p-2 text-center"><p className="text-[10px] uppercase text-slate-500">Revenue</p><p className="font-extrabold text-slate-800">{formatINR(result.service_price)}</p></div>
            <div className="bg-rose-50 rounded p-2 text-center"><p className="text-[10px] uppercase text-rose-700">Total Cost</p><p className="font-extrabold text-rose-700">{formatINR(result.total_cost)}</p></div>
            <div className="bg-emerald-50 rounded p-2 text-center"><p className="text-[10px] uppercase text-emerald-700">Net Margin</p><p className="font-extrabold text-emerald-700">{formatINR(result.margin)} <span className="text-[10px]">({result.margin_pct}%)</span></p></div>
          </div>
        </Card>
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// PRODUCT DETAIL (right pane)
// ═══════════════════════════════════════════════════════════════════════
function ProductDetail({ product, onSaved, onDeleted }) {
  const [form, setForm] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!product) return;
    setForm({
      name: product.name || '',
      description: product.description || '',
      country: product.country || '',
      visa_type: product.visa_type || '',
      category: product.category || 'immigration',
      service_price: product.service_price || product.base_fee || 0,
      status: product.status || 'active',
      cost_allocations: product.cost_allocations || [],
      success_bonuses: product.success_bonuses || [],
    });
    setDirty(false);
    setActiveTab('overview');
  }, [product?.id]);  // eslint-disable-line

  const patch = (p) => { setForm({ ...form, ...p }); setDirty(true); };

  const save = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API}/products/${product.id}`,
        { ...form, service_price: parseFloat(form.service_price) || 0 },
        { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Product saved');
      setDirty(false);
      onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  const remove = async () => {
    if (!window.confirm(`Delete product "${product.name}"? This cannot be undone.`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/products/${product.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Deleted');
      onDeleted();
    } catch (e) { toast.error('Delete failed'); }
  };

  if (!form) return null;

  return (
    <Card className="p-6 h-fit sticky top-6" data-testid="product-detail">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-extrabold text-slate-800 truncate">{form.name}</h2>
          <div className="flex gap-1.5 mt-1">
            {form.country && <Badge className="bg-slate-100 text-slate-700 text-[10px] gap-1"><Globe className="h-2.5 w-2.5" />{form.country}</Badge>}
            {form.visa_type && <Badge className="bg-purple-100 text-purple-700 text-[10px]">{form.visa_type}</Badge>}
            <Badge className={`text-[10px] ${form.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>{form.status}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          {dirty && <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-product"><Save className="h-4 w-4 mr-1" />{saving ? 'Saving…' : 'Save'}</Button>}
          <Button onClick={remove} variant="outline" className="text-rose-600 border-rose-300 hover:bg-rose-50" data-testid="delete-product"><Trash2 className="h-4 w-4" /></Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-4 mb-4">
          <TabsTrigger value="overview" data-testid="tab-overview"><Edit className="h-3.5 w-3.5 mr-1" />Overview</TabsTrigger>
          <TabsTrigger value="cost" data-testid="tab-cost"><Layers className="h-3.5 w-3.5 mr-1" />Cost ({form.cost_allocations.length})</TabsTrigger>
          <TabsTrigger value="bonus" data-testid="tab-bonus"><Trophy className="h-3.5 w-3.5 mr-1" />Bonuses ({form.success_bonuses.length})</TabsTrigger>
          <TabsTrigger value="preview" data-testid="tab-preview"><Calculator className="h-3.5 w-3.5 mr-1" />Calculator</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label className="text-xs font-bold">Product Name *</Label><Input value={form.name} onChange={e => patch({ name: e.target.value })} data-testid="field-name" /></div>
            <div><Label className="text-xs font-bold">Service Price (₹)</Label><Input type="number" value={form.service_price} onChange={e => patch({ service_price: e.target.value })} data-testid="field-price" /></div>
            <div><Label className="text-xs font-bold">Country</Label><Input value={form.country} onChange={e => patch({ country: e.target.value })} placeholder="Canada / Australia / UK..." data-testid="field-country" /></div>
            <div><Label className="text-xs font-bold">Visa Type</Label><Input value={form.visa_type} onChange={e => patch({ visa_type: e.target.value })} placeholder="PR / Student / H1B..." data-testid="field-visa" /></div>
            <div><Label className="text-xs font-bold">Category</Label>
              <Select value={form.category} onValueChange={v => patch({ category: v })}>
                <SelectTrigger data-testid="field-category"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="immigration">Immigration</SelectItem>
                  <SelectItem value="study">Study Abroad</SelectItem>
                  <SelectItem value="work">Work Permit</SelectItem>
                  <SelectItem value="business">Business / Investor</SelectItem>
                  <SelectItem value="travel">Travel / Tourist</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label className="text-xs font-bold">Status</Label>
              <Select value={form.status} onValueChange={v => patch({ status: v })}>
                <SelectTrigger data-testid="field-status"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive (archived)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div><Label className="text-xs font-bold">Description</Label><Textarea value={form.description} onChange={e => patch({ description: e.target.value })} rows={3} data-testid="field-description" /></div>
          {product.computed && (
            <Card className="p-3 bg-gradient-to-br from-indigo-50 to-emerald-50 mt-3">
              <p className="text-[10px] uppercase font-bold text-indigo-700 mb-2 flex items-center gap-1"><TrendingUp className="h-3 w-3" />Computed Economics</p>
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div><p className="text-slate-500">Base Cost</p><p className="font-bold">{formatINR(product.computed.expected_base_cost)}</p></div>
                <div><p className="text-slate-500">Margin</p><p className="font-bold text-emerald-700">{formatINR(product.computed.expected_margin)}</p></div>
                <div><p className="text-slate-500">Margin %</p><p className="font-bold text-emerald-700">{product.computed.expected_margin_pct}%</p></div>
                <div><p className="text-slate-500">Max Bonuses</p><p className="font-bold text-amber-700">{formatINR(product.computed.max_bonus_payout)}</p></div>
              </div>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="cost">
          <AllocationsEditor product={form} allocations={form.cost_allocations} onChange={(arr) => patch({ cost_allocations: arr })} />
        </TabsContent>

        <TabsContent value="bonus">
          <BonusesEditor bonuses={form.success_bonuses} onChange={(arr) => patch({ success_bonuses: arr })} />
        </TabsContent>

        <TabsContent value="preview">
          <PreviewCalculator product={product} />
        </TabsContent>
      </Tabs>

      {(product.workflow_steps || []).length > 0 && (
        <Card className="p-3 mt-4 bg-slate-50 text-xs">
          <p className="font-bold text-slate-700 flex items-center gap-1 mb-1"><WorkflowIcon className="h-3.5 w-3.5" />AI Workflow Steps: {product.workflow_steps.length}</p>
          <p className="text-slate-500">Workflow editing is available in the legacy System → Products tab. To be migrated soon.</p>
        </Card>
      )}
    </Card>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// PAGE
// ═══════════════════════════════════════════════════════════════════════
function NewProductDialog({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', country: '', visa_type: '', service_price: 0, description: '' });
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) setForm({ name: '', country: '', visa_type: '', service_price: 0, description: '' }); }, [open]);

  const save = async () => {
    if (!form.name.trim()) { toast.error('Name required'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/products`,
        { ...form, service_price: parseFloat(form.service_price) || 0, category: 'immigration' },
        { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Product created');
      onCreated(r.data.id);
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="new-product-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Package className="h-5 w-5 text-indigo-600" />New Product</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label className="text-xs font-bold">Product Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g., Canada PR Express Entry" data-testid="new-name" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label className="text-xs font-bold">Country</Label><Input value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} placeholder="Canada" data-testid="new-country" /></div>
            <div><Label className="text-xs font-bold">Visa Type</Label><Input value={form.visa_type} onChange={e => setForm({ ...form, visa_type: e.target.value })} placeholder="PR" data-testid="new-visa" /></div>
          </div>
          <div><Label className="text-xs font-bold">Service Price (₹)</Label><Input type="number" value={form.service_price} onChange={e => setForm({ ...form, service_price: e.target.value })} data-testid="new-price" /></div>
          <div><Label className="text-xs font-bold">Description</Label><Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2} data-testid="new-desc" /></div>
          <p className="text-[11px] text-slate-500 italic">💡 You can configure cost allocations and success bonuses after creation, in the product&apos;s edit screen.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-create">{saving ? 'Creating…' : 'Create Product'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


export default function ProductsManager() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all'); // all, costed, uncosted
  const [newOpen, setNewOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/products`, { headers: { Authorization: `Bearer ${token}` } });
      setProducts(r.data || []);
    } catch (e) { toast.error('Failed to load products'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const selected = useMemo(() => products.find(p => p.id === selectedId) || null, [products, selectedId]);

  const filtered = useMemo(() => {
    let out = products;
    if (search) {
      const s = search.toLowerCase();
      out = out.filter(p => (p.name || '').toLowerCase().includes(s) ||
        (p.country || '').toLowerCase().includes(s) ||
        (p.visa_type || '').toLowerCase().includes(s));
    }
    if (filterStatus === 'costed') out = out.filter(p => (p.cost_allocations || []).length > 0);
    if (filterStatus === 'uncosted') out = out.filter(p => (p.cost_allocations || []).length === 0);
    return out;
  }, [products, search, filterStatus]);

  const counts = useMemo(() => ({
    total: products.length,
    costed: products.filter(p => (p.cost_allocations || []).length > 0).length,
    uncosted: products.filter(p => (p.cost_allocations || []).length === 0).length,
    active: products.filter(p => p.status === 'active').length,
  }), [products]);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="products-manager-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-btn"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Package className="h-7 w-7 text-indigo-600" />Products</h1>
              <p className="text-sm text-slate-500 mt-1">One source of truth — manage product identity, pricing, cost structures, and bonuses in one place.</p>
            </div>
          </div>
          <Button onClick={() => setNewOpen(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-product-btn"><Plus className="h-4 w-4 mr-1.5" />New Product</Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <Card className="p-3 bg-gradient-to-br from-indigo-50 to-indigo-100 border-indigo-300" data-testid="stat-total">
            <p className="text-[10px] uppercase font-bold text-indigo-800">Total Products</p>
            <p className="text-2xl font-extrabold text-indigo-900 mt-0.5">{counts.total}</p>
          </Card>
          <Card className="p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-300" data-testid="stat-active">
            <p className="text-[10px] uppercase font-bold text-emerald-800">Active</p>
            <p className="text-2xl font-extrabold text-emerald-900 mt-0.5">{counts.active}</p>
          </Card>
          <Card className="p-3 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-300" data-testid="stat-costed">
            <p className="text-[10px] uppercase font-bold text-amber-800">With Cost Structure</p>
            <p className="text-2xl font-extrabold text-amber-900 mt-0.5">{counts.costed}</p>
          </Card>
          <Card className="p-3 bg-gradient-to-br from-slate-50 to-slate-100 border-slate-300" data-testid="stat-uncosted">
            <p className="text-[10px] uppercase font-bold text-slate-700">Need Cost Setup</p>
            <p className="text-2xl font-extrabold text-slate-800 mt-0.5">{counts.uncosted}</p>
          </Card>
        </div>

        {/* Filter */}
        <Card className="p-3 mb-4 flex items-center gap-3" data-testid="filter-bar">
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-2.5 top-2.5 text-slate-400" />
            <Input placeholder="Search by name, country, visa type…" value={search} onChange={e => setSearch(e.target.value)} className="pl-8" data-testid="search-input" />
          </div>
          <div className="flex gap-1.5 text-xs">
            {[
              { v: 'all', label: 'All' },
              { v: 'costed', label: 'Costed' },
              { v: 'uncosted', label: 'Need Setup' },
            ].map(b => (
              <button key={b.v} onClick={() => setFilterStatus(b.v)}
                className={`px-3 py-1.5 rounded ${filterStatus === b.v ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                data-testid={`filter-${b.v}`}>{b.label}</button>
            ))}
          </div>
        </Card>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-10 w-10 text-indigo-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading products…</p></Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Master list */}
            <div className="lg:col-span-1 space-y-2.5" data-testid="product-list">
              {filtered.length === 0 ? (
                <Card className="p-8 text-center">
                  <Package className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">No products match your filter.</p>
                </Card>
              ) : (
                filtered.map(p => (
                  <ProductCard key={p.id} product={p} selected={selectedId === p.id} onSelect={() => setSelectedId(p.id)} />
                ))
              )}
            </div>

            {/* Detail */}
            <div className="lg:col-span-2">
              {selected ? (
                <ProductDetail product={selected} onSaved={load} onDeleted={() => { setSelectedId(null); load(); }} />
              ) : (
                <Card className="p-16 text-center" data-testid="no-selection">
                  <Briefcase className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">Select a product on the left to view & edit its details.</p>
                  <p className="text-xs text-slate-400 mt-1">Or click <strong>New Product</strong> at the top right.</p>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
      <NewProductDialog open={newOpen} onClose={() => setNewOpen(false)} onCreated={(id) => { load(); setSelectedId(id); }} />
    </div>
  );
}
