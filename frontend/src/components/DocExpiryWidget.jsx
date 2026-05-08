import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CalendarClock, AlertTriangle, ShieldAlert, RefreshCw, Bell } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SEV_STYLE = {
  expired:  { c: 'bg-red-50 border-red-200 text-red-700', icon: ShieldAlert, label: 'Expired' },
  critical: { c: 'bg-orange-50 border-orange-200 text-orange-700', icon: AlertTriangle, label: 'Critical (≤15d)' },
  warning:  { c: 'bg-amber-50 border-amber-200 text-amber-700', icon: AlertTriangle, label: 'Warning (≤60d)' },
  info:     { c: 'bg-blue-50 border-blue-200 text-blue-700', icon: CalendarClock, label: 'Heads-up (≤90d)' },
};

export default function DocExpiryWidget() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [firing, setFiring] = useState(false);

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/doc-expiry/upcoming?horizon_days=120`, auth());
      setItems(r.data.items || []);
      setStats(r.data.stats || {});
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const fireAlerts = async () => {
    setFiring(true);
    try {
      const r = await axios.post(`${API}/doc-expiry/check-now`, {}, auth());
      toast.success(`Scan complete — ${r.data.alerts_fired} new alert(s) sent across ${r.data.scanned} doc(s)`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Scan failed'); }
    setFiring(false);
  };

  const totalActionable = (stats.expired || 0) + (stats.critical || 0) + (stats.warning || 0);

  return (
    <Card className="p-5 border-l-4 border-l-amber-500" data-testid="doc-expiry-widget">
      <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <CalendarClock className="h-5 w-5 text-amber-600" />
          <div>
            <p className="font-semibold text-slate-800">Document Expiry Tracker</p>
            <p className="text-[11px] text-slate-500">Passport, IELTS, PCC, medicals — proactive alerts</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={load} disabled={loading} data-testid="docexp-refresh">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button size="sm" onClick={fireAlerts} disabled={firing || totalActionable === 0} className="bg-amber-600 hover:bg-amber-700 text-white" data-testid="docexp-fire">
            <Bell className={`h-3.5 w-3.5 mr-1 ${firing ? 'animate-pulse' : ''}`} /> {firing ? 'Sending…' : 'Send Alerts'}
          </Button>
        </div>
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        {['expired', 'critical', 'warning', 'info'].map(k => {
          const s = SEV_STYLE[k];
          return (
            <div key={k} className={`p-2 rounded border ${s.c}`}>
              <p className="text-[10px] uppercase font-semibold tracking-wide opacity-70">{s.label.split(' ')[0]}</p>
              <p className="text-xl font-bold">{stats[k] || 0}</p>
            </div>
          );
        })}
      </div>

      {/* List */}
      {items.length === 0 ? (
        <div className="text-center py-6 text-slate-400 text-sm">
          {loading ? 'Loading…' : 'No documents expiring in the next 120 days.'}
        </div>
      ) : (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {items.slice(0, 12).map(it => {
            const s = SEV_STYLE[it.severity] || SEV_STYLE.info;
            const Icon = s.icon;
            return (
              <div key={it.id} className={`flex items-center gap-2 p-2 rounded border ${s.c}`} data-testid={`docexp-row-${it.id}`}>
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold truncate">
                    {it.client_name || '—'} <span className="text-[10px] font-mono opacity-60">{it.scope_label}</span>
                  </p>
                  <p className="text-[10px] opacity-80">{(it.doc_type || '').replace(/_/g, ' ')} · {it.file_name || ''}</p>
                </div>
                <Badge className={`${s.c} text-[10px] border`}>
                  {it.days_left < 0 ? `${Math.abs(it.days_left)}d ago` : `${it.days_left}d left`}
                </Badge>
              </div>
            );
          })}
          {items.length > 12 && (
            <p className="text-[11px] text-slate-500 text-center pt-1">+ {items.length - 12} more — refresh "Send Alerts" for full coverage.</p>
          )}
        </div>
      )}
    </Card>
  );
}
