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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  RotateCcw, DollarSign, TrendingDown, CheckCircle, Loader2, AlertTriangle, Search
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RefundManager = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('history');
  const [refundDialog, setRefundDialog] = useState({ open: false, sale: null, amount: 0, reason: '', method: 'original_payment', notes: '' });
  const [paRefundProcessing, setPaRefundProcessing] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

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

  const handleProcessRefund = async () => {
    if (!refundDialog.reason || refundDialog.reason.trim().length < 5) {
      toast.error('Reason required (min 5 characters)');
      return;
    }
    if (!refundDialog.amount || refundDialog.amount <= 0) {
      toast.error('Amount must be positive');
      return;
    }
    setProcessing(true);
    try {
      await axios.post(`${API}/refunds`, {
        sale_id: refundDialog.sale.sale_id,
        amount: refundDialog.amount,
        reason: refundDialog.reason.trim(),
        refund_method: refundDialog.method,
        notes: refundDialog.notes,
      }, { headers });
      toast.success('Refund processed successfully');
      setRefundDialog({ open: false, sale: null, amount: 0, reason: '', method: 'original_payment', notes: '' });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Refund failed');
    }
    setProcessing(false);
  };

  const handleProcessPARefund = async (paId) => {
    setPaRefundProcessing(paId);
    try {
      await axios.post(`${API}/admin-super/refund-manager/process-pa-refund`, {
        pa_id: paId,
        notes: 'Pre-assessment refund processed from Refund Manager',
      }, { headers });
      toast.success('PA refund processed');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'PA refund failed');
    }
    setPaRefundProcessing(null);
  };

  if (loading || !data) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  const filteredRefunds = (data.refunds || []).filter(r =>
    !searchTerm || r.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) || r.reason?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6" data-testid="refund-manager">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <div className="flex items-center gap-2 mb-1"><RotateCcw className="h-4 w-4 text-red-600" /><p className="text-xs text-red-600 font-medium">Total Refunded</p></div>
          <p className="text-2xl font-bold text-red-800">₹{(data.stats?.total_refunded || 0).toLocaleString()}</p>
          <p className="text-xs text-red-500 mt-1">{data.stats?.total_count || 0} refunds</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
          <div className="flex items-center gap-2 mb-1"><AlertTriangle className="h-4 w-4 text-amber-600" /><p className="text-xs text-amber-600 font-medium">PA Refunds Pending</p></div>
          <p className="text-2xl font-bold text-amber-800">{data.stats?.pa_pending_count || 0}</p>
          <p className="text-xs text-amber-500 mt-1">₹{(data.stats?.pa_pending_amount || 0).toLocaleString()}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-center gap-2 mb-1"><DollarSign className="h-4 w-4 text-blue-600" /><p className="text-xs text-blue-600 font-medium">Eligible for Refund</p></div>
          <p className="text-2xl font-bold text-blue-800">{(data.eligible_for_refund || []).length}</p>
          <p className="text-xs text-blue-500 mt-1">sales with received amount</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 border-slate-200">
          <div className="flex items-center gap-2 mb-1"><TrendingDown className="h-4 w-4 text-slate-600" /><p className="text-xs text-slate-600 font-medium">Monthly Trend</p></div>
          <p className="text-2xl font-bold text-slate-800">{(data.monthly_trend || []).length}</p>
          <p className="text-xs text-slate-500 mt-1">months of data</p>
        </Card>
      </div>

      {/* View Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {[
          { key: 'history', label: 'Refund History', count: data.refunds?.length || 0 },
          { key: 'pa_pending', label: 'PA Refunds Pending', count: data.pa_refunds_pending?.length || 0 },
          { key: 'eligible', label: 'Issue New Refund', count: data.eligible_for_refund?.length || 0 },
        ].map(tab => (
          <Button
            key={tab.key}
            variant={activeView === tab.key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveView(tab.key)}
            className={activeView === tab.key ? 'bg-[#2a777a] hover:bg-[#236466]' : ''}
            data-testid={`refund-tab-${tab.key}`}
          >
            {tab.label} <Badge className="ml-2 bg-white/20 text-current">{tab.count}</Badge>
          </Button>
        ))}
      </div>

      {/* Refund History */}
      {activeView === 'history' && (
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search refunds..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="refund-search" />
          </div>
          {filteredRefunds.length === 0 ? (
            <Card className="p-12 text-center">
              <CheckCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600">No refunds found</p>
            </Card>
          ) : (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left p-3 font-medium text-slate-600">Date</th>
                      <th className="text-left p-3 font-medium text-slate-600">Client</th>
                      <th className="text-left p-3 font-medium text-slate-600">Product</th>
                      <th className="text-right p-3 font-medium text-slate-600">Original</th>
                      <th className="text-right p-3 font-medium text-slate-600">Refund</th>
                      <th className="text-left p-3 font-medium text-slate-600">Reason</th>
                      <th className="text-left p-3 font-medium text-slate-600">Method</th>
                      <th className="text-left p-3 font-medium text-slate-600">By</th>
                      <th className="text-center p-3 font-medium text-slate-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRefunds.map((r, idx) => (
                      <tr key={r.id || idx} className="border-t hover:bg-slate-50" data-testid={`refund-row-${idx}`}>
                        <td className="p-3 text-slate-600">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</td>
                        <td className="p-3 font-medium text-slate-800">{r.client_name}</td>
                        <td className="p-3 text-slate-600">{r.product_name || '-'}</td>
                        <td className="p-3 text-right text-slate-600">₹{(r.original_fee || 0).toLocaleString()}</td>
                        <td className="p-3 text-right font-bold text-red-600">₹{(r.amount || 0).toLocaleString()}</td>
                        <td className="p-3 text-slate-600 max-w-[180px] truncate" title={r.reason}>{r.reason}</td>
                        <td className="p-3 text-slate-600 capitalize">{r.refund_method?.replace('_', ' ')}</td>
                        <td className="p-3 text-slate-600">{r.processed_by_name}</td>
                        <td className="p-3 text-center">
                          <Badge className={r.status === 'processed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>{r.status}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* PA Refunds Pending */}
      {activeView === 'pa_pending' && (
        <div className="space-y-3">
          {(data.pa_refunds_pending || []).length === 0 ? (
            <Card className="p-12 text-center">
              <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
              <p className="text-lg font-semibold text-slate-700">No Pending PA Refunds</p>
            </Card>
          ) : (
            (data.pa_refunds_pending || []).map((pa, idx) => (
              <Card key={pa.id} className="p-5 border-l-4 border-l-amber-400" data-testid={`pa-refund-${idx}`}>
                <div className="flex flex-col md:flex-row justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-slate-800">{pa.client_name}</h4>
                      <Badge className="bg-amber-100 text-amber-700">{pa.pa_number}</Badge>
                    </div>
                    <p className="text-sm text-slate-600">{pa.client_email} | Partner: {pa.partner_name}</p>
                    <p className="text-sm text-slate-500">Reason: {pa.reason}</p>
                    <p className="text-sm font-medium text-red-600 mt-1">Refund Amount: ₹{pa.amount?.toLocaleString()}</p>
                  </div>
                  <Button
                    onClick={() => handleProcessPARefund(pa.id)}
                    disabled={paRefundProcessing === pa.id}
                    className="bg-[#f7620b] hover:bg-[#e0580a] text-white"
                    data-testid={`process-pa-refund-${idx}`}
                  >
                    {paRefundProcessing === pa.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RotateCcw className="h-4 w-4 mr-1" />}
                    Process Refund
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Issue New Refund */}
      {activeView === 'eligible' && (
        <div className="space-y-3">
          {(data.eligible_for_refund || []).length === 0 ? (
            <Card className="p-12 text-center">
              <CheckCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600">No sales eligible for refund</p>
            </Card>
          ) : (
            (data.eligible_for_refund || []).map((sale, idx) => (
              <Card key={sale.sale_id} className="p-5" data-testid={`eligible-refund-${idx}`}>
                <div className="flex flex-col md:flex-row justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-800">{sale.client_name}</h4>
                    <p className="text-sm text-slate-600">{sale.client_email} | {sale.product_name}</p>
                    <div className="flex gap-4 mt-2 text-sm">
                      <span>Fee: <span className="font-semibold">₹{(sale.fee_amount || 0).toLocaleString()}</span></span>
                      <span className="text-emerald-600">Received: ₹{(sale.amount_received || 0).toLocaleString()}</span>
                      {sale.already_refunded > 0 && <span className="text-red-600">Already Refunded: ₹{sale.already_refunded.toLocaleString()}</span>}
                      <span className="text-[#2a777a] font-semibold">Max Refundable: ₹{sale.max_refundable?.toLocaleString()}</span>
                    </div>
                  </div>
                  <Button
                    onClick={() => setRefundDialog({ open: true, sale, amount: sale.max_refundable, reason: '', method: 'original_payment', notes: '' })}
                    className="bg-red-600 hover:bg-red-700 text-white"
                    data-testid={`initiate-refund-${idx}`}
                  >
                    <RotateCcw className="h-4 w-4 mr-1" />Issue Refund
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Refund Dialog */}
      <Dialog open={refundDialog.open} onOpenChange={(o) => setRefundDialog({ ...refundDialog, open: o })}>
        <DialogContent>
          <DialogHeader><DialogTitle>Process Refund</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            {refundDialog.sale && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium text-slate-800">{refundDialog.sale.client_name}</p>
                <p className="text-sm text-slate-600">Max refundable: ₹{refundDialog.sale.max_refundable?.toLocaleString()}</p>
              </div>
            )}
            <div>
              <Label>Refund Amount (₹)</Label>
              <Input type="number" value={refundDialog.amount} onChange={(e) => setRefundDialog({ ...refundDialog, amount: parseFloat(e.target.value) || 0 })} max={refundDialog.sale?.max_refundable} data-testid="refund-amount-input" />
            </div>
            <div>
              <Label>Reason (required, min 5 chars)</Label>
              <Textarea value={refundDialog.reason} onChange={(e) => setRefundDialog({ ...refundDialog, reason: e.target.value })} placeholder="Reason for refund..." rows={2} data-testid="refund-reason-input" />
            </div>
            <div>
              <Label>Method</Label>
              <Select value={refundDialog.method} onValueChange={(v) => setRefundDialog({ ...refundDialog, method: v })}>
                <SelectTrigger data-testid="refund-method-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="original_payment">Original Payment Method</SelectItem>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="cheque">Cheque</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes (optional)</Label>
              <Textarea value={refundDialog.notes} onChange={(e) => setRefundDialog({ ...refundDialog, notes: e.target.value })} placeholder="Additional notes..." rows={2} />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setRefundDialog({ ...refundDialog, open: false })}>Cancel</Button>
              <Button onClick={handleProcessRefund} disabled={processing} className="bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-refund-btn">
                {processing ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RotateCcw className="h-4 w-4 mr-1" />}
                Process Refund
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RefundManager;
