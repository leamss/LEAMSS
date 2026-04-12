import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function RevenueForecasting({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchForecast(); }, []);

  const fetchForecast = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/revenue-forecast?months=6`, { headers: { Authorization: `Bearer ${token}` } });
      setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  if (!data) return null;

  const s = data.summary || {};
  const maxRevenue = Math.max(...[...(data.historical || []), ...(data.forecast || [])].map(h => h.revenue || h.predicted_revenue || 0), 1);

  return (
    <div className="space-y-6" data-testid="revenue-forecast">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <DollarSign className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">₹{(s.avg_monthly || 0).toLocaleString()}</p>
                <p className="text-xs text-gray-500">Avg Monthly Revenue</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              {s.growth_rate >= 0 ? <TrendingUp className="w-8 h-8 text-green-500" /> : <TrendingDown className="w-8 h-8 text-red-500" />}
              <div>
                <p className="text-2xl font-bold">{s.growth_rate || 0}%</p>
                <p className="text-xs text-gray-500">Growth Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">₹{(s.pipeline_value || 0).toLocaleString()}</p>
                <p className="text-xs text-gray-500">Pipeline Value</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Badge className={`text-lg px-3 py-1 ${s.trend === 'growing' ? 'bg-green-100 text-green-700' : s.trend === 'declining' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
                {(s.trend || 'N/A').toUpperCase()}
              </Badge>
              <p className="text-xs text-gray-500">Trend</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chart */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Revenue Timeline</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-end gap-1 h-48">
            {(data.historical || []).map((h, i) => (
              <div key={`h-${i}`} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full bg-blue-500 rounded-t transition-all" style={{ height: `${(h.revenue / maxRevenue) * 100}%`, minHeight: '4px' }} title={`₹${h.revenue}`} />
                <span className="text-[9px] text-gray-500 -rotate-45 origin-left">{h.month}</span>
              </div>
            ))}
            <div className="w-px h-full bg-gray-300 mx-1" />
            {(data.forecast || []).map((f, i) => (
              <div key={`f-${i}`} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full bg-green-400 rounded-t border-2 border-dashed border-green-600 transition-all" style={{ height: `${(f.predicted_revenue / maxRevenue) * 100}%`, minHeight: '4px' }} title={`₹${f.predicted_revenue} (predicted)`} />
                <span className="text-[9px] text-green-600 -rotate-45 origin-left">{f.month}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-4 text-xs">
            <div className="flex items-center gap-1"><div className="w-3 h-3 bg-blue-500 rounded" /> Historical</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 bg-green-400 rounded border border-dashed border-green-600" /> Forecast</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
