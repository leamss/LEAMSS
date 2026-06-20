/**
 * Phase 4C.1 — Vendor Categories Manager.
 * View 9 seeded categories. Admin can add/edit custom ones.
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
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Layers, Plus, Edit, Lock, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CategoryModal = ({ open, onClose, editing, onSaved }) => {
  const [form, setForm] = useState({ key: '', name: '', description: '', default_payment_type: 'flat', is_internal: false, linked_role: '' });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) {
      if (editing) setForm({ ...editing, linked_role: editing.linked_role || '' });
      else setForm({ key: '', name: '', description: '', default_payment_type: 'flat', is_internal: false, linked_role: '' });
    }
  }, [open, editing]);

  const save = async () => {
    if (!editing && !form.key) { toast.error('Key required (e.g., my_vendor)'); return; }
    if (!form.name) { toast.error('Name required'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const payload = { ...form, linked_role: form.linked_role || null };
      if (editing) await axios.patch(`${API}/vendors/categories/${editing.key}`, payload, { headers });
      else await axios.post(`${API}/vendors/categories`, payload, { headers });
      toast.success(editing ? 'Category updated' : 'Category created');
      onSaved();
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="category-modal">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Layers className="h-5 w-5 text-leamss-teal-600" />{editing ? 'Edit Category' : 'New Category'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label className="text-sm font-bold">Key (lowercase_snake) *</Label><Input value={form.key} onChange={e => setForm({ ...form, key: e.target.value.toLowerCase().replace(/[^a-z_]/g, '') })} disabled={!!editing} data-testid="cat-key" /></div>
          <div><Label className="text-sm font-bold">Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="cat-name" /></div>
          <div><Label className="text-sm font-bold">Description</Label><Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2} data-testid="cat-desc" /></div>
          <div>
            <Label className="text-sm font-bold">Default Payment Type</Label>
            <Select value={form.default_payment_type} onValueChange={v => setForm({ ...form, default_payment_type: v })}>
              <SelectTrigger data-testid="cat-payment-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="flat">Flat</SelectItem>
                <SelectItem value="percentage">Percentage</SelectItem>
                <SelectItem value="hourly">Hourly</SelectItem>
                <SelectItem value="per_document">Per Document</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_internal} onChange={e => setForm({ ...form, is_internal: e.target.checked })} data-testid="cat-internal" /> <span>Internal (linked to user role)</span></div>
          {form.is_internal && <div><Label className="text-sm font-bold">Linked Role</Label><Input value={form.linked_role} onChange={e => setForm({ ...form, linked_role: e.target.value })} placeholder="case_manager / sales_executive / …" data-testid="cat-linked-role" /></div>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-category">{saving ? 'Saving…' : 'Save'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default function VendorCategoriesManager() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/vendors/categories`, { headers: { Authorization: `Bearer ${token}` } });
      setItems(r.data.categories || []);
    } catch (e) { toast.error('Load failed'); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="vendor-categories-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin/vendors')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-vendors"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Layers className="h-7 w-7 text-leamss-teal-600" />Vendor Categories</h1>
              <p className="text-sm text-slate-500 mt-1">Define the types of vendors your CRM works with</p>
            </div>
          </div>
          <Button onClick={() => setCreating(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="new-category-btn"><Plus className="h-4 w-4 mr-1.5" />New Category</Button>
        </div>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="categories-grid">
            {items.map(c => (
              <Card key={c.key} className="p-5 hover:shadow-md transition" data-testid={`cat-card-${c.key}`}>
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-slate-800">{c.name}</h3>
                  <div className="flex gap-1">
                    {c.is_system && <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[10px]"><Lock className="h-3 w-3 mr-0.5 inline" />System</Badge>}
                    {c.is_internal ? <Badge className="bg-leamss-red-100 text-leamss-red-700 text-[10px]">Internal</Badge> : <Badge className="bg-cyan-100 text-cyan-700 text-[10px]">External</Badge>}
                  </div>
                </div>
                <p className="text-xs text-slate-500 mb-2 min-h-[32px]">{c.description}</p>
                <div className="text-xs text-slate-700 space-y-0.5">
                  <p><strong>Key:</strong> <code className="bg-slate-100 px-1 rounded">{c.key}</code></p>
                  <p><strong>Payment:</strong> {c.default_payment_type}</p>
                  {c.linked_role && <p><strong>Role:</strong> {c.linked_role}</p>}
                </div>
                <div className="mt-3">
                  <Button size="sm" variant="outline" onClick={() => setEditing(c)} data-testid={`edit-cat-${c.key}`}><Edit className="h-3.5 w-3.5 mr-1" /> Edit</Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <CategoryModal open={creating || !!editing} editing={editing} onClose={() => { setEditing(null); setCreating(false); }} onSaved={load} />
    </div>
  );
}
