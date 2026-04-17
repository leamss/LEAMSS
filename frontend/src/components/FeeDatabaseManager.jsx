import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Globe, Plus, Edit2, Trash2, Save, X, FileText, Loader2,
  ExternalLink, Calculator, AlertTriangle, Check, Database,
  RefreshCw, Search, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CURRENCIES = ['USD', 'CAD', 'AUD', 'GBP', 'EUR', 'NZD', 'SGD', 'JPY', 'SEK', 'DKK', 'CHF', 'HKD', 'MYR', 'KRW', 'AED', 'INR', 'THB', 'BRL', 'MXN', 'ZAR', 'ARS', 'PLN', 'CZK', 'NOK', 'ILS', 'PHP', 'VND', 'IDR'];

/**
 * FeeDatabaseManager — Admin interface to manage the master fee catalog.
 * Admin can:
 *   - Add/Edit/Delete countries (name, flag emoji, currency)
 *   - Add/Edit/Delete visa categories per country (name, processing days, official URL)
 *   - Add/Edit/Delete individual fee line items (label, amount, mandatory, per_applicant, notes)
 */
export default function FeeDatabaseManager({ token }) {
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null); // { country_id, category }
  const [countryDialog, setCountryDialog] = useState({ open: false, mode: 'create', data: null });
  const [reseeding, setReseeding] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/fee-calculator/admin/catalog`, { headers });
      setCatalog(r.data.countries || []);
      // refresh selected if exists
      if (selectedCountry) {
        const next = r.data.countries.find(c => c.id === selectedCountry.id);
        setSelectedCountry(next || null);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const filtered = catalog.filter(c => {
    if (!search) return true;
    return c.name.toLowerCase().includes(search.toLowerCase())
        || (c.currency || '').toLowerCase().includes(search.toLowerCase());
  });

  const handleCountrySave = async (data) => {
    try {
      if (countryDialog.mode === 'create') {
        await axios.post(`${API}/fee-calculator/admin/countries`, data, { headers });
        toast.success('Country added');
      } else {
        await axios.put(`${API}/fee-calculator/admin/countries/${data.id}`, data, { headers });
        toast.success('Country updated');
      }
      setCountryDialog({ open: false, mode: 'create', data: null });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    }
  };

  const handleDeleteCountry = async (c) => {
    if (!window.confirm(`Delete "${c.name}" and all its visa categories? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/fee-calculator/admin/countries/${c.id}`, { headers });
      toast.success('Country deleted');
      if (selectedCountry?.id === c.id) setSelectedCountry(null);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Delete failed');
    }
  };

  const handleDeleteCategory = async (countryId, catId, catName) => {
    if (!window.confirm(`Delete visa category "${catName}"?`)) return;
    try {
      await axios.delete(`${API}/fee-calculator/admin/countries/${countryId}/categories/${catId}`, { headers });
      toast.success('Category deleted');
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Delete failed');
    }
  };

  const handleReseed = async () => {
    if (!window.confirm('Reseed will WIPE all manual changes and restore built-in data. Continue?')) return;
    setReseeding(true);
    try {
      await axios.post(`${API}/fee-calculator/admin/reseed`, {}, { headers });
      toast.success('Catalog reseeded from built-in data');
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Reseed failed');
    } finally {
      setReseeding(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="fee-db-manager">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <div className="p-2 bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] rounded-lg text-white">
              <Database className="h-4 w-4" />
            </div>
            Fee Database Manager
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Master catalog of countries, visa categories & government fees — used by all portals
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleReseed} disabled={reseeding} data-testid="fdb-reseed">
            {reseeding ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
            Reseed from defaults
          </Button>
          <Button size="sm" className="bg-[#f7620b] hover:bg-[#e55a09]"
            onClick={() => setCountryDialog({ open: true, mode: 'create', data: { name: '', flag: '', currency: 'USD', categories: [] } })}
            data-testid="fdb-add-country">
            <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Country
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-4 gap-4">
        {/* Countries list */}
        <Card className="lg:col-span-1 p-3 bg-white border-slate-200">
          <div className="relative mb-2">
            <Search className="h-4 w-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <Input placeholder="Search country…" value={search} onChange={e => setSearch(e.target.value)}
              className="pl-8 h-9" data-testid="fdb-search" />
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-[#2a777a]" /></div>
          ) : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {filtered.map(c => (
                <button key={c.id}
                  onClick={() => setSelectedCountry(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-lg flex items-center gap-2 text-sm transition-colors ${selectedCountry?.id === c.id ? 'bg-[#2a777a]/10 border border-[#2a777a]/30 text-[#2a777a] font-semibold' : 'hover:bg-slate-50 text-slate-700'}`}
                  data-testid={`fdb-country-${c.id}`}>
                  <span className="text-xl leading-none">{c.flag}</span>
                  <span className="flex-1 min-w-0 truncate">{c.name}</span>
                  <Badge variant="outline" className="text-[10px] h-4 px-1.5">{c.categories?.length || 0}</Badge>
                  <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
                </button>
              ))}
              {filtered.length === 0 && <p className="text-xs text-slate-400 text-center py-4">No matches</p>}
            </div>
          )}
        </Card>

        {/* Right panel */}
        <div className="lg:col-span-3 space-y-4">
          {!selectedCountry ? (
            <Card className="p-12 text-center bg-white border-slate-200 border-dashed">
              <Globe className="h-12 w-12 text-slate-200 mx-auto mb-3" />
              <p className="text-slate-500">Select a country from the left to view & edit its visa categories</p>
            </Card>
          ) : (
            <>
              <Card className="p-4 bg-white border-slate-200">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{selectedCountry.flag}</span>
                    <div>
                      <h3 className="text-lg font-bold text-slate-800">{selectedCountry.name}</h3>
                      <p className="text-xs text-slate-500">
                        Currency: <span className="font-medium">{selectedCountry.currency}</span> ·
                        {' '}{selectedCountry.categories?.length || 0} visa categories ·
                        {' '}<span className="text-slate-400">id: {selectedCountry.id}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm"
                      onClick={() => setCountryDialog({ open: true, mode: 'edit', data: { ...selectedCountry } })}
                      data-testid="fdb-edit-country">
                      <Edit2 className="h-3.5 w-3.5 mr-1.5" /> Edit Meta
                    </Button>
                    <Button variant="outline" size="sm" className="border-red-200 text-red-600 hover:bg-red-50"
                      onClick={() => handleDeleteCountry(selectedCountry)} data-testid="fdb-delete-country">
                      <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete
                    </Button>
                    <Button size="sm" className="bg-[#2a777a] hover:bg-[#236466]"
                      onClick={() => setEditingCategory({ country_id: selectedCountry.id, category: { name: '', processing_days: '', official_url: '', fees: [] }, mode: 'create' })}
                      data-testid="fdb-add-category">
                      <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Category
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Categories */}
              <div className="space-y-3">
                {(selectedCountry.categories || []).map(cat => (
                  <Card key={cat.id} className="p-4 bg-white border-slate-200" data-testid={`fdb-cat-${cat.id}`}>
                    <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-bold text-slate-800 flex items-center gap-2 flex-wrap">
                          <FileText className="h-4 w-4 text-[#2a777a]" />
                          {cat.name}
                          {cat.processing_days && (
                            <Badge variant="outline" className="text-xs">{cat.processing_days} days</Badge>
                          )}
                        </h4>
                        {cat.official_url && (
                          <a href={cat.official_url} target="_blank" rel="noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-[#2a777a] hover:underline mt-1">
                            <ExternalLink className="h-3 w-3" /> Official source
                          </a>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="h-8"
                          onClick={() => setEditingCategory({ country_id: selectedCountry.id, category: { ...cat }, mode: 'edit' })}
                          data-testid={`fdb-edit-cat-${cat.id}`}>
                          <Edit2 className="h-3.5 w-3.5 mr-1" /> Edit
                        </Button>
                        <Button variant="ghost" size="sm" className="h-8 text-red-600 hover:bg-red-50"
                          onClick={() => handleDeleteCategory(selectedCountry.id, cat.id, cat.name)}
                          data-testid={`fdb-del-cat-${cat.id}`}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                    <div className="text-xs text-slate-500 mt-2 grid grid-cols-2 md:grid-cols-3 gap-1">
                      {(cat.fees || []).map(f => (
                        <div key={f.id} className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-50 border border-slate-100">
                          {f.mandatory ? <Check className="h-3 w-3 text-emerald-500 shrink-0" /> : <span className="text-amber-500 shrink-0">○</span>}
                          <span className="truncate flex-1">{f.label}</span>
                          <span className="font-semibold whitespace-nowrap">{f.amount.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-400 mt-2">{(cat.fees || []).length} fee line items</p>
                  </Card>
                ))}
                {(selectedCountry.categories || []).length === 0 && (
                  <Card className="p-8 text-center bg-white border-slate-200 border-dashed">
                    <AlertTriangle className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">No visa categories. Click "Add Category" to start.</p>
                  </Card>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Country Dialog */}
      <CountryDialog
        open={countryDialog.open}
        mode={countryDialog.mode}
        initial={countryDialog.data}
        onClose={() => setCountryDialog({ open: false, mode: 'create', data: null })}
        onSave={handleCountrySave}
      />

      {/* Category Editor */}
      <CategoryEditor
        state={editingCategory}
        token={token}
        onClose={() => setEditingCategory(null)}
        onSaved={() => { setEditingCategory(null); load(); }}
      />
    </div>
  );
}

/* --------- Country dialog (add / edit meta) --------- */
function CountryDialog({ open, mode, initial, onClose, onSave }) {
  const [form, setForm] = useState({ id: '', name: '', flag: '', currency: 'USD' });

  useEffect(() => {
    if (initial) setForm({ id: initial.id || '', name: initial.name || '', flag: initial.flag || '', currency: initial.currency || 'USD' });
  }, [initial]);

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="fdb-country-dialog">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'Add Country' : 'Edit Country'}</DialogTitle>
          <DialogDescription>Manage country metadata (ID cannot be changed once created).</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs font-semibold">Name *</Label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="e.g., Argentina" data-testid="fdb-ctr-name" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Flag Emoji</Label>
              <Input value={form.flag} onChange={e => setForm({ ...form, flag: e.target.value })}
                placeholder="🇦🇷" maxLength={4} data-testid="fdb-ctr-flag" />
            </div>
            <div>
              <Label className="text-xs font-semibold">Currency Code *</Label>
              <Select value={form.currency} onValueChange={v => setForm({ ...form, currency: v })}>
                <SelectTrigger data-testid="fdb-ctr-currency"><SelectValue /></SelectTrigger>
                <SelectContent className="max-h-64">
                  {CURRENCIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          {mode === 'create' && (
            <p className="text-xs text-slate-400">
              ID will be auto-generated from name (e.g., "United Arab Emirates" → "united_arab_emirates")
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button className="bg-[#2a777a] hover:bg-[#236466]"
            disabled={!form.name.trim() || !form.currency}
            onClick={() => onSave({ ...form, categories: initial?.categories || [] })}
            data-testid="fdb-ctr-save">
            <Save className="h-3.5 w-3.5 mr-1.5" /> {mode === 'create' ? 'Add Country' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* --------- Category editor (add / edit with fees) --------- */
function CategoryEditor({ state, token, onClose, onSaved }) {
  const [cat, setCat] = useState({ name: '', processing_days: '', official_url: '', fees: [] });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (state) {
      setCat({
        name: state.category.name || '',
        processing_days: state.category.processing_days || '',
        official_url: state.category.official_url || '',
        fees: (state.category.fees || []).map(f => ({ ...f })),
      });
    }
  }, [state]);

  if (!state) return null;

  const addFee = () => {
    setCat({ ...cat, fees: [...cat.fees, { label: '', amount: 0, mandatory: true, per_applicant: true, notes: '' }] });
  };
  const updateFee = (idx, patch) => {
    const next = cat.fees.map((f, i) => i === idx ? { ...f, ...patch } : f);
    setCat({ ...cat, fees: next });
  };
  const removeFee = (idx) => {
    setCat({ ...cat, fees: cat.fees.filter((_, i) => i !== idx) });
  };

  const save = async () => {
    if (!cat.name.trim()) { toast.error('Category name required'); return; }
    setSaving(true);
    try {
      const payload = {
        name: cat.name,
        processing_days: cat.processing_days,
        official_url: cat.official_url,
        fees: cat.fees.map((f, i) => ({
          label: f.label,
          amount: Number(f.amount) || 0,
          mandatory: !!f.mandatory,
          per_applicant: !!f.per_applicant,
          notes: f.notes || '',
          order: i,
        })),
      };
      if (state.mode === 'create') {
        await axios.post(`${API}/fee-calculator/admin/countries/${state.country_id}/categories`, payload,
          { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Category added');
      } else {
        await axios.put(`${API}/fee-calculator/admin/countries/${state.country_id}/categories/${state.category.id}`, payload,
          { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Category updated');
      }
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!state} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="fdb-cat-editor">
        <DialogHeader>
          <DialogTitle>{state.mode === 'create' ? 'Add Visa Category' : 'Edit Visa Category'}</DialogTitle>
          <DialogDescription>Define visa category details and individual fee line items.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label className="text-xs font-semibold">Category Name *</Label>
              <Input value={cat.name} onChange={e => setCat({ ...cat, name: e.target.value })}
                placeholder="e.g., Subclass 189 — Skilled Independent" data-testid="fdb-cat-name" />
            </div>
            <div>
              <Label className="text-xs font-semibold">Processing Time</Label>
              <Input value={cat.processing_days} onChange={e => setCat({ ...cat, processing_days: e.target.value })}
                placeholder="e.g., 180-540" data-testid="fdb-cat-days" />
            </div>
            <div>
              <Label className="text-xs font-semibold">Official URL</Label>
              <Input value={cat.official_url} onChange={e => setCat({ ...cat, official_url: e.target.value })}
                placeholder="https://…" data-testid="fdb-cat-url" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-sm font-semibold">Fee Line Items ({cat.fees.length})</Label>
              <Button variant="outline" size="sm" onClick={addFee} data-testid="fdb-fee-add">
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Fee
              </Button>
            </div>

            <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
              {cat.fees.map((f, idx) => (
                <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2" data-testid={`fdb-fee-row-${idx}`}>
                  <div className="flex items-start gap-2">
                    <div className="flex-1">
                      <Input value={f.label} onChange={e => updateFee(idx, { label: e.target.value })}
                        placeholder="Fee label (e.g., Application Processing Fee)" className="mb-2"
                        data-testid={`fdb-fee-label-${idx}`} />
                      <div className="grid grid-cols-12 gap-2 items-end">
                        <div className="col-span-3">
                          <Label className="text-[10px] text-slate-500">Amount (native)</Label>
                          <Input type="number" min={0} step="0.01" value={f.amount}
                            onChange={e => updateFee(idx, { amount: e.target.value })}
                            data-testid={`fdb-fee-amount-${idx}`} />
                        </div>
                        <label className="col-span-3 flex items-center gap-1.5 text-xs text-slate-700 pt-5">
                          <Checkbox checked={f.mandatory} onCheckedChange={v => updateFee(idx, { mandatory: v })}
                            data-testid={`fdb-fee-mand-${idx}`} />
                          Mandatory
                        </label>
                        <label className="col-span-3 flex items-center gap-1.5 text-xs text-slate-700 pt-5">
                          <Checkbox checked={f.per_applicant} onCheckedChange={v => updateFee(idx, { per_applicant: v })}
                            data-testid={`fdb-fee-ppl-${idx}`} />
                          Per applicant
                        </label>
                        <div className="col-span-3 pt-5 flex justify-end">
                          <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-50 h-8"
                            onClick={() => removeFee(idx)} data-testid={`fdb-fee-del-${idx}`}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                      <Textarea value={f.notes || ''} onChange={e => updateFee(idx, { notes: e.target.value })}
                        placeholder="Optional notes (e.g., 'Per country resided')" rows={1}
                        className="mt-2 resize-none" data-testid={`fdb-fee-notes-${idx}`} />
                    </div>
                  </div>
                </div>
              ))}
              {cat.fees.length === 0 && (
                <p className="text-center text-sm text-slate-400 py-6">No fees yet. Click "Add Fee" above.</p>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}><X className="h-3.5 w-3.5 mr-1.5" /> Cancel</Button>
          <Button className="bg-[#2a777a] hover:bg-[#236466]" onClick={save} disabled={saving} data-testid="fdb-cat-save">
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Save className="h-3.5 w-3.5 mr-1.5" />}
            {state.mode === 'create' ? 'Add Category' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
