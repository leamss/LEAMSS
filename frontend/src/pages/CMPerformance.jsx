import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Clock, Star, AlertTriangle, Loader2, Briefcase, CheckCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CMPerformance({ token, role }) {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchMetrics(); }, []);

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/cm-performance`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setMetrics(data.metrics || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="cm-performance">
      {metrics.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-gray-500"><User className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No case manager data available.</p></CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {metrics.map(cm => (
            <Card key={cm.cm_id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <User className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{cm.cm_name}</CardTitle>
                    <p className="text-xs text-gray-500">{cm.total_cases} total cases</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-blue-500" />
                      <span className="text-lg font-bold">{cm.active_cases}</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">Active Cases</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <span className="text-lg font-bold">{cm.completed_cases}</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">Completed</p>
                  </div>
                  <div className="p-3 bg-amber-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-amber-500" />
                      <span className="text-lg font-bold">{cm.avg_completion_days}</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">Avg Days</p>
                  </div>
                  <div className="p-3 bg-yellow-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span className="text-lg font-bold">{cm.avg_satisfaction || 'N/A'}</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">Satisfaction ({cm.surveys_received} surveys)</p>
                  </div>
                </div>
                {cm.overdue_steps > 0 && (
                  <div className="mt-3 flex items-center gap-2 p-2 bg-red-50 rounded-lg text-red-700 text-sm">
                    <AlertTriangle className="w-4 h-4" /> {cm.overdue_steps} overdue steps
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
