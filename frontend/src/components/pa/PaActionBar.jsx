import { Button } from '@/components/ui/button';
import { Send, Eye, ArrowRight } from 'lucide-react';

/**
 * PaActionBar — Copy Link + Preview as Client + dynamic next-action button.
 */
export default function PaActionBar({ pa, nextAction, handleCopyPublicLink, handlePreviewAsClient }) {
  return (
    <div className="flex justify-end gap-2 flex-wrap">
      <Button variant="outline" size="sm" onClick={() => handleCopyPublicLink(pa.id)} data-testid={`copy-link-${pa.id}`} title="Copy public payment link — share via WhatsApp/Email">
        <Send className="h-4 w-4 mr-1" /> Copy Public Link
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
