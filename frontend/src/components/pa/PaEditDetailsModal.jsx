import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Edit3, X, Save, AlertCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FIELDS = [
  { key: 'client_name', label: 'Client Name', required: true },
  { key: 'client_email', label: 'Email', type: 'email' },
  { key: 'client_mobile', label: 'Mobile (with country code)', placeholder: '+91-XXXXXXXXXX' },
  { key: 'client_age', label: 'Age', type: 'number' },
  { key: 'education', label: 'Education', placeholder: "Bachelor's, Master's..." },
  { key: 'work_experience', label: 'Work Experience', placeholder: '5 years IT' },
  { key: 'country', label: 'Country', placeholder: 'Canada / Australia...' },
  { key: 'service_type', label: 'Service Type', placeholder: 'PR / Work Visa...' },
];

export default function PaEditDetailsModal({ pa, open, onClose, onSaved }) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const locked = pa?.stage === 'case_created';

  useEffect(() => {
    if (open && pa) {
      setForm({
        client_name: pa.client_name || '',
        client_email: pa.client_email || '',
        client_mobile: pa.client_mobile || '',
        client_age: pa.client_age || '',
        education: pa.education || '',
        work_experience: pa.work_experience || '',
        country: pa.country || '',
        service_type: pa.service_type || '',
        notes: pa.notes || '',
      });
    }
  }, [open, pa]);

  if (!open || !pa) return null;

  const save = async () => {
    if (locked) return;
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach(f => {
        const v = form[f.key];
        if (v !== '' && v !== null && v !== undefined && String(v) !== String(pa[f.key] || '')) {
          payload[f.key] = f.type === 'number' ? parseInt(v) : v;
        }
      });
      if ((form.notes || '') !== (pa.notes || '')) payload.notes = form.notes;

      if (Object.keys(payload).length === 0) {
        toast.info('No changes to save');
        setSaving(false);
        return;
      }

      const r = await axios.put(`${API}/pre-assessment/${pa.id}/details`, payload, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      const changes = r.data.changes || [];
      toast.success(`Saved ${changes.length} change(s)`);
      if (onSaved) onSaved(payload);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Update failed');
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="pa-edit-modal">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[92vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b bg-gradient-to-r from-indigo-50 to-violet-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Edit3 className="h-5 w-5 text-indigo-600" />
            <div>
              <p className="font-bold text-slate-800">Edit Pre-Assessment Details</p>
              <p className="text-[11px] text-slate-500 font-mono">{pa.pa_number || pa.id?.slice(0, 8)}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} data-testid="edit-modal-close"><X className="h-4 w-4" /></Button>
        </div>

        {locked && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center gap-2 text-xs text-amber-800">
            <AlertCircle className="h-4 w-4" />
            <span>This case is <strong>active</strong> — details are locked. Edit from the Case page instead.</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {FIELDS.map(f => (
              <div key={f.key}>
                <label className="text-xs font-medium text-slate-600 block mb-1">
                  {f.label}{f.required ? ' *' : ''}
                </label>
                <Input
                  type={f.type || 'text'}
                  value={form[f.key] ?? ''}
                  placeholder={f.placeholder || ''}
                  onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                  disabled={locked}
                  data-testid={`edit-${f.key}`}
                />
              </div>
            ))}
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Notes</label>
            <textarea
              value={form.notes ?? ''}
              onChange={e => setForm({ ...form, notes: e.target.value })}
              className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm h-20"
              disabled={locked}
              data-testid="edit-notes"
              placeholder="Internal notes / context for admin..."
            />
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded p-2.5 text-[11px] text-slate-500">
            ✏️ Edits create an audit-log entry visible to Admin. Stage transitions are not editable here — use the workflow buttons.
          </div>
        </div>

        <div className="p-4 border-t bg-slate-50 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving || locked} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="edit-save-btn">
            <Save className="h-4 w-4 mr-1" /> {saving ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}
