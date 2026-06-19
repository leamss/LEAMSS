/**
 * Phase 19.11 — Pre-Assessment Report Generator.
 *
 * Compact button + modal for generating WeasyPrint Pre-Assessment Report PDF.
 * Usable from Smart Sales Helper, Verify Hub, or Client Detail pages.
 */
import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { FileDown, Loader2, X, Eye } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token')}` };
}

export function PreAssessmentReportButton({ countryCode, occupationCode, occupationTitle, defaultClient = {}, size = 'default' }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [client, setClient] = useState({
    name: defaultClient.name || '',
    email: defaultClient.email || '',
    phone: defaultClient.phone || '',
    age: defaultClient.age || '',
    english_score: defaultClient.english_score || '',
    work_exp_years: defaultClient.work_exp_years || '',
  });
  const [previewUrl, setPreviewUrl] = useState(null);

  const generate = async (preview = false) => {
    setBusy(true);
    try {
      const payload = {
        client: {
          name: client.name,
          email: client.email,
          phone: client.phone,
          age: client.age ? Number(client.age) : null,
          english_score: client.english_score,
          work_exp_years: client.work_exp_years ? Number(client.work_exp_years) : null,
        },
        country_code: countryCode,
        occupation_code: occupationCode,
        preview_html: preview,
      };
      const r = await axios.post(`${API}/reports/pre-assessment`, payload, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        responseType: preview ? 'text' : 'blob',
      });
      if (preview) {
        const blob = new Blob([r.data], { type: 'text/html' });
        setPreviewUrl(URL.createObjectURL(blob));
        toast.info('HTML preview ready · review before downloading PDF');
      } else {
        const blob = new Blob([r.data], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const ref = r.headers['x-report-ref'] || 'XXXXXXXX';
        a.href = url;
        a.download = `leamss_pre_assessment_${occupationCode}_${ref}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(`Pre-Assessment Report downloaded · Ref ${ref}`);
        setOpen(false);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Generation failed');
    } finally { setBusy(false); }
  };

  return (
    <>
      <Button
        size={size}
        onClick={() => setOpen(true)}
        className="bg-amber-600 hover:bg-amber-700 text-white"
        data-testid="generate-pre-assessment-btn"
      >
        <FileDown className="h-3.5 w-3.5 mr-1" />
        Generate Pre-Assessment Report
      </Button>

      {open && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="pa-report-modal">
          <Card className="w-full max-w-2xl p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-base font-bold">Pre-Assessment Report</h3>
                <p className="text-xs text-slate-500">{countryCode} · {occupationCode} · {occupationTitle}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}><X className="h-4 w-4" /></Button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="col-span-2">
                <label className="text-[10px] font-semibold text-slate-700 uppercase">Client Name *</label>
                <Input value={client.name} onChange={e => setClient({...client, name: e.target.value})} placeholder="e.g. Rajesh Sharma" data-testid="pa-client-name" />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-700 uppercase">Email</label>
                <Input value={client.email} onChange={e => setClient({...client, email: e.target.value})} placeholder="client@example.com" data-testid="pa-client-email" />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-700 uppercase">Phone</label>
                <Input value={client.phone} onChange={e => setClient({...client, phone: e.target.value})} placeholder="+91 ..." data-testid="pa-client-phone" />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-700 uppercase">Age</label>
                <Input type="number" value={client.age} onChange={e => setClient({...client, age: e.target.value})} placeholder="29" data-testid="pa-client-age" />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-700 uppercase">English Score</label>
                <Input value={client.english_score} onChange={e => setClient({...client, english_score: e.target.value})} placeholder="IELTS 7.5" data-testid="pa-client-english" />
              </div>
              <div className="col-span-2">
                <label className="text-[10px] font-semibold text-slate-700 uppercase">Work Experience (years)</label>
                <Input type="number" value={client.work_exp_years} onChange={e => setClient({...client, work_exp_years: e.target.value})} placeholder="6" data-testid="pa-client-experience" />
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded p-2 mt-3 text-[10px] text-amber-800">
              Report ships in PDF format (WeasyPrint, Phase 19.11). Includes salary + INR conversion, growth projection, assessing body, state nomination demand, visa pathways, indicative timeline (8-18 months), and next-steps CTA. Cached 5 mins per client.
            </div>

            <div className="flex justify-end gap-2 mt-4 pt-3 border-t">
              <Button variant="outline" onClick={() => generate(true)} disabled={busy || !client.name} data-testid="pa-preview-btn">
                {busy ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Eye className="h-3.5 w-3.5 mr-1" />}
                HTML Preview
              </Button>
              <Button onClick={() => generate(false)} disabled={busy || !client.name} className="bg-amber-600 hover:bg-amber-700" data-testid="pa-download-pdf-btn">
                {busy ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <FileDown className="h-3.5 w-3.5 mr-1" />}
                Generate PDF
              </Button>
            </div>

            {previewUrl && (
              <div className="mt-3 border rounded">
                <div className="bg-slate-100 px-2 py-1 flex justify-between items-center">
                  <span className="text-[10px] text-slate-600">HTML Preview</span>
                  <Button size="sm" variant="ghost" onClick={() => setPreviewUrl(null)}><X className="h-3 w-3" /></Button>
                </div>
                <iframe src={previewUrl} title="report-preview" className="w-full h-96 border-0" data-testid="pa-preview-iframe" />
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  );
}

export default PreAssessmentReportButton;
