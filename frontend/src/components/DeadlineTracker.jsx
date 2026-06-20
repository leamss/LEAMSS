import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Clock, AlertTriangle, CheckCircle, XCircle, Plus, Trash2,
  CalendarClock, FileText, Shield, Loader2, ChevronDown, ChevronRight,
  AlertOctagon, Timer, Bell
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const URGENCY_CONFIG = {
  expired: { bg: 'bg-red-500', text: 'text-white', border: 'border-red-500', light: 'bg-red-50 border-red-200', icon: XCircle, dot: 'bg-red-500' },
  critical: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', light: 'bg-red-50 border-red-200', icon: AlertOctagon, dot: 'bg-red-500' },
  urgent: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-300', light: 'bg-amber-50 border-amber-200', icon: AlertTriangle, dot: 'bg-amber-500' },
  warning: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300', light: 'bg-yellow-50 border-yellow-200', icon: Clock, dot: 'bg-yellow-500' },
  safe: { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300', light: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, dot: 'bg-emerald-500' },
  unknown: { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-300', light: 'bg-slate-50 border-slate-200', icon: Clock, dot: 'bg-slate-400' },
};

const TYPE_LABELS = {
  document_expiry: { label: 'Document Expiry', icon: FileText, color: 'text-blue-600' },
  visa_deadline: { label: 'Visa Deadline', icon: CalendarClock, color: 'text-leamss-orange-600' },
  processing_sla: { label: 'Processing SLA', icon: Timer, color: 'text-leamss-teal-600' },
  task_due: { label: 'Task Due', icon: CheckCircle, color: 'text-teal-600' },
  milestone: { label: 'Milestone', icon: Shield, color: 'text-amber-600' },
  custom: { label: 'Custom', icon: Bell, color: 'text-slate-600' },
};

const DeadlineTracker = ({ token, caseId, role = 'client', caseName = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [filter, setFilter] = useState('all');
  const [newDeadline, setNewDeadline] = useState({
    title: '', deadline_type: 'custom', due_date: '', description: '', step_name: '', auto_remind: true, remind_days_before: 7
  });

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = useCallback(async () => {
    if (!caseId) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/deadlines/case/${caseId}`, { headers });
      setData(res.data);
    } catch (e) { console.error('Failed to load deadlines', e); }
    setLoading(false);
  }, [caseId]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!newDeadline.title || !newDeadline.due_date) { toast.error('Title and due date required'); return; }
    try {
      await axios.post(`${API}/deadlines/create`, { ...newDeadline, case_id: caseId }, { headers });
      toast.success('Deadline created!');
      setShowAddForm(false);
      setNewDeadline({ title: '', deadline_type: 'custom', due_date: '', description: '', step_name: '', auto_remind: true, remind_days_before: 7 });
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to create'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this deadline?')) return;
    try {
      await axios.delete(`${API}/deadlines/${id}`, { headers });
      toast.success('Deleted'); loadData();
    } catch (e) { toast.error('Failed to delete'); }
  };

  const deadlines = data?.deadlines || [];
  const summary = data?.summary || {};
  const filtered = filter === 'all' ? deadlines : deadlines.filter(d => d.urgency?.level === filter);

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (!caseId) return (
    <Card className="p-12 text-center border-0 shadow-sm"><CalendarClock className="h-12 w-12 text-slate-200 mx-auto mb-3" /><p className="text-slate-500">No active case</p></Card>
  );

  const hasAlerts = summary.expired > 0 || summary.critical > 0;

  return (
    <div className="space-y-5" data-testid="deadline-tracker" style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}>
      {/* Summary Header */}
      <Card className={`overflow-hidden border-0 shadow-lg ${hasAlerts ? 'ring-2 ring-red-300' : ''}`} data-testid="deadline-summary">
        <div className={`p-5 ${hasAlerts ? 'bg-gradient-to-r from-red-600 to-red-500' : 'bg-gradient-to-r from-[#2a777a] to-[#1e6365]'} text-white`}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                <CalendarClock className="h-5 w-5" /> Deadline & SLA Tracker
              </h3>
              <p className="text-white/70 text-sm mt-0.5">{caseName || 'Case Deadlines & Document Expiry'}</p>
            </div>
            {hasAlerts && (
              <div className="bg-white/20 backdrop-blur-sm rounded-lg px-3 py-1.5 flex items-center gap-1.5">
                <AlertOctagon className="h-4 w-4" />
                <span className="text-sm font-bold">{summary.expired + summary.critical} Alert{(summary.expired + summary.critical) > 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-5 divide-x bg-white">
          {[
            { label: 'Total', count: summary.total || 0, color: 'text-slate-800' },
            { label: 'Expired', count: summary.expired || 0, color: 'text-red-600', dot: 'bg-red-500' },
            { label: 'Critical', count: summary.critical || 0, color: 'text-red-500', dot: 'bg-red-400' },
            { label: 'Urgent', count: summary.urgent || 0, color: 'text-amber-600', dot: 'bg-amber-500' },
            { label: 'Safe', count: summary.safe || 0, color: 'text-emerald-600', dot: 'bg-emerald-500' },
          ].map(s => (
            <button key={s.label} onClick={() => setFilter(s.label === 'Total' ? 'all' : s.label.toLowerCase())}
                    className={`p-3 text-center hover:bg-slate-50 transition-colors ${filter === (s.label === 'Total' ? 'all' : s.label.toLowerCase()) ? 'bg-slate-50' : ''}`}>
              <div className="flex items-center justify-center gap-1.5">
                {s.dot && <span className={`w-2 h-2 rounded-full ${s.dot}`} />}
                <p className={`text-lg font-bold ${s.color}`}>{s.count}</p>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">{s.label}</p>
            </button>
          ))}
        </div>
      </Card>

      {/* Filter + Add */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1.5">
          {['all', 'expired', 'critical', 'urgent', 'warning', 'safe'].map(f => {
            const cfg = f === 'all' ? { bg: 'bg-slate-100', text: 'text-slate-700' } : URGENCY_CONFIG[f];
            return (
              <button key={f} onClick={() => setFilter(f)}
                      className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors ${filter === f ? (f === 'all' ? 'bg-slate-800 text-white' : cfg.bg + ' ' + cfg.text) : 'text-slate-500 hover:bg-slate-100'}`}>
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            );
          })}
        </div>
        {(role === 'admin' || role === 'case_manager') && (
          <Button size="sm" onClick={() => setShowAddForm(!showAddForm)} className="bg-[#2a777a] hover:bg-[#215f62] rounded-lg h-8 text-xs font-semibold" data-testid="add-deadline-btn">
            <Plus className="h-3.5 w-3.5 mr-1" />Add Deadline
          </Button>
        )}
      </div>

      {/* Add Form */}
      {showAddForm && (
        <Card className="p-5 border-2 border-dashed border-[#2a777a]/30 bg-[#2a777a]/5 rounded-xl" data-testid="add-deadline-form">
          <h4 className="font-bold text-sm text-slate-800 mb-3" style={{ fontFamily: 'Manrope, sans-serif' }}>New Deadline</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div><Label className="text-[10px] font-bold uppercase text-slate-500">Title</Label>
              <Input value={newDeadline.title} onChange={e => setNewDeadline({ ...newDeadline, title: e.target.value })} placeholder="e.g., ITA Expiry" className="mt-1 h-9 text-sm rounded-lg" /></div>
            <div><Label className="text-[10px] font-bold uppercase text-slate-500">Due Date</Label>
              <Input type="date" value={newDeadline.due_date} onChange={e => setNewDeadline({ ...newDeadline, due_date: e.target.value })} className="mt-1 h-9 text-sm rounded-lg" /></div>
            <div><Label className="text-[10px] font-bold uppercase text-slate-500">Type</Label>
              <Select value={newDeadline.deadline_type} onValueChange={v => setNewDeadline({ ...newDeadline, deadline_type: v })}>
                <SelectTrigger className="mt-1 h-9 text-sm rounded-lg"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select></div>
            <div><Label className="text-[10px] font-bold uppercase text-slate-500">Step (Optional)</Label>
              <Input value={newDeadline.step_name} onChange={e => setNewDeadline({ ...newDeadline, step_name: e.target.value })} placeholder="Step name" className="mt-1 h-9 text-sm rounded-lg" /></div>
            <div className="md:col-span-2"><Label className="text-[10px] font-bold uppercase text-slate-500">Description</Label>
              <Textarea value={newDeadline.description} onChange={e => setNewDeadline({ ...newDeadline, description: e.target.value })} placeholder="Details..." rows={2} className="mt-1 text-sm rounded-lg" /></div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={() => setShowAddForm(false)} className="rounded-lg">Cancel</Button>
            <Button size="sm" onClick={handleCreate} className="bg-[#2a777a] hover:bg-[#215f62] rounded-lg font-semibold" data-testid="save-deadline-btn">Create Deadline</Button>
          </div>
        </Card>
      )}

      {/* Deadline Cards */}
      {filtered.length === 0 ? (
        <Card className="p-12 text-center border-0 shadow-sm">
          <CheckCircle className="h-10 w-10 text-emerald-300 mx-auto mb-3" />
          <p className="font-semibold text-slate-600" style={{ fontFamily: 'Manrope, sans-serif' }}>{filter === 'all' ? 'No deadlines tracked yet' : `No ${filter} deadlines`}</p>
          <p className="text-sm text-slate-400 mt-1">Upload documents or add manual deadlines to start tracking</p>
        </Card>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((d, i) => {
            const urg = d.urgency || {};
            const cfg = URGENCY_CONFIG[urg.level] || URGENCY_CONFIG.unknown;
            const typeInfo = TYPE_LABELS[d.deadline_type] || TYPE_LABELS.custom;
            const UrgIcon = cfg.icon;
            const TypeIcon = typeInfo.icon;

            return (
              <Card key={d.id || i} className={`overflow-hidden border ${cfg.light} rounded-xl`} data-testid={`deadline-${i}`}>
                <div className="flex items-start gap-3 p-4">
                  {/* Urgency indicator */}
                  <div className={`w-10 h-10 rounded-xl ${urg.level === 'expired' ? 'bg-red-500' : cfg.bg} flex items-center justify-center flex-shrink-0`}>
                    <UrgIcon className={`h-5 w-5 ${urg.level === 'expired' ? 'text-white' : cfg.text}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-sm text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>{d.title}</h4>
                      <Badge className={`text-[9px] font-semibold ${cfg.bg} ${cfg.text} border-0`}>{urg.label}</Badge>
                      <div className={`flex items-center gap-1 text-[10px] ${typeInfo.color}`}>
                        <TypeIcon className="h-3 w-3" />{typeInfo.label}
                      </div>
                    </div>
                    {d.description && <p className="text-xs text-slate-600 mt-1">{d.description}</p>}
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1"><CalendarClock className="h-3 w-3" />Due: {d.due_date ? new Date(d.due_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'N/A'}</span>
                      {d.step_name && <span className="flex items-center gap-1"><FileText className="h-3 w-3" />{d.step_name}</span>}
                      {d.source && <Badge variant="outline" className="text-[8px]">{d.source === 'estimated' ? 'Est.' : d.source === 'auto_detected' ? 'Auto' : 'Manual'}</Badge>}
                    </div>
                  </div>

                  {/* Actions */}
                  {d.source === 'manual' && (role === 'admin' || role === 'case_manager') && (
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600 flex-shrink-0" onClick={() => handleDelete(d.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

// Overview component for Admin/CM dashboard
export const DeadlineOverviewWidget = ({ token, role = 'admin' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/deadlines/overview`, { headers: { Authorization: `Bearer ${token}` } });
        setData(res.data);
      } catch { /* ignore */ }
      setLoading(false);
    };
    load();
  }, [token]);

  if (loading) return null;
  if (!data || data.summary.total === 0) return null;

  const alerts = data.alerts || [];
  const s = data.summary;

  return (
    <Card className="overflow-hidden border-0 shadow-md" data-testid="deadline-overview-widget">
      <div className={`p-4 ${s.expired > 0 ? 'bg-gradient-to-r from-red-600 to-red-500' : s.critical > 0 ? 'bg-gradient-to-r from-amber-500 to-amber-400' : 'bg-gradient-to-r from-[#2a777a] to-[#1e6365]'} text-white`}>
        <h4 className="font-bold text-sm flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
          <AlertTriangle className="h-4 w-4" /> Deadline Alerts
          {(s.expired + s.critical) > 0 && <Badge className="bg-white/20 text-white border-0 text-[10px]">{s.expired + s.critical} urgent</Badge>}
        </h4>
      </div>
      <div className="divide-y max-h-64 overflow-y-auto">
        {alerts.slice(0, 5).map((a, i) => {
          const cfg = URGENCY_CONFIG[a.urgency?.level] || URGENCY_CONFIG.unknown;
          return (
            <div key={i} className="p-3 flex items-center gap-3 hover:bg-slate-50">
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-800 truncate">{a.title}</p>
                <p className="text-[10px] text-slate-500">{a.case_display} {a.client_name ? `- ${a.client_name}` : ''}</p>
              </div>
              <Badge className={`text-[9px] ${cfg.bg} ${cfg.text} border-0 flex-shrink-0`}>{a.urgency?.label}</Badge>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default DeadlineTracker;
