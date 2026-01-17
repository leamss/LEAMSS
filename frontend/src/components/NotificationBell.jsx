import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Bell, FileText, MessageSquare, CheckCircle, AlertCircle, DollarSign, User, Wifi, WifiOff, BellRing, History, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import usePushNotifications from '@/hooks/usePushNotifications';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const NotificationBell = ({ onNotificationClick }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifications, setUnreadNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const initialLoadRef = useRef(false);
  
  // Push notifications hook
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, subscribe: subscribePush, permission: pushPermission } = usePushNotifications();

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  // Fetch notifications from API
  const fetchNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications`, getAuthHeader());
      const allNotifications = response.data;
      setNotifications(allNotifications);
      const unread = allNotifications.filter(n => !n.is_read);
      setUnreadNotifications(unread);
      setUnreadCount(unread.length);
      return allNotifications;
    } catch (error) {
      console.error('Failed to load notifications', error);
      return null;
    }
  };

  const handleNewNotification = useCallback((data) => {
    if (data.type === 'notification') {
      const newNotification = {
        id: data.data.id,
        title: data.data.title,
        message: data.data.message,
        type: data.data.notification_type,
        related_id: data.data.related_id,
        is_read: false,
        created_at: data.data.created_at
      };
      
      setNotifications(prev => [newNotification, ...prev]);
      setUnreadNotifications(prev => [newNotification, ...prev]);
      setUnreadCount(prev => prev + 1);
      
      // Show toast notification
      toast.info(data.data.title, {
        description: data.data.message,
        duration: 5000
      });
    }
  }, []);

  useEffect(() => {
    // Initial load of notifications (using an IIFE to avoid the linting warning)
    const loadInitial = async () => {
      if (!initialLoadRef.current) {
        initialLoadRef.current = true;
        try {
          const response = await axios.get(`${API}/notifications`, getAuthHeader());
          const allNotifications = response.data;
          setNotifications(allNotifications);
          const unread = allNotifications.filter(n => !n.is_read);
          setUnreadNotifications(unread);
          setUnreadCount(unread.length);
        } catch (error) {
          console.error('Failed to load notifications', error);
        }
      }
    };
    loadInitial();

    // Poll every 60 seconds as fallback
    const interval = setInterval(() => {
      fetchNotifications();
    }, 60000);

    // SSE Connection function (primary - works through HTTP ingress)
    const connectSSE = () => {
      const token = localStorage.getItem('token');
      if (!token) return;

      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      try {
        const sseUrl = `${API}/notifications/stream?token=${encodeURIComponent(token)}`;
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('SSE connected');
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'connected') {
              console.log('SSE connection confirmed for user:', data.user_id);
              setIsConnected(true);
            } else if (data.type === 'ping') {
              // Keep-alive ping, do nothing
            } else if (data.type === 'notification') {
              handleNewNotification(data);
            }
          } catch (e) {
            console.error('Failed to parse SSE message', e);
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE connection error', error);
          setIsConnected(false);
          eventSource.close();
          
          // Reconnect after 5 seconds
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          reconnectTimeoutRef.current = setTimeout(connectSSE, 5000);
        };
      } catch (error) {
        console.error('Failed to create SSE connection', error);
        setIsConnected(false);
      }
    };

    // Connect to SSE for real-time notifications
    connectSSE();
    
    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleNewNotification]);

  const markAsRead = async (notificationId) => {
    try {
      await axios.post(`${API}/notifications/${notificationId}/read`, {}, getAuthHeader());
      // Remove from unread list immediately for auto-read behavior
      setUnreadNotifications(prev => prev.filter(n => n.id !== notificationId));
      setNotifications(prev => prev.map(n => n.id === notificationId ? {...n, is_read: true} : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
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
        unreadNotifications.map(n => 
          axios.post(`${API}/notifications/${n.id}/read`, {}, getAuthHeader())
        )
      );
      // Clear unread list and update all to read
      setUnreadNotifications([]);
      setNotifications(prev => prev.map(n => ({...n, is_read: true})));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      console.error('Failed to mark all as read', error);
    }
  };

  // Navigate to notification history
  const goToHistory = () => {
    setIsOpen(false);
    navigate('/notifications');
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
          {/* Connection status indicator */}
          <span className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-yellow-500'}`} title={isConnected ? 'Real-time connected' : 'Polling mode'}></span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-96">
        <div className="px-4 py-3 border-b flex justify-between items-center bg-slate-50">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-800">Notifications</h3>
            {isConnected ? (
              <Wifi className="h-3 w-3 text-green-500" title="Real-time connected" />
            ) : (
              <WifiOff className="h-3 w-3 text-yellow-500" title="Polling mode" />
            )}
          </div>
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
        <ScrollArea className="max-h-[350px]">
          {unreadNotifications.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              <CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-30 text-green-500" />
              <p className="text-sm font-medium">All caught up!</p>
              <p className="text-xs mt-1">No new notifications</p>
            </div>
          ) : (
            unreadNotifications.slice(0, 10).map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="p-4 cursor-pointer border-b border-slate-100 focus:bg-slate-50 bg-blue-50/30"
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="w-full flex gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <h4 className="font-medium text-sm text-slate-800 truncate">{notification.title}</h4>
                      <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1"></span>
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
        <DropdownMenuSeparator />
        <div className="p-3 bg-slate-50 space-y-2">
          {pushSupported && !pushSubscribed && pushPermission !== 'denied' && (
            <Button
              variant="outline"
              size="sm"
              className="w-full text-[#2a777a] border-[#2a777a] hover:bg-[#2a777a]/10"
              onClick={async (e) => {
                e.stopPropagation();
                const success = await subscribePush();
                if (success) {
                  toast.success('Push notifications enabled! You will receive alerts even when the portal is closed.');
                } else if (pushPermission === 'denied') {
                  toast.error('Please enable notifications in browser settings');
                }
              }}
              data-testid="enable-push-notifications"
            >
              <BellRing className="h-4 w-4 mr-2" />
              Enable Desktop Alerts
            </Button>
          )}
          {pushSubscribed && (
            <div className="flex items-center justify-center gap-2 text-xs text-green-600">
              <BellRing className="h-3 w-3" />
              Desktop alerts enabled
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-slate-600 hover:text-slate-800"
            onClick={goToHistory}
            data-testid="view-notification-history"
          >
            <History className="h-4 w-4 mr-2" />
            View All Notifications
            <ExternalLink className="h-3 w-3 ml-auto" />
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationBell;
