import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  CheckCircle, XCircle, Eye, FileText, User, Globe, 
  GraduationCap, Briefcase, Clock, CreditCard, Download,
  ChevronDown, ChevronUp, AlertTriangle, RefreshCw, IndianRupee,
  Sparkles, UserCog
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PreAssessmentQueue = ({ initialFilter = null }) => {
  const [queue, setQueue] = useState([]);
  const [allAssessments, setAllAssessments] = useState([]);
  const [stats, setStats] = useState({});
  const [expandedId, setExpandedId] = useState(null);
  const [reviewForm, setReviewForm] = useState({ decision: '', reason: '', notes: '' });
  const [reviewingId, setReviewingId] = useState(null);
  const [activeView, setActiveView] = useState('queue'); // queue | all | proposal_paid | under_review
  const [loading, setLoading] = useState(true);
  const [caseManagers, setCaseManagers] = useState([]);
  const [finalizingId, setFinalizingId] = useState(null);
  const [selectedCmId, setSelectedCmId] = useState('');

  // Apply initialFilter on mount or when it changes
  useEffect(() => {
    if (initialFilter === 'first_approval') setActiveView('under_review');
    else if (initialFilter === 'second_approval') setActiveView('proposal_paid');
    else if (initialFilter === 'all') setActiveView('all');
  }, [initialFilter]);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const [qRes, aRes, sRes, cmRes] = await Promise.all([
        axios.get(`${API}/pre-assessment/admin/queue`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/my-assessments`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/stats/overview`, getAuthHeader()),
        axios.get(`${API}/pre-assess-portal/admin/case-managers`, getAuthHeader()).catch(() => ({ data: { case_managers: [] } })),
      ]);
      setQueue(qRes.data || []);
      setAllAssessments(aRes.data || []);
      setStats(sRes.data || {});
      setCaseManagers(cmRes.data?.case_managers || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Admin "Preview as Client" — opens public payment page for unpaid PAs OR MiniPortal preview for paid ones
  const handlePreviewAsClient = async (pa) => {
    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` };
      // Unpaid → open public payment page (what client sees BEFORE paying)
      if (['new', 'payment_pending'].includes(pa.stage) || pa.fee_payment_status !== 'paid') {
        const r = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: pa.id }, { headers });
        const url = r.data.public_url?.startsWith('http')
          ? r.data.public_url
          : `${window.location.origin}${r.data.public_url}`;
        window.open(url, '_blank');
        toast.success('Opening public payment page (what client sees before paying)');
        return;
      }
      // Paid → open MiniPortal magic link (what client sees after paying)
      const r = await axios.post(`${API}/pre-assess-portal/partner/preview-magic/${pa.id}`, {}, { headers });
      if (r.data.portal_url) {
        const url = r.data.portal_url.startsWith('http')
          ? r.data.portal_url
          : `${window.location.origin}${r.data.portal_url}`;
        window.open(url, '_blank');
        toast.success('Opening client portal preview in new tab');
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Preview failed');
    }
  };

  const handleReview = async (paId) => {
    if (!reviewForm.decision) { toast.error('Select a decision'); return; }
    if (!reviewForm.reason) { toast.error('Please provide a reason'); return; }
    // Optimistic UI: immediately update the card stage so user sees zero-lag feedback.
    const decisionStage = reviewForm.decision === 'approved' ? 'approved' : 'rejected';
    const snapshot = { queue: [...queue], allAssessments: [...allAssessments] };
    const updateLocally = (list) => list.map(p => p.id === paId ? { ...p, stage: decisionStage, admin_decision: reviewForm.decision, admin_reason: reviewForm.reason } : p);
    setQueue(updateLocally);
    setAllAssessments(updateLocally);
    setReviewingId(null);
    const formCopy = { ...reviewForm };
    setReviewForm({ decision: '', reason: '', notes: '' });
    try {
      await axios.put(`${API}/pre-assessment/${paId}/review`, formCopy, getAuthHeader());
      toast.success(`Pre-assessment ${formCopy.decision}!`);
      loadData();
    } catch (e) {
      // Rollback on failure
      setQueue(snapshot.queue);
      setAllAssessments(snapshot.allAssessments);
      toast.error(e.response?.data?.detail || 'Failed — reverted');
    }
  };

  const handleApproveFinal = async (paId) => {
    // Optimistic: stage → case_created
    const snapshot = { queue: [...queue], allAssessments: [...allAssessments] };
    const updateLocally = (list) => list.map(p => p.id === paId ? { ...p, stage: 'case_created' } : p);
    setQueue(updateLocally);
    setAllAssessments(updateLocally);
    setFinalizingId(null);
    const cmId = selectedCmId;
    setSelectedCmId('');
    try {
      const payload = cmId ? { case_manager_id: cmId } : {};
      const res = await axios.post(`${API}/pre-assess-portal/admin/approve-final/${paId}`, payload, getAuthHeader());
      toast.success(`Case ${res.data.case_code} created${res.data.case_manager_id ? ` & assigned to ${res.data.case_manager_name}` : ''}!`);
      loadData();
    } catch (e) {
      setQueue(snapshot.queue);
      setAllAssessments(snapshot.allAssessments);
      toast.error(e.response?.data?.detail || 'Failed — reverted');
    }
  };

  const underReviewItems = [
    ...queue.filter(p => ['under_review', 'documents_submitted'].includes(p.stage)),
    // include history (admin's past decisions) so approved items remain visible in this tab
    ...allAssessments.filter(p => ['approved', 'rejected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'].includes(p.stage)),
  ];
  const proposalPaidItems = queue.filter(p => ['proposal_paid', 'awaiting_final_approval'].includes(p.stage));
  const items = (
    activeView === 'queue' ? queue :
    activeView === 'under_review' ? underReviewItems :
    activeView === 'proposal_paid' ? proposalPaidItems :
    allAssessments
  );

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="pre-assessment-queue">
      {/* Filter context banner */}
      {(activeView === 'under_review' || activeView === 'proposal_paid') && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-amber-800">
            <span className="font-semibold">Filter active:</span>{' '}
            {activeView === 'under_review' ? 'Showing items needing 1st Approval (eligibility review)' : 'Showing items needing 2nd Approval (create case & assign CM)'}
          </p>
          <Button variant="ghost" size="sm" onClick={() => setActiveView('queue')} data-testid="clear-filter">
            <XCircle className="h-4 w-4 mr-1" /> Clear filter
          </Button>
        </div>
      )}

      {/* Stats — clickable for filter */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: 'Total', value: stats.total || 0, color: 'from-slate-500 to-slate-600', click: () => setActiveView('all') },
          { label: '1st Review', value: stats.under_review || 0, color: 'from-leamss-orange-500 to-leamss-orange-600', click: () => setActiveView('under_review') },
          { label: 'Approved', value: stats.approved || 0, color: 'from-emerald-500 to-emerald-600', click: () => setActiveView('all') },
          { label: 'Rejected', value: stats.rejected || 0, color: 'from-red-500 to-red-600', click: () => setActiveView('all') },
          { label: 'Awaiting Case', value: proposalPaidItems.length || 0, color: 'from-[#f7620b] to-[#e55a09]', click: () => setActiveView('proposal_paid') },
          { label: 'Conversion', value: `${stats.conversion_rate || 0}%`, color: 'from-[#2a777a] to-[#236466]' },
        ].map((s, i) => (
          <Card key={i} onClick={s.click} className={`bg-gradient-to-br ${s.color} text-white p-4 border-0 shadow-lg ${s.click ? 'cursor-pointer hover:shadow-xl hover:-translate-y-0.5 transition-all' : ''}`}>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-white/80">{s.label}</p>
          </Card>
        ))}
      </div>

      {/* View Toggle */}
      <div className="flex gap-2 flex-wrap">
        <Button variant={activeView === 'queue' ? 'default' : 'outline'} onClick={() => setActiveView('queue')}
          className={activeView === 'queue' ? 'bg-[#2a777a]' : ''} data-testid="view-queue">
          <Eye className="h-4 w-4 mr-2" /> Pending Review ({queue.length})
        </Button>
        <Button variant={activeView === 'under_review' ? 'default' : 'outline'} onClick={() => setActiveView('under_review')}
          className={activeView === 'under_review' ? 'bg-leamss-orange-600' : ''} data-testid="view-first-approval">
          1st Approval ({underReviewItems.length})
        </Button>
        <Button variant={activeView === 'proposal_paid' ? 'default' : 'outline'} onClick={() => setActiveView('proposal_paid')}
          className={activeView === 'proposal_paid' ? 'bg-[#f7620b]' : ''} data-testid="view-second-approval">
          2nd Approval ({proposalPaidItems.length})
        </Button>
        <Button variant={activeView === 'all' ? 'default' : 'outline'} onClick={() => setActiveView('all')}
          className={activeView === 'all' ? 'bg-[#2a777a]' : ''} data-testid="view-all">
          All Pre-Assessments ({allAssessments.length})
        </Button>
      </div>

      {/* Queue List */}
      {items.length === 0 ? (
        <Card className="p-12 text-center bg-white border-0 shadow-md">
          <CheckCircle className="h-12 w-12 text-emerald-300 mx-auto mb-3" />
          <p className="text-slate-500 font-medium">{activeView === 'queue' ? 'No pending reviews! All caught up.' : 'No pre-assessments yet.'}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map(pa => {
            const isExpanded = expandedId === pa.id;
            const isReviewing = reviewingId === pa.id;
            const stageColors = {
              under_review: 'border-l-leamss-orange-500 bg-leamss-orange-50/30',
              documents_submitted: 'border-l-leamss-teal-500 bg-leamss-teal-50/30',
              approved: 'border-l-emerald-500 bg-emerald-50/30',
              rejected: 'border-l-red-500 bg-red-50/30',
              proposal_sent: 'border-l-teal-500 bg-teal-50/30',
              proposal_paid: 'border-l-[#f7620b] bg-orange-50/30',
              awaiting_final_approval: 'border-l-leamss-teal-600 bg-leamss-teal-50/30',
              case_created: 'border-l-green-600 bg-green-50/30',
            };

            return (
              <Card key={pa.id} className={`border-0 shadow-md overflow-hidden border-l-4 ${stageColors[pa.stage] || 'border-l-slate-300'}`} data-testid={`queue-item-${pa.id}`}>
                <div className="flex items-center gap-4 p-4 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : pa.id)}>
                  <div className="w-12 h-12 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-lg font-bold flex-shrink-0">
                    {(pa.client_name || 'C')[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-slate-800">{pa.client_name}</p>
                      <Badge className="bg-slate-100 text-slate-600 text-xs">{pa.pa_number}</Badge>
                    </div>
                    <p className="text-sm text-slate-500">
                      {pa.country} — {pa.service_type} {pa.product_name ? `| ${pa.product_name}` : ''}
                    </p>
                    <p className="text-xs text-slate-400">Partner: {pa.partner_name} | {pa.created_at ? new Date(pa.created_at).toLocaleDateString() : ''}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={
                      pa.stage === 'under_review' ? 'bg-leamss-orange-100 text-leamss-orange-700' :
                      pa.stage === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                      pa.stage === 'rejected' ? 'bg-red-100 text-red-700' :
                      pa.stage === 'proposal_sent' ? 'bg-teal-100 text-teal-700' :
                      pa.stage === 'proposal_paid' ? 'bg-orange-100 text-orange-700' :
                      pa.stage === 'awaiting_final_approval' ? 'bg-leamss-teal-100 text-leamss-teal-700' :
                      pa.stage === 'case_created' ? 'bg-green-100 text-green-700' :
                      'bg-slate-100 text-slate-700'
                    }>{pa.stage?.replace(/_/g, ' ').toUpperCase()}</Badge>
                    {pa.documents?.length > 0 && (
                      <Badge variant="outline" className="text-xs">{pa.documents.length} docs</Badge>
                    )}
                  </div>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                </div>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-slate-100 pt-4 space-y-4">
                    {/* Client Details */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { icon: Mail, label: 'Email', value: pa.client_email },
                        { icon: User, label: 'Mobile', value: pa.client_mobile || 'N/A' },
                        { icon: GraduationCap, label: 'Education', value: pa.education || 'N/A' },
                        { icon: Briefcase, label: 'Experience', value: pa.work_experience || 'N/A' },
                        { icon: Clock, label: 'Age', value: pa.client_age || 'N/A' },
                        { icon: Globe, label: 'Country', value: pa.country },
                        { icon: CreditCard, label: 'Pre-Assessment Fee', value: pa.fee_payment_status === 'paid' ? '₹5,100 Paid' : 'Unpaid' },
                        { icon: FileText, label: 'Documents', value: `${pa.documents?.length || pa.documents_count || 0} uploaded` },
                      ].map((item, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <item.icon className="h-4 w-4 text-slate-400 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-slate-500">{item.label}</p>
                            <p className="font-medium text-slate-700">{item.value}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {pa.notes && (
                      <div className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs font-semibold text-slate-600">Partner Notes:</p>
                        <p className="text-sm text-slate-700">{pa.notes}</p>
                      </div>
                    )}

                    {/* Documents List with View/Download */}
                    {pa.documents?.length > 0 && (
                      <div>
                        <p className="text-sm font-semibold text-slate-700 mb-2">Submitted Documents ({pa.documents.length}):</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {pa.documents.map((doc, di) => {
                            const dlUrl = `${API}/pre-assessment/${pa.id}/document/${doc.id}/download`;
                            const tok = localStorage.getItem('token');
                            const handleView = async () => {
                              try {
                                const r = await fetch(`${dlUrl}?inline=true`, { headers: { Authorization: `Bearer ${tok}` } });
                                if (!r.ok) throw new Error();
                                const blob = await r.blob();
                                const url = URL.createObjectURL(blob);
                                window.open(url, '_blank');
                              } catch { toast.error('View failed'); }
                            };
                            const handleDownload = async () => {
                              try {
                                const r = await fetch(dlUrl, { headers: { Authorization: `Bearer ${tok}` } });
                                if (!r.ok) throw new Error();
                                const blob = await r.blob();
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url; a.download = doc.file_name;
                                document.body.appendChild(a); a.click(); a.remove();
                                URL.revokeObjectURL(url);
                              } catch { toast.error('Download failed'); }
                            };
                            return (
                              <div key={di} className="flex items-center gap-2 bg-slate-50 rounded-lg p-3 border border-slate-200">
                                <FileText className="h-4 w-4 text-blue-500 flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-slate-700 truncate">{doc.file_name}</p>
                                  <p className="text-xs text-slate-500 capitalize">{doc.document_type}</p>
                                </div>
                                <Button size="sm" variant="outline" onClick={handleView} className="h-7 text-xs" data-testid={`admin-view-doc-${doc.id}`}>
                                  <Eye className="h-3.5 w-3.5 mr-1" /> View
                                </Button>
                                <Button size="sm" variant="outline" onClick={handleDownload} className="h-7 text-xs" data-testid={`admin-download-doc-${doc.id}`}>
                                  <Download className="h-3.5 w-3.5 mr-1" /> Save
                                </Button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Admin can preview the PA as the client will see it (public payment page for unpaid, MiniPortal for paid) */}
                    <div className="flex justify-end gap-3 -mt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-leamss-teal-300 text-leamss-teal-700 hover:bg-leamss-teal-50"
                        onClick={() => handlePreviewAsClient(pa)}
                        data-testid={`preview-as-client-${pa.id}`}
                      >
                        <Eye className="h-4 w-4 mr-1.5" /> Preview as Client
                      </Button>
                    </div>

                    {/* Review Form - Only show for pending items */}
                    {(pa.stage === 'under_review' || pa.stage === 'documents_submitted') && (
                      <>
                        {!isReviewing ? (
                          <div className="flex justify-end gap-3">
                            <Button onClick={() => { setReviewingId(pa.id); setReviewForm({ decision: 'rejected', reason: '', notes: '' }); }}
                              variant="outline" className="border-red-300 text-red-600 hover:bg-red-50" data-testid="reject-btn">
                              <XCircle className="h-4 w-4 mr-2" /> Reject
                            </Button>
                            <Button onClick={() => { setReviewingId(pa.id); setReviewForm({ decision: 'approved', reason: '', notes: '' }); }}
                              className="bg-emerald-600 hover:bg-emerald-700" data-testid="approve-btn">
                              <CheckCircle className="h-4 w-4 mr-2" /> Approve
                            </Button>
                          </div>
                        ) : (
                          <div className={`rounded-lg p-4 border ${reviewForm.decision === 'approved' ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                            <h4 className={`font-semibold mb-3 ${reviewForm.decision === 'approved' ? 'text-emerald-800' : 'text-red-800'}`}>
                              {reviewForm.decision === 'approved' ? 'Approve Eligibility' : 'Reject — Not Eligible'}
                            </h4>
                            <div className="space-y-3">
                              <div>
                                <label className="text-sm font-medium text-slate-700 block mb-1">Reason *</label>
                                <textarea value={reviewForm.reason} onChange={e => setReviewForm({...reviewForm, reason: e.target.value})}
                                  className="w-full border rounded-md px-3 py-2 text-sm h-20" placeholder={
                                    reviewForm.decision === 'approved' ? 'Client meets all eligibility criteria...' : 'Client does not meet criteria because...'
                                  } data-testid="review-reason" />
                              </div>
                              <div>
                                <label className="text-sm font-medium text-slate-700 block mb-1">Internal Notes</label>
                                <textarea value={reviewForm.notes} onChange={e => setReviewForm({...reviewForm, notes: e.target.value})}
                                  className="w-full border rounded-md px-3 py-2 text-sm h-16" placeholder="Internal notes..." />
                              </div>
                              <div className="flex justify-end gap-2">
                                <Button variant="outline" size="sm" onClick={() => setReviewingId(null)}>Cancel</Button>
                                <Button size="sm" onClick={() => handleReview(pa.id)}
                                  className={reviewForm.decision === 'approved' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                                  data-testid="submit-review">
                                  Confirm {reviewForm.decision === 'approved' ? 'Approval' : 'Rejection'}
                                </Button>
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    )}

                    {/* 2ND APPROVAL: Create Case & Assign CM (for awaiting_final_approval / proposal_paid stage) */}
                    {['awaiting_final_approval', 'proposal_paid'].includes(pa.stage) && (
                      <div className="rounded-lg p-4 border bg-gradient-to-br from-[#f7620b]/10 to-[#2a777a]/5 border-[#f7620b]/30">
                        <div className="flex items-start gap-3 mb-3">
                          <div className="w-10 h-10 bg-[#f7620b] rounded-lg flex items-center justify-center flex-shrink-0">
                            <Sparkles className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-bold text-slate-800">Main Fee Received — Create Case</h4>
                            <p className="text-sm text-slate-600 mt-0.5">
                              Client paid ₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}. Activate case and optionally assign a Case Manager.
                            </p>
                          </div>
                        </div>
                        {finalizingId !== pa.id ? (
                          <div className="flex justify-end">
                            <Button onClick={() => { setFinalizingId(pa.id); setSelectedCmId(''); }}
                              className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="finalize-btn">
                              <Sparkles className="h-4 w-4 mr-2" /> Activate Case & Assign CM
                            </Button>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div>
                              <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5 mb-1">
                                <UserCog className="h-4 w-4" /> Assign Case Manager (optional)
                              </label>
                              <select value={selectedCmId} onChange={e => setSelectedCmId(e.target.value)}
                                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm bg-white" data-testid="cm-select">
                                <option value="">— Leave unassigned (assign later) —</option>
                                {caseManagers.map(cm => (
                                  <option key={cm.id} value={cm.id}>{cm.name} ({cm.email})</option>
                                ))}
                              </select>
                              {caseManagers.length === 0 && (
                                <p className="text-xs text-amber-600 mt-1">No case managers found — add one from Users admin first.</p>
                              )}
                            </div>
                            <div className="flex justify-end gap-2">
                              <Button variant="outline" size="sm" onClick={() => { setFinalizingId(null); setSelectedCmId(''); }}>Cancel</Button>
                              <Button size="sm" onClick={() => handleApproveFinal(pa.id)}
                                className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="confirm-finalize">
                                <CheckCircle className="h-4 w-4 mr-1.5" /> Confirm — Create Case
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Already reviewed info */}
                    {pa.admin_decision && (
                      <div className={`rounded-lg p-4 ${pa.admin_decision === 'approved' ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          {pa.admin_decision === 'approved' ?
                            <CheckCircle className="h-5 w-5 text-emerald-600" /> :
                            <XCircle className="h-5 w-5 text-red-600" />
                          }
                          <p className={`font-semibold ${pa.admin_decision === 'approved' ? 'text-emerald-800' : 'text-red-800'}`}>
                            {pa.admin_decision === 'approved' ? 'Approved' : 'Rejected'}
                          </p>
                          <span className="text-xs text-slate-500 ml-auto">{pa.admin_reviewed_at ? new Date(pa.admin_reviewed_at).toLocaleString() : ''}</span>
                        </div>
                        {pa.admin_reason && <p className="text-sm text-slate-700">{pa.admin_reason}</p>}
                      </div>
                    )}
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

const Mail = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>;

export default PreAssessmentQueue;
