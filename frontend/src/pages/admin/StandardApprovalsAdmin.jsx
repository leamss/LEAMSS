/**
 * Phase 4B (Part 2) — Admin Express Approvals queue.
 * Lists pending express PAs awaiting admin decision.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { ArrowLeft, Zap, CheckCircle2, XCircle, Clock, User, Globe, FileText, AlertTriangle, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const REASON_LABELS = {
  repeat_client: 'Repeat Client',
  pre_qualified_referral: 'Pre-qualified Referral',
  vip_customer: 'VIP Customer',
  direct_walkin: 'Direct Walk-in',
  partner_channel: 'Partner Channel',
  renewal_upgrade: 'Renewal / Upgrade',
  other: 'Other',
};

const REASON_COLORS = {
  vip_customer: 'bg-amber-100 text-amber-700 border-amber-300',
  repeat_client: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  pre_qualified_referral: 'bg-blue-100 text-blue-700 border-blue-300',
  partner_channel: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300',
  renewal_upgrade: 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-300',
  direct_walkin: 'bg-sky-100 text-sky-700 border-sky-300',
  other: 'bg-slate-100 text-slate-700 border-slate-300',
};

const formatDate = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
};

const ApprovalDialog = ({ open, onClose, pa, action, onConfirm }) => {
  const [remarks, setRemarks] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (open) setRemarks(''); }, [open]);

  const submit = async () => {
    if (action === 'reject' && remarks.trim().length < 5) { toast.error('Rejection reason must be at least 5 characters'); return; }
    setSubmitting(true);
    await onConfirm(remarks);
    setSubmitting(false);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid={`${action}-dialog`}>
        <DialogHeader>
          <DialogTitle className={action === 'approve' ? 'text-emerald-700' : 'text-rose-700'}>
            {action === 'approve' ? '✅ Approve Express Sale' : '❌ Reject Express Sale'}
          </DialogTitle>
          <DialogDescription>
            <strong>{pa?.client_name}</strong> · {pa?.country} {pa?.service_type} · by {pa?.partner_name}
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          placeholder={action === 'approve' ? 'Optional remarks…' : 'Reason for rejection (required, min 5 chars)'}
          rows={3}
          data-testid={`${action}-remarks`}
        />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={submitting} className={action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'} data-testid={`confirm-${action}`}>
            {submitting ? 'Submitting…' : (action === 'approve' ? 'Approve' : 'Reject')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const ExpressCard = ({ pa, onAction, isPending = true }) => {
  const reasonColor = REASON_COLORS[pa.express_sale_reason] || REASON_COLORS.other;
  const statusBadge = (() => {
    if (isPending) return <Badge className="bg-amber-100 text-amber-700 border border-amber-300 uppercase text-[10px] font-bold"><Clock className="h-3 w-3 mr-1 inline" />Pending</Badge>;
    if (pa.express_sale_approval_status === 'approved') return <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-300 uppercase text-[10px] font-bold"><CheckCircle2 className="h-3 w-3 mr-1 inline" />Approved</Badge>;
    return <Badge className="bg-rose-100 text-rose-700 border border-rose-300 uppercase text-[10px] font-bold"><XCircle className="h-3 w-3 mr-1 inline" />Rejected</Badge>;
  })();

  return (
    <Card className="p-5 border-l-4 border-l-amber-500" data-testid={`express-card-${pa.id}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
            <Zap className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h3 className="font-bold text-slate-800 text-lg flex items-center gap-2">
              {pa.client_name}
              <span className="text-xs font-normal text-slate-500">· {pa.pa_number}</span>
            </h3>
            <p className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
              <Globe className="h-3 w-3" />
              {pa.country} · {pa.service_type} {pa.product_name ? `· ${pa.product_name}` : ''}
            </p>
          </div>
        </div>
        {statusBadge}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm mb-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Sales Person</p>
          <p className="font-semibold text-slate-800 flex items-center gap-1.5 mt-0.5"><User className="h-3.5 w-3.5" />{pa.partner_name}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Reason</p>
          <Badge className={`${reasonColor} text-xs uppercase border mt-0.5`}>{REASON_LABELS[pa.express_sale_reason] || pa.express_sale_reason}</Badge>
        </div>
        <div className="md:col-span-2">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-0.5">Justification</p>
          <p className="text-sm text-slate-700 bg-amber-50 border border-amber-200 rounded p-2.5">
            <FileText className="h-3.5 w-3.5 inline mr-1 text-amber-700" />
            {pa.express_sale_justification}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Requested {formatDate(pa.express_sale_requested_at || pa.created_at)}</span>
        {!isPending && pa.express_sale_approval_remarks && (
          <span className="italic">Remarks: "{pa.express_sale_approval_remarks}"</span>
        )}
      </div>

      {isPending && (
        <div className="flex gap-2 mt-3">
          <Button onClick={() => onAction(pa, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-700" data-testid={`approve-btn-${pa.id}`}>
            <CheckCircle2 className="h-4 w-4 mr-1.5" /> Approve
          </Button>
          <Button onClick={() => onAction(pa, 'reject')} variant="destructive" className="flex-1" data-testid={`reject-btn-${pa.id}`}>
            <XCircle className="h-4 w-4 mr-1.5" /> Reject
          </Button>
        </div>
      )}
    </Card>
  );
};

export default function ExpressApprovalsAdmin() {
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, action: null, pa: null });

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [p, h] = await Promise.all([
        axios.get(`${API}/pre-assessment/admin/queue`, { headers }),
        
  axios.get(`${API}/pre-assessment/admin/history`, { headers }), 
      ]);
      console.log(`${API}/pre-assessment/admin/queue`);
      setPending(p.data.items || []);
      const decided = (h.data.items || []).filter(i => i.express_sale_approval_status !== 'pending');
      setHistory(decided);
    } catch (e) {
      toast.error('Failed to load Express queue');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAction = (pa, action) => setDialog({ open: true, action, pa });

  const confirmAction = async (remarks) => {
    const { pa, action } = dialog;
    try {
      const token = localStorage.getItem('token');
     await axios.put(
  `${API}/pre-assessment/${pa.id}/review`,
  {
    decision: action === "approve" ? "approved" : "rejected",
    reason: remarks,
    notes: remarks,
  },
  {
    headers: { Authorization: `Bearer ${token}` }
  }
);
      toast.success(`Express Sale ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
      setDialog({ open: false, action: null, pa: null });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Action failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="express-approvals-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200 transition" data-testid="back-to-admin">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Zap className="h-7 w-7 text-amber-600" /> Express Sale Approvals
              </h1>
              <p className="text-sm text-slate-500 mt-1">Review sales bypassing the Pre-Assessment fee step</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-amber-100 text-amber-700 border border-amber-300 text-base px-3 py-1.5 font-bold" data-testid="pending-count-badge">
              {pending.length} pending
            </Badge>
          </div>
        </div>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-amber-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <Tabs defaultValue="pending" className="space-y-4" data-testid="express-tabs">
            <TabsList className="grid w-full grid-cols-2 max-w-md">
              <TabsTrigger value="pending" data-testid="tab-pending">Pending ({pending.length})</TabsTrigger>
              <TabsTrigger value="history" data-testid="tab-history">History ({history.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="pending" className="space-y-3">
              {pending.length === 0 ? (
                <Card className="p-12 text-center" data-testid="empty-pending">
                  <CheckCircle2 className="h-12 w-12 text-emerald-300 mx-auto mb-2" />
                  <p className="text-slate-600 font-semibold">No pending Express approvals</p>
                  <p className="text-sm text-slate-400 mt-1">All caught up — well done!</p>
                </Card>
              ) : (
                pending.map((pa) => <ExpressCard key={pa.id} pa={pa} onAction={handleAction} isPending />)
              )}
            </TabsContent>

            <TabsContent value="history" className="space-y-3">
              {history.length === 0 ? (
                <Card className="p-10 text-center text-slate-400" data-testid="empty-history">No decided Express sales yet</Card>
              ) : (
                history.map((pa) => <ExpressCard key={pa.id} pa={pa} onAction={() => {}} isPending={false} />)
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>

      <ApprovalDialog
        open={dialog.open}
        action={dialog.action}
        pa={dialog.pa}
        onClose={() => setDialog({ open: false, action: null, pa: null })}
        onConfirm={confirmAction}
      />
    </div>
  );
}
