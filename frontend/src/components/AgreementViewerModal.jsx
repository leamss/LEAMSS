import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Download, RefreshCw, FileText } from 'lucide-react';
import './agreement-doc.css';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Modal that shows an existing agreement for a PA — read-only view + download + regenerate.
 */
export default function AgreementViewerModal({ pa, onClose, onRegenerate }) {
  const [agreement, setAgreement] = useState(null);
  const [loading, setLoading] = useState(true);

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    (async () => {
      try {
        const list = await axios.get(`${API}/pa-agreements/pa/${pa.id}`, auth());
        if (!list.data || list.data.length === 0) { setAgreement(null); setLoading(false); return; }
        const full = await axios.get(`${API}/pa-agreements/${list.data[0].id}`, auth());
        setAgreement(full.data);
      } catch (e) { /* silent */ }
      setLoading(false);
    })();
  }, [pa.id]);

  const downloadPdf = async () => {
    if (!agreement) return;
    try {
      const r = await fetch(`${API}/pa-agreements/${agreement.id}/pdf`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      window.open(u, '_blank');
      setTimeout(() => URL.revokeObjectURL(u), 60000);
    } catch { toast.error('Download failed'); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[92vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()} data-testid="agreement-viewer-modal">
        <div className="p-4 border-b flex items-center justify-between bg-gradient-to-r from-leamss-teal-500 to-leamss-orange-600 text-white">
          <div>
            <h3 className="font-bold flex items-center gap-2"><FileText className="h-5 w-5" /> Service Agreement</h3>
            <p className="text-xs opacity-80">{pa.client_name} · {pa.country}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0 text-white hover:bg-white/20"><X className="h-4 w-4" /></Button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading…</div>
        ) : !agreement ? (
          <div className="p-8 text-center text-slate-400">No agreement found.</div>
        ) : (
          <>
            <div className="px-4 py-3 border-b bg-slate-50 flex items-center justify-between flex-wrap gap-2">
              <div>
                <p className="text-xs text-slate-500">Reference</p>
                <p className="font-mono text-sm font-bold text-slate-800">{agreement.reference_id}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Template</p>
                <p className="text-sm">{agreement.template_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Status</p>
                {agreement.status === 'signed'
                  ? <Badge className="bg-emerald-100 text-emerald-700">✓ Signed by Client</Badge>
                  : <Badge className="bg-amber-100 text-amber-700">Pending Client Signature</Badge>}
              </div>
              <div>
                <p className="text-xs text-slate-500">Generated</p>
                <p className="text-xs">{agreement.generated_at ? new Date(agreement.generated_at).toLocaleString() : '—'}</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto agreement-doc-wrap" data-testid="agreement-body-viewer">
              <div dangerouslySetInnerHTML={{ __html: agreement.rendered_html }} />
            </div>

            <div className="p-3 border-t bg-slate-50 flex items-center justify-between">
              <Button variant="outline" size="sm" onClick={onRegenerate} data-testid="regenerate-agreement">
                <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate (new template / variables)
              </Button>
              <Button size="sm" onClick={downloadPdf} className="bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="dl-agreement-pdf">
                <Download className="h-3.5 w-3.5 mr-1" /> Download PDF
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
