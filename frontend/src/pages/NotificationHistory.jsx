import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  ArrowLeft, Bell, FileText, MessageSquare, CheckCircle, AlertCircle, 
  DollarSign, User, Search, Filter, Trash2, CheckCheck
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const NotificationHistory = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [filteredNotifications, setFilteredNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ type: 'all', status: 'all', search: '' });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    loadNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifications, filter]);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/notifications`, getAuthHeader());
      setNotifications(response.data);
    } catch (error) {
      toast.error('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...notifications];
    
    if (filter.type !== 'all') {
      filtered = filtered.filter(n => n.type?.includes(filter.type));
    }
    
    if (filter.status === 'unread') {
      filtered = filtered.filter(n => !n.is_read);
    } else if (filter.status === 'read') {
      filtered = filtered.filter(n => n.is_read);
    }
    
    if (filter.search) {
      const search = filter.search.toLowerCase();
      filtered = filtered.filter(n => 
        n.title?.toLowerCase().includes(search) || 
        n.message?.toLowerCase().includes(search)
      );
    }
    
    setFilteredNotifications(filtered);
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.post(`${API}/notifications/${notificationId}/read`, {}, getAuthHeader());
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? {...n, is_read: true} : n
      ));
      toast.success('Marked as read');
    } catch (error) {
      toast.error('Failed to mark as read');
    }
  };

  const markAllAsRead = async () => {
    try {
      const unread = notifications.filter(n => !n.is_read);
      await Promise.all(unread.map(n => 
        axios.post(`${API}/notifications/${n.id}/read`, {}, getAuthHeader())
      ));
      setNotifications(prev => prev.map(n => ({...n, is_read: true})));
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark all as read');
    }
  };

  const deleteNotification = async (notificationId) => {
    try {
      await axios.delete(`${API}/notifications/${notificationId}`, getAuthHeader());
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      toast.success('Notification deleted');
    } catch (error) {
      toast.error('Failed to delete notification');
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'ticket_status_update':
      case 'ticket_message':
      case 'ticket_created':
        return <MessageSquare className="h-5 w-5 text-blue-500" />;
      case 'doc_uploaded':
      case 'doc_approved':
      case 'doc_rejected':
      case 'document_request':
      case 'doc_requested':
        return <FileText className="h-5 w-5 text-green-500" />;
      case 'sale_approved':
      case 'sale_rejected':
        return <DollarSign className="h-5 w-5 text-amber-500" />;
      case 'step_completed':
        return <CheckCircle className="h-5 w-5 text-[#2a777a]" />;
      case 'case_assigned':
        return <User className="h-5 w-5 text-leamss-orange-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-slate-500" />;
    }
  };

  const getNotificationBadgeColor = (type) => {
    if (type?.includes('ticket')) return 'bg-blue-100 text-blue-700';
    if (type?.includes('doc')) return 'bg-green-100 text-green-700';
    if (type?.includes('sale')) return 'bg-amber-100 text-amber-700';
    if (type?.includes('step') || type?.includes('case')) return 'bg-leamss-orange-100 text-leamss-orange-700';
    return 'bg-slate-100 text-slate-700';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const goBack = () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.role === 'admin') navigate('/admin');
    else if (user.role === 'case_manager') navigate('/case-manager');
    else if (user.role === 'partner') navigate('/partner');
    else navigate('/client');
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={goBack} data-testid="back-button">
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                  <Bell className="h-6 w-6 text-[#2a777a]" />
                  Notification History
                </h1>
                <p className="text-sm text-slate-500">
                  {notifications.length} total • {unreadCount} unread
                </p>
              </div>
            </div>
            {unreadCount > 0 && (
              <Button 
                onClick={markAllAsRead} 
                variant="outline"
                className="text-[#2a777a] border-[#2a777a] hover:bg-[#2a777a]/10"
                data-testid="mark-all-read-btn"
              >
                <CheckCheck className="h-4 w-4 mr-2" />
                Mark All Read
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-6xl mx-auto px-4 py-4">
        <Card className="p-4 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-700">Filters</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search notifications..."
                value={filter.search}
                onChange={(e) => setFilter({ ...filter, search: e.target.value })}
                className="pl-10"
                data-testid="notification-search"
              />
            </div>
            <Select value={filter.type} onValueChange={(v) => setFilter({ ...filter, type: v })}>
              <SelectTrigger data-testid="type-filter">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="ticket">Tickets</SelectItem>
                <SelectItem value="doc">Documents</SelectItem>
                <SelectItem value="sale">Sales</SelectItem>
                <SelectItem value="case">Cases</SelectItem>
                <SelectItem value="step">Workflow</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filter.status} onValueChange={(v) => setFilter({ ...filter, status: v })}>
              <SelectTrigger data-testid="status-filter">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="unread">Unread</SelectItem>
                <SelectItem value="read">Read</SelectItem>
              </SelectContent>
            </Select>
            <Button 
              variant="outline" 
              onClick={() => setFilter({ type: 'all', status: 'all', search: '' })}
            >
              Clear Filters
            </Button>
          </div>
        </Card>

        {/* Notification List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin h-8 w-8 border-4 border-[#2a777a] border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-4 text-slate-500">Loading notifications...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <Card className="p-12 text-center">
            <Bell className="h-16 w-16 mx-auto mb-4 text-slate-300" />
            <h3 className="text-lg font-medium text-slate-700 mb-2">No notifications found</h3>
            <p className="text-slate-500">
              {filter.type !== 'all' || filter.status !== 'all' || filter.search 
                ? 'Try adjusting your filters'
                : 'You have no notifications yet'}
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredNotifications.map((notification) => (
              <Card 
                key={notification.id} 
                className={`p-4 hover:shadow-md transition-shadow cursor-pointer ${
                  !notification.is_read ? 'border-l-4 border-l-[#2a777a] bg-blue-50/30' : ''
                }`}
                data-testid={`notification-item-${notification.id}`}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 p-2 bg-slate-100 rounded-lg">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div>
                        <h4 className={`font-medium text-slate-800 ${!notification.is_read ? 'font-semibold' : ''}`}>
                          {notification.title}
                          {!notification.is_read && (
                            <span className="ml-2 w-2 h-2 inline-block rounded-full bg-[#2a777a]"></span>
                          )}
                        </h4>
                        <p className="text-sm text-slate-600 mt-1">{notification.message}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {!notification.is_read && (
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={(e) => { e.stopPropagation(); markAsRead(notification.id); }}
                            title="Mark as read"
                            data-testid={`mark-read-${notification.id}`}
                          >
                            <CheckCircle className="h-4 w-4 text-[#2a777a]" />
                          </Button>
                        )}
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={(e) => { e.stopPropagation(); deleteNotification(notification.id); }}
                          title="Delete"
                          className="text-red-500 hover:text-red-600 hover:bg-red-50"
                          data-testid={`delete-${notification.id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={`text-xs ${getNotificationBadgeColor(notification.type)}`}>
                        {notification.type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Notification'}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        {formatDate(notification.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationHistory;
