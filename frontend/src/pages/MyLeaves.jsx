import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  ArrowLeft, Calendar, Plus, AlertTriangle, CheckCircle2, XCircle,
  Clock as ClockIcon, Hourglass,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_META = {
  pending_l1:    { label: 'Pending Manager', color: 'bg-amber-100 text-amber-800', icon: Hourglass },
  pending_final: { label: 'Pending Final',   color: 'bg-orange-100 text-orange-800', icon: Hourglass },
  approved:      { label: 'Approved',        color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
  rejected:      { label: 'Rejected',        color: 'bg-rose-100 text-rose-800', icon: XCircle },
  cancelled:     { label: 'Cancelled',       color: 'bg-slate-100 text-slate-700', icon: XCircle },
};

export default function MyLeaves() {
  const navigate = useNavigate();
  const [balances, setBalances] = useState([]);
  const [history, setHistory] = useState([]);
  const [showApply, setShowApply] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [bal, hist] = await Promise.all([
        axios.get(`${API}/leaves/my-balance`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/leaves/my-history?limit=20`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setBalances(bal.data.balances || []);
      setHistory(hist.data || []);
    } catch (e) {
      toast.error('Failed to load leaves');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this leave request?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/leaves/${id}/cancel`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success('Leave request cancelled');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Cancel failed');
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading leaves...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="my-leaves-page">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/portal/welcome')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Back
          </Button>
          <h1 className="font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-indigo-600" /> My Leaves
          </h1>
        </div>
        <Button onClick={() => setShowApply(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="apply-leave-btn">
          <Plus className="h-4 w-4 mr-1.5" /> Apply Leave
        </Button>
      </header>

      <main className="max-w-6xl mx-auto p-6 space-y-5">
        {/* Balance cards */}
        <Card className="p-5" data-testid="balance-section">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide mb-3">Leave Balances (2026)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {balances.map((b) => {
              const pct = b.annual_quota > 0 ? (b.available / b.annual_quota) * 100 : 0;
              return (
                <Card key={b.leave_type_key} className="p-3 border" style={{ borderLeftColor: b.color, borderLeftWidth: '4px' }} data-testid={`balance-${b.leave_type_key}`}>
                  <div className="flex items-start justify-between mb-1">
                    <p className="text-xs font-bold text-slate-700">{b.leave_type_name}</p>
                    <Badge className="text-[10px]" style={{ background: `${b.color}20`, color: b.color }}>{b.short_code}</Badge>
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold tabular-nums" style={{ color: b.color }}>{b.available}</span>
                    <span className="text-xs text-slate-400">/ {b.annual_quota || '—'}</span>
                  </div>
                  <div className="h-1 bg-slate-200 rounded overflow-hidden mt-1.5">
                    <div className="h-full transition-all" style={{ width: `${Math.min(100, pct)}%`, background: b.color }} />
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1.5 space-y-0.5">
                    <p>Used: {b.used}</p>
                    {b.monthly_cap > 0 && (
                      <p className={b.used_this_month >= b.monthly_cap ? 'text-rose-600 font-semibold' : ''}>
                        Monthly cap: {b.used_this_month}/{b.monthly_cap}
                      </p>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </Card>

        {/* History */}
        <Card className="p-5" data-testid="history-section">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide mb-3">My Leave History</h2>
          {history.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No leave requests yet.</p>
          ) : (
            <div className="space-y-2">
              {history.map((r) => {
                const meta = STATUS_META[r.status] || { label: r.status, color: 'bg-slate-100 text-slate-700', icon: ClockIcon };
                const Icon = meta.icon;
                return (
                  <Card key={r.id} className="p-3" data-testid={`history-item-${r.id}`}>
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="flex-1 min-w-[200px]">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge className={meta.color}><Icon className="h-3 w-3 mr-1" />{meta.label}</Badge>
                          <span className="text-sm font-semibold text-slate-800">{r.leave_type_name}</span>
                          {r.is_sandwich && <Badge className="bg-amber-100 text-amber-800 text-[10px]">🥪 Sandwich</Badge>}
                        </div>
                        <p className="text-xs text-slate-600 mt-1">
                          📅 {r.from_date} → {r.to_date} · <strong>{r.total_days} day{r.total_days > 1 ? 's' : ''}</strong>
                          {r.working_days !== r.total_days && ` (${r.working_days} working)`}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">"{r.reason}"</p>
                        {r.rejection_reason && (
                          <p className="text-xs text-rose-700 mt-1">Reason: {r.rejection_reason}</p>
                        )}
                        <p className="text-[10px] text-slate-400 mt-1">
                          Applied {new Date(r.applied_at || r.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                          {r.manager_name && ` · L1: ${r.manager_name}`}
                          {r.final_approver_name && r.final_approver_name !== r.manager_name && ` · Final: ${r.final_approver_name}`}
                        </p>
                      </div>
                      {(r.status === 'pending_l1' || r.status === 'pending_final') && (
                        <Button variant="outline" size="sm" onClick={() => handleCancel(r.id)} className="text-rose-600" data-testid={`cancel-${r.id}`}>
                          Cancel
                        </Button>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </Card>
      </main>

      {showApply && (
        <ApplyLeaveModal
          balances={balances}
          onClose={() => setShowApply(false)}
          onSuccess={() => { setShowApply(false); load(); }}
        />
      )}
    </div>
  );
}


function ApplyLeaveModal({ balances, onClose, onSuccess }) {
  const [leaveType, setLeaveType] = useState('casual_leave');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [reason, setReason] = useState('');
  const [validation, setValidation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [acceptSandwich, setAcceptSandwich] = useState(false);

  // Live validation
  useEffect(() => {
    if (!fromDate || !toDate || !leaveType) {
      setValidation(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.post(`${API}/leaves/validate`, {
          leave_type_key: leaveType, from_date: fromDate, to_date: toDate,
        }, { headers: { Authorization: `Bearer ${token}` } });
        setValidation(r.data);
      } catch (e) {
        setValidation(null);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [fromDate, toDate, leaveType]);

  const submit = async () => {
    if (reason.length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    if (!validation?.ok) {
      toast.error('Fix validation errors first');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/leaves/apply`, {
        leave_type_key: leaveType,
        from_date: fromDate,
        to_date: toDate,
        reason,
        accept_sandwich: acceptSandwich,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`✅ Leave applied! ${validation.total_days} day(s) — pending approval`);
      onSuccess();
    } catch (e) {
      const detail = e.response?.data?.detail;
      if (typeof detail === 'object') {
        if (detail.requires_acknowledgement) {
          toast.warning('Please tick the sandwich leave checkbox to confirm');
        } else if (detail.errors) {
          toast.error(detail.errors.join(' · '));
        } else {
          toast.error(detail.message || 'Application failed');
        }
      } else {
        toast.error(detail || 'Failed to apply leave');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 overflow-y-auto" onClick={onClose}>
      <Card className="max-w-lg w-full p-5 bg-white my-8" onClick={(e) => e.stopPropagation()} data-testid="apply-leave-modal">
        <h2 className="text-lg font-bold text-slate-900 mb-3">Apply for Leave</h2>

        <div className="space-y-3">
          {/* Leave type */}
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">Leave Type</label>
            <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="apply-leave-type">
              {balances.map((b) => (
                <option key={b.leave_type_key} value={b.leave_type_key}>
                  {b.leave_type_name} ({b.short_code}) — {b.available} available
                  {b.monthly_cap > 0 && ` · monthly cap: ${b.monthly_cap}/month`}
                </option>
              ))}
            </select>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase">From Date</label>
              <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="apply-from-date" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase">To Date</label>
              <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="apply-to-date" />
            </div>
          </div>

          {/* Live validation preview */}
          {validation && (
            <div className="rounded p-3 bg-slate-50 border" data-testid="validation-preview">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-bold text-slate-700">Days Breakdown</p>
                <span className={`text-xs font-semibold ${validation.ok ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {validation.ok ? '✅ Eligible' : '❌ Blocked'}
                </span>
              </div>
              <div className="text-xs text-slate-700 grid grid-cols-3 gap-2">
                <div>
                  <p className="text-[10px] uppercase text-slate-400">Total</p>
                  <p className="font-bold">{validation.total_days} days</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-400">Working</p>
                  <p className="font-bold">{validation.working_days}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-400">Weekend</p>
                  <p className="font-bold">{validation.days_breakdown?.weekend_included || 0}</p>
                </div>
              </div>
              {validation.days_breakdown?.is_sandwich && (
                <div className="mt-2 p-2 bg-amber-100 border border-amber-300 rounded text-xs text-amber-900" data-testid="sandwich-warning">
                  <p className="font-bold">🥪 Sandwich Leave Detected</p>
                  <p className="text-[11px]">Total {validation.total_days} days will be deducted including weekend per company policy.</p>
                </div>
              )}
              {validation.errors?.map((err, i) => (
                <p key={i} className="text-xs text-rose-700 mt-1 font-semibold" data-testid={`error-${i}`}>{err}</p>
              ))}
              {validation.warnings?.map((w, i) => (
                <p key={i} className="text-xs text-amber-700 mt-1" data-testid={`warning-${i}`}>{w}</p>
              ))}
            </div>
          )}

          {/* Sandwich acknowledgement */}
          {validation?.days_breakdown?.is_sandwich && (
            <label className="flex items-start gap-2 cursor-pointer">
              <input type="checkbox" checked={acceptSandwich} onChange={(e) => setAcceptSandwich(e.target.checked)} className="mt-1" data-testid="accept-sandwich-check" />
              <span className="text-xs text-slate-700">
                I acknowledge this is a sandwich leave and {validation.total_days} days (including weekend) will be deducted from my balance.
              </span>
            </label>
          )}

          {/* Reason */}
          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase">
              Reason <span className="text-slate-400">(min 10 chars)</span>
            </label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full mt-1 px-3 py-2 border rounded text-sm" placeholder="Why are you taking this leave?" data-testid="apply-reason" />
            <p className="text-[10px] text-slate-400 mt-0.5">{reason.length}/10 chars</p>
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose} data-testid="apply-cancel">Cancel</Button>
            <Button
              onClick={submit}
              disabled={submitting || !validation?.ok || reason.length < 10 || (validation?.days_breakdown?.is_sandwich && !acceptSandwich)}
              data-testid="apply-submit"
            >
              {submitting ? 'Submitting...' : 'Submit Application'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
