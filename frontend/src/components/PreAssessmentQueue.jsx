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

const PreAssessmentQueue = () => {
  const [queue, setQueue] = useState([]);
  const [allAssessments, setAllAssessments] = useState([]);
  const [stats, setStats] = useState({});
  const [expandedId, setExpandedId] = useState(null);
  const [reviewForm, setReviewForm] = useState({ decision: '', reason: '', notes: '' });
  const [reviewingId, setReviewingId] = useState(null);
  const [activeView, setActiveView] = useState('queue'); // queue | all
  const [loading, setLoading] = useState(true);
  const [caseManagers, setCaseManagers] = useState([]);
  const [finalizingId, setFinalizingId] = useState(null);
  const [selectedCmId, setSelectedCmId] = useState('');

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

  const handleReview = async (paId) => {
    if (!reviewForm.decision) { toast.error('Select a decision'); return; }
    if (!reviewForm.reason) { toast.error('Please provide a reason'); return; }
    try {
      await axios.put(`${API}/pre-assessment/${paId}/review`, reviewForm, getAuthHeader());
      toast.success(`Pre-assessment ${reviewForm.decision}!`);
      setReviewingId(null);
      setReviewForm({ decision: '', reason: '', notes: '' });
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleApproveFinal = async (paId) => {
    try {
      const payload = selectedCmId ? { case_manager_id: selectedCmId } : {};
      const res = await axios.post(`${API}/pre-assess-portal/admin/approve-final/${paId}`, payload, getAuthHeader());
      toast.success(`Case ${res.data.case_code} created${res.data.case_manager_id ? ` & assigned to ${res.data.case_manager_name}` : ''}!`);
      setFinalizingId(null);
      setSelectedCmId('');
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const items = activeView === 'queue' ? queue : allAssessments;

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="pre-assessment-queue">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: 'Total', value: stats.total || 0, color: 'from-slate-500 to-slate-600' },
          { label: '1st Review', value: stats.under_review || 0, color: 'from-purple-500 to-purple-600' },
          { label: 'Approved', value: stats.approved || 0, color: 'from-emerald-500 to-emerald-600' },
          { label: 'Rejected', value: stats.rejected || 0, color: 'from-red-500 to-red-600' },
          { label: 'Awaiting Case', value: queue.filter(p => p.stage === 'proposal_paid').length || 0, color: 'from-[#f7620b] to-[#e55a09]' },
          { label: 'Conversion', value: `${stats.conversion_rate || 0}%`, color: 'from-[#2a777a] to-[#236466]' },
        ].map((s, i) => (
          <Card key={i} className={`bg-gradient-to-br ${s.color} text-white p-4 border-0 shadow-lg`}>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-white/80">{s.label}</p>
          </Card>
        ))}
      </div>

      {/* View Toggle */}
      <div className="flex gap-2">
        <Button variant={activeView === 'queue' ? 'default' : 'outline'} onClick={() => setActiveView('queue')}
          className={activeView === 'queue' ? 'bg-[#2a777a]' : ''} data-testid="view-queue">
          <Eye className="h-4 w-4 mr-2" /> Pending Review ({queue.length})
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
              under_review: 'border-l-purple-500 bg-purple-50/30',
              documents_submitted: 'border-l-indigo-500 bg-indigo-50/30',
              approved: 'border-l-emerald-500 bg-emerald-50/30',
              rejected: 'border-l-red-500 bg-red-50/30',
              proposal_sent: 'border-l-teal-500 bg-teal-50/30',
              proposal_paid: 'border-l-[#f7620b] bg-orange-50/30',
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
                      pa.stage === 'under_review' ? 'bg-purple-100 text-purple-700' :
                      pa.stage === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                      pa.stage === 'rejected' ? 'bg-red-100 text-red-700' :
                      pa.stage === 'proposal_sent' ? 'bg-teal-100 text-teal-700' :
                      pa.stage === 'proposal_paid' ? 'bg-orange-100 text-orange-700' :
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

                    {/* Documents List */}
                    {pa.documents?.length > 0 && (
                      <div>
                        <p className="text-sm font-semibold text-slate-700 mb-2">Submitted Documents:</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {pa.documents.map((doc, di) => (
                            <div key={di} className="flex items-center gap-2 bg-slate-50 rounded-lg p-3">
                              <FileText className="h-4 w-4 text-blue-500 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-slate-700 truncate">{doc.file_name}</p>
                                <p className="text-xs text-slate-500 capitalize">{doc.document_type}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

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

                    {/* 2ND APPROVAL: Create Case & Assign CM (for proposal_paid stage) */}
                    {pa.stage === 'proposal_paid' && (
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
