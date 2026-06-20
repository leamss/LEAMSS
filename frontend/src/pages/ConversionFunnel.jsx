import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowDown, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const stageColors = ['bg-blue-500', 'bg-leamss-orange-500', 'bg-amber-500', 'bg-green-500'];

export default function ConversionFunnel({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/conversion-funnel`, { headers: { Authorization: `Bearer ${token}` } });
      setData(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  if (!data) return null;

  const stages = data.stages || [];
  const maxTotal = Math.max(...stages.map(s => s.total), 1);

  return (
    <div className="space-y-6" data-testid="conversion-funnel">
      {/* Summary */}
      {data.summary && (
        <div className="grid grid-cols-3 gap-4">
          <Card><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-blue-500">{data.summary.total_leads}</p><p className="text-xs text-gray-500">Total Leads</p></CardContent></Card>
          <Card><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-green-500">{data.summary.total_completions}</p><p className="text-xs text-gray-500">Completions</p></CardContent></Card>
          <Card><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-leamss-orange-500">{data.summary.overall_rate}%</p><p className="text-xs text-gray-500">Overall Rate</p></CardContent></Card>
        </div>
      )}

      {/* Funnel Visualization */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Conversion Funnel</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-1">
            {stages.map((stage, i) => {
              const width = Math.max(20, (stage.total / maxTotal) * 100);
              return (
                <div key={i}>
                  <div className="flex items-center gap-4">
                    <div className="w-36 text-right text-sm font-medium text-gray-700">{stage.stage}</div>
                    <div className="flex-1">
                      <div className={`${stageColors[i]} h-12 rounded-lg flex items-center justify-between px-4 text-white transition-all`} style={{ width: `${width}%` }}>
                        <span className="font-bold text-sm">{stage.total}</span>
                        <Badge className="bg-white/20 text-white text-xs">{stage.rate}%</Badge>
                      </div>
                    </div>
                    <div className="w-20 text-sm text-gray-500">{stage.converted} conv.</div>
                  </div>
                  {i < stages.length - 1 && (
                    <div className="flex items-center gap-4 py-1">
                      <div className="w-36" />
                      <ArrowDown className="w-4 h-4 text-gray-300 ml-8" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
