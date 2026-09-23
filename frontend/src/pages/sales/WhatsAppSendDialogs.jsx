import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  Loader2, Send, Users, FileWarning, MessageSquare, FileText, CheckCircle2, XCircle,
  Paperclip, QrCode, FileUser, Settings,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const Stat = ({ label, value, color = 'text-slate-800', testid }) => (
  <div className="rounded-lg border bg-white px-3 py-2 text-center" data-testid={testid}>
    <div className={`text-xl font-bold ${color}`}>{value}</div>
    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
  </div>
);

export function WhatsAppPreviewDialog({ batchId, headers, onClose, onConfirmed }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const [selectedTemplate, setSelectedTemplate] = useState('report_summary');
  const [customMessage, setCustomMessage] = useState('');
  const [attachReport, setAttachReport] = useState(true);
  const [attachResume, setAttachResume] = useState(true);
  const [attachSla, setAttachSla] = useState(true);
  const [attachQr, setAttachQr] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/bulk-assessments/${batchId}/whatsapp-preview`, { headers });
        setData(r.data);
        if (r.data.templates && r.data.templates.length > 0) {
          const first = r.data.templates[0];
          setSelectedTemplate(first.id || 'report_summary');
          if (first.attach_report !== undefined) setAttachReport(Boolean(first.attach_report));
          if (first.attach_resume !== undefined) setAttachResume(Boolean(first.attach_resume));
          if (first.attach_sla !== undefined) setAttachSla(Boolean(first.attach_sla));
          if (first.attach_qr !== undefined) setAttachQr(Boolean(first.attach_qr));
        }
      } catch (e) {
        toast.error('Could not load WhatsApp preview');
      } finally {
        setLoading(false);
      }
    })();
    /* eslint-disable-next-line */
  }, []);

  const handleTemplateChange = (tmplId) => {
    setSelectedTemplate(tmplId);
    const tmpl = (data?.templates || []).find(t => t.id === tmplId);
    if (tmpl) {
      if (tmpl.attach_report !== undefined) setAttachReport(Boolean(tmpl.attach_report));
      if (tmpl.attach_resume !== undefined) setAttachResume(Boolean(tmpl.attach_resume));
      if (tmpl.attach_sla !== undefined) setAttachSla(Boolean(tmpl.attach_sla));
      if (tmpl.attach_qr !== undefined) setAttachQr(Boolean(tmpl.attach_qr));
    }
  };

  const confirm = async () => {
    setSending(true);
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batchId}/whatsapp-all`, {
        template_id: selectedTemplate || null,
        custom_message: customMessage || null,
        attach_report: attachReport,
        attach_resume: attachResume,
        attach_sla: attachSla,
        attach_qr: attachQr,
      }, { headers });
      toast.success(`Sending WhatsApp messages to ${r.data.queued} client(s)…`);
      onConfirmed?.();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not start WhatsApp broadcast');
    } finally {
      setSending(false);
    }
  };

  const activeAttachmentsCount = [
    attachReport,
    attachResume,
    attachSla,
    attachQr,
  ].filter(Boolean).length;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg" data-testid="whatsapp-preview-dialog">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900">
              <MessageSquare className="h-5 w-5 text-emerald-600" />
              Confirm — Send WhatsApp to All Clients
            </DialogTitle>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 flex items-center gap-1 font-medium"
              onClick={() => { onClose(); navigate('/sales/whatsapp-templates'); }}
              data-testid="whatsapp-dialog-manage-templates-btn"
            >
              <Settings className="h-3.5 w-3.5 text-emerald-600" />
              Templates Manager
            </Button>
          </div>
          <DialogDescription className="text-xs text-slate-500">
            Selected WhatsApp template and document attachments will be dispatched directly to all clients with valid mobile numbers.
          </DialogDescription>
        </DialogHeader>

        {loading || !data ? (
          <div className="py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" />
          </div>
        ) : (
          <div className="space-y-3.5">
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Will receive WhatsApp" value={data.sendable} color="text-emerald-700" testid="preview-whatsapp-sendable" />
              <Stat label="Resumes Available" value={data.with_resume ?? 0} color="text-amber-700" testid="preview-whatsapp-resumes" />
              <Stat label="No phone number" value={data.missing_phone} color={data.missing_phone ? 'text-rose-600' : 'text-slate-400'} testid="preview-whatsapp-missing" />
            </div>

            {/* Template Selector */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">WhatsApp Template</label>
                <button
                  type="button"
                  onClick={() => { onClose(); navigate('/sales/whatsapp-templates'); }}
                  className="text-[10px] text-emerald-600 hover:underline font-medium"
                >
                  + Manage Templates
                </button>
              </div>
              <select
                value={selectedTemplate}
                onChange={e => handleTemplateChange(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-2.5 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                data-testid="whatsapp-template-select"
              >
                {(data?.templates || []).map(t => (
                  <option key={t.id} value={t.id}>{t.name} {t.description ? `— ${t.description}` : ''}</option>
                ))}
              </select>
            </div>

            {/* Custom Note */}
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1 block">Custom Note / Override Message</label>
              <textarea
                value={customMessage}
                onChange={e => setCustomMessage(e.target.value)}
                placeholder="Leave blank to use the selected template message above..."
                rows={2}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Attachments Section */}
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/30 p-3 space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-900 block">
                📎 Attachments to Dispatch ({activeAttachmentsCount})
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachReport ? 'bg-emerald-100/70 border-emerald-400 text-emerald-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachReport}
                    onChange={e => setAttachReport(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <FileText className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                  <span className="truncate">Report (23p)</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachResume ? 'bg-amber-100/70 border-amber-400 text-amber-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`} title={`${data.with_resume || 0} client(s) have resumes`}>
                  <input
                    type="checkbox"
                    checked={attachResume}
                    onChange={e => setAttachResume(e.target.checked)}
                    className="rounded text-amber-600 focus:ring-amber-500"
                  />
                  <FileUser className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                  <span className="truncate">Resume ({data.with_resume || 0})</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachSla ? 'bg-blue-100/70 border-blue-400 text-blue-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachSla}
                    onChange={e => setAttachSla(e.target.checked)}
                    className="rounded text-blue-600 focus:ring-blue-500"
                  />
                  <Paperclip className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                  <span className="truncate">SLA</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachQr ? 'bg-purple-100/70 border-purple-400 text-purple-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachQr}
                    onChange={e => setAttachQr(e.target.checked)}
                    className="rounded text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-xs">💳</span>
                  <span className="truncate">Payment QR</span>
                </label>
              </div>
            </div>

            {data.missing_phone > 0 && (
              <p className="text-[11px] text-slate-500 pt-0.5">
                Skipped (no phone): {data.missing_sample.join(', ')}
                {data.missing_phone > data.missing_sample.length ? ` +${data.missing_phone - data.missing_sample.length} more` : ''}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="preview-whatsapp-cancel">Cancel</Button>
          <Button
            onClick={confirm}
            disabled={sending || loading || !data?.sendable}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
            data-testid="preview-whatsapp-confirm"
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
            Send to {data?.sendable || 0} clients
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
