import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { ArrowLeft, CheckSquare, CheckCircle2, XCircle, AlertTriangle, Inbox } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LeaveApprovals() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('l1'); // l1 | final
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [decideItem, setDecideItem] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const endpoint = tab === 'l1' ? '/leaves/inbox' : '/leaves/inbox-final';
      const r = await axios.get(`${API}${endpoint}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setItems(r.data || []);
    } catch (e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [tab]);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="leave-approvals-page">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/portal/welcome')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Back
          </Button>
          <h1 className="font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-purple-600" /> Leave Approvals
          </h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-4">
        {/* Tabs */}
        <div className="flex gap-2">
          <Button variant={tab === 'l1' ? 'default' : 'outline'} onClick={() => setTab('l1')} size="sm" data-testid="tab-l1">
            L1 Manager Inbox
          </Button>
          <Button variant={tab === 'final' ? 'default' : 'outline'} onClick={() => setTab('final')} size="sm" data-testid="tab-final">
            Final Approver Inbox
          </Button>
        </div>

        {loading ? (
          <p className="text-slate-500 text-sm">Loading...</p>
        ) : items.length === 0 ? (
          <Card className="p-10 text-center" data-testid="empty-state">
            <Inbox className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No pending {tab === 'l1' ? 'L1' : 'final'} approvals</p>
          </Card>
        ) : (
          <div className="space-y-3" data-testid="approval-list">
            {items.map((r) => (
              <Card key={r.id} className="p-4" data-testid={`approval-${r.id}`}>
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-[250px]">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-800">{r.user_name}</span>
                      <Badge variant="outline" className="text-[10px]">{r.user_employee_id || r.department}</Badge>
                      <Badge className="bg-indigo-100 text-indigo-800 text-[10px]">{r.leave_type_name}</Badge>
                      {r.is_sandwich && (
                        <Badge className="bg-amber-100 text-amber-800 text-[10px] flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" /> Sandwich
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 mt-1">
                      📅 {r.from_date} → {r.to_date} · <strong>{r.total_days} day{r.total_days > 1 ? 's' : ''}</strong>
                      {r.working_days !== r.total_days && ` (${r.working_days} working + ${r.weekend_included} weekend)`}
                    </p>
                    <p className="text-xs text-slate-700 mt-1.5 italic">"{r.reason}"</p>
                    {r.warnings?.length > 0 && (
                      <div className="mt-2 space-y-0.5">
                        {r.warnings.map((w, i) => (
                          <p key={i} className="text-[10px] text-amber-700">{w}</p>
                        ))}
                      </div>
                    )}
                    <p className="text-[10px] text-slate-400 mt-1.5">
                      Applied {new Date(r.applied_at || r.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => setDecideItem({ ...r, decision: 'approved' })} data-testid={`approve-${r.id}`}>
                      <CheckCircle2 className="h-4 w-4 mr-1" /> Approve
                    </Button>
                    <Button size="sm" variant="outline" className="text-rose-600 border-rose-300" onClick={() => setDecideItem({ ...r, decision: 'rejected' })} data-testid={`reject-${r.id}`}>
                      <XCircle className="h-4 w-4 mr-1" /> Reject
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>

      {decideItem && (
        <DecideModal
          item={decideItem}
          onClose={() => setDecideItem(null)}
          onSuccess={() => { setDecideItem(null); load(); }}
        />
      )}
    </div>
  );
}


function DecideModal({ item, onClose, onSuccess }) {
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (item.decision === 'rejected' && note.length < 5) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/leaves/${item.id}/decide`, {
        decision: item.decision,
        note,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Leave ${r.data.new_status}`);
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Decision failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <Card className="max-w-md w-full p-5 bg-white" onClick={(e) => e.stopPropagation()} data-testid="decide-modal">
        <h2 className="text-lg font-bold text-slate-900 mb-3">
          {item.decision === 'approved' ? '✅ Approve Leave' : '❌ Reject Leave'}
        </h2>
        <div className="text-sm text-slate-700 bg-slate-50 p-3 rounded mb-3">
          <p><strong>{item.user_name}</strong> · {item.leave_type_name}</p>
          <p className="text-xs text-slate-600 mt-1">
            {item.from_date} → {item.to_date} · {item.total_days} day(s)
          </p>
          {item.is_sandwich && (
            <p className="text-xs text-amber-700 mt-1">🥪 Sandwich leave — {item.weekend_included} weekend day(s) included</p>
          )}
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-700 uppercase">
            {item.decision === 'rejected' ? 'Rejection Reason (required)' : 'Note (optional)'}
          </label>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="w-full mt-1 px-3 py-2 border rounded text-sm" data-testid="decide-note" />
        </div>
        <div className="flex gap-2 justify-end pt-3">
          <Button variant="outline" onClick={onClose} data-testid="decide-cancel">Cancel</Button>
          <Button
            onClick={submit}
            disabled={submitting}
            className={item.decision === 'approved' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'}
            data-testid="decide-confirm"
          >
            {submitting ? 'Submitting...' : `Confirm ${item.decision === 'approved' ? 'Approval' : 'Rejection'}`}
          </Button>
        </div>
      </Card>
    </div>
  );
}
