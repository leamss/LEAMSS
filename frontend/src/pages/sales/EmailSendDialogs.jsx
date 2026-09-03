import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  Loader2, Send, Users, FileWarning, Mail, CheckCircle2, XCircle, FileText, Paperclip,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Stat = ({ label, value, color = 'text-slate-800', testid }) => (
  <div className="rounded-lg border bg-white px-3 py-2 text-center" data-testid={testid}>
    <div className={`text-xl font-bold ${color}`}>{value}</div>
    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
  </div>
);

export function EmailPreviewDialog({ batchId, headers, onClose, onConfirmed }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/bulk-assessments/${batchId}/email-preview`, { headers });
        setData(r.data);
      } catch (e) { toast.error('Could not load preview'); }
      finally { setLoading(false); }
    })();
    /* eslint-disable-next-line */
  }, []);

  const confirm = async () => {
    setSending(true);
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batchId}/email-all`, { bcc_self: true }, { headers });
      toast.success(`Emailing ${r.data.queued} report(s)…`);
      onConfirmed?.();
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Could not start emailing'); }
    finally { setSending(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg" data-testid="email-preview-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Send className="h-4 w-4" />Confirm — Email All Reports</DialogTitle>
          <DialogDescription className="text-[12px]">Bhejne se pehle ek final check. Neeche dekh lijiye kitne clients ko, kis mailbox se, aur kya-kya attach hoga.</DialogDescription>
        </DialogHeader>

        {loading || !data ? (
          <div className="py-12 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Will be sent" value={data.sendable} color="text-teal-700" testid="preview-sendable" />
              <Stat label="No email (skip)" value={data.missing_email} color={data.missing_email ? 'text-amber-600' : 'text-slate-400'} testid="preview-missing" />
              <Stat label="With resume" value={data.with_resume} color="text-indigo-600" testid="preview-resume" />
            </div>

            <div className="rounded-lg border p-2.5">
              <p className="text-[11px] font-semibold text-slate-600 flex items-center gap-1 mb-1.5"><Users className="h-3.5 w-3.5" />Sending from</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {data.by_consultant.map((c) => (
                  <div key={c.email} className="flex justify-between text-[11px]" data-testid={`preview-consultant-${c.email}`}>
                    <span className="text-slate-700 truncate">{c.name} <span className="text-slate-400">· {c.email || 'default'}</span></span>
                    <span className="font-bold text-slate-800">{c.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              <span className="text-[10px] px-2 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200"><FileText className="h-3 w-3 inline mr-1" />Report PDF</span>
              {data.attach_sla && <span className="text-[10px] px-2 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200"><Paperclip className="h-3 w-3 inline mr-1" />SLA</span>}
              {data.attach_qr && <span className="text-[10px] px-2 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">Payment QR</span>}
              {data.attach_resume && <span className="text-[10px] px-2 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">Resume ({data.with_resume})</span>}
              {data.offer_enabled && <span className="text-[10px] px-2 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Offer banner</span>}
            </div>

            {data.attach_resume && data.without_resume > 0 && (
              <p className="text-[11px] text-amber-700 flex items-start gap-1" data-testid="preview-resume-warn">
                <FileWarning className="h-3.5 w-3.5 mt-0.5 shrink-0" />{data.without_resume} client(s) ka resume link nahi mila — unki report bina resume ke jaayegi.
              </p>
            )}
            {data.missing_email > 0 && (
              <p className="text-[11px] text-slate-500">Skipped (no email): {data.missing_sample.join(', ')}{data.missing_email > data.missing_sample.length ? ` +${data.missing_email - data.missing_sample.length} more` : ''}</p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="preview-cancel">Cancel</Button>
          <Button onClick={confirm} disabled={sending || loading || !data?.sendable} className="bg-indigo-600 hover:bg-indigo-700" data-testid="preview-confirm-send">
            {sending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}Send to {data?.sendable || 0} clients
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function EmailSummaryDialog({ batchId, headers, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/bulk-assessments/${batchId}/email-summary`, { headers });
        setData(r.data);
      } catch (e) { toast.error('Could not load summary'); }
      finally { setLoading(false); }
    })();
    /* eslint-disable-next-line */
  }, []);

  const t = data?.totals || {};
  const List = ({ title, items, render, color, testid }) => items?.length ? (
    <div className="rounded-lg border p-2.5" data-testid={testid}>
      <p className={`text-[11px] font-semibold mb-1.5 ${color}`}>{title} ({items.length})</p>
      <div className="space-y-1 max-h-40 overflow-y-auto">{items.map((x, i) => <div key={i} className="text-[11px] text-slate-600">{render(x)}</div>)}</div>
    </div>
  ) : null;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[88vh] overflow-y-auto" data-testid="email-summary-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Mail className="h-4 w-4" />Email Send Summary</DialogTitle>
          <DialogDescription className="text-[12px]">Is batch mein kisko gaya, kiska resume nahi mila, aur kaunse fail huye.</DialogDescription>
        </DialogHeader>

        {loading || !data ? (
          <div className="py-12 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-2">
              <Stat label="Sent" value={t.sent || 0} color="text-emerald-600" testid="summary-sent" />
              <Stat label="Failed" value={t.failed || 0} color={t.failed ? 'text-rose-600' : 'text-slate-400'} testid="summary-failed" />
              <Stat label="Skipped" value={t.skipped || 0} color={t.skipped ? 'text-amber-600' : 'text-slate-400'} testid="summary-skipped" />
              <Stat label="No resume" value={t.resume_missing || 0} color={t.resume_missing ? 'text-indigo-600' : 'text-slate-400'} testid="summary-noresume" />
            </div>

            {data.by_consultant?.length > 0 && (
              <div className="rounded-lg border p-2.5">
                <p className="text-[11px] font-semibold text-slate-600 mb-1.5">Sent from</p>
                {data.by_consultant.map((c) => (
                  <div key={c.from} className="flex justify-between text-[11px]"><span className="text-slate-600 truncate">{c.from}</span><span className="font-bold">{c.count}</span></div>
                ))}
              </div>
            )}

            <List title="Failed" items={data.failed} color="text-rose-600" testid="summary-failed-list"
              render={(x) => <><CheckCircle2 className="hidden" /><XCircle className="h-3 w-3 inline text-rose-400 mr-1" />{x.name} <span className="text-slate-400">· {x.email}</span> — <span className="text-rose-500">{x.error}</span></>} />
            <List title="Resume missing" items={data.resume_missing} color="text-indigo-600" testid="summary-resume-list"
              render={(x) => <>{x.name} <span className="text-slate-400">— {x.reason}</span></>} />
            <List title="Skipped (no email)" items={data.skipped} color="text-amber-600" testid="summary-skipped-list"
              render={(x) => <>{x.name} <span className="text-slate-400">— {x.reason}</span></>} />
            <List title="Delivered" items={data.sent} color="text-emerald-600" testid="summary-sent-list"
              render={(x) => <><CheckCircle2 className="h-3 w-3 inline text-emerald-500 mr-1" />{x.name} <span className="text-slate-400">· {x.email}</span></>} />
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="summary-close">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
