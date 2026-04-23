import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Bell, RefreshCw, Send } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * DropoffRecoveryWidget — shows leads stuck beyond SLA.
 * Partners see their own; Admins see all.
 */
export default function DropoffRecoveryWidget() {
  const [data, setData] = useState({ count: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [nudging, setNudging] = useState(null);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const r = await axios.get(`${API}/intelligence/dropoff-leads`, getAuth());
      setData(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const nudge = async (paId) => {
    setNudging(paId);
    try {
      await axios.post(`${API}/intelligence/nudge/${paId}`, {}, getAuth());
      toast.success('Nudge sent (mock email)');
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    setNudging(null);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5" data-testid="dropoff-widget">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          <h3 className="text-base font-semibold text-slate-800">Drop-off Recovery</h3>
          <Badge className="bg-orange-100 text-orange-700 h-5">{data.count}</Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={load} className="h-7 text-xs" data-testid="dropoff-refresh">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {loading ? (
        <p className="text-xs text-slate-400">Scanning stuck leads…</p>
      ) : data.count === 0 ? (
        <div className="text-center py-6 text-sm text-slate-500">
          All leads moving on time. Great job!
        </div>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {data.items.map(it => (
            <div key={it.id} className={`border rounded-lg p-3 ${it.severity === 'high' ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`} data-testid={`dropoff-item-${it.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{it.client_name} · {it.country}</p>
                  <p className="text-xs text-slate-600 capitalize">{it.stage.replace(/_/g, ' ')} · idle {it.idle_days}d (SLA {it.sla_days}d)</p>
                  <p className="text-[11px] text-slate-700 mt-1"><span className="font-semibold">Action:</span> {it.suggested_action}</p>
                  {it.last_nudge_at && <p className="text-[10px] text-slate-400 mt-0.5">Last nudge: {new Date(it.last_nudge_at).toLocaleString()}</p>}
                </div>
                <Button size="sm" onClick={() => nudge(it.id)} disabled={nudging === it.id}
                  className="h-7 text-xs bg-[#f7620b] hover:bg-[#e55a09] text-white shrink-0" data-testid={`nudge-${it.id}`}>
                  <Bell className="h-3 w-3 mr-1" /> {nudging === it.id ? 'Sending…' : 'Nudge'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
