import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Send, Eye, ArrowRight, MessageCircle } from 'lucide-react';

/**
 * PaActionBar — Copy Public Link + Preview as Client + WhatsApp Share + dynamic next-action button.
 */

function buildWhatsAppMessage(pa) {
  const link = `${window.location.origin}/pre-assess/${pa.public_token || pa.id}`;
  const fee = pa.fee_payment_status === 'paid' && pa.proposal_fee
    ? `₹${(pa.proposal_fee || 0).toLocaleString('en-IN')}`
    : '₹5,100';
  const lines = [
    `Hi ${pa.client_name || ''},`,
    ``,
    `This is ${pa.partner_name || 'LEAMSS'} regarding your *${pa.country || ''} ${pa.service_type || 'immigration'}* enquiry.`,
    ``,
    `Reference: *${pa.pa_number || pa.id?.slice(0, 8)}*`,
    `Pre-assessment fee: *${fee}*`,
    ``,
    `Please use this secure link to view your case + complete payment:`,
    link,
    ``,
    `Reply here for any questions. — Team LEAMSS`,
  ];
  return encodeURIComponent(lines.join('\n'));
}

export default function PaActionBar({ pa, nextAction, handleCopyPublicLink, handlePreviewAsClient }) {
  const sendWhatsApp = () => {
    const num = (pa.client_mobile || '').replace(/[^\d+]/g, '');
    if (!num || num.length < 8) {
      toast.error('Client mobile not on file. Add it to share via WhatsApp.');
      return;
    }
    const cleanNum = num.startsWith('+') ? num.slice(1) : num;
    const text = buildWhatsAppMessage(pa);
    const url = `https://wa.me/${cleanNum}?text=${text}`;
    window.open(url, '_blank', 'noopener');
  };

  return (
    <div className="flex justify-end gap-2 flex-wrap">
      <Button variant="outline" size="sm" onClick={() => handleCopyPublicLink(pa.id)} data-testid={`copy-link-${pa.id}`} title="Copy public payment link — share via WhatsApp/Email">
        <Send className="h-4 w-4 mr-1" /> Copy Public Link
      </Button>
      <Button variant="outline" size="sm" onClick={sendWhatsApp} data-testid={`whatsapp-share-${pa.id}`} title="Open WhatsApp chat with client + pre-filled message + payment link" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
        <MessageCircle className="h-4 w-4 mr-1" /> WhatsApp
      </Button>
      <Button variant="outline" size="sm" onClick={() => handlePreviewAsClient(pa.id)} data-testid={`preview-client-${pa.id}`} title="Preview what your client sees (opens client MiniPortal in new tab)" className="border-[#f7620b]/40 text-[#f7620b] hover:bg-[#f7620b]/5">
        <Eye className="h-4 w-4 mr-1" /> Preview as Client
      </Button>
      {nextAction && (
        <Button onClick={nextAction.action} className={`${nextAction.color} text-white`} data-testid={`action-${pa.stage}`}>
          <ArrowRight className="h-4 w-4 mr-2" /> {nextAction.label}
        </Button>
      )}
    </div>
  );
}
