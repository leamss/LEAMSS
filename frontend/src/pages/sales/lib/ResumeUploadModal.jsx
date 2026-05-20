// Resume Upload Modal — opens from Step 3, calls /eligibility/profiles/resume-extract
import { useState, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Bot, CheckCircle2, Loader2, Upload } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API } from './constants';

export default function ResumeUploadModal({ onClose, onExtracted, headers }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const inputRef = useRef(null);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/eligibility/profiles/resume-extract`, form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        timeout: 90000,
      });
      setExtracted(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Resume extraction failed'));
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="resume-modal">
      <Card className="max-w-xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-bold flex items-center gap-2 mb-3">
          <Upload className="h-5 w-5 text-indigo-600" />Upload Resume
        </h3>
        {!extracted ? (
          <>
            <p className="text-[11px] text-slate-500 mb-3">PDF, DOCX or TXT · Max 10 MB · AI extracts the profile in 10-20 sec.</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={e => setFile(e.target.files?.[0])}
              className="block w-full text-sm"
              data-testid="resume-file-input"
            />
            {file && (
              <div className="mt-2 p-2 bg-slate-50 rounded text-xs">
                📄 {file.name} ({(file.size / 1024).toFixed(0)} KB)
              </div>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={submit} disabled={!file || loading} data-testid="resume-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading ? 'Extracting…' : 'Parse Resume with AI'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-[11px] text-emerald-700 bg-emerald-50 p-2 rounded mb-3">✅ Resume parsed. Review the data and use it.</p>
            <pre className="bg-slate-50 p-2 rounded text-[10px] max-h-72 overflow-auto">
              {JSON.stringify({
                name: extracted.name,
                primary_applicant: extracted.primary_applicant,
              }, null, 2)}
            </pre>
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={() => setExtracted(null)}>Re-parse</Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => onExtracted(extracted)} data-testid="use-extracted-data">
                <CheckCircle2 className="h-3 w-3 mr-1" />Use This Data
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
