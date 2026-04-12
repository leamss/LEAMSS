import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  TrendingUp, DollarSign, Users, Briefcase, RotateCcw,
  Loader2, BarChart3, CreditCard, ArrowUpRight, ArrowDownRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RevenueDashboard = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeBreakdown, setActiveBreakdown] = useState('partner');

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/admin-super/revenue-dashboard`, { headers });
      setData(res.data);
    } catch (e) {
      toast.error('Failed to load revenue data');
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  if (loading || !data) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  const s = data.summary || {};
  const collectionRate = s.total_revenue > 0 ? ((s.total_received / s.total_revenue) * 100).toFixed(1) : 0;

  return (
    <div className="space-y-6" data-testid="revenue-dashboard">
      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-5 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
          <div className="flex items-center justify-between mb-2">
            <DollarSign className="h-5 w-5 text-emerald-600" />
            <ArrowUpRight className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-xs text-emerald-600 font-medium">Total Revenue</p>
          <p className="text-2xl font-bold text-emerald-800">₹{(s.total_revenue || 0).toLocaleString()}</p>
          <p className="text-xs text-emerald-500 mt-1">{s.total_sales || 0} approved sales</p>
        </Card>
        <Card className="p-5 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-center justify-between mb-2">
            <CreditCard className="h-5 w-5 text-blue-600" />
            <Badge className="bg-blue-200 text-blue-700 text-xs">{collectionRate}%</Badge>
          </div>
          <p className="text-xs text-blue-600 font-medium">Collected</p>
          <p className="text-2xl font-bold text-blue-800">₹{(s.total_received || 0).toLocaleString()}</p>
          <p className="text-xs text-blue-500 mt-1">Pending: ₹{(s.total_pending || 0).toLocaleString()}</p>
        </Card>
        <Card className="p-5 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
          <div className="flex items-center justify-between mb-2">
            <Users className="h-5 w-5 text-amber-600" />
            <ArrowDownRight className="h-4 w-4 text-amber-500" />
          </div>
          <p className="text-xs text-amber-600 font-medium">Commission Paid</p>
          <p className="text-2xl font-bold text-amber-800">₹{(s.total_commission || 0).toLocaleString()}</p>
          <p className="text-xs text-amber-500 mt-1">PA Revenue: ₹{(s.pa_revenue || 0).toLocaleString()}</p>
        </Card>
        <Card className="p-5 bg-gradient-to-br from-teal-50 to-teal-100 border-teal-200">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="h-5 w-5 text-teal-600" />
          </div>
          <p className="text-xs text-teal-600 font-medium">Net Revenue</p>
          <p className="text-2xl font-bold text-teal-800">₹{(s.net_revenue || 0).toLocaleString()}</p>
          <p className="text-xs text-red-500 mt-1">Refunded: ₹{(s.total_refunded || 0).toLocaleString()}</p>
        </Card>
      </div>

      {/* Monthly Trend */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-[#2a777a]" />Monthly Revenue Trend
        </h3>
        {(data.monthly_trend || []).length === 0 ? (
          <p className="text-slate-500 text-center py-8">No monthly data yet</p>
        ) : (
          <div className="space-y-2">
            {/* Simple bar chart */}
            {(() => {
              const maxRev = Math.max(...data.monthly_trend.map(m => m.revenue), 1);
              return data.monthly_trend.slice(-12).map((m, idx) => (
                <div key={m.month} className="flex items-center gap-3" data-testid={`month-row-${idx}`}>
                  <span className="text-sm font-medium text-slate-600 w-20">{m.month}</span>
                  <div className="flex-1 flex items-center gap-2">
                    <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden relative">
                      <div
                        className="h-full bg-gradient-to-r from-[#2a777a] to-[#3a9a9d] rounded-full transition-all duration-500"
                        style={{ width: `${(m.revenue / maxRev) * 100}%` }}
                      />
                      <div
                        className="absolute top-0 h-full bg-emerald-400/50 rounded-full"
                        style={{ width: `${(m.received / maxRev) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-slate-800 w-28 text-right">₹{m.revenue.toLocaleString()}</span>
                  </div>
                  <span className="text-xs text-slate-500 w-16 text-right">{m.count} sales</span>
                </div>
              ));
            })()}
            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
              <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#2a777a] rounded-sm" />Revenue</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 bg-emerald-400 rounded-sm" />Received</span>
            </div>
          </div>
        )}
      </Card>

      {/* Breakdown Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {[
          { key: 'partner', label: 'By Partner', icon: Users },
          { key: 'product', label: 'By Service', icon: Briefcase },
          { key: 'payment', label: 'By Payment Method', icon: CreditCard },
          { key: 'currency', label: 'By Currency', icon: DollarSign },
        ].map(tab => (
          <Button
            key={tab.key}
            variant={activeBreakdown === tab.key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveBreakdown(tab.key)}
            className={activeBreakdown === tab.key ? 'bg-[#2a777a] hover:bg-[#236466]' : ''}
            data-testid={`breakdown-${tab.key}`}
          >
            <tab.icon className="h-4 w-4 mr-1" />{tab.label}
          </Button>
        ))}
      </div>

      {/* By Partner */}
      {activeBreakdown === 'partner' && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-3 font-medium text-slate-600">Partner</th>
                  <th className="text-right p-3 font-medium text-slate-600">Sales</th>
                  <th className="text-right p-3 font-medium text-slate-600">Revenue</th>
                  <th className="text-right p-3 font-medium text-slate-600">Received</th>
                  <th className="text-right p-3 font-medium text-slate-600">Commission</th>
                  <th className="text-right p-3 font-medium text-slate-600">% of Total</th>
                </tr>
              </thead>
              <tbody>
                {(data.by_partner || []).map((p, idx) => (
                  <tr key={p.partner_id} className="border-t hover:bg-slate-50" data-testid={`partner-rev-${idx}`}>
                    <td className="p-3 font-medium text-slate-800">{p.partner_name}</td>
                    <td className="p-3 text-right text-slate-600">{p.sales_count}</td>
                    <td className="p-3 text-right font-semibold text-slate-800">₹{p.revenue.toLocaleString()}</td>
                    <td className="p-3 text-right text-emerald-600">₹{p.received.toLocaleString()}</td>
                    <td className="p-3 text-right text-amber-600">₹{p.commission.toLocaleString()}</td>
                    <td className="p-3 text-right text-slate-500">{s.total_revenue > 0 ? ((p.revenue / s.total_revenue) * 100).toFixed(1) : 0}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* By Product/Service */}
      {activeBreakdown === 'product' && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-3 font-medium text-slate-600">Service</th>
                  <th className="text-right p-3 font-medium text-slate-600">Sales</th>
                  <th className="text-right p-3 font-medium text-slate-600">Revenue</th>
                  <th className="text-right p-3 font-medium text-slate-600">Received</th>
                  <th className="text-right p-3 font-medium text-slate-600">Commission</th>
                </tr>
              </thead>
              <tbody>
                {(data.by_product || []).map((p, idx) => (
                  <tr key={p.product_id} className="border-t hover:bg-slate-50" data-testid={`product-rev-${idx}`}>
                    <td className="p-3 font-medium text-slate-800">{p.product_name}</td>
                    <td className="p-3 text-right text-slate-600">{p.sales_count}</td>
                    <td className="p-3 text-right font-semibold text-slate-800">₹{p.revenue.toLocaleString()}</td>
                    <td className="p-3 text-right text-emerald-600">₹{p.received.toLocaleString()}</td>
                    <td className="p-3 text-right text-amber-600">₹{p.commission.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* By Payment Method */}
      {activeBreakdown === 'payment' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(data.payment_methods || []).map((pm, idx) => (
            <Card key={pm.method} className="p-5" data-testid={`payment-method-${idx}`}>
              <div className="flex items-center gap-3 mb-3">
                <CreditCard className="h-5 w-5 text-[#2a777a]" />
                <h4 className="font-semibold text-slate-800 capitalize">{pm.method.replace('_', ' ')}</h4>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500">Transactions</p>
                  <p className="text-lg font-bold text-slate-800">{pm.count}</p>
                </div>
                <div className="p-2 bg-emerald-50 rounded-lg">
                  <p className="text-xs text-emerald-500">Amount</p>
                  <p className="text-lg font-bold text-emerald-800">₹{pm.amount.toLocaleString()}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* By Currency (Domestic vs International) */}
      {activeBreakdown === 'currency' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(data.by_currency || []).map((c, idx) => (
            <Card key={c.currency} className="p-5" data-testid={`currency-${idx}`}>
              <div className="flex items-center gap-3 mb-3">
                <DollarSign className="h-5 w-5 text-[#2a777a]" />
                <div>
                  <h4 className="font-semibold text-slate-800">{c.currency}</h4>
                  <p className="text-xs text-slate-500">{c.label}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="p-2 bg-slate-50 rounded-lg text-center">
                  <p className="text-xs text-slate-500">Sales</p>
                  <p className="text-lg font-bold text-slate-800">{c.count}</p>
                </div>
                <div className="p-2 bg-emerald-50 rounded-lg text-center">
                  <p className="text-xs text-emerald-500">Revenue</p>
                  <p className="text-lg font-bold text-emerald-800">₹{c.revenue.toLocaleString()}</p>
                </div>
                <div className="p-2 bg-blue-50 rounded-lg text-center">
                  <p className="text-xs text-blue-500">Received</p>
                  <p className="text-lg font-bold text-blue-800">₹{c.received.toLocaleString()}</p>
                </div>
              </div>
            </Card>
          ))}
          {(data.by_currency || []).length === 0 && (
            <Card className="p-8 text-center col-span-3"><p className="text-slate-500">All transactions are in INR (Domestic)</p></Card>
          )}
        </div>
      )}
    </div>
  );
};

export default RevenueDashboard;
