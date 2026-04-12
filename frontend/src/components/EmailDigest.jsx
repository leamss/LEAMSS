import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Mail, Send, Loader2, TrendingUp, DollarSign, Users,
  Briefcase, MessageSquare, Clock, CheckCircle, AlertTriangle, Eye
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EmailDigest = ({ token }) => {
  const [digest, setDigest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [settings, setSettings] = useState({ frequency: 'weekly', enabled: true });
  const [previewOpen, setPreviewOpen] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const load = async () => {
      try {
        const [previewRes, settingsRes] = await Promise.all([
          axios.get(`${API}/email-digest/preview`, { headers }),
          axios.get(`${API}/email-digest/settings`, { headers }).catch(() => ({ data: { frequency: 'weekly', enabled: true } })),
        ]);
        setDigest(previewRes.data);
        setSettings(settingsRes.data);
      } catch (e) {
        toast.error('Failed to load digest');
      }
      setLoading(false);
    };
    load();
  }, []);

  const handleSendNow = async () => {
    setSending(true);
    try {
      const res = await axios.post(`${API}/email-digest/send-now`, {}, { headers });
      toast.success(res.data.message);
    } catch (e) {
      toast.error('Failed to send digest');
    }
    setSending(false);
  };

  const handleSaveSettings = async (freq) => {
    try {
      await axios.put(`${API}/email-digest/settings`, { ...settings, frequency: freq }, { headers });
      setSettings({ ...settings, frequency: freq });
      toast.success('Digest settings saved');
    } catch (e) {
      toast.error('Failed to save settings');
    }
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  const r = digest?.revenue || {};
  const a = digest?.approvals || {};
  const c = digest?.cases || {};
  const t = digest?.tickets || {};
  const tp = digest?.top_partner;

  return (
    <div className="space-y-6" data-testid="email-digest">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2"><Mail className="h-5 w-5 text-[#2a777a]" />Quick Stats Digest</h3>
          <p className="text-sm text-slate-500">Preview and send weekly summary to all admins</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={settings.frequency} onValueChange={handleSaveSettings}>
            <SelectTrigger className="w-[130px]" data-testid="digest-frequency"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => setPreviewOpen(true)} variant="outline" data-testid="preview-digest-btn"><Eye className="h-4 w-4 mr-1" />Preview</Button>
          <Button onClick={handleSendNow} disabled={sending} className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="send-digest-btn">
            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
            Send Now
          </Button>
        </div>
      </div>

      {/* Revenue Card */}
      <Card className="p-6 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
        <h4 className="text-sm font-medium text-emerald-600 mb-3 flex items-center gap-2"><DollarSign className="h-4 w-4" />Revenue Overview</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div><p className="text-xs text-slate-500">Total Revenue</p><p className="text-lg font-bold text-slate-800">₹{(r.total || 0).toLocaleString()}</p></div>
          <div><p className="text-xs text-slate-500">Collected</p><p className="text-lg font-bold text-emerald-600">₹{(r.received || 0).toLocaleString()}</p></div>
          <div><p className="text-xs text-slate-500">Pending</p><p className="text-lg font-bold text-amber-600">₹{(r.pending || 0).toLocaleString()}</p></div>
          <div><p className="text-xs text-slate-500">Commission</p><p className="text-lg font-bold text-slate-600">₹{(r.commission || 0).toLocaleString()}</p></div>
          <div><p className="text-xs text-slate-500">Refunded</p><p className="text-lg font-bold text-red-600">₹{(r.refunded || 0).toLocaleString()}</p></div>
          <div><p className="text-xs text-slate-500">Net Revenue</p><p className="text-lg font-bold text-[#2a777a]">₹{(r.net || 0).toLocaleString()}</p></div>
        </div>
        <div className="mt-3 pt-3 border-t border-emerald-200 flex items-center gap-4 text-sm">
          <span className="text-emerald-600 flex items-center gap-1"><TrendingUp className="h-4 w-4" />This Week: {r.week_new_sales || 0} new sales, ₹{(r.week_revenue || 0).toLocaleString()}</span>
        </div>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center bg-red-50 border-red-200">
          <AlertTriangle className="h-6 w-6 text-red-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-red-700">{a.total_pending || 0}</p>
          <p className="text-xs text-red-600">Pending Approvals</p>
          <p className="text-xs text-slate-500 mt-1">{a.pending_sales || 0} sales + {a.pending_pre_assessments || 0} PA</p>
        </Card>
        <Card className="p-4 text-center bg-blue-50 border-blue-200">
          <Briefcase className="h-6 w-6 text-blue-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-blue-700">{c.active || 0}</p>
          <p className="text-xs text-blue-600">Active Cases</p>
          <p className="text-xs text-slate-500 mt-1">{c.completion_rate || 0}% completion</p>
        </Card>
        <Card className="p-4 text-center bg-purple-50 border-purple-200">
          <MessageSquare className="h-6 w-6 text-purple-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-purple-700">{t.open || 0}</p>
          <p className="text-xs text-purple-600">Open Tickets</p>
          <p className="text-xs text-slate-500 mt-1">{t.urgent || 0} urgent</p>
        </Card>
        <Card className="p-4 text-center bg-amber-50 border-amber-200">
          <Users className="h-6 w-6 text-amber-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-amber-700">{digest?.pre_assessments?.total || 0}</p>
          <p className="text-xs text-amber-600">Pre-Assessments</p>
          <p className="text-xs text-slate-500 mt-1">{digest?.pre_assessments?.approved || 0} approved</p>
        </Card>
      </div>

      {/* Top Partner */}
      {tp && (
        <Card className="p-4 bg-gradient-to-r from-amber-50 to-amber-100 border-amber-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-200 rounded-full"><Users className="h-5 w-5 text-amber-700" /></div>
              <div>
                <p className="text-sm font-medium text-amber-800">Top Partner This Week</p>
                <p className="text-lg font-bold text-amber-900">{tp.name}</p>
              </div>
            </div>
            <p className="text-xl font-bold text-amber-800">₹{(tp.revenue || 0).toLocaleString()}</p>
          </div>
        </Card>
      )}

      <p className="text-xs text-slate-400 text-center">Email is in {digest?.revenue ? 'mock' : ''} mode. Configure RESEND_API_KEY for live email delivery.</p>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Email Digest Preview</DialogTitle>
            <DialogDescription>This is what the digest email will look like</DialogDescription>
          </DialogHeader>
          <div className="bg-white border rounded-lg p-6 mt-4">
            <div className="bg-[#2a777a] p-4 rounded-t-lg text-center"><h2 className="text-white text-lg font-bold">LEAMSS Immigration</h2></div>
            <div className="p-4 space-y-4">
              <h3 className="font-semibold text-slate-800">Weekly Stats Digest</h3>
              <div className="bg-emerald-50 p-3 rounded-lg">
                <p className="text-sm font-medium text-emerald-700 mb-2">Revenue Overview</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>Total: ₹{(r.total || 0).toLocaleString()}</div>
                  <div>Collected: ₹{(r.received || 0).toLocaleString()}</div>
                  <div>Pending: ₹{(r.pending || 0).toLocaleString()}</div>
                  <div className="font-bold">Net: ₹{(r.net || 0).toLocaleString()}</div>
                </div>
              </div>
              <div className="flex gap-3 text-center text-xs">
                <div className="flex-1 p-2 bg-red-50 rounded"><p className="font-bold text-red-700 text-lg">{a.total_pending || 0}</p>Pending Approvals</div>
                <div className="flex-1 p-2 bg-blue-50 rounded"><p className="font-bold text-blue-700 text-lg">{c.active || 0}</p>Active Cases</div>
                <div className="flex-1 p-2 bg-purple-50 rounded"><p className="font-bold text-purple-700 text-lg">{t.open || 0}</p>Open Tickets</div>
              </div>
            </div>
            <div className="bg-slate-50 p-3 rounded-b-lg text-center"><p className="text-xs text-slate-400">LEAMSS Portal - Automated Digest</p></div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailDigest;
