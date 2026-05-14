/**
 * Phase 4C.4 — Commission Slabs Manager (Admin).
 * CRUD for sales commission tiers. Drives commission calculation when PA → case_created.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Trophy, Plus, Edit, Trash2, Lock, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '∞';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const COLOR_MAP = {
  amber: 'bg-amber-100 text-amber-700 border-amber-300',
  slate: 'bg-slate-100 text-slate-700 border-slate-300',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  emerald: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  indigo: 'bg-indigo-100 text-indigo-700 border-indigo-300',
};


function SlabEditor({ open, slab, onClose, onSaved }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(slab ? { ...slab } : { key: '', name: '', min_revenue: 0, max_revenue: null, rate_pct: 5, color: 'slate' });
  }, [open, slab]);

  if (!form) return null;
  const isEdit = !!slab?.id;

  const handleSave = async () => {
    if (!form.key || !form.name) { toast.error('Key and name required'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        ...(isEdit ? {} : { key: form.key.toLowerCase().replace(/[^a-z_]/g, '_') }),
        name: form.name,
        min_revenue: parseFloat(form.min_revenue) || 0,
        max_revenue: (form.max_revenue === null || form.max_revenue === '' || form.max_revenue === undefined) ? null : parseFloat(form.max_revenue),
        rate_pct: parseFloat(form.rate_pct) || 0,
        color: form.color || 'slate',
      };
      if (isEdit) await axios.patch(`${API}/sales-commission/slabs/${slab.id}`, payload, { headers: { Authorization: `Bearer ${token}` } });
      else await axios.post(`${API}/sales-commission/slabs`, payload, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(isEdit ? 'Slab updated' : 'Slab created');
      onSaved();
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="slab-editor">
        <DialogHeader><DialogTitle>{isEdit ? 'Edit Slab' : 'New Slab'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label className="text-xs font-bold">Slab Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="slab-name" /></div>
          {!isEdit && (
            <div><Label className="text-xs font-bold">Key * (lowercase, e.g., platinum)</Label><Input value={form.key} onChange={e => setForm({ ...form, key: e.target.value })} placeholder="bronze | silver | gold..." data-testid="slab-key" /></div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div><Label className="text-xs font-bold">Min Revenue (₹)</Label><Input type="number" value={form.min_revenue} onChange={e => setForm({ ...form, min_revenue: e.target.value })} data-testid="slab-min" /></div>
            <div><Label className="text-xs font-bold">Max Revenue (₹, leave empty for unlimited)</Label><Input type="number" value={form.max_revenue ?? ''} onChange={e => setForm({ ...form, max_revenue: e.target.value })} data-testid="slab-max" /></div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div><Label className="text-xs font-bold">Rate (%) *</Label><Input type="number" step="0.1" value={form.rate_pct} onChange={e => setForm({ ...form, rate_pct: e.target.value })} data-testid="slab-rate" /></div>
            <div><Label className="text-xs font-bold">Color</Label>
              <select className="w-full h-9 border rounded px-2 text-sm" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} data-testid="slab-color">
                {Object.keys(COLOR_MAP).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className={`p-3 rounded text-xs border ${COLOR_MAP[form.color] || COLOR_MAP.slate}`}>
            <p className="font-bold flex items-center gap-1"><Trophy className="h-3 w-3" />Preview: {form.name || 'New Slab'} ({form.rate_pct}%)</p>
            <p className="mt-1">Applies when revenue is between <strong>{formatINR(form.min_revenue)}</strong> and <strong>{form.max_revenue ? formatINR(form.max_revenue) : '∞'}</strong></p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-slab">{saving ? 'Saving…' : (isEdit ? 'Update' : 'Create')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


export default function CommissionSlabsManager() {
  const navigate = useNavigate();
  const [slabs, setSlabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/sales-commission/slabs`, { headers: { Authorization: `Bearer ${token}` } });
      setSlabs(r.data.slabs || []);
    } catch (e) { toast.error('Failed to load slabs'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const remove = async (s) => {
    if (s.is_system) { toast.error('System slabs cannot be deleted. Deactivate instead.'); return; }
    if (!window.confirm(`Delete slab "${s.name}"?`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/sales-commission/slabs/${s.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Slab deleted');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Delete failed'); }
  };

  const toggleActive = async (s) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`${API}/sales-commission/slabs/${s.id}`, { is_active: !s.is_active }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Slab ${s.is_active ? 'deactivated' : 'activated'}`);
      load();
    } catch (e) { toast.error('Toggle failed'); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="slabs-manager-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Trophy className="h-7 w-7 text-amber-600" />Sales Commission Slabs</h1>
              <p className="text-sm text-slate-500 mt-1">Configure tiered commission rates. Applied automatically when a PA reaches <strong>case_created</strong>.</p>
            </div>
          </div>
          <Button onClick={() => setCreating(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-slab-btn"><Plus className="h-4 w-4 mr-1.5" />New Slab</Button>
        </div>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-indigo-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="slabs-grid">
            {slabs.map(s => (
              <Card key={s.id} className={`p-5 border-2 ${COLOR_MAP[s.color] || COLOR_MAP.slate} ${!s.is_active ? 'opacity-50' : ''}`} data-testid={`slab-card-${s.id}`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-lg flex items-center gap-1"><Trophy className="h-4 w-4" />{s.name}</h3>
                    <p className="text-[10px] uppercase tracking-wider mt-0.5 opacity-70">{s.key}</p>
                  </div>
                  {s.is_system && <Badge className="bg-purple-100 text-purple-700 text-[10px]"><Lock className="h-3 w-3 mr-0.5 inline" />System</Badge>}
                </div>
                <div className="my-3">
                  <p className="text-3xl font-extrabold">{s.rate_pct}%</p>
                  <p className="text-xs opacity-70">commission rate</p>
                </div>
                <div className="bg-white/60 rounded p-2 text-xs space-y-0.5">
                  <p>Min Revenue: <strong>{formatINR(s.min_revenue)}</strong></p>
                  <p>Max Revenue: <strong>{formatINR(s.max_revenue)}</strong></p>
                </div>
                <div className="flex gap-1.5 mt-3">
                  <Button size="sm" variant="outline" onClick={() => setEditing(s)} className="flex-1 bg-white/50" data-testid={`edit-slab-${s.id}`}><Edit className="h-3.5 w-3.5 mr-1" />Edit</Button>
                  <Button size="sm" variant="ghost" onClick={() => toggleActive(s)} className="bg-white/50" data-testid={`toggle-slab-${s.id}`}>{s.is_active ? 'Disable' : 'Enable'}</Button>
                  {s.is_system ? (
                    <Button size="sm" variant="ghost" className="text-slate-400 bg-white/30 cursor-not-allowed" disabled title="System slabs are protected — deactivate instead"><Lock className="h-3.5 w-3.5" /></Button>
                  ) : (
                    <Button size="sm" variant="outline" className="text-rose-600 border-rose-300 hover:bg-rose-50 bg-white" onClick={() => remove(s)} data-testid={`del-slab-${s.id}`} title="Delete this slab"><Trash2 className="h-3.5 w-3.5" /></Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
        <Card className="mt-6 p-4 bg-indigo-50/50 border-indigo-200">
          <p className="text-xs text-indigo-700 leading-relaxed">
            <strong>How it works:</strong> When a sales rep&apos;s pre-assessment reaches the <strong>case_created</strong> stage, the system looks at their cumulative revenue for the current month, matches the slab whose range covers their <em>achieved-after-this-deal</em> revenue, and applies that slab&apos;s rate to this single deal. Each deal is logged as a commission entry which an admin can later approve and mark as paid.
          </p>
        </Card>
      </div>
      <SlabEditor open={creating || !!editing} slab={editing} onClose={() => { setCreating(false); setEditing(null); }} onSaved={load} />
    </div>
  );
}
