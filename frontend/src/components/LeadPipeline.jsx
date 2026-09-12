import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  Plus, CreditCard, FileText, Eye, CheckCircle, Send, XCircle,
  RefreshCw, Globe, Clock, LayoutGrid, List as ListIcon, Search, ChevronRight,
  MessageCircle, Mail, Phone, ExternalLink, Copy, Check, User, Sparkles, BookOpen, Briefcase
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGES = [
  { key: 'new', label: 'New Leads', color: 'bg-slate-500', text: 'text-slate-700', border: 'border-slate-300', bg: 'bg-slate-50', dot: 'bg-slate-500', icon: Plus },
  { key: 'payment_pending', label: 'Payment Pending', color: 'bg-amber-500', text: 'text-amber-700', border: 'border-amber-300', bg: 'bg-amber-50', dot: 'bg-amber-500', icon: Clock },
  { key: 'payment_received', label: 'Paid', color: 'bg-blue-500', text: 'text-blue-700', border: 'border-blue-300', bg: 'bg-blue-50', dot: 'bg-blue-500', icon: CreditCard },
  { key: 'under_review', label: 'Under Review', color: 'bg-orange-500', text: 'text-orange-700', border: 'border-orange-300', bg: 'bg-orange-50', dot: 'bg-orange-500', icon: Eye },
  { key: 'approved', label: 'Approved', color: 'bg-emerald-500', text: 'text-emerald-700', border: 'border-emerald-300', bg: 'bg-emerald-50', dot: 'bg-emerald-500', icon: CheckCircle },
  { key: 'proposal_sent', label: 'Proposal Sent', color: 'bg-teal-500', text: 'text-teal-700', border: 'border-teal-300', bg: 'bg-teal-50', dot: 'bg-teal-500', icon: Send },
  { key: 'proposal_paid', label: 'Proposal Paid', color: 'bg-cyan-500', text: 'text-cyan-700', border: 'border-cyan-300', bg: 'bg-cyan-50', dot: 'bg-cyan-500', icon: CreditCard },
  { key: 'awaiting_final_approval', label: 'Awaiting Approval', color: 'bg-indigo-500', text: 'text-indigo-700', border: 'border-indigo-300', bg: 'bg-indigo-50', dot: 'bg-indigo-500', icon: Clock },
  { key: 'case_created', label: 'Case Created', color: 'bg-green-600', text: 'text-green-700', border: 'border-green-300', bg: 'bg-green-50', dot: 'bg-green-600', icon: CheckCircle },
  { key: 'rejected', label: 'Rejected', color: 'bg-rose-500', text: 'text-rose-700', border: 'border-rose-300', bg: 'bg-rose-50', dot: 'bg-rose-500', icon: XCircle },
  { key: 'refunded', label: 'Refunded', color: 'bg-gray-500', text: 'text-gray-700', border: 'border-gray-300', bg: 'bg-gray-50', dot: 'bg-gray-500', icon: XCircle },
];

const STAGE_MAP = Object.fromEntries(STAGES.map(s => [s.key, s]));

const cleanPhone = (phone) => {
  if (!phone) return '';
  return String(phone).replace(/[^\d+]/g, '').replace(/^\+/, '');
};

const LeadPipeline = ({ onLeadClick }) => {
  const [pipeline, setPipeline] = useState({});
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('list'); // 'list' | 'board'
  const [activeStage, setActiveStage] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedLead, setSelectedLead] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [customMsg, setCustomMsg] = useState('');

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/partner-analytics/pipeline-summary`, getAuthHeader());
      setPipeline(res.data || {});
    } catch (e) {
      console.error(e);
      toast.error('Failed to load lead pipeline');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const totalLeads = useMemo(() => Object.values(pipeline).reduce((s, v) => s + (v?.count || 0), 0), [pipeline]);

  // Flatten all leads into one list, each tagged with its stage
  const allLeads = useMemo(() => {
    const rows = [];
    STAGES.forEach(stage => {
      const items = pipeline[stage.key]?.items || [];
      items.forEach(item => rows.push({ ...item, _stage: stage.key }));
    });
    return rows.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [pipeline]);

  const filteredLeads = useMemo(() => {
    return allLeads.filter(lead => {
      if (activeStage !== 'all' && lead._stage !== activeStage) return false;
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const hay = `${lead.client_name || ''} ${lead.client_email || ''} ${lead.client_mobile || ''} ${lead.country || ''} ${lead.service_type || ''} ${lead.pa_number || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [allLeads, activeStage, search]);

  const handleWhatsApp = (e, lead, customText) => {
    if (e) e.stopPropagation();
    const phone = cleanPhone(lead.client_mobile || lead.client_phone || lead.mobile || lead.phone);
    if (!phone) {
      toast.error('No mobile number available for this client');
      return;
    }
    const name = lead.client_name || 'Client';
    const text = customText || `Hi ${name}, this is regarding your visa assessment with LEAMSS. We would love to guide you on the next steps!`;
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(text)}`, '_blank');
  };

  const handleEmail = (e, lead) => {
    if (e) e.stopPropagation();
    const email = lead.client_email || lead.email;
    if (!email) {
      toast.error('No email address available for this client');
      return;
    }
    const name = lead.client_name || 'Client';
    const subject = `Regarding your application — LEAMSS`;
    const body = `Hi ${name},\n\nWe are following up on your visa application and assessment with LEAMSS.\n\nPlease let us know if you have any questions.\n\nWarm regards,\nLEAMSS Team`;
    window.open(`mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank');
  };

  const handleCall = (e, lead) => {
    if (e) e.stopPropagation();
    const phone = lead.client_mobile || lead.client_phone || lead.mobile || lead.phone;
    if (!phone) {
      toast.error('No phone number available');
      return;
    }
    window.open(`tel:${phone}`, '_self');
  };

  const handleCopyLink = (e, lead) => {
    if (e) e.stopPropagation();
    const portalUrl = `${window.location.origin}/pre-assessment-portal/${lead.id}`;
    navigator.clipboard.writeText(portalUrl);
    setCopiedId(lead.id);
    toast.success('Assessment link copied to clipboard!');
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-4" data-testid="lead-pipeline">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-800">Lead Pipeline & Follow-Up</h3>
          <p className="text-sm text-slate-500">{totalLeads} total leads across all stages · Full WhatsApp & Email engagement</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex items-center bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setView('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'list' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid="view-list-btn"
            >
              <ListIcon className="h-3.5 w-3.5" /> List
            </button>
            <button
              onClick={() => setView('board')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'board' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid="view-board-btn"
            >
              <LayoutGrid className="h-3.5 w-3.5" /> Board
            </button>
          </div>
          <Button variant="outline" size="sm" onClick={() => { setLoading(true); loadData(); }} className="text-xs text-[#2a777a] border-[#2a777a]/30 hover:bg-[#2a777a]/10 gap-1">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Stage filter pills + search */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setActiveStage('all')}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${activeStage === 'all' ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'}`}
        >
          All ({totalLeads})
        </button>
        {STAGES.map(stage => {
          const count = pipeline[stage.key]?.count || 0;
          if (count === 0) return null;
          const active = activeStage === stage.key;
          return (
            <button
              key={stage.key}
              onClick={() => setActiveStage(active ? 'all' : stage.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${active ? `${stage.color} text-white border-transparent` : `bg-white ${stage.text} ${stage.border} hover:opacity-80`}`}
              data-testid={`filter-${stage.key}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-white' : stage.dot}`} />
              {stage.label} ({count})
            </button>
          );
        })}
        <div className="relative ml-auto w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, PA#..."
            className="pl-8 h-8 text-xs"
            data-testid="lead-search-input"
          />
        </div>
      </div>

      {/* LIST VIEW */}
      {view === 'list' && (
        <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm">
          <div className="hidden sm:grid grid-cols-[1.2fr_130px_150px_110px_150px_100px] gap-3 px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <span>Client</span>
            <span>Stage</span>
            <span>Country / Type</span>
            <span>PA Number</span>
            <span>Follow-Up Actions</span>
            <span>Date</span>
          </div>
          <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-100">
            {filteredLeads.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-300">
                <FileText className="h-10 w-10 mb-2" />
                <p className="text-sm">No leads match this filter</p>
              </div>
            ) : (
              filteredLeads.map(lead => {
                const stage = STAGE_MAP[lead._stage] || STAGES[0];
                const StageIcon = stage.icon;
                return (
                  <div
                    key={lead.id}
                    onClick={() => setSelectedLead(lead)}
                    className="grid grid-cols-1 sm:grid-cols-[1.2fr_130px_150px_110px_150px_100px] gap-2 sm:gap-3 items-center px-4 py-3 hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    data-testid={`lead-row-${lead.id}`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                        {(lead.client_name || 'C')[0].toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-sm text-slate-800 truncate group-hover:text-[#2a777a] transition-colors">{lead.client_name}</p>
                        <p className="text-xs text-slate-400 truncate">{lead.client_email || lead.client_mobile || 'No contact'}</p>
                      </div>
                    </div>

                    <div>
                      <Badge className={`${stage.bg} ${stage.text} border-0 text-xs gap-1 font-medium`}>
                        <StageIcon className="h-3 w-3" /> {stage.label}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-slate-600 min-w-0">
                      <Globe className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                      <span className="truncate">{lead.country || 'Global'} · {lead.service_type || 'PR'}</span>
                    </div>

                    <div>
                      <span className="text-xs font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">{lead.pa_number || 'N/A'}</span>
                    </div>

                    {/* Quick follow-up buttons */}
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={(e) => handleWhatsApp(e, lead)}
                        title="Chat on WhatsApp"
                        className="p-1.5 rounded-md hover:bg-emerald-50 text-emerald-600 border border-emerald-200 transition-colors"
                        data-testid={`whatsapp-btn-${lead.id}`}
                      >
                        <MessageCircle className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleEmail(e, lead)}
                        title="Send Email"
                        className="p-1.5 rounded-md hover:bg-blue-50 text-blue-600 border border-blue-200 transition-colors"
                        data-testid={`email-btn-${lead.id}`}
                      >
                        <Mail className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleCall(e, lead)}
                        title="Call Client"
                        className="p-1.5 rounded-md hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
                        data-testid={`call-btn-${lead.id}`}
                      >
                        <Phone className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleCopyLink(e, lead)}
                        title="Copy Client Assessment Link"
                        className="p-1.5 rounded-md hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
                        data-testid={`copy-link-btn-${lead.id}`}
                      >
                        {copiedId === lead.id ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>

                    <div className="flex items-center justify-between sm:justify-start gap-2">
                      <span className="text-xs text-slate-400">{lead.created_at ? new Date(lead.created_at).toLocaleDateString() : ''}</span>
                      <ChevronRight className="h-3.5 w-3.5 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-0.5 transition-all hidden sm:block" />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* BOARD VIEW */}
      {view === 'board' && (
        <div className="flex items-start gap-3 overflow-x-auto pb-4" style={{ minHeight: '450px' }}>
          {STAGES.filter(s => activeStage === 'all' || activeStage === s.key).map(stage => {
            const StageIcon = stage.icon;
            const stageData = pipeline[stage.key] || { count: 0, items: [] };
            const items = search.trim()
              ? (stageData.items || []).filter(item => `${item.client_name || ''} ${item.client_email || ''} ${item.country || ''} ${item.service_type || ''} ${item.pa_number || ''}`.toLowerCase().includes(search.trim().toLowerCase()))
              : (stageData.items || []);

            return (
              <div key={stage.key} className="flex-shrink-0 w-72" data-testid={`kanban-${stage.key}`}>
                <div className={`${stage.bg} rounded-t-xl p-3 border ${stage.border} border-b-0`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 ${stage.color} rounded-md flex items-center justify-center`}>
                        <StageIcon className="h-3.5 w-3.5 text-white" />
                      </div>
                      <span className="font-semibold text-sm text-slate-700">{stage.label}</span>
                    </div>
                    <Badge variant="outline" className="text-xs h-5 bg-white">{stageData.count}</Badge>
                  </div>
                </div>
                <div className={`border ${stage.border} border-t-0 rounded-b-xl bg-slate-50/50 p-2 space-y-2 min-h-[350px] max-h-[550px] overflow-y-auto`}>
                  {items.length === 0 ? (
                    <div className="flex items-center justify-center h-32 text-slate-300">
                      <p className="text-xs">No leads</p>
                    </div>
                  ) : (
                    items.map(item => (
                      <div
                        key={item.id}
                        onClick={() => setSelectedLead({ ...item, _stage: stage.key })}
                        className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                        data-testid={`lead-card-${item.id}`}
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <div className="w-7 h-7 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                            {(item.client_name || 'C')[0]}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-semibold text-sm text-slate-800 truncate group-hover:text-[#2a777a] transition-colors">{item.client_name}</p>
                            <p className="text-[11px] text-slate-400 truncate">{item.client_email || item.client_mobile || ''}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
                          <Globe className="h-3 w-3 flex-shrink-0 text-slate-400" />
                          <span className="truncate">{item.country || 'Global'}</span>
                          <span className="text-slate-300">|</span>
                          <span className="truncate">{item.service_type || 'PR'}</span>
                        </div>

                        {/* Quick action bar */}
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100" onClick={(e) => e.stopPropagation()}>
                          <Badge className="bg-slate-100 text-slate-600 text-[11px] font-mono h-5">{item.pa_number || 'N/A'}</Badge>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => handleWhatsApp(e, item)}
                              title="WhatsApp"
                              className="p-1 rounded hover:bg-emerald-50 text-emerald-600 transition-colors"
                            >
                              <MessageCircle className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleEmail(e, item)}
                              title="Email"
                              className="p-1 rounded hover:bg-blue-50 text-blue-600 transition-colors"
                            >
                              <Mail className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleCopyLink(e, item)}
                              title="Copy Link"
                              className="p-1 rounded hover:bg-slate-100 text-slate-500 transition-colors"
                            >
                              {copiedId === item.id ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* LEAD FOLLOW-UP DETAIL MODAL */}
      {selectedLead && (
        <Dialog open={!!selectedLead} onOpenChange={(open) => { if (!open) { setSelectedLead(null); setCustomMsg(''); } }}>
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <div className="flex items-center justify-between pr-6">
                <DialogTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-[#2a777a]" />
                  <span>{selectedLead.client_name}</span>
                </DialogTitle>
                <Badge className={`${(STAGE_MAP[selectedLead._stage] || STAGES[0]).bg} ${(STAGE_MAP[selectedLead._stage] || STAGES[0]).text} border-0 text-xs`}>
                  {(STAGE_MAP[selectedLead._stage] || STAGES[0]).label}
                </Badge>
              </div>
            </DialogHeader>

            <div className="space-y-4 text-sm mt-2">
              {/* Quick Details Card */}
              <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-slate-400 font-medium">Email</p>
                  <p className="text-slate-800 font-semibold truncate">{selectedLead.client_email || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-medium">Mobile / Phone</p>
                  <p className="text-slate-800 font-semibold">{selectedLead.client_mobile || selectedLead.client_phone || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-medium">Target Country & Service</p>
                  <p className="text-slate-800 font-semibold">{selectedLead.country || 'Global'} · {selectedLead.service_type || 'PR'}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-medium">PA Number</p>
                  <p className="text-slate-800 font-semibold font-mono">{selectedLead.pa_number || 'N/A'}</p>
                </div>
                {selectedLead.education && (
                  <div>
                    <p className="text-slate-400 font-medium">Education</p>
                    <p className="text-slate-800">{selectedLead.education}</p>
                  </div>
                )}
                {selectedLead.work_experience && (
                  <div>
                    <p className="text-slate-400 font-medium">Work Experience</p>
                    <p className="text-slate-800">{selectedLead.work_experience}</p>
                  </div>
                )}
              </div>

              {/* Follow-Up Action Hub */}
              <div className="border border-slate-200 rounded-xl p-4 bg-white space-y-3">
                <p className="font-semibold text-xs uppercase tracking-wider text-slate-500">Engage & Follow Up</p>
                
                {/* 1-Click Action Buttons */}
                <div className="grid grid-cols-3 gap-2">
                  <Button
                    onClick={() => handleWhatsApp(null, selectedLead, customMsg)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 h-9 text-xs"
                    data-testid="modal-whatsapp-btn"
                  >
                    <MessageCircle className="h-4 w-4" /> WhatsApp
                  </Button>
                  <Button
                    onClick={() => handleEmail(null, selectedLead)}
                    className="bg-blue-600 hover:bg-blue-700 text-white gap-1.5 h-9 text-xs"
                    data-testid="modal-email-btn"
                  >
                    <Mail className="h-4 w-4" /> Send Email
                  </Button>
                  <Button
                    onClick={() => handleCall(null, selectedLead)}
                    variant="outline"
                    className="gap-1.5 h-9 text-xs"
                    data-testid="modal-call-btn"
                  >
                    <Phone className="h-4 w-4 text-slate-600" /> Phone Call
                  </Button>
                </div>

                {/* Custom WhatsApp Note Input */}
                <div className="pt-2">
                  <label className="text-[11px] font-medium text-slate-500 block mb-1">Custom WhatsApp Greeting / Message:</label>
                  <textarea
                    rows={2}
                    value={customMsg}
                    onChange={(e) => setCustomMsg(e.target.value)}
                    placeholder={`Hi ${selectedLead.client_name}, this is regarding your visa assessment with LEAMSS...`}
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#2a777a]"
                  />
                </div>
              </div>

              {/* Deep Workflow Actions */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const url = `${window.location.origin}/pre-assessment-portal/${selectedLead.id}`;
                    window.open(url, '_blank');
                  }}
                  className="text-xs gap-1 text-slate-600"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Preview as Client
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => handleCopyLink(e, selectedLead)}
                  className="text-xs gap-1 text-slate-600"
                >
                  {copiedId === selectedLead.id ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                  Copy Assessment Link
                </Button>

                {onLeadClick && (
                  <Button
                    size="sm"
                    onClick={() => {
                      const l = selectedLead;
                      setSelectedLead(null);
                      onLeadClick(l);
                    }}
                    className="bg-[#2a777a] hover:bg-[#236466] text-white text-xs gap-1 ml-auto"
                  >
                    <Sparkles className="h-3.5 w-3.5" /> Open Full Assessment
                  </Button>
                )}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default LeadPipeline;