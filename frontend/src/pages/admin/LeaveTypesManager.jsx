import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Plus, X, History, Pencil, Trash2, EyeOff, Eye, AlertTriangle, Sparkles } from 'lucide-react';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PRESET_COLORS = [
  { name: 'Blue',    hex: '#3b82f6' },
  { name: 'Red',     hex: '#ef4444' },
  { name: 'Green',   hex: '#10b981' },
  { name: 'Yellow',  hex: '#eab308' },
  { name: 'Purple',  hex: '#a855f7' },
  { name: 'Pink',    hex: '#ec4899' },
  { name: 'Cyan',    hex: '#06b6d4' },
  { name: 'Orange',  hex: '#f97316' },
  { name: 'Indigo',  hex: '#6366f1' },
  { name: 'Teal',    hex: '#14b8a6' },
  { name: 'Rose',    hex: '#f43f5e' },
  { name: 'Gray',    hex: '#737373' },
];

export default function LeaveTypesManager() {
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteItem, setDeleteItem] = useState(null);
  const [deactivateItem, setDeactivateItem] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [showAudit, setShowAudit] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [r1, r2] = await Promise.all([
        axios.get(`${API}/hr/leave-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/hr/audit-log?limit=30`, { headers: { Authorization: `Bearer ${token}` } }),
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

  const handleToggleActive = async (lt, next) => {
    try {
      const token = localStorage.getItem('token');
      if (next) {
        await axios.post(`${API}/hr/leave-types/${lt.key}/activate`, {}, { headers: { Authorization: `Bearer ${token}` } });
        toast.success(`${lt.name} reactivated`);
        load();
      } else {
        setDeactivateItem(lt);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  return (
    <HRSettingsLayout
      title="Leave Types & Policies"
      subtitle="Configure annual quotas, monthly caps, colors, and rules per leave type"
      breadcrumb="Leave Types & Policies"
    >
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">{types.filter((t) => t.is_active && !t.soft_deleted).length} active</Badge>
          <Badge variant="outline" className="text-xs text-slate-500">{types.filter((t) => !t.is_active && !t.soft_deleted).length} inactive</Badge>
          {types.some((t) => t.soft_deleted) && (
            <Badge variant="outline" className="text-xs text-rose-500">{types.filter((t) => t.soft_deleted).length} deleted</Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowAudit(!showAudit)} data-testid="toggle-audit">
            <History className="h-3.5 w-3.5 mr-1.5" /> Audit Log
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="add-leave-type-btn">
            <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Custom Type
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <p className="text-slate-500 text-sm">Loading...</p>
        ) : (
          types.map((lt) => (
            <LeaveTypeCard
              key={lt.key}
              lt={lt}
              onEdit={() => setEditItem(lt)}
              onDelete={() => setDeleteItem(lt)}
              onToggleActive={(v) => handleToggleActive(lt, v)}
            />
          ))
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
            <div className="space-y-1.5 max-h-96 overflow-y-auto">
              {auditLog.map((a) => (
                <div key={a.id} className="text-xs p-2 bg-slate-50 rounded">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Badge className="text-[10px]">{a.action}</Badge>
                    <span className="font-mono text-slate-700">{a.scope}</span>
                    <span className="text-slate-500">by {a.actor_name}</span>
                    <span className="text-[10px] text-slate-400 ml-auto">{new Date(a.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}</span>
                  </div>
                  {(Object.keys(a.before || {}).length > 0 || Object.keys(a.after || {}).length > 0) && (
                    <div className="mt-1 text-[11px]">
                      {Object.keys(a.before || {}).map((k) => {
                        const isColor = k === 'color';
                        return (
                          <div key={k} className="text-slate-600 flex items-center gap-1">
                            <strong>{k}:</strong>
                            {isColor ? (
                              <><span className="inline-block w-3 h-3 rounded border" style={{ background: a.before[k] }} /> {a.before[k]}</>
                            ) : (
                              <span>{JSON.stringify(a.before[k])}</span>
                            )}
                            <span className="text-slate-400">→</span>
                            {isColor ? (
                              <><span className="inline-block w-3 h-3 rounded border" style={{ background: a.after[k] }} /> {a.after[k]}</>
                            ) : (
                              <strong>{JSON.stringify(a.after[k])}</strong>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {a.note && <p className="text-[10px] text-slate-500 italic mt-1">"{a.note}"</p>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {showCreate && (
        <EditCreateModal mode="create" onClose={() => setShowCreate(false)} onSuccess={() => { setShowCreate(false); load(); }} />
      )}
      {editItem && (
        <EditCreateModal mode="edit" item={editItem} onClose={() => setEditItem(null)} onSuccess={() => { setEditItem(null); load(); }} />
      )}
      {deleteItem && (
        <DeleteModal item={deleteItem} onClose={() => setDeleteItem(null)} onSuccess={() => { setDeleteItem(null); load(); }} />
      )}
      {deactivateItem && (
        <DeactivateModal item={deactivateItem} onClose={() => setDeactivateItem(null)} onSuccess={() => { setDeactivateItem(null); load(); }} />
      )}
    </HRSettingsLayout>
  );
}


function LeaveTypeCard({ lt, onEdit, onDelete, onToggleActive }) {
  const stats = lt.stats || {};
  const isInactive = !lt.is_active;
  const isDeleted = lt.soft_deleted;

  return (
    <Card
      className={`overflow-hidden border-t-4 transition-opacity ${isInactive ? 'opacity-60' : ''}`}
      style={{ borderTopColor: lt.color || '#6b7280' }}
      data-testid={`leave-type-${lt.key}`}
    >
      <div className="p-4">
        {/* Top action bar */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className={`text-sm font-bold flex items-center gap-2 ${isInactive ? 'line-through text-slate-500' : 'text-slate-900'}`}>
              {lt.name}
              <Badge className="text-[10px]" style={{ background: `${lt.color}22`, color: lt.color }}>{lt.short_code}</Badge>
              {lt.is_system && <Badge variant="outline" className="text-[10px]">System</Badge>}
              {isDeleted && <Badge className="text-[10px] bg-rose-100 text-rose-800">Deleted</Badge>}
            </h3>
            <p className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5 font-mono">{lt.key}</p>
            {lt.description && <p className="text-[11px] text-slate-600 mt-1">{lt.description}</p>}
          </div>
          <div className="flex items-center gap-1">
            {!isDeleted && (
              <Switch
                checked={!!lt.is_active}
                onCheckedChange={onToggleActive}
                data-testid={`toggle-active-${lt.key}`}
                title={lt.is_active ? 'Deactivate' : 'Reactivate'}
              />
            )}
          </div>
        </div>

        {isInactive && !isDeleted && (
          <div className="mb-3 p-2 bg-slate-100 rounded text-[10px] text-slate-700 flex items-center gap-1.5" data-testid={`inactive-banner-${lt.key}`}>
            <EyeOff className="h-3 w-3" /> Inactive — Not shown to employees
          </div>
        )}
        {isDeleted && (
          <div className="mb-3 p-2 bg-rose-50 rounded text-[10px] text-rose-700 flex items-center gap-1.5" data-testid={`deleted-banner-${lt.key}`}>
            <Trash2 className="h-3 w-3" /> Soft-deleted on {lt.deleted_at ? new Date(lt.deleted_at).toLocaleDateString('en-IN') : '?'}
            {lt.delete_reason && <span className="ml-1 italic">"{lt.delete_reason}"</span>}
          </div>
        )}

        {/* Read-only summary fields */}
        <div className="space-y-1 text-xs">
          <SummaryRow label="Annual Quota" value={lt.annual_quota} />
          <SummaryRow label="Monthly Cap" value={lt.monthly_cap > 0 ? lt.monthly_cap : 'None'} />
          <SummaryRow label="Max Consecutive" value={lt.max_consecutive} unit="days" />
          <SummaryRow label="Min Notice" value={lt.min_notice_days || 0} unit="days" />
          {lt.carry_forward && (
            <SummaryRow label="Carry Forward" value={lt.carry_forward_cap > 0 ? `up to ${lt.carry_forward_cap}` : 'enabled'} />
          )}
          {lt.requires_proof_after_days > 0 && (
            <SummaryRow label="Proof After" value={lt.requires_proof_after_days} unit="days" />
          )}
        </div>

        {/* Stats */}
        <div className="mt-3 pt-3 border-t border-slate-200">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <p className="text-slate-400 uppercase">Active Apps</p>
              <p className="font-bold text-slate-700">{stats.active_applications || 0}</p>
            </div>
            <div>
              <p className="text-slate-400 uppercase">Employees Used</p>
              <p className="font-bold text-slate-700">{stats.employees_used || 0}</p>
            </div>
          </div>
          {lt.updated_by_name && (
            <p className="text-[10px] text-slate-400 mt-2 italic">
              Last edited by {lt.updated_by_name} · {lt.updated_at ? new Date(lt.updated_at).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '?'}
            </p>
          )}
        </div>

        {/* Action buttons */}
        {!isDeleted && (
          <div className="mt-3 pt-3 border-t border-slate-200 flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={onEdit} data-testid={`edit-${lt.key}`}>
              <Pencil className="h-3 w-3 mr-1" /> Edit
            </Button>
            {lt.is_system ? (
              <Button size="sm" variant="outline" className="text-slate-600" onClick={() => onToggleActive(!lt.is_active)} disabled={!lt.is_active} data-testid={`deactivate-${lt.key}`}>
                <EyeOff className="h-3 w-3 mr-1" /> Deactivate
              </Button>
            ) : (
              <Button size="sm" variant="outline" className="text-rose-600 border-rose-200 hover:bg-rose-50" onClick={onDelete} data-testid={`delete-${lt.key}`}>
                <Trash2 className="h-3 w-3 mr-1" /> Delete
              </Button>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}


function SummaryRow({ label, value, unit }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold text-slate-800">
        {value}{unit ? ` ${unit}` : ''}
      </span>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Edit / Create Modal — handles both modes
// ─────────────────────────────────────────────────────────────────
function EditCreateModal({ mode, item, onClose, onSuccess }) {
  const initial = mode === 'edit' ? { ...item } : {
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
    description: '',
    applicable_to: ['all'],
  };
  const [form, setForm] = useState(initial);
  const [submitting, setSubmitting] = useState(false);

  const isSystem = mode === 'edit' && form.is_system;
  const setF = (k, v) => setForm({ ...form, [k]: v });

  const submit = async () => {
    if (mode === 'create') {
      if (!/^[a-z][a-z0-9_]+$/.test(form.key)) {
        toast.error('Key must be lowercase letters/numbers/underscore');
        return;
      }
      if (!form.name || form.name.length < 2) { toast.error('Name is required'); return; }
      if (!form.short_code) { toast.error('Short code is required'); return; }
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      if (mode === 'edit') {
        // Build diff
        const allowedFields = isSystem
          ? ['annual_quota', 'monthly_cap', 'max_consecutive', 'min_notice_days', 'requires_proof_after_days', 'color', 'description', 'carry_forward', 'carry_forward_cap', 'is_active']
          : ['name', 'annual_quota', 'monthly_cap', 'max_consecutive', 'min_notice_days', 'requires_proof_after_days', 'color', 'description', 'carry_forward', 'carry_forward_cap', 'is_active'];
        const payload = {};
        for (const f of allowedFields) {
          if (JSON.stringify(form[f]) !== JSON.stringify(item[f])) {
            payload[f] = form[f];
          }
        }
        if (Object.keys(payload).length === 0) {
          toast.info('No changes to save');
          setSubmitting(false);
          return;
        }
        // Get usage stats before save
        let usageMsg = '';
        try {
          const u = await axios.get(`${API}/hr/leave-types/${item.key}/usage`, { headers: { Authorization: `Bearer ${token}` } });
          if (u.data?.stats?.employees_used > 0) {
            usageMsg = `\n\n${u.data.stats.employees_used} employee(s) currently use this type. ${u.data.stats.active_applications} active application(s) exist. Changes take effect immediately.`;
          }
        } catch (e) {}
        if (!window.confirm(`Save ${Object.keys(payload).length} change(s)?${usageMsg}`)) {
          setSubmitting(false);
          return;
        }
        await axios.patch(`${API}/hr/leave-types/${item.key}`, payload, { headers: { Authorization: `Bearer ${token}` } });
        toast.success(`${item.name} updated`);
      } else {
        await axios.post(`${API}/hr/leave-types`, form, { headers: { Authorization: `Bearer ${token}` } });
        toast.success(`Leave type "${form.name}" created`);
      }
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <Card className="max-w-2xl w-full p-5 bg-white my-8" onClick={(e) => e.stopPropagation()} data-testid="edit-modal">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold">
              {mode === 'edit' ? `Edit ${item.name}` : 'Create Custom Leave Type'}
            </h2>
            {isSystem && (
              <p className="text-xs text-amber-700 mt-0.5 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> System type — limited editing (Name, Key, Short Code locked)
              </p>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {mode === 'create' && (
            <FormField label="Key (slug)" hint="lowercase_with_underscores">
              <input value={form.key} onChange={(e) => setF('key', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))} className="w-full px-3 py-2 border rounded text-sm font-mono" data-testid="modal-key" />
            </FormField>
          )}
          <FormField label="Display Name">
            <input value={form.name} onChange={(e) => setF('name', e.target.value)} disabled={isSystem} className="w-full px-3 py-2 border rounded text-sm disabled:bg-slate-100" data-testid="modal-name" />
          </FormField>
          {mode === 'create' && (
            <FormField label="Short Code">
              <input value={form.short_code} onChange={(e) => setF('short_code', e.target.value.toUpperCase())} maxLength={8} className="w-full px-3 py-2 border rounded text-sm uppercase font-mono" data-testid="modal-short" />
            </FormField>
          )}
          <FormField label="Annual Quota">
            <input type="number" min="0" value={form.annual_quota || 0} onChange={(e) => setF('annual_quota', parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-quota" />
          </FormField>
          <FormField label="Monthly Cap" hint="0 = no cap">
            <input type="number" min="0" value={form.monthly_cap || 0} onChange={(e) => setF('monthly_cap', parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-monthly" />
          </FormField>
          <FormField label="Max Consecutive (days)">
            <input type="number" min="1" max="365" value={form.max_consecutive || 1} onChange={(e) => setF('max_consecutive', parseInt(e.target.value) || 1)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-consec" />
          </FormField>
          <FormField label="Min Notice (days)">
            <input type="number" min="0" value={form.min_notice_days || 0} onChange={(e) => setF('min_notice_days', parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-notice" />
          </FormField>
          <FormField label="Proof Required After (days)" hint="0 = never">
            <input type="number" min="0" value={form.requires_proof_after_days || 0} onChange={(e) => setF('requires_proof_after_days', parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-proof" />
          </FormField>
          <FormField label="Carry Forward">
            <label className="flex items-center gap-2 mt-2">
              <Switch checked={!!form.carry_forward} onCheckedChange={(v) => setF('carry_forward', v)} data-testid="modal-carry" />
              <span className="text-xs text-slate-700">{form.carry_forward ? 'Enabled' : 'Disabled'}</span>
            </label>
          </FormField>
          {form.carry_forward && (
            <FormField label="Carry Forward Cap">
              <input type="number" min="0" value={form.carry_forward_cap || 0} onChange={(e) => setF('carry_forward_cap', parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-carry-cap" />
            </FormField>
          )}
        </div>

        {/* Color Picker */}
        <div className="mt-4 pt-4 border-t border-slate-200">
          <label className="text-xs font-semibold text-slate-700 uppercase mb-2 block">Color</label>
          <div className="flex items-start gap-4 flex-wrap">
            <div className="flex flex-wrap gap-1.5" data-testid="color-presets">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c.hex}
                  type="button"
                  onClick={() => setF('color', c.hex)}
                  className={`w-8 h-8 rounded border-2 transition-transform hover:scale-110 ${form.color === c.hex ? 'border-slate-800 ring-2 ring-offset-1 ring-slate-300' : 'border-slate-200'}`}
                  style={{ background: c.hex }}
                  title={c.name}
                  data-testid={`color-${c.name.toLowerCase()}`}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.color || '#6366f1'}
                onChange={(e) => setF('color', e.target.value)}
                className="w-12 h-8 border rounded cursor-pointer"
                data-testid="modal-color-custom"
              />
              <input
                type="text"
                value={form.color || ''}
                onChange={(e) => setF('color', e.target.value)}
                className="w-24 px-2 py-1 border rounded text-xs font-mono"
                placeholder="#3b82f6"
                data-testid="modal-color-hex"
              />
            </div>
          </div>

          {/* Live preview */}
          <div className="mt-3 p-3 bg-slate-50 rounded">
            <p className="text-[10px] uppercase text-slate-500 font-semibold mb-2">Live Preview</p>
            <div className="flex items-center gap-3 flex-wrap text-xs">
              <Card className="p-2 border-t-2" style={{ borderTopColor: form.color, minWidth: '100px' }}>
                <p className="font-bold text-slate-800">{form.name || 'Type Name'}</p>
                <span className="text-[10px]" style={{ color: form.color }}>{form.short_code || 'SC'}</span>
              </Card>
              <Badge style={{ background: `${form.color}22`, color: form.color }}>{form.short_code || 'CODE'}</Badge>
              <span className="px-2 py-1 rounded text-[10px] text-white" style={{ background: form.color }}>Notification</span>
              <div className="w-8 h-8 rounded border-t-4 bg-white shadow-sm flex items-center justify-center" style={{ borderTopColor: form.color }}>
                <span className="text-[10px]">CAL</span>
              </div>
            </div>
          </div>
        </div>

        {/* Description */}
        <div className="mt-4">
          <FormField label="Description (optional)">
            <textarea value={form.description || ''} onChange={(e) => setF('description', e.target.value)} rows={2} className="w-full px-3 py-2 border rounded text-sm" data-testid="modal-description" />
          </FormField>
        </div>

        <div className="flex gap-2 justify-end pt-4 mt-4 border-t border-slate-200">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={submitting} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="modal-submit">
            {submitting ? 'Saving...' : (mode === 'edit' ? 'Save Changes' : 'Create Leave Type')}
          </Button>
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


// ─────────────────────────────────────────────────────────────────
// Delete Modal (custom types only)
// ─────────────────────────────────────────────────────────────────
function DeleteModal({ item, onClose, onSuccess }) {
  const [usage, setUsage] = useState(null);
  const [reason, setReason] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/hr/leave-types/${item.key}/usage`, { headers: { Authorization: `Bearer ${token}` } });
        setUsage(r.data?.stats);
      } catch (e) {
        setUsage(item.stats || {});
      }
    };
    fetchUsage();
  }, [item.key]);

  const submit = async () => {
    if (reason.length < 20) {
      toast.error('Reason must be at least 20 characters');
      return;
    }
    if (confirmText !== 'DELETE') {
      toast.error('Type DELETE to confirm');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.delete(`${API}/hr/leave-types/${item.key}`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { reason },
      });
      toast.success(`Soft-deleted. ${r.data.cancelled_applications || 0} pending application(s) cancelled.`);
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Delete failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white my-8 border-2 border-rose-300" onClick={(e) => e.stopPropagation()} data-testid="delete-modal">
        <div className="flex items-center gap-2 mb-4 text-rose-700">
          <AlertTriangle className="h-5 w-5" />
          <h2 className="text-lg font-bold">⚠️ Permanent Action</h2>
        </div>
        <p className="text-sm text-slate-700 mb-3">
          Delete leave type: <strong className="text-slate-900">{item.name}</strong>?
        </p>

        {usage && (
          <Card className="p-3 bg-slate-50 mb-3" data-testid="delete-impact">
            <p className="text-xs font-bold text-slate-700 uppercase mb-2">Impact Analysis</p>
            <div className="space-y-1 text-xs text-slate-700">
              <p>• Active applications: <strong className="text-amber-700">{usage.active_applications || 0}</strong> (will be cancelled)</p>
              <p>• Approved future leaves: <strong className="text-amber-700">{usage.approved_future || 0}</strong> (remain valid)</p>
              <p>• Historical records: <strong>{usage.historical_total || 0}</strong> (preserved for audit)</p>
              <p>• Employees ever used: <strong>{usage.employees_used || 0}</strong></p>
            </div>
          </Card>
        )}

        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">
              Reason <span className="text-rose-500">(required, min 20 chars)</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full mt-1 px-3 py-2 border rounded text-sm"
              placeholder="Why is this leave type being deleted?"
              data-testid="delete-reason"
            />
            <p className="text-[10px] text-slate-400 mt-0.5">{reason.length}/20 chars</p>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">
              Type <span className="font-mono text-rose-600">DELETE</span> to confirm
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded text-sm font-mono"
              placeholder="DELETE"
              data-testid="delete-confirm-text"
            />
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose} data-testid="delete-cancel">Cancel</Button>
            <Button
              onClick={submit}
              disabled={submitting || reason.length < 20 || confirmText !== 'DELETE'}
              className="bg-rose-600 hover:bg-rose-700"
              data-testid="delete-confirm"
            >
              {submitting ? 'Deleting...' : 'Permanently Delete'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Deactivate Modal (system types — soft toggle)
// ─────────────────────────────────────────────────────────────────
function DeactivateModal({ item, onClose, onSuccess }) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/hr/leave-types/${item.key}/deactivate`, { reason }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`${item.name} deactivated. Employees will not see this for new applications.`);
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white" onClick={(e) => e.stopPropagation()} data-testid="deactivate-modal">
        <div className="flex items-center gap-2 mb-3 text-amber-700">
          <EyeOff className="h-5 w-5" />
          <h2 className="text-lg font-bold">Deactivate Leave Type</h2>
        </div>
        <Card className="p-3 bg-amber-50 mb-3">
          <p className="text-xs text-amber-900">
            <strong>{item.name}</strong> will be hidden from new leave applications. Existing applications continue normally.
            You can reactivate it anytime.
          </p>
        </Card>
        <div>
          <label className="text-xs font-semibold text-slate-700 uppercase">Reason (optional)</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className="w-full mt-1 px-3 py-2 border rounded text-sm"
            data-testid="deactivate-reason"
          />
        </div>
        <div className="flex gap-2 justify-end pt-3">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={submitting} className="bg-amber-600 hover:bg-amber-700" data-testid="deactivate-confirm">
            {submitting ? 'Saving...' : 'Deactivate'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
