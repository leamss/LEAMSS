import { useState } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Send, Eye, ArrowRight, MessageCircle, Clock, X, Copy, ExternalLink } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EXPIRY_OPTIONS = [
  { value: 1, label: '1 day' },
  { value: 7, label: '7 days' },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 0, label: 'Never expire' },
];

function buildWhatsAppMessage(pa, link, linkInfo) {
  const purpose = linkInfo?.purpose || 'pre_assessment_fee';
  const amount = linkInfo?.amount_label || '₹5,100';
  const purposeLine =
    purpose === 'proposal_fee_payment'
      ? `Service fee: *${amount}* (proposal already approved)`
      : purpose === 'view_portal'
        ? 'View your case status & documents'
        : `Pre-assessment fee: *${amount}*`;

  const lines = [
    `Hi ${pa.client_name || ''},`,
    ``,
    `This is ${pa.partner_name || 'LEAMSS'} regarding your *${pa.country || ''} ${pa.service_type || 'immigration'}* enquiry.`,
    ``,
    `Reference: *${pa.pa_number || (pa.id || '').slice(0, 8)}*`,
    purposeLine,
    ``,
    `Please use this secure link to ${purpose === 'view_portal' ? 'access your portal' : 'view your case + complete payment'}:`,
    link,
    ``,
    `Reply here for any questions. — Team LEAMSS`,
  ];
  return encodeURIComponent(lines.join('\n'));
}

export default function PaActionBar({ pa, nextAction, handlePreviewAsClient }) {
  const [showDialog, setShowDialog] = useState(false);
  const [expiryDays, setExpiryDays] = useState(30);
  const [generated, setGenerated] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [intent, setIntent] = useState(null); // 'copy' | 'whatsapp'

  const callGenerate = async () => {
    setGenerating(true);
    try {
      const r = await axios.post(
        `${API}/pre-assess-portal/generate-public-link`,
        { pa_id: pa.id, expires_in_days: expiryDays },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      const link = r.data.public_url?.startsWith('http')
        ? r.data.public_url
        : `${window.location.origin}${r.data.public_url}`;
      setGenerated({ ...r.data, full_url: link });
      return { ...r.data, full_url: link };
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to generate link');
      return null;
    } finally {
      setGenerating(false);
    }
  };

  const copyLink = async () => {
    const info = await callGenerate();
    if (!info) return;
    await navigator.clipboard.writeText(info.full_url);
    toast.success(`${info.amount_label} link copied · ${info.expires_in_days === 0 ? 'never expires' : `expires in ${info.expires_in_days} day(s)`}`);
  };

  const sendOnWhatsApp = async () => {
    const num = (pa.client_mobile || '').replace(/[^\d+]/g, '');
    if (!num || num.length < 8) {
      toast.error('Client mobile not on file. Edit details (✏️) to add it.');
      return;
    }
    const popup = window.open('about:blank', '_blank');
    const info = await callGenerate();
    if (!info) { if (popup) popup.close(); return; }
    const cleanNum = num.startsWith('+') ? num.slice(1) : num;
    const text = buildWhatsAppMessage(pa, info.full_url, info);
    const url = `https://wa.me/${cleanNum}?text=${text}`;
    if (popup) popup.location.href = url;
    else window.open(url, '_blank', 'noopener');
  };

  const openDialog = (i) => { setIntent(i); setGenerated(null); setShowDialog(true); };
  const submitDialog = async () => {
    if (intent === 'copy') await copyLink();
    else if (intent === 'whatsapp') await sendOnWhatsApp();
    setShowDialog(false);
  };

  return (
    <>
      <div className="flex justify-end gap-2 flex-wrap">
        <Button variant="outline" size="sm" onClick={() => openDialog('copy')} data-testid={`copy-link-${pa.id}`} title="Generate a smart secure link with custom expiry">
          <Send className="h-4 w-4 mr-1" /> Copy Public Link
        </Button>
        <Button variant="outline" size="sm" onClick={() => openDialog('whatsapp')} data-testid={`whatsapp-share-${pa.id}`} title="Send the right link to client on WhatsApp" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
          <MessageCircle className="h-4 w-4 mr-1" /> WhatsApp
        </Button>
        <Button variant="outline" size="sm" onClick={() => handlePreviewAsClient(pa.id)} data-testid={`preview-client-${pa.id}`} title="Preview client portal" className="border-[#f7620b]/40 text-[#f7620b] hover:bg-[#f7620b]/5">
          <Eye className="h-4 w-4 mr-1" /> Preview as Client
        </Button>
        {nextAction && (
          <Button onClick={nextAction.action} className={`${nextAction.color} text-white`} data-testid={`action-${pa.stage}`}>
            <ArrowRight className="h-4 w-4 mr-2" /> {nextAction.label}
          </Button>
        )}
      </div>

      {showDialog && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowDialog(false)} data-testid={`share-dialog-${pa.id}`}>
          <div className="bg-white rounded-xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b bg-gradient-to-r from-emerald-50 to-teal-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {intent === 'whatsapp' ? <MessageCircle className="h-5 w-5 text-emerald-600" /> : <Send className="h-5 w-5 text-[#2a777a]" />}
                <p className="font-bold text-slate-800">
                  {intent === 'whatsapp' ? 'Send via WhatsApp' : 'Generate Secure Link'}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowDialog(false)}><X className="h-4 w-4" /></Button>
            </div>
            <div className="p-5 space-y-4">
              {!generated && (
                <>
                  <p className="text-xs text-slate-500">
                    System auto-detects what the client needs to do (pay PA fee, pay proposal, or view portal) based on the current stage.
                  </p>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5 mb-2"><Clock className="h-3.5 w-3.5" /> Link Expires In</label>
                    <div className="grid grid-cols-3 gap-2">
                      {EXPIRY_OPTIONS.map(o => (
                        <button key={o.value} type="button" onClick={() => setExpiryDays(o.value)}
                          className={`text-xs py-2 rounded-md border ${expiryDays === o.value ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'}`}
                          data-testid={`expiry-${o.value}`}>
                          {o.label}
                        </button>
                      ))}
                    </div>
                    {expiryDays === 0 && (
                      <p className="text-[10px] text-amber-700 mt-2 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        ⚠ Never-expiring links remain accessible forever. Use only for trusted recipients.
                      </p>
                    )}
                  </div>
                </>
              )}

              {generated && (
                <div className="space-y-3" data-testid="share-link-preview">
                  <div className="bg-emerald-50 border border-emerald-200 rounded p-3 text-xs">
                    <p className="font-semibold text-emerald-800 mb-1">
                      ✓ Smart link ready · {generated.amount_label} · {generated.expires_in_days === 0 ? 'never expires' : `expires in ${generated.expires_in_days}d`}
                    </p>
                    <p className="text-slate-600 capitalize">{generated.purpose.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="flex items-center gap-1 bg-slate-50 border rounded p-2">
                    <Input readOnly value={generated.full_url} className="text-[10px] border-0 bg-transparent" />
                    <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(generated.full_url); toast.success('Copied'); }}>
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => window.open(generated.full_url, '_blank')}>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t bg-slate-50 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowDialog(false)}>Close</Button>
              {!generated && (
                <Button onClick={submitDialog} disabled={generating} className={intent === 'whatsapp' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-[#2a777a] hover:bg-[#1d5658] text-white'} data-testid="dialog-submit">
                  {generating ? 'Generating…' : intent === 'whatsapp' ? 'Open WhatsApp →' : 'Copy Link'}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
