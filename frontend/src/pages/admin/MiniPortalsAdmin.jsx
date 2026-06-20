/**
 * Phase 20.5 — Admin Mini Portal Management.
 * /admin/mini-portals
 */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Lock, Unlock, KeyRound, RefreshCw, ExternalLink, Eye } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });


export default function MiniPortalsAdmin() {
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('active');

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/mini-portal/admin/list?status=${filter}`, auth());
      setPortals(r.data.portals);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load portals');
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter]);

  const reset = async (p) => {
    const reason = prompt('Reason for password reset (min 10 chars)');
    if (!reason || reason.length < 10) {
      toast.error('Reason must be ≥10 chars');
      return;
    }
    try {
      const r = await axios.post(`${API}/mini-portal/admin/${p.client_id}/reset-password`,
        { reason }, auth());
      toast.success(`New password: ${r.data.new_password} · Revocable 24h`);
      navigator.clipboard?.writeText(r.data.new_password);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Reset failed');
    }
  };

  const toggleLock = async (p) => {
    if (p.locked) {
      try {
        await axios.post(`${API}/mini-portal/admin/${p.client_id}/unlock`, {}, auth());
        toast.success('Portal unlocked');
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Unlock failed');
      }
    } else {
      const reason = prompt('Reason for locking (min 10 chars)');
      if (!reason || reason.length < 10) {
        toast.error('Reason must be ≥10 chars');
        return;
      }
      try {
        await axios.post(`${API}/mini-portal/admin/${p.client_id}/lock`, { reason }, auth());
        toast.success('Portal locked');
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Lock failed');
      }
    }
    load();
  };

  return (
    <div className="max-w-7xl mx-auto p-6" data-testid="mini-portals-admin">
      <header className="mb-4">
        <h1 className="text-3xl font-bold text-leamss-teal flex items-center gap-2">
          <KeyRound className="h-7 w-7" />Client Mini Portals
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Phase 20.5 · Auto-provisioned on PA payment · Admin reset/lock/unlock controls.
        </p>
      </header>

      <div className="flex gap-1 mb-4 border-b">
        {['active', 'locked', 'closed'].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors ${
              filter === s ? 'border-leamss-teal text-leamss-teal' : 'border-transparent text-slate-500'
            }`}
            data-testid={`portal-filter-${s}`}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <Card className="p-4">
        {loading && <p className="text-center py-8 text-slate-500"><RefreshCw className="h-5 w-5 inline animate-spin mr-2" />Loading…</p>}
        {!loading && portals.length === 0 && (
          <p className="text-center py-8 text-slate-400 text-sm">No {filter} portals.</p>
        )}
        {!loading && portals.length > 0 && (
          <table className="w-full text-xs" data-testid="portals-table">
            <thead className="text-[10px] uppercase text-slate-500 border-b">
              <tr>
                <th className="text-left p-2">Client</th>
                <th className="text-left p-2">PA / Product</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Created</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {portals.map(p => (
                <tr key={p.id} className="border-b hover:bg-leamss-teal_50/30" data-testid={`portal-row-${p.client_id}`}>
                  <td className="p-2">
                    <p className="font-bold">{p.client_name}</p>
                    <p className="text-[10px] text-slate-500">{p.client_email}</p>
                  </td>
                  <td className="p-2">
                    <p>{p.country} / {p.service_type}</p>
                    <p className="text-[10px] text-slate-500">PA: {p.pa_id?.slice(0, 12)}…</p>
                  </td>
                  <td className="p-2">
                    <Badge className={p.locked ? 'bg-leamss-red' : 'bg-leamss-teal'} variant="default">
                      {p.locked ? 'Locked' : 'Active'}
                    </Badge>
                  </td>
                  <td className="p-2">{p.created_at?.slice(0, 16).replace('T', ' ')}</td>
                  <td className="p-2 text-right space-x-1">
                    <Button size="sm" variant="ghost" onClick={() => window.open(`/admin/info-sheets/client/${p.client_id}`, '_blank')} title="View Info Sheet" data-testid={`view-sheet-${p.client_id}`}>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => reset(p)} title="Reset Password" data-testid={`reset-pw-${p.client_id}`}>
                      <KeyRound className="h-3.5 w-3.5 text-leamss-orange" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => toggleLock(p)} title={p.locked ? 'Unlock' : 'Lock'} data-testid={`lock-toggle-${p.client_id}`}>
                      {p.locked ? <Unlock className="h-3.5 w-3.5 text-leamss-teal" /> : <Lock className="h-3.5 w-3.5 text-leamss-red" />}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
