import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { FileText, RefreshCw, Eye, Download, XCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * PaDocumentsList — client documents panel (extracted from PreAssessmentPipeline.jsx).
 * Owns its own view/download/delete fetch handlers; relies on parent for refresh.
 */
export default function PaDocumentsList({ pa, docs, onRefresh, getAuthHeader }) {
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

  return (
    <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-slate-700 flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> Client Documents</p>
        <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={onRefresh} data-testid={`refresh-docs-${pa.id}`}>
          <RefreshCw className="h-3 w-3 mr-1" /> Refresh
        </Button>
      </div>
      {docs.length === 0 ? (
        <p className="text-xs text-slate-400 italic">No documents yet</p>
      ) : (
        <div className="space-y-1.5">
          {docs.map(d => {
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
              <div key={d.id} className="flex items-center gap-1.5 text-xs bg-white rounded px-2 py-1.5 border border-slate-100">
                <FileText className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-700 truncate">{d.file_name}</p>
                  <p className="text-[10px] text-slate-400 capitalize">{d.document_type}</p>
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
          })}
        </div>
      )}
    </div>
  );
}
