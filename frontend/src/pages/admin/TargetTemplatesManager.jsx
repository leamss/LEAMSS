/**
 * Phase 4B — Target Templates Manager (admin/head only).
 * Simple CRUD: list active templates, create new, edit, soft-delete.
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
import { ArrowLeft, Layers, Plus, Edit, Trash2, Lock } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const formatINR = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

const TemplateModal = ({ open, onClose, template, onSaved }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [revenue, setRevenue] = useState('');
  const [paCount, setPaCount] = useState('');
  const [periodType, setPeriodType] = useState('monthly');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName(template?.name || '');
      setDescription(template?.description || '');
      setRevenue(template?.revenue?.toString() || '');
      setPaCount(template?.pa_count?.toString() || '');
      setPeriodType(template?.period_type || 'monthly');
    }
  }, [open, template]);

  const handleSave = async () => {
    if (!name || !revenue || !paCount) { toast.error('Name, revenue, PA count required'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const body = {
        name, description,
        revenue: parseFloat(revenue),
        pa_count: parseInt(paCount, 10),
        period_type: periodType,
        applicable_roles: ['sales_executive', 'sr_sales_executive'],
      };
      if (template) {
        await axios.patch(`${API}/sales/target-templates/${template.id}`, body, { headers });
        toast.success('Template updated');
      } else {
        await axios.post(`${API}/sales/target-templates`, body, { headers });
        toast.success('Template created');
      }
      onSaved();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="template-modal">
        <DialogHeader><DialogTitle>{template ? 'Edit Template' : 'New Template'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label className="text-sm font-bold">Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} data-testid="tpl-name" /></div>
          <div><Label className="text-sm font-bold">Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} data-testid="tpl-description" /></div>
          <div><Label className="text-sm font-bold">Period Type</Label>
            <Select value={periodType} onValueChange={setPeriodType}>
              <SelectTrigger data-testid="tpl-period-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="quarterly">Quarterly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label className="text-sm font-bold">Revenue (₹)</Label><Input type="number" value={revenue} onChange={(e) => setRevenue(e.target.value)} data-testid="tpl-revenue" /></div>
            <div><Label className="text-sm font-bold">PA Count</Label><Input type="number" value={paCount} onChange={(e) => setPaCount(e.target.value)} data-testid="tpl-pa-count" /></div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-template-btn">{saving ? 'Saving…' : 'Save'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default function TargetTemplatesManager() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/sales/target-templates`, { headers: { Authorization: `Bearer ${token}` } });
      setTemplates(r.data.templates || []);
    } catch (e) { toast.error('Failed to load templates'); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const remove = async (id, isSystem) => {
    if (isSystem) { toast.error('System templates cannot be deleted'); return; }
    if (!window.confirm('Soft-delete this template? Existing assigned targets will not be affected.')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/sales/target-templates/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Template deactivated');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Delete failed'); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="target-templates-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin/sales/targets')} className="p-2 rounded-lg hover:bg-slate-200 transition" data-testid="back-to-targets">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Layers className="h-7 w-7 text-indigo-600" />Target Templates</h1>
              <p className="text-sm text-slate-500 mt-1">Reusable target presets for bulk-applying to teams</p>
            </div>
          </div>
          <Button onClick={() => setCreating(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-template-btn"><Plus className="h-4 w-4 mr-1.5" /> New Template</Button>
        </div>

        {loading ? (
          <Card className="p-12 text-center text-slate-500">Loading…</Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="templates-grid">
            {templates.filter((t) => t.is_active).map((t) => (
              <Card key={t.id} className="p-5 hover:shadow-md transition" data-testid={`template-card-${t.id}`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-slate-800">{t.name}</h3>
                    {t.is_system && <Badge className="bg-purple-100 text-purple-700 text-[10px] mt-1"><Lock className="h-3 w-3 mr-1" />System</Badge>}
                  </div>
                  <Badge variant="outline" className="text-xs uppercase">{t.period_type}</Badge>
                </div>
                <p className="text-xs text-slate-500 mb-3 min-h-[36px]">{t.description}</p>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                    <p className="text-[10px] font-bold uppercase text-emerald-700">Revenue</p>
                    <p className="text-lg font-extrabold text-emerald-700">{formatINR(t.revenue)}</p>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded p-2">
                    <p className="text-[10px] font-bold uppercase text-blue-700">PA Count</p>
                    <p className="text-lg font-extrabold text-blue-700">{t.pa_count}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={t.is_system} onClick={() => setEditing(t)} data-testid={`edit-tpl-${t.id}`}><Edit className="h-3.5 w-3.5 mr-1" /> Edit</Button>
                  <Button size="sm" variant="destructive" disabled={t.is_system} onClick={() => remove(t.id, t.is_system)} data-testid={`delete-tpl-${t.id}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <TemplateModal open={creating || !!editing} onClose={() => { setEditing(null); setCreating(false); }} template={editing} onSaved={load} />
    </div>
  );
}
