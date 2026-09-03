import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  FileCheck, Upload, CheckCircle, CheckCircle2, Clock, AlertCircle, Loader2,
  ChevronDown, ChevronRight, FileText, XCircle, Shield, Download,
  AlertTriangle, Calendar, Eye, FileUp, Info, Lock, CreditCard
} from 'lucide-react';
import ClientPaymentModal from './ClientPaymentModal';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const UnifiedDocumentView = ({ token, caseId, caseData, onDocumentUploaded }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [uploading, setUploading] = useState(null);
  const [fieldValues, setFieldValues] = useState({});
  const [uploadFiles, setUploadFiles] = useState({});
  const [submittingField, setSubmittingField] = useState(null);
  const [submittedFields, setSubmittedFields] = useState({});
  const [stepPaymentModalData, setStepPaymentModalData] = useState({ open: false, data: null });

  const headers = { Authorization: `Bearer ${token}` };

  const handleStepPayment = (saleId, step) => {
    const payAmt = Number(step?.payment_amount || 10125);
    setStepPaymentModalData({
      open: true,
      data: {
        saleId: saleId || caseData?.sale_id,
        amount: payAmt,
        part: { label: '2nd Installment (50%)', index: 1, amount: payAmt },
        productName: caseData?.service_type ? `${caseData.service_type} Application` : (caseData?.product_name || 'PR Journey & Immigration'),
        partnerName: caseData?.partner_name || 'LEAMSS Consultant',
        clientName: caseData?.client_name || 'Client',
        destination: caseData?.country || 'Australia',
        serviceType: caseData?.service_type || 'PR',
      }
    });
  };

const loadData = useCallback(async () => {
  if (!caseId) {
    setLoading(false);
    return;
  }

  try {
    const [documentsRes, intakeRes] = await Promise.all([
      axios.get(
        `${API}/step-documents/case/${caseId}`,
        { headers }
      ),

      axios.get(
        `${API}/intake-forms/case/${caseId}`,
        { headers }
      )
    ]);

    setData(documentsRes.data);

    const savedValues = {};
const savedSubmittedFields = {};

for (const section of intakeRes.data.sections || []) {
  for (const field of section.fields || []) {
    if (
      field.value !== undefined &&
      field.value !== null &&
      field.value !== ''
    ) {
      savedValues[field.key] = field.value;
      savedSubmittedFields[field.key] = true;
    }
  }
}

setFieldValues(savedValues);
setSubmittedFields(savedSubmittedFields);

// setFieldValues(savedValues);

//     setFieldValues(savedValues);

    const firstIncomplete = documentsRes.data.steps?.find(
      (step) =>
        step.uploaded_count < step.required_count &&
        step.status !== 'completed'
    );

    if (
      firstIncomplete &&
      Object.keys(expandedSteps).length === 0
    ) {
      setExpandedSteps({
        [firstIncomplete.step_name]: true
      });
    }
  } catch (e) {
    console.error('Failed to load documents/intake data', e);
  }

  setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [caseId]);

  useEffect(() => { loadData(); }, [loadData]);

  const toggleStep = (stepName) => {
    setExpandedSteps(prev => ({ ...prev, [stepName]: !prev[stepName] }));
  };
 const handleFieldSubmit = async (field, step) => {
  const fieldKey = field.key || field.doc_name;
  const value = fieldValues[fieldKey];

  if (
    value === undefined ||
    value === null ||
    String(value).trim() === ''
  ) {
    toast.error('Please enter a value before submitting');
    return;
  }

  try {
    setSubmittingField(fieldKey);

    await axios.post(
      `${API}/intake-forms/case/save`,
      {
        case_id: caseId,
        data: {
          [fieldKey]: value
        }
      },
      { headers }
    );

    setSubmittedFields((prev) => ({
      ...prev,
      [fieldKey]: true
    }));

    toast.success(
      `"${field.doc_name || field.label}" submitted successfully!`
    );

    await loadData();

    onDocumentUploaded?.();
  } catch (e) {
    console.error('Field submit failed:', e);

    toast.error(
      e.response?.data?.detail || 'Failed to submit field'
    );
  } finally {
    setSubmittingField(null);
  }
};

  const handleUpload = async (stepName, docName, filesInput) => {
    if (!filesInput) return;
    const files = filesInput instanceof FileList || Array.isArray(filesInput)
      ? Array.from(filesInput)
      : [filesInput];
    if (files.length === 0) return;

    const uploadKey = `${stepName}-${docName}`;
    setUploading(uploadKey);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    formData.append('case_id', caseId);
    formData.append('step_name', stepName);
    formData.append('document_type', docName);

    try {
      await axios.post(`${API}/documents/upload`, formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(
        files.length > 1
          ? `${files.length} documents uploaded for "${docName}"!`
          : `"${docName}" uploaded successfully!`
      );
      setUploadFiles((prev) => {
        const n = { ...prev };
        delete n[uploadKey];
        return n;
      });
      loadData();
      onDocumentUploaded?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
    setUploading(null);
  };

  const handleAdditionalUpload = async (requestId, docName, filesInput) => {
    if (!filesInput) return;
    const files = filesInput instanceof FileList || Array.isArray(filesInput)
      ? Array.from(filesInput)
      : [filesInput];
    if (files.length === 0) return;

    setUploading(requestId);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    formData.append('case_id', caseId);
    formData.append('document_type', docName);
    formData.append('additional_request_id', requestId);

    try {
      await axios.post(`${API}/documents/upload`, formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(
        files.length > 1
          ? `${files.length} documents uploaded for "${docName}"!`
          : `"${docName}" uploaded successfully!`
      );
      setUploadFiles((prev) => {
        const n = { ...prev };
        delete n[requestId];
        return n;
      });
      loadData();
      onDocumentUploaded?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
    setUploading(null);
  };

  const handleDeleteDoc = async (docId, filename) => {
    if (!window.confirm(`Are you sure you want to remove "${filename}"?`)) return;
    try {
      await axios.delete(`${API}/documents/${docId}`, { headers });
      toast.success(`"${filename}" removed successfully`);
      loadData();
      onDocumentUploaded?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete document');
    }
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
//   const renderIntakeField = (field, step) => {
//   const fieldKey = `${step.step_name}-${field.key || field.doc_name}`;

//   const value = fieldValues[fieldKey] || '';

//   const updateValue = (newValue) => {
//     setFieldValues(prev => ({
//       ...prev,
//       [fieldKey]: newValue
//     }));
//   };

//   if (field.field_type === 'textarea') {
//     return (
//       <textarea
//         value={value}
//         onChange={(e) => updateValue(e.target.value)}
//         placeholder={field.placeholder || field.notes || ''}
//         className="w-full min-h-[100px] border border-slate-200 rounded-lg p-3 text-sm"
//       />
//     );
//   }

//   if (field.field_type === 'date') {
//     return (
//       <Input
//         type="date"
//         value={value}
//         onChange={(e) => updateValue(e.target.value)}
//       />
//     );
//   }

//   if (field.field_type === 'select') {
//     return (
//       <select
//         value={value}
//         onChange={(e) => updateValue(e.target.value)}
//         className="w-full h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white"
//       >
//         <option value="">Select option</option>

//         {(field.options || []).map((option, index) => (
//           <option key={index} value={option}>
//             {option}
//           </option>
//         ))}
//       </select>
//     );
//   }

//   if (field.field_type === 'text') {
//     return (
//       <Input
//         type="text"
//         value={value}
//         onChange={(e) => updateValue(e.target.value)}
//         placeholder={field.placeholder || field.notes || ''}
//       />
//     );
//   }

//   return null;
// };
const renderIntakeField = (field, step) => {
  
  const fieldKey = field.key || field.doc_name;

  const fieldType = (
    field.field_type ||
    field.type ||
    'text'
  ).toLowerCase();

  const value = fieldValues[fieldKey] || '';
  // const isSubmitted =
  // value !== undefined &&
  // value !== null &&
  // value !== '';
  const isSubmitted = submittedFields[fieldKey] === true;

  const updateValue = (newValue) => {
    setFieldValues((prev) => ({
      ...prev,
      [fieldKey]: newValue
    }));
  };

  const isSubmitting = submittingField === fieldKey;
  const isLocked = step?.is_locked === true;

  return (
    <div className="space-y-2">
      {fieldType === 'textarea' && (
        <textarea
          value={value}
          disabled={isSubmitted || isLocked}
          onChange={(e) => updateValue(e.target.value)}
          placeholder={isLocked ? 'Locked until Case Manager completes previous step' : (field.placeholder || field.notes || '')}
          className="w-full min-h-[100px] border border-slate-200 rounded-lg p-3 text-sm disabled:bg-slate-100 disabled:text-slate-700"
        />
      )}

      {fieldType === 'date' && (
        <Input
          type="date"
          value={value}
          disabled={isSubmitted || isLocked}
          onChange={(e) => updateValue(e.target.value)}
        />
      )}

      {(fieldType === 'select' || fieldType === 'dropdown') && (
        <select
          value={value}
          disabled={isSubmitted || isLocked}
          onChange={(e) => updateValue(e.target.value)}
          className="w-full h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white disabled:bg-slate-100"
        >
          <option value="">{isLocked ? 'Locked' : 'Select option'}</option>

          {(field.options || []).map((option, index) => {
            const optionValue =
              typeof option === 'string'
                ? option
                : option.value;

            const optionLabel =
              typeof option === 'string'
                ? option
                : option.label;

            return (
              <option key={index} value={optionValue}>
                {optionLabel}
              </option>
            );
          })}
        </select>
      )}

      {fieldType === 'text' && (
        <Input
          type="text"
          value={value}
          disabled={isSubmitted || isLocked}
          onChange={(e) => updateValue(e.target.value)}
          placeholder={isLocked ? 'Locked until Case Manager completes previous step' : (field.placeholder || field.notes || '')}
        />
      )}

      <Button
        type="button"
        size="sm"
        onClick={() => handleFieldSubmit(field, step)}
        disabled={
          isLocked ||
          isSubmitting ||
          isSubmitted ||
          value === ''
        }
        className="bg-[#2a777a] hover:bg-[#236466] text-white disabled:opacity-60"
      >
        {isLocked ? (
          <>
            <Lock className="h-3.5 w-3.5 mr-1.5" /> Locked
          </>
        ) : isSubmitting ? (
          <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
        ) : (
          <FileCheck className="h-3.5 w-3.5 mr-1.5" />
        )}

        {isLocked
          ? ''
          : isSubmitting
          ? 'Submitting...'
          : isSubmitted
          ? 'Submitted'
          : 'Submit'}
      </Button>
    </div>
  );
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
        const isLocked = step.is_locked === true;
        const stepComplete = step.required_count > 0 && step.uploaded_count >= step.required_count;
        const hasDocuments = step.required_count > 0;
        const isCurrentStep = caseData?.current_step === step.step_name;

        return (
          <Card
            key={step.step_name}
            className={`overflow-hidden transition-all border-0 shadow-md ${
              isLocked ? 'opacity-90 bg-slate-50/60 ring-1 ring-slate-200' :
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
                  isLocked ? 'bg-slate-400' :
                  stepComplete ? 'bg-emerald-500' :
                  step.status === 'completed' ? 'bg-emerald-500' :
                  step.status === 'in_progress' ? 'bg-[#2a777a]' : 'bg-slate-300'
                }`}>
                  {isLocked ? (
                    <Lock className="h-4 w-4 text-white" />
                  ) : stepComplete || step.status === 'completed' ? (
                    <CheckCircle className="h-5 w-5 text-white" />
                  ) : (
                    <span className="text-white font-bold text-sm">{step.step_order}</span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold text-slate-800 dark:text-white text-sm">{step.step_name}</h4>
                    {isLocked ? (
                      <Badge className="bg-amber-50 text-amber-800 border border-amber-300 text-[10px] gap-1 flex items-center">
                        <Lock className="h-2.5 w-2.5 text-amber-600" /> Locked
                      </Badge>
                    ) : isCurrentStep ? (
                      <Badge className="bg-[#2a777a]/10 text-[#2a777a] text-[10px] border border-[#2a777a]/20">Current Step</Badge>
                    ) : null}
                    {step.uploaded_count > 0 && (
                      <Badge className="bg-blue-50 text-blue-800 border border-blue-200 text-[10px] gap-1 font-semibold flex items-center">
                        📄 {step.uploaded_count} Uploaded
                      </Badge>
                    )}
                    {!isLocked && (
                      <Badge className={`text-[10px] ${
                        step.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                        step.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                      }`}>{step.status === 'in_progress' ? 'In Progress' : step.status === 'completed' ? 'Complete' : 'Pending'}</Badge>
                    )}
                  </div>
                  {isLocked ? (
                    <p className="text-xs text-amber-700 font-medium mt-0.5 flex items-center gap-1">
                      <Lock className="h-3 w-3 inline text-amber-600 shrink-0" /> {step.locked_reason || 'Locked until Case Manager completes previous step'}
                    </p>
                  ) : step.description ? (
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{step.description}</p>
                  ) : null}
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
                {/* Locked Banner inside step */}
                {isLocked && (
                  <div className={`p-4 border-b flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                    step.payment_required || step.locked_reason?.includes('Installment')
                      ? 'bg-amber-50/90 border-amber-300'
                      : 'bg-amber-50/80 border-amber-200/80'
                  }`}>
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                        step.payment_required || step.locked_reason?.includes('Installment')
                          ? 'bg-amber-200 text-amber-900'
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        {step.payment_required || step.locked_reason?.includes('Installment') ? (
                          <CreditCard className="h-4 w-4 text-amber-900" />
                        ) : (
                          <Lock className="h-4 w-4 text-amber-700" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h5 className="text-xs font-bold text-amber-900">
                          {step.payment_required || step.locked_reason?.includes('Installment')
                            ? `Step ${step.step_order}: ${step.step_name} — 2nd Installment Payment Required`
                            : `Step ${step.step_order}: ${step.step_name} is Locked`}
                        </h5>
                        <p className="text-xs text-amber-800 mt-0.5">
                          {step.locked_reason || 'This step and its documents will automatically unlock once your Case Manager completes the previous step.'}
                        </p>
                        <p className="text-[11px] text-amber-600 mt-1 font-medium">
                          {step.payment_required || step.locked_reason?.includes('Installment')
                            ? '💳 Complete your 2nd installment payment to immediately unlock this step and document uploads.'
                            : '🔒 Document uploads and requirements for this step are not open yet.'}
                        </p>
                      </div>
                    </div>

                    {(step.payment_required || step.locked_reason?.includes('Installment')) && (
                      <div className="shrink-0 mt-2 sm:mt-0">
                        <Button
                          onClick={() => handleStepPayment(step.sale_id, step)}
                          className="bg-[#f7620b] hover:bg-[#e0580a] text-white shadow-md text-xs font-semibold px-4 py-2 flex items-center gap-1.5 rounded-lg"
                          data-testid={`pay-step-${step.step_order}-btn`}
                        >
                          <CreditCard className="h-3.5 w-3.5" />
                          Pay ₹{Number(step.payment_amount || 10125).toLocaleString()} Now
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {step.documents.length === 0 ? (
                  <div className="p-6 text-center">
                    <FileText className="h-8 w-8 text-slate-200 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No documents required for this step</p>
                  </div>
                ) : (
                  [...step.documents].sort((a, b) => {
                    const aRank = (a.is_locked_until_paid && a.uploaded) ? 0 : a.is_locked_until_paid ? 1 : a.uploaded ? 2 : 3;
                    const bRank = (b.is_locked_until_paid && b.uploaded) ? 0 : b.is_locked_until_paid ? 1 : b.uploaded ? 2 : 3;
                    return aRank - bRank;
                  }).map((doc, dIdx) => {
                      const expiry = getExpiryWarning(doc);
                      const uploadKey = `${step.step_name}-${doc.doc_name}`;
                      const isCmLockedDoc = doc.is_locked_until_paid && doc.uploaded;
                      const uploadedList = (doc.uploaded_docs && doc.uploaded_docs.length > 0)
                        ? doc.uploaded_docs
                        : (doc.uploaded_doc ? [doc.uploaded_doc] : []);

                      return (
                        <div
                          key={dIdx}
                          className={`p-4 border-b last:border-b-0 ${
                            doc.is_payment_locked
                              ? 'bg-gradient-to-r from-amber-50/90 to-orange-50/50 border-amber-200'
                              : isCmLockedDoc && !doc.is_payment_locked
                              ? 'bg-gradient-to-r from-emerald-50/80 to-teal-50/40 border-emerald-200'
                              : isLocked
                              ? 'bg-slate-50/50 opacity-75'
                              : doc.status === 'approved' || doc.status === 'verified'
                              ? 'bg-emerald-50/30'
                              : doc.uploaded
                              ? 'bg-blue-50/30'
                              : doc.status === 'rejected'
                              ? 'bg-red-50/40'
                              : 'bg-white'
                          }`}
                          data-testid={`doc-${sIdx}-${dIdx}`}
                        >
                          <div className="flex flex-col sm:flex-row items-start justify-between gap-3">
                            <div className="flex items-start gap-3 flex-1 min-w-0">
                              {doc.is_payment_locked ? (
                                <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 shrink-0 mt-0.5 shadow-xs">
                                  <Lock className="h-4 w-4 text-amber-700" />
                                </div>
                              ) : isCmLockedDoc && !doc.is_payment_locked ? (
                                <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0 mt-0.5 shadow-xs">
                                  <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                                </div>
                              ) : isLocked ? (
                                <Lock className="h-5 w-5 text-slate-300 flex-shrink-0 mt-0.5" />
                              ) : (
                                getStatusIcon(doc)
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span
                                    className={`font-medium text-sm ${
                                      doc.is_payment_locked
                                        ? 'text-amber-950 font-semibold'
                                        : 'text-slate-800 dark:text-white'
                                    }`}
                                  >
                                    {doc.doc_name}
                                  </span>
                                  <Badge
                                    className={`text-[9px] ${
                                      doc.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                                    }`}
                                  >
                                    {doc.tag || (doc.is_mandatory ? 'Mandatory' : 'Optional')}
                                  </Badge>
                                  {uploadedList.length > 0 && (
                                    <Badge className="text-[10px] bg-blue-50 text-blue-800 border border-blue-200 font-semibold">
                                      📄 {uploadedList.length} {uploadedList.length === 1 ? 'File' : 'Files'} Uploaded
                                    </Badge>
                                  )}
                                  {doc.source === 'cm_request' && (
                                    <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">
                                      CM Requested
                                    </Badge>
                                  )}
                                  {doc.is_payment_locked ? (
                                    <Badge className="text-[10px] bg-amber-100 text-amber-800 border border-amber-300 font-semibold flex items-center gap-1">
                                      🔒 Case Manager Uploaded · Locked Until Full Payment
                                    </Badge>
                                  ) : isCmLockedDoc && !doc.is_payment_locked ? (
                                    <Badge className="text-[10px] bg-emerald-100 text-emerald-800 border border-emerald-300 font-semibold flex items-center gap-1">
                                      🔓 Unlocked · Full Payment Completed
                                    </Badge>
                                  ) : isLocked ? (
                                    <Badge className="text-[9px] bg-amber-100 text-amber-800 border border-amber-200">
                                      Locked
                                    </Badge>
                                  ) : null}
                                </div>

                                {doc.notes && (
                                  <p className="text-xs text-slate-500 mt-1 flex items-start gap-1">
                                    <Info className="h-3 w-3 mt-0.5 flex-shrink-0" /> {doc.notes}
                                  </p>
                                )}

                                {doc.is_payment_locked && (
                                  <p className="text-xs text-amber-800 font-medium mt-1">
                                    Your Case Manager has uploaded document(s). Locked until pending payment (₹{Number(doc.payment_pending_amount).toLocaleString()}) is completed.
                                  </p>
                                )}

                                {/* LIST OF ALL UPLOADED FILES UNDER THIS STEP / REQUIREMENT */}
                                {uploadedList.length > 0 && (
                                  <div className="mt-2.5 space-y-1.5 w-full">
                                    {uploadedList.map((uDoc, uIdx) => {
                                      const uExpiry = getExpiryWarning({ uploaded_doc: uDoc });
                                      return (
                                        <div
                                          key={uDoc.id || uIdx}
                                          className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50/90 dark:bg-slate-800/60 border border-slate-200/90 hover:bg-slate-100/80 transition-colors gap-2"
                                        >
                                          <div className="flex items-center gap-2 min-w-0 flex-1">
                                            <FileText className="h-4 w-4 text-[#2a777a] shrink-0" />
                                            <span
                                              className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate"
                                              title={uDoc.filename}
                                            >
                                              {uDoc.filename}
                                            </span>
                                            {uDoc.file_size && (
                                              <span className="text-[10px] text-slate-400 shrink-0">
                                                ({(uDoc.file_size / 1024).toFixed(0)} KB)
                                              </span>
                                            )}
                                            <Badge
                                              className={`text-[9px] px-1.5 py-0 h-4 ${getStatusColor(
                                                uDoc.status
                                              )}`}
                                            >
                                              {uDoc.status === 'pending_review'
                                                ? 'Under Review'
                                                : uDoc.status === 'not_uploaded'
                                                ? 'Pending'
                                                : uDoc.status}
                                            </Badge>
                                            {uExpiry && (
                                              <span
                                                className={`text-[9px] px-1.5 py-0.5 rounded border ${uExpiry.color}`}
                                              >
                                                {uExpiry.text}
                                              </span>
                                            )}
                                          </div>

                                          <div className="flex items-center gap-1.5 shrink-0">
                                            <Button
                                              variant="outline"
                                              size="sm"
                                              className="h-7 px-2 text-xs flex items-center gap-1 border-slate-300 text-slate-700 hover:bg-white shadow-2xs"
                                              title="Download file"
                                              onClick={() => downloadDocument(uDoc.id, uDoc.filename)}
                                            >
                                              <Download className="h-3.5 w-3.5 text-slate-600" />
                                              <span className="hidden sm:inline">Download</span>
                                            </Button>

                                            {!isLocked && (
                                              <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-7 w-7 p-0 text-red-400 hover:text-red-600 hover:bg-red-50"
                                                title="Delete file"
                                                onClick={() => handleDeleteDoc(uDoc.id, uDoc.filename)}
                                              >
                                                <XCircle className="h-3.5 w-3.5" />
                                              </Button>
                                            )}
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}

                                {(doc.status === 'rejected' || doc.status === 'revision_required') &&
                                  (doc.uploaded_doc?.review_comment || doc.uploaded_doc?.comment) && (
                                    <div className="mt-1.5 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-start gap-1.5">
                                      <AlertCircle className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
                                      <div>
                                        <span className="font-semibold">Reason: </span>
                                        <span>
                                          {doc.uploaded_doc.review_comment || doc.uploaded_doc.comment}
                                        </span>
                                      </div>
                                    </div>
                                  )}
                              </div>
                            </div>

                            {/* RIGHT-HAND ACTIONS */}
                            <div className="shrink-0 flex items-center justify-end flex-wrap gap-2 w-full sm:w-auto mt-2 sm:mt-0">
                              {doc.is_payment_locked ? (
                                <Button
                                  size="sm"
                                  onClick={() =>
                                    handleStepPayment(doc.sale_id || step.sale_id, {
                                      step_order: step.step_order,
                                      payment_amount: doc.payment_pending_amount || step.payment_amount,
                                      label: 'Full Payment',
                                    })
                                  }
                                  className="bg-[#f7620b] hover:bg-[#e0580a] text-white text-xs h-8 px-3.5 font-bold shadow-xs flex items-center gap-1.5 rounded-md"
                                  data-testid={`pay-locked-doc-${sIdx}-${dIdx}-btn`}
                                >
                                  <CreditCard className="h-3.5 w-3.5" />
                                  Pay ₹{Number(doc.payment_pending_amount || step.payment_amount || 0).toLocaleString()} to Unlock
                                </Button>
                              ) : isLocked ? (
                                <Button
                                  disabled
                                  variant="outline"
                                  size="sm"
                                  className="opacity-60 cursor-not-allowed bg-slate-100 text-slate-500 border-slate-200 text-xs h-8 px-3"
                                >
                                  <Lock className="h-3.5 w-3.5 mr-1 text-slate-400" /> Locked
                                </Button>
                              ) : !doc.field_type || doc.field_type === 'file' ? (
                                <label
                                  className="cursor-pointer flex items-center"
                                  data-testid={`upload-btn-${sIdx}-${dIdx}`}
                                >
                                  <input
                                    type="file"
                                    multiple
                                    className="hidden"
                                    accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                                    onChange={(e) => {
                                      if (e.target.files && e.target.files.length > 0) {
                                        handleUpload(step.step_name, doc.doc_name, e.target.files);
                                        e.target.value = '';
                                      }
                                    }}
                                  />
                                  <span
                                    className={`inline-flex items-center gap-1.5 text-xs px-3 py-2 rounded-md font-semibold transition-colors cursor-pointer shadow-xs ${
                                      uploadedList.length > 0
                                        ? 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300'
                                        : 'bg-[#2a777a] hover:bg-[#236466] text-white'
                                    }`}
                                  >
                                    {uploading === uploadKey ? (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                      <Upload className="h-3.5 w-3.5" />
                                    )}
                                    {uploadedList.length > 0 ? '+ Upload More' : '+ Upload File(s)'}
                                  </span>
                                </label>
                              ) : (
                                  renderIntakeField(doc, step)
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
                <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-xs">
                  {additionalRequests.length}
                </Badge>
              </div>

              {additionalRequests.map((req, rIdx) => {
                const reqUploadList = (req.uploaded_docs && req.uploaded_docs.length > 0)
                  ? req.uploaded_docs
                  : (req.uploaded_doc ? [req.uploaded_doc] : []);
                const isComplete = reqUploadList.length > 0;

                return (
                  <Card
                    key={req.id || rIdx}
                    className={`overflow-hidden shadow-sm border-l-4 ${
                      isComplete ? 'border-l-emerald-500 bg-emerald-50/20' : 'border-l-leamss-orange-400'
                    }`}
                    data-testid={`additional-doc-${rIdx}`}
                  >
                    <div className="p-4">
                      <div className="flex flex-col sm:flex-row items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          {isComplete ? (
                            <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                          ) : (
                            <AlertCircle className="h-5 w-5 text-leamss-orange-400 flex-shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-sm text-slate-800 dark:text-white">
                                {req.doc_name}
                              </span>
                              <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">
                                Additional
                              </Badge>
                              <Badge
                                className={`text-[9px] ${
                                  req.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                                }`}
                              >
                                {req.tag || (req.is_mandatory ? 'Required' : 'Optional')}
                              </Badge>
                              {isComplete && (
                                <Badge className="text-[9px] bg-emerald-100 text-emerald-700 font-semibold">
                                  📄 {reqUploadList.length} {reqUploadList.length === 1 ? 'File' : 'Files'} Uploaded
                                </Badge>
                              )}
                            </div>
                            {req.notes && <p className="text-xs text-slate-500 mt-1">{req.notes}</p>}
                            <p className="text-[10px] text-slate-400 mt-1">
                              Requested by {req.requested_by_name || 'Case Manager'}{' '}
                              {req.created_at ? `on ${new Date(req.created_at).toLocaleDateString()}` : ''}
                            </p>

                            {/* LIST OF UPLOADED FILES UNDER ADDITIONAL REQUEST */}
                            {reqUploadList.length > 0 && (
                              <div className="mt-2.5 space-y-1.5">
                                {reqUploadList.map((uDoc, uIdx) => (
                                  <div
                                    key={uDoc.id || uIdx}
                                    className="flex items-center justify-between p-2 rounded-lg bg-white border border-emerald-200 gap-2"
                                  >
                                    <div className="flex items-center gap-2 min-w-0 flex-1">
                                      <FileText className="h-4 w-4 text-emerald-600 shrink-0" />
                                      <span className="text-xs font-semibold text-slate-700 truncate">
                                        {uDoc.filename}
                                      </span>
                                      <Badge className="text-[9px] bg-emerald-100 text-emerald-700 px-1.5 py-0 h-4">
                                        {uDoc.status || 'Uploaded'}
                                      </Badge>
                                    </div>
                                    <div className="flex items-center gap-1 shrink-0">
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-6 px-2 text-xs flex items-center gap-1 border-slate-200"
                                        onClick={() => downloadDocument(uDoc.id, uDoc.filename)}
                                      >
                                        <Download className="h-3 w-3 text-slate-600" />
                                        <span className="hidden sm:inline">Download</span>
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0 text-red-400 hover:text-red-600 hover:bg-red-50"
                                        title="Delete file"
                                        onClick={() => handleDeleteDoc(uDoc.id, uDoc.filename)}
                                      >
                                        <XCircle className="h-3 w-3" />
                                      </Button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        <label
                          className="cursor-pointer flex-shrink-0 mt-2 sm:mt-0"
                          data-testid={`upload-additional-${rIdx}`}
                        >
                          <input
                            type="file"
                            multiple
                            className="hidden"
                            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                            onChange={(e) => {
                              if (e.target.files && e.target.files.length > 0) {
                                handleAdditionalUpload(req.id, req.doc_name, e.target.files);
                                e.target.value = '';
                              }
                            }}
                          />
                          <span
                            className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md font-semibold transition-colors cursor-pointer shadow-xs ${
                              isComplete
                                ? 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300'
                                : 'bg-leamss-orange-600 hover:bg-leamss-orange-700 text-white'
                            }`}
                          >
                            {uploading === req.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Upload className="h-3.5 w-3.5" />
                            )}
                            {isComplete ? '+ Upload More' : '+ Upload File(s)'}
                          </span>
                        </label>
                      </div>
                    </div>
                  </Card>
                );
              })}
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

      {/* Installment Payment Modal with exact First Payment UI */}
      <ClientPaymentModal
        open={stepPaymentModalData.open}
        onClose={() => setStepPaymentModalData({ open: false, data: null })}
        paymentData={stepPaymentModalData.data}
        onSuccess={() => {
          loadData();
          onDocumentUploaded?.();
        }}
      />
    </div>
  );
};

export default UnifiedDocumentView;