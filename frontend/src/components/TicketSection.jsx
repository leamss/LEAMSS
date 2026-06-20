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

const TicketSection = ({ caseId = null, assignedCaseManagerId = null, clientId = null, initialTicketId = null, initialFilter = null }) => {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'detail'
  const [newMessage, setNewMessage] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  const [activeTab, setActiveTab] = useState(initialFilter?.status || 'open');
  const [priorityFilter, setPriorityFilter] = useState(initialFilter?.priority || 'all');
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

  const loadTicketDetails = useCallback(async (ticketId) => {
    try {
      const response = await axios.get(`${API}/tickets/${ticketId}`, getAuthHeader());
      setSelectedTicket(response.data);
      setViewMode('detail');
      setResolutionNote('');
    } catch (error) {
      toast.error('Failed to load ticket details');
    }
  }, [getAuthHeader]);

  // Handle initial ticket ID from notification navigation
  useEffect(() => {
    if (initialTicketId && tickets.length > 0) {
      const ticket = tickets.find(t => t.id === initialTicketId);
      if (ticket) {
        loadTicketDetails(initialTicketId);
      }
    }
  }, [initialTicketId, tickets, loadTicketDetails]);

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

  // React to initialFilter changes from QuickActions
  useEffect(() => {
    if (initialFilter) {
      if (initialFilter.status) setActiveTab(initialFilter.status);
      if (initialFilter.priority) setPriorityFilter(initialFilter.priority);
    }
  }, [initialFilter]);

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

  const updateTicketStatus = async (status) => {
    if (!selectedTicket) return;

    // Require resolution note for resolved/closed
    if ((status === 'resolved' || status === 'closed')) {
      if (!resolutionNote || resolutionNote.trim().length < 10) {
        toast.error('Please enter a resolution note (min 10 characters) in the field below before resolving/closing.');
        // Focus the resolution note input
        const input = document.querySelector('[data-testid="resolution-note-input"]');
        if (input) {
          input.focus();
          input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
      }
    }

    try {
      await axios.put(`${API}/tickets/${selectedTicket.id}/status`, 
        { status, closure_comment: resolutionNote || '', resolution_note: resolutionNote || '' }, 
        getAuthHeader()
      );
      toast.success(`Ticket ${status}`);
      loadTicketDetails(selectedTicket.id);
      loadTickets();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const uploadAttachment = async (file) => {
    if (!selectedTicket || !file) return;
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size must be less than 10MB');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await axios.post(`${API}/tickets/${selectedTicket.id}/attachment`, formData, {
        ...getAuthHeader(),
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('Attachment uploaded');
      loadTicketDetails(selectedTicket.id);
    } catch (error) {
      toast.error('Failed to upload attachment');
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
    let filtered = tickets;
    if (status === 'open') filtered = tickets.filter(t => t.status === 'open');
    else if (status === 'in_progress') filtered = tickets.filter(t => t.status === 'in_progress');
    else if (status === 'resolved') filtered = tickets.filter(t => t.status === 'resolved');
    else if (status === 'closed') filtered = tickets.filter(t => t.status === 'closed');
    
    // Apply priority filter
    if (priorityFilter && priorityFilter !== 'all') {
      filtered = filtered.filter(t => t.priority === priorityFilter);
    }
    return filtered;
  };

  // Render ticket card inline to avoid nested component issues
  const renderTicketCard = (ticket) => (
    <div 
      key={ticket.id}
      className="p-4 bg-white rounded-xl border border-slate-200 hover:border-[#2a777a] hover:shadow-md transition-all cursor-pointer"
      onClick={() => loadTicketDetails(ticket.id)}
      data-testid={`ticket-card-${ticket.id}`}
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
      {/* Detail View */}
      {viewMode === 'detail' && selectedTicket ? (
        <div className="space-y-6" data-testid="ticket-detail-view">
          <Button onClick={() => { setViewMode('list'); setSelectedTicket(null); }} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />Back to Tickets
          </Button>
          
          {/* Ticket Info Card */}
          <Card className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-xl font-semibold text-slate-800">{selectedTicket.subject}</h3>
                  {getPriorityBadge(selectedTicket.priority)}
                  {getStatusBadge(selectedTicket.status)}
                </div>
                <p className="text-sm text-slate-600">Category: {selectedTicket.category}</p>
                <p className="text-sm text-slate-600">Created by: {selectedTicket.created_by_name} ({selectedTicket.created_by_role})</p>
                <p className="text-sm text-slate-600">Created: {new Date(selectedTicket.created_at).toLocaleString()}</p>
                {selectedTicket.target_user_ids?.length > 0 && (
                  <p className="text-sm text-slate-600">Assigned to: {selectedTicket.target_user_ids.length} user(s)</p>
                )}
              </div>
              <div className="flex gap-2">
                {selectedTicket.status === 'open' && (
                  <Button onClick={() => updateTicketStatus('in_progress')} size="sm" className="bg-leamss-orange-500 hover:bg-leamss-orange-600">
                    <Clock className="mr-1 h-4 w-4" />Start
                  </Button>
                )}
                {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'closed' && (
                  <Button onClick={() => updateTicketStatus('resolved')} size="sm" className="bg-green-500 hover:bg-green-600">
                    <CheckCircle className="mr-1 h-4 w-4" />Resolve
                  </Button>
                )}
                {selectedTicket.status === 'resolved' && (
                  <Button onClick={() => updateTicketStatus('closed')} size="sm" variant="outline">
                    <Archive className="mr-1 h-4 w-4" />Close
                  </Button>
                )}
              </div>
            </div>
            
            <div className="p-4 bg-slate-50 rounded-lg mb-4">
              <p className="text-slate-800">{selectedTicket.description}</p>
            </div>

            {/* Resolution Note Input - show when not resolved/closed */}
            {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'closed' && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <Label className="text-amber-800 font-semibold flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4" />
                  Resolution Note (required before resolving or closing — min 10 chars)
                </Label>
                <Textarea 
                  value={resolutionNote} 
                  onChange={(e) => setResolutionNote(e.target.value)} 
                  placeholder="Describe how the issue was resolved..." 
                  rows={2} 
                  data-testid="resolution-note-input"
                  className={resolutionNote.trim().length > 0 && resolutionNote.trim().length < 10 ? 'border-red-300' : ''}
                />
                {resolutionNote.trim().length > 0 && resolutionNote.trim().length < 10 && (
                  <p className="text-xs text-red-500 mt-1">{10 - resolutionNote.trim().length} more characters needed</p>
                )}
              </div>
            )}

            {/* Display Resolution Note when resolved */}
            {(selectedTicket.resolution_note || selectedTicket.closure_comment) && (
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <p className="text-sm font-medium text-green-800">Closure Comment:</p>
                <p className="text-green-700">{selectedTicket.closure_comment || selectedTicket.resolution_note}</p>
                {selectedTicket.closed_by && (
                  <p className="text-xs text-green-600 mt-1">
                    Closed on {selectedTicket.closed_at ? new Date(selectedTicket.closed_at).toLocaleString() : 'N/A'}
                  </p>
                )}
                {selectedTicket.resolved_by_name && (
                  <p className="text-xs text-green-600 mt-1">
                    Resolved by {selectedTicket.resolved_by_name} on {new Date(selectedTicket.resolved_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </Card>

          {/* Attachments Card */}
          <Card className="p-6">
            <h4 className="font-semibold mb-4 text-slate-800 flex items-center gap-2">
              <FileText className="h-5 w-5" /> Attachments ({selectedTicket.attachments?.length || 0})
            </h4>
            <div className="space-y-2 mb-4">
              {selectedTicket.attachments?.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">No attachments</p>
              ) : (
                selectedTicket.attachments?.map((att, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 border rounded-lg hover:bg-slate-50">
                    <div>
                      <p className="font-medium text-slate-800">{att.filename}</p>
                      <p className="text-xs text-slate-500">
                        Uploaded by {att.uploaded_by_name} on {new Date(att.uploaded_at).toLocaleString()}
                        {att.file_size && ` • ${(att.file_size / 1024).toFixed(1)} KB`}
                      </p>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => downloadAttachment(att.file_id, att.filename)} data-testid={`download-attachment-${idx}`}>
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                ))
              )}
            </div>
            {selectedTicket.status !== 'closed' && (
              <div className="pt-3 border-t">
                <Label className="text-sm mb-2 block">Upload Attachment (max 10MB)</Label>
                <Input
                  type="file"
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      uploadAttachment(e.target.files[0]);
                      e.target.value = '';
                    }
                  }}
                  className="cursor-pointer"
                  data-testid="ticket-attachment-input"
                />
              </div>
            )}
          </Card>

          {/* Messages Card */}
          <Card className="p-6">
            <h4 className="font-semibold mb-4 text-slate-800">Messages ({selectedTicket.messages?.length || 0})</h4>
            <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
              {selectedTicket.messages?.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">No messages yet</p>
              ) : (
                selectedTicket.messages?.map((msg, idx) => (
                  <div key={idx} className={`p-3 rounded-lg ${msg.user_id === currentUser?.id ? 'bg-[#2a777a]/10 ml-8' : 'bg-slate-100 mr-8'}`}>
                    <div className="flex justify-between items-center mb-1">
                      <p className="text-sm font-medium text-slate-800">{msg.user_name} <span className="text-slate-500">({msg.user_role})</span></p>
                      <p className="text-xs text-slate-500">{new Date(msg.created_at).toLocaleString()}</p>
                    </div>
                    <p className="text-slate-700">{msg.message}</p>
                  </div>
                ))
              )}
            </div>
            {selectedTicket.status !== 'closed' && (
              <div className="flex gap-2">
                <Textarea 
                  value={newMessage} 
                  onChange={(e) => setNewMessage(e.target.value)} 
                  placeholder="Type your reply..." 
                  rows={2} 
                  className="flex-1" 
                  data-testid="ticket-reply-input"
                  onKeyPress={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                />
                <Button onClick={sendMessage} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="send-reply-btn">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            )}
          </Card>

          {/* Activity Log Card */}
          <Card className="p-6">
            <h4 className="font-semibold mb-4 text-slate-800 flex items-center gap-2">
              <RefreshCw className="h-5 w-5" /> Activity Log ({selectedTicket.activity_log?.length || 0})
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {selectedTicket.activity_log?.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">No activity logged</p>
              ) : (
                [...(selectedTicket.activity_log || [])].reverse().map((activity, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-2 border-l-2 border-slate-300 pl-4">
                    <div className="flex-1">
                      <p className="text-sm text-slate-800">{typeof activity.details === 'object' ? Object.entries(activity.details).map(([k,v]) => `${k}: ${v}`).join(', ') : activity.details}</p>
                      <p className="text-xs text-slate-500">
                        {activity.user_name} • {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      ) : (
        /* List View */
        <>
          {/* Header */}
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-slate-800">Support Tickets</h2>
              <p className="text-slate-500">Manage your support requests</p>
            </div>
            <div className="flex items-center gap-3">
              <select 
                value={priorityFilter} 
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="text-sm border rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#2a777a]"
                data-testid="ticket-priority-filter"
              >
                <option value="all">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <CreateTicket 
                caseId={caseId} 
                assignedCaseManagerId={assignedCaseManagerId}
                clientId={clientId}
                onTicketCreated={loadTickets} 
              />
            </div>
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
                    {filterTickets(status).map(ticket => renderTicketCard(ticket))}
                  </div>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </>
      )}
    </div>
  );
};

export default TicketSection;
