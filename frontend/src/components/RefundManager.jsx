import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  RotateCcw, DollarSign, CheckCircle, Loader2, AlertTriangle, Search,
  Eye, Download, FileText, XCircle, Clock, ArrowLeft, Printer, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RefundManager = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('pending');
  const [searchTerm, setSearchTerm] = useState('');
  // Initiate refund dialog
  const [refundDialog, setRefundDialog] = useState({ open: false, sale: null, amount: 0, reason: '', method: 'original_payment', notes: '', category: '' });
  // Review dialog
  const [reviewDialog, setReviewDialog] = useState({ open: false, refund: null, action: '', notes: '' });
  // Detail view
  const [detailView, setDetailView] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  // PA refund
  const [paRefundProcessing, setPaRefundProcessing] = useState(null);
  const [processing, setProcessing] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/admin-super/refund-manager`, { headers });
      setData(res.data);
    } catch (e) {
      toast.error('Failed to load refund data');
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const handleInitiateRefund = async () => {
    if (!refundDialog.reason || refundDialog.reason.trim().length < 5) { toast.error('Reason required (min 5 chars)'); return; }
    if (!refundDialog.amount || refundDialog.amount <= 0) { toast.error('Amount must be positive'); return; }
    if (!refundDialog.category) { toast.error('Select a refund category'); return; }
    setProcessing(true);
    try {
      await axios.post(`${API}/refunds`, {
        sale_id: refundDialog.sale.sale_id,
        amount: refundDialog.amount,
        reason: refundDialog.reason.trim(),
        refund_method: refundDialog.method,
        notes: refundDialog.notes,
        category: refundDialog.category,
      }, { headers });
      toast.success('Refund initiated — pending review');
      setRefundDialog({ open: false, sale: null, amount: 0, reason: '', method: 'original_payment', notes: '', category: '' });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
    setProcessing(false);
  };

  const handleReview = async () => {
    if (reviewDialog.action === 'reject' && (!reviewDialog.notes || reviewDialog.notes.trim().length < 5)) {
      toast.error('Rejection reason required (min 5 chars)'); return;
    }
    setProcessing(true);
    try {
      await axios.post(`${API}/refunds/review`, {
        refund_id: reviewDialog.refund.id,
        action: reviewDialog.action,
        review_notes: reviewDialog.notes.trim(),
      }, { headers });
      toast.success(reviewDialog.action === 'approve' ? 'Refund approved & processed' : 'Refund rejected');
      setReviewDialog({ open: false, refund: null, action: '', notes: '' });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Review failed');
    }
    setProcessing(false);
  };

  const openDetail = async (refundId) => {
    setDetailLoading(true);
    try {
      const res = await axios.get(`${API}/refunds/detail/${refundId}`, { headers });
      setDetailView(res.data);
    } catch (e) {
      toast.error('Failed to load details');
    }
    setDetailLoading(false);
  };

  const handleProcessPARefund = async (paId) => {
    setPaRefundProcessing(paId);
    try {
      await axios.post(`${API}/admin-super/refund-manager/process-pa-refund`, { pa_id: paId, notes: 'Pre-assessment refund processed' }, { headers });
      toast.success('PA refund processed');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
    setPaRefundProcessing(null);
  };

  const printRefundDetail = (detail) => {
    const d = detail;
    const html = `<!DOCTYPE html><html><head><title>Refund Confirmation - ${d.id?.slice(0,8)}</title>
    <style>body{font-family:Arial,sans-serif;padding:30px;max-width:800px;margin:auto;color:#333}
    .header{background:#2a777a;color:white;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px}
    .header h1{margin:0;font-size:20px}.header p{margin:5px 0;font-size:12px;opacity:0.8}
    .section{margin:16px 0;padding:16px;border:1px solid #e5e7eb;border-radius:8px}
    .section h3{margin:0 0 12px 0;font-size:14px;color:#2a777a;border-bottom:1px solid #e5e7eb;padding-bottom:6px}
    .row{display:flex;justify-content:space-between;padding:4px 0;font-size:13px}
    .row .label{color:#6b7280}.row .value{font-weight:600}
    .amount{font-size:28px;font-weight:bold;color:#dc2626;text-align:center;margin:20px 0}
    .status{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold}
    .status.processed{background:#d1fae5;color:#065f46}.status.rejected{background:#fee2e2;color:#991b1b}
    .status.pending{background:#fef3c7;color:#92400e}
    .footer{text-align:center;margin-top:30px;font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:10px}
    </style></head><body>
    <div class="header"><h1>LEAMSS Immigration Services</h1><p>Refund Confirmation</p></div>
    <div class="amount">Refund: ₹${(d.amount || 0).toLocaleString()}</div>
    <p style="text-align:center"><span class="status ${d.status}">${(d.status || '').toUpperCase()}</span></p>
    <div class="section"><h3>Refund Details</h3>
    <div class="row"><span class="label">Refund ID</span><span class="value">${d.id?.slice(0,8) || ''}</span></div>
    <div class="row"><span class="label">Category</span><span class="value">${(d.category || 'N/A').replace('_',' ')}</span></div>
    <div class="row"><span class="label">Reason</span><span class="value">${d.reason || ''}</span></div>
    <div class="row"><span class="label">Method</span><span class="value">${(d.refund_method || '').replace('_',' ')}</span></div>
    <div class="row"><span class="label">Date</span><span class="value">${d.created_at ? new Date(d.created_at).toLocaleString() : ''}</span></div>
    ${d.review_notes ? `<div class="row"><span class="label">Review Notes</span><span class="value">${d.review_notes}</span></div>` : ''}
    </div>
    <div class="section"><h3>Client & Payment</h3>
    <div class="row"><span class="label">Client</span><span class="value">${d.sale?.client_name || d.client_name || ''}</span></div>
    <div class="row"><span class="label">Email</span><span class="value">${d.sale?.client_email || d.client_email || ''}</span></div>
    <div class="row"><span class="label">Product</span><span class="value">${d.sale?.product_name || d.product_name || ''}</span></div>
    <div class="row"><span class="label">Original Fee</span><span class="value">₹${(d.sale?.fee_amount || d.original_fee || 0).toLocaleString()}</span></div>
    <div class="row"><span class="label">Amount Received</span><span class="value">₹${(d.sale?.amount_received || d.amount_received || 0).toLocaleString()}</span></div>
    <div class="row"><span class="label">Payment Method</span><span class="value">${d.sale?.payment_method || ''}</span></div>
    </div>
    <div class="section"><h3>Partner & Processing</h3>
    <div class="row"><span class="label">Partner</span><span class="value">${d.partner?.name || d.partner_name || ''}</span></div>
    <div class="row"><span class="label">Initiated By</span><span class="value">${d.initiator?.name || d.initiated_by_name || ''}</span></div>
    <div class="row"><span class="label">Reviewed By</span><span class="value">${d.reviewer?.name || d.reviewed_by_name || 'Pending'}</span></div>
    </div>
    <div class="footer">This is a system-generated document from LEAMSS Portal.<br/>Generated: ${new Date().toLocaleString()}</div>
    </body></html>`;
    const w = window.open('', '_blank');
    w.document.write(html);
    w.document.close();
    setTimeout(() => w.print(), 400);
  };

  const downloadBulkReport = () => {
    const refunds = data?.refunds || [];
    if (!refunds.length) { toast.error('No data'); return; }
    const cols = ['Date','Client','Email','Product','Partner','Original Fee','Refund Amount','Reason','Category','Method','Status','Processed By','Review Notes'];
    const rows = refunds.map(r => [
      r.created_at ? new Date(r.created_at).toLocaleDateString() : '',
      r.client_name || '', r.client_email || '', r.product_name || '', r.partner_name || '',
      r.original_fee || 0, r.amount || 0, `"${(r.reason || '').replace(/"/g,'""')}"`,
      r.category || '', (r.refund_method || '').replace('_',' '), r.status || '',
      r.processed_by_name || '', `"${(r.review_notes || r.notes || '').replace(/"/g,'""')}"`
    ]);
    const csv = [cols.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `refund_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link); link.click(); link.remove();
    toast.success('Report downloaded');
  };

  if (loading || !data) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  // If detail view is open
  if (detailView) {
    const d = detailView;
    return (
      <div className="space-y-5" data-testid="refund-detail">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => setDetailView(null)} data-testid="back-btn"><ArrowLeft className="h-4 w-4 mr-1" />Back</Button>
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Refund Detail</h3>
          <Badge className={d.status === 'processed' ? 'bg-emerald-100 text-emerald-700' : d.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{d.status}</Badge>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" size="sm" onClick={() => printRefundDetail(d)} data-testid="print-refund"><Printer className="h-4 w-4 mr-1" />Print / PDF</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-5 text-center bg-red-50 border-red-200 dark:bg-red-900/20">
            <p className="text-sm text-red-600">Refund Amount</p>
            <p className="text-3xl font-bold text-red-700">₹{(d.amount || 0).toLocaleString()}</p>
          </Card>
          <Card className="p-5 text-center bg-slate-50 dark:bg-slate-800">
            <p className="text-sm text-slate-600 dark:text-slate-400">Original Fee</p>
            <p className="text-2xl font-bold text-slate-800 dark:text-white">₹{(d.sale?.fee_amount || d.original_fee || 0).toLocaleString()}</p>
          </Card>
          <Card className="p-5 text-center bg-emerald-50 dark:bg-emerald-900/20">
            <p className="text-sm text-emerald-600">Amount Received</p>
            <p className="text-2xl font-bold text-emerald-700">₹{(d.sale?.amount_received || d.amount_received || 0).toLocaleString()}</p>
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-5">
            <h4 className="font-semibold text-slate-800 dark:text-white mb-3">Client & Payment</h4>
            <div className="space-y-2 text-sm">
              {[['Client', d.sale?.client_name || d.client_name], ['Email', d.sale?.client_email || d.client_email], ['Product', d.sale?.product_name || d.product_name], ['Payment Method', d.sale?.payment_method], ['Payment Status', d.sale?.payment_status]].map(([l,v]) => v && (
                <div key={l} className="flex justify-between"><span className="text-slate-500">{l}</span><span className="font-medium text-slate-800 dark:text-white">{v}</span></div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h4 className="font-semibold text-slate-800 dark:text-white mb-3">Refund Info</h4>
            <div className="space-y-2 text-sm">
              {[['Category', (d.category || '').replace('_',' ')], ['Reason', d.reason], ['Method', (d.refund_method || '').replace('_',' ')], ['Notes', d.notes], ['Review Notes', d.review_notes]].map(([l,v]) => v && (
                <div key={l} className="flex justify-between gap-4"><span className="text-slate-500 flex-shrink-0">{l}</span><span className="font-medium text-slate-800 dark:text-white text-right">{v}</span></div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h4 className="font-semibold text-slate-800 dark:text-white mb-3">Partner</h4>
            <div className="space-y-2 text-sm">
              {[['Name', d.partner?.name || d.partner_name], ['Email', d.partner?.email]].map(([l,v]) => v && (
                <div key={l} className="flex justify-between"><span className="text-slate-500">{l}</span><span className="font-medium">{v}</span></div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h4 className="font-semibold text-slate-800 dark:text-white mb-3">Processing</h4>
            <div className="space-y-2 text-sm">
              {[['Initiated By', d.initiator?.name || d.initiated_by_name], ['Reviewed By', d.reviewer?.name || d.reviewed_by_name || 'Pending'], ['Created', d.created_at ? new Date(d.created_at).toLocaleString() : ''], ['Reviewed', d.reviewed_at ? new Date(d.reviewed_at).toLocaleString() : 'Pending']].map(([l,v]) => (
                <div key={l} className="flex justify-between"><span className="text-slate-500">{l}</span><span className="font-medium">{v || '-'}</span></div>
              ))}
            </div>
          </Card>
        </div>

        {d.status === 'pending_review' && (
          <Card className="p-5 border-amber-200 bg-amber-50 dark:bg-amber-900/20">
            <h4 className="font-semibold text-amber-800 mb-3">Review Required</h4>
            <div className="flex gap-3">
              <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => setReviewDialog({ open: true, refund: d, action: 'approve', notes: '' })} data-testid="approve-refund"><CheckCircle className="h-4 w-4 mr-1" />Approve & Process</Button>
              <Button variant="destructive" onClick={() => setReviewDialog({ open: true, refund: d, action: 'reject', notes: '' })} data-testid="reject-refund"><XCircle className="h-4 w-4 mr-1" />Reject Refund</Button>
            </div>
          </Card>
        )}
      </div>
    );
  }

  const pendingRefunds = (data.refunds || []).filter(r => r.status === 'pending_review');
  const processedRefunds = (data.refunds || []).filter(r => r.status !== 'pending_review');
  const filteredHistory = processedRefunds.filter(r =>
    !searchTerm || r.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) || r.reason?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-5" data-testid="refund-manager">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200 cursor-pointer" onClick={() => setActiveView('pending')}>
          <div className="flex items-center gap-2 mb-1"><Clock className="h-4 w-4 text-amber-600" /><p className="text-xs text-amber-600 font-medium">Pending Review</p></div>
          <p className="text-2xl font-bold text-amber-800">{pendingRefunds.length}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-red-50 to-red-100 border-red-200 cursor-pointer" onClick={() => setActiveView('history')}>
          <div className="flex items-center gap-2 mb-1"><RotateCcw className="h-4 w-4 text-red-600" /><p className="text-xs text-red-600 font-medium">Total Refunded</p></div>
          <p className="text-2xl font-bold text-red-800">₹{(data.stats?.total_refunded || 0).toLocaleString()}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 cursor-pointer" onClick={() => setActiveView('pa_pending')}>
          <div className="flex items-center gap-2 mb-1"><AlertTriangle className="h-4 w-4 text-blue-600" /><p className="text-xs text-blue-600 font-medium">PA Refunds Pending</p></div>
          <p className="text-2xl font-bold text-blue-800">{data.stats?.pa_pending_count || 0}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200 cursor-pointer" onClick={() => setActiveView('eligible')}>
          <div className="flex items-center gap-2 mb-1"><DollarSign className="h-4 w-4 text-emerald-600" /><p className="text-xs text-emerald-600 font-medium">Eligible for Refund</p></div>
          <p className="text-2xl font-bold text-emerald-800">{(data.eligible_for_refund || []).length}</p>
        </Card>
      </div>

      {/* View Tabs */}
      <Card className="p-3">
        <div className="flex flex-wrap items-center gap-2">
          {[
            { key: 'pending', label: 'Pending Review', count: pendingRefunds.length, color: 'bg-amber-500' },
            { key: 'history', label: 'Refund History', count: processedRefunds.length },
            { key: 'pa_pending', label: 'PA Refunds', count: data.pa_refunds_pending?.length || 0 },
            { key: 'eligible', label: 'Issue New', count: data.eligible_for_refund?.length || 0 },
          ].map(tab => (
            <Button key={tab.key} variant={activeView === tab.key ? 'default' : 'outline'} size="sm"
              onClick={() => setActiveView(tab.key)}
              className={activeView === tab.key ? 'bg-[#2a777a] hover:bg-[#236466]' : ''}
              data-testid={`refund-tab-${tab.key}`}
            >
              {tab.label} <Badge className={`ml-1.5 ${tab.color || 'bg-slate-200'} text-xs`}>{tab.count}</Badge>
            </Button>
          ))}
          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={downloadBulkReport} data-testid="download-report"><Download className="h-4 w-4 mr-1" />Export CSV</Button>
          </div>
        </div>
      </Card>

      {/* PENDING REVIEW */}
      {activeView === 'pending' && (
        <div className="space-y-3">
          {pendingRefunds.length === 0 ? (
            <Card className="p-12 text-center"><CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" /><p className="text-lg font-semibold text-slate-600">No Pending Reviews</p></Card>
          ) : pendingRefunds.map((r, idx) => (
            <Card key={r.id} className="p-4 border-l-4 border-l-amber-400 hover:shadow-md transition-shadow" data-testid={`pending-refund-${idx}`}>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-slate-800 dark:text-white">{r.client_name}</h4>
                    <Badge className="bg-amber-100 text-amber-700">{(r.category || 'other').replace('_',' ')}</Badge>
                    <Badge className="bg-red-100 text-red-700 font-bold">₹{(r.amount || 0).toLocaleString()}</Badge>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{r.reason}</p>
                  <p className="text-xs text-slate-400 mt-1">{r.product_name} | Partner: {r.partner_name} | {r.created_at ? new Date(r.created_at).toLocaleDateString() : ''}</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => openDetail(r.id)} data-testid={`view-refund-${idx}`}><Eye className="h-4 w-4 mr-1" />Review</Button>
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => setReviewDialog({ open: true, refund: r, action: 'approve', notes: '' })}><CheckCircle className="h-4 w-4 mr-1" />Approve</Button>
                  <Button size="sm" variant="destructive" onClick={() => setReviewDialog({ open: true, refund: r, action: 'reject', notes: '' })}><XCircle className="h-4 w-4 mr-1" />Reject</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* REFUND HISTORY */}
      {activeView === 'history' && (
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search refunds..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="refund-search" />
          </div>
          {filteredHistory.length === 0 ? (
            <Card className="p-12 text-center"><p className="text-slate-500">No refunds found</p></Card>
          ) : (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-800">
                    <tr>
                      <th className="text-left p-3 font-medium text-slate-600">Date</th>
                      <th className="text-left p-3 font-medium text-slate-600">Client</th>
                      <th className="text-left p-3 font-medium text-slate-600">Product</th>
                      <th className="text-left p-3 font-medium text-slate-600">Category</th>
                      <th className="text-right p-3 font-medium text-slate-600">Refund</th>
                      <th className="text-center p-3 font-medium text-slate-600">Status</th>
                      <th className="text-center p-3 font-medium text-slate-600">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistory.map((r, idx) => (
                      <tr key={r.id || idx} className="border-t hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer" onClick={() => openDetail(r.id)} data-testid={`history-row-${idx}`}>
                        <td className="p-3 text-slate-600">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</td>
                        <td className="p-3"><span className="font-medium text-slate-800 dark:text-white">{r.client_name}</span><br/><span className="text-xs text-slate-400">{r.client_email}</span></td>
                        <td className="p-3 text-slate-600">{r.product_name || '-'}</td>
                        <td className="p-3"><Badge variant="outline" className="text-xs">{(r.category || 'other').replace('_',' ')}</Badge></td>
                        <td className="p-3 text-right font-bold text-red-600">₹{(r.amount || 0).toLocaleString()}</td>
                        <td className="p-3 text-center"><Badge className={r.status === 'processed' ? 'bg-emerald-100 text-emerald-700' : r.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{r.status}</Badge></td>
                        <td className="p-3 text-center"><ChevronRight className="h-4 w-4 text-slate-400 mx-auto" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* PA REFUNDS */}
      {activeView === 'pa_pending' && (
        <div className="space-y-3">
          {(data.pa_refunds_pending || []).length === 0 ? (
            <Card className="p-12 text-center"><CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" /><p className="text-lg font-semibold text-slate-600">No Pending PA Refunds</p></Card>
          ) : (data.pa_refunds_pending || []).map((pa, idx) => (
            <Card key={pa.id} className="p-5 border-l-4 border-l-blue-400" data-testid={`pa-refund-${idx}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-slate-800 dark:text-white">{pa.client_name}</h4>
                    <Badge className="bg-blue-100 text-blue-700">{pa.pa_number}</Badge>
                  </div>
                  <p className="text-sm text-slate-500">{pa.client_email} | Partner: {pa.partner_name}</p>
                  <p className="text-sm text-slate-500">Reason: {pa.reason}</p>
                  <p className="text-sm font-semibold text-red-600 mt-1">₹{pa.amount?.toLocaleString()}</p>
                </div>
                <Button onClick={() => handleProcessPARefund(pa.id)} disabled={paRefundProcessing === pa.id}
                  className="bg-[#f7620b] hover:bg-[#e0580a] text-white" data-testid={`process-pa-${idx}`}>
                  {paRefundProcessing === pa.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RotateCcw className="h-4 w-4 mr-1" />}
                  Process Refund
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ISSUE NEW REFUND */}
      {activeView === 'eligible' && (
        <div className="space-y-3">
          {(data.eligible_for_refund || []).length === 0 ? (
            <Card className="p-12 text-center"><p className="text-slate-500">No sales eligible for refund</p></Card>
          ) : (data.eligible_for_refund || []).map((sale, idx) => (
            <Card key={sale.sale_id} className="p-4" data-testid={`eligible-${idx}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-slate-800 dark:text-white">{sale.client_name}</h4>
                  <p className="text-sm text-slate-500">{sale.product_name} | Fee: ₹{(sale.fee_amount || 0).toLocaleString()} | Received: ₹{(sale.amount_received || 0).toLocaleString()}</p>
                  <p className="text-sm text-[#2a777a] font-semibold">Max Refundable: ₹{sale.max_refundable?.toLocaleString()}</p>
                </div>
                <Button onClick={() => setRefundDialog({ open: true, sale, amount: sale.max_refundable, reason: '', method: 'original_payment', notes: '', category: '' })}
                  className="bg-red-600 hover:bg-red-700 text-white" data-testid={`initiate-refund-${idx}`}>
                  <RotateCcw className="h-4 w-4 mr-1" />Initiate Refund
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Initiate Refund Dialog */}
      <Dialog open={refundDialog.open} onOpenChange={(o) => setRefundDialog({ ...refundDialog, open: o })}>
        <DialogContent><DialogHeader><DialogTitle>Initiate Refund</DialogTitle><DialogDescription>This will create a refund request that needs review before processing</DialogDescription></DialogHeader>
          <div className="space-y-4 py-3">
            {refundDialog.sale && <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"><p className="font-medium">{refundDialog.sale.client_name}</p><p className="text-sm text-slate-500">Max: ₹{refundDialog.sale.max_refundable?.toLocaleString()}</p></div>}
            <div><Label>Amount (₹) *</Label><Input type="number" value={refundDialog.amount} onChange={(e) => setRefundDialog({ ...refundDialog, amount: parseFloat(e.target.value) || 0 })} data-testid="refund-amount" /></div>
            <div><Label>Category *</Label>
              <Select value={refundDialog.category} onValueChange={(v) => setRefundDialog({ ...refundDialog, category: v })}>
                <SelectTrigger data-testid="refund-category"><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="service_issue">Service Issue</SelectItem>
                  <SelectItem value="client_request">Client Request</SelectItem>
                  <SelectItem value="overcharge">Overcharge</SelectItem>
                  <SelectItem value="duplicate_payment">Duplicate Payment</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label>Reason * (min 5 chars)</Label><Textarea value={refundDialog.reason} onChange={(e) => setRefundDialog({ ...refundDialog, reason: e.target.value })} rows={2} data-testid="refund-reason" /></div>
            <div><Label>Method</Label>
              <Select value={refundDialog.method} onValueChange={(v) => setRefundDialog({ ...refundDialog, method: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="original_payment">Original Payment</SelectItem>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="cheque">Cheque</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label>Notes (optional)</Label><Textarea value={refundDialog.notes} onChange={(e) => setRefundDialog({ ...refundDialog, notes: e.target.value })} rows={2} /></div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setRefundDialog({ ...refundDialog, open: false })}>Cancel</Button>
              <Button onClick={handleInitiateRefund} disabled={processing} className="bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-initiate">
                {processing && <Loader2 className="h-4 w-4 animate-spin mr-1" />}Initiate Refund
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Review Dialog */}
      <Dialog open={reviewDialog.open} onOpenChange={(o) => setReviewDialog({ ...reviewDialog, open: o })}>
        <DialogContent><DialogHeader><DialogTitle>{reviewDialog.action === 'approve' ? 'Approve Refund' : 'Reject Refund'}</DialogTitle><DialogDescription>Confirm your review decision</DialogDescription></DialogHeader>
          <div className="space-y-4 py-3">
            {reviewDialog.refund && (
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <p className="font-medium">{reviewDialog.refund.client_name}</p>
                <p className="text-sm text-red-600 font-bold">₹{(reviewDialog.refund.amount || 0).toLocaleString()}</p>
                <p className="text-xs text-slate-500 mt-1">Reason: {reviewDialog.refund.reason}</p>
              </div>
            )}
            <div>
              <Label>{reviewDialog.action === 'reject' ? 'Rejection Reason * (min 5 chars)' : 'Review Notes (optional)'}</Label>
              <Textarea value={reviewDialog.notes} onChange={(e) => setReviewDialog({ ...reviewDialog, notes: e.target.value })} rows={3} data-testid="review-notes" />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setReviewDialog({ ...reviewDialog, open: false })}>Cancel</Button>
              <Button onClick={handleReview} disabled={processing} className={reviewDialog.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'} data-testid="confirm-review">
                {processing && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {reviewDialog.action === 'approve' ? 'Approve & Process' : 'Reject Refund'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RefundManager;
