import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  FileCheck, Upload, CheckCircle, Clock, AlertCircle, Loader2,
  ChevronDown, ChevronRight, FileText, XCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StepDocuments = ({ token, caseId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedStep, setExpandedStep] = useState(null);
  const [uploading, setUploading] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    if (!caseId) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/step-documents/case/${caseId}`, { headers });
      setData(res.data);
      // Auto-expand first incomplete step
      const firstIncomplete = res.data.steps?.find(s => s.uploaded_count < s.required_count);
      if (firstIncomplete) setExpandedStep(firstIncomplete.step_name);
    } catch (e) {
      console.error('Failed to load step documents');
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, [caseId]);

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
      toast.success(`${docName} uploaded!`);
      loadData();
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
      toast.success(`${docName} uploaded!`);
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
    setUploading(null);
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (!data || !caseId) {
    return (
      <Card className="p-12 text-center" data-testid="step-documents">
        <FileCheck className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <p className="text-lg font-semibold text-slate-600">No Active Case</p>
        <p className="text-sm text-slate-400">Document requirements will appear when you have an active case</p>
      </Card>
    );
  }

  const s = data.summary || {};
  const progressColor = s.completion_pct >= 80 ? 'bg-emerald-500' : s.completion_pct >= 50 ? 'bg-blue-500' : 'bg-amber-500';

  return (
    <div className="space-y-5" data-testid="step-documents">
      {/* Overall Progress */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-[#2a777a]" />Document Requirements
          </h3>
          <div className="text-right">
            <p className="text-2xl font-bold text-[#2a777a]">{s.completion_pct || 0}%</p>
            <p className="text-xs text-slate-500">{s.total_uploaded}/{s.total_required} uploaded</p>
          </div>
        </div>
        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-3">
          <div className={`h-3 rounded-full transition-all duration-700 ${progressColor}`} style={{ width: `${s.completion_pct || 0}%` }} />
        </div>
      </Card>

      {/* Step-wise Documents */}
      {(data.steps || []).map((step, sIdx) => {
        const isExpanded = expandedStep === step.step_name;
        const stepComplete = step.required_count > 0 && step.uploaded_count >= step.required_count;
        return (
          <Card key={step.step_name} className={`overflow-hidden ${stepComplete ? 'border-emerald-200' : step.required_count > 0 ? 'border-amber-200' : ''}`} data-testid={`step-card-${sIdx}`}>
            {/* Step Header */}
            <div className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors" onClick={() => setExpandedStep(isExpanded ? null : step.step_name)}>
              <div className="flex items-center gap-3">
                {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                <span className="w-7 h-7 rounded-full bg-[#2a777a] text-white text-xs flex items-center justify-center font-bold">{step.step_order}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-slate-800 dark:text-white">{step.step_name}</h4>
                    {stepComplete && <CheckCircle className="h-4 w-4 text-emerald-500" />}
                    <Badge variant="outline" className="text-xs">{step.status}</Badge>
                  </div>
                  {step.description && <p className="text-xs text-slate-500 mt-0.5">{step.description}</p>}
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-800 dark:text-white">{step.uploaded_count}/{step.required_count}</p>
                  <p className="text-xs text-slate-500">documents</p>
                </div>
              </div>
              {step.required_count > 0 && (
                <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 mt-3 ml-11">
                  <div className={`h-1.5 rounded-full ${stepComplete ? 'bg-emerald-500' : step.uploaded_count > 0 ? 'bg-blue-500' : 'bg-slate-200'}`} style={{ width: `${step.required_count > 0 ? (step.uploaded_count / step.required_count) * 100 : 0}%` }} />
                </div>
              )}
            </div>

            {/* Expanded: Documents */}
            {isExpanded && (
              <div className="border-t p-4 space-y-3 bg-slate-50/50 dark:bg-slate-800/30">
                {step.documents.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-3">No documents required for this step</p>
                ) : (
                  step.documents.map((doc, dIdx) => (
                    <div key={dIdx} className={`flex items-center justify-between p-3 rounded-lg border ${
                      doc.status === 'approved' || doc.status === 'verified' ? 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20' :
                      doc.uploaded ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20' :
                      doc.status === 'rejected' ? 'bg-red-50 border-red-200 dark:bg-red-900/20' :
                      'bg-white border-slate-200 dark:bg-slate-800'
                    }`} data-testid={`doc-${sIdx}-${dIdx}`}>
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        {doc.uploaded ? (
                          doc.status === 'approved' || doc.status === 'verified' ? <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0" /> :
                          doc.status === 'rejected' ? <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" /> :
                          <Clock className="h-5 w-5 text-blue-500 flex-shrink-0" />
                        ) : (
                          <AlertCircle className="h-5 w-5 text-slate-300 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-sm text-slate-800 dark:text-white">{doc.doc_name}</span>
                            <Badge className={`text-[10px] ${doc.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                              {doc.tag || (doc.is_mandatory ? 'Mandatory' : 'Optional')}
                            </Badge>
                            {doc.source === 'cm_request' && <Badge className="text-[10px] bg-leamss-orange-100 text-leamss-orange-700">CM Requested</Badge>}
                          </div>
                          {doc.notes && <p className="text-xs text-slate-500 mt-0.5">{doc.notes}</p>}
                          {doc.uploaded && doc.uploaded_doc && (
                            <p className="text-xs text-emerald-600 mt-0.5">{doc.uploaded_doc.filename || 'Uploaded'} — {doc.status}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex-shrink-0 ml-3">
                        {doc.uploaded ? (
                          <Badge className={
                            doc.status === 'approved' || doc.status === 'verified' ? 'bg-emerald-100 text-emerald-700' :
                            doc.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                          }>{doc.status}</Badge>
                        ) : (
                          <label className="cursor-pointer">
                            <input type="file" className="hidden" onChange={(e) => handleUpload(step.step_name, doc.doc_name, e.target.files[0])} />
                            <span className="flex items-center gap-1 text-xs bg-[#2a777a] hover:bg-[#236466] text-white px-3 py-1.5 rounded-md transition-colors">
                              {uploading === `${step.step_name}-${doc.doc_name}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                              Upload
                            </span>
                          </label>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </Card>
        );
      })}

      {/* Additional Documents Section */}
      {(data.additional_requests || []).length > 0 && (
        <Card className="p-5" data-testid="additional-docs-section">
          <h4 className="font-semibold text-slate-800 dark:text-white mb-3 flex items-center gap-2">
            <FileText className="h-4 w-4 text-leamss-orange-500" />Additional Requested Documents
          </h4>
          <div className="space-y-3">
            {data.additional_requests.map((req, rIdx) => (
              <div key={req.id} className={`flex items-center justify-between p-3 rounded-lg border ${
                req.uploaded_doc ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-slate-200 dark:bg-slate-800'
              }`} data-testid={`additional-doc-${rIdx}`}>
                <div className="flex items-center gap-3 flex-1">
                  {req.uploaded_doc ? <CheckCircle className="h-5 w-5 text-emerald-500" /> : <AlertCircle className="h-5 w-5 text-leamss-orange-400" />}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-slate-800 dark:text-white">{req.doc_name}</span>
                      <Badge className="text-[10px] bg-leamss-orange-100 text-leamss-orange-700">Additional</Badge>
                      <Badge className={`text-[10px] ${req.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                        {req.tag || (req.is_mandatory ? 'Mandatory' : 'Optional')}
                      </Badge>
                    </div>
                    {req.notes && <p className="text-xs text-slate-500">{req.notes}</p>}
                    <p className="text-xs text-slate-400">Requested by {req.requested_by_name} on {req.created_at ? new Date(req.created_at).toLocaleDateString() : ''}</p>
                  </div>
                </div>
                {!req.uploaded_doc ? (
                  <label className="cursor-pointer">
                    <input type="file" className="hidden" onChange={(e) => handleAdditionalUpload(req.id, req.doc_name, e.target.files[0])} />
                    <span className="flex items-center gap-1 text-xs bg-[#2a777a] hover:bg-[#236466] text-white px-3 py-1.5 rounded-md">
                      {uploading === req.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                      Upload
                    </span>
                  </label>
                ) : (
                  <Badge className="bg-emerald-100 text-emerald-700">Uploaded</Badge>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default StepDocuments;
