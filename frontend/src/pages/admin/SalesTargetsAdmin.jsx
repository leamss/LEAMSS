/**
 * Phase 4B — Admin/Manager Sales Targets Management page.
 *
 * Shows team grid with current targets + achievement, supports:
 *   - Set/edit target per user (modal)
 *   - Bulk apply template to many users (modal)
 *   - Period selector
 *   - Filters (status, achievement range)
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowLeft, Target, Users, Sparkles, Edit, Trash2, Plus, Layers, Calendar, IndianRupee, Hash, Filter } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const monthNames = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const statusColors = {
  active: 'bg-blue-100 text-blue-700 border-blue-300',
  completed: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  exceeded: 'bg-amber-100 text-amber-700 border-amber-300',
  missed: 'bg-rose-100 text-rose-700 border-rose-300',
};

const pctColor = (p) => {
  if (p >= 100) return 'text-emerald-600';
  if (p >= 75) return 'text-blue-600';
  if (p >= 50) return 'text-amber-600';
  return 'text-rose-600';
};

const TargetEditModal = ({ open, onClose, member, period, onSaved, existingTarget }) => {
  const [revenue, setRevenue] = useState('');
  const [paCount, setPaCount] = useState('');
  const [notes, setNotes] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setRevenue(existingTarget?.targets?.revenue?.toString() || '');
      setPaCount(existingTarget?.targets?.pa_count?.toString() || '');
      setNotes(existingTarget?.notes || '');
      setReason('');
    }
  }, [open, existingTarget]);

  const handleSave = async () => {
    if (!revenue || !paCount) { toast.error('Both revenue and PA count required'); return; }
    if (existingTarget && reason.trim().length < 5) { toast.error('Reason must be at least 5 characters'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      if (existingTarget) {
        await axios.patch(`${API}/sales/targets/${existingTarget.id}`, {
          revenue: parseFloat(revenue),
          pa_count: parseInt(paCount, 10),
          notes,
          reason,
        }, { headers });
        toast.success('Target updated');
      } else {
        await axios.post(`${API}/sales/targets`, {
          user_id: member.id,
          period_type: period.period_type,
          period_year: period.period_year,
          period_month: period.period_type === 'monthly' ? period.period_month : null,
          period_quarter: period.period_type === 'quarterly' ? period.period_quarter : null,
          revenue: parseFloat(revenue),
          pa_count: parseInt(paCount, 10),
          notes,
        }, { headers });
        toast.success('Target created');
      }
      onSaved();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="target-edit-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-leamss-teal-600" />
            {existingTarget ? 'Edit Target' : 'Set Target'}
          </DialogTitle>
          <DialogDescription>
            For <strong>{member?.name}</strong> · {period.period_type === 'monthly' ? `${monthNames[period.period_month]} ${period.period_year}` : `Q${period.period_quarter} ${period.period_year}`}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="flex items-center gap-1.5 text-sm font-bold"><IndianRupee className="h-4 w-4" />Revenue Target (₹)</Label>
            <Input type="number" value={revenue} onChange={(e) => setRevenue(e.target.value)} placeholder="500000" data-testid="input-revenue" />
            {revenue && <p className="text-xs text-slate-500 mt-1">{formatINR(parseFloat(revenue))}</p>}
          </div>
          <div>
            <Label className="flex items-center gap-1.5 text-sm font-bold"><Hash className="h-4 w-4" />PA Count Target</Label>
            <Input type="number" value={paCount} onChange={(e) => setPaCount(e.target.value)} placeholder="10" data-testid="input-pa-count" />
          </div>
          <div>
            <Label className="text-sm font-bold">Notes (optional)</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Additional context…" rows={2} data-testid="input-notes" />
          </div>
          {existingTarget && (
            <div>
              <Label className="text-sm font-bold text-amber-700">Reason for change (required) *</Label>
              <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Min 5 characters — explain why this target is being changed" rows={2} data-testid="input-reason" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="cancel-edit">Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-target">
            {saving ? 'Saving…' : (existingTarget ? 'Update Target' : 'Set Target')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const BulkApplyModal = ({ open, onClose, members, period, templates, onApplied }) => {
  const [tplId, setTplId] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [overrideExisting, setOverrideExisting] = useState(false);
  const [applying, setApplying] = useState(false);

  useEffect(() => { if (open) { setTplId(''); setSelectedIds([]); setOverrideExisting(false); } }, [open]);

  const toggle = (id) => setSelectedIds((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  const tpl = templates.find((t) => t.id === tplId);

  const apply = async () => {
    if (!tplId || selectedIds.length === 0) { toast.error('Select template + at least one user'); return; }
    setApplying(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/sales/targets/bulk-set`, {
        template_id: tplId,
        user_ids: selectedIds,
        period_type: period.period_type,
        period_year: period.period_year,
        period_month: period.period_type === 'monthly' ? period.period_month : null,
        period_quarter: period.period_type === 'quarterly' ? period.period_quarter : null,
        override_existing: overrideExisting,
      }, { headers: { Authorization: `Bearer ${token}` } });
      const s = r.data.summary;
      toast.success(`Applied: ${s.created} created · ${s.skipped} skipped · ${s.failed} failed`);
      onApplied();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Bulk apply failed');
    } finally {
      setApplying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl" data-testid="bulk-apply-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Layers className="h-5 w-5 text-leamss-teal-600" />Bulk Apply Template</DialogTitle>
          <DialogDescription>Apply a target template to multiple users at once.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-sm font-bold">Template</Label>
            <Select value={tplId} onValueChange={setTplId} data-testid="select-template">
              <SelectTrigger><SelectValue placeholder="Choose a template…" /></SelectTrigger>
              <SelectContent>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name} — {formatINR(t.revenue)} / {t.pa_count} PAs
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {tpl && <p className="text-xs text-slate-600 mt-1">{tpl.description}</p>}
          </div>

          <div>
            <Label className="text-sm font-bold">Users ({selectedIds.length} selected)</Label>
            <div className="border rounded-md max-h-60 overflow-y-auto" data-testid="bulk-users-list">
              {members.map((m) => (
                <div key={m.user.id} className="flex items-center gap-2 p-2 hover:bg-slate-50 border-b last:border-b-0">
                  <Checkbox checked={selectedIds.includes(m.user.id)} onCheckedChange={() => toggle(m.user.id)} data-testid={`bulk-checkbox-${m.user.id}`} />
                  <span className="text-sm font-medium text-slate-800 flex-1">{m.user.name}</span>
                  <Badge variant="outline" className="text-xs">{m.user.rbac_role}</Badge>
                  {m.target && <Badge className="bg-amber-100 text-amber-700 text-xs">Has target</Badge>}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-md p-3">
            <Checkbox checked={overrideExisting} onCheckedChange={setOverrideExisting} data-testid="checkbox-override" />
            <span className="text-sm text-amber-900">Override existing targets (will create updated history entry)</span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={apply} disabled={applying} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="apply-bulk-btn">
            {applying ? 'Applying…' : `Apply to ${selectedIds.length} user${selectedIds.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default function SalesTargetsAdmin() {
  const navigate = useNavigate();
  const now = new Date();
  const [periodType, setPeriodType] = useState('monthly');
  const [periodYear, setPeriodYear] = useState(now.getFullYear());
  const [periodMonth, setPeriodMonth] = useState(now.getMonth() + 1);
  const [periodQuarter, setPeriodQuarter] = useState(Math.floor(now.getMonth() / 3) + 1);

  const [members, setMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  const [editTarget, setEditTarget] = useState(null);
  const [bulkOpen, setBulkOpen] = useState(false);

  const period = { period_type: periodType, period_year: periodYear, period_month: periodMonth, period_quarter: periodQuarter };

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const params = new URLSearchParams({
        period_type: periodType,
        year: periodYear.toString(),
        ...(periodType === 'monthly' ? { month: periodMonth.toString() } : { quarter: periodQuarter.toString() }),
      });
      const [team, tpls] = await Promise.all([
        axios.get(`${API}/sales/targets/department?${params}`, { headers }),
        axios.get(`${API}/sales/target-templates`, { headers }),
      ]);
      setMembers(team.data.members || []);
      setTemplates(tpls.data.templates || []);
    } catch (e) {
      toast.error('Failed to load team targets');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [periodType, periodYear, periodMonth, periodQuarter]);

  const filtered = useMemo(() => members.filter((m) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'no_target') return !m.target;
    return m.target?.status === statusFilter;
  }), [members, statusFilter]);

  const stats = useMemo(() => {
    const with_target = members.filter((m) => m.target);
    const exceeded = with_target.filter((m) => m.target.status === 'exceeded').length;
    const completed = with_target.filter((m) => m.target.status === 'completed').length;
    const on_track = with_target.filter((m) => (m.target.achievement?.overall_percentage || 0) >= 50 && m.target.status === 'active').length;
    const at_risk = with_target.filter((m) => (m.target.achievement?.overall_percentage || 0) < 50 && m.target.status === 'active').length;
    return { with_target: with_target.length, no_target: members.length - with_target.length, exceeded, completed, on_track, at_risk };
  }, [members]);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="sales-targets-admin-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200 transition" data-testid="back-to-admin">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Target className="h-7 w-7 text-leamss-teal-600" /> Sales Targets Management
              </h1>
              <p className="text-sm text-slate-500 mt-1">Set and monitor targets for your sales team</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => navigate('/admin/sales/target-templates')} variant="outline" data-testid="manage-templates-btn">
              <Layers className="h-4 w-4 mr-1.5" /> Templates
            </Button>
            <Button onClick={() => setBulkOpen(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="bulk-apply-btn">
              <Plus className="h-4 w-4 mr-1.5" /> Bulk Apply Template
            </Button>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <Card className="p-3" data-testid="stat-total"><p className="text-xs text-slate-500 uppercase tracking-wide font-bold">Total</p><p className="text-2xl font-extrabold text-slate-800">{members.length}</p></Card>
          <Card className="p-3 border-emerald-200" data-testid="stat-exceeded"><p className="text-xs text-emerald-700 uppercase tracking-wide font-bold">Exceeded</p><p className="text-2xl font-extrabold text-emerald-700">{stats.exceeded}</p></Card>
          <Card className="p-3 border-blue-200" data-testid="stat-on-track"><p className="text-xs text-blue-700 uppercase tracking-wide font-bold">On Track</p><p className="text-2xl font-extrabold text-blue-700">{stats.on_track}</p></Card>
          <Card className="p-3 border-rose-200" data-testid="stat-at-risk"><p className="text-xs text-rose-700 uppercase tracking-wide font-bold">At Risk</p><p className="text-2xl font-extrabold text-rose-700">{stats.at_risk}</p></Card>
          <Card className="p-3 border-amber-200" data-testid="stat-no-target"><p className="text-xs text-amber-700 uppercase tracking-wide font-bold">No Target</p><p className="text-2xl font-extrabold text-amber-700">{stats.no_target}</p></Card>
        </div>

        {/* Period selector */}
        <Card className="p-4 mb-6 flex flex-wrap items-center gap-3" data-testid="period-selector">
          <Calendar className="h-4 w-4 text-slate-500" />
          <Select value={periodType} onValueChange={setPeriodType}>
            <SelectTrigger className="w-36" data-testid="period-type-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="quarterly">Quarterly</SelectItem>
            </SelectContent>
          </Select>
          <Select value={periodYear.toString()} onValueChange={(v) => setPeriodYear(parseInt(v))}>
            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => (
                <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {periodType === 'monthly' ? (
            <Select value={periodMonth.toString()} onValueChange={(v) => setPeriodMonth(parseInt(v))}>
              <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
              <SelectContent>
                {monthNames.slice(1).map((m, i) => <SelectItem key={i + 1} value={(i + 1).toString()}>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          ) : (
            <Select value={periodQuarter.toString()} onValueChange={(v) => setPeriodQuarter(parseInt(v))}>
              <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4].map((q) => <SelectItem key={q} value={q.toString()}>Q{q}</SelectItem>)}
              </SelectContent>
            </Select>
          )}

          <div className="ml-auto flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40" data-testid="status-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="exceeded">Exceeded</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="missed">Missed</SelectItem>
                <SelectItem value="no_target">No Target Set</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Team grid */}
        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <Card className="p-0 overflow-hidden" data-testid="team-targets-table">
            <table className="w-full">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">Member</th>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">Role</th>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">Target</th>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">Achievement</th>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">%</th>
                  <th className="p-3 text-left text-xs uppercase font-bold text-slate-600 tracking-wide">Status</th>
                  <th className="p-3 text-right text-xs uppercase font-bold text-slate-600 tracking-wide">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && <tr><td colSpan={7} className="p-10 text-center text-slate-400">No members match the filter</td></tr>}
                {filtered.map((m) => {
                  const t = m.target;
                  const ach = t?.achievement || {};
                  return (
                    <tr key={m.user.id} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`row-${m.user.id}`}>
                      <td className="p-3">
                        <p className="font-semibold text-slate-800">{m.user.name}</p>
                        <p className="text-xs text-slate-500">{m.user.email}</p>
                      </td>
                      <td className="p-3"><Badge variant="outline" className="text-xs">{m.user.rbac_role?.replace(/_/g, ' ')}</Badge></td>
                      <td className="p-3 text-sm text-slate-700">
                        {t ? `${formatINR(t.targets.revenue)} / ${t.targets.pa_count} PAs` : <span className="italic text-slate-400">Not set</span>}
                      </td>
                      <td className="p-3 text-sm text-slate-700">
                        {t ? `${formatINR(ach.revenue || 0)} / ${ach.pa_count || 0} PAs` : '—'}
                      </td>
                      <td className={`p-3 text-sm font-extrabold ${t ? pctColor(ach.overall_percentage || 0) : 'text-slate-400'}`}>
                        {t ? `${(ach.overall_percentage || 0).toFixed(0)}%` : '—'}
                      </td>
                      <td className="p-3">{t ? <Badge className={`${statusColors[t.status]} uppercase text-[10px] font-bold border`}>{t.status}</Badge> : '—'}</td>
                      <td className="p-3 text-right">
                        <Button size="sm" variant="outline" onClick={() => setEditTarget({ member: m.user, existing: t })} data-testid={`set-target-${m.user.id}`}>
                          {t ? <><Edit className="h-3.5 w-3.5 mr-1" /> Edit</> : <><Plus className="h-3.5 w-3.5 mr-1" /> Set</>}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}
      </div>

      {editTarget && (
        <TargetEditModal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          member={editTarget.member}
          existingTarget={editTarget.existing}
          period={period}
          onSaved={load}
        />
      )}
      <BulkApplyModal
        open={bulkOpen}
        onClose={() => setBulkOpen(false)}
        members={members}
        period={period}
        templates={templates.filter((t) => t.is_active)}
        onApplied={load}
      />
    </div>
  );
}
