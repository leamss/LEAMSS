/**
 * Phase 22 Slice 22.3 — Payroll Admin Hub
 * UI for: bulk payslip generation, payslip list with filters, approve, mark-paid.
 * Backend `/api/payroll/*` + `/api/payslips/*` already exists (Slice 2).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Wallet, Receipt, CheckCircle2, Download, FileText } from 'lucide-react';
import DashboardShell from '@/components/DashboardShell';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STATUS_BG = {
  draft: 'bg-slate-100 text-slate-700',
  generated: 'bg-leamss-orange-100 text-leamss-orange-700',
  approved: 'bg-sky-100 text-sky-700',
  paid: 'bg-emerald-100 text-emerald-700',
};

export default function PayrollAdminHub() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [payslips, setPayslips] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [filterPeriod, setFilterPeriod] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(true);

  const [genOpen, setGenOpen] = useState(false);
  const [genPeriod, setGenPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [genSelectedIds, setGenSelectedIds] = useState(new Set());
  const [generating, setGenerating] = useState(false);

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [m, p, e] = await Promise.all([
        axios.get(`${API}/auth/me`, auth),
        axios.get(`${API}/payslips${filterPeriod ? `?period=${filterPeriod}` : ''}`, auth),
        axios.get(`${API}/employees?limit=100`, auth),
      ]);
      setMe(m.data);
      let items = p.data || [];
      if (filterStatus !== 'all') items = items.filter(x => x.status === filterStatus);
      setPayslips(items);
      setEmployees(Array.isArray(e.data) ? e.data : e.data?.items || []);
    } catch (err) {
      if (err?.response?.status === 401) navigate('/');
    } finally { setLoading(false); }
  }, [filterPeriod, filterStatus, navigate]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (!token) { navigate('/'); return; } loadAll(); }, [token, navigate, loadAll]);

  const toggleEmpForGen = (id) => {
    const s = new Set(genSelectedIds);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setGenSelectedIds(s);
  };

  const handleBulkGenerate = async () => {
    if (!genPeriod || genSelectedIds.size === 0) {
      toast.error('Pick period and at least one employee');
      return;
    }
    setGenerating(true);
    try {
      const { data } = await axios.post(`${API}/payslips/generate`, {
        employee_ids: [...genSelectedIds],
        period: genPeriod,
      }, auth);
      toast.success(`Generated ${data?.generated || 0} payslips`);
      setGenOpen(false);
      setGenSelectedIds(new Set());
      await loadAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Generation failed');
    } finally { setGenerating(false); }
  };

  const handleApprove = async (id) => {
    try {
      await axios.patch(`${API}/payslips/${id}/approve`, {}, auth);
      toast.success('Approved');
      await loadAll();
    } catch (err) { toast.error('Approve failed'); }
  };

  const handleMarkPaid = async (id) => {
    const ref = window.prompt('Payment reference (UTR / cheque #):');
    if (!ref) return;
    try {
      await axios.patch(`${API}/payslips/${id}/mark-paid`, { payment_reference: ref }, auth);
      toast.success('Marked paid');
      await loadAll();
    } catch (err) { toast.error('Mark-paid failed'); }
  };

  const downloadPdf = (id) => {
    window.open(`${API}/payslips/${id}/pdf`, '_blank');
  };

  const empName = (eid) => {
    const e = employees.find(x => (x.id || x.user_id) === eid);
    return e?.name || e?.email || eid?.slice(0, 8);
  };

  if (!me) return null;

  // KPI computations
  const totalGross = payslips.reduce((s, p) => s + (p.gross_inr || 0), 0);
  const totalNet = payslips.reduce((s, p) => s + (p.net_pay_inr || 0), 0);
  const paidCount = payslips.filter(p => p.status === 'paid').length;
  const pendingCount = payslips.length - paidCount;

  return (
    <DashboardShell user={me} onLogout={() => { localStorage.removeItem('token'); navigate('/'); }} pageTitle="Payroll Admin">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-5 space-y-4" data-testid="payroll-admin-hub">
        {/* Header + KPIs */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-xl font-bold text-leamss-teal-800 flex items-center gap-2">
            <Wallet className="h-5 w-5" /> Payroll Admin Hub
          </h1>
          <Button
            onClick={() => setGenOpen(true)}
            className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
            data-testid="payroll-bulk-generate-btn"
          >
            <Receipt className="h-4 w-4 mr-1" /> Bulk Generate Payslips
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="p-3 bg-leamss-teal-50 border-leamss-teal-200">
            <div className="text-xs text-leamss-teal-700">Total payslips</div>
            <div className="text-2xl font-bold text-leamss-teal-900" data-testid="payroll-kpi-total">{payslips.length}</div>
          </Card>
          <Card className="p-3 bg-emerald-50 border-emerald-200">
            <div className="text-xs text-emerald-700">Paid</div>
            <div className="text-2xl font-bold text-emerald-900" data-testid="payroll-kpi-paid">{paidCount}</div>
          </Card>
          <Card className="p-3 bg-leamss-orange-50 border-leamss-orange-200">
            <div className="text-xs text-leamss-orange-700">Pending</div>
            <div className="text-2xl font-bold text-leamss-orange-900" data-testid="payroll-kpi-pending">{pendingCount}</div>
          </Card>
          <Card className="p-3 bg-sky-50 border-sky-200">
            <div className="text-xs text-sky-700">Net total (₹)</div>
            <div className="text-2xl font-bold text-sky-900" data-testid="payroll-kpi-net">₹{totalNet.toLocaleString('en-IN')}</div>
            <div className="text-[10px] text-sky-600">gross ₹{totalGross.toLocaleString('en-IN')}</div>
          </Card>
        </div>

        {/* Filter row */}
        <Card className="p-3 flex items-center gap-3 flex-wrap">
          <Input
            type="month"
            value={filterPeriod}
            onChange={(e) => setFilterPeriod(e.target.value)}
            className="w-40"
            placeholder="Period (YYYY-MM)"
            data-testid="payroll-filter-period"
          />
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-32" data-testid="payroll-filter-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="generated">Generated</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadAll} data-testid="payroll-refresh-btn">Refresh</Button>
        </Card>

        {/* Payslips list */}
        <Card className="p-3" data-testid="payroll-list">
          {loading && <p className="text-sm text-slate-500">Loading…</p>}
          {!loading && payslips.length === 0 && (
            <div className="text-center py-10 text-slate-400 text-sm">
              Koi payslip nahi mili. Bulk Generate se naye payslips banao.
            </div>
          )}
          <div className="space-y-2">
            {payslips.map(p => (
              <div
                key={p.id}
                className="flex items-center justify-between gap-3 p-3 border border-slate-200 rounded hover:border-leamss-teal-300 transition-all flex-wrap"
                data-testid={`payroll-row-${p.id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-800 text-sm">{empName(p.employee_id)}</span>
                    <Badge className="bg-slate-100 text-slate-700 text-[10px]">{p.period}</Badge>
                    <Badge className={`${STATUS_BG[p.status] || 'bg-slate-100 text-slate-700'} text-[10px]`}>{p.status}</Badge>
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Gross ₹{(p.gross_inr || 0).toLocaleString('en-IN')} ·
                    Deduct ₹{(p.total_deductions_inr || 0).toLocaleString('en-IN')} ·
                    <span className="font-semibold text-emerald-700"> Net ₹{(p.net_pay_inr || 0).toLocaleString('en-IN')}</span>
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => downloadPdf(p.id)} title="Download PDF" data-testid={`payroll-pdf-${p.id}`}>
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  {p.status === 'generated' && (
                    <Button size="sm" variant="outline" onClick={() => handleApprove(p.id)} data-testid={`payroll-approve-${p.id}`}>
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Approve
                    </Button>
                  )}
                  {p.status === 'approved' && (
                    <Button
                      size="sm"
                      onClick={() => handleMarkPaid(p.id)}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      data-testid={`payroll-mark-paid-${p.id}`}
                    >
                      <FileText className="h-3.5 w-3.5 mr-1" /> Mark Paid
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Bulk Generate Dialog */}
      <Dialog open={genOpen} onOpenChange={setGenOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="payroll-gen-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Generate Payslips</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-600 font-semibold">Period (YYYY-MM)</label>
              <Input
                type="month"
                value={genPeriod}
                onChange={(e) => setGenPeriod(e.target.value)}
                data-testid="payroll-gen-period"
              />
            </div>
            <div>
              <label className="text-xs text-slate-600 font-semibold mb-1 block">
                Employees ({genSelectedIds.size} selected)
                <button
                  onClick={() => {
                    if (genSelectedIds.size === employees.length) setGenSelectedIds(new Set());
                    else setGenSelectedIds(new Set(employees.map(e => e.id || e.user_id)));
                  }}
                  className="ml-2 text-leamss-teal-600 text-[10px] underline"
                  data-testid="payroll-gen-toggle-all"
                >
                  {genSelectedIds.size === employees.length ? 'Deselect All' : 'Select All'}
                </button>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 max-h-60 overflow-y-auto border border-slate-200 rounded p-2">
                {employees.map(e => {
                  const eid = e.id || e.user_id;
                  return (
                    <label key={eid} className="flex items-center gap-2 text-xs p-1 hover:bg-slate-50">
                      <input
                        type="checkbox"
                        checked={genSelectedIds.has(eid)}
                        onChange={() => toggleEmpForGen(eid)}
                        data-testid={`payroll-gen-emp-${eid}`}
                      />
                      <span className="font-medium">{e.name || e.email}</span>
                      <span className="text-slate-400 text-[10px]">{e.department || '—'}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGenOpen(false)}>Cancel</Button>
            <Button
              onClick={handleBulkGenerate}
              disabled={generating || !genPeriod || genSelectedIds.size === 0}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
              data-testid="payroll-gen-submit"
            >
              {generating ? 'Generating…' : `Generate ${genSelectedIds.size} payslips`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
}
