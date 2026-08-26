import { useState, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { FileText, RefreshCw, Eye, Download, XCircle, ClipboardCheck, Upload, Loader2, FilePlus } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * PaDocumentsList — client documents panel (extracted from PreAssessmentPipeline.jsx).
 * Owns its own view/download/delete fetch handlers; relies on parent for refresh.
 * Splits documents into "Client Documents" and "Pre-Assessment Report" with direct Upload Report capability.
 */

// Shared row renderer used by both sections
function DocRow({ d, pa, getAuthHeader, onRefresh }) {
  const dlUrl = `${API}/pre-assessment/${pa.id}/document/${d.id}/download`;
  const tok = localStorage.getItem('token');

  const handleView = async () => {
    try {
      const r = await fetch(`${dlUrl}?inline=true`, { headers: { Authorization: `Bearer ${tok}` } });
      if (!r.ok) throw new Error('Fetch failed');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const w = window.open(url, '_blank');
      if (!w) toast.info('Popup blocked — allow popups to view');
    } catch (err) { toast.error('View failed'); }
  };

  const handleDownload = async () => {
    try {
      const r = await fetch(dlUrl, { headers: { Authorization: `Bearer ${tok}` } });
      if (!r.ok) throw new Error('Fetch failed');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = d.file_name;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error('Download failed'); }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${d.file_name}"? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/pre-assessment/${pa.id}/document/${d.id}`, getAuthHeader());
      toast.success('Document deleted');
      await onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Delete failed'); }
  };

  return (
    <div className="flex items-center gap-1.5 text-xs bg-white rounded px-2 py-1.5 border border-slate-100 shadow-2xs">
      <FileText className="h-3.5 w-3.5 text-blue-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-700 truncate">{d.file_name}</p>
        <p className="text-[10px] text-slate-400 capitalize">{d.document_type?.replace(/_/g, ' ')}</p>
      </div>
      <Button size="sm" variant="outline" onClick={handleView} className="h-6 text-[11px] px-2" data-testid={`view-doc-${d.id}`}>
        <Eye className="h-3 w-3 mr-0.5" /> View
      </Button>
      <Button size="sm" variant="outline" onClick={handleDownload} className="h-6 text-[11px] px-2" data-testid={`download-doc-${d.id}`}>
        <Download className="h-3 w-3 mr-0.5" /> Save
      </Button>
      <Button size="sm" variant="outline" onClick={handleDelete} className="h-6 text-[11px] px-1.5 text-red-500 hover:bg-red-50 border-red-200" data-testid={`delete-doc-${d.id}`}>
        <XCircle className="h-3 w-3" />
      </Button>
    </div>
  );
}

export default function PaDocumentsList({ pa, docs, onRefresh, getAuthHeader }) {
  const [uploadingReport, setUploadingReport] = useState(false);
  const reportInputRef = useRef(null);

  const handleReportUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingReport(true);
    const formData = new FormData();
    formData.append('document_type', 'pre_assessment_report');
    formData.append('file', file);

    try {
      await axios.post(`${API}/pre-assessment/${pa.id}/upload-document`, formData, {
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success(`Assessment Report uploaded: ${file.name}`);
      await onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Report upload failed');
    } finally {
      setUploadingReport(false);
      if (reportInputRef.current) reportInputRef.current.value = '';
    }
  };

  if (docs === undefined) {
    return (
      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> Client Documents</p>
        </div>
        <Button variant="link" size="sm" onClick={onRefresh} className="text-xs h-auto p-0">Click to load documents</Button>
      </div>
    );
  }

  // Split documents by type / role
  const isReportDoc = (d) => d.document_type === 'pre_assessment_report' || d.document_type === 'assessment_report' || d.uploaded_by_role === 'admin';
  const reportDocs = docs.filter(isReportDoc);
  const clientDocs = docs.filter(d => !isReportDoc(d));

  return (
    <div className="space-y-3">
      {/* Hidden file input for report upload */}
      <input
        type="file"
        ref={reportInputRef}
        className="hidden"
        accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
        onChange={handleReportUpload}
      />

      {/* ── Client Documents box ── */}
      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> Client Documents</p>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[11px] px-2 bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100"
              disabled={uploadingReport}
              onClick={() => reportInputRef.current?.click()}
              data-testid={`upload-report-btn-${pa.id}`}
            >
              {uploadingReport ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Upload className="h-3 w-3 mr-1" />}
              {uploadingReport ? 'Uploading Report...' : 'Upload Report'}
            </Button>
            <Button variant="ghost" size="sm" className="h-6 text-xs px-2" onClick={onRefresh} data-testid={`refresh-docs-${pa.id}`}>
              <RefreshCw className="h-3 w-3 mr-1" /> Refresh
            </Button>
          </div>
        </div>
        {clientDocs.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No documents yet</p>
        ) : (
          <div className="space-y-1.5">
            {clientDocs.map(d => (
              <DocRow key={d.id} d={d} pa={pa} getAuthHeader={getAuthHeader} onRefresh={onRefresh} />
            ))}
          </div>
        )}
      </div>

      {/* ── Pre-Assessment Report box ── */}
      {reportDocs.length > 0 && (
        <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-emerald-800 flex items-center gap-1">
              <ClipboardCheck className="h-3.5 w-3.5" /> Pre-Assessment Report ({reportDocs.length})
            </p>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 text-[11px] text-emerald-800 hover:bg-emerald-100"
              disabled={uploadingReport}
              onClick={() => reportInputRef.current?.click()}
            >
              <FilePlus className="h-3 w-3 mr-1" /> Upload Another / Replace
            </Button>
          </div>
          <div className="space-y-1.5">
            {reportDocs.map(d => (
              <DocRow key={d.id} d={d} pa={pa} getAuthHeader={getAuthHeader} onRefresh={onRefresh} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}