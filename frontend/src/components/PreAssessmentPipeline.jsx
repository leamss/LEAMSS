import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { 
  Plus, Send, CheckCircle, Clock, XCircle, FileText, Upload, 
  CreditCard, ArrowRight, Eye, ChevronDown, ChevronUp, Search,
  User, Globe, Briefcase, GraduationCap, Phone, Mail, IndianRupee,
  AlertTriangle, RefreshCw, Filter
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGE_CONFIG = {
  new: { label: 'New Lead', color: 'bg-slate-500', textColor: 'text-slate-700', bgColor: 'bg-slate-50', icon: Plus },
  payment_pending: { label: 'Payment Pending', color: 'bg-amber-500', textColor: 'text-amber-700', bgColor: 'bg-amber-50', icon: Clock },
  payment_received: { label: 'Payment Received', color: 'bg-blue-500', textColor: 'text-blue-700', bgColor: 'bg-blue-50', icon: CreditCard },
  documents_submitted: { label: 'Docs Submitted', color: 'bg-indigo-500', textColor: 'text-indigo-700', bgColor: 'bg-indigo-50', icon: FileText },
  under_review: { label: 'Under Review', color: 'bg-purple-500', textColor: 'text-purple-700', bgColor: 'bg-purple-50', icon: Eye },
  approved: { label: 'Approved', color: 'bg-emerald-500', textColor: 'text-emerald-700', bgColor: 'bg-emerald-50', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-500', textColor: 'text-red-700', bgColor: 'bg-red-50', icon: XCircle },
  proposal_sent: { label: 'Proposal Sent', color: 'bg-teal-500', textColor: 'text-teal-700', bgColor: 'bg-teal-50', icon: Send },
  proposal_paid: { label: 'Proposal Paid', color: 'bg-green-500', textColor: 'text-green-700', bgColor: 'bg-green-50', icon: CheckCircle },
  case_created: { label: 'Case Created', color: 'bg-green-600', textColor: 'text-green-800', bgColor: 'bg-green-50', icon: CheckCircle },
  refund_initiated: { label: 'Refund Initiated', color: 'bg-orange-500', textColor: 'text-orange-700', bgColor: 'bg-orange-50', icon: RefreshCw },
  refunded: { label: 'Refunded', color: 'bg-gray-500', textColor: 'text-gray-700', bgColor: 'bg-gray-50', icon: RefreshCw },
};

const PreAssessmentPipeline = () => {
  const [assessments, setAssessments] = useState([]);
  const [stats, setStats] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [filterStage, setFilterStage] = useState('all');
  const [search, setSearch] = useState('');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Create form state
  const [form, setForm] = useState({
    client_name: '', client_email: '', client_mobile: '', country: '',
    service_type: '', product_id: '', notes: '', client_age: 0,
    education: '', work_experience: ''
  });
  const [proposalForm, setProposalForm] = useState({ fee_amount: '', notes: '' });
  const [showProposal, setShowProposal] = useState(null);
  const [uploading, setUploading] = useState(false);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const [aRes, sRes, pRes] = await Promise.all([
        axios.get(`${API}/pre-assessment/my-assessments`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/stats/overview`, getAuthHeader()),
        axios.get(`${API}/products`, getAuthHeader()),
      ]);
      setAssessments(aRes.data || []);
      setStats(sRes.data || {});
      setProducts(pRes.data || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!form.client_name || !form.client_email || !form.country || !form.service_type) {
      toast.error('Please fill required fields'); return;
    }
    try {
      await axios.post(`${API}/pre-assessment/create`, {
        ...form, client_age: parseInt(form.client_age) || 0
      }, getAuthHeader());
      toast.success('Pre-assessment created!');
      setShowCreate(false);
      setForm({ client_name: '', client_email: '', client_mobile: '', country: '', service_type: '', product_id: '', notes: '', client_age: 0, education: '', work_experience: '' });
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to create'); }
  };

  const handleSendPayment = async (paId) => {
    try {
      // Generate public share-token link (new client-facing flow)
      const res = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: paId }, getAuthHeader());
      const publicUrl = res.data.public_url;
      try { await navigator.clipboard.writeText(publicUrl); } catch (_) { /* ignore */ }
      toast.success('Public payment link generated & copied to clipboard');
      window.open(publicUrl, '_blank');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to generate link');
    }
  };

  const handleCopyPublicLink = async (paId) => {
    try {
      const res = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: paId }, getAuthHeader());
      await navigator.clipboard.writeText(res.data.public_url);
      toast.success('Public payment link copied — share via WhatsApp/Email');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  const handleConfirmPayment = async (paId) => {
    try {
      await axios.post(`${API}/pre-assessment/${paId}/confirm-payment`, {}, getAuthHeader());
      toast.success('Payment confirmed!');
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleSubmitDocs = async (paId) => {
    try {
      const formData = new FormData();
      formData.append('remarks', 'Documents ready for review');
      await axios.post(`${API}/pre-assessment/${paId}/submit-documents`, formData, getAuthHeader());
      toast.success('Submitted to admin for review!');
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleUploadDoc = async (paId, file, docType) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('document_type', docType);
      await axios.post(`${API}/pre-assessment/${paId}/upload-document`, fd, getAuthHeader());
      toast.success('Document uploaded!');
      loadData();
    } catch (e) { toast.error('Upload failed'); }
    setUploading(false);
  };

  const handleSendProposal = async (paId) => {
    if (!proposalForm.fee_amount || parseFloat(proposalForm.fee_amount) <= 0) {
      toast.error('Enter valid fee amount'); return;
    }
    try {
      const res = await axios.post(`${API}/pre-assessment/${paId}/send-proposal`, {
        fee_amount: parseFloat(proposalForm.fee_amount),
        payment_method: 'online', notes: proposalForm.notes, currency: 'INR'
      }, getAuthHeader());
      toast.success(res.data.message);
      setShowProposal(null);
      setProposalForm({ fee_amount: '', notes: '' });
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const filtered = assessments.filter(a =>
    (filterStage === 'all' || a.stage === filterStage) &&
    (!search || a.client_name?.toLowerCase().includes(search.toLowerCase()) || a.pa_number?.toLowerCase().includes(search.toLowerCase()))
  );

  const getStageInfo = (stage) => STAGE_CONFIG[stage] || STAGE_CONFIG.new;

  const getNextAction = (pa) => {
    switch (pa.stage) {
      case 'new': return { label: 'Send Payment Link (₹5,100)', action: () => handleSendPayment(pa.id), color: 'bg-amber-500 hover:bg-amber-600' };
      case 'payment_pending': return { label: 'Confirm Payment Received', action: () => handleConfirmPayment(pa.id), color: 'bg-blue-500 hover:bg-blue-600' };
      case 'payment_received': return { label: 'Submit to Admin for Review', action: () => handleSubmitDocs(pa.id), color: 'bg-purple-500 hover:bg-purple-600' };
      case 'approved': return { label: 'Send Proposal to Client', action: () => setShowProposal(pa.id), color: 'bg-emerald-500 hover:bg-emerald-600' };
      default: return null;
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="pre-assessment-pipeline">
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Total', value: stats.total || 0, color: 'from-slate-500 to-slate-600' },
          { label: 'Under Review', value: stats.under_review || 0, color: 'from-purple-500 to-purple-600' },
          { label: 'Approved', value: stats.approved || 0, color: 'from-emerald-500 to-emerald-600' },
          { label: 'Proposals Sent', value: stats.proposal_sent || 0, color: 'from-teal-500 to-teal-600' },
          { label: 'Conversion', value: `${stats.conversion_rate || 0}%`, color: 'from-[#2a777a] to-[#236466]' },
        ].map((s, i) => (
          <Card key={i} className={`bg-gradient-to-br ${s.color} text-white p-4 border-0 shadow-lg`}>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-white/80">{s.label}</p>
          </Card>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => setShowCreate(true)} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="create-pa-btn">
          <Plus className="h-4 w-4 mr-2" /> New Pre-Assessment
        </Button>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input placeholder="Search by name or PA number..." value={search}
            onChange={e => setSearch(e.target.value)} className="pl-9" data-testid="search-pa" />
        </div>
        <select value={filterStage} onChange={e => setFilterStage(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white" data-testid="filter-stage">
          <option value="all">All Stages</option>
          {Object.entries(STAGE_CONFIG).map(([key, val]) => (
            <option key={key} value={key}>{val.label}</option>
          ))}
        </select>
      </div>

      {/* Create Form Modal */}
      {showCreate && (
        <Card className="p-6 bg-white shadow-xl border-0 border-l-4 border-l-[#2a777a]">
          <h3 className="text-lg font-bold text-slate-800 mb-4">New Pre-Assessment</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Client Name *</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input value={form.client_name} onChange={e => setForm({...form, client_name: e.target.value})} className="pl-9" placeholder="Full name" data-testid="pa-client-name" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Email *</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input type="email" value={form.client_email} onChange={e => setForm({...form, client_email: e.target.value})} className="pl-9" placeholder="email@example.com" data-testid="pa-client-email" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Mobile</label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input value={form.client_mobile} onChange={e => setForm({...form, client_mobile: e.target.value})} className="pl-9" placeholder="+91-XXXXXXXXXX" data-testid="pa-client-mobile" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Country *</label>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input value={form.country} onChange={e => setForm({...form, country: e.target.value})} className="pl-9" placeholder="Canada, Australia..." data-testid="pa-country" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Service Type *</label>
              <Input value={form.service_type} onChange={e => setForm({...form, service_type: e.target.value})} placeholder="PR, Work Visa, Study..." data-testid="pa-service-type" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Product</label>
              <select value={form.product_id} onChange={e => setForm({...form, product_id: e.target.value})}
                className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm" data-testid="pa-product">
                <option value="">Select product</option>
                {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Age</label>
              <Input type="number" value={form.client_age} onChange={e => setForm({...form, client_age: e.target.value})} placeholder="28" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Education</label>
              <div className="relative">
                <GraduationCap className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input value={form.education} onChange={e => setForm({...form, education: e.target.value})} className="pl-9" placeholder="Bachelor's, Master's..." />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1">Work Experience</label>
              <div className="relative">
                <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input value={form.work_experience} onChange={e => setForm({...form, work_experience: e.target.value})} className="pl-9" placeholder="5 years IT..." />
              </div>
            </div>
          </div>
          <div className="mt-4">
            <label className="text-sm font-medium text-slate-700 block mb-1">Notes</label>
            <textarea value={form.notes} onChange={e => setForm({...form, notes: e.target.value})}
              className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm h-20" placeholder="Additional notes..." />
          </div>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="submit-create-pa">Create Pre-Assessment</Button>
          </div>
        </Card>
      )}

      {/* Pipeline Cards */}
      {filtered.length === 0 ? (
        <Card className="p-12 text-center bg-white border-0 shadow-md">
          <FileText className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No pre-assessments found</p>
          <Button onClick={() => setShowCreate(true)} className="mt-3 bg-[#2a777a] hover:bg-[#236466]">Create First Pre-Assessment</Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(pa => {
            const stageInfo = getStageInfo(pa.stage);
            const StageIcon = stageInfo.icon;
            const isExpanded = expandedId === pa.id;
            const nextAction = getNextAction(pa);

            return (
              <Card key={pa.id} className="bg-white border-0 shadow-md overflow-hidden hover:shadow-lg transition-shadow" data-testid={`pa-card-${pa.id}`}>
                <div className="flex items-center gap-4 p-4 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : pa.id)}>
                  <div className={`w-10 h-10 ${stageInfo.color} rounded-full flex items-center justify-center flex-shrink-0`}>
                    <StageIcon className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-slate-800">{pa.client_name}</p>
                      <Badge className="bg-slate-100 text-slate-600 text-xs">{pa.pa_number}</Badge>
                    </div>
                    <p className="text-sm text-slate-500">{pa.country} — {pa.service_type} {pa.product_name ? `(${pa.product_name})` : ''}</p>
                  </div>
                  <Badge className={`${stageInfo.bgColor} ${stageInfo.textColor} border-0`}>{stageInfo.label}</Badge>
                  <p className="text-xs text-slate-400 hidden md:block">{pa.created_at ? new Date(pa.created_at).toLocaleDateString() : ''}</p>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                </div>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-slate-100 pt-4 space-y-4">
                    {/* Client Info */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div><span className="text-slate-500">Email:</span> <span className="font-medium">{pa.client_email}</span></div>
                      <div><span className="text-slate-500">Mobile:</span> <span className="font-medium">{pa.client_mobile || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Age:</span> <span className="font-medium">{pa.client_age || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Education:</span> <span className="font-medium">{pa.education || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Experience:</span> <span className="font-medium">{pa.work_experience || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Payment:</span> <Badge className={pa.fee_payment_status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>{pa.fee_payment_status === 'paid' ? '₹5,100 Paid' : 'Unpaid'}</Badge></div>
                      <div><span className="text-slate-500">Docs:</span> <span className="font-medium">{pa.documents_count || 0} uploaded</span></div>
                      {pa.admin_decision && (
                        <div><span className="text-slate-500">Decision:</span> <Badge className={pa.admin_decision === 'approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{pa.admin_decision}</Badge></div>
                      )}
                    </div>

                    {pa.admin_reason && (
                      <div className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs font-semibold text-slate-600 mb-1">Admin Review Notes:</p>
                        <p className="text-sm text-slate-700">{pa.admin_reason}</p>
                      </div>
                    )}

                    {/* Document Upload (when payment_received) */}
                    {pa.stage === 'payment_received' && (
                      <div className="bg-blue-50 rounded-lg p-4">
                        <p className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
                          <Upload className="h-4 w-4" /> Upload Documents for Review
                        </p>
                        <div className="flex items-center gap-3">
                          <select id={`docType-${pa.id}`} className="border border-blue-200 rounded-md px-3 py-2 text-sm bg-white">
                            <option value="passport">Passport</option>
                            <option value="ielts">IELTS/Language Test</option>
                            <option value="education">Education Certificate</option>
                            <option value="experience">Work Experience Letter</option>
                            <option value="financial">Financial Documents</option>
                            <option value="other">Other</option>
                          </select>
                          <Input type="file" className="flex-1" id={`fileInput-${pa.id}`}
                            onChange={async (e) => {
                              const file = e.target.files[0];
                              if (file) {
                                const docType = document.getElementById(`docType-${pa.id}`).value;
                                await handleUploadDoc(pa.id, file, docType);
                              }
                            }} />
                        </div>
                      </div>
                    )}

                    {/* Proposal Form (when approved) */}
                    {showProposal === pa.id && (
                      <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                        <p className="text-sm font-semibold text-emerald-800 mb-3 flex items-center gap-2">
                          <IndianRupee className="h-4 w-4" /> Send Service Proposal
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="text-xs font-medium text-slate-600 block mb-1">Service Fee (INR) *</label>
                            <Input type="number" value={proposalForm.fee_amount}
                              onChange={e => setProposalForm({...proposalForm, fee_amount: e.target.value})}
                              placeholder="150000" data-testid="proposal-fee" />
                          </div>
                          <div>
                            <label className="text-xs font-medium text-slate-600 block mb-1">Notes</label>
                            <Input value={proposalForm.notes}
                              onChange={e => setProposalForm({...proposalForm, notes: e.target.value})}
                              placeholder="Canada PR Express Entry..." />
                          </div>
                        </div>
                        <div className="flex justify-end gap-2 mt-3">
                          <Button variant="outline" size="sm" onClick={() => setShowProposal(null)}>Cancel</Button>
                          <Button size="sm" onClick={() => handleSendProposal(pa.id)}
                            className="bg-emerald-600 hover:bg-emerald-700" data-testid="submit-proposal">
                            <Send className="h-4 w-4 mr-1" /> Send Proposal with Payment Link
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Next Action Button */}
                    {nextAction && showProposal !== pa.id && (
                      <div className="flex justify-end gap-2">
                        {['new', 'payment_pending'].includes(pa.stage) && (
                          <Button variant="outline" size="sm" onClick={() => handleCopyPublicLink(pa.id)} data-testid={`copy-link-${pa.id}`}>
                            <Send className="h-4 w-4 mr-1" /> Copy Public Link
                          </Button>
                        )}
                        <Button onClick={nextAction.action} className={`${nextAction.color} text-white`} data-testid={`action-${pa.stage}`}>
                          <ArrowRight className="h-4 w-4 mr-2" /> {nextAction.label}
                        </Button>
                      </div>
                    )}

                    {/* Stage Progress Indicator */}
                    <div className="flex items-center gap-1 overflow-x-auto py-2">
                      {['new', 'payment_pending', 'payment_received', 'under_review', 'approved', 'proposal_sent', 'case_created'].map((stage, idx) => {
                        const isCurrent = pa.stage === stage;
                        const isPast = ['new', 'payment_pending', 'payment_received', 'under_review', 'approved', 'proposal_sent', 'case_created'].indexOf(pa.stage) > idx;
                        const isRejected = pa.stage === 'rejected' || pa.stage === 'refund_initiated' || pa.stage === 'refunded';
                        return (
                          <div key={stage} className="flex items-center">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                              isPast ? 'bg-emerald-500 text-white' : isCurrent ? 'bg-[#2a777a] text-white ring-2 ring-[#2a777a]/20' : 'bg-slate-200 text-slate-400'
                            }`}>{isPast ? '✓' : idx + 1}</div>
                            {idx < 6 && <div className={`w-6 h-0.5 ${isPast ? 'bg-emerald-300' : 'bg-slate-200'}`} />}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PreAssessmentPipeline;
