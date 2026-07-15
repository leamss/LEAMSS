/**
 * My CRM — full lead management page.
 * Kanban board + searchable table + rich Add Lead form + lead detail panel
 * with remarks timeline, stage changes, and quick WhatsApp/Call actions.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import {
  ArrowLeft, Plus, Search, RefreshCw, LayoutGrid, List as ListIcon,
  Phone, Mail, MessageCircle, X, Clock, User, MapPin, GraduationCap,
  Briefcase, ChevronRight, Send, Sparkles, CheckCircle2, LayoutDashboard,
  CalendarClock, TrendingUp, Users,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGES = [
  { key: 'new', label: 'New', color: 'bg-slate-500', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-300' },
  { key: 'contacted', label: 'Contacted', color: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
  { key: 'not_connected', label: 'Not Connected', color: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300' },
  { key: 'prospect', label: 'Prospect', color: 'bg-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-300' },
  { key: 'payment_done', label: 'Payment Done', color: 'bg-teal-500', bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-300' },
  { key: 'converted', label: 'Converted', color: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300' },
  { key: 'not_interested', label: 'Not Interested', color: 'bg-rose-500', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-300' },
];
const STAGE_MAP = Object.fromEntries(STAGES.map(s => [s.key, s]));

const SOURCES = ['Website', 'Google Ads', 'Facebook', 'Instagram', 'Referral', 'Walk-In', 'Direct Call', 'WhatsApp', 'Sample Leads', 'Other'];

const emptyLead = {
  name: '', email: '', phone: '', alternate_phone: '', address: '', city: '',
  service_interested: '', country_of_interest: '', source: 'Website', subsource: '',
  date_of_birth: '', occupation: '', total_work_experience: '', backlogs: '',
  lead_type: '', latest_qualification: '', university: '', course: '', message: '',
};

const timeAgo = (iso) => {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const waLink = (phone) => {
  if (!phone) return null;
  const digits = phone.replace(/[^\d]/g, '');
  return `https://wa.me/${digits}`;
};

const MyCRM = () => {
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('dashboard');
  const [followUps, setFollowUps] = useState([]);
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [showAddLead, setShowAddLead] = useState(false);
  const [newLead, setNewLead] = useState(emptyLead);
  const [saving, setSaving] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [newRemark, setNewRemark] = useState('');
  const [addingRemark, setAddingRemark] = useState(false);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/leads/`, getAuthHeader());
      setLeads(res.data || []);
    } catch (e) {
      console.error('Failed to load leads', e);
    }
    try {
      const fuRes = await axios.get(`${API}/leads/follow-ups/pending`, getAuthHeader());
      setFollowUps(fuRes.data || []);
    } catch (e) {
      console.error('Failed to load follow-ups', e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadLeads(); }, [loadLeads]);

  const filtered = useMemo(() => {
    return leads.filter(l => {
      if (stageFilter !== 'all' && l.stage !== stageFilter) return false;
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const hay = `${l.name || ''} ${l.email || ''} ${l.phone || ''} ${l.lead_number || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [leads, stageFilter, search]);

  const latestRemark = (lead) => {
    const notes = lead.notes || [];
    if (notes.length === 0) return '—';
    return notes[notes.length - 1].text;
  };

  const handleCreateLead = async () => {
    if (!newLead.name.trim() || !newLead.phone.trim()) {
      toast.error('Name and Phone are required');
      return;
    }
    setSaving(true);
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      await axios.post(`${API}/leads/capture`, {
        ...newLead,
        assigned_to: user.id,
        assigned_to_name: user.name,
      });
      toast.success('Lead added successfully');
      setShowAddLead(false);
      setNewLead(emptyLead);
      loadLeads();
    } catch (e) {
      toast.error('Failed to add lead');
    }
    setSaving(false);
  };

  const handleStageChange = async (leadId, newStage) => {
    // optimistic update
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, stage: newStage } : l));
    if (selectedLead?.id === leadId) setSelectedLead(prev => ({ ...prev, stage: newStage }));
    try {
      await axios.put(`${API}/leads/${leadId}`, { stage: newStage }, getAuthHeader());
      toast.success(`Moved to ${STAGE_MAP[newStage]?.label || newStage}`);
    } catch (e) {
      toast.error('Failed to update stage');
      loadLeads();
    }
  };

  const handleAddRemark = async () => {
    if (!newRemark.trim() || !selectedLead) return;
    setAddingRemark(true);
    try {
      await axios.post(`${API}/leads/${selectedLead.id}/note`, { text: newRemark.trim() }, getAuthHeader());
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const optimisticNote = { id: 'temp', text: newRemark.trim(), added_by_name: user.name, created_at: new Date().toISOString() };
      setSelectedLead(prev => ({ ...prev, notes: [...(prev.notes || []), optimisticNote] }));
      setLeads(prev => prev.map(l => l.id === selectedLead.id ? { ...l, notes: [...(l.notes || []), optimisticNote] } : l));
      setNewRemark('');
      toast.success('Remark added');
    } catch (e) {
      toast.error('Failed to add remark');
    }
    setAddingRemark(false);
  };

  const stageCounts = useMemo(() => {
    const counts = {};
    STAGES.forEach(s => { counts[s.key] = leads.filter(l => l.stage === s.key).length; });
    return counts;
  }, [leads]);

  const chartData = useMemo(() => STAGES.map(s => ({ name: s.label, count: stageCounts[s.key] || 0 })), [stageCounts, leads]);

  const todaysLeads = useMemo(() => {
    const todayStr = new Date().toDateString();
    return leads.filter(l => l.created_at && new Date(l.created_at).toDateString() === todayStr)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }, [leads]);

  const recentUpdates = useMemo(() => {
    return [...leads]
      .filter(l => l.updated_at)
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, 6);
  }, [leads]);

  const convertedCount = stageCounts.converted || 0;
  const conversionRate = leads.length > 0 ? Math.round((convertedCount / leads.length) * 100) : 0;

  const sourceBreakdown = useMemo(() => {
    const counts = {};
    leads.forEach(l => {
      const src = l.source || 'Unknown';
      counts[src] = (counts[src] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [leads]);
  const maxSourceCount = sourceBreakdown.length > 0 ? sourceBreakdown[0][1] : 1;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 sm:px-8 py-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/portal/welcome')} className="p-2 rounded-lg hover:bg-slate-100 transition" data-testid="back-to-portal">
            <ArrowLeft className="h-5 w-5 text-slate-700" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[#2a777a]" /> My CRM
            </h1>
            <p className="text-xs text-slate-500">{leads.length} total leads</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-100 rounded-lg p-1">
            <button onClick={() => setView('dashboard')} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'dashboard' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`} data-testid="view-dashboard-btn">
              <LayoutDashboard className="h-3.5 w-3.5" /> Dashboard
            </button>
            <button onClick={() => setView('kanban')} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'kanban' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`} data-testid="view-kanban-btn">
              <LayoutGrid className="h-3.5 w-3.5" /> Board
            </button>
            <button onClick={() => setView('table')} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'table' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`} data-testid="view-table-btn">
              <ListIcon className="h-3.5 w-3.5" /> Table
            </button>
          </div>
          <Button variant="ghost" size="sm" onClick={loadLeads}><RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh</Button>
          <Button className="bg-[#2a777a] hover:bg-[#236466]" size="sm" onClick={() => setShowAddLead(true)} data-testid="add-lead-btn">
            <Plus className="h-4 w-4 mr-1" /> Add Lead
          </Button>
        </div>
      </div>

      <div className="p-4 sm:p-8 space-y-4">
        {view === 'dashboard' ? (
          /* DASHBOARD VIEW */
          <div className="space-y-4">
            {/* Stat cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Card className="p-4 bg-gradient-to-br from-slate-600 to-slate-700 text-white border-0">
                <p className="text-xs text-white/70 uppercase tracking-wide">Total Leads</p>
                <p className="text-2xl font-bold mt-1">{leads.length}</p>
              </Card>
              <Card className="p-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white border-0">
                <p className="text-xs text-white/70 uppercase tracking-wide">Today's Leads</p>
                <p className="text-2xl font-bold mt-1">{todaysLeads.length}</p>
              </Card>
              <Card className="p-4 bg-gradient-to-br from-amber-500 to-amber-600 text-white border-0">
                <p className="text-xs text-white/70 uppercase tracking-wide">Pending Follow-ups</p>
                <p className="text-2xl font-bold mt-1">{followUps.length}</p>
              </Card>
              <Card className="p-4 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white border-0">
                <p className="text-xs text-white/70 uppercase tracking-wide">Conversion Rate</p>
                <p className="text-2xl font-bold mt-1">{conversionRate}%</p>
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Left column: Today's Leads + Recent Updates */}
              <div className="lg:col-span-1 space-y-4">
                <Card className="p-4">
                  <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><Sparkles className="h-4 w-4 text-blue-500" /> Today's Leads</p>
                  {todaysLeads.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No leads added today yet</p>
                  ) : (
                    <div className="space-y-2">
                      {todaysLeads.map(l => (
                        <button key={l.id} onClick={() => setSelectedLead(l)} className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-slate-50 text-left transition-colors" data-testid={`today-lead-${l.id}`}>
                          <div className="w-7 h-7 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                            {(l.name || '?')[0]?.toUpperCase()}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-slate-800 truncate">{l.name}</p>
                            <p className="text-xs text-slate-400">{timeAgo(l.created_at)}</p>
                          </div>
                          <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
                        </button>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="p-4">
                  <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><Clock className="h-4 w-4 text-purple-500" /> Last Updated</p>
                  {recentUpdates.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No updates yet</p>
                  ) : (
                    <div className="space-y-2">
                      {recentUpdates.map(l => {
                        const stage = STAGE_MAP[l.stage] || STAGES[0];
                        return (
                          <button key={l.id} onClick={() => setSelectedLead(l)} className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-slate-50 text-left transition-colors" data-testid={`recent-update-${l.id}`}>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-slate-800 truncate">{l.name}</p>
                              <p className="text-xs text-slate-400">{timeAgo(l.updated_at)}</p>
                            </div>
                            <Badge className={`${stage.bg} ${stage.text} border-0 text-[10px]`}>{stage.label}</Badge>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </Card>
              </div>

              {/* Middle: chart */}
              <div className="lg:col-span-1">
                <Card className="p-4 h-full">
                  <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><TrendingUp className="h-4 w-4 text-teal-500" /> Leads by Stage</p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 30 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                        <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#2a777a" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>

              {/* Right: follow-ups + sources */}
              <div className="lg:col-span-1 space-y-4">
                <Card className="p-4">
                  <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><CalendarClock className="h-4 w-4 text-amber-500" /> Pending Follow-ups</p>
                  {followUps.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No pending follow-ups</p>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {followUps.map(fu => (
                        <div key={fu.id} className="p-2.5 rounded-lg bg-amber-50 border border-amber-100">
                          <p className="text-sm font-medium text-slate-800">{fu.lead_name}</p>
                          <p className="text-xs text-slate-500 capitalize">{fu.type} · {fu.message || 'No note'}</p>
                          <p className="text-[10px] text-slate-400 mt-1">{fu.scheduled_at ? new Date(fu.scheduled_at).toLocaleString() : ''}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="p-4">
                  <p className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2"><Users className="h-4 w-4 text-indigo-500" /> Lead Sources</p>
                  {sourceBreakdown.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No source data yet</p>
                  ) : (
                    <div className="space-y-2.5">
                      {sourceBreakdown.map(([src, count]) => (
                        <div key={src}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-slate-600 font-medium">{src}</span>
                            <span className="text-slate-400">{count}</span>
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-[#2a777a] rounded-full" style={{ width: `${(count / maxSourceCount) * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          </div>
        ) : (
        <>
        {/* Stage filter pills */}
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setStageFilter('all')} className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${stageFilter === 'all' ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-600 border-slate-200'}`}>
            All ({leads.length})
          </button>
          {STAGES.map(s => (
            <button
              key={s.key}
              onClick={() => setStageFilter(stageFilter === s.key ? 'all' : s.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${stageFilter === s.key ? `${s.color} text-white border-transparent` : `bg-white ${s.text} ${s.border}`}`}
              data-testid={`stage-filter-${s.key}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${stageFilter === s.key ? 'bg-white' : s.color}`} />
              {s.label} ({stageCounts[s.key] || 0})
            </button>
          ))}
          <div className="relative ml-auto w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name, phone, email..." className="pl-8 h-8 text-xs" data-testid="crm-search" />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-40"><RefreshCw className="h-6 w-6 text-[#2a777a] animate-spin" /></div>
        ) : filtered.length === 0 ? (
          <Card className="p-12 text-center text-slate-500">
            <User className="h-10 w-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm font-medium">No leads found</p>
            <p className="text-xs mt-1">Click "Add Lead" to create your first one.</p>
          </Card>
        ) : view === 'kanban' ? (
          /* KANBAN VIEW */
          <div className="flex items-start gap-3 overflow-x-auto pb-4">
            {STAGES.map(stage => {
              const items = filtered.filter(l => l.stage === stage.key);
              return (
                <div key={stage.key} className="flex-shrink-0 w-72">
                  <div className={`${stage.bg} rounded-t-xl p-3 border ${stage.border} border-b-0 flex items-center justify-between`}>
                    <span className={`font-semibold text-sm ${stage.text}`}>{stage.label}</span>
                    <Badge variant="outline" className="text-xs h-5">{items.length}</Badge>
                  </div>
                  <div className={`border ${stage.border} border-t-0 rounded-b-xl bg-slate-50/50 p-2 space-y-2 min-h-[200px] max-h-[560px] overflow-y-auto`}>
                    {items.length === 0 ? (
                      <p className="text-center text-xs text-slate-300 py-8">No leads</p>
                    ) : items.map(lead => (
                      <div
                        key={lead.id}
                        onClick={() => setSelectedLead(lead)}
                        className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                        data-testid={`lead-card-${lead.id}`}
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <div className="w-7 h-7 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                            {(lead.name || '?')[0]?.toUpperCase()}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-semibold text-sm text-slate-800 truncate">{lead.name || 'Unnamed'}</p>
                            <p className="text-[10px] text-slate-400 flex items-center gap-1"><Clock className="h-2.5 w-2.5" /> {timeAgo(lead.updated_at || lead.created_at)}</p>
                          </div>
                          {waLink(lead.phone) && (
                            <a href={waLink(lead.phone)} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="p-1.5 bg-green-500 rounded-full hover:bg-green-600 transition-colors flex-shrink-0">
                              <MessageCircle className="h-3 w-3 text-white" />
                            </a>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 truncate flex items-center gap-1"><Phone className="h-3 w-3" /> {lead.phone || '—'}</p>
                        {lead.email && <p className="text-xs text-slate-400 truncate flex items-center gap-1 mt-0.5"><Mail className="h-3 w-3" /> {lead.email}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* TABLE VIEW */
          <div className="border border-slate-200 rounded-xl bg-white overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  <th className="text-left px-4 py-2.5">Lead #</th>
                  <th className="text-left px-4 py-2.5">Name</th>
                  <th className="text-left px-4 py-2.5">Contact</th>
                  <th className="text-left px-4 py-2.5">Source</th>
                  <th className="text-left px-4 py-2.5">Status</th>
                  <th className="text-left px-4 py-2.5">Latest Remark</th>
                  <th className="text-left px-4 py-2.5">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map(lead => {
                  const stage = STAGE_MAP[lead.stage] || STAGES[0];
                  return (
                    <tr key={lead.id} onClick={() => setSelectedLead(lead)} className="hover:bg-slate-50 cursor-pointer" data-testid={`lead-row-${lead.id}`}>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{lead.lead_number}</td>
                      <td className="px-4 py-3 font-medium text-slate-800">{lead.name}</td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        <p>{lead.phone}</p>
                        <p className="text-slate-400">{lead.email}</p>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{lead.source}</td>
                      <td className="px-4 py-3"><Badge className={`${stage.bg} ${stage.text} border-0 text-xs`}>{stage.label}</Badge></td>
                      <td className="px-4 py-3 text-xs text-slate-500 max-w-[220px] truncate">{latestRemark(lead)}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{timeAgo(lead.updated_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        </>
        )}
      </div>

      {/* ADD LEAD MODAL */}
      <Dialog open={showAddLead} onOpenChange={setShowAddLead}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Add Lead</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-700 mb-2">Contact Details</p>
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Name *" value={newLead.name} onChange={e => setNewLead({ ...newLead, name: e.target.value })} data-testid="lead-name-input" />
                <Input placeholder="Phone *" value={newLead.phone} onChange={e => setNewLead({ ...newLead, phone: e.target.value })} data-testid="lead-phone-input" />
                <Input placeholder="Email" value={newLead.email} onChange={e => setNewLead({ ...newLead, email: e.target.value })} />
                <Input placeholder="Alternate Phone" value={newLead.alternate_phone} onChange={e => setNewLead({ ...newLead, alternate_phone: e.target.value })} />
                <Input placeholder="Address" className="col-span-2" value={newLead.address} onChange={e => setNewLead({ ...newLead, address: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Select value={newLead.source} onValueChange={v => setNewLead({ ...newLead, source: v })}>
                <SelectTrigger data-testid="lead-source-select"><SelectValue placeholder="Lead Source" /></SelectTrigger>
                <SelectContent>{SOURCES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
              <Input placeholder="Lead Subsource" value={newLead.subsource} onChange={e => setNewLead({ ...newLead, subsource: e.target.value })} />
              <Input placeholder="Country of Interest" value={newLead.country_of_interest} onChange={e => setNewLead({ ...newLead, country_of_interest: e.target.value })} />
              <Input placeholder="Service Interested" value={newLead.service_interested} onChange={e => setNewLead({ ...newLead, service_interested: e.target.value })} />
              <Input placeholder="City" value={newLead.city} onChange={e => setNewLead({ ...newLead, city: e.target.value })} />
              <Input type="date" placeholder="Date of Birth" value={newLead.date_of_birth} onChange={e => setNewLead({ ...newLead, date_of_birth: e.target.value })} />
              <Input placeholder="Occupation" value={newLead.occupation} onChange={e => setNewLead({ ...newLead, occupation: e.target.value })} />
              <Input placeholder="Total Work Experience" value={newLead.total_work_experience} onChange={e => setNewLead({ ...newLead, total_work_experience: e.target.value })} />
              <Input placeholder="Backlogs" value={newLead.backlogs} onChange={e => setNewLead({ ...newLead, backlogs: e.target.value })} />
              <Input placeholder="Lead Type" value={newLead.lead_type} onChange={e => setNewLead({ ...newLead, lead_type: e.target.value })} />
              <Input placeholder="Latest Qualification" value={newLead.latest_qualification} onChange={e => setNewLead({ ...newLead, latest_qualification: e.target.value })} />
              <Input placeholder="University" value={newLead.university} onChange={e => setNewLead({ ...newLead, university: e.target.value })} />
              <Input placeholder="Course" value={newLead.course} onChange={e => setNewLead({ ...newLead, course: e.target.value })} />
            </div>
            <Textarea placeholder="Note / message" value={newLead.message} onChange={e => setNewLead({ ...newLead, message: e.target.value })} />
            <Button className="w-full bg-[#2a777a] hover:bg-[#236466]" disabled={saving} onClick={handleCreateLead} data-testid="save-lead-btn">
              {saving ? 'Saving...' : 'Save Lead'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* LEAD DETAIL DRAWER */}
      {selectedLead && (
        <>
          <div className="fixed inset-0 bg-black/40 z-[100]" onClick={() => setSelectedLead(null)} />
          <div className="fixed top-0 right-0 h-full w-full sm:w-[440px] bg-white z-[101] shadow-2xl flex flex-col" data-testid="lead-detail-panel">
            <div className="px-5 py-4 border-b flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white font-bold">
                  {(selectedLead.name || '?')[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-slate-800">{selectedLead.name}</p>
                  <p className="text-xs text-slate-400 font-mono">{selectedLead.lead_number}</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setSelectedLead(null)}><X className="h-4 w-4" /></Button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Quick actions */}
              <div className="flex gap-2">
                {selectedLead.phone && (
                  <a href={`tel:${selectedLead.phone}`} className="flex-1"><Button variant="outline" size="sm" className="w-full"><Phone className="h-3.5 w-3.5 mr-1.5" /> Call</Button></a>
                )}
                {waLink(selectedLead.phone) && (
                  <a href={waLink(selectedLead.phone)} target="_blank" rel="noreferrer" className="flex-1"><Button variant="outline" size="sm" className="w-full text-green-600 border-green-300 hover:bg-green-50"><MessageCircle className="h-3.5 w-3.5 mr-1.5" /> WhatsApp</Button></a>
                )}
                {selectedLead.email && (
                  <a href={`mailto:${selectedLead.email}`} className="flex-1"><Button variant="outline" size="sm" className="w-full"><Mail className="h-3.5 w-3.5 mr-1.5" /> Email</Button></a>
                )}
              </div>

              {/* Stage selector */}
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-2 uppercase">Stage</p>
                <div className="flex flex-wrap gap-1.5">
                  {STAGES.map(s => (
                    <button
                      key={s.key}
                      onClick={() => handleStageChange(selectedLead.id, s.key)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${selectedLead.stage === s.key ? `${s.color} text-white border-transparent` : `bg-white ${s.text} ${s.border}`}`}
                      data-testid={`detail-stage-${s.key}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Info grid */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex items-start gap-2"><Phone className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700">{selectedLead.phone || '—'}</span></div>
                <div className="flex items-start gap-2"><Mail className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700 truncate">{selectedLead.email || '—'}</span></div>
                <div className="flex items-start gap-2"><MapPin className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700">{selectedLead.city || '—'}</span></div>
                <div className="flex items-start gap-2"><Briefcase className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700">{selectedLead.occupation || '—'}</span></div>
                <div className="flex items-start gap-2"><GraduationCap className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700">{selectedLead.latest_qualification || '—'}</span></div>
                <div className="flex items-start gap-2"><Sparkles className="h-3.5 w-3.5 text-slate-400 mt-0.5" /><span className="text-slate-700">{selectedLead.source || '—'}</span></div>
              </div>

              {/* Remarks timeline */}
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-2 uppercase">Remarks</p>
                <div className="space-y-2 mb-3 max-h-48 overflow-y-auto">
                  {(selectedLead.notes || []).length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No remarks yet</p>
                  ) : (
                    [...(selectedLead.notes || [])].reverse().map((n, i) => (
                      <div key={n.id || i} className="bg-slate-50 rounded-lg p-2.5 text-xs">
                        <p className="text-slate-700">{n.text}</p>
                        <p className="text-slate-400 mt-1">{n.added_by_name} · {timeAgo(n.created_at)}</p>
                      </div>
                    ))
                  )}
                </div>
                <div className="flex gap-2">
                  <Input value={newRemark} onChange={e => setNewRemark(e.target.value)} placeholder="Add a remark..." className="text-sm" onKeyDown={e => e.key === 'Enter' && handleAddRemark()} data-testid="new-remark-input" />
                  <Button size="icon" disabled={addingRemark || !newRemark.trim()} onClick={handleAddRemark} data-testid="add-remark-btn"><Send className="h-4 w-4" /></Button>
                </div>
              </div>

              {selectedLead.converted && (
                <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-700 text-sm">
                  <CheckCircle2 className="h-4 w-4" /> This lead has been converted to a sale
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default MyCRM;