import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileCheck, CheckCircle2, Download } from 'lucide-react';
import SignatureCanvas from '@/components/SignatureCanvas';
import './agreement-doc.css';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * ClientAgreementSigning — shows the latest agreement for a PA, full body preview,
 * scroll-to-end gate, then canvas signature.
 */
export default function ClientAgreementSigning({ paId, onSigned }) {
  const [agreement, setAgreement] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scrolledToEnd, setScrolledToEnd] = useState(false);
  const [saving, setSaving] = useState(false);

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/pa-agreements/pa/${paId}`, auth());
      const items = r.data || [];
      if (items.length === 0) {
        setAgreement(null);
      } else {
        // Get the latest one with full HTML
        const latest = items[0];
        const full = await axios.get(`${API}/pa-agreements/${latest.id}`, auth());
        setAgreement(full.data);
      }
    } catch (e) { /* silent */ }
    setLoading(false);
  }, [paId]);

  useEffect(() => { load(); }, [load]);

  const handleScroll = (e) => {
    const el = e.target;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) {
      setScrolledToEnd(true);
    }
  };

  const handleSave = async (dataUrl, meta) => {
    if (!agreement) return;
    setSaving(true);
    try {
      const r = await axios.post(`${API}/pa-agreements/${agreement.id}/sign`, {
        signature_data_url: dataUrl,
        typed_name: meta.typed_name,
        consent_text: `I electronically sign agreement ${agreement.reference_id}`,
      }, auth());
      toast.success(`Agreement signed · ${new Date(r.data.signed_at).toLocaleString()}`);
      onSigned && onSigned(r.data);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Sign failed'); }
    setSaving(false);
  };

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

  if (loading) return <Card className="p-4"><p className="text-xs text-slate-400">Loading agreement…</p></Card>;
  if (!agreement) return null;

  // If signed — show confirmation card
  if (agreement.status === 'signed') {
    return (
      <Card className="p-5 border-emerald-200 bg-emerald-50" data-testid="agreement-signed">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 bg-emerald-500 rounded-full flex items-center justify-center shrink-0">
            <CheckCircle2 className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-emerald-900">Agreement Signed Successfully</h3>
            <p className="text-xs text-emerald-700 mt-0.5">
              {agreement.template_name} · Reference: <span className="font-mono">{agreement.reference_id}</span>
            </p>
            <p className="text-[11px] text-emerald-600 mt-1">
              Signed by <strong>{agreement.signed_by_typed_name}</strong> on {new Date(agreement.signed_at).toLocaleString()}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={downloadPdf} className="border-emerald-300 text-emerald-700 hover:bg-emerald-100" data-testid="dl-signed-pdf">
            <Download className="h-3.5 w-3.5 mr-1" /> Download Signed PDF
          </Button>
        </div>
      </Card>
    );
  }

  // Pending — full agreement view + scroll gate + signature
  return (
    <Card className="border-amber-200 bg-amber-50/50 overflow-hidden" data-testid="agreement-pending">
      <div className="p-4 border-b border-amber-200 bg-amber-100/50 flex items-center gap-3">
        <FileCheck className="h-5 w-5 text-amber-700 shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-amber-900">Service Agreement Awaiting Your Signature</h3>
          <p className="text-xs text-amber-700">{agreement.template_name} · Ref: <span className="font-mono">{agreement.reference_id}</span></p>
        </div>
        <Badge className="bg-amber-200 text-amber-900 h-6">Pending Signature</Badge>
      </div>
      <div
        className="agreement-doc-wrap max-h-[480px] overflow-y-auto border-b border-amber-200"
        onScroll={handleScroll}
        data-testid="agreement-body"
      >
        <div dangerouslySetInnerHTML={{ __html: agreement.rendered_html }} />
      </div>
      {!scrolledToEnd ? (
        <div className="p-4 text-center bg-amber-50">
          <p className="text-xs text-amber-700">📜 Please scroll through the entire agreement before signing.</p>
        </div>
      ) : (
        <div className="p-4 bg-white">
          <p className="text-xs text-emerald-700 mb-3 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> You've reviewed the entire agreement. Please sign below.
          </p>
          <SignatureCanvas onSigned={handleSave} disabled={saving} />
        </div>
      )}
    </Card>
  );
}
