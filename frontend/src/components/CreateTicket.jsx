import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { MessageSquarePlus } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreateTicket = ({ caseId = null, onTicketCreated }) => {
  const [open, setOpen] = useState(false);
  const [ticket, setTicket] = useState({
    case_id: caseId,
    subject: '',
    category: 'general',
    priority: 'medium',
    description: ''
  });
  const [loading, setLoading] = useState(false);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const handleSubmit = async () => {
    if (!ticket.subject || !ticket.description) {
      toast.error('Please fill all required fields');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/tickets`, ticket, getAuthHeader());
      toast.success('Ticket created successfully');
      setOpen(false);
      setTicket({
        case_id: caseId,
        subject: '',
        category: 'general',
        priority: 'medium',
        description: ''
      });
      if (onTicketCreated) onTicketCreated();
    } catch (error) {
      toast.error('Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          data-testid="create-ticket-button"
        >
          <MessageSquarePlus className="h-4 w-4" />
          Raise Ticket
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Support Ticket</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <Label>Subject *</Label>
            <Input
              value={ticket.subject}
              onChange={(e) => setTicket({ ...ticket, subject: e.target.value })}
              placeholder="Brief description of the issue"
              data-testid="ticket-subject-input"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Category</Label>
              <Select value={ticket.category} onValueChange={(value) => setTicket({ ...ticket, category: value })}>
                <SelectTrigger data-testid="ticket-category-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="document">Document</SelectItem>
                  <SelectItem value="payment">Payment</SelectItem>
                  <SelectItem value="technical">Technical</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Priority</Label>
              <Select value={ticket.priority} onValueChange={(value) => setTicket({ ...ticket, priority: value })}>
                <SelectTrigger data-testid="ticket-priority-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Description *</Label>
            <Textarea
              value={ticket.description}
              onChange={(e) => setTicket({ ...ticket, description: e.target.value })}
              placeholder="Detailed description of your issue or concern"
              rows={5}
              data-testid="ticket-description-textarea"
            />
          </div>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full"
          data-testid="submit-ticket-button"
        >
          {loading ? 'Creating...' : 'Create Ticket'}
        </Button>
      </DialogContent>
    </Dialog>
  );
};

export default CreateTicket;
