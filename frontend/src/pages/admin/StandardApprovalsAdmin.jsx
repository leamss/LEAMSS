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
import { ArrowLeft, ClipboardList, CheckCircle2, XCircle, Clock, User, Globe, FileText, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
            {action === 'approve' ? '✅ Approve Pre-Assessment' : '❌ Reject Pre-Assessment'}
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

const StandardCard = ({ pa, onAction, isPending = true }) => {
  const statusBadge = (() => {
    if (isPending) return <Badge className="bg-amber-100 text-amber-700 border border-amber-300 uppercase text-[10px] font-bold"><Clock className="h-3 w-3 mr-1 inline" />Pending</Badge>;
    if (pa.admin_decision === 'approved') return <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-300 uppercase text-[10px] font-bold"><CheckCircle2 className="h-3 w-3 mr-1 inline" />Approved</Badge>;
    return <Badge className="bg-rose-100 text-rose-700 border border-rose-300 uppercase text-[10px] font-bold"><XCircle className="h-3 w-3 mr-1 inline" />Rejected</Badge>;
  })();

  return (
    <Card className="p-5 border-l-4 border-l-leamss-orange-500" data-testid={`standard-card-${pa.id}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
            <ClipboardList className="h-5 w-5 text-leamss-orange-600" />
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
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Submitted By</p>
          <p className="font-semibold text-slate-800 flex items-center gap-1.5 mt-0.5"><User className="h-3.5 w-3.5" />{pa.partner_name || '—'}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Stage</p>
          <Badge className="bg-slate-100 text-slate-700 text-xs uppercase border mt-0.5">{(pa.stage || '').replace(/_/g, ' ')}</Badge>
        </div>
        {(pa.education || pa.experience || pa.age) && (
          <div className="md:col-span-2">
            <p className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-0.5">Client Profile</p>
            <p className="text-sm text-slate-700 bg-orange-50 border border-orange-200 rounded p-2.5 flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-leamss-orange-700" />
              {[pa.age && `Age ${pa.age}`, pa.education, pa.experience && `${pa.experience} yrs exp`].filter(Boolean).join(' · ') || '—'}
            </p>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Submitted {formatDate(pa.submitted_at || pa.created_at)}</span>
        {!isPending && pa.admin_notes && (
          <span className="italic">Remarks: "{pa.admin_notes}"</span>
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

export default function StandardApprovalsAdmin() {
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, action: null, pa: null });

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([
        axios.get(`${API}/pre-assessment/admin/standard-queue`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/admin/standard-history`, getAuthHeader()),
      ]);
      setPending(p.data.items || []);
      setHistory(h.data.items || []);
    } catch (e) {
      toast.error('Failed to load approval queue');
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
      await axios.put(
        `${API}/pre-assessment/${pa.id}/review`,
        { decision: action === 'approve' ? 'approved' : 'rejected', reason: remarks, notes: remarks },
        getAuthHeader()
      );
      toast.success(`Pre-Assessment ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
      setDialog({ open: false, action: null, pa: null });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Action failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="standard-approvals-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200 transition" data-testid="back-to-admin">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <ClipboardList className="h-7 w-7 text-leamss-orange-600" /> Standard Sale Approvals
              </h1>
              <p className="text-sm text-slate-500 mt-1">Pre-Assessments awaiting eligibility review</p>
            </div>
          </div>
          <Badge className="bg-orange-100 text-leamss-orange-700 border border-orange-300 text-base px-3 py-1.5 font-bold" data-testid="pending-count-badge">
            {pending.length} pending
          </Badge>
        </div>

        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-orange-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : (
          <Tabs defaultValue="pending" className="space-y-4" data-testid="standard-tabs">
            <TabsList className="grid w-full grid-cols-2 max-w-md">
              <TabsTrigger value="pending" data-testid="tab-pending">Pending ({pending.length})</TabsTrigger>
              <TabsTrigger value="history" data-testid="tab-history">History ({history.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="pending" className="space-y-3">
              {pending.length === 0 ? (
                <Card className="p-12 text-center" data-testid="empty-pending">
                  <CheckCircle2 className="h-12 w-12 text-emerald-300 mx-auto mb-2" />
                  <p className="text-slate-600 font-semibold">No pending approvals</p>
                  <p className="text-sm text-slate-400 mt-1">All caught up — well done!</p>
                </Card>
              ) : (
                pending.map((pa) => <StandardCard key={pa.id} pa={pa} onAction={handleAction} isPending />)
              )}
            </TabsContent>

            <TabsContent value="history" className="space-y-3">
              {history.length === 0 ? (
                <Card className="p-10 text-center text-slate-400" data-testid="empty-history">No decided approvals yet</Card>
              ) : (
                history.map((pa) => <StandardCard key={pa.id} pa={pa} onAction={() => {}} isPending={false} />)
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