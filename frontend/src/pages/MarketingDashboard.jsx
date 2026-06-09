import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  ArrowLeft, Plus, Users, Target, Mail, Star, Trophy, BarChart3, Send,
  Trash2, Edit, Phone, Globe, TrendingUp, Filter, Search, MessageSquare,
  Calendar, CheckCircle, XCircle, Eye, ChevronRight, FileText, Download, UserPlus
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';
const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const MarketingDashboard = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  
  // Leads CRM
  const [leads, setLeads] = useState([]);
  const [pipelineStats, setPipelineStats] = useState({ stages: {}, total: 0, conversion_rate: 0, sources: {} });
  const [leadDialog, setLeadDialog] = useState({ open: false, data: null, mode: 'create' });
  const [selectedLead, setSelectedLead] = useState(null);
  const [leadStageFilter, setLeadStageFilter] = useState('all');
  const [followUpDialog, setFollowUpDialog] = useState({ open: false, leadId: null });
  const [pendingFollowUps, setPendingFollowUps] = useState([]);
  
  // Campaigns
  const [campaigns, setCampaigns] = useState([]);
  const [campaignDialog, setCampaignDialog] = useState({ open: false, data: null, mode: 'create' });
  const [campaignStats, setCampaignStats] = useState({ total_campaigns: 0, sent_campaigns: 0, total_recipients: 0 });
  
  // Testimonials
  const [testimonials, setTestimonials] = useState([]);
  const [testimonialDialog, setTestimonialDialog] = useState({ open: false, data: null });
  
  // Leaderboard
  const [leaderboard, setLeaderboard] = useState([]);
  
  // Promos
  const [promos, setPromos] = useState([]);
  const [promoDialog, setPromoDialog] = useState({ open: false, data: {} });

  // Scorecards (eligibility leads)
  const [scorecardLeads, setScorecardLeads] = useState([]);
  const [assignableUsers, setAssignableUsers] = useState([]);
  const [assignDialog, setAssignDialog] = useState({ open: false, lead: null, userId: '' });

  const loadScorecards = useCallback(async () => {
    try {
      const [scRes, usersRes] = await Promise.allSettled([
        axios.get(`${API}/eligibility/admin/scorecard-leads`, getAuthHeader()),
        axios.get(`${API}/users`, getAuthHeader()),
      ]);
      if (scRes.status === 'fulfilled') setScorecardLeads(scRes.value.data || []);
      if (usersRes.status === 'fulfilled') {
        const roles = ['partner', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'case_manager'];
        setAssignableUsers((usersRes.value.data || []).filter(u => roles.includes(u.role)));
      }
    } catch (e) { console.error(e); }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [leadsRes, statsRes, followUpsRes, campaignsRes, campStatsRes, testimonialsRes, leaderboardRes, promosRes] = await Promise.allSettled([
        axios.get(`${API}/leads/`, getAuthHeader()),
        axios.get(`${API}/leads/pipeline-stats`, getAuthHeader()),
        axios.get(`${API}/leads/follow-ups/pending`, getAuthHeader()),
        axios.get(`${API}/campaigns/`, getAuthHeader()),
        axios.get(`${API}/campaigns/stats/overview`, getAuthHeader()),
        axios.get(`${API}/marketing-tools/testimonials?status=all`, getAuthHeader()),
        axios.get(`${API}/marketing-tools/leaderboard`, getAuthHeader()),
        axios.get(`${API}/marketing/promos`, getAuthHeader())
      ]);
      if (leadsRes.status === 'fulfilled') setLeads(leadsRes.value.data);
      if (statsRes.status === 'fulfilled') setPipelineStats(statsRes.value.data);
      if (followUpsRes.status === 'fulfilled') setPendingFollowUps(followUpsRes.value.data);
      if (campaignsRes.status === 'fulfilled') setCampaigns(campaignsRes.value.data);
      if (campStatsRes.status === 'fulfilled') setCampaignStats(campStatsRes.value.data);
      if (testimonialsRes.status === 'fulfilled') setTestimonials(testimonialsRes.value.data);
      if (leaderboardRes.status === 'fulfilled') setLeaderboard(leaderboardRes.value.data);
      if (promosRes.status === 'fulfilled') setPromos(promosRes.value.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadScorecards(); }, [loadScorecards]);

  const openPdf = (scoreId) => {
    if (!scoreId) { toast.error('No scorecard PDF for this lead'); return; }
    window.open(`${API}/eligibility/report/${scoreId}`, '_blank', 'noopener,noreferrer');
  };

  const handleAssign = async () => {
    const { lead, userId } = assignDialog;
    if (!userId) { toast.error('Select a person'); return; }
    const u = assignableUsers.find(x => x.id === userId);
    try {
      await axios.put(`${API}/eligibility/admin/scorecard-leads/${lead.id}/assign`,
        { assigned_to: userId, assigned_to_name: u?.name }, getAuthHeader());
      toast.success(`Assigned to ${u?.name || 'team member'}`);
      setAssignDialog({ open: false, lead: null, userId: '' });
      loadScorecards();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Assign failed');
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'leads', label: 'Lead CRM', icon: Target },
    { id: 'scorecards', label: 'Scorecards', icon: FileText },
    { id: 'campaigns', label: 'Campaigns', icon: Mail },
    { id: 'testimonials', label: 'Testimonials', icon: Star },
    { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { id: 'promos', label: 'Promo Codes', icon: Gift },
  ];

  // ===== HANDLERS =====
  const handleSaveLead = async () => {
    try {
      if (leadDialog.mode === 'create') {
        await axios.post(`${API}/leads/capture`, leadDialog.data);
      } else {
        await axios.put(`${API}/leads/${leadDialog.data.id}`, leadDialog.data, getAuthHeader());
      }
      toast.success(leadDialog.mode === 'create' ? 'Lead captured!' : 'Lead updated!');
      setLeadDialog({ open: false, data: null, mode: 'create' });
      loadData();
    } catch (e) { toast.error('Failed to save lead'); }
  };

  const handleMoveLead = async (leadId, newStage) => {
    try {
      await axios.put(`${API}/leads/${leadId}`, { stage: newStage }, getAuthHeader());
      toast.success(`Lead moved to ${newStage}`);
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleAddNote = async (leadId, text) => {
    try {
      await axios.post(`${API}/leads/${leadId}/note`, { text }, getAuthHeader());
      toast.success('Note added');
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleScheduleFollowUp = async () => {
    try {
      await axios.post(`${API}/leads/${followUpDialog.leadId}/follow-up`, followUpDialog.data || {}, getAuthHeader());
      toast.success('Follow-up scheduled!');
      setFollowUpDialog({ open: false, leadId: null });
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleCompleteFollowUp = async (fuId) => {
    try {
      await axios.put(`${API}/leads/follow-ups/${fuId}/complete`, { outcome: 'completed' }, getAuthHeader());
      toast.success('Follow-up completed!');
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleSaveCampaign = async () => {
    try {
      if (campaignDialog.mode === 'create') {
        await axios.post(`${API}/campaigns/`, campaignDialog.data, getAuthHeader());
      } else {
        await axios.put(`${API}/campaigns/${campaignDialog.data.id}`, campaignDialog.data, getAuthHeader());
      }
      toast.success('Campaign saved!');
      setCampaignDialog({ open: false, data: null, mode: 'create' });
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleSendCampaign = async (id) => {
    try {
      const res = await axios.post(`${API}/campaigns/${id}/send`, {}, getAuthHeader());
      toast.success(res.data.message);
      loadData();
    } catch (e) { toast.error('Failed to send'); }
  };

  const handleSaveTestimonial = async () => {
    try {
      if (testimonialDialog.data?.id) {
        await axios.put(`${API}/marketing-tools/testimonials/${testimonialDialog.data.id}`, testimonialDialog.data, getAuthHeader());
      } else {
        await axios.post(`${API}/marketing-tools/testimonials`, testimonialDialog.data, getAuthHeader());
      }
      toast.success('Testimonial saved!');
      setTestimonialDialog({ open: false, data: null });
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const handleSavePromo = async () => {
    try {
      await axios.post(`${API}/marketing/promo`, promoDialog.data, getAuthHeader());
      toast.success('Promo code created!');
      setPromoDialog({ open: false, data: {} });
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  const stageColors = {
    new: 'bg-blue-100 text-blue-700 border-blue-200',
    contacted: 'bg-indigo-100 text-indigo-700 border-indigo-200',
    qualified: 'bg-purple-100 text-purple-700 border-purple-200',
    proposal: 'bg-amber-100 text-amber-700 border-amber-200',
    negotiation: 'bg-orange-100 text-orange-700 border-orange-200',
    won: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    lost: 'bg-red-100 text-red-700 border-red-200',
  };

  const tierColors = { gold: 'text-amber-500', silver: 'text-slate-400', bronze: 'text-orange-600' };

  return (
    <div className="min-h-screen bg-[#F5F7FA]" data-testid="marketing-dashboard">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn">
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-slate-800">Marketing Hub</h1>
                <p className="text-sm text-slate-500">Leads, Campaigns, Testimonials & Performance</p>
              </div>
            </div>
          </div>
          {/* Tabs */}
          <div className="flex gap-1 mt-4 overflow-x-auto pb-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id ? 'bg-[#2a777a] text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">

        {/* ===== OVERVIEW TAB ===== */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('leads')} data-testid="stat-leads">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg"><Target className="h-5 w-5 text-blue-600" /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{pipelineStats.total}</p>
                    <p className="text-xs text-slate-500">Total Leads</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('campaigns')} data-testid="stat-campaigns">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-50 rounded-lg"><Mail className="h-5 w-5 text-purple-600" /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{campaignStats.sent_campaigns}</p>
                    <p className="text-xs text-slate-500">Campaigns Sent</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4" data-testid="stat-conversion">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-50 rounded-lg"><TrendingUp className="h-5 w-5 text-emerald-600" /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{pipelineStats.conversion_rate}%</p>
                    <p className="text-xs text-slate-500">Conversion Rate</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('testimonials')} data-testid="stat-testimonials">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg"><Star className="h-5 w-5 text-amber-600" /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{testimonials.length}</p>
                    <p className="text-xs text-slate-500">Testimonials</p>
                  </div>
                </div>
              </Card>
            </div>

            {/* Pipeline Overview */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Lead Pipeline</h3>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {Object.entries(pipelineStats.stages || {}).map(([stage, count]) => (
                  <div key={stage} className={`flex-1 min-w-[100px] p-3 rounded-xl text-center border ${stageColors[stage] || 'bg-slate-50'}`}>
                    <p className="text-2xl font-bold">{count}</p>
                    <p className="text-xs font-medium capitalize">{stage}</p>
                  </div>
                ))}
              </div>
            </Card>

            {/* Follow-ups & Sources */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Pending Follow-ups</h3>
                {pendingFollowUps.length === 0 ? (
                  <p className="text-slate-500 text-sm">No pending follow-ups</p>
                ) : (
                  <div className="space-y-3">
                    {pendingFollowUps.slice(0, 5).map(fu => (
                      <div key={fu.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                        <div>
                          <p className="font-medium text-slate-800 text-sm">{fu.lead_name}</p>
                          <p className="text-xs text-slate-500">{fu.type} &middot; {fu.message}</p>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => handleCompleteFollowUp(fu.id)}>
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Lead Sources</h3>
                {Object.entries(pipelineStats.sources || {}).length === 0 ? (
                  <p className="text-slate-500 text-sm">No data yet</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(pipelineStats.sources || {}).map(([source, count]) => (
                      <div key={source} className="flex items-center justify-between">
                        <span className="text-sm text-slate-700 capitalize">{source.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-100 rounded-full h-2"><div className="h-2 bg-[#2a777a] rounded-full" style={{ width: `${(count / pipelineStats.total * 100)}%` }} /></div>
                          <span className="text-sm font-semibold text-slate-800">{count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        {/* ===== LEAD CRM TAB ===== */}
        {activeTab === 'leads' && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Select value={leadStageFilter} onValueChange={setLeadStageFilter}>
                  <SelectTrigger className="w-[140px]" data-testid="lead-stage-filter"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Stages</SelectItem>
                    <SelectItem value="new">New</SelectItem>
                    <SelectItem value="contacted">Contacted</SelectItem>
                    <SelectItem value="qualified">Qualified</SelectItem>
                    <SelectItem value="proposal">Proposal</SelectItem>
                    <SelectItem value="negotiation">Negotiation</SelectItem>
                    <SelectItem value="won">Won</SelectItem>
                    <SelectItem value="lost">Lost</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => setLeadDialog({ open: true, data: { source: 'manual' }, mode: 'create' })} data-testid="add-lead-btn">
                <Plus className="h-4 w-4 mr-2" />Add Lead
              </Button>
            </div>

            {/* Leads Table */}
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-slate-50 border-b">
                    <th className="text-left p-4">Name</th>
                    <th className="text-left p-4">Contact</th>
                    <th className="text-left p-4">Service</th>
                    <th className="text-left p-4">Source</th>
                    <th className="text-center p-4">Stage</th>
                    <th className="text-center p-4">Actions</th>
                  </tr></thead>
                  <tbody>
                    {leads.filter(l => leadStageFilter === 'all' || l.stage === leadStageFilter).map(lead => (
                      <tr key={lead.id} className="border-b hover:bg-slate-50/50 cursor-pointer" onClick={() => setSelectedLead(lead)} data-testid={`lead-row-${lead.id}`}>
                        <td className="p-4">
                          <p className="font-medium text-slate-800">{lead.name}</p>
                          <p className="text-xs text-slate-500">{new Date(lead.created_at).toLocaleDateString()}</p>
                        </td>
                        <td className="p-4">
                          <p className="text-slate-700">{lead.email}</p>
                          <p className="text-xs text-slate-500">{lead.phone}</p>
                        </td>
                        <td className="p-4 text-slate-600">{lead.service_interested}</td>
                        <td className="p-4"><Badge variant="outline" className="text-xs capitalize">{lead.source?.replace(/_/g, ' ')}</Badge></td>
                        <td className="p-4 text-center">
                          <Badge className={`capitalize ${stageColors[lead.stage] || ''}`}>{lead.stage}</Badge>
                        </td>
                        <td className="p-4 text-center" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-center gap-1">
                            <Button size="sm" variant="ghost" onClick={() => setLeadDialog({ open: true, data: lead, mode: 'edit' })}><Edit className="h-4 w-4" /></Button>
                            <Button size="sm" variant="ghost" onClick={() => setFollowUpDialog({ open: true, leadId: lead.id, data: { type: 'call', message: '' } })}><Phone className="h-4 w-4" /></Button>
                            {lead.stage !== 'won' && lead.stage !== 'lost' && (
                              <Select onValueChange={(v) => handleMoveLead(lead.id, v)}>
                                <SelectTrigger className="w-[90px] h-8 text-xs"><SelectValue placeholder="Move" /></SelectTrigger>
                                <SelectContent>
                                  {['contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost'].filter(s => s !== lead.stage).map(s => (
                                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {leads.filter(l => leadStageFilter === 'all' || l.stage === leadStageFilter).length === 0 && (
                <div className="p-8 text-center text-slate-500">No leads found. Start capturing leads!</div>
              )}
            </Card>

            {/* Lead Detail Panel */}
            {selectedLead && (
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">{selectedLead.name}</h3>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedLead(null)}><XCircle className="h-5 w-5" /></Button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div><Label className="text-xs text-slate-500">Email</Label><p className="text-sm font-medium">{selectedLead.email}</p></div>
                  <div><Label className="text-xs text-slate-500">Phone</Label><p className="text-sm font-medium">{selectedLead.phone}</p></div>
                  <div><Label className="text-xs text-slate-500">Service</Label><p className="text-sm font-medium">{selectedLead.service_interested}</p></div>
                  <div><Label className="text-xs text-slate-500">Source</Label><p className="text-sm font-medium capitalize">{selectedLead.source?.replace(/_/g, ' ')}</p></div>
                </div>
                {/* Notes */}
                <div>
                  <Label className="text-sm font-medium mb-2">Notes</Label>
                  <div className="space-y-2 max-h-40 overflow-y-auto mb-2">
                    {(selectedLead.notes || []).map((note, idx) => (
                      <div key={idx} className="bg-slate-50 p-2 rounded text-sm">
                        <span className="font-medium text-[#2a777a]">{note.added_by_name}</span>: {note.text}
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input id="note-input" placeholder="Add a note..." className="flex-1" onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.target.value) { handleAddNote(selectedLead.id, e.target.value); e.target.value = ''; }
                    }} />
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* ===== SCORECARDS TAB ===== */}
        {activeTab === 'scorecards' && (
          <div className="space-y-4" data-testid="scorecards-tab">
            <Card className="p-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2"><FileText className="h-4 w-4 text-[#2a777a]" /> Eligibility Scorecard Leads</h3>
                  <p className="text-sm text-slate-500">Visitors who downloaded their pathway-fit PDF. View the report and assign to a partner / sales person.</p>
                </div>
                <Badge className="bg-[#2a777a] text-white">{scorecardLeads.length} leads</Badge>
              </div>
            </Card>

            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                    <tr>
                      <th className="text-left px-4 py-3">Client</th>
                      <th className="text-left px-4 py-3">Contact</th>
                      <th className="text-left px-4 py-3">Best Fit</th>
                      <th className="text-center px-4 py-3">Score</th>
                      <th className="text-left px-4 py-3">Assigned To</th>
                      <th className="text-right px-4 py-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {scorecardLeads.length === 0 && (
                      <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">No scorecard leads yet.</td></tr>
                    )}
                    {scorecardLeads.map(ld => (
                      <tr key={ld.id} className="hover:bg-slate-50" data-testid={`scorecard-row-${ld.id}`}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800">{ld.name || '—'}</p>
                          <p className="text-xs text-slate-400">{ld.created_at ? new Date(ld.created_at).toLocaleDateString() : ''} · {ld.source === 'eligibility_quiz' ? 'Quiz' : 'Pre-score'}</p>
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          <p className="text-xs flex items-center gap-1"><Mail className="h-3 w-3 text-slate-400" /> {ld.email || '—'}</p>
                          <p className="text-xs flex items-center gap-1"><Phone className="h-3 w-3 text-slate-400" /> {ld.phone || '—'}</p>
                        </td>
                        <td className="px-4 py-3 text-slate-700">{ld.top_pathway_name || '—'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="font-bold text-[#2a777a]">{ld.top_score ?? '—'}</span><span className="text-xs text-slate-400">/100</span>
                        </td>
                        <td className="px-4 py-3">
                          {ld.assigned_to_name
                            ? <Badge className="bg-emerald-100 text-emerald-700">{ld.assigned_to_name}</Badge>
                            : <span className="text-xs text-slate-400">Unassigned</span>}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <Button size="sm" variant="outline" onClick={() => openPdf(ld.score_id)} data-testid={`view-pdf-${ld.id}`}>
                              <Download className="h-3.5 w-3.5 mr-1" /> PDF
                            </Button>
                            <Button size="sm" className="bg-[#2a777a] hover:bg-[#1f5c5e] text-white" onClick={() => setAssignDialog({ open: true, lead: ld, userId: ld.assigned_to || '' })} data-testid={`assign-btn-${ld.id}`}>
                              <UserPlus className="h-3.5 w-3.5 mr-1" /> {ld.assigned_to_name ? 'Reassign' : 'Assign'}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}


        {/* ===== CAMPAIGNS TAB ===== */}
        {activeTab === 'campaigns' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Email Campaigns</h3>
              <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => setCampaignDialog({ open: true, data: { target_audience: 'all' }, mode: 'create' })} data-testid="create-campaign-btn">
                <Plus className="h-4 w-4 mr-2" />New Campaign
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 text-center"><p className="text-2xl font-bold">{campaignStats.total_campaigns}</p><p className="text-xs text-slate-500">Total Campaigns</p></Card>
              <Card className="p-4 text-center"><p className="text-2xl font-bold">{campaignStats.sent_campaigns}</p><p className="text-xs text-slate-500">Sent</p></Card>
              <Card className="p-4 text-center"><p className="text-2xl font-bold">{campaignStats.total_recipients}</p><p className="text-xs text-slate-500">Total Recipients</p></Card>
            </div>

            <div className="space-y-4">
              {campaigns.map(c => (
                <Card key={c.id} className="p-4 hover:shadow-md transition-shadow" data-testid={`campaign-${c.id}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-slate-800">{c.name}</h4>
                      <p className="text-sm text-slate-500">Subject: {c.subject}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="capitalize">{c.target_audience}</Badge>
                        <Badge className={c.status === 'sent' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'}>{c.status}</Badge>
                        {c.sent_count > 0 && <span className="text-xs text-slate-500">Sent to {c.sent_count} recipients</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {c.status === 'draft' && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => setCampaignDialog({ open: true, data: c, mode: 'edit' })}><Edit className="h-4 w-4" /></Button>
                          <Button size="sm" className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => handleSendCampaign(c.id)}><Send className="h-4 w-4 mr-1" />Send</Button>
                        </>
                      )}
                      <Button size="sm" variant="ghost" className="text-red-500" onClick={async () => { await axios.delete(`${API}/campaigns/${c.id}`, getAuthHeader()); toast.success('Deleted'); loadData(); }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
              {campaigns.length === 0 && <Card className="p-8 text-center text-slate-500">No campaigns yet. Create your first email campaign!</Card>}
            </div>
          </div>
        )}

        {/* ===== TESTIMONIALS TAB ===== */}
        {activeTab === 'testimonials' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Client Testimonials & Success Stories</h3>
              <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => setTestimonialDialog({ open: true, data: { rating: 5, status: 'published' } })} data-testid="add-testimonial-btn">
                <Plus className="h-4 w-4 mr-2" />Add Testimonial
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {testimonials.map(t => (
                <Card key={t.id} className={`p-5 ${t.featured ? 'border-amber-300 bg-amber-50/30' : ''}`} data-testid={`testimonial-${t.id}`}>
                  {t.featured && <Badge className="bg-amber-100 text-amber-700 mb-2">Featured</Badge>}
                  <div className="flex mb-2">{Array.from({length: t.rating}, (_, i) => <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />)}</div>
                  <p className="text-slate-700 text-sm italic mb-3">"{t.text}"</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-slate-800 text-sm">{t.client_name}</p>
                      <p className="text-xs text-slate-500">{t.client_country} &middot; {t.service_used}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => setTestimonialDialog({ open: true, data: t })}><Edit className="h-4 w-4" /></Button>
                      <Button size="sm" variant="ghost" className="text-red-500" onClick={async () => { await axios.delete(`${API}/marketing-tools/testimonials/${t.id}`, getAuthHeader()); loadData(); }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
              {testimonials.length === 0 && <Card className="p-8 text-center text-slate-500 col-span-full">No testimonials yet. Add your first success story!</Card>}
            </div>
          </div>
        )}

        {/* ===== LEADERBOARD TAB ===== */}
        {activeTab === 'leaderboard' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Partner Performance Leaderboard</h3>
            <div className="space-y-3">
              {leaderboard.map((partner, idx) => (
                <Card key={partner.partner_id} className={`p-5 ${idx === 0 ? 'border-amber-300 bg-gradient-to-r from-amber-50 to-white' : ''}`} data-testid={`partner-rank-${partner.rank}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold ${idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-slate-200 text-slate-600' : idx === 2 ? 'bg-orange-100 text-orange-600' : 'bg-slate-100 text-slate-500'}`}>
                        #{partner.rank}
                      </div>
                      <div>
                        <p className="font-semibold text-slate-800">{partner.partner_name}</p>
                        <p className="text-xs text-slate-500">{partner.email}</p>
                      </div>
                      <Badge className={`ml-2 capitalize ${tierColors[partner.tier] || ''} bg-transparent border`}>
                        <Trophy className={`h-3 w-3 mr-1 ${tierColors[partner.tier]}`} />{partner.tier}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-6 text-right">
                      <div><p className="text-lg font-bold text-slate-800">{partner.total_sales}</p><p className="text-xs text-slate-500">Sales</p></div>
                      <div><p className="text-lg font-bold text-[#2a777a]">{partner.total_revenue.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}</p><p className="text-xs text-slate-500">Revenue</p></div>
                      <div><p className="text-lg font-bold text-emerald-600">{partner.conversion_rate}%</p><p className="text-xs text-slate-500">Conversion</p></div>
                    </div>
                  </div>
                </Card>
              ))}
              {leaderboard.length === 0 && <Card className="p-8 text-center text-slate-500">No partner data available.</Card>}
            </div>
          </div>
        )}

        {/* ===== PROMO CODES TAB ===== */}
        {activeTab === 'promos' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Promo Codes</h3>
              <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => setPromoDialog({ open: true, data: { discount_type: 'percentage', discount_value: 10, max_uses: 100 } })} data-testid="create-promo-btn">
                <Plus className="h-4 w-4 mr-2" />Create Promo
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {promos.map(p => (
                <Card key={p.id} className={`p-5 ${p.active ? '' : 'opacity-60'}`} data-testid={`promo-${p.code}`}>
                  <div className="flex items-center justify-between mb-2">
                    <code className="text-lg font-bold text-[#2a777a] bg-teal-50 px-3 py-1 rounded">{p.code}</code>
                    <Badge className={p.active ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{p.active ? 'Active' : 'Inactive'}</Badge>
                  </div>
                  <p className="text-sm text-slate-600">{p.discount_type === 'percentage' ? `${p.discount_value}% off` : `Flat ${p.discount_value} off`}</p>
                  <p className="text-xs text-slate-500 mt-1">Used: {p.used_count || 0} / {p.max_uses || 'Unlimited'}</p>
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" variant="ghost" className="text-red-500" onClick={async () => { await axios.delete(`${API}/marketing/promo/${p.id}`, getAuthHeader()); loadData(); }}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ===== DIALOGS ===== */}
      {/* Lead Dialog */}
      <Dialog open={leadDialog.open} onOpenChange={(o) => setLeadDialog({ ...leadDialog, open: o })}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{leadDialog.mode === 'create' ? 'Add New Lead' : 'Edit Lead'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Name *</Label><Input value={leadDialog.data?.name || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, name: e.target.value } })} /></div>
              <div><Label>Phone</Label><Input value={leadDialog.data?.phone || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, phone: e.target.value } })} /></div>
            </div>
            <div><Label>Email *</Label><Input type="email" value={leadDialog.data?.email || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, email: e.target.value } })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Service Interested</Label><Input value={leadDialog.data?.service_interested || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, service_interested: e.target.value } })} /></div>
              <div><Label>Source</Label>
                <Select value={leadDialog.data?.source || 'manual'} onValueChange={(v) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, source: v } })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="website">Website</SelectItem><SelectItem value="google_ads">Google Ads</SelectItem><SelectItem value="facebook">Facebook</SelectItem><SelectItem value="instagram">Instagram</SelectItem><SelectItem value="referral">Referral</SelectItem><SelectItem value="walk_in">Walk-in</SelectItem><SelectItem value="manual">Manual</SelectItem><SelectItem value="whatsapp">WhatsApp</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>Country of Interest</Label><Input value={leadDialog.data?.country_of_interest || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, country_of_interest: e.target.value } })} /></div>
            <div><Label>Message</Label><Textarea value={leadDialog.data?.message || ''} onChange={(e) => setLeadDialog({ ...leadDialog, data: { ...leadDialog.data, message: e.target.value } })} /></div>
            <Button onClick={handleSaveLead} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">{leadDialog.mode === 'create' ? 'Capture Lead' : 'Update Lead'}</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Follow-up Dialog */}
      <Dialog open={followUpDialog.open} onOpenChange={(o) => setFollowUpDialog({ ...followUpDialog, open: o })}>
        <DialogContent>
          <DialogHeader><DialogTitle>Schedule Follow-up</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Type</Label>
              <Select value={followUpDialog.data?.type || 'call'} onValueChange={(v) => setFollowUpDialog({ ...followUpDialog, data: { ...followUpDialog.data, type: v } })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="call">Phone Call</SelectItem><SelectItem value="email">Email</SelectItem><SelectItem value="whatsapp">WhatsApp</SelectItem><SelectItem value="meeting">Meeting</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label>Date & Time</Label><Input type="datetime-local" value={followUpDialog.data?.scheduled_at || ''} onChange={(e) => setFollowUpDialog({ ...followUpDialog, data: { ...followUpDialog.data, scheduled_at: e.target.value } })} /></div>
            <div><Label>Message/Note</Label><Textarea value={followUpDialog.data?.message || ''} onChange={(e) => setFollowUpDialog({ ...followUpDialog, data: { ...followUpDialog.data, message: e.target.value } })} /></div>
            <Button onClick={handleScheduleFollowUp} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">Schedule Follow-up</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Campaign Dialog */}
      <Dialog open={campaignDialog.open} onOpenChange={(o) => setCampaignDialog({ ...campaignDialog, open: o })}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{campaignDialog.mode === 'create' ? 'Create Campaign' : 'Edit Campaign'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Campaign Name *</Label><Input value={campaignDialog.data?.name || ''} onChange={(e) => setCampaignDialog({ ...campaignDialog, data: { ...campaignDialog.data, name: e.target.value } })} /></div>
            <div><Label>Email Subject *</Label><Input value={campaignDialog.data?.subject || ''} onChange={(e) => setCampaignDialog({ ...campaignDialog, data: { ...campaignDialog.data, subject: e.target.value } })} /></div>
            <div><Label>Email Body *</Label><Textarea rows={5} value={campaignDialog.data?.body || ''} onChange={(e) => setCampaignDialog({ ...campaignDialog, data: { ...campaignDialog.data, body: e.target.value } })} /></div>
            <div><Label>Target Audience</Label>
              <Select value={campaignDialog.data?.target_audience || 'all'} onValueChange={(v) => setCampaignDialog({ ...campaignDialog, data: { ...campaignDialog.data, target_audience: v } })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem><SelectItem value="clients">Clients Only</SelectItem><SelectItem value="partners">Partners Only</SelectItem><SelectItem value="leads">Leads Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleSaveCampaign} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">Save Campaign</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Testimonial Dialog */}
      <Dialog open={testimonialDialog.open} onOpenChange={(o) => setTestimonialDialog({ ...testimonialDialog, open: o })}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{testimonialDialog.data?.id ? 'Edit Testimonial' : 'Add Testimonial'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Client Name *</Label><Input value={testimonialDialog.data?.client_name || ''} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, client_name: e.target.value } })} /></div>
              <div><Label>Country</Label><Input value={testimonialDialog.data?.client_country || ''} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, client_country: e.target.value } })} /></div>
            </div>
            <div><Label>Service Used</Label><Input value={testimonialDialog.data?.service_used || ''} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, service_used: e.target.value } })} /></div>
            <div><Label>Rating (1-5)</Label><Input type="number" min="1" max="5" value={testimonialDialog.data?.rating || 5} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, rating: parseInt(e.target.value) } })} /></div>
            <div><Label>Testimonial Text *</Label><Textarea rows={3} value={testimonialDialog.data?.text || ''} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, text: e.target.value } })} /></div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={testimonialDialog.data?.featured || false} onChange={(e) => setTestimonialDialog({ ...testimonialDialog, data: { ...testimonialDialog.data, featured: e.target.checked } })} />
              <Label>Featured Testimonial</Label>
            </div>
            <Button onClick={handleSaveTestimonial} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">Save Testimonial</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Promo Dialog */}
      <Dialog open={promoDialog.open} onOpenChange={(o) => setPromoDialog({ ...promoDialog, open: o })}>
        <DialogContent>
          <DialogHeader><DialogTitle>Create Promo Code</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Code *</Label><Input placeholder="e.g., SUMMER2026" value={promoDialog.data?.code || ''} onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, code: e.target.value.toUpperCase() } })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Discount Type</Label>
                <Select value={promoDialog.data?.discount_type || 'percentage'} onValueChange={(v) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, discount_type: v } })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="percentage">Percentage (%)</SelectItem><SelectItem value="flat">Flat Amount</SelectItem></SelectContent>
                </Select>
              </div>
              <div><Label>Discount Value</Label><Input type="number" value={promoDialog.data?.discount_value || 10} onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, discount_value: parseFloat(e.target.value) } })} /></div>
            </div>
            <div><Label>Max Uses</Label><Input type="number" value={promoDialog.data?.max_uses || 100} onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, max_uses: parseInt(e.target.value) } })} /></div>
            <Button onClick={handleSavePromo} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">Create Promo Code</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Assign Scorecard Lead Dialog */}
      <Dialog open={assignDialog.open} onOpenChange={(o) => setAssignDialog({ ...assignDialog, open: o })}>
        <DialogContent data-testid="assign-dialog">
          <DialogHeader>
            <DialogTitle>Assign scorecard lead</DialogTitle>
          </DialogHeader>
          {assignDialog.lead && (
            <div className="space-y-4">
              <div className="rounded-lg bg-slate-50 p-3 text-sm">
                <p className="font-semibold text-slate-800">{assignDialog.lead.name}</p>
                <p className="text-xs text-slate-500">{assignDialog.lead.email} · {assignDialog.lead.phone}</p>
                <p className="text-xs text-slate-500 mt-1">Best fit: <b>{assignDialog.lead.top_pathway_name}</b> ({assignDialog.lead.top_score}/100)</p>
                <button onClick={() => openPdf(assignDialog.lead.score_id)} className="text-xs text-[#2a777a] font-semibold mt-1 inline-flex items-center gap-1" data-testid="assign-dialog-pdf">
                  <Download className="h-3 w-3" /> View attached PDF report
                </button>
              </div>
              <div>
                <Label className="text-sm">Assign to partner / sales person</Label>
                <Select value={assignDialog.userId} onValueChange={(v) => setAssignDialog({ ...assignDialog, userId: v })}>
                  <SelectTrigger className="mt-1" data-testid="assign-user-select"><SelectValue placeholder="Select a team member" /></SelectTrigger>
                  <SelectContent>
                    {assignableUsers.map(u => (
                      <SelectItem key={u.id} value={u.id} data-testid={`assign-user-${u.id}`}>
                        {u.name} · {String(u.role).replace(/_/g, ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-slate-400">The client details and PDF scorecard will be linked to the assigned person.</p>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setAssignDialog({ open: false, lead: null, userId: '' })}>Cancel</Button>
                <Button className="bg-[#2a777a] hover:bg-[#1f5c5e] text-white" onClick={handleAssign} data-testid="assign-confirm-btn">Assign</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

    </div>
  );
};

// Gift icon stub
const Gift = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" /></svg>
);

export default MarketingDashboard;
