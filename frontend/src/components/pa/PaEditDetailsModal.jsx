import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Edit3, X, Save, AlertCircle, History, ShieldCheck, FileText, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Phase 9.9 — Helpers for the audit timeline rendering
function actionTone(action) {
  if (!action) return '#cbd5e1';
  if (action.includes('signed')) return '#10b981';
  if (action.includes('edited') || action.includes('updated')) return '#6366f1';
  if (action.includes('approved') || action.includes('proposal')) return '#0ea5e9';
  if (action.includes('rejected') || action.includes('refund')) return '#ef4444';
  if (action.includes('stage')) return '#f59e0b';
  return '#94a3b8';
}
function humanAction(action) {
  if (!action) return 'Activity';
  return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
function formatWhen(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

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
  // Phase 9.9 — derive initial form from pa prop using useState initializer
  // (modal is remounted on each open, so this is safe + avoids set-state-in-effect)
  const [form, setForm] = useState(() => ({
    client_name: pa?.client_name || '',
    client_email: pa?.client_email || '',
    client_mobile: pa?.client_mobile || '',
    client_age: pa?.client_age || '',
    education: pa?.education || '',
    work_experience: pa?.work_experience || '',
    country: pa?.country || '',
    service_type: pa?.service_type || '',
    notes: pa?.notes || '',
  }));
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('details');  // 'details' | 'history'
  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const locked = pa?.stage === 'case_created';

  const loadHistory = async () => {
    if (!pa?.id) return;
    setHistoryLoading(true);
    try {
      const r = await axios.get(`${API}/pre-assessment/${pa.id}/edit-history`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setHistory(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not load history');
      setHistory({ error: true });
    }
    setHistoryLoading(false);
  };

  const switchTab = (tabId) => {
    setActiveTab(tabId);
    if (tabId === 'history' && !history && !historyLoading) loadHistory();
  };

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

        {/* Phase 9.9 — Tabs: Details + Edit History */}
        <div className="border-b bg-slate-50 flex" data-testid="pa-edit-tabs">
          {[
            { id: 'details', label: 'Details', icon: Edit3 },
            { id: 'history', label: 'Edit History', icon: History },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => switchTab(t.id)}
              className="px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors -mb-px"
              style={{
                borderColor: activeTab === t.id ? '#4f46e5' : 'transparent',
                color:       activeTab === t.id ? '#3730a3' : '#94a3b8',
              }}
              data-testid={`pa-edit-tab-${t.id}`}
            >
              <t.icon className="h-3.5 w-3.5" />{t.label}
            </button>
          ))}
        </div>

        {activeTab === 'details' && (
        <div className="flex-1 overflow-y-auto p-5 space-y-3" data-testid="pa-edit-details-panel">
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
        )}

        {activeTab === 'history' && (
          <div className="flex-1 overflow-y-auto p-5 space-y-3" data-testid="pa-edit-history-panel">
            {historyLoading && (
              <div className="p-8 text-center text-sm text-slate-500 flex flex-col items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />Loading audit timeline…
              </div>
            )}
            {!historyLoading && history?.error && (
              <p className="text-sm text-rose-600">Failed to load history.</p>
            )}
            {!historyLoading && history && !history.error && (
              <>
                <div className="bg-indigo-50 border border-indigo-200 rounded p-2.5 text-xs text-indigo-900 flex items-center gap-2">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Total <strong>{history.total_entries}</strong> auditable events for {history.pa_number || history.client_name}
                </div>
                {history.entries?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic text-center py-6">No audit entries yet.</p>
                ) : (
                  <ol className="relative border-l border-slate-200 ml-2 space-y-3" data-testid="pa-history-timeline">
                    {history.entries.map((e, i) => (
                      <li key={i} className="ml-4" data-testid={`history-entry-${i}`}>
                        <div className="absolute -left-1.5 w-3 h-3 rounded-full"
                             style={{ background: actionTone(e.action) }} />
                        <p className="text-[10px] text-slate-400">{formatWhen(e.created_at)}</p>
                        <p className="text-xs font-bold text-slate-800 mt-0.5 flex items-center gap-1">
                          <FileText className="h-3 w-3 text-slate-400" />
                          {humanAction(e.action)}
                          {e.action === 'agreement_signed' && e.details?.biometric_captured && (
                            <span className="ml-1 text-[9px] bg-emerald-100 text-emerald-700 px-1 rounded">🔒 biometric</span>
                          )}
                        </p>
                        {e.user_name && (
                          <p className="text-[11px] text-slate-500">by <code className="bg-slate-100 px-1 rounded">{e.user_name}</code></p>
                        )}
                        {/* Detail rendering */}
                        {e.details?.changes && Array.isArray(e.details.changes) && (
                          <div className="mt-1 space-y-0.5">
                            {e.details.changes.map((ch, j) => (
                              <div key={j} className="text-[11px] flex items-center gap-1 flex-wrap" data-testid={`history-change-${j}`}>
                                <span className="font-mono bg-slate-100 px-1 rounded text-slate-600">{ch.field}</span>
                                <span className="text-rose-500 line-through max-w-[200px] truncate">{String(ch.from ?? '∅')}</span>
                                <span className="text-slate-400">→</span>
                                <span className="text-emerald-600 max-w-[200px] truncate">{String(ch.to ?? '∅')}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {e.details?.ip_address && (
                          <p className="text-[10px] text-slate-400 mt-0.5">📍 IP {e.details.ip_address}</p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </>
            )}
          </div>
        )}

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
