import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Upload, Send, FileText } from 'lucide-react';

/**
 * PaFinalSubmitForm — proposal_paid → awaiting_final_approval upload + submit form.
 */
export default function PaFinalSubmitForm({
  pa, pendingUpload, uploading, stageFile, confirmUpload, clearPendingFile,
  finalNotes, setFinalNotes, handleSubmitFinal, onCancel,
}) {
  return (
    <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
      <p className="text-sm font-semibold text-orange-900 mb-2 flex items-center gap-2">
        <Upload className="h-4 w-4" /> Upload Receipt / Agreement / Basic Docs
      </p>
      <p className="text-xs text-orange-700 mb-3">Client paid ₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}. Upload payment receipt + signed agreement + any basic docs, then submit to Admin for final approval.</p>
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <select id={`finalDocType-${pa.id}`} className="border border-orange-200 rounded-md px-3 py-2 text-sm bg-white" data-testid={`final-doc-type-${pa.id}`}>
          <option value="receipt">Payment Receipt</option>
          <option value="agreement">Signed Agreement</option>
          <option value="passport">Passport</option>
          <option value="other">Other Basic Doc</option>
        </select>
        <Input type="file" className="flex-1 min-w-[200px]" id={`finalFileInput-${pa.id}`}
          onChange={(e) => {
            const file = e.target.files[0];
            if (file) {
              const docType = document.getElementById(`finalDocType-${pa.id}`).value;
              stageFile(pa.id, file, docType);
            }
          }} data-testid="final-doc-upload" />
      </div>
      {pendingUpload && (
        <div className="mb-3 flex items-center gap-2 bg-white rounded-md p-2 border border-orange-200">
          <FileText className="h-4 w-4 text-orange-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-700 truncate">{pendingUpload.file.name}</p>
            <p className="text-[10px] text-slate-500 capitalize">{pendingUpload.docType} · {(pendingUpload.file.size / 1024).toFixed(1)} KB</p>
          </div>
          <Button size="sm" onClick={() => confirmUpload(pa.id)} disabled={uploading}
            className="h-7 text-xs bg-orange-600 hover:bg-orange-700 text-white" data-testid={`final-upload-btn-${pa.id}`}>
            <Upload className="h-3 w-3 mr-1" /> {uploading ? 'Uploading...' : 'Upload'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => { clearPendingFile(pa.id); const el = document.getElementById(`finalFileInput-${pa.id}`); if (el) el.value = ''; }}
            className="h-7 text-xs" data-testid={`final-cancel-upload-${pa.id}`}>
            Cancel
          </Button>
        </div>
      )}
      <label className="text-xs font-medium text-slate-600 block mb-1">Notes for admin (optional)</label>
      <textarea value={finalNotes} onChange={e => setFinalNotes(e.target.value)}
        className="w-full border rounded-md px-3 py-2 text-sm h-16"
        placeholder="e.g. All docs verified. Client ready for case activation." />
      <div className="flex justify-end gap-2 mt-3">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => handleSubmitFinal(pa.id)}
          className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="confirm-submit-final">
          <Send className="h-4 w-4 mr-1" /> Submit to Admin for Final Approval
        </Button>
      </div>
    </div>
  );
}
