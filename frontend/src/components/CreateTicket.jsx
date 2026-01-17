import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { MessageSquarePlus, Users, User } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreateTicket = ({ caseId = null, onTicketCreated, assignedCaseManagerId = null, clientId = null }) => {
  const [open, setOpen] = useState(false);
  const [ticket, setTicket] = useState({
    case_id: caseId,
    subject: '',
    category: 'general',
    priority: 'medium',
    description: '',
    target_user_ids: [],
    include_admin: false
  });
  const [loading, setLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [availableTargets, setAvailableTargets] = useState([]);
  const [admins, setAdmins] = useState([]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setCurrentUser(JSON.parse(userData));
    }
  }, []);

  useEffect(() => {
    if (open && currentUser) {
      loadAvailableTargets();
    }
  }, [open, currentUser]);

  const loadAvailableTargets = async () => {
    try {
      // Load admins for "include admin" option
      if (currentUser.role !== 'admin') {
        const usersRes = await axios.get(`${API}/users`, getAuthHeader()).catch(() => ({ data: [] }));
        const adminUsers = usersRes.data.filter(u => u.role === 'admin');
        setAdmins(adminUsers);
      }

      // Set available targets based on current user role
      let targets = [];
      
      if (currentUser.role === 'client') {
        // Client can send to their assigned Case Manager
        if (assignedCaseManagerId) {
          try {
            const casesRes = await axios.get(`${API}/cases/my-cases`, getAuthHeader());
            if (casesRes.data.length > 0) {
              const myCase = casesRes.data[0];
              targets.push({
                id: myCase.case_manager_id,
                name: myCase.case_manager_name,
                role: 'case_manager',
                label: `${myCase.case_manager_name} (Case Manager)`
              });
            }
          } catch (e) {
            console.error('Error loading case manager:', e);
          }
        }
      } else if (currentUser.role === 'case_manager') {
        // Case Manager can send to their clients
        try {
          const casesRes = await axios.get(`${API}/cases/my-cases`, getAuthHeader());
          const uniqueClients = [];
          const seenIds = new Set();
          casesRes.data.forEach(c => {
            if (!seenIds.has(c.client_id)) {
              seenIds.add(c.client_id);
              uniqueClients.push({
                id: c.client_id,
                name: c.client_name,
                role: 'client',
                label: `${c.client_name} (Client)`
              });
            }
          });
          targets = uniqueClients;
        } catch (e) {
          console.error('Error loading clients:', e);
        }
      } else if (currentUser.role === 'partner') {
        // Partner can only send to Admin (handled by include_admin)
        targets = [];
      } else if (currentUser.role === 'admin') {
        // Admin can send to anyone
        try {
          const usersRes = await axios.get(`${API}/users`, getAuthHeader());
          targets = usersRes.data
            .filter(u => u.id !== currentUser.id)
            .map(u => ({
              id: u.id,
              name: u.name,
              role: u.role,
              label: `${u.name} (${u.role.replace('_', ' ')})`
            }));
        } catch (e) {
          console.error('Error loading users:', e);
        }
      }

      setAvailableTargets(targets);
    } catch (error) {
      console.error('Error loading targets:', error);
    }
  };

  const handleSubmit = async () => {
    if (!ticket.subject || !ticket.description) {
      toast.error('Please fill all required fields');
      return;
    }

    // Build target user IDs
    let targetIds = [...ticket.target_user_ids];
    
    // Add admins if "include admin" is checked
    if (ticket.include_admin && admins.length > 0) {
      admins.forEach(admin => {
        if (!targetIds.includes(admin.id)) {
          targetIds.push(admin.id);
        }
      });
    }

    // If no targets selected and user is not admin, show error
    if (targetIds.length === 0 && currentUser?.role !== 'admin') {
      toast.error('Please select at least one recipient');
      return;
    }

    setLoading(true);
    try {
      const ticketData = {
        case_id: ticket.case_id,
        subject: ticket.subject,
        category: ticket.category,
        priority: ticket.priority,
        description: ticket.description,
        target_user_ids: targetIds
      };

      await axios.post(`${API}/tickets`, ticketData, getAuthHeader());
      toast.success('Ticket created successfully');
      setOpen(false);
      setTicket({
        case_id: caseId,
        subject: '',
        category: 'general',
        priority: 'medium',
        description: '',
        target_user_ids: [],
        include_admin: false
      });
      if (onTicketCreated) onTicketCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  const toggleTarget = (targetId) => {
    setTicket(prev => ({
      ...prev,
      target_user_ids: prev.target_user_ids.includes(targetId)
        ? prev.target_user_ids.filter(id => id !== targetId)
        : [...prev.target_user_ids, targetId]
    }));
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquarePlus className="h-5 w-5 text-[#2a777a]" />
            Create Support Ticket
          </DialogTitle>
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

          {/* Target Selection */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Send To *
            </Label>
            
            {availableTargets.length > 0 && (
              <div className="border rounded-lg p-3 space-y-2 max-h-40 overflow-y-auto bg-slate-50">
                {availableTargets.map(target => (
                  <div key={target.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`target-${target.id}`}
                      checked={ticket.target_user_ids.includes(target.id)}
                      onCheckedChange={() => toggleTarget(target.id)}
                    />
                    <label htmlFor={`target-${target.id}`} className="text-sm cursor-pointer flex items-center gap-2">
                      <User className="h-3 w-3 text-slate-500" />
                      {target.label}
                    </label>
                  </div>
                ))}
              </div>
            )}

            {currentUser?.role !== 'admin' && (
              <div className="flex items-center gap-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                <Checkbox
                  id="include-admin"
                  checked={ticket.include_admin}
                  onCheckedChange={(checked) => setTicket({ ...ticket, include_admin: checked })}
                />
                <label htmlFor="include-admin" className="text-sm cursor-pointer text-amber-800">
                  Also notify Admin (escalate issue)
                </label>
              </div>
            )}

            {availableTargets.length === 0 && currentUser?.role !== 'admin' && (
              <p className="text-sm text-slate-500 italic">
                {currentUser?.role === 'partner' 
                  ? 'Your ticket will be sent to Admin'
                  : 'No recipients available. Check "notify Admin" to escalate.'}
              </p>
            )}
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
                  <SelectItem value="support">Support</SelectItem>
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
              rows={4}
              data-testid="ticket-description-textarea"
            />
          </div>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-[#2a777a] hover:bg-[#236466]"
          data-testid="submit-ticket-button"
        >
          {loading ? 'Creating...' : 'Create Ticket'}
        </Button>
      </DialogContent>
    </Dialog>
  );
};

export default CreateTicket;
