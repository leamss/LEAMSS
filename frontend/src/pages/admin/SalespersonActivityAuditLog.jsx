import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  ShieldCheck, RefreshCw, Download, Search, Filter, Phone, MessageCircle,
  Mail, Clock, TrendingUp, FileText, Eye, Compass, LogIn, LogOut,
  User, Calendar, ArrowLeft, ChevronLeft, ChevronRight, Activity,
  CheckCircle2, AlertCircle, PhoneCall, FileCheck, Layers, Users
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const ACTIVITY_CONFIG = {
  call: { label: 'Call Logged', icon: PhoneCall, bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  phone_call: { label: 'Call Logged', icon: PhoneCall, bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  whatsapp: { label: 'WhatsApp', icon: MessageCircle, bg: 'bg-green-50 text-green-700 border-green-200' },
  email: { label: 'Email Sent', icon: Mail, bg: 'bg-blue-50 text-blue-700 border-blue-200' },
  follow_up: { label: 'Follow-up', icon: Clock, bg: 'bg-amber-50 text-amber-700 border-amber-200' },
  follow_up_created: { label: 'Follow-up Set', icon: Clock, bg: 'bg-amber-50 text-amber-700 border-amber-200' },
  follow_up_completed: { label: 'Follow-up Done', icon: CheckCircle2, bg: 'bg-teal-50 text-teal-700 border-teal-200' },
  status_change: { label: 'Stage Changed', icon: TrendingUp, bg: 'bg-purple-50 text-purple-700 border-purple-200' },
  note: { label: 'Note Added', icon: FileText, bg: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  client_view: { label: 'Profile Viewed', icon: Eye, bg: 'bg-sky-50 text-sky-700 border-sky-200' },
  client_profile_view: { label: 'Profile Viewed', icon: Eye, bg: 'bg-sky-50 text-sky-700 border-sky-200' },
  page_visit: { label: 'Page Visit', icon: Compass, bg: 'bg-slate-50 text-slate-700 border-slate-200' },
  document: { label: 'Document Update', icon: FileCheck, bg: 'bg-pink-50 text-pink-700 border-pink-200' },
  login: { label: 'User Login', icon: LogIn, bg: 'bg-emerald-50 text-emerald-800 border-emerald-300' },
  logout: { label: 'User Logout', icon: LogOut, bg: 'bg-rose-50 text-rose-800 border-rose-300' },
};

function formatTimestamp(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  } catch {
    return isoStr;
  }
}

function timeAgo(isoStr) {
  if (!isoStr) return '';
  try {
    const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return '';
  }
}

export default function SalespersonActivityAuditLog() {
  const navigate = useNavigate();

  // Authentication & Admin Check
  const token = localStorage.getItem('token');
  const authHeaders = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  // Data States
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [salespersons, setSalespersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 50;

  // Filter States
  const [selectedRep, setSelectedRep] = useState('all');
  const [selectedType, setSelectedType] = useState('all');
  const [datePreset, setDatePreset] = useState('7d'); // today, yesterday, 7d, 30d, custom
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Real-time Auto-Refresh
  const [refreshInterval, setRefreshInterval] = useState('15'); // '5', '15', '30', '0' (off)
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Modal for Detail View
  const [inspectItem, setInspectItem] = useState(null);

  // Compute effective start and end dates
  const effectiveDates = useMemo(() => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const toYMD = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (datePreset === 'today') {
      const today = toYMD(now);
      return { start: today, end: today };
    }
    if (datePreset === 'yesterday') {
      const yest = new Date(now);
      yest.setDate(now.getDate() - 1);
      const yestStr = toYMD(yest);
      return { start: yestStr, end: yestStr };
    }
    if (datePreset === '7d') {
      const past = new Date(now);
      past.setDate(now.getDate() - 7);
      return { start: toYMD(past), end: toYMD(now) };
    }
    if (datePreset === '30d') {
      const past = new Date(now);
      past.setDate(now.getDate() - 30);
      return { start: toYMD(past), end: toYMD(now) };
    }
    if (datePreset === 'custom') {
      return { start: startDate, end: endDate };
    }
    return { start: '', end: '' };
  }, [datePreset, startDate, endDate]);

  // Verify Admin Access
  useEffect(() => {
    const checkRole = async () => {
      try {
        const res = await axios.get(`${API}/auth/me`, authHeaders);
        const role = String(res.data?.rbac_role || res.data?.role || '').toLowerCase();
        if (!['admin', 'admin_owner', 'super_admin'].includes(role)) {
          toast.error('Access denied — Activity Audit Log is restricted to Administrators.');
          navigate('/sales/my-crm');
        }
      } catch {
        navigate('/');
      }
    };
    if (token) checkRole();
    else navigate('/');
  }, [authHeaders, navigate, token]);

  // Load Filter Options (Salespersons list)
  const fetchFilterOptions = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/salesperson-activity/filters`, authHeaders);
      if (res.data?.salespersons) {
        setSalespersons(res.data.salespersons);
      }
    } catch {
      // Non-critical
    }
  }, [authHeaders]);

  // Load KPI Stats
  const fetchStats = useCallback(async () => {
    try {
      const days = datePreset === '30d' ? 30 : 7;
      const repQuery = selectedRep !== 'all' ? `&salesperson_id=${selectedRep}` : '';
      const res = await axios.get(`${API}/salesperson-activity/stats?days=${days}${repQuery}`, authHeaders);
      setStats(res.data);
    } catch {
      // Non-critical
    }
  }, [authHeaders, datePreset, selectedRep]);

  // Load Activity Logs
  const fetchLogs = useCallback(async (isAuto = false) => {
    if (!isAuto) setLoading(true);
    else setIsRefreshing(true);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('limit', limit);
      if (selectedRep && selectedRep !== 'all') params.append('salesperson_id', selectedRep);
      if (selectedType && selectedType !== 'all') params.append('activity_type', selectedType);
      if (effectiveDates.start) params.append('start_date', effectiveDates.start);
      if (effectiveDates.end) params.append('end_date', effectiveDates.end);
      if (searchTerm.trim()) params.append('search', searchTerm.trim());

      const res = await axios.get(`${API}/salesperson-activity/logs?${params.toString()}`, authHeaders);
      setLogs(res.data.logs || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
      setLastUpdated(new Date());
    } catch {
      if (!isAuto) toast.error('Failed to load activity logs.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [authHeaders, page, limit, selectedRep, selectedType, effectiveDates, searchTerm]);

  // Initial Load
  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Auto-Refresh Polling Loop
  useEffect(() => {
    const sec = parseInt(refreshInterval, 10);
    if (!sec || sec <= 0) return;

    const interval = setInterval(() => {
      fetchLogs(true);
      fetchStats();
    }, sec * 1000);

    return () => clearInterval(interval);
  }, [refreshInterval, fetchLogs, fetchStats]);

  // Export CSV
  const handleExportCSV = async () => {
    try {
      toast.info('Generating activity audit report...');
      const params = new URLSearchParams();
      if (selectedRep && selectedRep !== 'all') params.append('salesperson_id', selectedRep);
      if (selectedType && selectedType !== 'all') params.append('activity_type', selectedType);
      if (effectiveDates.start) params.append('start_date', effectiveDates.start);
      if (effectiveDates.end) params.append('end_date', effectiveDates.end);
      if (searchTerm.trim()) params.append('search', searchTerm.trim());

      window.open(`${API}/salesperson-activity/export?${params.toString()}`, '_blank');
      toast.success('Download started');
    } catch {
      toast.error('Failed to export CSV report.');
    }
  };

  const handleResetFilters = () => {
    setSelectedRep('all');
    setSelectedType('all');
    setDatePreset('7d');
    setStartDate('');
    setEndDate('');
    setSearchTerm('');
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-4 md:p-8 space-y-6">
      
      {/* ── TOP HEADER ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/admin')}
              className="h-8 w-8 p-0 text-slate-500 hover:text-slate-800"
              title="Return to Admin Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <span>Salesperson Activity Audit Log</span>
              <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 font-semibold text-xs border-indigo-200">
                Admin Audit Trail
              </Badge>
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 pl-11">
            Real-time immutable monitoring of all CRM calls, WhatsApp, emails, follow-ups, client views, logins, and status updates.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 pl-11 md:pl-0 flex-wrap">
          {/* Live Indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 text-xs text-emerald-700 dark:text-emerald-300 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Live Stream
          </div>

          {/* Auto Refresh Select */}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span>Refresh:</span>
            <Select value={refreshInterval} onValueChange={setRefreshInterval}>
              <SelectTrigger className="h-8 w-24 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">Every 5s</SelectItem>
                <SelectItem value="15">Every 15s</SelectItem>
                <SelectItem value="30">Every 30s</SelectItem>
                <SelectItem value="0">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => { fetchLogs(); fetchStats(); }}
            disabled={loading || isRefreshing}
            className="h-8 text-xs gap-1.5 border-slate-200 text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            size="sm"
            onClick={handleExportCSV}
            className="h-8 text-xs gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* ── KPI METRICS SUMMARY CARDS ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 border-slate-200 dark:border-slate-700 shadow-sm bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Tracked Actions</span>
            <Activity className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {stats?.total_activities ?? '—'}
            </span>
            {stats?.today_activities > 0 && (
              <span className="text-xs font-semibold text-emerald-600">
                +{stats.today_activities} today
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Logged in selected period</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-700 shadow-sm bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Calls & Talk Time</span>
            <Phone className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {stats?.total_calls ?? 0}
            </span>
            <span className="text-xs font-semibold text-emerald-600">
              ({stats?.total_talk_time_display ?? '0s'})
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Strictly actual recorded durations</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-700 shadow-sm bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Outreach Messages</span>
            <MessageCircle className="w-4 h-4 text-green-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {(stats?.total_whatsapp || 0) + (stats?.total_emails || 0)}
            </span>
            <span className="text-xs text-slate-500">
              ({stats?.total_whatsapp || 0} WA / {stats?.total_emails || 0} Mail)
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Direct client communications</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-700 shadow-sm bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Sales Reps</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 dark:text-white">
              {stats?.active_salespersons_count ?? 0}
            </span>
            <span className="text-xs text-slate-500">performing in CRM</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Unique reps with activity</p>
        </Card>
      </div>

      {/* ── FILTER BAR ── */}
      <Card className="p-4 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-300">
            <Filter className="w-3.5 h-3.5 text-indigo-600" />
            <span>Filter Activities</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetFilters}
              className="h-7 text-xs text-slate-500 hover:text-slate-800"
            >
              Reset Filters
            </Button>
            <span className="text-xs text-slate-400">
              Showing <strong>{logs.length}</strong> of <strong>{total}</strong> activities
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          
          {/* 1. Salesperson Filter */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-500">Salesperson</label>
            <Select value={selectedRep} onValueChange={(v) => { setSelectedRep(v); setPage(1); }}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="All Salespersons" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Salespersons</SelectItem>
                {salespersons.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.name} ({r.role || r.rbac_role})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 2. Activity Type Filter */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-500">Activity Type</label>
            <Select value={selectedType} onValueChange={(v) => { setSelectedType(v); setPage(1); }}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="All Activities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Activities</SelectItem>
                <SelectItem value="call">Calls (with Duration)</SelectItem>
                <SelectItem value="client_view">Client Profile Views</SelectItem>
                <SelectItem value="page_visit">CRM Page Visits</SelectItem>
                <SelectItem value="whatsapp">WhatsApp Messages</SelectItem>
                <SelectItem value="email">Emails Sent</SelectItem>
                <SelectItem value="follow_up">Follow-ups</SelectItem>
                <SelectItem value="note">Notes Added</SelectItem>
                <SelectItem value="status_change">Stage / Status Changes</SelectItem>
                <SelectItem value="document">Document Updates</SelectItem>
                <SelectItem value="login">Logins</SelectItem>
                <SelectItem value="logout">Logouts</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 3. Date Preset */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-500">Date Range</label>
            <Select value={datePreset} onValueChange={(v) => { setDatePreset(v); setPage(1); }}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="today">Today</SelectItem>
                <SelectItem value="yesterday">Yesterday</SelectItem>
                <SelectItem value="7d">Last 7 Days</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
                <SelectItem value="custom">Custom Range...</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 4. Search Query */}
          <div className="space-y-1 md:col-span-2">
            <label className="text-[11px] font-semibold text-slate-500">Search Rep, Client, or Notes</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-3" />
              <Input
                placeholder="Search by client name, rep, notes..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
                className="h-9 pl-8 text-xs"
              />
            </div>
          </div>
        </div>

        {/* Custom Date Inputs if Custom selected */}
        {datePreset === 'custom' && (
          <div className="pt-2 flex items-center gap-3 border-t border-slate-100 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">From:</span>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
                className="h-8 text-xs w-36"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">To:</span>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
                className="h-8 text-xs w-36"
              />
            </div>
          </div>
        )}
      </Card>

      {/* ── REAL-TIME AUDIT LOG FEED & TABLE ── */}
      <Card className="bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Salesperson</th>
                <th className="py-3 px-4">Client / Lead</th>
                <th className="py-3 px-4">Activity Type</th>
                <th className="py-3 px-4">Date & Exact Time</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Activity Details</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-500" />
                    Loading activity audit logs...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="font-medium text-slate-600">No activity logs found</p>
                    <p className="text-[11px] text-slate-400 mt-1">Try broadening your date filter or selecting all salespersons.</p>
                  </td>
                </tr>
              ) : (
                logs.map((item) => {
                  const cfg = ACTIVITY_CONFIG[item.activity_type] || {
                    label: item.activity_type?.replace('_', ' ').toUpperCase() || 'ACTIVITY',
                    icon: Activity,
                    bg: 'bg-slate-50 text-slate-700 border-slate-200'
                  };
                  const IconComponent = cfg.icon;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-750/50 transition-colors"
                    >
                      {/* 1. Salesperson */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs uppercase flex-shrink-0">
                            {item.salesperson_name ? item.salesperson_name.charAt(0) : 'U'}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900 dark:text-white">
                              {item.salesperson_name || 'Unknown Rep'}
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono">
                              {item.salesperson_email || item.salesperson_role}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* 2. Client / Lead */}
                      <td className="py-3.5 px-4">
                        {item.client_name ? (
                          <div>
                            <div className="font-medium text-slate-800 dark:text-slate-200">
                              {item.client_name}
                            </div>
                            <div className="text-[10px] text-slate-400">
                              {item.client_phone || item.client_email || '—'}
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-xs">— (System/General)</span>
                        )}
                      </td>

                      {/* 3. Activity Type Badge */}
                      <td className="py-3.5 px-4">
                        {item.activity_type === 'whatsapp' ? (() => {
                          const rawWaStatus = (item.message_status || item.metadata?.status || '').toLowerCase();
                          const isWaFailed = rawWaStatus === 'failed';
                          const isWaPending = rawWaStatus === 'pending' || rawWaStatus === 'pending_confirmation';
                          if (isWaFailed) {
                            return (
                              <Badge variant="outline" className="gap-1 px-2 py-0.5 text-[11px] font-semibold border bg-rose-50 text-rose-700 border-rose-200">
                                <AlertCircle className="w-3 h-3 text-rose-600" />
                                WhatsApp (Failed)
                              </Badge>
                            );
                          }
                          if (isWaPending) {
                            return (
                              <Badge variant="outline" className="gap-1 px-2 py-0.5 text-[11px] font-semibold border bg-amber-50 text-amber-700 border-amber-200">
                                <Clock className="w-3 h-3 text-amber-600" />
                                WhatsApp (Pending)
                              </Badge>
                            );
                          }
                          return (
                            <Badge variant="outline" className="gap-1 px-2 py-0.5 text-[11px] font-semibold border bg-green-50 text-green-700 border-green-200">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              WhatsApp (Sent)
                            </Badge>
                          );
                        })() : (
                          <Badge
                            variant="outline"
                            className={`gap-1.5 px-2 py-0.5 text-[11px] font-semibold border ${cfg.bg}`}
                          >
                            <IconComponent className="w-3 h-3" />
                            {cfg.label}
                          </Badge>
                        )}
                      </td>

                      {/* 4. Date & Exact Timestamp */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-medium text-slate-700 dark:text-slate-300">
                          {formatTimestamp(item.created_at)}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {timeAgo(item.created_at)}
                        </div>
                      </td>

                      {/* 5. Actual Duration */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {item.duration_display ? (
                          <span className="inline-flex items-center gap-1 font-mono font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded text-[11px]">
                            <Clock className="w-3 h-3" />
                            {item.duration_display}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono">—</span>
                        )}
                      </td>

                      {/* 6. Activity Details */}
                      <td className="py-3.5 px-4 max-w-xs md:max-w-md">
                        <div className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                          {item.title}
                        </div>
                        {item.details && (
                          <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                            {item.details}
                          </div>
                        )}
                        {item.start_time && item.end_time && (
                          <div className="text-[10px] text-sky-700 font-mono mt-1 font-semibold flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5 text-sky-600" />
                            <span>Start: {item.start_time} &bull; End: {item.end_time}</span>
                          </div>
                        )}
                        {(item.session_state === 'active' || item.metadata?.session_state === 'active') && (
                          <div className="text-[10px] text-emerald-700 font-bold mt-1 flex items-center gap-1 animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            <span>Actively Viewing Now (Started: {item.start_time || item.time})</span>
                          </div>
                        )}
                        {item.activity_type === 'whatsapp' && (() => {
                          const rawWaStatus = (item.message_status || item.metadata?.status || '').toLowerCase();
                          const isWaFailed = rawWaStatus === 'failed';
                          const isWaPending = rawWaStatus === 'pending' || rawWaStatus === 'pending_confirmation';
                          return (
                            <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                isWaFailed
                                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                                  : isWaPending
                                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              }`}>
                                {isWaFailed ? <AlertCircle className="w-2.5 h-2.5" /> : isWaPending ? <Clock className="w-2.5 h-2.5" /> : <CheckCircle2 className="w-2.5 h-2.5" />}
                                Status: {isWaFailed ? 'Failed' : isWaPending ? 'Pending' : 'Sent'}
                                {item.metadata?.channel === 'whatsapp_web' ? ' (WhatsApp Web)' : ''}
                              </span>
                              {item.metadata?.error_message && (
                                <span className="text-[10px] text-rose-600 truncate max-w-xs">
                                  Reason: {item.metadata.error_message}
                                </span>
                              )}
                            </div>
                          );
                        })()}
                      </td>

                      {/* 7. Inspect Button */}
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setInspectItem(item)}
                          className="h-7 text-xs text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50"
                        >
                          View Details
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── PAGINATION CONTROLS ── */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between flex-wrap gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span>Page <strong>{page}</strong> of <strong>{totalPages}</strong></span>
            <span>•</span>
            <span>Total <strong>{total}</strong> logged activities</span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="h-8 text-xs gap-1 border-slate-200"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="h-8 text-xs gap-1 border-slate-200"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </Card>

      {/* ── DETAIL INSPECTION MODAL ── */}
      <Dialog open={!!inspectItem} onOpenChange={(open) => !open && setInspectItem(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              Activity Audit Record
            </DialogTitle>
            <DialogDescription className="text-xs">
              Immutable timestamped log entry stored permanently in MongoDB.
            </DialogDescription>
          </DialogHeader>

          {inspectItem && (
            <div className="space-y-4 text-xs py-2">
              <div className="grid grid-cols-2 gap-3 bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Salesperson</span>
                  <p className="font-semibold text-slate-900 dark:text-white mt-0.5">{inspectItem.salesperson_name}</p>
                  <p className="text-slate-500 font-mono text-[10px]">{inspectItem.salesperson_email || inspectItem.salesperson_role}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Client / Lead</span>
                  <p className="font-semibold text-slate-900 dark:text-white mt-0.5">{inspectItem.client_name || '—'}</p>
                  <p className="text-slate-500 text-[10px]">{inspectItem.client_phone || inspectItem.client_email || '—'}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Activity Type</span>
                  <p className="font-semibold text-slate-900 dark:text-white mt-0.5 capitalize">{inspectItem.activity_type?.replace('_', ' ')}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Actual Duration</span>
                  <p className="font-semibold text-slate-900 dark:text-white mt-0.5">{inspectItem.duration_display || '—'}</p>
                </div>
                {(inspectItem.start_time || inspectItem.metadata?.start_time) && (
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Activity Start Time</span>
                    <p className="font-mono text-slate-900 dark:text-white mt-0.5 font-semibold text-sky-600">{inspectItem.start_time || inspectItem.metadata?.start_time}</p>
                  </div>
                )}
                {(inspectItem.end_time || inspectItem.metadata?.end_time) && (
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Activity End Time</span>
                    <p className="font-mono text-slate-900 dark:text-white mt-0.5 font-semibold text-sky-600">{inspectItem.end_time || inspectItem.metadata?.end_time}</p>
                  </div>
                )}
                <div className="col-span-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Timestamp</span>
                  <p className="font-mono text-slate-700 dark:text-slate-300 mt-0.5">{inspectItem.created_at}</p>
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400">Title & Action Summary</span>
                <p className="font-semibold text-slate-800 dark:text-slate-200 mt-1">{inspectItem.title}</p>
              </div>

              {inspectItem.details && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Full Details / Notes</span>
                  <div className="mt-1 p-3 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {inspectItem.details}
                  </div>
                </div>
              )}

              {inspectItem.metadata && Object.keys(inspectItem.metadata).length > 0 && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Raw Metadata</span>
                  <pre className="mt-1 p-2.5 bg-slate-100 dark:bg-slate-950 rounded-lg text-[10px] font-mono overflow-x-auto text-slate-600 dark:text-slate-400">
                    {JSON.stringify(inspectItem.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

    </div>
  );
}
