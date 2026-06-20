import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  FileCheck, Upload, CheckCircle, Clock, AlertCircle, Loader2,
  ChevronDown, ChevronRight, FileText, XCircle, Shield, Download,
  AlertTriangle, Calendar, Eye, FileUp, Info
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const UnifiedDocumentView = ({ token, caseId, caseData, onDocumentUploaded }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [uploading, setUploading] = useState(null);
  const [uploadFiles, setUploadFiles] = useState({});

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = useCallback(async () => {
    if (!caseId) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/step-documents/case/${caseId}`, { headers });
      setData(res.data);
      const firstIncomplete = res.data.steps?.find(s => s.uploaded_count < s.required_count && s.status !== 'completed');
      if (firstIncomplete && Object.keys(expandedSteps).length === 0) {
        setExpandedSteps({ [firstIncomplete.step_name]: true });
      }
    } catch (e) {
      console.error('Failed to load documents', e);
    }
    setLoading(false);
  }, [caseId]);

  useEffect(() => { loadData(); }, [loadData]);

  const toggleStep = (stepName) => {
    setExpandedSteps(prev => ({ ...prev, [stepName]: !prev[stepName] }));
  };

  const handleUpload = async (stepName, docName, file) => {
    if (!file) return;
    setUploading(`${stepName}-${docName}`);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);
    formData.append('step_name', stepName);
    formData.append('document_type', docName);
    try {
      await axios.post(`${API}/documents/upload`, formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`"${docName}" uploaded successfully!`);
      setUploadFiles(prev => { const n = {...prev}; delete n[`${stepName}-${docName}`]; return n; });
      loadData();
      onDocumentUploaded?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
    setUploading(null);
  };

  const handleAdditionalUpload = async (requestId, docName, file) => {
    if (!file) return;
    setUploading(requestId);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);
    formData.append('document_type', docName);
    formData.append('additional_request_id', requestId);
    try {
      await axios.post(`${API}/documents/upload`, formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`"${docName}" uploaded!`);
      setUploadFiles(prev => { const n = {...prev}; delete n[requestId]; return n; });
      loadData();
      onDocumentUploaded?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
    setUploading(null);
  };

  const downloadDocument = async (docId, filename) => {
    try {
      const response = await axios.get(`${API}/documents/download/${docId}`, {
        headers, responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || 'document');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (e) {
      toast.error('Download failed');
    }
  };

  // Check document expiry
  const getExpiryWarning = (doc) => {
    if (!doc?.uploaded_doc) return null;
    const expiry = doc.uploaded_doc.expiry_date;
    if (!expiry) return null;
    const daysLeft = Math.ceil((new Date(expiry) - new Date()) / (1000 * 60 * 60 * 24));
    if (daysLeft < 0) return { type: 'expired', text: 'Expired', color: 'bg-red-100 text-red-700 border-red-200' };
    if (daysLeft <= 30) return { type: 'warning', text: `Expires in ${daysLeft} days`, color: 'bg-amber-100 text-amber-700 border-amber-200' };
    if (daysLeft <= 90) return { type: 'info', text: `Expires in ${daysLeft} days`, color: 'bg-blue-100 text-blue-700 border-blue-200' };
    return null;
  };

  const getStatusIcon = (doc) => {
    if (!doc.uploaded) return <AlertCircle className="h-5 w-5 text-slate-300 flex-shrink-0" />;
    if (doc.status === 'approved' || doc.status === 'verified') return <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0" />;
    if (doc.status === 'rejected') return <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />;
    return <Clock className="h-5 w-5 text-blue-500 flex-shrink-0" />;
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'approved': case 'verified': return 'bg-emerald-100 text-emerald-700';
      case 'rejected': return 'bg-red-100 text-red-700';
      case 'pending': case 'pending_review': return 'bg-blue-100 text-blue-700';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" />
    </div>
  );

  if (!data || !caseId) {
    return (
      <Card className="p-16 text-center" data-testid="unified-doc-view">
        <FileCheck className="h-14 w-14 text-slate-300 mx-auto mb-4" />
        <p className="text-lg font-semibold text-slate-600">No Active Case</p>
        <p className="text-sm text-slate-400 mt-1">Document requirements will appear when you have an active case</p>
      </Card>
    );
  }

  const s = data.summary || {};
  const steps = data.steps || [];
  const additionalRequests = data.additional_requests || [];
  const pendingAdditional = additionalRequests.filter(r => !r.uploaded_doc);
  const completedAdditional = additionalRequests.filter(r => r.uploaded_doc);

  const progressColor = s.completion_pct >= 80 ? 'from-emerald-500 to-emerald-600' : s.completion_pct >= 50 ? 'from-blue-500 to-blue-600' : 'from-amber-500 to-amber-600';

  return (
    <div className="space-y-5" data-testid="unified-doc-view">
      {/* Overall Progress Header */}
      <Card className="overflow-hidden border-0 shadow-lg" data-testid="doc-progress-card">
        <div className={`bg-gradient-to-r ${progressColor} p-5 text-white`}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Shield className="h-5 w-5" /> Document Progress
              </h3>
              <p className="text-white/80 text-sm mt-0.5">
                {steps.filter(st => st.required_count > 0 && st.uploaded_count >= st.required_count).length} of {steps.filter(st => st.required_count > 0).length} steps complete
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold">{s.completion_pct || 0}%</p>
              <p className="text-white/80 text-sm">{s.total_uploaded}/{s.total_required} docs</p>
            </div>
          </div>
          <div className="w-full bg-white/20 rounded-full h-2.5">
            <div className="bg-white rounded-full h-2.5 transition-all duration-700" style={{ width: `${s.completion_pct || 0}%` }} />
          </div>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-4 divide-x bg-white">
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-slate-800">{s.total_required || 0}</p>
            <p className="text-[11px] text-slate-500">Required</p>
          </div>
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-emerald-600">{s.total_uploaded || 0}</p>
            <p className="text-[11px] text-slate-500">Uploaded</p>
          </div>
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-amber-600">{(s.total_required || 0) - (s.total_uploaded || 0)}</p>
            <p className="text-[11px] text-slate-500">Pending</p>
          </div>
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-blue-600">{pendingAdditional.length}</p>
            <p className="text-[11px] text-slate-500">Requested</p>
          </div>
        </div>
      </Card>

      {/* Action Required Banner */}
      {pendingAdditional.length > 0 && (
        <Card className="border-l-4 border-l-[#f7620b] bg-gradient-to-r from-orange-50 to-white p-4 flex items-center gap-3" data-testid="action-required-banner">
          <AlertTriangle className="h-5 w-5 text-[#f7620b] flex-shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-slate-800 text-sm">Action Required</p>
            <p className="text-xs text-slate-500">{pendingAdditional.length} additional document(s) requested by your Case Manager</p>
          </div>
          <Button size="sm" variant="outline" className="border-[#f7620b] text-[#f7620b] hover:bg-[#f7620b]/10" onClick={() => {
            const el = document.getElementById('additional-docs-section');
            el?.scrollIntoView({ behavior: 'smooth' });
          }} data-testid="scroll-to-additional">
            View
          </Button>
        </Card>
      )}

      {/* Step-wise Document Cards */}
      {steps.map((step, sIdx) => {
        const isExpanded = expandedSteps[step.step_name];
        const stepComplete = step.required_count > 0 && step.uploaded_count >= step.required_count;
        const hasDocuments = step.required_count > 0;
        const isCurrentStep = caseData?.current_step === step.step_name;

        return (
          <Card
            key={step.step_name}
            className={`overflow-hidden transition-all border-0 shadow-md ${
              stepComplete ? 'ring-1 ring-emerald-200' :
              isCurrentStep ? 'ring-2 ring-[#2a777a]/40' : ''
            }`}
            data-testid={`step-card-${sIdx}`}
          >
            {/* Step Header */}
            <div
              className={`p-4 cursor-pointer transition-colors ${
                isExpanded ? 'bg-slate-50 dark:bg-slate-800/50' : 'hover:bg-slate-50 dark:hover:bg-slate-800/30'
              }`}
              onClick={() => toggleStep(step.step_name)}
            >
              <div className="flex items-center gap-3">
                {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 flex-shrink-0" />}
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  stepComplete ? 'bg-emerald-500' :
                  step.status === 'completed' ? 'bg-emerald-500' :
                  step.status === 'in_progress' ? 'bg-[#2a777a]' : 'bg-slate-300'
                }`}>
                  {stepComplete || step.status === 'completed' ?
                    <CheckCircle className="h-5 w-5 text-white" /> :
                    <span className="text-white font-bold text-sm">{step.step_order}</span>
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold text-slate-800 dark:text-white text-sm">{step.step_name}</h4>
                    {isCurrentStep && <Badge className="bg-[#2a777a]/10 text-[#2a777a] text-[10px] border border-[#2a777a]/20">Current Step</Badge>}
                    <Badge className={`text-[10px] ${
                      step.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                      step.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                    }`}>{step.status === 'in_progress' ? 'In Progress' : step.status === 'completed' ? 'Complete' : 'Pending'}</Badge>
                  </div>
                  {step.description && <p className="text-xs text-slate-500 mt-0.5 truncate">{step.description}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  {hasDocuments ? (
                    <>
                      <p className="text-sm font-bold text-slate-800 dark:text-white">{step.uploaded_count}/{step.required_count}</p>
                      <p className="text-[10px] text-slate-500">documents</p>
                    </>
                  ) : (
                    <p className="text-[10px] text-slate-400">No docs</p>
                  )}
                </div>
              </div>
              {/* Step progress bar */}
              {hasDocuments && (
                <div className="mt-2.5 ml-[52px]">
                  <Progress value={step.required_count > 0 ? (step.uploaded_count / step.required_count) * 100 : 0} className="h-1.5" />
                </div>
              )}
            </div>

            {/* Expanded: Documents */}
            {isExpanded && (
              <div className="border-t divide-y">
                {step.documents.length === 0 ? (
                  <div className="p-6 text-center">
                    <FileText className="h-8 w-8 text-slate-200 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No documents required for this step</p>
                  </div>
                ) : (
                  step.documents.map((doc, dIdx) => {
                    const expiry = getExpiryWarning(doc);
                    const uploadKey = `${step.step_name}-${doc.doc_name}`;
                    return (
                      <div key={dIdx} className={`p-4 ${
                        doc.status === 'approved' || doc.status === 'verified' ? 'bg-emerald-50/50' :
                        doc.uploaded ? 'bg-blue-50/30' :
                        doc.status === 'rejected' ? 'bg-red-50/50' : 'bg-white'
                      }`} data-testid={`doc-${sIdx}-${dIdx}`}>
                        <div className="flex items-start gap-3">
                          {getStatusIcon(doc)}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-sm text-slate-800 dark:text-white">{doc.doc_name}</span>
                              <Badge className={`text-[9px] ${doc.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                                {doc.tag || (doc.is_mandatory ? 'Mandatory' : 'Optional')}
                              </Badge>
                              {doc.source === 'cm_request' && (
                                <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">CM Requested</Badge>
                              )}
                            </div>
                            {doc.notes && (
                              <p className="text-xs text-slate-500 mt-1 flex items-start gap-1">
                                <Info className="h-3 w-3 mt-0.5 flex-shrink-0" /> {doc.notes}
                              </p>
                            )}
                            {doc.uploaded && doc.uploaded_doc && (
                              <p className="text-xs text-emerald-600 mt-1">{doc.uploaded_doc.filename || 'Uploaded'}</p>
                            )}
                            {expiry && (
                              <div className={`inline-flex items-center gap-1 text-[10px] mt-1 px-2 py-0.5 rounded-full border ${expiry.color}`}>
                                <AlertTriangle className="h-3 w-3" /> {expiry.text}
                              </div>
                            )}
                          </div>
                          <div className="flex-shrink-0 flex items-center gap-2">
                            {doc.uploaded ? (
                              <div className="flex items-center gap-1">
                                <Badge className={getStatusColor(doc.status)}>
                                  {doc.status === 'pending_review' ? 'Under Review' : doc.status === 'not_uploaded' ? 'Pending' : doc.status}
                                </Badge>
                                {doc.uploaded_doc?.id && (
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => downloadDocument(doc.uploaded_doc.id, doc.uploaded_doc.filename)}>
                                    <Download className="h-3.5 w-3.5 text-slate-500" />
                                  </Button>
                                )}
                              </div>
                            ) : (
                              <label className="cursor-pointer" data-testid={`upload-btn-${sIdx}-${dIdx}`}>
                                <input
                                  type="file"
                                  className="hidden"
                                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                                  onChange={(e) => {
                                    if (e.target.files[0]) {
                                      handleUpload(step.step_name, doc.doc_name, e.target.files[0]);
                                    }
                                  }}
                                />
                                <span className="flex items-center gap-1.5 text-xs bg-[#2a777a] hover:bg-[#236466] text-white px-3 py-1.5 rounded-md transition-colors cursor-pointer">
                                  {uploading === uploadKey ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                                  Upload
                                </span>
                              </label>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </Card>
        );
      })}

      {/* Additional Documents Section */}
      {additionalRequests.length > 0 && (
        <div id="additional-docs-section" className="space-y-4" data-testid="additional-docs-section">
          <div className="flex items-center gap-2 pt-2">
            <FileText className="h-5 w-5 text-leamss-orange-500" />
            <h3 className="font-semibold text-slate-800 dark:text-white">Additional Requested Documents</h3>
            <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-xs">{additionalRequests.length}</Badge>
          </div>

          {/* Pending additional docs */}
          {pendingAdditional.map((req, rIdx) => (
            <Card key={req.id} className="border-l-4 border-l-leamss-orange-400 overflow-hidden shadow-sm" data-testid={`additional-doc-${rIdx}`}>
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-leamss-orange-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-slate-800 dark:text-white">{req.doc_name}</span>
                      <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">Additional</Badge>
                      <Badge className={`text-[9px] ${req.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                        {req.tag || 'Required'}
                      </Badge>
                    </div>
                    {req.notes && <p className="text-xs text-slate-500 mt-1">{req.notes}</p>}
                    <p className="text-[10px] text-slate-400 mt-1">
                      Requested by {req.requested_by_name} {req.created_at ? `on ${new Date(req.created_at).toLocaleDateString()}` : ''}
                    </p>
                  </div>
                  <label className="cursor-pointer flex-shrink-0" data-testid={`upload-additional-${rIdx}`}>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                      onChange={(e) => {
                        if (e.target.files[0]) {
                          handleAdditionalUpload(req.id, req.doc_name, e.target.files[0]);
                        }
                      }}
                    />
                    <span className="flex items-center gap-1.5 text-xs bg-leamss-orange-600 hover:bg-leamss-orange-700 text-white px-3 py-1.5 rounded-md transition-colors cursor-pointer">
                      {uploading === req.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                      Upload
                    </span>
                  </label>
                </div>
              </div>
            </Card>
          ))}

          {/* Completed additional docs */}
          {completedAdditional.map((req, rIdx) => (
            <Card key={req.id} className="border-l-4 border-l-emerald-400 overflow-hidden shadow-sm bg-emerald-50/30">
              <div className="p-4 flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-slate-800">{req.doc_name}</span>
                    <Badge className="text-[9px] bg-emerald-100 text-emerald-700">Uploaded</Badge>
                  </div>
                  <p className="text-[10px] text-slate-400">{req.uploaded_doc?.filename || 'Submitted'}</p>
                </div>
                {req.uploaded_doc?.id && (
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => downloadDocument(req.uploaded_doc.id, req.uploaded_doc.filename)}>
                    <Download className="h-3.5 w-3.5 text-slate-500" />
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Other/Unmatched Uploads */}
      {(data.other_uploads || []).length > 0 && (
        <Card className="p-4 bg-slate-50 border-0 shadow-sm">
          <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
            <FileCheck className="h-4 w-4 text-slate-500" /> Other Uploaded Documents
          </h4>
          <div className="space-y-2">
            {data.other_uploads.map((doc, idx) => (
              <div key={idx} className="flex items-center justify-between p-2.5 bg-white rounded-lg border text-sm">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-slate-400" />
                  <span className="text-slate-700">{doc.filename || doc.document_type || 'Document'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={getStatusColor(doc.status)}>{doc.status}</Badge>
                  {doc.id && (
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => downloadDocument(doc.id, doc.filename)}>
                      <Download className="h-3 w-3 text-slate-500" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default UnifiedDocumentView;
