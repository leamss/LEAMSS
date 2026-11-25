/**
 * Phase 4B — Admin/Manager Sales Targets Management page.
 *
 * Allows Admin to set and manage individual salesperson targets for
 * daily, weekly, and monthly leads, calls, follow-ups, conversions, and revenue.
 * Displays target vs. actual performance, achievement %, pending targets, and visual dashboards.
 * Includes Performance Reports modal with salesperson and date range filters + CSV export.
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
import {
  ArrowLeft,
  Target,
  Users,
  Sparkles,
  Edit,
  Trash2,
  Plus,
  Layers,
  Calendar,
  IndianRupee,
  Hash,
  Filter,
  PhoneCall,
  UserCheck,
  CheckCircle2,
  TrendingUp,
  FileText,
  Download,
  Clock,
  Activity,
  Award
} from 'lucide-react';

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

const getIsoWeek = (date) => {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
};

// ────────────────────────────────────────────────────────────
// Target Set / Edit Modal
// ────────────────────────────────────────────────────────────
const TargetEditModal = ({ open, onClose, member, period, onSaved, existingTarget }) => {
  const [leads, setLeads] = useState('');
  const [calls, setCalls] = useState('');
  const [followUps, setFollowUps] = useState('');
  const [conversions, setConversions] = useState('');
  const [revenue, setRevenue] = useState('');
  const [paCount, setPaCount] = useState('');
  const [notes, setNotes] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setLeads(existingTarget?.targets?.leads?.toString() || '');
      setCalls(existingTarget?.targets?.calls?.toString() || '');
      setFollowUps(existingTarget?.targets?.follow_ups?.toString() || '');
      setConversions(existingTarget?.targets?.conversions?.toString() || '');
      setRevenue(existingTarget?.targets?.revenue?.toString() || '');
      setPaCount(existingTarget?.targets?.pa_count?.toString() || '');
      setNotes(existingTarget?.notes || '');
      setReason('');
    }
  }, [open, existingTarget]);

  const handleSave = async () => {
    if (existingTarget && reason.trim().length < 5) {
      toast.error('Reason must be at least 5 characters');
      return;
    }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const body = {
        leads: leads ? parseInt(leads, 10) : 0,
        calls: calls ? parseInt(calls, 10) : 0,
        follow_ups: followUps ? parseInt(followUps, 10) : 0,
        conversions: conversions ? parseInt(conversions, 10) : 0,
        revenue: revenue ? parseFloat(revenue) : 0,
        pa_count: paCount ? parseInt(paCount, 10) : 0,
        notes,
      };

      if (existingTarget) {
        await axios.patch(`${API}/sales/targets/${existingTarget.id}`, {
          ...body,
          reason,
        }, { headers });
        toast.success('Salesperson target updated successfully');
      } else {
        await axios.post(`${API}/sales/targets`, {
          user_id: member.id,
          period_type: period.period_type,
          period_year: period.period_year,
          period_month: period.period_type === 'monthly' ? period.period_month : null,
          period_quarter: period.period_type === 'quarterly' ? period.period_quarter : null,
          period_week: period.period_type === 'weekly' ? period.period_week : null,
          period_date: period.period_type === 'daily' ? period.period_date : null,
          ...body,
        }, { headers });
        toast.success('Salesperson target created successfully');
      }
      onSaved();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save target');
    } finally {
      setSaving(false);
    }
  };

  const periodLabelStr = useMemo(() => {
    if (period.period_type === 'daily') return period.period_date;
    if (period.period_type === 'weekly') return `Week ${period.period_week}, ${period.period_year}`;
    if (period.period_type === 'monthly') return `${monthNames[period.period_month]} ${period.period_year}`;
    return `Q${period.period_quarter} ${period.period_year}`;
  }, [period]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto" data-testid="target-edit-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-leamss-teal-600" />
            {existingTarget ? 'Edit Salesperson Target' : 'Set Salesperson Target'}
          </DialogTitle>
          <DialogDescription>
            Target for <strong>{member?.name}</strong> · <Badge variant="secondary" className="uppercase text-xs">{period.period_type}</Badge> ({periodLabelStr})
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-2">
          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <UserCheck className="h-3.5 w-3.5 text-blue-600" /> Leads Target
            </Label>
            <Input
              type="number"
              min="0"
              value={leads}
              onChange={(e) => setLeads(e.target.value)}
              placeholder="e.g. 15"
              data-testid="input-leads"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <PhoneCall className="h-3.5 w-3.5 text-emerald-600" /> Calls Target
            </Label>
            <Input
              type="number"
              min="0"
              value={calls}
              onChange={(e) => setCalls(e.target.value)}
              placeholder="e.g. 40"
              data-testid="input-calls"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <Clock className="h-3.5 w-3.5 text-amber-600" /> Follow-ups Target
            </Label>
            <Input
              type="number"
              min="0"
              value={followUps}
              onChange={(e) => setFollowUps(e.target.value)}
              placeholder="e.g. 20"
              data-testid="input-follow-ups"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <CheckCircle2 className="h-3.5 w-3.5 text-indigo-600" /> Conversions Target
            </Label>
            <Input
              type="number"
              min="0"
              value={conversions}
              onChange={(e) => setConversions(e.target.value)}
              placeholder="e.g. 5"
              data-testid="input-conversions"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <IndianRupee className="h-3.5 w-3.5 text-teal-600" /> Revenue Target (₹)
            </Label>
            <Input
              type="number"
              min="0"
              value={revenue}
              onChange={(e) => setRevenue(e.target.value)}
              placeholder="e.g. 250000"
              data-testid="input-revenue"
            />
            {revenue && <p className="text-[11px] text-slate-500">{formatINR(parseFloat(revenue))}</p>}
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <Hash className="h-3.5 w-3.5 text-purple-600" /> Closed Deals / PA Count Target
            </Label>
            <Input
              type="number"
              min="0"
              value={paCount}
              onChange={(e) => setPaCount(e.target.value)}
              placeholder="e.g. 3"
              data-testid="input-pa-count"
            />
          </div>
        </div>

        <div className="space-y-3 pt-2">
          <div>
            <Label className="text-xs font-bold text-slate-700">Notes / Instructions (optional)</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Special instructions or context for this target…"
              rows={2}
              data-testid="input-notes"
            />
          </div>

          {existingTarget && (
            <div>
              <Label className="text-xs font-bold text-amber-700">Reason for change (required for audit) *</Label>
              <Textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Min 5 characters — explain why this target is being adjusted"
                rows={2}
                data-testid="input-reason"
              />
            </div>
          )}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose} data-testid="cancel-edit">Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-target">
            {saving ? 'Saving…' : (existingTarget ? 'Update Target' : 'Set Target')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ────────────────────────────────────────────────────────────
// Bulk Apply Template Modal
// ────────────────────────────────────────────────────────────
const BulkApplyModal = ({ open, onClose, members, period, templates, onApplied }) => {
  const [tplId, setTplId] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [overrideExisting, setOverrideExisting] = useState(false);
  const [applying, setApplying] = useState(false);

  useEffect(() => { if (open) { setTplId(''); setSelectedIds([]); setOverrideExisting(false); } }, [open]);

  const toggle = (id) => setSelectedIds((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const toggleAll = () => setSelectedIds(selectedIds.length === members.length ? [] : members.map((m) => m.user.id));

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
          <DialogDescription>Apply a target template to multiple sales team members at once.</DialogDescription>
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
            <div className="flex items-center justify-between mb-1.5">
              <Label className="text-sm font-bold">Salespersons ({selectedIds.length} of {members.length} selected)</Label>
              <button type="button" onClick={toggleAll} className="text-xs text-leamss-teal-600 hover:underline font-semibold">
                {selectedIds.length === members.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>
            <div className="border rounded-md max-h-60 overflow-y-auto divide-y" data-testid="bulk-users-list">
              {members.map((m) => (
                <div key={m.user.id} className="flex items-center gap-3 p-2.5 hover:bg-slate-50 transition">
                  <Checkbox checked={selectedIds.includes(m.user.id)} onCheckedChange={() => toggle(m.user.id)} data-testid={`bulk-checkbox-${m.user.id}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{m.user.name}</p>
                    <p className="text-xs text-slate-500 truncate">{m.user.email}</p>
                  </div>
                  <Badge variant="outline" className="text-xs">{m.user.rbac_role?.replace(/_/g, ' ')}</Badge>
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
            {applying ? 'Applying…' : `Apply to ${selectedIds.length} salesperson${selectedIds.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ────────────────────────────────────────────────────────────
// Performance Reports Modal with Filters & CSV Export
// ────────────────────────────────────────────────────────────
const PerformanceReportsModal = ({ open, onClose, members }) => {
  const [salespersonId, setSalespersonId] = useState('all');
  const [periodTypeFilter, setPeriodTypeFilter] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        salesperson_id: salespersonId,
        period_type: periodTypeFilter,
        ...(startDate ? { start_date: startDate } : {}),
        ...(endDate ? { end_date: endDate } : {}),
      });
      const res = await axios.get(`${API}/sales/targets/reports?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setReportData(res.data);
    } catch (e) {
      toast.error('Failed to generate report');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchReport();
    }
  }, [open, salespersonId, periodTypeFilter, startDate, endDate]);

  const handleExportCSV = () => {
    const token = localStorage.getItem('token');
    const params = new URLSearchParams({
      salesperson_id: salespersonId,
      period_type: periodTypeFilter,
      format: 'csv',
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
    });
    const url = `${API}/sales/targets/reports?${params}`;
    window.open(url, '_blank');
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto" data-testid="performance-reports-modal">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                <FileText className="h-5 w-5 text-leamss-teal-600" /> Sales Performance Reports
              </DialogTitle>
              <DialogDescription>
                Detailed Target vs. Actual performance analysis, pending targets, and activity achievement.
              </DialogDescription>
            </div>
            <Button onClick={handleExportCSV} variant="outline" className="flex items-center gap-1.5" data-testid="export-csv-btn">
              <Download className="h-4 w-4 text-slate-600" /> Export CSV
            </Button>
          </div>
        </DialogHeader>

        {/* Filter bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 bg-slate-50 border rounded-lg">
          <div>
            <Label className="text-xs font-bold text-slate-600">Salesperson</Label>
            <Select value={salespersonId} onValueChange={setSalespersonId}>
              <SelectTrigger className="h-9"><SelectValue placeholder="All Salespersons" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sales Team Members</SelectItem>
                {members.map((m) => (
                  <SelectItem key={m.user.id} value={m.user.id}>{m.user.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs font-bold text-slate-600">Frequency / Period</Label>
            <Select value={periodTypeFilter} onValueChange={setPeriodTypeFilter}>
              <SelectTrigger className="h-9"><SelectValue placeholder="All Frequencies" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Periods</SelectItem>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="quarterly">Quarterly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs font-bold text-slate-600">From Date</Label>
            <Input
              type="date"
              className="h-9"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div>
            <Label className="text-xs font-bold text-slate-600">To Date</Label>
            <Input
              type="date"
              className="h-9"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>

        {/* Summary Metric Cards */}
        {reportData?.summary && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 py-2">
            <Card className="p-3 bg-blue-50/50 border-blue-200">
              <p className="text-xs text-blue-700 font-bold uppercase tracking-wide">Leads</p>
              <p className="text-lg font-black text-slate-800 mt-1">
                {reportData.summary.actuals.leads} <span className="text-xs font-normal text-slate-500">/ {reportData.summary.targets.leads}</span>
              </p>
              <p className="text-[11px] text-slate-600 font-medium">Pending: {reportData.summary.pending.leads}</p>
            </Card>

            <Card className="p-3 bg-emerald-50/50 border-emerald-200">
              <p className="text-xs text-emerald-700 font-bold uppercase tracking-wide">Calls</p>
              <p className="text-lg font-black text-slate-800 mt-1">
                {reportData.summary.actuals.calls} <span className="text-xs font-normal text-slate-500">/ {reportData.summary.targets.calls}</span>
              </p>
              <p className="text-[11px] text-slate-600 font-medium">Pending: {reportData.summary.pending.calls}</p>
            </Card>

            <Card className="p-3 bg-amber-50/50 border-amber-200">
              <p className="text-xs text-amber-700 font-bold uppercase tracking-wide">Follow-ups</p>
              <p className="text-lg font-black text-slate-800 mt-1">
                {reportData.summary.actuals.follow_ups} <span className="text-xs font-normal text-slate-500">/ {reportData.summary.targets.follow_ups}</span>
              </p>
              <p className="text-[11px] text-slate-600 font-medium">Pending: {reportData.summary.pending.follow_ups}</p>
            </Card>

            <Card className="p-3 bg-purple-50/50 border-purple-200">
              <p className="text-xs text-purple-700 font-bold uppercase tracking-wide">Conversions</p>
              <p className="text-lg font-black text-slate-800 mt-1">
                {reportData.summary.actuals.conversions} <span className="text-xs font-normal text-slate-500">/ {reportData.summary.targets.conversions}</span>
              </p>
              <p className="text-[11px] text-slate-600 font-medium">Pending: {reportData.summary.pending.conversions}</p>
            </Card>

            <Card className="p-3 bg-teal-50/50 border-teal-200">
              <p className="text-xs text-teal-700 font-bold uppercase tracking-wide">Revenue</p>
              <p className="text-lg font-black text-slate-800 mt-1">
                {formatINR(reportData.summary.actuals.revenue)}
              </p>
              <p className="text-[11px] text-slate-600 font-medium">Goal: {formatINR(reportData.summary.targets.revenue)}</p>
            </Card>
          </div>
        )}

        {/* Report rows table */}
        <div className="border rounded-md overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 border-b text-slate-700 font-bold uppercase tracking-wider">
              <tr>
                <th className="p-2.5">Salesperson</th>
                <th className="p-2.5">Period</th>
                <th className="p-2.5">Leads (T / A / P / %)</th>
                <th className="p-2.5">Calls (T / A / P / %)</th>
                <th className="p-2.5">Follow-ups (T / A / P / %)</th>
                <th className="p-2.5">Conversions (T / A / P / %)</th>
                <th className="p-2.5">Revenue (T / A / P / %)</th>
                <th className="p-2.5">Overall %</th>
                <th className="p-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">Loading performance report…</td>
                </tr>
              ) : reportData?.rows?.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">No targets found matching selected filters.</td>
                </tr>
              ) : (
                reportData?.rows?.map((r) => {
                  const tg = r.targets || {};
                  const ach = r.achievement || {};
                  const pnd = ach.pending || {};
                  return (
                    <tr key={r.id} className="hover:bg-slate-50 transition">
                      <td className="p-2.5">
                        <p className="font-bold text-slate-800">{r.user_name}</p>
                        <p className="text-[11px] text-slate-500">{r.user_role?.replace(/_/g, ' ')}</p>
                      </td>
                      <td className="p-2.5">
                        <Badge variant="outline" className="text-[10px] uppercase font-semibold">{r.period_type}</Badge>
                        <p className="text-slate-600 mt-0.5">{r.period_label}</p>
                      </td>
                      <td className="p-2.5">
                        <span className="font-semibold">{tg.leads || 0}</span> / <span className="text-blue-600 font-bold">{ach.leads || 0}</span> / <span className="text-slate-500">{pnd.leads || 0}</span>
                        <div className="text-[10px] font-bold text-blue-700">{(ach.leads_percentage || 0).toFixed(0)}%</div>
                      </td>
                      <td className="p-2.5">
                        <span className="font-semibold">{tg.calls || 0}</span> / <span className="text-emerald-600 font-bold">{ach.calls || 0}</span> / <span className="text-slate-500">{pnd.calls || 0}</span>
                        <div className="text-[10px] font-bold text-emerald-700">{(ach.calls_percentage || 0).toFixed(0)}%</div>
                      </td>
                      <td className="p-2.5">
                        <span className="font-semibold">{tg.follow_ups || 0}</span> / <span className="text-amber-600 font-bold">{ach.follow_ups || 0}</span> / <span className="text-slate-500">{pnd.follow_ups || 0}</span>
                        <div className="text-[10px] font-bold text-amber-700">{(ach.follow_ups_percentage || 0).toFixed(0)}%</div>
                      </td>
                      <td className="p-2.5">
                        <span className="font-semibold">{tg.conversions || 0}</span> / <span className="text-purple-600 font-bold">{ach.conversions || 0}</span> / <span className="text-slate-500">{pnd.conversions || 0}</span>
                        <div className="text-[10px] font-bold text-purple-700">{(ach.conversions_percentage || 0).toFixed(0)}%</div>
                      </td>
                      <td className="p-2.5">
                        <span className="font-semibold">{formatINR(tg.revenue || 0)}</span>
                        <div className="text-teal-700 font-bold">Act: {formatINR(ach.revenue || 0)}</div>
                        <div className="text-[10px] text-slate-500">Pend: {formatINR(pnd.revenue || 0)} ({(ach.revenue_percentage || 0).toFixed(0)}%)</div>
                      </td>
                      <td className="p-2.5 font-black text-sm">
                        <span className={pctColor(ach.overall_percentage || 0)}>{(ach.overall_percentage || 0).toFixed(0)}%</span>
                      </td>
                      <td className="p-2.5">
                        <Badge className={`${statusColors[r.status]} uppercase text-[10px] font-bold border`}>
                          {r.status}
                        </Badge>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <DialogFooter className="mt-2">
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ────────────────────────────────────────────────────────────
// Main Admin Sales Targets Page
// ────────────────────────────────────────────────────────────
export default function SalesTargetsAdmin() {
  const navigate = useNavigate();
  const now = new Date();
  const todayStr = now.toISOString().split('T')[0];

  const [periodType, setPeriodType] = useState('monthly');
  const [periodYear, setPeriodYear] = useState(now.getFullYear());
  const [periodMonth, setPeriodMonth] = useState(now.getMonth() + 1);
  const [periodQuarter, setPeriodQuarter] = useState(Math.floor(now.getMonth() / 3) + 1);
  const [periodWeek, setPeriodWeek] = useState(getIsoWeek(now));
  const [periodDate, setPeriodDate] = useState(todayStr);

  const [members, setMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  const [editTarget, setEditTarget] = useState(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [reportsOpen, setReportsOpen] = useState(false);

  const period = useMemo(() => ({
    period_type: periodType,
    period_year: periodYear,
    period_month: periodMonth,
    period_quarter: periodQuarter,
    period_week: periodWeek,
    period_date: periodDate,
  }), [periodType, periodYear, periodMonth, periodQuarter, periodWeek, periodDate]);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const params = new URLSearchParams({
        period_type: periodType,
        year: periodYear.toString(),
        ...(periodType === 'daily' ? { date: periodDate } : {}),
        ...(periodType === 'weekly' ? { week: periodWeek.toString() } : {}),
        ...(periodType === 'monthly' ? { month: periodMonth.toString() } : {}),
        ...(periodType === 'quarterly' ? { quarter: periodQuarter.toString() } : {}),
      });

      const [team, tpls] = await Promise.all([
        axios.get(`${API}/sales/targets/department?${params}`, { headers }),
        axios.get(`${API}/sales/target-templates`, { headers }),
      ]);
      setMembers(team.data.members || []);
      setTemplates(tpls.data.templates || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load team targets');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [periodType, periodYear, periodMonth, periodQuarter, periodWeek, periodDate]);

  const filtered = useMemo(() => members.filter((m) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'no_target') return !m.target;
    return m.target?.status === statusFilter;
  }), [members, statusFilter]);

  // Aggregate KPI stats across current team targets
  const aggregateKPIs = useMemo(() => {
    const kpis = {
      leads: { target: 0, actual: 0, pending: 0 },
      calls: { target: 0, actual: 0, pending: 0 },
      follow_ups: { target: 0, actual: 0, pending: 0 },
      conversions: { target: 0, actual: 0, pending: 0 },
      revenue: { target: 0, actual: 0, pending: 0 },
    };

    members.forEach((m) => {
      const tg = m.target?.targets;
      const ach = m.target?.achievement;
      const pnd = ach?.pending;
      if (tg && ach) {
        kpis.leads.target += tg.leads || 0;
        kpis.leads.actual += ach.leads || 0;
        kpis.leads.pending += pnd?.leads != null ? pnd.leads : Math.max(0, (tg.leads || 0) - (ach.leads || 0));

        kpis.calls.target += tg.calls || 0;
        kpis.calls.actual += ach.calls || 0;
        kpis.calls.pending += pnd?.calls != null ? pnd.calls : Math.max(0, (tg.calls || 0) - (ach.calls || 0));

        kpis.follow_ups.target += tg.follow_ups || 0;
        kpis.follow_ups.actual += ach.follow_ups || 0;
        kpis.follow_ups.pending += pnd?.follow_ups != null ? pnd.follow_ups : Math.max(0, (tg.follow_ups || 0) - (ach.follow_ups || 0));

        kpis.conversions.target += tg.conversions || 0;
        kpis.conversions.actual += ach.conversions || 0;
        kpis.conversions.pending += pnd?.conversions != null ? pnd.conversions : Math.max(0, (tg.conversions || 0) - (ach.conversions || 0));

        kpis.revenue.target += tg.revenue || 0;
        kpis.revenue.actual += ach.revenue || 0;
        kpis.revenue.pending += pnd?.revenue != null ? pnd.revenue : Math.max(0, (tg.revenue || 0) - (ach.revenue || 0));
      }
    });

    return kpis;
  }, [members]);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="sales-targets-admin-page">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/admin'))}
              className="p-2 rounded-lg hover:bg-slate-200 transition"
              data-testid="back-to-admin"
            >
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Target className="h-7 w-7 text-leamss-teal-600" /> Salesperson Target Management
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Configure daily, weekly, monthly targets for Leads, Calls, Follow-ups, Conversions & Revenue
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => setReportsOpen(true)}
              variant="outline"
              className="border-leamss-teal-300 text-leamss-teal-700 hover:bg-leamss-teal-50"
              data-testid="performance-reports-btn"
            >
              <FileText className="h-4 w-4 mr-1.5" /> Performance Reports
            </Button>
            <Button
              onClick={() => navigate('/admin/sales/target-templates')}
              variant="outline"
              data-testid="manage-templates-btn"
            >
              <Layers className="h-4 w-4 mr-1.5" /> Templates
            </Button>
            <Button
              onClick={() => setBulkOpen(true)}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
              data-testid="bulk-apply-btn"
            >
              <Plus className="h-4 w-4 mr-1.5" /> Bulk Apply
            </Button>
          </div>
        </div>

        {/* Activity KPI Dashboards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" data-testid="kpi-dashboards">
          {/* Leads KPI */}
          <Card className="p-3.5 bg-gradient-to-br from-blue-50/70 to-white border-blue-200 shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-blue-700 uppercase tracking-wide flex items-center gap-1">
                <UserCheck className="h-3.5 w-3.5" /> Leads
              </span>
              <Badge variant="secondary" className="text-[10px] font-bold">
                {aggregateKPIs.leads.target > 0
                  ? `${Math.round((aggregateKPIs.leads.actual / aggregateKPIs.leads.target) * 100)}%`
                  : '0%'}
              </Badge>
            </div>
            <p className="text-2xl font-black text-slate-800">
              {aggregateKPIs.leads.actual}{' '}
              <span className="text-xs font-normal text-slate-500">/ {aggregateKPIs.leads.target}</span>
            </p>
            <p className="text-[11px] text-slate-600 mt-1">
              Pending: <strong className="text-amber-700">{aggregateKPIs.leads.pending}</strong>
            </p>
          </Card>

          {/* Calls KPI */}
          <Card className="p-3.5 bg-gradient-to-br from-emerald-50/70 to-white border-emerald-200 shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-emerald-700 uppercase tracking-wide flex items-center gap-1">
                <PhoneCall className="h-3.5 w-3.5" /> Calls
              </span>
              <Badge variant="secondary" className="text-[10px] font-bold">
                {aggregateKPIs.calls.target > 0
                  ? `${Math.round((aggregateKPIs.calls.actual / aggregateKPIs.calls.target) * 100)}%`
                  : '0%'}
              </Badge>
            </div>
            <p className="text-2xl font-black text-slate-800">
              {aggregateKPIs.calls.actual}{' '}
              <span className="text-xs font-normal text-slate-500">/ {aggregateKPIs.calls.target}</span>
            </p>
            <p className="text-[11px] text-slate-600 mt-1">
              Pending: <strong className="text-amber-700">{aggregateKPIs.calls.pending}</strong>
            </p>
          </Card>

          {/* Follow-ups KPI */}
          <Card className="p-3.5 bg-gradient-to-br from-amber-50/70 to-white border-amber-200 shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-amber-700 uppercase tracking-wide flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" /> Follow-ups
              </span>
              <Badge variant="secondary" className="text-[10px] font-bold">
                {aggregateKPIs.follow_ups.target > 0
                  ? `${Math.round((aggregateKPIs.follow_ups.actual / aggregateKPIs.follow_ups.target) * 100)}%`
                  : '0%'}
              </Badge>
            </div>
            <p className="text-2xl font-black text-slate-800">
              {aggregateKPIs.follow_ups.actual}{' '}
              <span className="text-xs font-normal text-slate-500">/ {aggregateKPIs.follow_ups.target}</span>
            </p>
            <p className="text-[11px] text-slate-600 mt-1">
              Pending: <strong className="text-amber-700">{aggregateKPIs.follow_ups.pending}</strong>
            </p>
          </Card>

          {/* Conversions KPI */}
          <Card className="p-3.5 bg-gradient-to-br from-purple-50/70 to-white border-purple-200 shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-purple-700 uppercase tracking-wide flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Conversions
              </span>
              <Badge variant="secondary" className="text-[10px] font-bold">
                {aggregateKPIs.conversions.target > 0
                  ? `${Math.round((aggregateKPIs.conversions.actual / aggregateKPIs.conversions.target) * 100)}%`
                  : '0%'}
              </Badge>
            </div>
            <p className="text-2xl font-black text-slate-800">
              {aggregateKPIs.conversions.actual}{' '}
              <span className="text-xs font-normal text-slate-500">/ {aggregateKPIs.conversions.target}</span>
            </p>
            <p className="text-[11px] text-slate-600 mt-1">
              Pending: <strong className="text-amber-700">{aggregateKPIs.conversions.pending}</strong>
            </p>
          </Card>

          {/* Revenue KPI */}
          <Card className="p-3.5 bg-gradient-to-br from-teal-50/70 to-white border-teal-200 shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-teal-700 uppercase tracking-wide flex items-center gap-1">
                <IndianRupee className="h-3.5 w-3.5" /> Revenue
              </span>
              <Badge variant="secondary" className="text-[10px] font-bold">
                {aggregateKPIs.revenue.target > 0
                  ? `${Math.round((aggregateKPIs.revenue.actual / aggregateKPIs.revenue.target) * 100)}%`
                  : '0%'}
              </Badge>
            </div>
            <p className="text-lg font-black text-slate-800 truncate">
              {formatINR(aggregateKPIs.revenue.actual)}
            </p>
            <p className="text-[11px] text-slate-600 mt-1 truncate">
              Goal: {formatINR(aggregateKPIs.revenue.target)}
            </p>
          </Card>
        </div>

        {/* Period Selector Bar */}
        <Card className="p-4 flex flex-wrap items-center gap-3 bg-white" data-testid="period-selector">
          <Calendar className="h-4 w-4 text-slate-500" />
          <Select value={periodType} onValueChange={setPeriodType}>
            <SelectTrigger className="w-32 font-medium" data-testid="period-type-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="quarterly">Quarterly</SelectItem>
            </SelectContent>
          </Select>

          {periodType === 'daily' && (
            <Input
              type="date"
              className="w-44"
              value={periodDate}
              onChange={(e) => setPeriodDate(e.target.value)}
              data-testid="input-period-date"
            />
          )}

          {periodType === 'weekly' && (
            <>
              <Select value={periodYear.toString()} onValueChange={(v) => setPeriodYear(parseInt(v, 10))}>
                <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={periodWeek.toString()} onValueChange={(v) => setPeriodWeek(parseInt(v, 10))}>
                <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                <SelectContent className="max-h-56">
                  {Array.from({ length: 52 }, (_, i) => i + 1).map((w) => (
                    <SelectItem key={w} value={w.toString()}>{`Week ${w}`}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}

          {periodType === 'monthly' && (
            <>
              <Select value={periodYear.toString()} onValueChange={(v) => setPeriodYear(parseInt(v, 10))}>
                <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={periodMonth.toString()} onValueChange={(v) => setPeriodMonth(parseInt(v, 10))}>
                <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {monthNames.slice(1).map((m, i) => (
                    <SelectItem key={i + 1} value={(i + 1).toString()}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}

          {periodType === 'quarterly' && (
            <>
              <Select value={periodYear.toString()} onValueChange={(v) => setPeriodYear(parseInt(v, 10))}>
                <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={periodQuarter.toString()} onValueChange={(v) => setPeriodQuarter(parseInt(v, 10))}>
                <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4].map((q) => (
                    <SelectItem key={q} value={q.toString()}>{`Q${q}`}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}

          <div className="ml-auto flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40" data-testid="status-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="exceeded">Exceeded</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="missed">Missed</SelectItem>
                <SelectItem value="no_target">No Target Set</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Sales Team Targets Grid */}
        {loading ? (
          <Card className="p-12 text-center">
            <Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" />
            <p className="text-slate-500">Loading sales team targets…</p>
          </Card>
        ) : (
          <Card className="p-0 overflow-hidden shadow-sm" data-testid="team-targets-table">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-100 border-b text-slate-700 text-xs uppercase tracking-wider font-bold">
                  <tr>
                    <th className="p-3">Salesperson</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Target Metrics (L / C / F / Conv / Rev)</th>
                    <th className="p-3">Actuals Achieved</th>
                    <th className="p-3">Pending Targets</th>
                    <th className="p-3">Achievement %</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={8} className="p-10 text-center text-slate-400">
                        No team members found for this filter.
                      </td>
                    </tr>
                  )}
                  {filtered.map((m) => {
                    const t = m.target;
                    const tg = t?.targets || {};
                    const ach = t?.achievement || {};
                    const pnd = ach?.pending || {};
                    return (
                      <tr key={m.user.id} className="hover:bg-slate-50 transition" data-testid={`row-${m.user.id}`}>
                        <td className="p-3">
                          <p className="font-bold text-slate-800">{m.user.name}</p>
                          <p className="text-xs text-slate-500">{m.user.email}</p>
                        </td>

                        <td className="p-3">
                          <Badge variant="outline" className="text-xs">
                            {m.user.rbac_role?.replace(/_/g, ' ')}
                          </Badge>
                        </td>

                        <td className="p-3 text-xs text-slate-700">
                          {t ? (
                            <div className="space-y-0.5">
                              <p>
                                Leads: <strong className="text-blue-700">{tg.leads || 0}</strong> · Calls: <strong className="text-emerald-700">{tg.calls || 0}</strong>
                              </p>
                              <p>
                                F-ups: <strong className="text-amber-700">{tg.follow_ups || 0}</strong> · Conv: <strong className="text-purple-700">{tg.conversions || 0}</strong>
                              </p>
                              <p className="text-teal-700 font-semibold">{formatINR(tg.revenue || 0)}</p>
                            </div>
                          ) : (
                            <span className="italic text-slate-400">No target configured</span>
                          )}
                        </td>

                        <td className="p-3 text-xs text-slate-700">
                          {t ? (
                            <div className="space-y-0.5">
                              <p>
                                Leads: <span className="text-blue-700 font-bold">{ach.leads || 0}</span> · Calls: <span className="text-emerald-700 font-bold">{ach.calls || 0}</span>
                              </p>
                              <p>
                                F-ups: <span className="text-amber-700 font-bold">{ach.follow_ups || 0}</span> · Conv: <span className="text-purple-700 font-bold">{ach.conversions || 0}</span>
                              </p>
                              <p className="text-teal-700 font-bold">{formatINR(ach.revenue || 0)}</p>
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>

                        <td className="p-3 text-xs text-slate-700">
                          {t ? (
                            <div className="space-y-0.5">
                              <p>
                                Leads: <strong className="text-rose-600">{pnd.leads || 0}</strong> · Calls: <strong className="text-rose-600">{pnd.calls || 0}</strong>
                              </p>
                              <p>
                                F-ups: <strong className="text-rose-600">{pnd.follow_ups || 0}</strong> · Conv: <strong className="text-rose-600">{pnd.conversions || 0}</strong>
                              </p>
                              <p className="text-rose-600 font-semibold">{formatINR(pnd.revenue || 0)}</p>
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>

                        <td className={`p-3 text-sm font-extrabold ${t ? pctColor(ach.overall_percentage || 0) : 'text-slate-400'}`}>
                          {t ? `${(ach.overall_percentage || 0).toFixed(0)}%` : '—'}
                        </td>

                        <td className="p-3">
                          {t ? (
                            <Badge className={`${statusColors[t.status]} uppercase text-[10px] font-bold border`}>
                              {t.status}
                            </Badge>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Unassigned</span>
                          )}
                        </td>

                        <td className="p-3 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditTarget({ member: m.user, existing: t })}
                            className="border-slate-300 hover:bg-leamss-teal-50 hover:text-leamss-teal-700"
                            data-testid={`set-target-${m.user.id}`}
                          >
                            {t ? <><Edit className="h-3.5 w-3.5 mr-1" /> Edit</> : <><Plus className="h-3.5 w-3.5 mr-1" /> Set</>}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
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

      <PerformanceReportsModal
        open={reportsOpen}
        onClose={() => setReportsOpen(false)}
        members={members}
      />
    </div>
  );
}
