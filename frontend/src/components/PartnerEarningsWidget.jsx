/**
 * Partner Earnings & Commissions Widget.
 * Shows lifetime earnings, approved, pending, and paid commissions with client-wise breakdown.
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { IndianRupee, TrendingUp, Clock, CheckCircle, ExternalLink, Calendar } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

export default function PartnerEarningsWidget({ onSelectClient }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailOpen, setDetailOpen] = useState(false);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/partner-earnings/my`, { headers: { Authorization: `Bearer ${token}` } });
      setData(r.data);
    } catch (_) {
      // graceful fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading || !data || data.deal_count === 0) {
    return null;
  }

  const { totals, lifetime_total, deal_count, line_items } = data;

  return (
    <>
      <Card
        className="p-5 mb-5 bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 border-emerald-200 cursor-pointer hover:shadow-md transition"
        data-testid="partner-earnings-widget"
        onClick={() => setDetailOpen(true)}
      >
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center shadow-inner">
              <IndianRupee className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">My Earnings & Commissions</h3>
              <p className="text-xs text-slate-500">Lifetime partner earnings & sales commission</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-3xl font-extrabold text-emerald-700" data-testid="partner-lifetime-total">{formatINR(lifetime_total)}</p>
            <p className="text-xs text-slate-500">across {deal_count} client{deal_count !== 1 ? 's' : ''}</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="bg-amber-50/90 p-2.5 rounded-lg flex items-center gap-2 border border-amber-100" data-testid="partner-pending">
            <Clock className="h-4 w-4 text-amber-600 shrink-0" />
            <div>
              <p className="text-amber-700 font-bold text-[11px]">Pending</p>
              <p className="font-bold text-slate-800">{formatINR(totals.pending)}</p>
            </div>
          </div>
          <div className="bg-leamss-teal-50/90 p-2.5 rounded-lg flex items-center gap-2 border border-leamss-teal-100" data-testid="partner-approved">
            <TrendingUp className="h-4 w-4 text-leamss-teal-600 shrink-0" />
            <div>
              <p className="text-leamss-teal-700 font-bold text-[11px]">Approved</p>
              <p className="font-bold text-slate-800">{formatINR(totals.approved)}</p>
            </div>
          </div>
          <div className="bg-emerald-50/90 p-2.5 rounded-lg flex items-center gap-2 border border-emerald-100" data-testid="partner-paid">
            <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
            <div>
              <p className="text-emerald-700 font-bold text-[11px]">Paid</p>
              <p className="font-bold text-slate-800">{formatINR(totals.paid)}</p>
            </div>
          </div>
          <div className="bg-white/80 p-2 rounded-lg flex items-center justify-center border border-emerald-100" data-testid="partner-recent-count">
            <p className="text-[11px] text-slate-600 text-center font-medium">Last {Math.min(line_items.length, 5)} entries below</p>
          </div>
        </div>

        {/* Preview list */}
        {line_items.length > 0 && (
          <div className="mt-3 pt-3 border-t border-emerald-200/80 space-y-1.5">
            {line_items.slice(0, 3).map((li, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs py-0.5" data-testid={`partner-earning-row-${idx}`}>
                <span className="truncate text-slate-700 font-medium">
                  {li.client_name} <span className="text-slate-400 font-normal text-[11px]">({li.pa_number})</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Badge className={`text-[10px] px-1.5 py-0 h-4 capitalize ${
                    li.status === 'paid' ? 'bg-emerald-100 text-emerald-800' :
                    li.status === 'approved' ? 'bg-leamss-teal-100 text-leamss-teal-800' :
                    'bg-amber-100 text-amber-800'
                  }`}>
                    {li.status}
                  </Badge>
                  <strong className="text-slate-800 ml-1">{formatINR(li.amount)}</strong>
                </span>
              </div>
            ))}
            <div className="text-[11px] text-emerald-700 font-medium text-center mt-2 pt-1 flex items-center justify-center gap-1 hover:underline">
              <ExternalLink className="h-3 w-3" /> Click to view full earnings & client-wise details
            </div>
          </div>
        )}
      </Card>

      {/* Detailed Modal */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl" data-testid="partner-detail-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <IndianRupee className="h-5 w-5 text-emerald-600" /> My Earnings & Commission Details
            </DialogTitle>
          </DialogHeader>

          <div className="max-h-[70vh] overflow-y-auto pr-1">
            <Card className="p-4 mb-4 bg-gradient-to-br from-emerald-50 to-leamss-teal-50 border-emerald-200">
              <div className="flex justify-between items-center flex-wrap gap-3">
                <div>
                  <p className="text-xs uppercase font-bold text-emerald-700">Lifetime Total</p>
                  <p className="text-3xl font-extrabold text-emerald-700">{formatINR(lifetime_total)}</p>
                  <p className="text-xs text-slate-500 mt-0.5">across {deal_count} client{deal_count !== 1 ? 's' : ''}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-white/80 p-2.5 rounded text-center border border-amber-100"><p className="text-amber-700 font-bold">Pending</p><p className="font-bold">{formatINR(totals.pending)}</p></div>
                  <div className="bg-white/80 p-2.5 rounded text-center border border-leamss-teal-100"><p className="text-leamss-teal-700 font-bold">Approved</p><p className="font-bold">{formatINR(totals.approved)}</p></div>
                  <div className="bg-white/80 p-2.5 rounded text-center border border-emerald-100"><p className="text-emerald-700 font-bold">Paid</p><p className="font-bold">{formatINR(totals.paid)}</p></div>
                </div>
              </div>
            </Card>

            <div className="space-y-2">
              {line_items.map((li, idx) => (
                <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200 flex items-center justify-between text-xs hover:border-emerald-300 transition">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-slate-800">{li.client_name}</p>
                      <Badge variant="outline" className="text-[10px] text-slate-500 font-mono">{li.pa_number}</Badge>
                      <span className="text-[11px] text-slate-400">· {li.label}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1">
                      {li.approved_at && <span>Approved: {new Date(li.approved_at).toLocaleDateString()}</span>}
                      {li.paid_at && <span>Paid: {new Date(li.paid_at).toLocaleDateString()}</span>}
                      {li.payment_reference && <span className="font-mono text-emerald-700">Ref: {li.payment_reference}</span>}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-slate-800">{formatINR(li.amount)}</p>
                    <Badge className={`text-[10px] px-1.5 py-0 mt-1 capitalize ${
                      li.status === 'paid' ? 'bg-emerald-100 text-emerald-800' :
                      li.status === 'approved' ? 'bg-leamss-teal-100 text-leamss-teal-800' :
                      'bg-amber-100 text-amber-800'
                    }`}>
                      {li.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}