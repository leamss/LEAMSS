/**
 * Phase 4C.5 — Case Manager Earnings Widget.
 * Read-only widget that shows up at top of CM dashboard. Does NOT change workflow.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { IndianRupee, TrendingUp, Clock, CheckCircle, ChevronRight, ExternalLink } from 'lucide-react';

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
  const [detailOpen, setDetailOpen] = useState(false);

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
    <>
    <Card
      className="p-5 mb-4 bg-gradient-to-br from-emerald-50 via-blue-50 to-leamss-teal-50 border-emerald-200 cursor-pointer hover:shadow-md transition"
      data-testid="cm-earnings-widget"
      onClick={() => setDetailOpen(true)}
    >
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
        <div className="bg-leamss-teal-50 p-2 rounded flex items-center gap-2" data-testid="cm-approved">
          <TrendingUp className="h-3.5 w-3.5 text-leamss-teal-600" />
          <div>
            <p className="text-leamss-teal-700 font-bold">Approved</p>
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
                <Badge className={`text-[9px] ${li.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : li.status === 'approved' ? 'bg-leamss-teal-100 text-leamss-teal-700' : 'bg-amber-100 text-amber-700'}`}>{li.status}</Badge>
                <strong className="text-slate-800 ml-1">{formatINR(li.amount)}</strong>
              </span>
            </div>
          ))}
          <div className="text-[10px] text-emerald-600 text-center mt-2 flex items-center justify-center gap-1">
            <ExternalLink className="h-2.5 w-2.5" />Click to see all earnings & client-wise breakdown
          </div>
        </div>
      )}
    </Card>

    {/* Phase 4C — Click-through detail dialog (NO revenue/sales values exposed; only CM earnings) */}
    <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
      <DialogContent className="max-w-3xl" data-testid="cm-detail-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <IndianRupee className="h-5 w-5 text-emerald-600" />My Earnings — Detailed View
          </DialogTitle>
        </DialogHeader>
        <div className="max-h-[70vh] overflow-y-auto pr-2">
          <Card className="p-4 mb-4 bg-gradient-to-br from-emerald-50 to-leamss-teal-50">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs uppercase font-bold text-emerald-700">Lifetime Total</p>
                <p className="text-3xl font-extrabold text-emerald-700" data-testid="cm-detail-lifetime">{formatINR(lifetime_total)}</p>
                <p className="text-xs text-slate-500 mt-0.5">across {deal_count} client{deal_count !== 1 ? 's' : ''}</p>
              </div>
              <div className="text-right grid grid-cols-3 gap-2 text-xs">
                <div className="bg-white/60 p-2 rounded"><p className="text-amber-700 font-bold">Pending</p><p className="font-bold">{formatINR(totals.pending)}</p></div>
                <div className="bg-white/60 p-2 rounded"><p className="text-leamss-teal-700 font-bold">Approved</p><p className="font-bold">{formatINR(totals.approved)}</p></div>
                <div className="bg-white/60 p-2 rounded"><p className="text-emerald-700 font-bold">Paid</p><p className="font-bold">{formatINR(totals.paid)}</p></div>
              </div>
            </div>
          </Card>

          <h3 className="text-sm font-bold text-slate-700 mb-2">Client-wise Breakdown</h3>
          {line_items.length === 0 ? (
            <p className="text-sm italic text-slate-400 text-center py-8">No earnings yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-[10px] uppercase text-slate-500">
                  <th className="text-left py-2">Client</th>
                  <th className="text-left py-2">PA #</th>
                  <th className="text-left py-2">Role</th>
                  <th className="text-right py-2">My Fee</th>
                  <th className="text-center py-2">Status</th>
                  <th className="text-left py-2">Paid On</th>
                  <th className="text-left py-2">Reference</th>
                </tr>
              </thead>
              <tbody>
                {line_items.map((li, i) => (
                  <tr key={i} className="border-b last:border-b-0 hover:bg-slate-50" data-testid={`cm-detail-row-${i}`}>
                    <td className="py-2 font-medium">{li.client_name}</td>
                    <td className="py-2 text-[11px] text-slate-500 font-mono">{li.pa_number}</td>
                    <td className="py-2 text-xs">{li.label}</td>
                    <td className="py-2 text-right font-bold text-emerald-700">{formatINR(li.amount)}</td>
                    <td className="py-2 text-center">
                      <Badge className={`text-[10px] ${li.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : li.status === 'approved' ? 'bg-leamss-teal-100 text-leamss-teal-700' : 'bg-amber-100 text-amber-700'}`}>{li.status}</Badge>
                    </td>
                    <td className="py-2 text-[11px] text-slate-500">{li.paid_at ? new Date(li.paid_at).toLocaleDateString() : '—'}</td>
                    <td className="py-2 text-[11px] text-slate-500 font-mono">{li.payment_reference || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="text-[11px] text-slate-400 italic text-center mt-4">
            🔒 Only your case-manager earnings are shown here. Client revenue and sales commissions are not exposed to you.
          </p>
        </div>
        <div className="flex justify-end pt-2">
          <Button variant="outline" onClick={() => setDetailOpen(false)} data-testid="close-cm-detail">Close</Button>
        </div>
      </DialogContent>
    </Dialog>
    </>
  );
}
