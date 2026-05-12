import { useEffect, useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  Users, Target, IndianRupee, TrendingUp, Award, AlertCircle,
  RefreshCw, Crown, Trophy, Edit3, Briefcase, ArrowDown,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGE_LABELS = {
  new: 'New',
  partner_review: 'Partner Review',
  approved: 'Admin Approved',
  proposal_sent: 'Proposal Sent',
  proposal_paid: 'Fee Paid',
  awaiting_final_approval: 'Final Approval',
  case_created: 'Case Created',
};

const STAGE_COLORS = {
  new: 'bg-slate-100 text-slate-700',
  partner_review: 'bg-pink-100 text-pink-700',
  approved: 'bg-blue-100 text-blue-700',
  proposal_sent: 'bg-amber-100 text-amber-700',
  proposal_paid: 'bg-emerald-100 text-emerald-700',
  awaiting_final_approval: 'bg-indigo-100 text-indigo-700',
  case_created: 'bg-teal-100 text-teal-700',
};

const TIER_BADGE = {
  Bronze: 'bg-amber-100 text-amber-800 border-amber-300',
  Silver: 'bg-slate-200 text-slate-800 border-slate-300',
  Gold: 'bg-yellow-200 text-yellow-900 border-yellow-400',
};

function currentMonthString() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function inr(v) {
  return `₹${Number(v || 0).toLocaleString('en-IN')}`;
}

/**
 * ManagerDashboard — Phase 3 of In-House Sales CRM.
 * Visible to admin (sees all reps) and sales_manager (sees own direct reports).
 * Shows: team stats · per-rep performance + target editor · pipeline by stage · top performer.
 */
export default function ManagerDashboard() {
  const [month, setMonth] = useState(currentMonthString());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);  // rep object being edited
  const [tgtRev, setTgtRev] = useState('');
  const [tgtDeals, setTgtDeals] = useState('');
  const [saving, setSaving] = useState(false);
  const [assignDialog, setAssignDialog] = useState(null);
  const [managers, setManagers] = useState([]);
  const [selectedMgr, setSelectedMgr] = useState('');

  const auth = useMemo(() => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }), []);

  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  }, []);
  const isAdmin = user.role === 'admin';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/sales-team/manager-dashboard?month=${month}`, auth);
      setData(r.data);
      if (isAdmin) {
        const mgr = await axios.get(`${API}/sales-team/managers`, auth);
        setManagers(mgr.data.items || []);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load dashboard');
      setData(null);
    }
    setLoading(false);
  }, [auth, month, isAdmin]);

  useEffect(() => { load(); }, [load]);

  const openEditTarget = (rep) => {
    setEditing(rep);
    setTgtRev(rep.target_revenue || '');
    setTgtDeals(rep.target_deals || '');
  };

  const saveTarget = async () => {
    if (!editing) return;
    const rev = Number(tgtRev);
    if (isNaN(rev) || rev < 0) {
      toast.error('Target revenue must be a non-negative number');
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/sales-team/targets`, {
        rep_id: editing.id,
        month,
        target_revenue: rev,
        target_deals: Number(tgtDeals) || 0,
      }, auth);
      toast.success(`Target set for ${editing.name}`);
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    }
    setSaving(false);
  };

  const openAssign = (rep) => {
    setAssignDialog(rep);
    setSelectedMgr(rep.manager_id || 'none');
  };

  const saveAssign = async () => {
    if (!assignDialog) return;
    try {
      await axios.post(`${API}/sales-team/reps/${assignDialog.id}/assign-manager`,
        { manager_id: selectedMgr === 'none' ? null : selectedMgr }, auth);
      toast.success('Manager assignment updated');
      setAssignDialog(null);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  if (loading && !data) {
    return <div className="p-8 text-center text-slate-500" data-testid="manager-dashboard-loading">Loading sales team dashboard…</div>;
  }
  if (!data) {
    return <div className="p-8 text-center text-rose-600">Failed to load dashboard.</div>;
  }

  const { stats, reps, pipeline_by_stage, top_performer } = data;
  const maxPipelineCount = Math.max(1, ...pipeline_by_stage.map(p => p.count));

  return (
    <div className="space-y-6" data-testid="manager-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Briefcase className="h-6 w-6 text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-800">Sales Team Dashboard</h1>
            <Badge className={data.scope === 'admin_all' ? 'bg-rose-100 text-rose-700 border-rose-200' : 'bg-indigo-100 text-indigo-700 border-indigo-200'}>
              {data.scope === 'admin_all' ? 'Org-wide' : 'My Team'}
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">Track in-house rep performance, set monthly targets, and approve discounts.</p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value || currentMonthString())}
            className="w-40"
            data-testid="md-month-picker"
          />
          <Button variant="outline" size="sm" onClick={load} disabled={loading} data-testid="md-refresh">
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* Top stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="md-stats-strip">
        <Card className="p-4 border-l-4 border-l-emerald-500" data-testid="stat-team-revenue">
          <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wide">
            <IndianRupee className="h-3.5 w-3.5" /> Team Revenue
          </div>
          <p className="text-2xl font-bold text-slate-800 mt-1">{inr(stats.team_revenue)}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">{stats.team_deals} deals · {month}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-indigo-500" data-testid="stat-rep-count">
          <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wide">
            <Users className="h-3.5 w-3.5" /> Active Reps
          </div>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats.rep_count}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">In-house employees in scope</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-amber-500" data-testid="stat-target-attainment">
          <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wide">
            <Target className="h-3.5 w-3.5" /> Team Target
          </div>
          <p className="text-2xl font-bold text-slate-800 mt-1">
            {stats.team_attainment_pct !== null ? `${stats.team_attainment_pct}%` : '—'}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">{inr(stats.team_target)} target</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-rose-500" data-testid="stat-pending-approvals">
          <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wide">
            <AlertCircle className="h-3.5 w-3.5" /> Pending Approvals
          </div>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats.pending_approvals}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">{inr(stats.pending_discount_value)} at risk</p>
        </Card>
      </div>

      {/* Top performer banner */}
      {top_performer && top_performer.revenue > 0 && (
        <Card className="p-4 bg-gradient-to-r from-yellow-50 to-amber-50 border-amber-200" data-testid="md-top-performer">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="h-12 w-12 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 flex items-center justify-center shadow-md">
              <Crown className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <p className="text-xs text-amber-700 font-semibold uppercase tracking-wide">🏆 Top Performer · {data.month}</p>
              <p className="font-bold text-slate-800 text-lg">{top_performer.name}</p>
              <p className="text-sm text-slate-600">
                {inr(top_performer.revenue)} · {top_performer.deal_count} deals · {top_performer.tier_label} tier ({top_performer.tier_rate_pct}%)
              </p>
            </div>
            <div className="text-right">
              <p className="text-[11px] text-slate-500 uppercase">Projected Payout</p>
              <p className="font-bold text-emerald-700 text-xl">{inr(top_performer.projected_payout)}</p>
            </div>
          </div>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Reps table — 2/3 */}
        <Card className="p-5 lg:col-span-2" data-testid="md-reps-table">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-800 flex items-center gap-2"><Users className="h-4 w-4 text-indigo-600" /> Rep Performance</h2>
            <span className="text-xs text-slate-500">{reps.length} reps</span>
          </div>
          {reps.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-sm">
              No in-house employees in scope yet. Set <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">employment_type = employee</code> on a Partner user in the Users page.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] text-slate-500 uppercase tracking-wide border-b">
                    <th className="text-left py-2 px-2">Rep</th>
                    <th className="text-right py-2 px-2">Revenue</th>
                    <th className="text-center py-2 px-2">Deals</th>
                    <th className="text-center py-2 px-2">Tier</th>
                    <th className="text-right py-2 px-2">Target</th>
                    <th className="text-right py-2 px-2">Attainment</th>
                    <th className="text-right py-2 px-2">Payout</th>
                    <th className="text-right py-2 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reps.map((r) => (
                    <tr key={r.id} className="border-b last:border-0 hover:bg-slate-50" data-testid={`md-rep-row-${r.id}`}>
                      <td className="py-2.5 px-2">
                        <div className="font-medium text-slate-800">{r.name}</div>
                        <div className="text-[11px] text-slate-500">{r.email}</div>
                      </td>
                      <td className="py-2.5 px-2 text-right font-semibold text-slate-800">{inr(r.revenue)}</td>
                      <td className="py-2.5 px-2 text-center">{r.deal_count}</td>
                      <td className="py-2.5 px-2 text-center">
                        <Badge className={`${TIER_BADGE[r.tier_label] || 'bg-slate-100'} border text-[10px]`}>
                          {r.tier_label} {r.tier_rate_pct}%
                        </Badge>
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-600">{r.target_revenue ? inr(r.target_revenue) : <span className="text-slate-400">—</span>}</td>
                      <td className="py-2.5 px-2 text-right">
                        {r.attainment_pct !== null ? (
                          <span className={`font-semibold ${r.attainment_pct >= 100 ? 'text-emerald-700' : r.attainment_pct >= 60 ? 'text-amber-700' : 'text-rose-600'}`}>
                            {r.attainment_pct}%
                          </span>
                        ) : <span className="text-slate-400">—</span>}
                      </td>
                      <td className="py-2.5 px-2 text-right text-emerald-700 font-medium">{inr(r.projected_payout)}</td>
                      <td className="py-2.5 px-2 text-right">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => openEditTarget(r)} data-testid={`md-edit-target-${r.id}`}>
                            <Edit3 className="h-3 w-3 mr-1" /> Target
                          </Button>
                          {isAdmin && (
                            <Button size="sm" variant="ghost" className="h-7 text-xs text-indigo-600" onClick={() => openAssign(r)} data-testid={`md-assign-mgr-${r.id}`}>
                              Manager
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Pipeline by stage — 1/3 */}
        <Card className="p-5" data-testid="md-pipeline-stages">
          <h2 className="font-semibold text-slate-800 flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-emerald-600" /> Pipeline by Stage
          </h2>
          <div className="space-y-2.5">
            {pipeline_by_stage.map((p, idx) => {
              const widthPct = (p.count / maxPipelineCount) * 100;
              return (
                <div key={p.stage} data-testid={`md-stage-${p.stage}`}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <Badge className={`${STAGE_COLORS[p.stage] || 'bg-slate-100'} text-[10px] border-0`}>{STAGE_LABELS[p.stage] || p.stage}</Badge>
                    <span className="text-slate-600">
                      <strong className="text-slate-800">{p.count}</strong>
                      {p.value > 0 && <span className="ml-1.5 text-emerald-600">· {inr(p.value)}</span>}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-400 to-emerald-500 transition-all"
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  {idx < pipeline_by_stage.length - 1 && (
                    <div className="flex justify-center -mt-0.5"><ArrowDown className="h-3 w-3 text-slate-300" /></div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Set Target dialog */}
      <Dialog open={!!editing} onOpenChange={(o) => { if (!o) setEditing(null); }}>
        <DialogContent data-testid="md-target-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Target className="h-5 w-5 text-amber-600" /> Set Target — {editing?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="text-xs text-slate-500">Month: <strong className="text-slate-700">{month}</strong></div>
            <div>
              <label className="text-xs font-medium text-slate-700">Target Revenue (₹)</label>
              <Input
                type="number"
                value={tgtRev}
                onChange={(e) => setTgtRev(e.target.value)}
                placeholder="e.g. 500000"
                data-testid="md-target-revenue-input"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-700">Target Deals</label>
              <Input
                type="number"
                value={tgtDeals}
                onChange={(e) => setTgtDeals(e.target.value)}
                placeholder="e.g. 5"
                data-testid="md-target-deals-input"
              />
            </div>
            {editing?.revenue > 0 && (
              <div className="bg-slate-50 border rounded p-2.5 text-xs text-slate-600">
                <div>Current Revenue: <strong>{inr(editing.revenue)}</strong></div>
                <div>Current Deals: <strong>{editing.deal_count}</strong></div>
                {tgtRev && Number(tgtRev) > 0 && (
                  <div className="mt-1 text-emerald-700">
                    Projected attainment: <strong>{Math.round((editing.revenue / Number(tgtRev)) * 100)}%</strong>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={saveTarget} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="md-save-target-btn">
              {saving ? 'Saving…' : 'Save Target'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign manager dialog */}
      <Dialog open={!!assignDialog} onOpenChange={(o) => { if (!o) setAssignDialog(null); }}>
        <DialogContent data-testid="md-assign-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Trophy className="h-5 w-5 text-indigo-600" /> Assign Manager — {assignDialog?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-xs text-slate-500">Choose a sales-manager this rep will report to. Their requests and target visibility will route through this manager.</p>
            <Select value={selectedMgr} onValueChange={setSelectedMgr}>
              <SelectTrigger data-testid="md-mgr-select"><SelectValue placeholder="Select manager" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">— No manager (detach) —</SelectItem>
                {managers.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.name} ({m.email})</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {managers.length === 0 && (
              <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                <Award className="h-3 w-3 inline mr-1" />
                No sales_managers exist yet. Create a user with role <code className="bg-white px-1 rounded">sales_manager</code> in the Users page first.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAssignDialog(null)}>Cancel</Button>
            <Button onClick={saveAssign} className="bg-indigo-600 hover:bg-indigo-700" data-testid="md-save-assign-btn">Assign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
