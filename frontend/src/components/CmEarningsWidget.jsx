/**
 * Phase 4C.5 — Case Manager Earnings Widget.
 * Read-only widget that shows up at top of CM dashboard. Does NOT change workflow.
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { IndianRupee, TrendingUp, Clock, CheckCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};


export default function CmEarningsWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/cm-earnings/my`, { headers: { Authorization: `Bearer ${token}` } });
        if (!cancelled) setData(r.data);
      } catch (_) {
        // Silently fail — widget hides
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading || !data || data.deal_count === 0) {
    // Hide widget if no earnings
    return null;
  }

  const { totals, lifetime_total, deal_count, line_items } = data;

  return (
    <Card className="p-5 mb-4 bg-gradient-to-br from-emerald-50 via-blue-50 to-indigo-50 border-emerald-200" data-testid="cm-earnings-widget">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
            <IndianRupee className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-800">My Earnings</h3>
            <p className="text-xs text-slate-500">Lifetime case manager fees</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-extrabold text-emerald-700" data-testid="lifetime-total">{formatINR(lifetime_total)}</p>
          <p className="text-xs text-slate-500">across {deal_count} case{deal_count !== 1 ? 's' : ''}</p>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="bg-amber-50 p-2 rounded flex items-center gap-2" data-testid="cm-pending">
          <Clock className="h-3.5 w-3.5 text-amber-600" />
          <div>
            <p className="text-amber-700 font-bold">Pending</p>
            <p className="font-bold text-slate-800">{formatINR(totals.pending)}</p>
          </div>
        </div>
        <div className="bg-indigo-50 p-2 rounded flex items-center gap-2" data-testid="cm-approved">
          <TrendingUp className="h-3.5 w-3.5 text-indigo-600" />
          <div>
            <p className="text-indigo-700 font-bold">Approved</p>
            <p className="font-bold text-slate-800">{formatINR(totals.approved)}</p>
          </div>
        </div>
        <div className="bg-emerald-50 p-2 rounded flex items-center gap-2" data-testid="cm-paid">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
          <div>
            <p className="text-emerald-700 font-bold">Paid</p>
            <p className="font-bold text-slate-800">{formatINR(totals.paid)}</p>
          </div>
        </div>
        <div className="bg-slate-100 p-2 rounded flex items-center justify-center" data-testid="cm-recent-count">
          <p className="text-[11px] text-slate-600">Last {Math.min(line_items.length, 5)} entries available below</p>
        </div>
      </div>
      {/* Tiny preview of last 3 cases */}
      {line_items.length > 0 && (
        <div className="mt-3 pt-3 border-t border-emerald-200 space-y-1">
          {line_items.slice(0, 3).map((li, idx) => (
            <div key={idx} className="flex justify-between text-[11px]" data-testid={`cm-earning-row-${idx}`}>
              <span className="truncate text-slate-600">{li.client_name} ({li.pa_number})</span>
              <span className="flex items-center gap-1">
                <Badge className={`text-[9px] ${li.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : li.status === 'approved' ? 'bg-indigo-100 text-indigo-700' : 'bg-amber-100 text-amber-700'}`}>{li.status}</Badge>
                <strong className="text-slate-800 ml-1">{formatINR(li.amount)}</strong>
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
