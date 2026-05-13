import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Save, Plus, X, History } from 'lucide-react';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LeaveTypesManager() {
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [showAudit, setShowAudit] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [r1, r2] = await Promise.all([
        axios.get(`${API}/hr/leave-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/hr/audit-log?limit=20`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setTypes(r1.data || []);
      setAuditLog((r2.data || []).filter((a) => a.scope?.startsWith('leave_type')));
    } catch (e) {
      toast.error('Failed to load leave types');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <HRSettingsLayout
      title="Leave Types & Policies"
      subtitle="Configure annual quotas, monthly caps, and rules per leave type"
      breadcrumb="Leave Types & Policies"
    >
      <div className="flex items-center justify-between mb-4">
        <Badge variant="outline" className="text-xs">{types.length} type{types.length !== 1 ? 's' : ''}</Badge>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowAudit(!showAudit)} data-testid="toggle-audit">
            <History className="h-3.5 w-3.5 mr-1.5" /> Audit Log
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-leave-type-btn">
            <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Custom Type
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <p className="text-slate-500 text-sm">Loading...</p>
        ) : (
          types.map((lt) => <LeaveTypeCard key={lt.key} lt={lt} onChange={load} />)
        )}
      </div>

      {showAudit && (
        <Card className="mt-5 p-4" data-testid="audit-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-800">Recent Policy Changes</h3>
            <Button size="sm" variant="ghost" onClick={() => setShowAudit(false)}><X className="h-4 w-4" /></Button>
          </div>
          {auditLog.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No recent changes</p>
          ) : (
            <div className="space-y-1.5">
              {auditLog.map((a) => (
                <div key={a.id} className="text-xs p-2 bg-slate-50 rounded flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-800">
                      <Badge className="text-[10px] mr-1.5">{a.action}</Badge>
                      {a.scope} · by {a.actor_name}
                    </p>
                    <p className="text-slate-500 text-[10px]">
                      Before: {JSON.stringify(a.before).slice(0, 80)}
                    </p>
                    <p className="text-slate-700 text-[10px]">
                      After: {JSON.stringify(a.after).slice(0, 80)}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap">
                    {new Date(a.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {showCreate && (
        <CreateLeaveTypeModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); load(); }}
        />
      )}
    </HRSettingsLayout>
  );
}


function LeaveTypeCard({ lt, onChange }) {
  const [form, setForm] = useState(lt);
  const [saving, setSaving] = useState(false);
  const dirty = JSON.stringify(form) !== JSON.stringify(lt);

  const save = async () => {
    const payload = {};
    for (const k of ['annual_quota', 'monthly_cap', 'max_consecutive', 'carry_forward', 'carry_forward_cap', 'min_notice_days', 'requires_proof_after_days', 'is_active', 'color']) {
      if (form[k] !== lt[k]) payload[k] = form[k];
    }
    if (Object.keys(payload).length === 0) return;
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`${API}/hr/leave-types/${lt.key}`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`${lt.name} updated`);
      onChange();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="overflow-hidden border-t-4" style={{ borderTopColor: lt.color || '#6b7280' }} data-testid={`leave-type-${lt.key}`}>
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              {lt.name}
              <Badge className="text-[10px]" style={{ background: `${lt.color}22`, color: lt.color }}>{lt.short_code}</Badge>
            </h3>
            <p className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5">{lt.key}</p>
          </div>
          <div className="flex items-center gap-1.5">
            <Switch checked={!!form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} data-testid={`active-${lt.key}`} />
          </div>
        </div>

        <div className="space-y-2">
          <NumField label="Annual Quota" value={form.annual_quota} onChange={(v) => setForm({ ...form, annual_quota: v })} testid={`quota-${lt.key}`} />
          <NumField label="Monthly Cap" value={form.monthly_cap} onChange={(v) => setForm({ ...form, monthly_cap: v })} hint="0 = no cap" testid={`monthly-${lt.key}`} />
          <NumField label="Max Consecutive" value={form.max_consecutive} onChange={(v) => setForm({ ...form, max_consecutive: v })} testid={`consec-${lt.key}`} />
          <NumField label="Min Notice (days)" value={form.min_notice_days || 0} onChange={(v) => setForm({ ...form, min_notice_days: v })} testid={`notice-${lt.key}`} />
          <div className="flex items-center justify-between py-1">
            <label className="text-xs text-slate-700">Carry Forward</label>
            <Switch checked={!!form.carry_forward} onCheckedChange={(v) => setForm({ ...form, carry_forward: v })} data-testid={`carry-${lt.key}`} />
          </div>
          {form.carry_forward && (
            <NumField label="Carry Forward Cap" value={form.carry_forward_cap || 0} onChange={(v) => setForm({ ...form, carry_forward_cap: v })} testid={`carry-cap-${lt.key}`} />
          )}
          <NumField label="Proof Required After (days)" value={form.requires_proof_after_days || 0} onChange={(v) => setForm({ ...form, requires_proof_after_days: v })} hint="0 = never" testid={`proof-${lt.key}`} />
        </div>

        <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between">
          {dirty ? (
            <span className="text-[10px] text-amber-600 font-semibold">● Unsaved</span>
          ) : (
            <span className="text-[10px] text-emerald-600">✓ Saved</span>
          )}
          <Button size="sm" onClick={save} disabled={!dirty || saving} data-testid={`save-${lt.key}`}>
            <Save className="h-3 w-3 mr-1" /> {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
        {lt.is_system && (
          <p className="text-[10px] text-slate-400 italic mt-2">System type — cannot be deleted, only deactivated</p>
        )}
      </div>
    </Card>
  );
}


function NumField({ label, value, onChange, hint, testid }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-xs text-slate-700 flex-1">
        {label}
        {hint && <span className="text-[10px] text-slate-400 ml-1">({hint})</span>}
      </label>
      <input
        type="number"
        min="0"
        value={value ?? 0}
        onChange={(e) => onChange(parseInt(e.target.value) || 0)}
        className="px-2 py-1 border rounded text-xs w-20 tabular-nums text-right"
        data-testid={testid}
      />
    </div>
  );
}


function CreateLeaveTypeModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    key: '',
    name: '',
    short_code: '',
    annual_quota: 12,
    monthly_cap: 0,
    max_consecutive: 7,
    carry_forward: false,
    carry_forward_cap: 0,
    requires_proof_after_days: 0,
    min_notice_days: 0,
    color: '#6366f1',
    applicable_to: ['all'],
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!/^[a-z][a-z0-9_]+$/.test(form.key)) {
      toast.error('Key must be lowercase letters/numbers/underscore, start with a letter');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/hr/leave-types`, form, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`✅ Leave type "${form.name}" created`);
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Create failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white my-8" onClick={(e) => e.stopPropagation()} data-testid="create-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Create Custom Leave Type</h2>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="space-y-3">
          <FormField label="Key (slug)" hint="lowercase_with_underscores, e.g., bereavement_leave">
            <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value.toLowerCase() })} className="w-full px-3 py-2 border rounded text-sm font-mono" data-testid="create-key" />
          </FormField>
          <div className="grid grid-cols-2 gap-2">
            <FormField label="Display Name">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 border rounded text-sm" data-testid="create-name" />
            </FormField>
            <FormField label="Short Code">
              <input value={form.short_code} onChange={(e) => setForm({ ...form, short_code: e.target.value.toUpperCase() })} maxLength={8} className="w-full px-3 py-2 border rounded text-sm uppercase font-mono" data-testid="create-short" />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <FormField label="Annual Quota">
              <input type="number" min="0" value={form.annual_quota} onChange={(e) => setForm({ ...form, annual_quota: parseInt(e.target.value) || 0 })} className="w-full px-3 py-2 border rounded text-sm" data-testid="create-quota" />
            </FormField>
            <FormField label="Monthly Cap (0=none)">
              <input type="number" min="0" value={form.monthly_cap} onChange={(e) => setForm({ ...form, monthly_cap: parseInt(e.target.value) || 0 })} className="w-full px-3 py-2 border rounded text-sm" data-testid="create-monthly" />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <FormField label="Max Consecutive">
              <input type="number" min="1" value={form.max_consecutive} onChange={(e) => setForm({ ...form, max_consecutive: parseInt(e.target.value) || 1 })} className="w-full px-3 py-2 border rounded text-sm" data-testid="create-consec" />
            </FormField>
            <FormField label="Color">
              <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} className="w-full h-10 border rounded" data-testid="create-color" />
            </FormField>
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={submit} disabled={submitting || !form.key || !form.name || !form.short_code} data-testid="create-submit">
              {submitting ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}


function FormField({ label, hint, children }) {
  return (
    <div>
      <label className="text-xs font-semibold text-slate-700 uppercase block">{label}</label>
      {hint && <p className="text-[10px] text-slate-500 mb-1">{hint}</p>}
      {children}
    </div>
  );
}
