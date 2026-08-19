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

const UploadReportDialog = ({ open, onClose, pa, onUpload }) => {
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (open) setFile(null); }, [open]);

  const submit = async () => {
    if (!file) { toast.error('Please choose a file first'); return; }
    setSubmitting(true);
    await onUpload(file);
    setSubmitting(false);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="upload-report-dialog">
        <DialogHeader>
          <DialogTitle className="text-emerald-700">📄 Upload Report for Client</DialogTitle>
          <DialogDescription>
            <strong>{pa?.client_name}</strong> · {pa?.country} {pa?.service_type} — Pre-Assessment approved. You can upload the report now or later from History.
          </DialogDescription>
        </DialogHeader>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm border border-slate-300 rounded p-2"
        />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Skip for now</Button>
          <Button onClick={submit} disabled={submitting || !file} className="bg-emerald-600 hover:bg-emerald-700">
            {submitting ? 'Uploading…' : 'Upload'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const viewDocument = async (paId, docId) => {
  try {
    const res = await axios.get(
      `${API}/pre-assessment/${paId}/document/${docId}/download?inline=true`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([res.data]));
    window.open(url, '_blank');
  } catch (e) {
    toast.error('Failed to open document');
    console.error(e);
  }
};

const downloadDocument = async (paId, docId, fileName) => {
  try {
    const res = await axios.get(
      `${API}/pre-assessment/${paId}/document/${docId}/download`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName || 'document');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    toast.error('Failed to download document');
    console.error(e);
  }
};

const uploadDocument = async (paId, file, documentType, onSuccess) => {
  try {
    const formData = new FormData();
    formData.append('document_type', documentType || 'admin_report');
    formData.append('file', file);
    await axios.post(
      `${API}/pre-assessment/${paId}/upload-document`,
      formData,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    toast.success('Document uploaded successfully');
    if (onSuccess) onSuccess();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to upload document');
    console.error(e);
  }
};

const StandardCard = ({ pa, onAction, isPending = true, onUploaded }) => {
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
       
<div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3 bg-slate-50 rounded p-3">
        <div><p className="text-xs text-slate-400">Email</p><p className="font-medium text-slate-700">{pa.client_email || 'N/A'}</p></div><br></br>
        <div><p className="text-xs text-slate-400">Mobile</p><p className="font-medium text-slate-700">{pa.client_mobile || 'N/A'}</p></div>
        <div><p className="text-xs text-slate-400">Education</p><p className="font-medium text-slate-700">{pa.education || 'N/A'}</p></div>
        <div><p className="text-xs text-slate-400">Experience</p><p className="font-medium text-slate-700">{pa.work_experience || 'N/A'}</p></div>
        <div><p className="text-xs text-slate-400">Age</p><p className="font-medium text-slate-700">{pa.client_age || 'N/A'}</p></div>
        <div><p className="text-xs text-slate-400">Country</p><p className="font-medium text-slate-700">{pa.country || 'N/A'}</p></div>
        <div><p className="text-xs text-slate-400">Pre-Assessment Fee</p><p className="font-medium text-slate-700">₹{pa.pre_assessment_fee || 0} {pa.fee_payment_status === 'paid' ? 'Paid' : 'Unpaid'}</p></div>
        <div><p className="text-xs text-slate-400">Documents</p><p className="font-medium text-slate-700">{(pa.documents || []).length} uploaded</p></div>
      </div>

      {(pa.documents || []).length > 0 && (
        <div className="mb-3">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-1.5">Submitted Documents ({pa.documents.length})</p>
          <div className="space-y-2">
            {pa.documents.map(doc => (
              <div key={doc.id} className="flex items-center justify-between bg-white border border-slate-200 rounded p-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{doc.file_name}</p>
                    <p className="text-xs text-slate-400">
                      {doc.document_type}
                      {doc.uploaded_by_role === 'admin' && (
                        <span className="ml-2 text-[10px] font-bold text-emerald-600 uppercase">· Uploaded by Admin</span>
                      )}
                    </p>
                  </div>
                </div>
               <div className="flex gap-2 flex-shrink-0">
                  <Button size="sm" variant="outline" onClick={() => viewDocument(pa.id, doc.id)}>View</Button>
                  <Button size="sm" variant="outline" onClick={() => downloadDocument(pa.id, doc.id, doc.file_name)}>Save</Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isPending && pa.admin_decision === 'approved' && (
        <div className="mb-3 border border-dashed border-slate-300 rounded p-3 bg-slate-50">
          <label className="text-xs uppercase tracking-wider text-slate-500 font-bold block mb-2">
            Upload Report for Client
          </label>
          <input
            type="file"
            id={`admin-upload-${pa.id}`}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                uploadDocument(pa.id, file, 'admin_report', onUploaded);
              }
              e.target.value = '';
            }}
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => document.getElementById(`admin-upload-${pa.id}`).click()}
          >
            <FileText className="h-4 w-4 mr-1.5" /> Choose File & Upload
          </Button>
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
  const [uploadDialog, setUploadDialog] = useState({ open: false, pa: null });

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([
        axios.get(`${API}/pre-assessment/admin/standard-queue`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/admin/standard-history`, getAuthHeader()),
        // axios.get(`${API}/pre-assessment/admin/standard-approvals`, { headers }),
        
  // axios.get(`${API}/pre-assessment/admin/history`, { headers }), 
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
      // 👇 NEW — right after approval, open the upload-report prompt for this PA
      if (action === 'approve') {
        setUploadDialog({ open: true, pa });
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Action failed');
    }
  };

  const handleReportUpload = async (file) => {
    try {
      await uploadDocument(uploadDialog.pa.id, file, 'admin_report');
      toast.success('Report uploaded successfully');
      setUploadDialog({ open: false, pa: null });
      load();
    } catch (e) {
      // uploadDocument already shows a toast on failure
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
                history.map((pa) => (
                  <StandardCard
                    key={pa.id}
                    pa={pa}
                    onAction={() => {}}
                    isPending={false}
                    onUploaded={load}
                  />
                ))
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

      <UploadReportDialog
        open={uploadDialog.open}
        pa={uploadDialog.pa}
        onClose={() => setUploadDialog({ open: false, pa: null })}
        onUpload={handleReportUpload}
      />
    </div>
  );
}