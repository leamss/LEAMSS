import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Bell, Send, Loader2, Search, AlertTriangle, Clock, CheckCircle,
  DollarSign, Users, Filter, Download, History, MessageSquare
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PaymentReminders = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('pending');
  const [searchTerm, setSearchTerm] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('all');
  const [sendingId, setSendingId] = useState(null);
  const [bulkSending, setBulkSending] = useState(false);
  const [customDialog, setCustomDialog] = useState({ open: false, sale: null, message: '' });
  const [history, setHistory] = useState([]);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/reminders/pending-payments`, { headers });
      setData(res.data);
    } catch (e) {
      toast.error('Failed to load reminders');
    }
    setLoading(false);
  };

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API}/reminders/history`, { headers });
      setHistory(res.data || []);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { loadData(); loadHistory(); }, []);

  const handleSendReminder = async (saleId, customMsg) => {
    setSendingId(saleId);
    try {
      const payload = {};
      if (customMsg) payload.message = customMsg;
      await axios.post(`${API}/reminders/send/${saleId}`, payload, { headers });
      toast.success('Reminder sent!');
      setCustomDialog({ open: false, sale: null, message: '' });
      loadData();
      loadHistory();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
    setSendingId(null);
  };

  const handleBulkSend = async () => {
    setBulkSending(true);
    try {
      const res = await axios.post(`${API}/reminders/send-bulk`, {}, { headers });
      toast.success(res.data.message);
      loadData();
      loadHistory();
    } catch (e) {
      toast.error('Bulk send failed');
    }
    setBulkSending(false);
  };

  const downloadCSV = () => {
    const items = data?.items || [];
    if (!items.length) { toast.error('No data'); return; }
    const cols = ['Client', 'Email', 'Mobile', 'Product', 'Partner', 'Fee (₹)', 'Paid (₹)', 'Pending (₹)', 'Urgency', 'Days Overdue', 'Reminders Sent', 'Last Reminder'];
    const rows = items.map(i => [i.client_name, i.client_email, i.client_mobile || '', i.product_name, i.partner_name || '', i.fee_amount, i.amount_received, i.pending_amount, i.urgency, i.days_since_creation, i.reminder_count, i.last_reminder_sent || 'Never']);
    const csv = [cols.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `payment_reminders_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link); link.click(); link.remove();
    toast.success('Report downloaded');
  };

  if (loading || !data) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  const s = data.stats || {};
  const items = data.items || [];
  const filtered = items.filter(i => {
    if (urgencyFilter !== 'all' && i.urgency !== urgencyFilter) return false;
    if (searchTerm && !i.client_name.toLowerCase().includes(searchTerm.toLowerCase()) && !i.client_email.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const urgencyConfig = {
    critical: { icon: AlertTriangle, color: 'border-red-500', badge: 'bg-red-500 text-white', cardBg: 'bg-red-50 dark:bg-red-900/20' },
    high: { icon: Clock, color: 'border-orange-500', badge: 'bg-orange-500 text-white', cardBg: 'bg-orange-50 dark:bg-orange-900/20' },
    medium: { icon: Clock, color: 'border-amber-400', badge: 'bg-amber-500 text-white', cardBg: '' },
    low: { icon: CheckCircle, color: 'border-slate-300', badge: 'bg-slate-400 text-white', cardBg: '' },
  };

  return (
    <div className="space-y-5" data-testid="payment-reminders">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <Card className="p-3 text-center bg-gradient-to-br from-slate-50 to-slate-100 border-slate-200 cursor-pointer" onClick={() => setUrgencyFilter('all')}>
          <p className="text-xs text-slate-600 font-medium">Total</p>
          <p className="text-xl font-bold text-slate-800">{s.total_clients}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-red-50 to-red-100 border-red-200 cursor-pointer" onClick={() => setUrgencyFilter('critical')}>
          <p className="text-xs text-red-600 font-medium">Critical (14d+)</p>
          <p className="text-xl font-bold text-red-800">{s.critical}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200 cursor-pointer" onClick={() => setUrgencyFilter('high')}>
          <p className="text-xs text-orange-600 font-medium">High (7-14d)</p>
          <p className="text-xl font-bold text-orange-800">{s.high}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200 cursor-pointer" onClick={() => setUrgencyFilter('medium')}>
          <p className="text-xs text-amber-600 font-medium">Medium (3-7d)</p>
          <p className="text-xl font-bold text-amber-800">{s.medium}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200 cursor-pointer" onClick={() => setUrgencyFilter('low')}>
          <p className="text-xs text-emerald-600 font-medium">Low (0-3d)</p>
          <p className="text-xl font-bold text-emerald-800">{s.low}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <p className="text-xs text-blue-600 font-medium">Never Reminded</p>
          <p className="text-xl font-bold text-blue-800">{s.never_reminded}</p>
        </Card>
        <Card className="p-3 text-center bg-gradient-to-br from-leamss-orange-50 to-leamss-orange-100 border-leamss-orange-200">
          <p className="text-xs text-leamss-orange-600 font-medium">Total Pending</p>
          <p className="text-xl font-bold text-leamss-orange-800">₹{(s.total_pending || 0).toLocaleString()}</p>
        </Card>
      </div>

      {/* Controls */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
            <button onClick={() => setView('pending')} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${view === 'pending' ? 'bg-white dark:bg-slate-700 shadow-sm text-[#2a777a]' : 'text-slate-500'}`} data-testid="view-pending">Pending</button>
            <button onClick={() => setView('history')} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${view === 'history' ? 'bg-white dark:bg-slate-700 shadow-sm text-[#2a777a]' : 'text-slate-500'}`} data-testid="view-history">History</button>
          </div>
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search client..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="reminder-search" />
          </div>
          <Select value={urgencyFilter} onValueChange={setUrgencyFilter}>
            <SelectTrigger className="w-[140px]" data-testid="urgency-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Urgency</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={downloadCSV} data-testid="download-reminders"><Download className="h-4 w-4 mr-1" />CSV</Button>
          <Button onClick={handleBulkSend} disabled={bulkSending} className="bg-[#f7620b] hover:bg-[#e0580a] text-white" data-testid="bulk-remind">
            {bulkSending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
            Bulk Remind (3d+ Overdue)
          </Button>
        </div>
      </Card>

      {/* Pending View */}
      {view === 'pending' && (
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <Card className="p-12 text-center"><CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" /><p className="text-lg font-semibold text-slate-700">All Clear!</p><p className="text-slate-500">No pending payments{urgencyFilter !== 'all' ? ` at ${urgencyFilter} urgency` : ''}</p></Card>
          ) : (
            filtered.map((item, idx) => {
              const uc = urgencyConfig[item.urgency] || urgencyConfig.low;
              const progressPct = item.fee_amount > 0 ? Math.round((item.amount_received / item.fee_amount) * 100) : 0;
              return (
                <Card key={item.sale_id} className={`p-5 border-l-4 ${uc.color} ${uc.cardBg} hover:shadow-md transition-shadow`} data-testid={`reminder-card-${idx}`}>
                  <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <h4 className="font-semibold text-slate-800 dark:text-white">{item.client_name}</h4>
                        <Badge className={`text-xs ${uc.badge}`}>{item.urgency.toUpperCase()} — {item.days_since_creation}d</Badge>
                        {item.reminder_count > 0 && <Badge variant="outline" className="text-xs"><Bell className="h-3 w-3 mr-0.5" />{item.reminder_count}x sent</Badge>}
                        {item.reminder_count === 0 && <Badge className="bg-blue-100 text-blue-700 text-xs">Never reminded</Badge>}
                      </div>
                      <p className="text-sm text-slate-500">{item.client_email} {item.client_mobile ? `| ${item.client_mobile}` : ''}</p>
                      <p className="text-sm text-slate-500">{item.product_name} {item.partner_name ? `| Partner: ${item.partner_name}` : ''}</p>

                      {/* Payment progress bar */}
                      <div className="mt-3">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-500">Payment Progress</span>
                          <span className="font-medium">{progressPct}% (₹{(item.amount_received || 0).toLocaleString()} / ₹{(item.fee_amount || 0).toLocaleString()})</span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                          <div className="h-2 rounded-full bg-emerald-500 transition-all" style={{ width: `${progressPct}%` }} />
                        </div>
                        <div className="flex justify-between mt-1 text-xs">
                          <span className="text-emerald-600 font-medium">Paid: ₹{(item.amount_received || 0).toLocaleString()}</span>
                          <span className="text-[#f7620b] font-bold">Pending: ₹{(item.pending_amount || 0).toLocaleString()}</span>
                        </div>
                      </div>

                      {item.last_reminder_sent && (
                        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1"><History className="h-3 w-3" />Last: {new Date(item.last_reminder_sent).toLocaleDateString()} {item.days_since_last_reminder !== null ? `(${item.days_since_last_reminder}d ago)` : ''}</p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-2 justify-center">
                      <Button size="sm" onClick={() => handleSendReminder(item.sale_id)} disabled={sendingId === item.sale_id}
                        className="bg-[#f7620b] hover:bg-[#e0580a] text-white" data-testid={`remind-${idx}`}>
                        {sendingId === item.sale_id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Bell className="h-4 w-4 mr-1" />}
                        Quick Remind
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setCustomDialog({ open: true, sale: item, message: `Dear ${item.client_name},\n\nThis is a reminder about your pending payment of ₹${(item.pending_amount || 0).toLocaleString()} for ${item.product_name}.\n\nTotal Fee: ₹${(item.fee_amount || 0).toLocaleString()}\nPaid: ₹${(item.amount_received || 0).toLocaleString()}\nPending: ₹${(item.pending_amount || 0).toLocaleString()}\n\nPlease complete your payment at the earliest.\n\nThank you,\nLEAMSS Immigration` })}
                        data-testid={`custom-remind-${idx}`}>
                        <MessageSquare className="h-4 w-4 mr-1" />Custom Message
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* History View */}
      {view === 'history' && (
        <Card className="overflow-hidden">
          {history.length === 0 ? (
            <div className="p-12 text-center"><History className="h-12 w-12 text-slate-300 mx-auto mb-4" /><p className="text-slate-500">No reminders sent yet</p></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800">
                  <tr>
                    <th className="text-left p-3 font-medium text-slate-600">Date</th>
                    <th className="text-left p-3 font-medium text-slate-600">Client</th>
                    <th className="text-left p-3 font-medium text-slate-600">Email</th>
                    <th className="text-right p-3 font-medium text-slate-600">Pending (₹)</th>
                    <th className="text-center p-3 font-medium text-slate-600">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, idx) => (
                    <tr key={idx} className="border-t hover:bg-slate-50 dark:hover:bg-slate-800" data-testid={`history-row-${idx}`}>
                      <td className="p-3 text-slate-600">{h.sent_at ? new Date(h.sent_at).toLocaleString() : '-'}</td>
                      <td className="p-3 font-medium text-slate-800 dark:text-white">{h.client_name || '-'}</td>
                      <td className="p-3 text-slate-500">{h.client_email || '-'}</td>
                      <td className="p-3 text-right text-[#f7620b] font-semibold">₹{(h.pending_amount || 0).toLocaleString()}</td>
                      <td className="p-3 text-center"><Badge variant="outline">{h.reminder_count || 1}x</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Custom Message Dialog */}
      <Dialog open={customDialog.open} onOpenChange={(o) => setCustomDialog({ ...customDialog, open: o })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Custom Reminder Message</DialogTitle>
            <DialogDescription>Edit the message before sending to {customDialog.sale?.client_name}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-3">
            {customDialog.sale && (
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                <p className="font-medium">{customDialog.sale.client_name}</p>
                <p className="text-slate-500">{customDialog.sale.client_email}</p>
                <p className="text-[#f7620b] font-semibold mt-1">Pending: ₹{(customDialog.sale.pending_amount || 0).toLocaleString()}</p>
              </div>
            )}
            <Textarea value={customDialog.message} onChange={(e) => setCustomDialog({ ...customDialog, message: e.target.value })} rows={8} data-testid="custom-msg-input" />
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setCustomDialog({ ...customDialog, open: false })}>Cancel</Button>
              <Button onClick={() => handleSendReminder(customDialog.sale?.sale_id, customDialog.message)} disabled={sendingId === customDialog.sale?.sale_id}
                className="bg-[#f7620b] hover:bg-[#e0580a] text-white" data-testid="send-custom-remind">
                {sendingId === customDialog.sale?.sale_id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
                Send Custom Reminder
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PaymentReminders;
