import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  CheckCircle, XCircle, Clock, FileText, Users, Briefcase,
  AlertTriangle, Search, Filter, Loader2, MessageSquare
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ApprovalCenter = ({ token, onNavigate }) => {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [actionDialog, setActionDialog] = useState({ open: false, item: null, action: '', notes: '' });
  const [processing, setProcessing] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/admin-super/approval-center`, { headers });
      setItems(res.data.items || []);
      setSummary(res.data.summary || {});
    } catch (e) {
      toast.error('Failed to load approval center');
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async () => {
    if (actionDialog.action === 'reject' && (!actionDialog.notes || actionDialog.notes.trim().length < 5)) {
      toast.error('Rejection reason required (min 5 characters)');
      return;
    }
    setProcessing(true);
    try {
      await axios.post(`${API}/admin-super/approval-center/action`, {
        item_id: actionDialog.item.id,
        item_type: actionDialog.item.type,
        action: actionDialog.action,
        notes: actionDialog.notes,
      }, { headers });
      toast.success(`Item ${actionDialog.action}d successfully`);
      setActionDialog({ open: false, item: null, action: '', notes: '' });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Action failed');
    }
    setProcessing(false);
  };

  const filtered = items.filter(i => {
    if (filter !== 'all' && i.type !== filter) return false;
    if (searchTerm && !i.title.toLowerCase().includes(searchTerm.toLowerCase()) && !i.subtitle?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const typeIcon = (type) => {
    switch (type) {
      case 'sale': return <FileText className="h-5 w-5 text-emerald-600" />;
      case 'pre_assessment': return <Users className="h-5 w-5 text-blue-600" />;
      case 'document': return <Briefcase className="h-5 w-5 text-amber-600" />;
      case 'ticket': return <MessageSquare className="h-5 w-5 text-red-600" />;
      default: return <Clock className="h-5 w-5 text-slate-500" />;
    }
  };

  const typeBadge = (type) => {
    const styles = {
      sale: 'bg-emerald-100 text-emerald-700 border-emerald-300',
      pre_assessment: 'bg-blue-100 text-blue-700 border-blue-300',
      document: 'bg-amber-100 text-amber-700 border-amber-300',
      ticket: 'bg-red-100 text-red-700 border-red-300',
    };
    const labels = { sale: 'Sale', pre_assessment: 'Pre-Assessment', document: 'Document', ticket: 'Ticket' };
    return <Badge className={styles[type] || 'bg-slate-100 text-slate-700'}>{labels[type] || type}</Badge>;
  };

  const priorityBadge = (priority) => {
    const styles = {
      high: 'bg-red-500 text-white',
      medium: 'bg-amber-500 text-white',
      low: 'bg-slate-400 text-white',
      urgent: 'bg-red-700 text-white',
    };
    return <Badge className={styles[priority] || 'bg-slate-400 text-white'}>{priority}</Badge>;
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div className="space-y-6" data-testid="approval-center">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('sale')}>
          <p className="text-xs text-amber-600 font-medium">Pending Sales</p>
          <p className="text-2xl font-bold text-amber-800">{summary.pending_sales || 0}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('pre_assessment')}>
          <p className="text-xs text-blue-600 font-medium">Pre-Assessments</p>
          <p className="text-2xl font-bold text-blue-800">{summary.pending_pre_assessments || 0}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('document')}>
          <p className="text-xs text-emerald-600 font-medium">Documents</p>
          <p className="text-2xl font-bold text-emerald-800">{summary.pending_documents || 0}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-red-50 to-red-100 border-red-200 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('ticket')}>
          <p className="text-xs text-red-600 font-medium">Urgent Tickets</p>
          <p className="text-2xl font-bold text-red-800">{summary.urgent_tickets || 0}</p>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 border-slate-200 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('all')}>
          <p className="text-xs text-slate-600 font-medium">Total Pending</p>
          <p className="text-2xl font-bold text-slate-800">{summary.total || 0}</p>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <Filter className="h-4 w-4 text-slate-500" />
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search items..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="approval-search" />
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[160px]" data-testid="approval-type-filter">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="sale">Sales</SelectItem>
              <SelectItem value="pre_assessment">Pre-Assessments</SelectItem>
              <SelectItem value="document">Documents</SelectItem>
              <SelectItem value="ticket">Tickets</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadData} data-testid="approval-refresh">Refresh</Button>
        </div>
      </Card>

      {/* Items List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <Card className="p-12 text-center">
            <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
            <p className="text-lg font-semibold text-slate-700">All Clear!</p>
            <p className="text-slate-500 mt-1">No pending approvals in this category</p>
          </Card>
        ) : (
          filtered.map((item, idx) => (
            <Card key={`${item.type}-${item.id}-${idx}`} className="p-4 hover:shadow-md transition-shadow border-l-4" style={{
              borderLeftColor: item.type === 'sale' ? '#059669' : item.type === 'pre_assessment' ? '#2563eb' : item.type === 'document' ? '#d97706' : '#dc2626'
            }} data-testid={`approval-item-${item.type}-${idx}`}>
              <div className="flex flex-col md:flex-row justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <div className="mt-1">{typeIcon(item.type)}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h4 className="font-semibold text-slate-800">{item.title}</h4>
                      {typeBadge(item.type)}
                      {priorityBadge(item.priority)}
                    </div>
                    <p className="text-sm text-slate-600">{item.subtitle}</p>
                    {item.amount > 0 && <p className="text-sm font-medium text-[#2a777a] mt-1">Amount: ₹{item.amount?.toLocaleString()}</p>}
                    <p className="text-xs text-slate-400 mt-1">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</p>
                  </div>
                </div>
                {item.type !== 'ticket' && (
                  <div className="flex items-center gap-2">
                    <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => setActionDialog({ open: true, item, action: 'approve', notes: '' })} data-testid={`approve-${item.type}-${idx}`}>
                      <CheckCircle className="h-4 w-4 mr-1" />Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => setActionDialog({ open: true, item, action: 'reject', notes: '' })} data-testid={`reject-${item.type}-${idx}`}>
                      <XCircle className="h-4 w-4 mr-1" />Reject
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Action Dialog */}
      <Dialog open={actionDialog.open} onOpenChange={(o) => setActionDialog({ ...actionDialog, open: o })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{actionDialog.action === 'approve' ? 'Approve' : 'Reject'} Item</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {actionDialog.item && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium text-slate-800">{actionDialog.item.title}</p>
                <p className="text-sm text-slate-600">{actionDialog.item.subtitle}</p>
              </div>
            )}
            <div>
              <label className="text-sm font-medium text-slate-700">
                {actionDialog.action === 'reject' ? 'Rejection Reason (required, min 5 chars)' : 'Notes (optional)'}
              </label>
              <Textarea
                value={actionDialog.notes}
                onChange={(e) => setActionDialog({ ...actionDialog, notes: e.target.value })}
                placeholder={actionDialog.action === 'reject' ? 'Reason for rejection...' : 'Add any notes...'}
                rows={3}
                data-testid="action-notes-input"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setActionDialog({ ...actionDialog, open: false })}>Cancel</Button>
              <Button
                onClick={handleAction}
                disabled={processing}
                className={actionDialog.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                data-testid="confirm-action-btn"
              >
                {processing ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                {actionDialog.action === 'approve' ? 'Confirm Approve' : 'Confirm Reject'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApprovalCenter;
