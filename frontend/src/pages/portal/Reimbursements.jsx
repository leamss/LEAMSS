import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  ArrowLeft, Receipt, Plus, Check, X, Clock, Wallet, AlertCircle,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CATEGORIES = [
  'travel', 'food', 'office_supplies', 'client_entertainment',
  'phone', 'internet', 'medical', 'other',
];

const STATUS_BADGE = {
  submitted: 'bg-amber-100 text-amber-700',
  manager_approved: 'bg-sky-100 text-sky-700',
  hr_approved: 'bg-emerald-100 text-emerald-700',
  reimbursed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-leamss-red-100 text-leamss-red-700',
};

/**
 * Phase 21 Slice 3 Day 1 — Reimbursements UI.
 * Single component drives 3 views via `view` prop:
 *   - me   (Employee): submit + see own claims
 *   - team (Manager): approve direct reports
 *   - all  (HR/Admin): see + approve everything
 */
export default function Reimbursements({ view = 'me' }) {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [actionDialog, setActionDialog] = useState({ open: false, claim: null, action: '' });
  const [statusFilter, setStatusFilter] = useState('');

  const [form, setForm] = useState({
    category: 'travel',
    amount_inr: '',
    vendor_name: '',
    description: '',
    expense_date: new Date().toISOString().slice(0, 10),
    bill_url: '',
  });
  const [actionForm, setActionForm] = useState({ notes: '', reason: '' });

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const load = async () => {
    setLoading(true);
    try {
      const me = await axios.get(`${API}/auth/me`, auth);
      setUser(me.data);
      const params = { for_view: view };
      if (statusFilter) params.status = statusFilter;
      const res = await axios.get(`${API}/reimbursements`, { ...auth, params });
      setClaims(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load claims');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (!token) { navigate('/'); return; } load(); /* eslint-disable-next-line */ }, [view, statusFilter]);

  const submitClaim = async () => {
    if (!form.amount_inr || !form.description.trim()) {
      toast.error('Amount and description required');
      return;
    }
    try {
      const payload = {
        category: form.category,
        amount_inr: Number(form.amount_inr),
        vendor_name: form.vendor_name,
        description: form.description,
        expense_date: form.expense_date,
        bills: form.bill_url ? [{ file_url: form.bill_url, file_name: 'bill', mime_type: 'application/pdf' }] : [],
      };
      await axios.post(`${API}/reimbursements`, payload, auth);
      toast.success('Claim submitted');
      setSubmitOpen(false);
      setForm({ category: 'travel', amount_inr: '', vendor_name: '', description: '', expense_date: new Date().toISOString().slice(0, 10), bill_url: '' });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit');
    }
  };

  const doAction = async () => {
    const { claim, action } = actionDialog;
    try {
      const endpoint = action === 'manager-approve' ? `manager-approve`
        : action === 'hr-approve' ? `hr-approve` : `reject`;
      const body = action === 'reject' ? { reason: actionForm.reason } : { notes: actionForm.notes };
      await axios.patch(`${API}/reimbursements/${claim.id}/${endpoint}`, body, auth);
      toast.success('Action completed');
      setActionDialog({ open: false, claim: null, action: '' });
      setActionForm({ notes: '', reason: '' });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Action failed');
    }
  };

  const isManager = (user?.rbac_role || '').match(/manager|lead|head/i);
  const isHR = ['admin', 'admin_owner'].includes(user?.rbac_role) || (user?.rbac_role || '').match(/hr|head/i);

  const headerTitle = view === 'me' ? 'My Reimbursements' : view === 'team' ? 'Team Reimbursements (Manager)' : 'All Reimbursements (HR)';

  return (
    <div className="min-h-screen bg-slate-50" data-testid="reimbursements-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="reimb-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-leamss-orange-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">{headerTitle}</h1>
                <p className="text-xs text-slate-500">{user?.name} · {user?.designation || user?.rbac_role}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Select value={statusFilter || 'all'} onValueChange={v => setStatusFilter(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-40 h-9" data-testid="reimb-status-filter"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All status</SelectItem>
                <SelectItem value="submitted">Submitted</SelectItem>
                <SelectItem value="manager_approved">Manager approved</SelectItem>
                <SelectItem value="hr_approved">HR approved</SelectItem>
                <SelectItem value="reimbursed">Reimbursed</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            {view === 'me' && (
              <Button size="sm" onClick={() => setSubmitOpen(true)} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="reimb-new-btn">
                <Plus className="h-4 w-4 mr-1" /> New claim
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && claims.length === 0 && (
          <Card className="p-8 text-center text-slate-500 italic" data-testid="reimb-empty">No reimbursement claims yet.</Card>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {claims.map(c => (
            <Card key={c.id} className="p-4" data-testid={`claim-${c.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="capitalize text-[10px]">{c.category.replace('_', ' ')}</Badge>
                    <Badge className={`${STATUS_BADGE[c.status] || 'bg-slate-100'} capitalize`}>{c.status.replace('_', ' ')}</Badge>
                    {view !== 'me' && <span className="text-xs text-slate-500">· {c.employee_name}</span>}
                  </div>
                  <p className="text-sm text-slate-800 mt-2 line-clamp-2">{c.description}</p>
                  <p className="text-[10px] text-slate-400 mt-1 inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" /> Expense {c.expense_date}{c.vendor_name ? ` · ${c.vendor_name}` : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-slate-400 uppercase">Amount</p>
                  <p className="text-xl font-bold text-leamss-orange-600">₹ {c.amount_inr?.toLocaleString()}</p>
                </div>
              </div>
              {/* Action row for managers / HR */}
              {(view === 'team' || view === 'all') && c.status === 'submitted' && (
                <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100">
                  <Button size="sm" variant="outline" onClick={() => setActionDialog({ open: true, claim: c, action: 'manager-approve' })} data-testid={`manager-approve-${c.id}`}>
                    <Check className="h-3.5 w-3.5 mr-1" /> Manager approve
                  </Button>
                  {isHR && (
                    <Button size="sm" variant="outline" onClick={() => setActionDialog({ open: true, claim: c, action: 'hr-approve' })} data-testid={`hr-approve-${c.id}`}>
                      <Check className="h-3.5 w-3.5 mr-1" /> HR approve
                    </Button>
                  )}
                  <Button size="sm" variant="outline" className="text-leamss-red-600 border-leamss-red-300 hover:bg-leamss-red-50" onClick={() => setActionDialog({ open: true, claim: c, action: 'reject' })} data-testid={`reject-${c.id}`}>
                    <X className="h-3.5 w-3.5 mr-1" /> Reject
                  </Button>
                </div>
              )}
              {(view === 'all' || view === 'team') && c.status === 'manager_approved' && isHR && (
                <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100">
                  <Button size="sm" onClick={() => setActionDialog({ open: true, claim: c, action: 'hr-approve' })} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid={`hr-approve-${c.id}`}>
                    <Check className="h-3.5 w-3.5 mr-1" /> HR approve & merge into payslip
                  </Button>
                  <Button size="sm" variant="outline" className="text-leamss-red-600" onClick={() => setActionDialog({ open: true, claim: c, action: 'reject' })} data-testid={`reject-${c.id}`}>
                    Reject
                  </Button>
                </div>
              )}
              {c.rejected_reason && (
                <p className="text-[11px] text-leamss-red-600 mt-2 inline-flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> Rejected: {c.rejected_reason}
                </p>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Submit dialog */}
      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>New Reimbursement Claim</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Category</Label>
                <Select value={form.category} onValueChange={v => setForm({ ...form, category: v })}>
                  <SelectTrigger data-testid="claim-category"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => <SelectItem key={c} value={c} className="capitalize">{c.replace('_', ' ')}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Amount (INR)</Label>
                <Input type="number" value={form.amount_inr} onChange={e => setForm({ ...form, amount_inr: e.target.value })} data-testid="claim-amount" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Expense date</Label>
                <Input type="date" value={form.expense_date} onChange={e => setForm({ ...form, expense_date: e.target.value })} data-testid="claim-date" />
              </div>
              <div>
                <Label>Vendor</Label>
                <Input value={form.vendor_name} onChange={e => setForm({ ...form, vendor_name: e.target.value })} placeholder="e.g., Uber, Hotel Taj" data-testid="claim-vendor" />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="What was this expense for?" data-testid="claim-description" />
            </div>
            <div>
              <Label>Bill URL (optional)</Label>
              <Input value={form.bill_url} onChange={e => setForm({ ...form, bill_url: e.target.value })} placeholder="https://drive.google.com/..." data-testid="claim-bill" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSubmitOpen(false)} data-testid="claim-cancel">Cancel</Button>
            <Button onClick={submitClaim} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="claim-submit">Submit claim</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Action dialog */}
      <Dialog open={actionDialog.open} onOpenChange={(o) => setActionDialog(prev => ({ ...prev, open: o }))}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="capitalize">{actionDialog.action.replace('-', ' ')}</DialogTitle></DialogHeader>
          {actionDialog.action === 'reject' ? (
            <Textarea rows={3} value={actionForm.reason} onChange={e => setActionForm({ ...actionForm, reason: e.target.value })} placeholder="Reason for rejection (required)" data-testid="reject-reason" />
          ) : (
            <Textarea rows={3} value={actionForm.notes} onChange={e => setActionForm({ ...actionForm, notes: e.target.value })} placeholder="Optional notes" data-testid="approve-notes" />
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionDialog({ open: false, claim: null, action: '' })}>Cancel</Button>
            <Button onClick={doAction} className={actionDialog.action === 'reject' ? 'bg-leamss-red-600 hover:bg-leamss-red-700 text-white' : 'bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white'} data-testid="action-confirm">
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
