import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Percent, CheckCircle2, X, Clock, RefreshCw, AlertCircle, ShieldCheck } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LEVEL_COLOR = {
  auto: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  manager: 'bg-amber-100 text-amber-700 border-amber-200',
  admin: 'bg-rose-100 text-rose-700 border-rose-200',
};

export default function DiscountApprovalInbox() {
  const [data, setData] = useState({ items: [], stats: {} });
  const [loading, setLoading] = useState(false);
  const [actingOn, setActingOn] = useState(null);
  const [note, setNote] = useState('');

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/sales-team/discount-requests?status=pending`, auth());
      setData(r.data);
    } catch (e) { toast.error('Failed to load'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const decide = async (id, decision) => {
    try {
      await axios.post(`${API}/sales-team/discount-requests/${id}/decide`,
        { decision, note: note || null }, auth());
      toast.success(`Discount ${decision === 'approve' ? 'approved' : 'rejected'}`);
      setActingOn(null);
      setNote('');
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  return (
    <Card className="p-5 border-l-4 border-l-rose-500" data-testid="discount-approval-inbox">
      <div className="flex items-center justify-between gap-2 mb-4 flex-wrap">
        <div className="flex items-center gap-2.5">
          <Percent className="h-5 w-5 text-rose-600" />
          <div>
            <p className="font-semibold text-slate-800">Discount Approval Inbox</p>
            <p className="text-[11px] text-slate-500">Sales-rep discount requests above auto-approve cap</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-amber-100 text-amber-700 border-amber-200">{data.stats.pending || 0} pending</Badge>
          <Button size="sm" variant="outline" onClick={load} disabled={loading} data-testid="dai-refresh">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {data.items.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">
          <ShieldCheck className="h-10 w-10 mx-auto mb-2 text-emerald-300" />
          {loading ? 'Loading…' : 'No pending discount requests. Margins are protected. ✓'}
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map(req => (
            <div key={req.id} className="border rounded-lg p-3 hover:bg-slate-50" data-testid={`disc-req-${req.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-mono text-[10px] text-slate-500">{req.pa_number}</span>
                    <Badge className={`${LEVEL_COLOR[req.level_required]} text-[10px] border`}>
                      Needs {req.level_required} approval
                    </Badge>
                    <Badge className="bg-slate-100 text-slate-700 border-slate-200 text-[10px]">
                      {req.requester_employment_type === 'employee' ? '🏢' : '🌍'} {req.requester_name}
                    </Badge>
                  </div>
                  <p className="font-semibold text-slate-800 text-sm">{req.client_name}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs">
                    <span className="text-slate-500">Base: <strong className="text-slate-700">₹{req.base_fee.toLocaleString('en-IN')}</strong></span>
                    <span className="text-rose-600 font-semibold">−{req.discount_pct}%</span>
                    <span className="text-emerald-700">Final: <strong>₹{req.final_amount.toLocaleString('en-IN')}</strong></span>
                  </div>
                  {req.reason && <p className="text-[11px] text-slate-500 italic mt-1">💬 {req.reason}</p>}
                </div>
                {actingOn === req.id ? (
                  <div className="flex flex-col gap-2 w-full sm:w-auto" data-testid="disc-decision-row">
                    <Input value={note} onChange={e => setNote(e.target.value)} placeholder="Decision note (optional)" className="h-7 text-xs" />
                    <div className="flex gap-1">
                      <Button size="sm" onClick={() => decide(req.id, 'approve')} className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-7" data-testid="disc-confirm-approve">
                        <CheckCircle2 className="h-3 w-3 mr-1" /> Approve
                      </Button>
                      <Button size="sm" onClick={() => decide(req.id, 'reject')} className="bg-rose-600 hover:bg-rose-700 text-white text-xs h-7" data-testid="disc-confirm-reject">
                        <X className="h-3 w-3 mr-1" /> Reject
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => { setActingOn(null); setNote(''); }} className="text-xs h-7">Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" onClick={() => setActingOn(req.id)} className="text-xs h-7 border-emerald-300 text-emerald-700 hover:bg-emerald-50" data-testid={`disc-action-${req.id}`}>
                      Decide
                    </Button>
                  </div>
                )}
              </div>
              <div className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400">
                <Clock className="h-3 w-3" /> {new Date(req.created_at).toLocaleString('en-IN')}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
