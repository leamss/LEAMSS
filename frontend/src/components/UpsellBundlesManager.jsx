import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, Package, Edit, Save, X, IndianRupee } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORIES = [
  { id: 'general', label: 'General' },
  { id: 'processing', label: 'Processing' },
  { id: 'family', label: 'Family' },
  { id: 'document', label: 'Document' },
  { id: 'priority', label: 'Priority' },
];

const EMPTY_FORM = { name: '', amount: '', description: '', category: 'general', is_active: true };

export default function UpsellBundlesManager() {
  const [bundles, setBundles] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [creating, setCreating] = useState(false);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = async () => {
    try {
      const r = await axios.get(`${API}/upsell-bundles`, getAuth());
      setBundles(r.data || []);
    } catch (e) { toast.error('Failed to load bundles'); }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    const payload = {
      name: form.name.trim(),
      amount: parseFloat(form.amount),
      description: form.description,
      category: form.category,
      is_active: form.is_active,
    };
    if (!payload.name || !payload.amount || payload.amount <= 0) {
      toast.error('Name and positive amount required'); return;
    }
    try {
      if (editingId) {
        await axios.put(`${API}/upsell-bundles/${editingId}`, payload, getAuth());
        toast.success('Bundle updated');
      } else {
        await axios.post(`${API}/upsell-bundles`, payload, getAuth());
        toast.success('Bundle created');
      }
      setEditingId(null); setCreating(false); setForm(EMPTY_FORM); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this bundle?')) return;
    try {
      await axios.delete(`${API}/upsell-bundles/${id}`, getAuth());
      toast.success('Bundle deleted'); load();
    } catch (e) { toast.error('Delete failed'); }
  };

  const edit = (b) => {
    setEditingId(b.id); setCreating(false);
    setForm({ name: b.name, amount: String(b.amount), description: b.description || '', category: b.category || 'general', is_active: b.is_active !== false });
  };

  const formCard = (
    <Card className="p-5 border-2 border-dashed border-emerald-300 bg-emerald-50/40" data-testid="bundle-form">
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-semibold text-slate-600 block mb-1">Bundle Name *</label>
          <Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Priority Processing" data-testid="bundle-name" />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 block mb-1">Amount (₹) *</label>
          <Input type="number" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} placeholder="5000" data-testid="bundle-amount" />
        </div>
        <div className="md:col-span-2">
          <label className="text-xs font-semibold text-slate-600 block mb-1">Description</label>
          <Input value={form.description} onChange={e => setForm({...form, description: e.target.value})} placeholder="Brief 1-line description visible to partners" />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 block mb-1">Category</label>
          <select value={form.category} onChange={e => setForm({...form, category: e.target.value})}
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm bg-white">
            {CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm({...form, is_active: e.target.checked})} />
            Active (visible to partners)
          </label>
        </div>
      </div>
      <div className="flex justify-end gap-2 mt-4">
        <Button variant="outline" size="sm" onClick={() => { setEditingId(null); setCreating(false); setForm(EMPTY_FORM); }}>
          <X className="h-4 w-4 mr-1" /> Cancel
        </Button>
        <Button size="sm" onClick={save} className="bg-emerald-600 hover:bg-emerald-700" data-testid="save-bundle">
          <Save className="h-4 w-4 mr-1" /> {editingId ? 'Update' : 'Create'} Bundle
        </Button>
      </div>
    </Card>
  );

  return (
    <div className="space-y-5" data-testid="upsell-bundles-manager">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Package className="h-6 w-6 text-[#f7620b]" /> Upsell Bundles
          </h2>
          <p className="text-sm text-slate-500">Add-on services partners can attach to a proposal to increase deal size.</p>
        </div>
        {!creating && !editingId && (
          <Button onClick={() => { setCreating(true); setForm(EMPTY_FORM); }} className="bg-[#f7620b] hover:bg-[#e55a09]" data-testid="new-bundle-btn">
            <Plus className="h-4 w-4 mr-1" /> New Bundle
          </Button>
        )}
      </div>

      {(creating || editingId) && formCard}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {bundles.map(b => (
          <Card key={b.id} className={`p-4 border ${b.is_active === false ? 'opacity-50 border-slate-200' : 'border-slate-200'}`} data-testid={`bundle-card-${b.id}`}>
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <h3 className="font-bold text-slate-800 leading-snug">{b.name}</h3>
              <Badge variant="outline" className="text-[10px] capitalize shrink-0">{b.category || 'general'}</Badge>
            </div>
            <p className="text-xs text-slate-500 mb-3 min-h-[2.5rem]">{b.description || 'No description'}</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center text-xl font-bold text-emerald-700">
                <IndianRupee className="h-4 w-4" />{(b.amount || 0).toLocaleString('en-IN')}
              </div>
              <div className="flex gap-1">
                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => edit(b)}><Edit className="h-3.5 w-3.5" /></Button>
                <Button size="icon" variant="ghost" className="h-7 w-7 text-red-500 hover:text-red-600" onClick={() => remove(b.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
              </div>
            </div>
          </Card>
        ))}
        {bundles.length === 0 && !creating && (
          <Card className="md:col-span-3 p-8 text-center text-sm text-slate-500">
            No bundles yet. Create your first one.
          </Card>
        )}
      </div>
    </div>
  );
}
