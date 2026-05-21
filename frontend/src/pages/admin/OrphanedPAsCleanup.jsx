/**
 * Orphaned PAs Cleanup Utility — Phase 6.8.1
 * Admin-only panel for assigning a Partner to or deleting "blank" PAs created
 * before the Phase 6.8 fix (i.e. PAs that don't have a partner_id / pa_number).
 *
 * Embed inside AdminDashboard or visit /admin/orphaned-pas standalone.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Trash2, UserCheck, RefreshCw, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function OrphanedPAsCleanup() {
  const headers = useMemo(() => ({ Authorization: `Bearer ${localStorage.getItem('token')}` }), []);
  const [items, setItems] = useState([]);
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [assignments, setAssignments] = useState({}); // pa_id → partner_id
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [orphRes, partRes] = await Promise.all([
        axios.get(`${API}/sales/assessments/orphaned-pas/list`, { headers }),
        axios.get(`${API}/sales/assessments/partner-options`, { headers }),
      ]);
      setItems(orphRes.data.items || []);
      setPartners(partRes.data.items || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load orphaned PAs');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const assign = async (paId) => {
    const partnerId = assignments[paId];
    if (!partnerId) {
      toast.error('Pick a partner first');
      return;
    }
    setBusyId(paId);
    try {
      await axios.post(`${API}/sales/assessments/orphaned-pas/${paId}/assign`, { partner_id: partnerId }, { headers });
      toast.success('Assigned — PA will now appear in partner pipeline');
      setItems(prev => prev.filter(p => p.id !== paId));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Assign failed');
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (paId) => {
    if (!window.confirm('Delete this orphaned PA permanently?')) return;
    setBusyId(paId);
    try {
      await axios.delete(`${API}/sales/assessments/orphaned-pas/${paId}`, { headers });
      toast.success('Deleted');
      setItems(prev => prev.filter(p => p.id !== paId));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Delete failed');
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <Card className="p-4 flex items-center justify-center" data-testid="orphan-loading">
        <Loader2 className="h-5 w-5 animate-spin text-amber-600 mr-2" />Loading orphaned PAs…
      </Card>
    );
  }

  return (
    <Card className="p-4" data-testid="orphaned-pas-cleanup">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <h2 className="text-base font-bold">Orphaned PAs — Cleanup Utility</h2>
          <Badge className="bg-amber-100 text-amber-700">{items.length} found</Badge>
        </div>
        <Button variant="outline" size="sm" onClick={load} className="h-7" data-testid="orphan-refresh">
          <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
        </Button>
      </div>
      <p className="text-[11px] text-slate-500 mb-3">
        PAs created via Smart Sales Helper before the Phase 6.8.1 fix may lack a partner. Assign or delete each one below.
      </p>
      {items.length === 0 ? (
        <p className="text-xs text-emerald-700 bg-emerald-50 p-3 rounded text-center" data-testid="orphan-empty">
          ✅ No orphaned PAs — pipeline is clean!
        </p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {items.map(pa => (
            <div key={pa.id} className="p-3 bg-slate-50 rounded border border-slate-200 grid grid-cols-1 md:grid-cols-12 gap-2 items-center" data-testid={`orphan-row-${pa.id.slice(0, 8)}`}>
              <div className="md:col-span-4">
                <p className="text-xs font-semibold text-slate-800">{pa.client_name || '—'}</p>
                <p className="text-[10px] text-slate-500 font-mono">{pa.id.slice(0, 12)}…</p>
                <p className="text-[10px] text-slate-500">{pa.client_email || ''}</p>
              </div>
              <div className="md:col-span-2 text-[11px]">
                <p className="text-slate-500">Created by</p>
                <p className="font-semibold text-slate-700">{pa.created_by_name || '—'}</p>
              </div>
              <div className="md:col-span-3">
                <select
                  value={assignments[pa.id] || ''}
                  onChange={e => setAssignments(prev => ({ ...prev, [pa.id]: e.target.value }))}
                  className="w-full border border-slate-200 rounded px-2 py-1 text-xs bg-white"
                  data-testid={`orphan-select-${pa.id.slice(0, 8)}`}
                >
                  <option value="">— Assign to —</option>
                  {partners.map(p => (
                    <option key={p.id} value={p.id}>{p.name || p.email} ({p.role.replace(/_/g, ' ')})</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-3 flex gap-1 justify-end">
                <Button size="sm" className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-700" onClick={() => assign(pa.id)} disabled={busyId === pa.id || !assignments[pa.id]} data-testid={`orphan-assign-${pa.id.slice(0, 8)}`}>
                  {busyId === pa.id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <UserCheck className="h-3 w-3 mr-1" />}
                  Assign
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-[11px] text-rose-600 border-rose-300 hover:bg-rose-50" onClick={() => remove(pa.id)} disabled={busyId === pa.id} data-testid={`orphan-delete-${pa.id.slice(0, 8)}`}>
                  <Trash2 className="h-3 w-3 mr-1" />Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
