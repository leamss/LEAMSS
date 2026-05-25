// Step 1 — Capture client name + optional email/phone + send Info Sheet CTA (Phase 7.4)
import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { User, Send, Copy, Loader2, ExternalLink, MessageSquare } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Step1Start({ data, update }) {
  const [sending, setSending] = useState(false);
  const [linkInfo, setLinkInfo] = useState(null);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const sendInfoSheet = async () => {
    if (!data.client_name) {
      toast.error('Client name required first');
      return;
    }
    if (!data.client_email && !data.client_phone) {
      toast.error('Email or phone required to send the Info Sheet link');
      return;
    }
    setSending(true);
    try {
      const r = await axios.post(`${API}/eligibility/info-sheet/generate-link`, {
        client_name: data.client_name,
        client_email: data.client_email || undefined,
        client_phone: data.client_phone || undefined,
      }, { headers });
      setLinkInfo(r.data);
      toast.success('Info Sheet link generated — copy + share with client');
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to generate link'));
    } finally { setSending(false); }
  };

  const copyLink = () => {
    const url = linkInfo?.public_url || `${window.location.origin}/info-sheet/${linkInfo?.token}`;
    navigator.clipboard.writeText(url);
    toast.success('Link copied to clipboard');
  };

  const openWhatsApp = () => {
    if (!data.client_phone) {
      toast.error('Client phone required for WhatsApp');
      return;
    }
    const url = linkInfo?.public_url || `${window.location.origin}/info-sheet/${linkInfo?.token}`;
    const message = encodeURIComponent(
      `Hi ${data.client_name},\n\nPlease fill your details using this secure link from LEAMSS:\n\n${url}\n\nThis helps us prepare your migration assessment accurately.\n\n— Team LEAMSS\nWe Value Emotions ❤️`,
    );
    const phone = data.client_phone.replace(/\D/g, '');
    window.open(`https://wa.me/${phone}?text=${message}`, '_blank');
  };

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <User className="h-5 w-5 text-indigo-600" />Start a New Assessment
      </h2>
      <p className="text-sm text-slate-600">Enter the client's basic contact info. You can edit these later.</p>
      <div>
        <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Client Name *</Label>
        <Input value={data.client_name} onChange={e => update('client_name', e.target.value)} placeholder="e.g., Rajesh Kumar" data-testid="ca-client-name" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Email</Label>
          <Input type="email" value={data.client_email} onChange={e => update('client_email', e.target.value)} placeholder="optional" data-testid="ca-client-email" />
        </div>
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Phone</Label>
          <Input value={data.client_phone} onChange={e => update('client_phone', e.target.value)} placeholder="optional" data-testid="ca-client-phone" />
        </div>
      </div>

      {/* Phase 7.4 — Send Info Sheet CTA */}
      <Card className="p-4 bg-gradient-to-r from-emerald-50 to-blue-50 border-l-4 border-l-emerald-500" data-testid="info-sheet-cta">
        <h3 className="text-sm font-bold text-emerald-900 flex items-center gap-2 mb-1">
          <Send className="h-4 w-4" />Save time — let the client self-fill
        </h3>
        <p className="text-[11px] text-slate-600 mb-3">
          Generate a secure link for the client to fill their own profile, education, work experience, and language scores.
          Once submitted, this wizard's Step 3 will auto-populate.
        </p>
        {!linkInfo ? (
          <Button
            size="sm"
            onClick={sendInfoSheet}
            disabled={sending || !data.client_name}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            data-testid="generate-infosheet-btn"
          >
            {sending ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Send className="h-3 w-3 mr-1" />}
            {sending ? 'Generating…' : 'Generate Info Sheet Link'}
          </Button>
        ) : (
          <div className="space-y-2" data-testid="info-sheet-link-card">
            <div className="bg-white p-2 rounded border text-[11px] font-mono text-slate-700 truncate">
              {linkInfo.public_url || `${window.location.origin}/info-sheet/${linkInfo.token}`}
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button size="sm" variant="outline" onClick={copyLink} className="h-7 text-[10px]" data-testid="copy-link-btn">
                <Copy className="h-3 w-3 mr-1" />Copy Link
              </Button>
              <Button size="sm" variant="outline"
                onClick={() => window.open(linkInfo.public_url || `${window.location.origin}/info-sheet/${linkInfo.token}`, '_blank')}
                className="h-7 text-[10px]" data-testid="open-link-btn">
                <ExternalLink className="h-3 w-3 mr-1" />Open
              </Button>
              {data.client_phone && (
                <Button size="sm" variant="outline" onClick={openWhatsApp}
                  className="h-7 text-[10px] border-emerald-300 text-emerald-700" data-testid="whatsapp-btn">
                  <MessageSquare className="h-3 w-3 mr-1" />WhatsApp
                </Button>
              )}
            </div>
            <p className="text-[9px] text-emerald-700">
              ✓ Link valid {linkInfo.expires_in_days || 30} days · Once client submits, you'll see their data in Step 3
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
