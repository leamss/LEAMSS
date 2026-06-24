import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
  ArrowLeft, Receipt, FileText, Package, ClipboardCheck,
  Download, Check, Clock, AlertCircle, Wallet, Plus,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TABS = [
  { id: 'payslips', label: 'Payslips', icon: Receipt, accent: 'emerald' },
  { id: 'reimbursements', label: 'Reimbursements', icon: Wallet, accent: 'leamss-orange' },
  { id: 'documents', label: 'Documents', icon: FileText, accent: 'sky' },
  { id: 'assets', label: 'Assets', icon: Package, accent: 'leamss-orange' },
  { id: 'onboarding', label: 'Onboarding', icon: ClipboardCheck, accent: 'leamss-teal' },
];

const STATUS_BADGE = {
  draft: 'bg-slate-100 text-slate-600',
  approved: 'bg-sky-100 text-sky-700',
  paid: 'bg-emerald-100 text-emerald-700',
  uploaded: 'bg-amber-100 text-amber-700',
  verified: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-leamss-red-100 text-leamss-red-700',
  expired: 'bg-slate-200 text-slate-500',
  issued: 'bg-emerald-100 text-emerald-700',
  in_progress: 'bg-sky-100 text-sky-700',
  completed: 'bg-emerald-100 text-emerald-700',
  submitted: 'bg-amber-100 text-amber-700',
  manager_approved: 'bg-sky-100 text-sky-700',
  hr_approved: 'bg-emerald-100 text-emerald-700',
  reimbursed: 'bg-emerald-100 text-emerald-700',
};

const REIMB_CATEGORIES = [
  'travel', 'food', 'office_supplies', 'client_entertainment',
  'phone', 'internet', 'medical', 'other',
];

// Indian number system formatter for INR amounts
const fmtINR = (n) => {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('en-IN').format(n);
};

export default function MyWorkspace() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState(params.get('tab') || 'payslips');
  const [payslips, setPayslips] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [assets, setAssets] = useState([]);
  const [onboarding, setOnboarding] = useState([]);
  const [reimbursements, setReimbursements] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Reimbursement submit dialog
  const [reimbDialogOpen, setReimbDialogOpen] = useState(false);
  const [reimbForm, setReimbForm] = useState({
    category: 'travel',
    amount_inr: '',
    vendor_name: '',
    description: '',
    expense_date: new Date().toISOString().slice(0, 10),
    bill_url: '',
  });
  const [reimbSubmitting, setReimbSubmitting] = useState(false);

  // Audit trail drawer
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditTrail, setAuditTrail] = useState([]);
  const [auditClaim, setAuditClaim] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    const auth = { headers: { Authorization: `Bearer ${token}` } };
    (async () => {
      try {
        const me = await axios.get(`${API}/auth/me`, auth);
        setUser(me.data);
        const uid = me.data.id;
        const [p, d, a, o, r] = await Promise.all([
          axios.get(`${API}/employees/me/payslips`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/documents`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/assets`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/employees/${uid}/onboarding`, auth).catch(() => ({ data: [] })),
          axios.get(`${API}/reimbursements?for_view=me`, auth).catch(() => ({ data: [] })),
        ]);
        setPayslips(p.data);
        setDocuments(d.data);
        setAssets(a.data);
        setOnboarding(o.data);
        setReimbursements(r.data);
      } catch (e) {
        navigate('/');
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate]);

  useEffect(() => {
    setParams(p => { p.set('tab', tab); return p; }, { replace: true });
  }, [tab, setParams]);

  const downloadPayslipPDF = async (id) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API}/payslips/${id}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `payslip-${id}.pdf`;
    a.click();
  };

  const submitReimbursement = async () => {
    if (!reimbForm.amount_inr || !reimbForm.description.trim()) {
      toast.error('Amount aur description dono zaroori hain');
      return;
    }
    setReimbSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const auth = { headers: { Authorization: `Bearer ${token}` } };
      const payload = {
        category: reimbForm.category,
        amount_inr: Number(reimbForm.amount_inr),
        vendor_name: reimbForm.vendor_name,
        description: reimbForm.description,
        expense_date: reimbForm.expense_date,
        bills: reimbForm.bill_url ? [{ file_url: reimbForm.bill_url, file_name: 'bill', mime_type: 'application/pdf' }] : [],
      };
      await axios.post(`${API}/reimbursements`, payload, auth);
      toast.success('Claim submitted ✓');
      setReimbDialogOpen(false);
      setReimbForm({
        category: 'travel', amount_inr: '', vendor_name: '', description: '',
        expense_date: new Date().toISOString().slice(0, 10), bill_url: '',
      });
      // refresh
      const r = await axios.get(`${API}/reimbursements?for_view=me`, auth);
      setReimbursements(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Submission failed');
    } finally {
      setReimbSubmitting(false);
    }
  };

  const openAuditTrail = async (claim) => {
    setAuditClaim(claim);
    setAuditOpen(true);
    setAuditTrail([]);
    try {
      const token = localStorage.getItem('token');
      const auth = { headers: { Authorization: `Bearer ${token}` } };
      const { data } = await axios.get(`${API}/reimbursements/${claim.id}/audit-trail`, auth);
      setAuditTrail(data || []);
    } catch (e) {
      toast.error('Failed to load audit trail');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-screen text-slate-500" data-testid="ws-loading">Loading…</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="my-workspace-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="ws-back-hub">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div>
              <h1 className="text-lg font-bold text-slate-900">My Workspace</h1>
              <p className="text-xs text-slate-500">{user?.name} · {user?.designation || user?.rbac_role}</p>
            </div>
          </div>
          <div className="flex gap-1 bg-slate-100 rounded-lg p-1 overflow-x-auto">
            {TABS.map(t => {
              const Icon = t.icon;
              const counts = {
                payslips: payslips.length,
                reimbursements: reimbursements.length,
                documents: documents.length,
                assets: assets.length,
                onboarding: onboarding.length,
              };
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 whitespace-nowrap ${
                    tab === t.id ? 'bg-white text-leamss-teal-700 shadow-sm' : 'text-slate-500'
                  }`}
                  data-testid={`ws-tab-${t.id}`}
                >
                  <Icon className="h-3.5 w-3.5" /> {t.label} ({counts[t.id]})
                </button>
              );
            })}
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 space-y-3">
        {/* PAYSLIPS */}
        {tab === 'payslips' && (
          <div data-testid="ws-payslips">
            {payslips.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic" data-testid="ws-payslips-empty">No payslips yet — HR will generate them monthly.</Card>
            )}
            {payslips.map(p => (
              <Card key={p.id} className="p-4 mb-3" data-testid={`payslip-${p.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900">{p.period}</h3>
                      <Badge className={STATUS_BADGE[p.status] || 'bg-slate-100'}>{p.status}</Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Gross: ₹ {fmtINR(p.gross_inr)} · Deductions: ₹ {fmtINR(p.total_deductions_inr)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Net pay</p>
                    <p className="text-2xl font-bold text-leamss-orange-600">₹ {fmtINR(p.net_pay_inr)}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => downloadPayslipPDF(p.id)} data-testid={`payslip-pdf-${p.id}`}>
                    <Download className="h-3.5 w-3.5 mr-1" /> PDF
                  </Button>
                </div>
                {p.attendance_summary && (
                  <p className="text-[10px] text-slate-400 mt-2">
                    Days present: {p.attendance_summary.present_days} · LWP: {p.attendance_summary.lwp_days}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* REIMBURSEMENTS */}
        {tab === 'reimbursements' && (
          <div data-testid="ws-reimbursements">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <p className="text-sm text-slate-600">
                Manager → HR approval workflow · approved claims auto-merge into next payslip
              </p>
              <Button
                size="sm"
                className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white"
                onClick={() => setReimbDialogOpen(true)}
                data-testid="reimbursement-new-btn"
              >
                <Plus className="h-4 w-4 mr-1" /> New Claim
              </Button>
            </div>
            {reimbursements.length === 0 && (
              <Card className="p-8 text-center" data-testid="reimb-empty">
                <Wallet className="h-12 w-12 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500 italic mb-3">Koi reimbursement claim nahi hai abhi tak.</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setReimbDialogOpen(true)}
                  data-testid="reimb-empty-cta"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Submit your first claim
                </Button>
              </Card>
            )}
            {reimbursements.map(c => (
              <Card key={c.id} className="p-4 mb-3" data-testid={`reimb-claim-${c.id}`}>
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="capitalize text-[10px]">{c.category.replace('_', ' ')}</Badge>
                      <Badge className={`${STATUS_BADGE[c.status] || 'bg-slate-100'} capitalize`} data-testid={`reimb-status-${c.id}`}>
                        {c.status.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-800 mt-2 line-clamp-2">{c.description}</p>
                    <p className="text-[10px] text-slate-400 mt-1 inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" /> Expense {c.expense_date}{c.vendor_name ? ` · ${c.vendor_name}` : ''}
                    </p>
                    {c.rejected_reason && (
                      <p className="text-[11px] text-leamss-red-600 mt-1.5 inline-flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" /> {c.rejected_reason}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-400 uppercase">Amount</p>
                    <p className="text-xl font-bold text-leamss-orange-600">₹ {fmtINR(c.amount_inr)}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="mt-1 text-xs"
                      onClick={() => openAuditTrail(c)}
                      data-testid={`reimb-trail-${c.id}`}
                    >
                      View trail
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* DOCUMENTS */}
        {tab === 'documents' && (
          <div data-testid="ws-documents">
            {documents.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No documents uploaded yet.</Card>
            )}
            {documents.map(d => (
              <Card key={d.id} className="p-4 mb-3" data-testid={`doc-${d.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-sky-50 rounded">
                      <FileText className="h-4 w-4 text-sky-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-800">{d.document_name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-[10px] capitalize">{d.document_type.replace('_', ' ')}</Badge>
                        <Badge className={`${STATUS_BADGE[d.status]} text-[10px]`}>{d.status}</Badge>
                        <Badge variant="outline" className="text-[10px] font-mono">v{d.version}</Badge>
                      </div>
                    </div>
                  </div>
                  <a href={d.file_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="outline" data-testid={`doc-view-${d.id}`}>
                      <Download className="h-3.5 w-3.5 mr-1" /> Open
                    </Button>
                  </a>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ASSETS */}
        {tab === 'assets' && (
          <div data-testid="ws-assets">
            {assets.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No assets currently assigned.</Card>
            )}
            {assets.map(a => (
              <Card key={a.id} className="p-4 mb-3" data-testid={`asset-${a.id}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-leamss-orange-50 rounded">
                      <Package className="h-4 w-4 text-leamss-orange-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-800 capitalize">{a.asset_type}: {a.brand} {a.model}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-[10px] font-mono">{a.asset_tag}</Badge>
                        {a.serial_number && <span className="text-[10px] text-slate-400">SN: {a.serial_number}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {a.expected_return_date && (
                      <p className="text-[10px] text-slate-500 inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" /> Return by {new Date(a.expected_return_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ONBOARDING */}
        {tab === 'onboarding' && (
          <div data-testid="ws-onboarding">
            {onboarding.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No onboarding workflow assigned.</Card>
            )}
            {onboarding.map(wf => (
              <Card key={wf.id} className="p-5 mb-4" data-testid={`onb-${wf.id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">{wf.template_name}</h3>
                    <p className="text-xs text-slate-500">Started {wf.started_at ? new Date(wf.started_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <Badge className={STATUS_BADGE[wf.status]}>{wf.status}</Badge>
                </div>
                <div className="space-y-2">
                  {(wf.steps || []).map(s => (
                    <div key={s.step_number} className={`flex items-center gap-3 p-2 rounded ${s.status === 'completed' ? 'bg-emerald-50' : 'bg-slate-50'}`} data-testid={`step-${wf.id}-${s.step_number}`}>
                      <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${s.status === 'completed' ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-slate-600'}`}>
                        {s.status === 'completed' ? <Check className="h-3.5 w-3.5" /> : s.step_number}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-800">{s.name}</p>
                        <p className="text-[10px] text-slate-500 capitalize">{(s.type || '').replace('_', ' ')} · assigned to {s.assigned_to_role}</p>
                      </div>
                      {s.status !== 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            const token = localStorage.getItem('token');
                            await axios.patch(
                              `${API}/onboarding/${wf.id}/step/${s.step_number}/complete`,
                              { notes: 'Done from My Workspace' },
                              { headers: { Authorization: `Bearer ${token}` } },
                            );
                            window.location.reload();
                          }}
                          data-testid={`complete-step-${wf.id}-${s.step_number}`}
                        >
                          Mark done
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Submit Reimbursement Dialog */}
      <Dialog open={reimbDialogOpen} onOpenChange={setReimbDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="reimb-dialog">
          <DialogHeader><DialogTitle>New Reimbursement Claim</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Category</Label>
                <Select value={reimbForm.category} onValueChange={v => setReimbForm({ ...reimbForm, category: v })}>
                  <SelectTrigger data-testid="reimbursement-category-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {REIMB_CATEGORIES.map(c => <SelectItem key={c} value={c} className="capitalize">{c.replace('_', ' ')}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Amount (₹ INR)</Label>
                <Input
                  type="number"
                  min="1"
                  value={reimbForm.amount_inr}
                  onChange={e => setReimbForm({ ...reimbForm, amount_inr: e.target.value })}
                  data-testid="reimbursement-amount-input"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Expense date</Label>
                <Input
                  type="date"
                  value={reimbForm.expense_date}
                  onChange={e => setReimbForm({ ...reimbForm, expense_date: e.target.value })}
                  data-testid="reimbursement-date-input"
                />
              </div>
              <div>
                <Label>Vendor (optional)</Label>
                <Input
                  value={reimbForm.vendor_name}
                  onChange={e => setReimbForm({ ...reimbForm, vendor_name: e.target.value })}
                  placeholder="e.g., Uber, Hotel Taj"
                  data-testid="reimbursement-vendor-input"
                />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                rows={3}
                value={reimbForm.description}
                onChange={e => setReimbForm({ ...reimbForm, description: e.target.value })}
                placeholder="What was this expense for?"
                data-testid="reimbursement-description-input"
              />
            </div>
            <div>
              <Label>Bill / receipt URL (optional)</Label>
              <Input
                value={reimbForm.bill_url}
                onChange={e => setReimbForm({ ...reimbForm, bill_url: e.target.value })}
                placeholder="https://drive.google.com/..."
                data-testid="reimbursement-bill-input"
              />
              <p className="text-[10px] text-slate-400 mt-1">Paste a link to your bill image/PDF (direct file upload arrives in Sub-Slice B)</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReimbDialogOpen(false)} data-testid="reimbursement-cancel-btn">Cancel</Button>
            <Button
              onClick={submitReimbursement}
              disabled={reimbSubmitting}
              className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white"
              data-testid="reimbursement-submit-btn"
            >
              {reimbSubmitting ? 'Submitting…' : 'Submit claim'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Audit trail drawer */}
      <Dialog open={auditOpen} onOpenChange={setAuditOpen}>
        <DialogContent className="max-w-md" data-testid="reimb-audit-dialog">
          <DialogHeader>
            <DialogTitle>Approval Trail</DialogTitle>
            {auditClaim && (
              <p className="text-xs text-slate-500">
                ₹ {fmtINR(auditClaim.amount_inr)} · {auditClaim.category} · {auditClaim.expense_date}
              </p>
            )}
          </DialogHeader>
          <div className="space-y-2 max-h-80 overflow-y-auto" data-testid="reimb-audit-list">
            {auditTrail.length === 0 && <p className="text-xs text-slate-400 italic">No events yet.</p>}
            {auditTrail.map((e, i) => (
              <div key={i} className="flex items-start gap-2 p-2 bg-slate-50 rounded">
                <div className={`mt-0.5 h-2 w-2 rounded-full ${
                  e.action === 'rejected' ? 'bg-leamss-red-500'
                  : e.action.includes('approved') ? 'bg-emerald-500'
                  : 'bg-leamss-orange-500'
                }`} />
                <div className="flex-1">
                  <p className="text-xs font-medium text-slate-800 capitalize">{e.action.replace('_', ' ')}</p>
                  <p className="text-[10px] text-slate-400">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</p>
                  {e.reason && <p className="text-[11px] text-leamss-red-600 mt-0.5">Reason: {e.reason}</p>}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
