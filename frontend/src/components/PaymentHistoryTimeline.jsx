import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Clock, CheckCircle, CreditCard, FileText, Package, Send, IndianRupee, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const KIND_ICON = {
  pre_assessment_fee: CreditCard,
  proposal_sent: Send,
  main_fee_paid: CheckCircle,
  milestone: Package,
  invoice: FileText,
};

const KIND_COLOR = {
  pre_assessment_fee: 'text-blue-600 bg-blue-50',
  proposal_sent: 'text-amber-700 bg-amber-50',
  main_fee_paid: 'text-emerald-600 bg-emerald-50',
  milestone: 'text-indigo-600 bg-indigo-50',
  invoice: 'text-slate-600 bg-slate-50',
};

/**
 * PaymentHistoryTimeline
 *  - scope: 'pa' | 'case'
 *  - id: pre_assessment_id or case_id
 */
export default function PaymentHistoryTimeline({ scope = 'pa', id, compact = false, initialData = null }) {
  const [data, setData] = useState(initialData || { events: [], totals: { received: 0, pending: 0 } });
  const [loading, setLoading] = useState(!initialData);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      const r = await axios.get(`${API}/payment-history/${scope}/${id}`, getAuth());
      setData(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, [scope, id]);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      setLoading(false);
    } else {
      load();
    }
  }, [initialData, load]);

  if (loading) {
    return <div className="text-xs text-slate-400 flex items-center gap-2"><RefreshCw className="h-3 w-3 animate-spin" /> Loading timeline…</div>;
  }

  if (!data.events || data.events.length === 0) {
    return <p className="text-xs text-slate-400 italic">No payment history yet.</p>;
  }

  return (
    <div className="space-y-3" data-testid="payment-history-timeline">
      {/* Totals */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
          <p className="text-[10px] uppercase tracking-wide text-emerald-700 font-semibold">Received</p>
          <p className="text-lg font-bold text-emerald-800 flex items-center"><IndianRupee className="h-3.5 w-3.5" />{(data.totals.received || 0).toLocaleString('en-IN')}</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5">
          <p className="text-[10px] uppercase tracking-wide text-amber-700 font-semibold">Pending</p>
          <p className="text-lg font-bold text-amber-800 flex items-center"><IndianRupee className="h-3.5 w-3.5" />{(data.totals.pending || 0).toLocaleString('en-IN')}</p>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative pl-4 space-y-2 before:content-[''] before:absolute before:left-[7px] before:top-1 before:bottom-1 before:w-px before:bg-slate-200">
        {data.events.slice(0, compact ? 5 : 50).map((e, i) => {
          const Icon = KIND_ICON[e.kind] || Clock;
          const color = KIND_COLOR[e.kind] || 'text-slate-600 bg-slate-50';
          const dt = e.ts ? new Date(e.ts).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
          return (
            <div key={i} className="relative" data-testid={`timeline-event-${i}`}>
              <div className={`absolute -left-[14px] top-1 h-4 w-4 rounded-full flex items-center justify-center ${color}`}>
                <Icon className="h-2.5 w-2.5" />
              </div>
              <div className="bg-white border border-slate-200 rounded-md px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-slate-800">{e.label}</p>
                  {e.amount > 0 && (
                    <span className={`text-xs font-bold ${e.direction === 'in' ? 'text-emerald-700' : e.direction === 'pending' ? 'text-amber-700' : 'text-slate-500'}`}>
                      {e.direction === 'in' ? '+ ' : e.direction === 'pending' ? '~ ' : ''}₹{(e.amount || 0).toLocaleString('en-IN')}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">{dt}</p>
                {e.meta?.reference && <p className="text-[10px] text-slate-500">Ref: {e.meta.reference}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
