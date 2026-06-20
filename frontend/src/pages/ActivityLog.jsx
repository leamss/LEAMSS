import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import DashboardShell from '@/components/DashboardShell';
import {
  Activity, ArrowLeft, Search, Filter, Clock, User, FileText, Briefcase,
  CreditCard, MessageSquare, Settings, RefreshCw, Calendar, ChevronDown, ChevronRight,
  Download, Shield
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ACTION_ICONS = {
  login: Shield, created: FileText, approved: Briefcase, rejected: Briefcase,
  uploaded: Download, review_document_approved: FileText, review_document_rejected: FileText,
  update_step: Clock, assigned_manager: User, initiated_payment: CreditCard,
  replied: MessageSquare, set_status_resolved: MessageSquare, saved_ai_workflow: Settings,
  generated_workflow: Settings, updated: Settings, deleted: Settings, record_payment: CreditCard,
  create_sale: FileText, sale_approved: Briefcase, sale_rejected: Briefcase,
  upload_document: Download, set_expiry: Calendar, bulk_uploaded: Download,
};

const ACTION_COLORS = {
  login: 'bg-blue-100 text-blue-700',
  created: 'bg-green-100 text-green-700', approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700', uploaded: 'bg-leamss-orange-100 text-leamss-orange-700',
  updated: 'bg-amber-100 text-amber-700', deleted: 'bg-red-100 text-red-700',
  replied: 'bg-teal-100 text-teal-700', initiated_payment: 'bg-orange-100 text-orange-700',
};

const formatDateTime = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
  });
};

const getActionColor = (action) => {
  for (const [key, cls] of Object.entries(ACTION_COLORS)) {
    if (action?.includes(key)) return cls;
  }
  return 'bg-gray-100 text-gray-700';
};

const ActivityLogPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [liveFeed, setLiveFeed] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    entity_type: '', action: '', user_id: '', days: 30, limit: 50
  });
  const [activeView, setActiveView] = useState('feed');
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [userLogs, setUserLogs] = useState([]);
  const [selectedUserInfo, setSelectedUserInfo] = useState(null);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    if (userData.role !== 'admin') { navigate('/'); return; }
    setUser(userData);
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [logsRes, statsRes, feedRes] = await Promise.all([
        axios.get(`${API}/activity/logs?days=${filters.days}&limit=${filters.limit}${filters.entity_type ? `&entity_type=${filters.entity_type}` : ''}${filters.action ? `&action=${filters.action}` : ''}${filters.user_id ? `&user_id=${filters.user_id}` : ''}`, getAuthHeader()),
        axios.get(`${API}/activity/stats?days=${filters.days}`, getAuthHeader()),
        axios.get(`${API}/activity/live-feed?limit=15`, getAuthHeader()),
      ]);
      setLogs(logsRes.data.logs || logsRes.data || []);
      setTotal(logsRes.data.total || 0);
      setStats(statsRes.data);
      setLiveFeed(feedRes.data);
    } catch (err) {
      toast.error('Failed to load activity data');
    }
    setLoading(false);
  };

  const fetchUserActivity = async (userId) => {
    try {
      const res = await axios.get(`${API}/activity/user/${userId}?days=90&limit=100`, getAuthHeader());
      setUserLogs(res.data.logs || []);
      setSelectedUserInfo(res.data.user || {});
      setSelectedUserId(userId);
      setActiveView('user-detail');
    } catch (err) {
      toast.error('Failed to load user activity');
    }
  };

  useEffect(() => { if (user) fetchAll(); }, [filters.days, filters.entity_type, filters.action]);

  const navGroups = [
    { id: 'back', icon: ArrowLeft, label: 'Back to Dashboard', onClick: () => navigate('/admin') },
  ];

  if (!user) return null;

  return (
    <DashboardShell
      user={user}
      roleLabel="Admin"
      navGroups={navGroups}
      activeTab="activity"
      pageTitle={activeView === 'user-detail' ? `User Activity: ${selectedUserInfo?.name || ''}` : 'Activity Log'}
      showBackButton={activeView === 'user-detail'}
      onBack={() => setActiveView('feed')}
      onLogout={() => { localStorage.clear(); navigate('/'); }}
    >
      {/* Stats Cards */}
      {activeView !== 'user-detail' && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6" data-testid="activity-stats">
          <Card className="p-4 border border-gray-200">
            <p className="text-xs font-semibold uppercase text-gray-500">Total Activities</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total_activities}</p>
            <p className="text-xs text-gray-400">Last {stats.period_days} days</p>
          </Card>
          <Card className="p-4 border border-gray-200">
            <p className="text-xs font-semibold uppercase text-gray-500">Entity Types</p>
            <p className="text-2xl font-bold text-[#2a777a] mt-1">{Object.keys(stats.activities_by_type || {}).length}</p>
            <p className="text-xs text-gray-400">Categories tracked</p>
          </Card>
          <Card className="p-4 border border-gray-200">
            <p className="text-xs font-semibold uppercase text-gray-500">Actions</p>
            <p className="text-2xl font-bold text-[#f7620b] mt-1">{Object.keys(stats.activities_by_action || {}).length}</p>
            <p className="text-xs text-gray-400">Distinct actions</p>
          </Card>
          <Card className="p-4 border border-gray-200">
            <p className="text-xs font-semibold uppercase text-gray-500">Active Users</p>
            <p className="text-2xl font-bold text-leamss-orange-600 mt-1">{(stats.most_active_users || []).length}</p>
            <p className="text-xs text-gray-400">Contributing users</p>
          </Card>
        </div>
      )}

      {/* Filters */}
      {activeView !== 'user-detail' && (
        <Card className="p-4 mb-6 border border-gray-200" data-testid="activity-filters">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-600">Filters:</span>
            </div>
            <Select value={filters.days.toString()} onValueChange={(v) => setFilters({ ...filters, days: parseInt(v) })}>
              <SelectTrigger className="w-[130px] h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Last 24 hours</SelectItem>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.entity_type} onValueChange={(v) => setFilters({ ...filters, entity_type: v === 'all' ? '' : v })}>
              <SelectTrigger className="w-[130px] h-8 text-xs"><SelectValue placeholder="All Types" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="sale">Sales</SelectItem>
                <SelectItem value="case">Cases</SelectItem>
                <SelectItem value="document">Documents</SelectItem>
                <SelectItem value="payment">Payments</SelectItem>
                <SelectItem value="ticket">Tickets</SelectItem>
                <SelectItem value="product">Products</SelectItem>
                <SelectItem value="user">Users</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={fetchAll} className="h-8" data-testid="refresh-activity">
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
            </Button>
            <Badge className="ml-auto bg-gray-100 text-gray-600">{total} records</Badge>
          </div>
        </Card>
      )}

      {/* View Tabs */}
      {activeView !== 'user-detail' && (
        <div className="flex gap-2 mb-4">
          <Button variant={activeView === 'feed' ? 'default' : 'outline'} size="sm"
                  className={activeView === 'feed' ? 'bg-[#2a777a]' : ''} onClick={() => setActiveView('feed')}>
            <Activity className="h-4 w-4 mr-1" /> Live Feed
          </Button>
          <Button variant={activeView === 'by-user' ? 'default' : 'outline'} size="sm"
                  className={activeView === 'by-user' ? 'bg-[#2a777a]' : ''} onClick={() => setActiveView('by-user')}>
            <User className="h-4 w-4 mr-1" /> By User
          </Button>
          <Button variant={activeView === 'by-type' ? 'default' : 'outline'} size="sm"
                  className={activeView === 'by-type' ? 'bg-[#2a777a]' : ''} onClick={() => setActiveView('by-type')}>
            <FileText className="h-4 w-4 mr-1" /> By Type
          </Button>
        </div>
      )}

      {/* Live Feed View */}
      {activeView === 'feed' && (
        <div className="space-y-2" data-testid="activity-feed">
          {(logs.length === 0 && !loading) && (
            <Card className="p-12 text-center">
              <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500">No activity logs found</p>
            </Card>
          )}
          {logs.map((log, idx) => {
            const IconComp = ACTION_ICONS[log.action] || Activity;
            return (
              <Card key={log.id || idx} className="p-3 border border-gray-200 hover:border-gray-300 transition-all" data-testid={`activity-log-${idx}`}>
                <div className="flex items-start gap-3">
                  <div className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${getActionColor(log.action)}`}>
                    <IconComp className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-gray-900">{log.user_name || 'System'}</span>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">{log.user_role}</Badge>
                      <span className="text-sm text-gray-600">{log.action?.replace(/_/g, ' ')}</span>
                      {log.entity_type && (
                        <Badge className={`text-[10px] px-1.5 py-0 ${getActionColor(log.action)}`}>
                          {log.entity_type}
                        </Badge>
                      )}
                    </div>
                    {log.details && <p className="text-xs text-gray-500 mt-0.5 truncate">{typeof log.details === 'object' ? Object.entries(log.details).map(([k,v]) => `${k}: ${v}`).join(', ') : log.details}</p>}
                    {log.new_value && <p className="text-xs text-gray-400 mt-0.5 truncate">{typeof log.new_value === 'object' ? Object.entries(log.new_value).map(([k,v]) => `${k}: ${v}`).join(', ') : log.new_value}</p>}
                    {log.client_name && <p className="text-xs text-gray-400 mt-0.5">Client: {log.client_name}</p>}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-[11px] text-gray-400 whitespace-nowrap">{formatDateTime(log.created_at)}</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* By User View */}
      {activeView === 'by-user' && stats && (
        <div className="space-y-3" data-testid="activity-by-user">
          {(stats.most_active_users || []).map((u, idx) => (
            <Card key={u.user_id || idx} className="p-4 border border-gray-200 cursor-pointer hover:border-[#2a777a]/40 hover:shadow-md transition-all"
                  onClick={() => fetchUserActivity(u.user_id)} data-testid={`user-activity-${idx}`}>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-[#2a777a]/10 flex items-center justify-center">
                  <span className="text-[#2a777a] font-bold text-sm">{u.user_name?.charAt(0) || '?'}</span>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">{u.user_name}</p>
                  <p className="text-xs text-gray-500 capitalize">{u.user_role}</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-[#2a777a]">{u.count}</p>
                  <p className="text-xs text-gray-400">activities</p>
                </div>
                <ChevronRight className="h-5 w-5 text-gray-300" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* By Type View */}
      {activeView === 'by-type' && stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4" data-testid="activity-by-type">
          {Object.entries(stats.activities_by_type || {}).map(([type, count]) => (
            <Card key={type} className="p-4 border border-gray-200 cursor-pointer hover:border-[#2a777a]/40 transition-all"
                  onClick={() => setFilters({ ...filters, entity_type: type })}>
              <p className="text-xs font-semibold uppercase text-gray-500">{type}</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{count}</p>
            </Card>
          ))}
        </div>
      )}

      {/* User Detail View */}
      {activeView === 'user-detail' && (
        <div className="space-y-3" data-testid="user-activity-detail">
          <Card className="p-4 bg-[#2a777a]/5 border border-[#2a777a]/20 mb-4">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-[#2a777a]/10 flex items-center justify-center">
                <span className="text-[#2a777a] font-bold text-lg">{selectedUserInfo?.name?.charAt(0) || '?'}</span>
              </div>
              <div>
                <h3 className="font-bold text-gray-900">{selectedUserInfo?.name}</h3>
                <p className="text-sm text-gray-500">{selectedUserInfo?.email} | <span className="capitalize">{selectedUserInfo?.role}</span></p>
              </div>
              <Badge className="ml-auto bg-[#2a777a] text-white">{userLogs.length} activities</Badge>
            </div>
          </Card>
          {userLogs.map((log, idx) => {
            const IconComp = ACTION_ICONS[log.action] || Activity;
            return (
              <div key={log.id || idx} className="flex items-start gap-3 pl-2">
                <div className="flex flex-col items-center">
                  <div className={`h-7 w-7 rounded-full flex items-center justify-center ${getActionColor(log.action)}`}>
                    <IconComp className="h-3.5 w-3.5" />
                  </div>
                  {idx < userLogs.length - 1 && <div className="w-0.5 h-8 bg-gray-200 mt-1" />}
                </div>
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">{log.action?.replace(/_/g, ' ')}</span>
                    {log.entity_type && <Badge variant="outline" className="text-[10px]">{log.entity_type}</Badge>}
                  </div>
                  {log.details && <p className="text-xs text-gray-500 mt-0.5">{typeof log.details === 'object' ? Object.entries(log.details).map(([k,v]) => `${k}: ${v}`).join(', ') : log.details}</p>}
                  <p className="text-[11px] text-gray-400 mt-0.5">{formatDateTime(log.created_at)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </DashboardShell>
  );
};

export default ActivityLogPage;
