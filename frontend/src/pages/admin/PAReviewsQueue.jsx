/**
 * Phase 20.5 — Admin Pre-Assessment Review Queue.
 * /admin/pa-reviews
 */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { CheckCircle2, XCircle, RefreshCw, Eye, AlertTriangle, History, RotateCcw } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const STATUS_TABS = [
  { key: 'pending', label: 'Pending', color: 'leamss-orange' },
  { key: 'approved', label: 'Approved', color: 'leamss-teal' },
  { key: 'rejected', label: 'Rejected (Docs Req.)', color: 'leamss-orange' },
  { key: 'refunded', label: 'Refunded', color: 'leamss-red' },
  { key: 'closed', label: 'Closed', color: 'leamss-red' },
];


function RejectModal({ review, onClose, onDone }) {
  const [action, setAction] = useState('request_more_docs');
  const [reason, setReason] = useState('');
  const [refundAmount, setRefundAmount] = useState(review?.pre_assessment_fee || 5100);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (reason.trim().length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    setSubmitting(true);
    try {
      const body = { action, reason: reason.trim() };
      if (action === 'refund') body.refund_amount_inr = Number(refundAmount);
      await axios.post(`${API}/admin/pa-reviews/${review.id}/reject`, body, auth());
      toast.success(`Action applied: ${action}`);
      onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Reject failed');
    }
    setSubmitting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-lg p-5" data-testid="reject-modal">
        <h3 className="text-lg font-bold text-leamss-red flex items-center gap-2 mb-3">
          <XCircle className="h-5 w-5" />Reject Pre-Assessment
        </h3>
        <Card className="p-3 mb-3 bg-leamss-teal_50">
          <p className="text-xs">
            Client: <span className="font-bold">{review.client_name}</span> · {review.country} / {review.service_type}
          </p>
        </Card>
        <div className="space-y-2 mb-3">
          {[
            ['request_more_docs', 'Request More Documents', 'Returns PA to client to upload more docs'],
            ['close_case', 'Close Case (no refund)', 'Archives case, no money returned'],
            ['refund', 'Refund + Close', 'Initiates refund of paid fee + closes'],
          ].map(([val, label, desc]) => (
            <label key={val} className="flex items-start gap-2 cursor-pointer p-2 border rounded hover:bg-leamss-orange_50" data-testid={`reject-action-${val}`}>
              <input type="radio" checked={action === val} onChange={() => setAction(val)} className="mt-1" />
              <span className="text-xs">
                <span className="font-bold">{label}</span><br/>
                <span className="text-slate-600">{desc}</span>
              </span>
            </label>
          ))}
        </div>
        {action === 'refund' && (
          <div className="mb-3">
            <label className="text-xs font-bold">Refund Amount (INR)</label>
            <input type="number" value={refundAmount} onChange={e => setRefundAmount(e.target.value)} className="w-full border rounded p-2 mt-1 text-sm" data-testid="refund-amount" />
          </div>
        )}
        <div className="mb-3">
          <label className="text-xs font-bold">Reason (min 10 chars, audit-logged)</label>
          <textarea rows={3} value={reason} onChange={e => setReason(e.target.value)}
            placeholder="e.g., Missing IELTS scorecard. Client to upload and resubmit by Friday."
            className="w-full border rounded p-2 mt-1 text-sm" data-testid="reject-reason" />
          <p className="text-[10px] text-slate-500">{reason.length} chars</p>
        </div>
        <div className="flex justify-end gap-2 border-t pt-3">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={submitting || reason.trim().length < 10} className="bg-leamss-red hover:bg-leamss-red/90" data-testid="reject-submit-btn">
            Submit Rejection
          </Button>
        </div>
      </Card>
    </div>
  );
}


export default function PAReviewsQueue() {
  const [status, setStatus] = useState('pending');
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rejecting, setRejecting] = useState(null);
  const navigate = (url) => window.location.assign(url);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/pa-reviews?status=${status}&limit=100`, auth());
      setReviews(r.data.reviews);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load reviews');
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [status]);

  const approve = async (rev) => {
    const notes = prompt('Approval notes (optional)') || '';
    try {
      await axios.post(`${API}/admin/pa-reviews/${rev.id}/approve`, { notes }, auth());
      toast.success(`Approved · PA stage → admin_approved`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Approve failed');
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6" data-testid="pa-reviews-page">
      <header className="mb-4">
        <h1 className="text-3xl font-bold text-leamss-teal flex items-center gap-2">
          <CheckCircle2 className="h-7 w-7" />Pre-Assessment Review Queue
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Phase 20.5 · Admin gate — approve or reject submitted Pre-Assessments. Every action is revocable for 24h.
        </p>
      </header>

      <div className="flex gap-1 mb-4 border-b" data-testid="status-tabs">
        {STATUS_TABS.map(t => (
          <button key={t.key} onClick={() => setStatus(t.key)}
            data-testid={`tab-${t.key}`}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors ${
              status === t.key ? `border-${t.color} text-${t.color}` : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      <Card className="p-4">
        {loading && <p className="text-center py-8 text-slate-500"><RefreshCw className="h-5 w-5 inline animate-spin mr-2" />Loading…</p>}
        {!loading && reviews.length === 0 && (
          <p className="text-center py-8 text-slate-400 text-sm">No {status} reviews.</p>
        )}
        {!loading && reviews.length > 0 && (
          <table className="w-full text-xs" data-testid="reviews-table">
            <thead className="text-[10px] uppercase text-slate-500 border-b">
              <tr>
                <th className="text-left p-2">Client</th>
                <th className="text-left p-2">Country / Visa</th>
                <th className="text-right p-2">Fee</th>
                <th className="text-left p-2">Submitted</th>
                <th className="text-left p-2">Reviewer</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map(r => (
                <tr key={r.id} className="border-b hover:bg-leamss-teal_50/30" data-testid={`review-row-${r.id}`}>
                  <td className="p-2">
                    <p className="font-bold">{r.client_name}</p>
                    <p className="text-[10px] text-slate-500">{r.client_email}</p>
                  </td>
                  <td className="p-2">{r.country} / {r.service_type}</td>
                  <td className="p-2 text-right font-mono">₹{r.pre_assessment_fee?.toLocaleString()}</td>
                  <td className="p-2">{r.submitted_at?.slice(0, 16).replace('T', ' ')}</td>
                  <td className="p-2">{r.reviewed_by ? '✓ ' + (r.reviewed_by_name || '') : '—'}</td>
                  <td className="p-2 text-right space-x-1">
                    {r.info_sheet_id && (
                      <Button size="sm" variant="ghost" onClick={() => navigate(`/admin/info-sheets/client/${r.client_id}`)} data-testid={`view-sheet-${r.id}`}>
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {status === 'pending' && (
                      <>
                        <Button size="sm" onClick={() => approve(r)} className="bg-leamss-teal hover:bg-leamss-teal/90" data-testid={`approve-${r.id}`}>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" onClick={() => setRejecting(r)} className="bg-leamss-red hover:bg-leamss-red/90" data-testid={`reject-${r.id}`}>
                          <XCircle className="h-3.5 w-3.5" />
                        </Button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {rejecting && (
        <RejectModal review={rejecting} onClose={() => setRejecting(null)} onDone={() => { setRejecting(null); load(); }} />
      )}
    </div>
  );
}
