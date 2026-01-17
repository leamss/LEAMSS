import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Bell, FileText, MessageSquare, CheckCircle, AlertCircle, DollarSign, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const NotificationBell = ({ onNotificationClick }) => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications`, getAuthHeader());
      setNotifications(response.data);
      setUnreadCount(response.data.filter(n => !n.is_read).length);
    } catch (error) {
      console.error('Failed to load notifications', error);
    }
  };

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await axios.get(`${API}/notifications`, getAuthHeader());
        setNotifications(response.data);
        setUnreadCount(response.data.filter(n => !n.is_read).length);
      } catch (error) {
        console.error('Failed to load notifications', error);
      }
    };
    
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const markAsRead = async (notificationId) => {
    try {
      await axios.post(`${API}/notifications/${notificationId}/read`, {}, getAuthHeader());
      loadNotifications();
    } catch (error) {
      console.error('Failed to mark as read', error);
    }
  };

  const getTimeAgo = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'ticket_status_update':
      case 'ticket_message':
      case 'ticket_created':
        return <MessageSquare className="h-4 w-4 text-blue-500" />;
      case 'doc_uploaded':
      case 'doc_approved':
      case 'doc_rejected':
      case 'document_request':
      case 'doc_requested':
        return <FileText className="h-4 w-4 text-green-500" />;
      case 'sale_approved':
      case 'sale_rejected':
        return <DollarSign className="h-4 w-4 text-amber-500" />;
      case 'step_completed':
        return <CheckCircle className="h-4 w-4 text-[#2a777a]" />;
      case 'case_assigned':
        return <User className="h-4 w-4 text-purple-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-slate-500" />;
    }
  };

  const getNotificationBadgeColor = (type) => {
    if (type?.includes('ticket')) return 'bg-blue-100 text-blue-700';
    if (type?.includes('doc')) return 'bg-green-100 text-green-700';
    if (type?.includes('sale')) return 'bg-amber-100 text-amber-700';
    if (type?.includes('step') || type?.includes('case')) return 'bg-purple-100 text-purple-700';
    return 'bg-slate-100 text-slate-700';
  };

  const handleNotificationClick = async (notification) => {
    // Mark as read first
    if (!notification.is_read) {
      await markAsRead(notification.id);
    }
    
    // Close the dropdown
    setIsOpen(false);
    
    // Navigate based on notification type and related_id
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const type = notification.type || '';
    const relatedId = notification.related_id;
    
    // If a custom handler is provided, use it
    if (onNotificationClick) {
      onNotificationClick(notification);
      return;
    }
    
    // Default navigation based on notification type
    if (type.includes('ticket')) {
      // Navigate to tickets - for admin/case manager, go to ticket detail
      if (user.role === 'admin') {
        // Store the ticket ID to open after navigation
        sessionStorage.setItem('openTicketId', relatedId);
        navigate('/admin');
        window.location.reload(); // Force reload to pick up the ticket
      } else if (user.role === 'case_manager') {
        navigate('/case-manager');
      } else {
        navigate('/client');
      }
    } else if (type.includes('doc') || type.includes('step') || type.includes('case')) {
      // Navigate to case/documents
      if (user.role === 'admin') {
        sessionStorage.setItem('openCaseId', relatedId);
        navigate('/admin');
      } else if (user.role === 'case_manager') {
        sessionStorage.setItem('openCaseId', relatedId);
        navigate('/case-manager');
      } else if (user.role === 'client') {
        navigate('/client');
      }
    } else if (type.includes('sale')) {
      // Navigate to sales
      if (user.role === 'admin') {
        navigate('/admin');
      } else if (user.role === 'partner') {
        navigate('/partner');
      }
    }
  };

  const markAllAsRead = async () => {
    try {
      await Promise.all(
        notifications.filter(n => !n.is_read).map(n => 
          axios.post(`${API}/notifications/${n.id}/read`, {}, getAuthHeader())
        )
      );
      loadNotifications();
    } catch (error) {
      console.error('Failed to mark all as read', error);
    }
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative"
          data-testid="notification-bell"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center animate-pulse">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-96">
        <div className="px-4 py-3 border-b flex justify-between items-center bg-slate-50">
          <h3 className="font-semibold text-slate-800">Notifications</h3>
          {unreadCount > 0 && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-xs text-[#2a777a] hover:text-[#236466]"
              onClick={markAllAsRead}
            >
              Mark all read
            </Button>
          )}
        </div>
        <ScrollArea className="max-h-[400px]">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              <Bell className="h-12 w-12 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className={`p-4 cursor-pointer border-b border-slate-100 focus:bg-slate-50 ${
                  notification.is_read ? 'opacity-70 bg-white' : 'bg-blue-50/50'
                }`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="w-full flex gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <h4 className="font-medium text-sm text-slate-800 truncate">{notification.title}</h4>
                      {!notification.is_read && (
                        <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1"></span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2 mb-2">{notification.message}</p>
                    <div className="flex items-center justify-between">
                      <Badge className={`text-xs ${getNotificationBadgeColor(notification.type)}`}>
                        {notification.type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Notification'}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        {getTimeAgo(notification.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </ScrollArea>
        {notifications.length > 0 && (
          <div className="p-2 border-t bg-slate-50 text-center">
            <p className="text-xs text-slate-500">Click on a notification to view details</p>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationBell;
