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
          <div className="space-y-3">
            <div className="flex items-center gap-2 p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Resume extracted successfully! Review the extracted details below:</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 text-xs max-h-80 overflow-y-auto">
              {/* Candidate Info */}
              <div className="grid grid-cols-2 gap-2 border-b pb-2.5">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Candidate Name</span>
                  <span className="font-semibold text-slate-800">{extracted.name || extracted.client_name || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Email</span>
                  <span className="font-semibold text-slate-800 truncate block">{extracted.email || extracted.client_email || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Phone</span>
                  <span className="font-semibold text-slate-800">{extracted.phone || extracted.client_phone || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Age / DOB</span>
                  <span className="font-semibold text-slate-800">
                    {extracted.primary_applicant?.age ? `${extracted.primary_applicant.age} yrs` : (extracted.primary_applicant?.dob || '—')}
                  </span>
                </div>
              </div>

              {/* Education & Experience */}
              <div className="grid grid-cols-2 gap-2 border-b pb-2.5">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Highest Qualification</span>
                  <span className="font-semibold text-slate-800 capitalize">{extracted.primary_applicant?.highest_qualification || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Field of Study</span>
                  <span className="font-semibold text-slate-800">{extracted.primary_applicant?.field_of_study || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Current Profession</span>
                  <span className="font-semibold text-slate-800">{extracted.primary_applicant?.current_profession || extracted.primary_applicant?.nominated_occupation_title || '—'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Experience</span>
                  <span className="font-semibold text-slate-800">
                    {extracted.primary_applicant?.experience_years_overall != null ? `${extracted.primary_applicant.experience_years_overall} years` : '—'}
                  </span>
                </div>
              </div>

              {/* Language & Marital */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Language Test</span>
                  <span className="font-semibold text-slate-800">
                    {extracted.primary_applicant?.primary_language_test || 'IELTS'} 
                    {extracted.primary_applicant?.test_completed ? ' (Completed)' : ' (Planned)'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Marital Status</span>
                  <span className="font-semibold text-slate-800 capitalize">{extracted.primary_applicant?.marital_status || 'Never Married / Single'}</span>
                </div>
              </div>
            </div>

            <div className="flex gap-2 justify-end pt-2">
              <Button variant="outline" size="sm" onClick={() => setExtracted(null)}>Upload Different Resume</Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium" onClick={() => onExtracted(extracted)} data-testid="use-extracted-data">
                <CheckCircle2 className="h-4 w-4 mr-1.5" />Use Extracted Details
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
