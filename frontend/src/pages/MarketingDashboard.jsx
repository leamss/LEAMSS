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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;
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
  const [reportDialog, setReportDialog] = useState({ open: false, lead: null });
  
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
  const [promoDialog, setPromoDialog] = useState({ open: false, data: {}, mode: 'create' });

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

  const printLeadReport = (lead) => {
    if (!lead) return;
    const rep = lead.assessment_report || {};
    const clientName = lead.name || 'Valued Client';
    const dateStr = rep.date || (lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-GB') : new Date().toLocaleDateString('en-GB'));
    const flag = rep.country_flag || (lead.country_of_interest === 'NZ' ? '🇳🇿' : (lead.country_of_interest === 'CA' ? '🇨🇦' : '🇦🇺'));
    const countryName = rep.country_name || (lead.country_of_interest === 'NZ' ? 'New Zealand' : (lead.country_of_interest === 'CA' ? 'Canada' : 'Australia'));
    const score = rep.score ?? lead.score_data?.total ?? '—';
    const maxScore = rep.max_score ?? lead.score_data?.maxScore ?? (countryName.includes('Zealand') ? 6 : 100);
    const unit = rep.unit ?? lead.score_data?.unit ?? 'Points';
    const passMark = rep.pass_mark ?? lead.score_data?.passMark ?? (countryName.includes('Zealand') ? 6 : 65);
    const qualifies = rep.qualifies ?? (score !== '—' && Number(score) >= passMark);
    const breakdown = rep.breakdown || lead.score_data?.breakdown || [];

    const printWin = window.open('', '_blank');
    if (!printWin) {
      toast.error('Popup blocked. Please allow popups to view/print report.');
      return;
    }

    const rowsHtml = breakdown.length > 0 ? breakdown.map(b => `
      <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e293b;">${b.label || b.id}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#475569;">${b.valLabel || '—'}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:700;color:#1b4332;">+${b.pts} pts</td>
      </tr>
    `).join('') : `
      <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e293b;">Total Points Evaluated</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#475569;">${qualifies ? 'Meets standard statutory benchmark' : 'Requires additional pathway points'}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:700;color:#1b4332;">${score} ${unit}</td>
      </tr>
    `;

    const statusPillHtml = qualifies
      ? `<span style="display:inline-block;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:700;background:#dcfce7;color:#166534;margin-top:12px;">✓ Qualifies for Minimum Statutory Threshold (Pass Mark: ${passMark} ${unit})</span>`
      : `<span style="display:inline-block;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:700;background:#fef3c7;color:#92400e;margin-top:12px;">⚠️ Requires ${typeof score === 'number' ? Math.max(0, Math.round((passMark - score) * 10) / 10) : 'additional'} more points to meet pass mark (${passMark} ${unit})</span>`;

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${countryName} Client Assessment Report - ${clientName}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 40px; color: #1e293b; background: #fff; }
          .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1b4332; padding-bottom: 20px; margin-bottom: 24px; }
          .brand { font-size: 24px; font-weight: 800; color: #1b4332; letter-spacing: -0.5px; }
          .brand-sub { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; font-weight: 700; }
          .score-card { background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
          .score-big { font-size: 42px; font-weight: 800; color: #1b4332; line-height: 1; }
          table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
          th { text-align: left; padding: 10px 14px; background: #f1f5f9; color: #475569; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
          .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }
          @media print {
            body { padding: 20px; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <div class="brand">LEAMSS IMMIGRATION</div>
            <div class="brand-sub">Official Client Assessment & Points Breakdown</div>
          </div>
          <div style="text-align: right; font-size: 12px; color: #64748b;">
            <div>Ref: <b>${lead.lead_number || lead.id || 'N/A'}</b></div>
            <div>Date: <b>${dateStr}</b></div>
          </div>
        </div>

        <div style="margin-bottom: 20px;">
          <h2 style="margin: 0 0 6px 0; font-size: 20px; color: #0f172a;">${flag} ${countryName} Immigration Points & Assessment Report</h2>
          <p style="margin: 0; font-size: 13px; color: #64748b;">Applicant: <b>${clientName}</b> · Phone: <b>${lead.phone || '—'}</b> · Email: <b>${lead.email || '—'}</b></p>
        </div>

        <div class="score-card">
          <div style="font-size: 12px; text-transform: uppercase; font-weight: 700; color: #64748b; margin-bottom: 8px;">Overall Evaluation Score</div>
          <div class="score-big">${score} <span style="font-size: 20px; font-weight: 500; color: #64748b;">/ ${maxScore} ${unit}</span></div>
          <div>${statusPillHtml}</div>
          <p style="margin: 16px 0 0 0; font-size: 13px; color: #334155; line-height: 1.6;">
            ${rep.summary || `Applicant profile was evaluated against statutory requirements for ${countryName}. Total score recorded is ${score} ${unit}.`}
          </p>
        </div>

        <div>
          <h3 style="font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 8px;">Detailed Assessment Parameter Breakdown</h3>
          <table>
            <thead>
              <tr>
                <th>Assessment Parameter</th>
                <th>Selection / Criteria</th>
                <th style="text-align:right;">Points Claimed</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>

        <div class="footer">
          LEAMSS Migration & Visa Advisory Platform · Confidential Assessment Document · Generated for ${clientName}
        </div>
      </body>
      </html>
    `;

    printWin.document.open();
    printWin.document.write(html);
    printWin.document.close();
    printWin.focus();
    setTimeout(() => { printWin.print(); }, 400);
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
      if (promoDialog.mode === 'edit' && promoDialog.data?.id) {
        await axios.put(`${API}/marketing/promo/${promoDialog.data.id}`, promoDialog.data, getAuthHeader());
        toast.success(`Promo code ${promoDialog.data.code} updated successfully!`);
      } else {
        await axios.post(`${API}/marketing/promo`, promoDialog.data, getAuthHeader());
        toast.success('Promo code created successfully!');
      }
      setPromoDialog({ open: false, data: {}, mode: 'create' });
      loadData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save promo code');
    }
  };

  const stageColors = {
    new: 'bg-sky-100 text-sky-700 border-sky-200',
    contacted: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-200',
    qualified: 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-200',
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

        {/* Phase 21 Slice 3 Sub-Slice B — AI Marketing Toolbox row */}
        <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="ai-marketing-toolbox">
          <button
            onClick={() => navigate('/portal/marketing/content-studio')}
            className="group text-left p-4 rounded-xl bg-gradient-to-br from-leamss-orange-500 to-leamss-orange-600 text-white shadow-md hover:shadow-lg transition-all"
            data-testid="open-content-studio"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wide opacity-80">AI Studio</span>
              <span className="text-[9px] bg-white/20 px-1.5 py-0.5 rounded-full">Claude 4.5</span>
            </div>
            <p className="font-bold text-sm">Content Studio</p>
            <p className="text-[11px] opacity-90 mt-0.5">3 variants per brief · 6 content types · 5 brand voices</p>
          </button>
          <button
            onClick={() => navigate('/portal/marketing/seo')}
            className="group text-left p-4 rounded-xl bg-white border-2 border-leamss-teal-300 hover:border-leamss-teal-500 hover:shadow-md transition-all"
            data-testid="open-seo-hub"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wide text-leamss-teal-600 font-semibold">SEO Tools</span>
            </div>
            <p className="font-bold text-sm text-slate-800">Keywords · Meta · Links</p>
            <p className="text-[11px] text-slate-500 mt-0.5">AI keyword research & meta optimisation</p>
          </button>
          <button
            onClick={() => navigate('/portal/marketing/aeo')}
            className="group text-left p-4 rounded-xl bg-white border-2 border-leamss-orange-300 hover:border-leamss-orange-500 hover:shadow-md transition-all"
            data-testid="open-aeo-hub"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wide text-leamss-orange-600 font-semibold">AEO Tools</span>
            </div>
            <p className="font-bold text-sm text-slate-800">FAQ · Voice · Snippets</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Answer engine optimisation for voice & SERP</p>
          </button>
          <button
            onClick={() => navigate('/portal/marketing/geo')}
            className="group text-left p-4 rounded-xl bg-white border-2 border-leamss-red-300 hover:border-leamss-red-500 hover:shadow-md transition-all relative overflow-hidden"
            data-testid="open-geo-hub"
          >
            <div className="absolute top-1 right-1">
              <span className="text-[8px] bg-leamss-red-600 text-white px-1.5 py-0.5 rounded-full font-bold tracking-wider">NEW</span>
            </div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wide text-leamss-red-600 font-semibold">GEO Tools</span>
            </div>
            <p className="font-bold text-sm text-slate-800">LLM Citation Optimiser</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Make content quotable by ChatGPT, Claude, Perplexity</p>
          </button>
        </div>

        {/* ===== OVERVIEW TAB ===== */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('leads')} data-testid="stat-leads">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-sky-50 rounded-lg"><Target className="h-5 w-5 text-sky-600" /></div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{pipelineStats.total}</p>
                    <p className="text-xs text-slate-500">Total Leads</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('campaigns')} data-testid="stat-campaigns">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-leamss-orange-50 rounded-lg"><Mail className="h-5 w-5 text-leamss-orange-600" /></div>
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
                        <td className="p-4 text-slate-600">
                          <p className="font-medium text-slate-800">{lead.service_interested || 'General Inquiry'}</p>
                          {lead.assessment_report && (
                            <div className="mt-1">
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                                <CheckCircle className="h-3 w-3 text-emerald-600" />
                                Score: {lead.assessment_report.score} {lead.assessment_report.unit || 'pts'}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="p-4"><Badge variant="outline" className="text-xs capitalize">{lead.source?.replace(/_/g, ' ')}</Badge></td>
                        <td className="p-4 text-center">
                          <Badge className={`capitalize ${stageColors[lead.stage] || ''}`}>{lead.stage}</Badge>
                        </td>
                        <td className="p-4 text-center" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-center gap-1.5 flex-wrap">
                            {(lead.assessment_report || lead.source === 'eligibility_calculator' || String(lead.message || '').includes('Score:')) && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-[#1b4332] border-[#1b4332]/40 bg-emerald-50 hover:bg-[#1b4332] hover:text-white h-8 px-2.5 text-xs font-bold flex items-center gap-1 transition-all shadow-xs"
                                onClick={() => setReportDialog({ open: true, lead })}
                                title="View Client Assessment Report"
                                data-testid={`view-report-btn-${lead.id}`}
                              >
                                <FileText className="h-3.5 w-3.5" /> Report
                              </Button>
                            )}
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

                {/* Generated Assessment Report Card if available */}
                {(selectedLead.assessment_report || String(selectedLead.message || '').includes('Score:')) && (
                  <div className="mb-5 rounded-xl border-2 border-[#1b4332]/20 bg-gradient-to-br from-emerald-50/40 via-white to-slate-50 p-4 shadow-xs">
                    <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{selectedLead.assessment_report?.country_flag || '🇳🇿'}</span>
                        <div>
                          <h4 className="font-bold text-slate-800 text-sm">
                            {selectedLead.assessment_report?.headline || `${selectedLead.service_interested || 'Assessment'} Report`}
                          </h4>
                          <p className="text-xs text-slate-500">
                            Generated on {selectedLead.assessment_report?.date || (selectedLead.created_at ? new Date(selectedLead.created_at).toLocaleDateString() : 'N/A')}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          className="bg-[#1b4332] hover:bg-[#143427] text-white text-xs h-8 font-semibold flex items-center gap-1"
                          onClick={() => setReportDialog({ open: true, lead: selectedLead })}
                        >
                          <Eye className="h-3.5 w-3.5" /> Full Report
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-slate-700 border-slate-300 hover:bg-slate-100 text-xs h-8 font-semibold flex items-center gap-1"
                          onClick={() => printLeadReport(selectedLead)}
                        >
                          <Download className="h-3.5 w-3.5" /> Print / PDF
                        </Button>
                      </div>
                    </div>

                    {/* Scorecard pill */}
                    <div className="flex items-center gap-4 p-3 bg-white rounded-lg border border-slate-200 mb-3">
                      <div className="text-center px-4 border-r border-slate-200">
                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Score</p>
                        <p className="text-2xl font-black text-[#1b4332]">
                          {selectedLead.assessment_report?.score ?? '—'}
                          <span className="text-xs font-normal text-slate-400"> / {selectedLead.assessment_report?.max_score ?? '—'} {selectedLead.assessment_report?.unit || 'Points'}</span>
                        </p>
                      </div>
                      <div className="flex-1">
                        {selectedLead.assessment_report?.qualifies ? (
                          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-100 px-3 py-1 rounded-full">
                            <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
                            Qualifies for Minimum Statutory Threshold (Pass Mark: {selectedLead.assessment_report?.pass_mark} {selectedLead.assessment_report?.unit})
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-100 px-3 py-1 rounded-full">
                            ⚠️ Requires {typeof selectedLead.assessment_report?.score === 'number' && selectedLead.assessment_report?.pass_mark ? Math.max(0, Math.round((selectedLead.assessment_report.pass_mark - selectedLead.assessment_report.score) * 10) / 10) : 'additional'} more points to meet pass mark ({selectedLead.assessment_report?.pass_mark} {selectedLead.assessment_report?.unit})
                          </span>
                        )}
                        <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                          {selectedLead.assessment_report?.summary || selectedLead.message}
                        </p>
                      </div>
                    </div>

                    {/* Parameter Breakdown Table if available */}
                    {(selectedLead.assessment_report?.breakdown || []).length > 0 && (
                      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                        <table className="w-full text-xs">
                          <thead className="bg-slate-50 text-slate-600 border-b">
                            <tr>
                              <th className="text-left p-2.5 font-semibold">Parameter</th>
                              <th className="text-left p-2.5 font-semibold">Selection / Claim</th>
                              <th className="text-right p-2.5 font-semibold">Points</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {selectedLead.assessment_report.breakdown.map((b, i) => (
                              <tr key={i} className="hover:bg-slate-50">
                                <td className="p-2.5 font-medium text-slate-800">{b.label || b.id}</td>
                                <td className="p-2.5 text-slate-600">{b.valLabel || '—'}</td>
                                <td className="p-2.5 text-right font-bold text-[#1b4332]">+{b.pts} pts</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
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
              <Button
                className="bg-[#2a777a] hover:bg-[#236466] text-white"
                onClick={() => setPromoDialog({ open: true, mode: 'create', data: { discount_type: 'percentage', discount_value: 10, max_uses: 100, is_active: true, active: true } })}
                data-testid="create-promo-btn"
              >
                <Plus className="h-4 w-4 mr-2" />Create Promo
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {promos.map(p => {
                const used = p.current_uses ?? p.used_count ?? 0;
                const max = p.max_uses;
                const isLimitReached = Boolean(max && max > 0 && used >= max);
                const isExpired = isLimitReached || p.status === 'expired';
                const isExplicitActive = p.is_active !== undefined ? p.is_active : (p.active !== undefined ? p.active : true);
                const isActive = isExplicitActive && !isExpired;

                return (
                  <Card key={p.id} className={`p-5 transition-all ${isActive ? 'bg-white hover:shadow-md' : 'bg-slate-50/80 border-dashed opacity-80'}`} data-testid={`promo-${p.code}`}>
                    <div className="flex items-center justify-between mb-2">
                      <code className="text-lg font-bold text-[#2a777a] bg-teal-50 px-3 py-1 rounded">{p.code}</code>
                      <Badge className={
                        isActive ? 'bg-emerald-100 text-emerald-800 border-emerald-200' :
                        isExpired ? 'bg-rose-100 text-rose-800 border-rose-300 font-semibold' :
                        'bg-slate-100 text-slate-800 border-slate-200'
                      }>
                        {isActive ? 'Active' : isExpired ? 'Expired' : 'Inactive'}
                      </Badge>
                    </div>
                    <p className="text-sm font-semibold text-slate-700">{p.discount_type === 'percentage' ? `${p.discount_value}% off` : `Flat ₹${p.discount_value} off`}</p>
                    <p className="text-xs text-slate-500 mt-1 font-medium">
                      Used: <strong className={isExpired ? 'text-rose-700 font-bold' : 'text-slate-700'}>{used}</strong> / {max || 'Unlimited'}
                    </p>
                    {p.notes && <p className="text-xs text-slate-400 mt-1 italic line-clamp-1">{p.notes}</p>}
                    
                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 text-xs font-medium text-slate-700 hover:text-[#2a777a] hover:border-[#2a777a] flex items-center gap-1.5"
                        onClick={() => setPromoDialog({
                          open: true,
                          mode: 'edit',
                          data: {
                            id: p.id,
                            code: p.code,
                            discount_type: p.discount_type || 'percentage',
                            discount_value: p.discount_value ?? 10,
                            max_uses: p.max_uses ?? 100,
                            is_active: p.is_active !== undefined ? p.is_active : (p.active !== undefined ? p.active : true),
                            active: p.is_active !== undefined ? p.is_active : (p.active !== undefined ? p.active : true),
                            current_uses: used,
                            notes: p.notes || ''
                          }
                        })}
                        data-testid={`edit-promo-${p.code}`}
                      >
                        <Edit className="h-3.5 w-3.5" />
                        Edit Details
                      </Button>

                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 text-xs text-red-500 hover:text-red-700 hover:bg-red-50"
                        title="Deactivate / Delete"
                        onClick={async () => {
                          if (window.confirm(`Deactivate promo code ${p.code}?`)) {
                            await axios.delete(`${API}/marketing/promo/${p.id}`, getAuthHeader());
                            toast.success(`Promo code ${p.code} deactivated`);
                            loadData();
                          }
                        }}
                        data-testid={`delete-promo-${p.code}`}
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Deactivate
                      </Button>
                    </div>
                  </Card>
                );
              })}
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
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-800">
              {promoDialog.mode === 'edit' ? 'Edit Promo Code Details' : 'Create New Promo Code'}
            </DialogTitle>
          </DialogHeader>

          {promoDialog.mode === 'edit' && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 text-xs text-teal-800 flex items-center justify-between">
              <div>
                <span className="font-semibold">Current Usage:</span> {promoDialog.data?.current_uses ?? 0} successful client payments
              </div>
              <Badge variant="outline" className="bg-white border-teal-300 text-teal-700">
                {promoDialog.data?.current_uses ?? 0} / {promoDialog.data?.max_uses || '∞'}
              </Badge>
            </div>
          )}

          <div className="space-y-3.5 pt-1">
            <div>
              <Label className="text-xs font-semibold text-slate-700">Promo Code *</Label>
              <Input
                placeholder="e.g., SUMMER2026"
                className="font-mono uppercase font-bold tracking-wider"
                value={promoDialog.data?.code || ''}
                onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, code: e.target.value.toUpperCase() } })}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold text-slate-700">Discount Type</Label>
                <Select
                  value={promoDialog.data?.discount_type || 'percentage'}
                  onValueChange={(v) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, discount_type: v } })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percentage">Percentage (%)</SelectItem>
                    <SelectItem value="flat">Flat Amount (₹)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-semibold text-slate-700">
                  {promoDialog.data?.discount_type === 'percentage' ? 'Discount Percentage (%)' : 'Discount Amount (₹)'}
                </Label>
                <Input
                  type="number"
                  value={promoDialog.data?.discount_value ?? 10}
                  onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, discount_value: parseFloat(e.target.value) || 0 } })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold text-slate-700">Status</Label>
                <Select
                  value={promoDialog.data?.is_active !== false && promoDialog.data?.active !== false ? 'active' : 'inactive'}
                  onValueChange={(v) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, is_active: v === 'active', active: v === 'active' } })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-semibold text-slate-700">Max User Limit (Uses)</Label>
                <Input
                  type="number"
                  min="1"
                  placeholder="e.g. 2, 5, 50"
                  value={promoDialog.data?.max_uses ?? 100}
                  onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, max_uses: parseInt(e.target.value) || 1 } })}
                />
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700">Internal Description / Notes</Label>
              <Input
                placeholder="e.g., Summer 2026 Special Campaign"
                value={promoDialog.data?.notes || ''}
                onChange={(e) => setPromoDialog({ ...promoDialog, data: { ...promoDialog.data, notes: e.target.value } })}
              />
            </div>

            <div className="pt-2">
              <Button onClick={handleSavePromo} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white font-medium">
                {promoDialog.mode === 'edit' ? 'Save & Update Promo Code' : 'Create Promo Code'}
              </Button>
            </div>
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

      {/* Generated Client Assessment Report Modal */}
      <Dialog open={reportDialog.open} onOpenChange={(o) => setReportDialog({ ...reportDialog, open: o })}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto p-0 border-0 shadow-2xl">
          {reportDialog.lead && (() => {
            const lead = reportDialog.lead;
            const rep = lead.assessment_report || {};
            const clientName = lead.name || 'Valued Client';
            const dateStr = rep.date || (lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-GB') : new Date().toLocaleDateString('en-GB'));
            const flag = rep.country_flag || (lead.country_of_interest === 'NZ' ? '🇳🇿' : (lead.country_of_interest === 'CA' ? '🇨🇦' : '🇦🇺'));
            const countryName = rep.country_name || (lead.country_of_interest === 'NZ' ? 'New Zealand' : (lead.country_of_interest === 'CA' ? 'Canada' : 'Australia'));
            const score = rep.score ?? lead.score_data?.total ?? '—';
            const maxScore = rep.max_score ?? lead.score_data?.maxScore ?? (countryName.includes('Zealand') ? 6 : 100);
            const unit = rep.unit ?? lead.score_data?.unit ?? 'Points';
            const passMark = rep.pass_mark ?? lead.score_data?.passMark ?? (countryName.includes('Zealand') ? 6 : 65);
            const qualifies = rep.qualifies ?? (score !== '—' && Number(score) >= passMark);
            const breakdown = rep.breakdown || lead.score_data?.breakdown || [];
            const pathways = rep.pathways || [];

            return (
              <div className="bg-white rounded-2xl overflow-hidden border border-slate-200">
                {/* Header ribbon matching start page report view */}
                <div className="bg-[#1b4332] text-white p-6 relative">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-widest text-emerald-300 bg-emerald-950/60 px-2.5 py-0.5 rounded-full inline-block mb-1.5">
                        Official Client Assessment Report
                      </span>
                      <h3 className="text-xl font-extrabold flex items-center gap-2">
                        <span>{flag}</span> {countryName} Immigration Points & Assessment Report
                      </h3>
                      <p className="text-xs text-emerald-100 mt-1">
                        Generated for <b>{clientName}</b> · {dateStr} · Ref: <b>{lead.lead_number || lead.id?.slice(0, 8)}</b>
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        className="bg-[#2a777a] hover:bg-[#205d60] text-white font-semibold text-xs h-9 px-3.5 shadow-sm"
                        onClick={() => printLeadReport(lead)}
                        data-testid="report-modal-download-btn"
                      >
                        <Download className="h-3.5 w-3.5 mr-1.5" /> Download Report (PDF)
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Score Highlight Box */}
                  <div className="rounded-xl border-2 border-slate-200 bg-gradient-to-br from-slate-50 to-white p-5">
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Total Profile Score</div>
                        <div className="text-4xl font-black text-[#1b4332] flex items-baseline gap-2">
                          {score}
                          <span className="text-lg font-semibold text-slate-400">/ {maxScore} {unit}</span>
                        </div>
                      </div>
                      <div>
                        {qualifies ? (
                          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                            <CheckCircle className="h-4 w-4 text-emerald-600" />
                            Qualifies for Minimum Statutory Threshold (Pass Mark: {passMark} {unit})
                          </div>
                        ) : (
                          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                            <span>⚠️</span> Requires {typeof score === 'number' ? Math.max(0, Math.round((passMark - score) * 10) / 10) : 'additional'} more points to meet pass mark ({passMark} {unit})
                          </div>
                        )}
                      </div>
                    </div>

                    <p className="text-sm text-slate-700 mt-4 leading-relaxed bg-white/80 p-3 rounded-lg border border-slate-100">
                      {rep.summary || `Dear ${clientName}, your profile was evaluated for ${countryName} skilled migration. Your profile scored a total of ${score} ${unit}. ${qualifies ? 'You meet the minimum statutory criteria for invitation rounds.' : 'You can bridge the points gap through Provincial/State nominations or partner skill claims.'}`}
                    </p>
                  </div>

                  {/* Parameter Breakdown Table */}
                  <div>
                    <h4 className="font-bold text-slate-800 text-sm mb-2 flex items-center justify-between">
                      <span>Detailed Assessment Parameter Breakdown</span>
                      <span className="text-xs font-normal text-slate-500">{breakdown.length} criteria evaluated</span>
                    </h4>

                    {breakdown.length > 0 ? (
                      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 text-xs">
                            <tr>
                              <th className="text-left p-3 font-semibold">Parameter</th>
                              <th className="text-left p-3 font-semibold">Value / Selection</th>
                              <th className="text-right p-3 font-semibold">Points Earned</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {breakdown.map((item, idx) => (
                              <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                                <td className="p-3 font-medium text-slate-800">{item.label || item.id}</td>
                                <td className="p-3 text-slate-600">{item.valLabel || '—'}</td>
                                <td className="p-3 text-right font-bold text-[#1b4332]">+{item.pts} pts</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-200 p-4 text-center bg-slate-50 text-slate-600 text-xs">
                        <p className="font-medium">Total recorded assessment score: <b className="text-[#1b4332]">{score} {unit}</b></p>
                        <p className="text-slate-500 mt-1">{lead.message || 'Points assessment was submitted via the eligibility portal.'}</p>
                      </div>
                    )}
                  </div>

                  {/* Pathways cards if present */}
                  {pathways.length > 0 && (
                    <div>
                      <h4 className="font-bold text-slate-800 text-sm mb-2">Verified Visa Pathways</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {pathways.map((pw, i) => (
                          <div key={i} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                            <h5 className="font-semibold text-xs text-[#1b4332]">{pw.name}</h5>
                            <p className="text-xs text-slate-600 mt-1 line-clamp-2">{pw.desc}</p>
                            {pw.req && <span className="inline-block mt-2 text-[10px] font-bold text-[#b45309] bg-amber-50 px-2 py-0.5 rounded border border-amber-200">Req: {pw.req}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Contact & Meta footer */}
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between flex-wrap gap-2 text-xs text-slate-500">
                    <div>
                      <span>Contact: <b>{lead.email}</b> · <b>{lead.phone || 'No phone'}</b></span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => setReportDialog({ open: false, lead: null })}>
                        Close
                      </Button>
                      <Button
                        size="sm"
                        className="bg-[#2a777a] hover:bg-[#205d60] text-white font-semibold"
                        onClick={() => printLeadReport(lead)}
                      >
                        <Download className="h-3.5 w-3.5 mr-1" /> Print Report
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}
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
