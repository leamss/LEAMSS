import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DollarSign, TrendingUp, Users, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CommissionAnalytics({ token, role }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/commission-analytics`, { headers: { Authorization: `Bearer ${token}` } });
      setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  if (!data) return null;

  const partners = data.partners || [];
  const trend = data.monthly_trend || [];
  const maxComm = Math.max(...partners.map(p => p.total_commission), 1);
  const maxTrend = Math.max(...trend.map(t => t.commission), 1);

  return (
    <div className="space-y-6" data-testid="commission-analytics">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <DollarSign className="w-8 h-8 text-green-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">₹{data.total_commission?.toLocaleString()}</p>
            <p className="text-xs text-gray-500">Total Commission</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <Users className="w-8 h-8 text-blue-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{partners.length}</p>
            <p className="text-xs text-gray-500">Active Partners</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <TrendingUp className="w-8 h-8 text-leamss-orange-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{trend.length}</p>
            <p className="text-xs text-gray-500">Months Tracked</p>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Trend */}
      {trend.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Monthly Commission Trend</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-32">
              {trend.map((t, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full bg-[#2a777a] rounded-t transition-all" style={{ height: `${(t.commission / maxTrend) * 100}%`, minHeight: '4px' }} title={`₹${t.commission}`} />
                  <span className="text-[8px] text-gray-500 -rotate-45 origin-left">{t.month}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Partner Breakdown */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Partner Commission Breakdown</CardTitle></CardHeader>
        <CardContent>
          {partners.length === 0 ? <p className="text-center text-gray-500 py-4">No partner commissions to display.</p> : (
            <div className="space-y-4">
              {partners.map(p => (
                <div key={p.partner_id}>
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <p className="font-medium text-sm">{p.partner_name}</p>
                      <p className="text-xs text-gray-500">{p.total_sales} sales | {p.approved_sales} approved</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-sm">₹{p.total_commission?.toLocaleString()}</p>
                      {p.pending_commission > 0 && <p className="text-xs text-amber-600">₹{p.pending_commission?.toLocaleString()} pending</p>}
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-[#f7620b] h-2 rounded-full transition-all" style={{ width: `${(p.total_commission / maxComm) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
