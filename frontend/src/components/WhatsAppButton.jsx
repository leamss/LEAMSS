import { MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

const WhatsAppButton = ({ phoneNumber, message, clientName, variant = 'floating' }) => {
  const defaultPhone = phoneNumber || '919876543210';
  const defaultMsg = message || `Hi, I am ${clientName || 'a client'} from LEAMSS Portal. I need assistance with my immigration case.`;
  const waUrl = `https://wa.me/${defaultPhone}?text=${encodeURIComponent(defaultMsg)}`;

  if (variant === 'floating') {
    return (
      <a
        href={waUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-20 right-5 z-50 bg-[#25D366] hover:bg-[#1DA851] text-white rounded-full p-3.5 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110 group"
        data-testid="whatsapp-float-btn"
        title="Chat on WhatsApp"
      >
        <MessageCircle className="h-6 w-6" />
        <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-gray-900 text-white text-xs px-3 py-1.5 rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          Chat on WhatsApp
        </span>
      </a>
    );
  }

  return (
    <Button
      asChild
      variant="outline"
      className="bg-[#25D366] hover:bg-[#1DA851] text-white border-[#25D366] hover:border-[#1DA851]"
      data-testid="whatsapp-btn"
    >
      <a href={waUrl} target="_blank" rel="noopener noreferrer">
        <MessageCircle className="h-4 w-4 mr-2" />WhatsApp
      </a>
    </Button>
  );
};

export default WhatsAppButton;
