import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Activity, Search, Filter, User, Calendar, 
  ChevronLeft, ChevronRight, RefreshCw
} from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    entityType: '',
    action: '',
    startDate: '',
    endDate: ''
  });
  const [page, setPage] = useState(1);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [page, filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (filters.entityType) params.append('entity_type', filters.entityType);
      if (filters.action) params.append('action', filters.action);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);

      const response = await axios.get(`${API_URL}/api/activity/logs?${params}`, { headers });
      setLogs(response.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/activity/stats?days=7`, { headers });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActionColor = (action) => {
    if (action?.includes('create') || action?.includes('add')) return 'bg-green-100 text-green-700';
    if (action?.includes('update') || action?.includes('edit')) return 'bg-blue-100 text-blue-700';
    if (action?.includes('delete') || action?.includes('remove')) return 'bg-red-100 text-red-700';
    if (action?.includes('approve')) return 'bg-emerald-100 text-emerald-700';
    if (action?.includes('reject')) return 'bg-orange-100 text-orange-700';
    return 'bg-gray-100 text-gray-700';
  };

  const entityTypes = ['user', 'sale', 'case', 'ticket', 'document', 'product'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
          <p className="text-gray-500">Track all system activities and changes</p>
        </div>
        <Button variant="outline" onClick={fetchLogs}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Activities (7d)</p>
                  <p className="text-2xl font-bold">{stats.total_activities}</p>
                </div>
                <Activity className="h-8 w-8 text-indigo-600" />
              </div>
            </CardContent>
          </Card>

          {stats.most_active_users?.slice(0, 3).map((user, idx) => (
            <Card key={user.user_id}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">#{idx + 1} Active User</p>
                    <p className="font-medium truncate">{user.user_name}</p>
                    <p className="text-sm text-indigo-600">{user.count} actions</p>
                  </div>
                  <User className="h-8 w-8 text-purple-600" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <Select 
              value={filters.entityType || "all"} 
              onValueChange={(v) => setFilters({ ...filters, entityType: v === "all" ? "" : v })}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Entity Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {entityTypes.map(type => (
                  <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Input
              type="text"
              placeholder="Filter by action..."
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="w-48"
            />

            <Input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
              className="w-40"
            />

            <Input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
              className="w-40"
            />

            <Button 
              variant="ghost" 
              onClick={() => setFilters({ entityType: '', action: '', startDate: '', endDate: '' })}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Activity List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : logs.length > 0 ? (
            <div className="space-y-4">
              {logs.map((log) => (
                <div 
                  key={log.id} 
                  className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <User className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{log.user_name || 'System'}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                        {log.action}
                      </span>
                      <span className="text-gray-500 capitalize">{log.entity_type}</span>
                    </div>
                    {log.entity_id && (
                      <p className="text-sm text-gray-500 mt-1">
                        Entity ID: {log.entity_id.substring(0, 8)}...
                      </p>
                    )}
                    {log.new_value && (
                      <details className="mt-2">
                        <summary className="text-sm text-indigo-600 cursor-pointer">View changes</summary>
                        <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                          {JSON.stringify(log.new_value, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 flex items-center gap-1 flex-shrink-0">
                    <Calendar className="h-4 w-4" />
                    {formatDate(log.created_at)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No activity logs found</p>
            </div>
          )}

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <Button
              variant="outline"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <Button
              variant="outline"
              onClick={() => setPage(p => p + 1)}
              disabled={logs.length < 20}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ActivityLog;
