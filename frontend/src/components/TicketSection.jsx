import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import CreateTicket from './CreateTicket';
import { 
  MessageSquare, Clock, CheckCircle, XCircle, AlertCircle, 
  Send, Paperclip, Download, User, Calendar, ChevronRight,
  Inbox, CheckCheck, Archive, FileText, RefreshCw, Upload, ArrowLeft
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TicketSection = ({ caseId = null, assignedCaseManagerId = null, clientId = null }) => {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketDialogOpen, setTicketDialogOpen] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [activeTab, setActiveTab] = useState('open');
  const [loading, setLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  const getAuthHeader = useCallback(() => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }), []);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setCurrentUser(JSON.parse(userData));
    }
  }, []);

  const loadTickets = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/tickets/my-tickets`, getAuthHeader());
      setTickets(response.data);
    } catch (error) {
      console.error('Failed to load tickets:', error);
    }
  }, [getAuthHeader]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  const loadTicketDetails = async (ticketId) => {
    try {
      const response = await axios.get(`${API}/tickets/${ticketId}`, getAuthHeader());
      setSelectedTicket(response.data);
      setTicketDialogOpen(true);
    } catch (error) {
      toast.error('Failed to load ticket details');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedTicket) return;

    try {
      await axios.post(`${API}/tickets/${selectedTicket.id}/message`, 
        { message: newMessage }, 
        getAuthHeader()
      );
      setNewMessage('');
      loadTicketDetails(selectedTicket.id);
      toast.success('Message sent');
    } catch (error) {
      toast.error('Failed to send message');
    }
  };

  const updateTicketStatus = async (status, resolutionNote = '') => {
    if (!selectedTicket) return;

    if ((status === 'resolved' || status === 'closed') && !resolutionNote) {
      toast.error('Resolution note is required');
      return;
    }

    try {
      await axios.put(`${API}/tickets/${selectedTicket.id}/status`, 
        { status, resolution_note: resolutionNote || undefined }, 
        getAuthHeader()
      );
      toast.success(`Ticket ${status}`);
      loadTicketDetails(selectedTicket.id);
      loadTickets();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const downloadAttachment = async (fileId, filename) => {
    try {
      const response = await axios.get(
        `${API}/tickets/${selectedTicket.id}/attachment/${fileId}`,
        { ...getAuthHeader(), responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      toast.error('Failed to download attachment');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      open: 'bg-blue-100 text-blue-700',
      in_progress: 'bg-amber-100 text-amber-700',
      resolved: 'bg-green-100 text-green-700',
      closed: 'bg-slate-100 text-slate-700'
    };
    return <Badge className={styles[status] || styles.open}>{status?.replace('_', ' ')}</Badge>;
  };

  const getPriorityBadge = (priority) => {
    const styles = {
      low: 'bg-slate-100 text-slate-600',
      medium: 'bg-blue-100 text-blue-600',
      high: 'bg-orange-100 text-orange-600',
      urgent: 'bg-red-100 text-red-600'
    };
    return <Badge className={styles[priority] || styles.medium}>{priority}</Badge>;
  };

  const filterTickets = (status) => {
    if (status === 'open') return tickets.filter(t => t.status === 'open');
    if (status === 'in_progress') return tickets.filter(t => t.status === 'in_progress');
    if (status === 'resolved') return tickets.filter(t => t.status === 'resolved');
    if (status === 'closed') return tickets.filter(t => t.status === 'closed');
    return tickets;
  };

  const TicketCard = ({ ticket }) => (
    <div 
      className="p-4 bg-white rounded-xl border border-slate-200 hover:border-[#2a777a] hover:shadow-md transition-all cursor-pointer"
      onClick={() => loadTicketDetails(ticket.id)}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-semibold text-slate-800 line-clamp-1">{ticket.subject}</h4>
        <ChevronRight className="h-4 w-4 text-slate-400" />
      </div>
      <p className="text-sm text-slate-500 line-clamp-2 mb-3">{ticket.description}</p>
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {getStatusBadge(ticket.status)}
          {getPriorityBadge(ticket.priority)}
        </div>
        <span className="text-xs text-slate-400">
          {new Date(ticket.created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
        <User className="h-3 w-3" />
        <span>{ticket.created_by_name}</span>
        {ticket.messages?.length > 0 && (
          <>
            <span>•</span>
            <MessageSquare className="h-3 w-3" />
            <span>{ticket.messages.length} messages</span>
          </>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Support Tickets</h2>
          <p className="text-slate-500">Manage your support requests</p>
        </div>
        <CreateTicket 
          caseId={caseId} 
          assignedCaseManagerId={assignedCaseManagerId}
          clientId={clientId}
          onTicketCreated={loadTickets} 
        />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <div className="flex items-center gap-3">
            <Inbox className="h-8 w-8 opacity-80" />
            <div>
              <p className="text-2xl font-bold">{filterTickets('open').length}</p>
              <p className="text-xs opacity-80">Open</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <div className="flex items-center gap-3">
            <Clock className="h-8 w-8 opacity-80" />
            <div>
              <p className="text-2xl font-bold">{filterTickets('in_progress').length}</p>
              <p className="text-xs opacity-80">In Progress</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-green-500 to-green-600 text-white">
          <div className="flex items-center gap-3">
            <CheckCheck className="h-8 w-8 opacity-80" />
            <div>
              <p className="text-2xl font-bold">{filterTickets('resolved').length}</p>
              <p className="text-xs opacity-80">Resolved</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 bg-gradient-to-br from-slate-500 to-slate-600 text-white">
          <div className="flex items-center gap-3">
            <Archive className="h-8 w-8 opacity-80" />
            <div>
              <p className="text-2xl font-bold">{filterTickets('closed').length}</p>
              <p className="text-xs opacity-80">Closed</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Tickets Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-white shadow rounded-lg p-1">
          <TabsTrigger value="open" className="data-[state=active]:bg-blue-500 data-[state=active]:text-white">
            Open ({filterTickets('open').length})
          </TabsTrigger>
          <TabsTrigger value="in_progress" className="data-[state=active]:bg-amber-500 data-[state=active]:text-white">
            In Progress ({filterTickets('in_progress').length})
          </TabsTrigger>
          <TabsTrigger value="resolved" className="data-[state=active]:bg-green-500 data-[state=active]:text-white">
            Resolved ({filterTickets('resolved').length})
          </TabsTrigger>
          <TabsTrigger value="closed" className="data-[state=active]:bg-slate-500 data-[state=active]:text-white">
            Closed ({filterTickets('closed').length})
          </TabsTrigger>
        </TabsList>

        {['open', 'in_progress', 'resolved', 'closed'].map(status => (
          <TabsContent key={status} value={status} className="mt-4">
            {filterTickets(status).length === 0 ? (
              <Card className="p-12 text-center bg-slate-50">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                <p className="text-slate-500">No {status.replace('_', ' ')} tickets</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filterTickets(status).map(ticket => (
                  <TicketCard key={ticket.id} ticket={ticket} />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Ticket Detail Dialog */}
      <Dialog open={ticketDialogOpen} onOpenChange={setTicketDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
          {selectedTicket && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center justify-between">
                  <span className="line-clamp-1">{selectedTicket.subject}</span>
                  <div className="flex gap-2">
                    {getStatusBadge(selectedTicket.status)}
                    {getPriorityBadge(selectedTicket.priority)}
                  </div>
                </DialogTitle>
              </DialogHeader>

              <div className="flex-1 overflow-hidden flex flex-col">
                {/* Ticket Info */}
                <div className="p-4 bg-slate-50 rounded-lg mb-4">
                  <p className="text-sm text-slate-600 mb-2">{selectedTicket.description}</p>
                  <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {selectedTicket.created_by_name}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(selectedTicket.created_at).toLocaleString()}
                    </span>
                    <Badge variant="outline">{selectedTicket.category}</Badge>
                  </div>
                </div>

                {/* Messages */}
                <ScrollArea className="flex-1 pr-4 mb-4">
                  <div className="space-y-3">
                    {selectedTicket.messages?.map((msg, idx) => (
                      <div 
                        key={idx} 
                        className={`p-3 rounded-lg ${
                          msg.user_id === currentUser?.id 
                            ? 'bg-[#2a777a]/10 ml-8' 
                            : 'bg-slate-100 mr-8'
                        }`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium text-sm">{msg.user_name}</span>
                          <span className="text-xs text-slate-500">
                            {new Date(msg.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-slate-700">{msg.message}</p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>

                {/* Attachments */}
                {selectedTicket.attachments?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-medium mb-2">Attachments</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedTicket.attachments.map((att, idx) => (
                        <Button
                          key={idx}
                          size="sm"
                          variant="outline"
                          onClick={() => downloadAttachment(att.file_id, att.filename)}
                        >
                          <Download className="h-3 w-3 mr-1" />
                          {att.filename}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Resolution Note */}
                {selectedTicket.resolution_note && (
                  <div className="p-3 bg-green-50 rounded-lg border border-green-200 mb-4">
                    <p className="text-sm font-medium text-green-800 mb-1">Resolution</p>
                    <p className="text-sm text-green-700">{selectedTicket.resolution_note}</p>
                    <p className="text-xs text-green-600 mt-1">
                      By {selectedTicket.resolved_by_name} on {new Date(selectedTicket.resolved_at).toLocaleString()}
                    </p>
                  </div>
                )}

                {/* Reply Box - Only show for non-closed tickets */}
                {selectedTicket.status !== 'closed' && (
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      <Input
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder="Type your message..."
                        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        className="flex-1"
                      />
                      <Button onClick={sendMessage} className="bg-[#2a777a] hover:bg-[#236466]">
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* Status Actions */}
                    <div className="flex gap-2 flex-wrap">
                      {selectedTicket.status === 'open' && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => updateTicketStatus('in_progress')}
                        >
                          <Clock className="h-4 w-4 mr-1" />
                          Mark In Progress
                        </Button>
                      )}
                      {(selectedTicket.status === 'open' || selectedTicket.status === 'in_progress') && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          className="text-green-600 border-green-600"
                          onClick={() => {
                            const note = prompt('Enter resolution note:');
                            if (note) updateTicketStatus('resolved', note);
                          }}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Resolve
                        </Button>
                      )}
                      {selectedTicket.status === 'resolved' && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => updateTicketStatus('closed', selectedTicket.resolution_note || 'Closed')}
                        >
                          <Archive className="h-4 w-4 mr-1" />
                          Close Ticket
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TicketSection;
