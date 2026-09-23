import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  Loader2, Send, Users, FileWarning, MessageSquare, FileText, CheckCircle2, XCircle,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Stat = ({ label, value, color = 'text-slate-800', testid }) => (
  <div className="rounded-lg border bg-white px-3 py-2 text-center" data-testid={testid}>
    <div className={`text-xl font-bold ${color}`}>{value}</div>
    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
  </div>
);

export function WhatsAppPreviewDialog({ batchId, headers, onClose, onConfirmed }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/bulk-assessments/${batchId}/whatsapp-preview`, { headers });
        setData(r.data);
      } catch (e) {
        toast.error('Could not load WhatsApp preview');
      } finally {
        setLoading(false);
      }
    })();
    /* eslint-disable-next-line */
  }, []);

  const confirm = async () => {
    setSending(true);
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batchId}/whatsapp-all`, {}, { headers });
      toast.success(`Sending WhatsApp messages to ${r.data.queued} client(s)…`);
      onConfirmed?.();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not start WhatsApp broadcast');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg" data-testid="whatsapp-preview-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-emerald-600" />
            Confirm — Send WhatsApp to All Clients
          </DialogTitle>
          <DialogDescription className="text-[12px]">
            The official Pre-Assessment PDF report will be sent directly to each client's WhatsApp number.
          </DialogDescription>
        </DialogHeader>

        {loading || !data ? (
          <div className="py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" />
          </div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Will receive WhatsApp" value={data.sendable} color="text-emerald-700" testid="preview-whatsapp-sendable" />
              <Stat label="No phone number (skip)" value={data.missing_phone} color={data.missing_phone ? 'text-amber-600' : 'text-slate-400'} testid="preview-whatsapp-missing" />
            </div>

            <div className="flex flex-wrap gap-1.5 pt-1">
              <span className="text-[10px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                <FileText className="h-3 w-3 inline mr-1" />
                Pre-Assessment Report PDF Attached
              </span>
              <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Direct WhatsApp API
              </span>
            </div>

            {data.missing_phone > 0 && (
              <p className="text-[11px] text-slate-500 pt-1">
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
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
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
