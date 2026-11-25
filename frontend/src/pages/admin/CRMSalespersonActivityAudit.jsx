import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Users, Phone, PhoneCall, MessageSquare, Mail, Calendar, Clock,
  CheckCircle2, XCircle, AlertCircle, Search, RefreshCw, ChevronRight,
  Filter, ArrowLeft, UserCheck, Shield, ExternalLink, ChevronDown,
  Activity, ArrowUpRight, ShieldCheck, Timer, FileText, Send, User,
  TrendingUp, BarChart3, Radio, Sparkles, CheckCheck, PhoneIncoming,
  PhoneOutgoing, Inbox, CalendarDays
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const ACTIVITY_BADGES = {
  call: { label: 'Call', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: PhoneCall },
  phone_call: { label: 'Call', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: PhoneCall },
  telephony_call: { label: 'Call', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: PhoneCall },
  whatsapp: { label: 'WhatsApp', bg: 'bg-green-50 text-green-700 border-green-200', icon: MessageSquare },
  email: { label: 'Email', bg: 'bg-blue-50 text-blue-700 border-blue-200', icon: Mail },
  follow_up: { label: 'Follow-up', bg: 'bg-amber-50 text-amber-700 border-amber-200', icon: Calendar },
  follow_up_created: { label: 'Follow-up Created', bg: 'bg-amber-50 text-amber-700 border-amber-200', icon: Calendar },
  follow_up_completed: { label: 'Follow-up Done', bg: 'bg-teal-50 text-teal-700 border-teal-200', icon: CheckCircle2 },
  status_change: { label: 'Status Change', bg: 'bg-purple-50 text-purple-700 border-purple-200', icon: TrendingUp },
  stage_change: { label: 'Stage Move', bg: 'bg-purple-50 text-purple-700 border-purple-200', icon: TrendingUp },
  note: { label: 'Note Added', bg: 'bg-slate-100 text-slate-700 border-slate-300', icon: FileText },
  client_view: { label: 'Client View / Session', bg: 'bg-sky-50 text-sky-700 border-sky-200', icon: Clock },
  client_profile_view: { label: 'Client View / Session', bg: 'bg-sky-50 text-sky-700 border-sky-200', icon: Clock },
  page_visit: { label: 'Page Visit', bg: 'bg-slate-50 text-slate-700 border-slate-200', icon: Activity },
  login: { label: 'Login', bg: 'bg-sky-50 text-sky-700 border-sky-200', icon: ShieldCheck },
  logout: { label: 'Logout', bg: 'bg-rose-50 text-rose-700 border-rose-200', icon: XCircle }
};

const renderWhatsAppStatusBadge = (act) => {
  const rawStatus = (act.message_status || act.metadata?.status || act.metadata?.message_status || 'sent').toLowerCase();
  const isFailed = rawStatus === 'failed';
  const isPending = rawStatus === 'pending' || rawStatus === 'pending_confirmation';
  const channel = act.metadata?.channel === 'whatsapp_web' ? ' (WhatsApp Web)' : '';

  if (isFailed) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-rose-50 text-rose-800 rounded border border-rose-200 font-semibold text-[10px]">
        <AlertCircle className="w-3 h-3 text-rose-600" />
        Status: <b>Failed{channel}</b>
        {act.metadata?.error_message && (
          <span className="text-rose-600 font-normal">({act.metadata.error_message})</span>
        )}
      </span>
    );
  }

  if (isPending) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-50 text-amber-800 rounded border border-amber-200 font-semibold text-[10px]">
        <Clock className="w-3 h-3 text-amber-600" />
        Status: <b>Pending{channel}</b>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-emerald-50 text-emerald-800 rounded border border-emerald-200 font-semibold text-[10px]">
      <CheckCheck className="w-3 h-3 text-emerald-600" />
      Status: <b>Sent{channel}</b>
    </span>
  );
};

// Asia/Kolkata (IST) standard timezone formatters
const formatDateTime = (timestamp, fallback) => {
  if (!timestamp && fallback) return fallback;
  if (!timestamp) return '—';
  try {
    let d = new Date(timestamp);
    if (isNaN(d.getTime())) return fallback || timestamp;
    const now = new Date();
    if (d > now) d = now;
    return d.toLocaleString('en-US', {
      timeZone: 'Asia/Kolkata',
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    }).replace(',', ' •');
  } catch {
    return fallback || timestamp;
  }
};

const formatTimeOnly = (timestamp, fallback) => {
  if (!timestamp && fallback) return fallback;
  if (!timestamp) return '—';
  try {
    let d = new Date(timestamp);
    if (isNaN(d.getTime())) return fallback || timestamp;
    const now = new Date();
    if (d > now) d = now;
    return d.toLocaleTimeString('en-US', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  } catch {
    return fallback || timestamp;
  }
};

const formatDateOnly = (timestamp, fallback) => {
  if (!timestamp && fallback) return fallback;
  if (!timestamp) return '—';
  try {
    let d = new Date(timestamp);
    if (isNaN(d.getTime())) return fallback || timestamp;
    const now = new Date();
    if (d > now) d = now;
    return d.toLocaleDateString('en-US', {
      timeZone: 'Asia/Kolkata',
      month: 'short',
      day: '2-digit',
      year: 'numeric'
    });
  } catch {
    return fallback || timestamp;
  }
};

export default function CRMSalespersonActivityAudit({ currentUser = null, isSalespersonOnly = false, onOpenLeadWorkspace }) {
  // Salespersons list state
  const [salespersons, setSalespersons] = useState([]);
  const [teamTotals, setTeamTotals] = useState(null);
  const [loadingSalespersons, setLoadingSalespersons] = useState(!isSalespersonOnly);

  // Selected salesperson drilldown
  const [selectedRep, setSelectedRep] = useState(() => {
    if (isSalespersonOnly && currentUser) {
      const uid = currentUser.id || currentUser._id;
      return {
        id: uid,
        name: currentUser.name || 'Sales Representative',
        email: currentUser.email || '',
        role: currentUser.role || 'salesperson',
        role_label: (currentUser.role || 'Salesperson').replace(/_/g, ' ').toUpperCase(),
        is_active_now: true,
      };
    }
    return null;
  });
  const [clientHistory, setClientHistory] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Filters
  const [searchRep, setSearchRep] = useState('');
  const [repTypeFilter, setRepTypeFilter] = useState('all'); // 'all' | 'internal' | 'external'
  const [clientSearch, setClientSearch] = useState('');
  const [selectedClientId, setSelectedClientId] = useState('all');
  const [activityTypeFilter, setActivityTypeFilter] = useState('all');
  const [datePreset, setDatePreset] = useState('all'); // 'all' | 'today' | 'yesterday' | '7d' | '30d' | 'custom'
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [viewMode, setViewMode] = useState('client_grouped'); // 'client_grouped' | 'date_wise' | 'timeline'

  // Expanded clients state in grouped mode
  const [expandedClients, setExpandedClients] = useState({});

  // Real-time auto-refresh interval
  const [refreshInterval, setRefreshInterval] = useState(15); // 0 (off), 5, 15, 30
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(15);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(new Date());

  const token = localStorage.getItem('token');
  const authHeader = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  // Compute actual date bounds from preset
  const { startDate, endDate } = useMemo(() => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const toYMD = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (datePreset === 'today') {
      const todayStr = toYMD(now);
      return { startDate: todayStr, endDate: todayStr };
    }
    if (datePreset === 'yesterday') {
      const y = new Date(now);
      y.setDate(y.getDate() - 1);
      const yStr = toYMD(y);
      return { startDate: yStr, endDate: yStr };
    }
    if (datePreset === '7d') {
      const d = new Date(now);
      d.setDate(d.getDate() - 6);
      return { startDate: toYMD(d), endDate: toYMD(now) };
    }
    if (datePreset === '30d') {
      const d = new Date(now);
      d.setDate(d.getDate() - 29);
      return { startDate: toYMD(d), endDate: toYMD(now) };
    }
    if (datePreset === 'custom') {
      const s = (customStartDate || '').trim();
      const e = (customEndDate || '').trim();
      return { startDate: s, endDate: e };
    }
    return { startDate: '', endDate: '' };
  }, [datePreset, customStartDate, customEndDate]);

  // Fetch all salespersons with aggregated metrics (Admin only)
  const fetchSalespersons = useCallback(async (showToast = false) => {
    if (isSalespersonOnly) return;
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (searchRep) params.append('search', searchRep);

      const res = await axios.get(`${API}/salesperson-activity/salespersons-list?${params.toString()}`, authHeader);
      if (res.data?.success) {
        setSalespersons(res.data.salespersons || []);
        setTeamTotals(res.data.team_totals || null);
        setLastRefreshedAt(new Date());
        if (showToast) toast.success('Salesperson metrics updated');
      }
    } catch (err) {
      console.error(err);
      if (showToast) toast.error('Failed to load salespersons list');
    } finally {
      setLoadingSalespersons(false);
    }
  }, [startDate, endDate, searchRep, authHeader, isSalespersonOnly]);

  // Fetch client-wise activity history for selected salesperson
  const fetchClientHistory = useCallback(async (repId, showToast = false) => {
    if (!repId) return;
    setLoadingHistory(true);
    try {
      const params = new URLSearchParams();
      if (selectedClientId && selectedClientId !== 'all') params.append('client_id', selectedClientId);
      if (activityTypeFilter && activityTypeFilter !== 'all') params.append('activity_type', activityTypeFilter);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (clientSearch) params.append('search', clientSearch);

      const res = await axios.get(`${API}/salesperson-activity/salesperson/${repId}/client-history?${params.toString()}`, authHeader);
      if (res.data?.success) {
        setClientHistory(res.data);
        setLastRefreshedAt(new Date());
        // Default expand top 3 clients
        if (res.data.clients?.length) {
          const initExp = {};
          res.data.clients.slice(0, 3).forEach((c, idx) => {
            initExp[c.client_id || c.client_name || idx] = true;
          });
          setExpandedClients((prev) => ({ ...initExp, ...prev }));
        }
        if (showToast) toast.success('Client activities refreshed');
      }
    } catch (err) {
      console.error(err);
      if (showToast) toast.error('Failed to load client activity history');
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedClientId, activityTypeFilter, startDate, endDate, clientSearch, authHeader]);

  // Initial load
  useEffect(() => {
    if (!isSalespersonOnly) {
      fetchSalespersons();
    } else if (currentUser) {
      const uid = currentUser.id || currentUser._id;
      if (!selectedRep || selectedRep.id !== uid) {
        setSelectedRep({
          id: uid,
          name: currentUser.name || 'Sales Representative',
          email: currentUser.email || '',
          role: currentUser.role || 'salesperson',
          role_label: (currentUser.role || 'Salesperson').replace(/_/g, ' ').toUpperCase(),
          is_active_now: true,
        });
      }
    }
  }, [fetchSalespersons, isSalespersonOnly, currentUser]);

  // When selected rep changes or filters change
  useEffect(() => {
    if (selectedRep?.id) {
      fetchClientHistory(selectedRep.id);
    }
  }, [selectedRep, fetchClientHistory]);

  // Real-time timer countdown
  useEffect(() => {
    if (!refreshInterval || refreshInterval <= 0) return;

    setSecondsUntilRefresh(refreshInterval);
    const timer = setInterval(() => {
      setSecondsUntilRefresh((prev) => {
        if (prev <= 1) {
          if (selectedRep?.id) {
            fetchClientHistory(selectedRep.id);
          } else if (!isSalespersonOnly) {
            fetchSalespersons();
          }
          return refreshInterval;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [refreshInterval, selectedRep, isSalespersonOnly, fetchClientHistory, fetchSalespersons]);

  // Handle manual refresh
  const handleManualRefresh = () => {
    if (selectedRep?.id) {
      fetchClientHistory(selectedRep.id, true);
    } else if (!isSalespersonOnly) {
      fetchSalespersons(true);
    }
  };

  // Toggle client card expansion
  const toggleClientExpand = (key) => {
    setExpandedClients((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Filter salespersons by internal/external
  const filteredSalespersons = useMemo(() => {
    return salespersons.filter((r) => {
      if (repTypeFilter === 'internal') return r.salesperson_type === 'internal';
      if (repTypeFilter === 'external') return r.salesperson_type === 'external';
      return true;
    });
  }, [salespersons, repTypeFilter]);

  // Filter clients inside selected salesperson
  const filteredClients = useMemo(() => {
    if (!clientHistory?.clients) return [];
    if (!clientSearch) return clientHistory.clients;
    const q = clientSearch.toLowerCase();
    return clientHistory.clients.filter(
      (c) =>
        (c.client_name || '').toLowerCase().includes(q) ||
        (c.client_email || '').toLowerCase().includes(q) ||
        (c.client_phone || '').toLowerCase().includes(q)
    );
  }, [clientHistory, clientSearch]);

  // Filter timeline items
  const filteredTimeline = useMemo(() => {
    if (!clientHistory?.timeline) return [];
    let items = clientHistory.timeline;
    if (selectedClientId && selectedClientId !== 'all') {
      items = items.filter((i) => i.client_id === selectedClientId);
    }
    if (activityTypeFilter && activityTypeFilter !== 'all') {
      items = items.filter((i) => i.activity_type === activityTypeFilter);
    }
    if (clientSearch) {
      const q = clientSearch.toLowerCase();
      items = items.filter(
        (i) =>
          (i.client_name || '').toLowerCase().includes(q) ||
          (i.title || '').toLowerCase().includes(q) ||
          (i.details || '').toLowerCase().includes(q)
      );
    }
    return items;
  }, [clientHistory, selectedClientId, activityTypeFilter, clientSearch]);

  return (
    <div className="space-y-5" data-testid="crm-salesperson-activity-audit-view">
      {/* ─── TOP HEADER BAR ─── */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${isSalespersonOnly ? 'bg-emerald-50 border-emerald-200 text-emerald-600' : 'bg-indigo-50 border-indigo-200 text-indigo-600'} border flex items-center justify-center shadow-sm`}>
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  {isSalespersonOnly ? 'My Activity Report & Audit History' : 'Salesperson Activity Audit Log'}
                </h1>
                <Badge variant="outline" className={isSalespersonOnly ? 'bg-emerald-50 text-emerald-700 border-emerald-200 text-xs font-semibold' : 'bg-indigo-50 text-indigo-700 border-indigo-200 text-xs font-semibold'}>
                  {isSalespersonOnly ? 'My Activity' : 'Admin Real-Time'}
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {isSalespersonOnly
                  ? 'Real-time breakdown of your calls, talk durations, WhatsApp messages, emails, client interactions, and date-wise performance'
                  : 'Real-time tracking of calls, durations, WhatsApp, emails, follow-ups, and client interactions'}
              </p>
            </div>
          </div>

          {/* Real-time controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Live Indicator */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>Live Feed</span>
              {refreshInterval > 0 && (
                <span className="text-[11px] text-emerald-600 font-mono">({secondsUntilRefresh}s)</span>
              )}
            </div>

            {/* Refresh Interval Selector */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
              <Timer className="w-3.5 h-3.5 text-slate-500 ml-1.5 mr-0.5" />
              {[
                { label: '5s', val: 5 },
                { label: '15s', val: 15 },
                { label: '30s', val: 30 },
                { label: 'Off', val: 0 }
              ].map((opt) => (
                <button
                  key={opt.val}
                  onClick={() => setRefreshInterval(opt.val)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                    refreshInterval === opt.val
                      ? 'bg-white text-indigo-700 shadow-sm font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Manual Refresh Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              className="h-8 gap-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Date presets bar */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1.5 overflow-x-auto">
            <span className="text-slate-500 font-medium mr-1 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Period:
            </span>
            {[
              { id: 'all', label: 'All Time' },
              { id: 'today', label: 'Today' },
              { id: 'yesterday', label: 'Yesterday' },
              { id: '7d', label: 'Last 7 Days' },
              { id: '30d', label: 'Last 30 Days' },
              { id: 'custom', label: 'Custom' }
            ].map((p) => (
              <button
                key={p.id}
                onClick={() => setDatePreset(p.id)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  datePreset === p.id
                    ? 'bg-indigo-600 text-white font-medium shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {datePreset === 'custom' && (
            <div className="flex items-center gap-2">
              <Input
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="h-8 w-36 text-xs bg-slate-50"
              />
              <span className="text-slate-400">to</span>
              <Input
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="h-8 w-36 text-xs bg-slate-50"
              />
            </div>
          )}

          <div className="text-[11px] text-slate-400">
            Last synced: {lastRefreshedAt.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* ─── LEVEL 1: ALL SALESPERSONS LIST (When no rep is selected) ─── */}
      {!selectedRep && !isSalespersonOnly && (
        <div className="space-y-5">
          {/* Team KPI Summary Cards */}
          {teamTotals && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">Salespersons</span>
                  <Users className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_salespersons}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Active team members</div>
              </Card>

              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">Total Activities</span>
                  <Activity className="w-4 h-4 text-teal-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_activities.toLocaleString()}</div>
                <div className="text-[11px] text-teal-600 mt-0.5 font-medium">Logged interactions</div>
              </Card>

              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">Total Calls</span>
                  <PhoneCall className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_calls}</div>
                <div className="text-[11px] text-emerald-600 mt-0.5 font-medium truncate" title={teamTotals.total_talk_time_display}>
                  Talk: {teamTotals.total_talk_time_display}
                </div>
              </Card>

              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">WhatsApp</span>
                  <MessageSquare className="w-4 h-4 text-green-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_whatsapp}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Client messages</div>
              </Card>

              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">Emails</span>
                  <Mail className="w-4 h-4 text-blue-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_emails}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Outbound emails</div>
              </Card>

              <Card className="p-3.5 bg-white border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-500 uppercase">Follow-ups</span>
                  <Calendar className="w-4 h-4 text-amber-500" />
                </div>
                <div className="text-xl font-bold text-slate-900 mt-1">{teamTotals.total_followups}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Scheduled / done</div>
              </Card>
            </div>
          )}

          {/* Salespersons Filter and Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <Input
                placeholder="Search salesperson by name or email..."
                value={searchRep}
                onChange={(e) => setSearchRep(e.target.value)}
                className="pl-9 h-9 text-xs bg-white border-slate-200"
              />
            </div>

            <div className="flex items-center gap-1.5 bg-white p-1 rounded-lg border border-slate-200 text-xs">
              <span className="text-slate-400 px-2 font-medium">Type:</span>
              {[
                { id: 'all', label: 'All Salespersons' },
                { id: 'internal', label: 'Internal' },
                { id: 'external', label: 'External' }
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setRepTypeFilter(t.id)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    repTypeFilter === t.id
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Salespersons Cards Grid */}
          {loadingSalespersons ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
              <p className="text-sm text-slate-600 font-medium">Loading salespersons audit metrics...</p>
            </div>
          ) : filteredSalespersons.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
              <Users className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <h3 className="text-base font-semibold text-slate-900">No Salespersons Found</h3>
              <p className="text-sm text-slate-500 mt-1">Try adjusting your search or date range filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSalespersons.map((rep) => {
                const initials = (rep.name || 'SP')
                  .split(' ')
                  .map((w) => w[0])
                  .slice(0, 2)
                  .join('')
                  .toUpperCase();

                return (
                  <Card
                    key={rep.id}
                    onClick={() => {
                      setSelectedRep(rep);
                      setSelectedClientId('all');
                      setClientSearch('');
                    }}
                    className="p-5 bg-white border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden"
                  >
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white font-bold text-sm flex items-center justify-center shadow-sm">
                            {initials}
                          </div>
                          {rep.is_active_now && (
                            <span className="absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 border-2 border-white"></span>
                            </span>
                          )}
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors flex items-center gap-1.5">
                            {rep.name}
                            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all" />
                          </h3>
                          <p className="text-xs text-slate-500 truncate max-w-[190px]">{rep.email}</p>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-1">
                        <Badge
                          variant="outline"
                          className={
                            rep.salesperson_type === 'external'
                              ? 'bg-amber-50 text-amber-700 border-amber-200 text-[10px]'
                              : 'bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px]'
                          }
                        >
                          {rep.role_label}
                        </Badge>
                        {rep.is_active_now ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                            Active Now
                          </span>
                        ) : rep.is_active_today ? (
                          <span className="text-[10px] text-emerald-700 font-medium bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            Active Today
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {/* Performance Metrics Grid */}
                    <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center my-3 bg-slate-50/60 rounded-lg">
                      <div className="p-1.5">
                        <div className="text-[10px] text-slate-500 uppercase font-medium">Activities</div>
                        <div className="text-base font-bold text-slate-900 mt-0.5">{rep.total_activities}</div>
                      </div>
                      <div className="p-1.5 border-x border-slate-200">
                        <div className="text-[10px] text-slate-500 uppercase font-medium">Calls / Talk</div>
                        <div className="text-base font-bold text-emerald-700 mt-0.5">{rep.calls_count}</div>
                        <div className="text-[10px] text-emerald-600 font-mono font-medium truncate" title={rep.talk_time_display}>
                          {rep.talk_time_display}
                        </div>
                      </div>
                      <div className="p-1.5">
                        <div className="text-[10px] text-slate-500 uppercase font-medium">Clients</div>
                        <div className="text-base font-bold text-indigo-700 mt-0.5">{rep.clients_count}</div>
                      </div>
                    </div>

                    {/* Secondary Metrics */}
                    <div className="flex items-center justify-between text-xs text-slate-600 mb-3 px-1">
                      <span className="flex items-center gap-1 text-[11px]">
                        <MessageSquare className="w-3.5 h-3.5 text-green-600" />
                        <b>{rep.whatsapp_count}</b> WA
                      </span>
                      <span className="flex items-center gap-1 text-[11px]">
                        <Mail className="w-3.5 h-3.5 text-blue-600" />
                        <b>{rep.emails_count}</b> Emails
                      </span>
                      <span className="flex items-center gap-1 text-[11px]">
                        <Calendar className="w-3.5 h-3.5 text-amber-600" />
                        <b>{rep.followups_count}</b> Follow-ups
                      </span>
                      <span className="flex items-center gap-1 text-[11px]">
                        <TrendingUp className="w-3.5 h-3.5 text-purple-600" />
                        <b>{rep.status_changes_count}</b> Moves
                      </span>
                    </div>

                    {/* Card Footer */}
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1.5 truncate">
                        <Clock className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                        {rep.is_active_now ? (
                          <span className="text-emerald-700 font-semibold truncate flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Active Now &bull; <span className="font-normal">{rep.last_active_relative}</span>
                          </span>
                        ) : rep.is_active_today ? (
                          <span className="text-emerald-700 font-medium truncate">
                            Active Today &bull; <b className="font-semibold">{rep.last_active_relative}</b>
                          </span>
                        ) : rep.last_active_relative && rep.last_active_relative !== '—' ? (
                          <span className="text-slate-500 truncate">
                            Active {rep.last_active_relative}
                          </span>
                        ) : (
                          <span className="text-slate-400">No recent activity</span>
                        )}
                      </div>
                      <span className="text-indigo-600 font-semibold group-hover:underline flex items-center gap-0.5 flex-shrink-0">
                        Client History &rarr;
                      </span>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── LEVEL 2: SELECTED SALESPERSON'S CLIENT-WISE ACTIVITY HISTORY ─── */}
      {selectedRep && (
        <div className="space-y-5">
          {/* Back Navigation & Switcher Header */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                {!isSalespersonOnly && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedRep(null);
                      setClientHistory(null);
                    }}
                    className="h-9 gap-1.5 text-xs text-slate-700 border-slate-300 hover:bg-slate-100"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    All Salespersons
                  </Button>
                )}

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-bold text-slate-900">{selectedRep.name}</h2>
                    <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 text-xs">
                      {selectedRep.role_label || 'Salesperson'}
                    </Badge>

                    {/* Real-time active status badge */}
                    {(selectedRep.is_active_now || clientHistory?.salesperson?.is_active_now) ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-2xs">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        Active Now ({selectedRep.last_active_relative || clientHistory?.salesperson?.last_active_relative || 'Just now'})
                      </span>
                    ) : (selectedRep.is_active_today || clientHistory?.salesperson?.is_active_today) ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <Clock className="w-3 h-3 text-emerald-600" />
                        Active Today &bull; {selectedRep.last_active_relative || clientHistory?.salesperson?.last_active_relative}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs text-slate-500 bg-slate-100 border border-slate-200">
                        Last active: {selectedRep.last_active_relative || clientHistory?.salesperson?.last_active_relative || selectedRep.last_active_display || '—'}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                    <span>{selectedRep.email}</span>
                    {(clientHistory?.salesperson?.last_active_raw || selectedRep.last_active_raw || clientHistory?.salesperson?.last_active_display || selectedRep.last_active_display) && (
                      <span className="text-slate-400">
                        &bull; Exact Last Active: <b className="text-slate-700 font-mono">
                          {formatDateTime(
                            clientHistory?.salesperson?.last_active_raw || selectedRep.last_active_raw,
                            clientHistory?.salesperson?.last_active_display || selectedRep.last_active_display
                          )}
                        </b>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Rep Dropdown Switcher (Admin only) */}
              {!isSalespersonOnly && salespersons.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">Switch Rep:</span>
                  <select
                    value={selectedRep.id}
                    onChange={(e) => {
                      const next = salespersons.find((s) => s.id === e.target.value);
                      if (next) setSelectedRep(next);
                    }}
                    className="h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    {salespersons.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.role_label})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Rep Summary Badges */}
            {clientHistory?.summary && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mt-4 pt-4 border-t border-slate-100 text-center">
                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-500 uppercase font-medium">Total Activities</div>
                  <div className="text-lg font-bold text-slate-900">{clientHistory.summary.total_activities}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{clientHistory.summary.total_clients_interacted} clients</div>
                </div>

                <div className="bg-emerald-50/60 p-2.5 rounded-lg border border-emerald-100">
                  <div className="text-[10px] text-emerald-800 uppercase font-medium">Total Calls</div>
                  <div className="text-lg font-bold text-emerald-700">{clientHistory.summary.total_calls}</div>
                  <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
                    {clientHistory.summary.calls_incoming || 0} In &bull; {clientHistory.summary.calls_outgoing || 0} Out
                  </div>
                  <div className="text-[11px] font-mono text-emerald-600 font-medium truncate mt-0.5" title={clientHistory.summary.total_talk_time_display}>
                    Talk: {clientHistory.summary.total_talk_time_display}
                  </div>
                </div>

                <div className="bg-green-50/60 p-2.5 rounded-lg border border-green-100">
                  <div className="text-[10px] text-green-800 uppercase font-medium">WhatsApp Messages</div>
                  <div className="text-lg font-bold text-green-700">{clientHistory.summary.total_whatsapp}</div>
                  <div className="text-[10px] text-green-700 font-medium mt-0.5">
                    {clientHistory.summary.whatsapp_sent || 0} Sent &bull; {clientHistory.summary.whatsapp_received || 0} Recv
                  </div>
                </div>

                <div className="bg-blue-50/60 p-2.5 rounded-lg border border-blue-100">
                  <div className="text-[10px] text-blue-800 uppercase font-medium">Total Emails</div>
                  <div className="text-lg font-bold text-blue-700">{clientHistory.summary.total_emails}</div>
                  <div className="text-[10px] text-blue-700 font-medium mt-0.5">
                    {clientHistory.summary.emails_sent || 0} Sent &bull; {clientHistory.summary.emails_received || 0} Recv
                  </div>
                </div>

                <div className="bg-amber-50/60 p-2.5 rounded-lg border border-amber-100">
                  <div className="text-[10px] text-amber-800 uppercase font-medium">Follow-ups</div>
                  <div className="text-lg font-bold text-amber-700">{clientHistory.summary.total_followups}</div>
                  <div className="text-[10px] text-amber-700 font-medium mt-0.5">Scheduled & Logged</div>
                </div>

                <div className="bg-purple-50/60 p-2.5 rounded-lg border border-purple-100">
                  <div className="text-[10px] text-purple-800 uppercase font-medium">Status Moves</div>
                  <div className="text-lg font-bold text-purple-700">{clientHistory.summary.total_status_changes}</div>
                  <div className="text-[10px] text-purple-700 font-medium mt-0.5">Pipeline Progress</div>
                </div>
              </div>
            )}

            {/* Today vs Yesterday Activity Comparison */}
            {clientHistory && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-100">
                {/* Today Card */}
                <Card className="p-4 bg-gradient-to-br from-indigo-50/60 to-white border-indigo-200/80 shadow-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-indigo-100">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-[10px] shadow-xs">
                        TODAY
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Today's Activity</h3>
                        <p className="text-[11px] text-slate-500 font-mono">
                          {clientHistory.today?.date_display || 'Today'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setDatePreset('today')}
                      className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                        datePreset === 'today'
                          ? 'bg-indigo-600 text-white shadow-xs'
                          : 'bg-white text-indigo-700 border border-indigo-200 hover:bg-indigo-50'
                      }`}
                    >
                      {datePreset === 'today' ? 'Filter Active' : 'Filter Today'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 text-center">
                    {/* Calls */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-emerald-800 uppercase font-semibold">
                        <PhoneCall className="w-3 h-3 text-emerald-600" /> Calls
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.today?.calls_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-emerald-700 font-medium">↓ {clientHistory.today?.calls_incoming || 0} in</span>
                        <span>•</span>
                        <span className="text-indigo-700 font-medium">↑ {clientHistory.today?.calls_outgoing || 0} out</span>
                      </div>
                      <div className="text-[10px] font-mono text-emerald-600 font-medium mt-0.5 truncate" title={clientHistory.today?.talk_time_display}>
                        {clientHistory.today?.talk_time_display || '0s'}
                      </div>
                    </div>

                    {/* Emails */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-blue-800 uppercase font-semibold">
                        <Mail className="w-3 h-3 text-blue-600" /> Emails
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.today?.emails_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-blue-700 font-medium">↑ {clientHistory.today?.emails_sent || 0} sent</span>
                        <span>•</span>
                        <span className="text-sky-700 font-medium">↓ {clientHistory.today?.emails_received || 0} recv</span>
                      </div>
                    </div>

                    {/* WhatsApp */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-green-800 uppercase font-semibold">
                        <MessageSquare className="w-3 h-3 text-green-600" /> WhatsApp
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.today?.whatsapp_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-green-700 font-medium">↑ {clientHistory.today?.whatsapp_sent || 0} sent</span>
                        <span>•</span>
                        <span className="text-teal-700 font-medium">↓ {clientHistory.today?.whatsapp_received || 0} recv</span>
                      </div>
                    </div>

                    {/* Follow-ups */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-amber-800 uppercase font-semibold">
                        <Calendar className="w-3 h-3 text-amber-600" /> Follow-ups
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.today?.followups_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        <b className="text-slate-800">{clientHistory.today?.clients_count || 0}</b> clients
                      </div>
                    </div>

                    {/* Stage Moves */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80 col-span-2 sm:col-span-1">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-purple-800 uppercase font-semibold">
                        <TrendingUp className="w-3 h-3 text-purple-600" /> Stage Moves
                      </div>
                      <div className="text-lg font-bold text-purple-700 mt-0.5">
                        {clientHistory.today?.status_changes_total || 0}
                      </div>
                      <div className="text-[10px] text-purple-600 font-medium mt-0.5">
                        pipeline moves
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Yesterday Card */}
                <Card className="p-4 bg-gradient-to-br from-slate-50/80 to-white border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-slate-700 text-white flex items-center justify-center font-bold text-[10px] shadow-xs">
                        Y'DAY
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Yesterday's Activity</h3>
                        <p className="text-[11px] text-slate-500 font-mono">
                          {clientHistory.yesterday?.date_display || 'Yesterday'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setDatePreset('yesterday')}
                      className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                        datePreset === 'yesterday'
                          ? 'bg-slate-800 text-white shadow-xs'
                          : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      {datePreset === 'yesterday' ? 'Filter Active' : 'Filter Yesterday'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 text-center">
                    {/* Calls */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-emerald-800 uppercase font-semibold">
                        <PhoneCall className="w-3 h-3 text-emerald-600" /> Calls
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.yesterday?.calls_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-emerald-700 font-medium">↓ {clientHistory.yesterday?.calls_incoming || 0} in</span>
                        <span>•</span>
                        <span className="text-indigo-700 font-medium">↑ {clientHistory.yesterday?.calls_outgoing || 0} out</span>
                      </div>
                      <div className="text-[10px] font-mono text-emerald-600 font-medium mt-0.5 truncate" title={clientHistory.yesterday?.talk_time_display}>
                        {clientHistory.yesterday?.talk_time_display || '0s'}
                      </div>
                    </div>

                    {/* Emails */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-blue-800 uppercase font-semibold">
                        <Mail className="w-3 h-3 text-blue-600" /> Emails
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.yesterday?.emails_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-blue-700 font-medium">↑ {clientHistory.yesterday?.emails_sent || 0} sent</span>
                        <span>•</span>
                        <span className="text-sky-700 font-medium">↓ {clientHistory.yesterday?.emails_received || 0} recv</span>
                      </div>
                    </div>

                    {/* WhatsApp */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-green-800 uppercase font-semibold">
                        <MessageSquare className="w-3 h-3 text-green-600" /> WhatsApp
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.yesterday?.whatsapp_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                        <span className="text-green-700 font-medium">↑ {clientHistory.yesterday?.whatsapp_sent || 0} sent</span>
                        <span>•</span>
                        <span className="text-teal-700 font-medium">↓ {clientHistory.yesterday?.whatsapp_received || 0} recv</span>
                      </div>
                    </div>

                    {/* Follow-ups */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-amber-800 uppercase font-semibold">
                        <Calendar className="w-3 h-3 text-amber-600" /> Follow-ups
                      </div>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {clientHistory.yesterday?.followups_total || 0}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        <b className="text-slate-800">{clientHistory.yesterday?.clients_count || 0}</b> clients
                      </div>
                    </div>

                    {/* Stage Moves */}
                    <div className="bg-white p-2 rounded-lg border border-slate-200/80 col-span-2 sm:col-span-1">
                      <div className="flex items-center justify-center gap-1 text-[10px] text-purple-800 uppercase font-semibold">
                        <TrendingUp className="w-3 h-3 text-purple-600" /> Stage Moves
                      </div>
                      <div className="text-lg font-bold text-purple-700 mt-0.5">
                        {clientHistory.yesterday?.status_changes_total || 0}
                      </div>
                      <div className="text-[10px] text-purple-600 font-medium mt-0.5">
                        pipeline moves
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </div>

          {/* Drilldown Filter Controls */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5 flex-1">
              {/* Search Client */}
              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                <Input
                  placeholder="Search client name or phone..."
                  value={clientSearch}
                  onChange={(e) => setClientSearch(e.target.value)}
                  className="pl-8 h-8 text-xs bg-slate-50 border-slate-200"
                />
              </div>

              {/* Client Dropdown */}
              <select
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="h-8 px-2.5 text-xs bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-medium"
              >
                <option value="all">All Clients ({clientHistory?.clients?.length || 0})</option>
                {(clientHistory?.clients || []).map((c) => (
                  <option key={c.client_id || c.client_name} value={c.client_id || c.client_name}>
                    {c.client_name} ({c.total_activities} activities)
                  </option>
                ))}
              </select>

              {/* Activity Type Dropdown */}
              <select
                value={activityTypeFilter}
                onChange={(e) => setActivityTypeFilter(e.target.value)}
                className="h-8 px-2.5 text-xs bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-medium"
              >
                <option value="all">All Activity Types</option>
                <option value="call">Calls Only (with duration)</option>
                <option value="whatsapp">WhatsApp Only</option>
                <option value="email">Emails Only</option>
                <option value="follow_up">Follow-ups</option>
                <option value="status_change">Stage & Status Moves</option>
                <option value="note">Notes Added</option>
                <option value="client_profile_view">Profile Views</option>
              </select>
            </div>

            {/* View Mode Toggle: Client Grouped vs Date-Wise vs Chronological Timeline */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs self-start lg:self-auto">
              <button
                onClick={() => setViewMode('client_grouped')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  viewMode === 'client_grouped'
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Client-Wise Activity
              </button>
              <button
                onClick={() => setViewMode('date_wise')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  viewMode === 'date_wise'
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Date-Wise History
              </button>
              <button
                onClick={() => setViewMode('timeline')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  viewMode === 'timeline'
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Timeline Stream
              </button>
            </div>
          </div>

          {/* ─── CLIENT GROUPED VIEW ─── */}
          {loadingHistory ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
              <p className="text-sm text-slate-600 font-medium">Loading client activity history...</p>
            </div>
          ) : viewMode === 'client_grouped' ? (
            filteredClients.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
                <Users className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                <h3 className="text-base font-semibold text-slate-900">No Client Activities in this Period</h3>
                <p className="text-sm text-slate-500 mt-1">Try selecting a different date range or activity filter.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredClients.map((client) => {
                  const clientKey = client.client_id || client.client_name;
                  const isExpanded = !!expandedClients[clientKey];

                  return (
                    <Card key={clientKey} className="bg-white border-slate-200 shadow-xs overflow-hidden">
                      {/* Client Card Header */}
                      <div
                        onClick={() => toggleClientExpand(clientKey)}
                        className="p-4 bg-slate-50/70 hover:bg-slate-50 border-b border-slate-200 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            className="w-7 h-7 rounded-md bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-900 shadow-2xs"
                          >
                            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? '' : '-rotate-90'}`} />
                          </button>

                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-bold text-slate-900">{client.client_name}</h3>
                              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-700 border-slate-300">
                                {client.stage || 'In Progress'}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                              {client.client_phone && client.client_phone !== '—' && (
                                <span className="flex items-center gap-1 font-mono">
                                  <Phone className="w-3 h-3 text-slate-400" />
                                  {client.client_phone}
                                </span>
                              )}
                              {client.client_email && client.client_email !== '—' && (
                                <span className="flex items-center gap-1 truncate max-w-[200px]">
                                  <Mail className="w-3 h-3 text-slate-400" />
                                  {client.client_email}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Client Activity Breakdown Pills */}
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 font-medium">
                            <PhoneCall className="w-3 h-3 mr-1" />
                            {client.calls_count} calls ({client.calls_incoming || 0} in / {client.calls_outgoing || 0} out) • {client.talk_time_display}
                          </Badge>

                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 font-medium">
                            <MessageSquare className="w-3 h-3 mr-1" />
                            {client.whatsapp_count} WA ({client.whatsapp_sent || 0} sent / {client.whatsapp_received || 0} recv)
                            {client.whatsapp_failed_count > 0 && (
                              <span className="text-rose-600 font-bold ml-1">({client.whatsapp_failed_count} failed)</span>
                            )}
                          </Badge>

                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 font-medium">
                            <Mail className="w-3 h-3 mr-1" />
                            {client.emails_count} Emails ({client.emails_sent || 0} sent / {client.emails_received || 0} recv)
                          </Badge>

                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 font-medium">
                            <Calendar className="w-3 h-3 mr-1" />
                            {client.followups_count} Follow-ups
                          </Badge>

                          {client.status_changes_count > 0 && (
                            <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 font-medium">
                              <TrendingUp className="w-3 h-3 mr-1" />
                              {client.status_changes_count} Stage moves
                            </Badge>
                          )}

                          {(client.client_views_count > 0 || client.active_time_seconds > 0 || client.is_actively_viewing) && (
                            <Badge variant="outline" className={`font-medium ${client.is_actively_viewing ? 'bg-emerald-50 text-emerald-800 border-emerald-300 animate-pulse font-bold' : 'bg-sky-50 text-sky-700 border-sky-200'}`}>
                              <Clock className="w-3 h-3 mr-1" />
                              {client.is_actively_viewing ? '● Actively Viewing Now' : `${client.client_views_count || 1} views • ${client.active_time_display || '0s'}`}
                            </Badge>
                          )}

                          <div className="text-[11px] text-slate-400 ml-2">
                            Total: <b className="text-slate-700">{client.total_activities}</b>
                          </div>
                        </div>
                      </div>

                      {/* Client Activities Timeline List */}
                      {isExpanded && (
                        <div className="p-4 bg-white divide-y divide-slate-100">
                          {client.activities.map((act) => {
                            const rawStatus = (act.message_status || act.metadata?.status || '').toLowerCase();
                            const isWaFailed = act.activity_type === 'whatsapp' && rawStatus === 'failed';
                            const isWaPending = act.activity_type === 'whatsapp' && (rawStatus === 'pending' || rawStatus === 'pending_confirmation');

                            const badge = isWaFailed
                              ? { label: 'WhatsApp (Failed)', bg: 'bg-rose-50 text-rose-700 border-rose-200', icon: AlertCircle }
                              : isWaPending
                              ? { label: 'WhatsApp (Pending)', bg: 'bg-amber-50 text-amber-700 border-amber-200', icon: Clock }
                              : (ACTIVITY_BADGES[act.activity_type] || {
                                  label: act.activity_type?.replace(/_/g, ' ') || 'Activity',
                                  bg: 'bg-slate-100 text-slate-700 border-slate-300',
                                  icon: Activity
                                });
                            const IconComponent = badge.icon;

                            return (
                              <div key={act.id} className="py-3.5 first:pt-1 last:pb-1 flex items-start justify-between gap-4">
                                <div className="flex items-start gap-3 min-w-0">
                                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border ${badge.bg}`}>
                                    <IconComponent className="w-4 h-4" />
                                  </div>

                                  <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <Badge variant="outline" className={`text-[10px] font-semibold ${badge.bg}`}>
                                        {badge.label}
                                      </Badge>
                                      <h4 className="text-xs font-bold text-slate-900">{act.title}</h4>
                                      {act.client_name && act.client_name !== 'Direct Activity / CRM' && (
                                        <Badge variant="secondary" className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                                          Client: {act.client_name}
                                        </Badge>
                                      )}
                                    </div>

                                    {act.details && (
                                      <p className="text-xs text-slate-600 mt-1 leading-relaxed bg-slate-50/70 p-2 rounded-md border border-slate-100">
                                        {act.details}
                                      </p>
                                    )}

                                    {/* Additional metadata tags */}
                                    <div className="flex flex-wrap items-center gap-1.5 mt-1.5 text-[10px] text-slate-500">
                                      {(act.activity_type === 'whatsapp' || act.message_status || act.metadata?.status) && (
                                        renderWhatsAppStatusBadge(act)
                                      )}
                                      {act.salesperson_name && (
                                        <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded border border-slate-200">
                                          Rep: <b>{act.salesperson_name}</b>
                                        </span>
                                      )}
                                      {act.metadata?.outcome && (
                                        <span className="px-1.5 py-0.5 bg-slate-100 rounded border border-slate-200">
                                          Outcome: <b>{act.metadata.outcome}</b>
                                        </span>
                                      )}
                                      {act.metadata?.direction && (
                                        <span className="px-1.5 py-0.5 bg-slate-100 rounded border border-slate-200 capitalize">
                                          Direction: <b>{act.metadata.direction}</b>
                                        </span>
                                      )}
                                      {act.metadata?.old_stage && act.metadata?.new_stage && (
                                        <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-200">
                                          {act.metadata.old_stage} &rarr; <b>{act.metadata.new_stage}</b>
                                        </span>
                                      )}
                                      {act.start_time && act.end_time && (
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-sky-50 text-sky-800 rounded border border-sky-200 font-semibold">
                                          <Clock className="w-3 h-3 text-sky-600" />
                                          Start: <b>{act.start_time}</b> &bull; End: <b>{act.end_time}</b>
                                        </span>
                                      )}
                                      {(act.session_state === 'active' || act.metadata?.session_state === 'active') && (
                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-800 rounded border border-emerald-300 font-bold animate-pulse">
                                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                          Actively Viewing Now (Started: {act.start_time || act.time})
                                        </span>
                                      )}
                                      {act.metadata?.switch_type === 'tab_focus' && (
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-200">
                                          Active Tab Switch
                                        </span>
                                      )}
                                      {(act.metadata?.is_all_leads_table || act.metadata?.source_tab === 'All Leads Table' || act.metadata?.source_view === 'table' || (act.title && act.title.toLowerCase().includes('all leads table'))) && (
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-200 font-semibold">
                                          All Leads Table
                                        </span>
                                      )}
                                      {(act.metadata?.is_leads_board || act.metadata?.source_tab === 'Leads Board' || act.metadata?.source_view === 'kanban' || (act.title && act.title.toLowerCase().includes('leads board'))) && (
                                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-50 text-amber-800 rounded border border-amber-200 font-semibold">
                                          Leads Board
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>

                                {/* Right: Duration, Relative Time, and Exact Timestamp */}
                                <div className="flex flex-col items-end text-right flex-shrink-0">
                                  {act.duration_display && act.duration_display !== '—' ? (
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                      <Clock className="w-3 h-3" />
                                      {act.duration_display}
                                    </span>
                                  ) : (
                                    <span className="text-[11px] text-slate-400 font-mono">—</span>
                                  )}

                                  <div className="flex items-center gap-1.5 mt-1.5">
                                    {act.relative_time && (
                                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                                        act.relative_time.includes('now') || act.relative_time.includes('m ago')
                                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                                      }`}>
                                        {act.relative_time}
                                      </span>
                                    )}
                                    <span className="text-[11px] font-medium text-slate-700">
                                      {formatDateOnly(act.timestamp, act.date)}
                                    </span>
                                  </div>
                                  <div className="text-[11px] text-slate-500 font-mono font-medium mt-0.5">
                                    {formatTimeOnly(act.timestamp, act.time || act.exact_timestamp_formatted)}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            )
          ) : viewMode === 'date_wise' ? (
            /* ─── DATE-WISE HISTORY VIEW ─── */
            (clientHistory?.date_wise_history || []).length === 0 ? (
              <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
                <CalendarDays className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                <h3 className="text-base font-semibold text-slate-900">No Date-Wise Records Found</h3>
                <p className="text-sm text-slate-500 mt-1">No activities logged in the selected date range.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {(clientHistory?.date_wise_history || []).map((dayRecord) => {
                  const isDayExpanded = expandedClients[dayRecord.date] || false;
                  return (
                    <Card key={dayRecord.date} className="p-4 bg-white border-slate-200 shadow-xs">
                      <div
                        onClick={() => toggleClientExpand(dayRecord.date)}
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs ${
                            dayRecord.is_today
                              ? 'bg-indigo-600 text-white shadow-xs'
                              : dayRecord.is_yesterday
                              ? 'bg-slate-700 text-white shadow-xs'
                              : 'bg-slate-100 text-slate-700'
                          }`}>
                            <Calendar className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-bold text-slate-900">
                                {dayRecord.date_display}
                              </h3>
                              <span className="text-xs text-slate-500 font-medium">({dayRecord.day_name})</span>
                              {dayRecord.is_today && (
                                <Badge className="bg-indigo-100 text-indigo-800 text-[10px] font-semibold">Today</Badge>
                              )}
                              {dayRecord.is_yesterday && (
                                <Badge className="bg-slate-100 text-slate-700 text-[10px] font-semibold">Yesterday</Badge>
                              )}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              {dayRecord.total_activities} activities across {dayRecord.clients_count} client(s)
                            </div>
                          </div>
                        </div>

                        {/* Day stats chips */}
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          {/* Calls */}
                          <div className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1.5 font-medium">
                            <PhoneCall className="w-3.5 h-3.5 text-emerald-600" />
                            <span><b>{dayRecord.calls_total}</b> Calls</span>
                            <span className="text-[10px] text-emerald-600">({dayRecord.calls_incoming} in / {dayRecord.calls_outgoing} out)</span>
                            {dayRecord.talk_time_seconds > 0 && (
                              <span className="font-mono text-[10px]">({dayRecord.talk_time_display})</span>
                            )}
                          </div>

                          {/* Emails */}
                          <div className="px-2.5 py-1 rounded bg-blue-50 text-blue-800 border border-blue-200 flex items-center gap-1.5 font-medium">
                            <Mail className="w-3.5 h-3.5 text-blue-600" />
                            <span><b>{dayRecord.emails_total}</b> Emails</span>
                            <span className="text-[10px] text-blue-600">({dayRecord.emails_sent} sent / {dayRecord.emails_received} recv)</span>
                          </div>

                          {/* WhatsApp */}
                          <div className="px-2.5 py-1 rounded bg-green-50 text-green-800 border border-green-200 flex items-center gap-1.5 font-medium">
                            <MessageSquare className="w-3.5 h-3.5 text-green-600" />
                            <span><b>{dayRecord.whatsapp_total}</b> WA</span>
                            <span className="text-[10px] text-green-600">({dayRecord.whatsapp_sent} sent / {dayRecord.whatsapp_received} recv)</span>
                          </div>

                          {/* Followups */}
                          {dayRecord.followups_total > 0 && (
                            <div className="px-2.5 py-1 rounded bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 font-medium">
                              <Calendar className="w-3.5 h-3.5 text-amber-600" />
                              <b>{dayRecord.followups_total}</b> Follow-ups
                            </div>
                          )}

                          {/* Stage Moves */}
                          {dayRecord.status_changes_total > 0 && (
                            <div className="px-2.5 py-1 rounded bg-purple-50 text-purple-800 border border-purple-200 flex items-center gap-1 font-medium">
                              <TrendingUp className="w-3.5 h-3.5 text-purple-600" />
                              <b>{dayRecord.status_changes_total}</b> Stage Moves
                            </div>
                          )}

                          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isDayExpanded ? 'rotate-180' : ''}`} />
                        </div>
                      </div>

                      {/* Expandable activities for this date */}
                      {isDayExpanded && (
                        <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                          <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                            Activities Logged on {dayRecord.date_display} ({dayRecord.activities?.length || 0})
                          </h4>
                          <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                            {(dayRecord.activities || []).map((act) => {
                              const badgeCfg = ACTIVITY_BADGES[act.activity_type] || { label: act.activity_type, bg: 'bg-slate-100 text-slate-700', icon: Activity };
                              const IconComp = badgeCfg.icon || Activity;
                              return (
                                <div key={act.id || Math.random()} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                                  <div className="flex items-start gap-2.5 flex-1 min-w-0">
                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${badgeCfg.bg}`}>
                                      <IconComp className="w-3 h-3" />
                                      {act.activity_type === 'call' && act.direction ? `${act.direction === 'incoming' ? 'Incoming' : 'Outgoing'} Call` :
                                       act.activity_type === 'email' && act.direction ? `Email ${act.direction === 'received' ? 'Received' : 'Sent'}` :
                                       act.activity_type === 'whatsapp' && act.direction ? `WA ${act.direction === 'received' ? 'Received' : 'Sent'}` :
                                       badgeCfg.label}
                                    </span>
                                    <div className="min-w-0 flex-1">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className="font-semibold text-slate-900 truncate">{act.title || act.details || 'Activity'}</span>
                                        {act.client_name && act.client_name !== 'Direct Activity / CRM' && (
                                          <Badge variant="secondary" className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                                            Client: {act.client_name}
                                          </Badge>
                                        )}
                                        {(act.metadata?.is_all_leads_table || act.metadata?.source_tab === 'All Leads Table' || act.metadata?.source_view === 'table' || (act.title && act.title.toLowerCase().includes('all leads table'))) && (
                                          <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200 font-medium">
                                            All Leads Table
                                          </Badge>
                                        )}
                                        {(act.metadata?.is_leads_board || act.metadata?.source_tab === 'Leads Board' || act.metadata?.source_view === 'kanban' || (act.title && act.title.toLowerCase().includes('leads board'))) && (
                                          <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-800 border-amber-200 font-semibold">
                                            Leads Board
                                          </Badge>
                                        )}
                                      </div>
                                      {act.details && act.details !== act.title && (
                                        <p className="text-slate-500 text-[11px] mt-0.5 truncate">{act.details}</p>
                                      )}
                                      {act.start_time && act.end_time && (
                                        <div className="text-[10px] text-sky-700 font-mono mt-0.5 font-medium flex items-center gap-1">
                                          <Clock className="w-2.5 h-2.5 text-sky-600" />
                                          <span>Start: {act.start_time} &bull; End: {act.end_time}</span>
                                        </div>
                                      )}
                                      {(act.session_state === 'active' || act.metadata?.session_state === 'active') && (
                                        <div className="text-[10px] text-emerald-700 font-bold mt-0.5 flex items-center gap-1 animate-pulse">
                                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                          <span>Actively Viewing Now (Started: {act.start_time || act.time})</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  <div className="text-right flex-shrink-0">
                                    <div className="text-slate-700 font-mono text-[11px] font-medium">{act.time}</div>
                                    {act.duration_display && act.duration_display !== '—' && (
                                      <div className="text-emerald-700 font-mono font-semibold text-[10px] mt-0.5">
                                        Duration: {act.duration_display}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            )
          ) : (
            /* ─── TIMELINE STREAM VIEW ─── */
            filteredTimeline.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
                <Clock className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                <h3 className="text-base font-semibold text-slate-900">No Timeline Activities Found</h3>
                <p className="text-sm text-slate-500 mt-1">Try adjusting your filters or date selection.</p>
              </div>
            ) : (
              <Card className="p-4 bg-white border-slate-200 divide-y divide-slate-100">
                {filteredTimeline.map((item) => {
                  const rawStatus = (item.message_status || item.metadata?.status || '').toLowerCase();
                  const isWaFailed = item.activity_type === 'whatsapp' && rawStatus === 'failed';
                  const isWaPending = item.activity_type === 'whatsapp' && (rawStatus === 'pending' || rawStatus === 'pending_confirmation');

                  const badge = isWaFailed
                    ? { label: 'WhatsApp (Failed)', bg: 'bg-rose-50 text-rose-700 border-rose-200', icon: AlertCircle }
                    : isWaPending
                    ? { label: 'WhatsApp (Pending)', bg: 'bg-amber-50 text-amber-700 border-amber-200', icon: Clock }
                    : (ACTIVITY_BADGES[item.activity_type] || {
                        label: item.activity_type?.replace(/_/g, ' ') || 'Activity',
                        bg: 'bg-slate-100 text-slate-700 border-slate-300',
                        icon: Activity
                      });
                  const IconComponent = badge.icon;

                  return (
                    <div key={item.id} className="py-3.5 first:pt-1 last:pb-1 flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border ${badge.bg}`}>
                          <IconComponent className="w-4 h-4" />
                        </div>

                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline" className={`text-[10px] font-semibold ${badge.bg}`}>
                              {badge.label}
                            </Badge>
                            {item.client_name && item.client_name !== 'Direct Activity / CRM' && (
                              <Badge variant="secondary" className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                                Client: {item.client_name}
                              </Badge>
                            )}
                            {(item.metadata?.is_all_leads_table || item.metadata?.source_tab === 'All Leads Table' || item.metadata?.source_view === 'table' || (item.title && item.title.toLowerCase().includes('all leads table'))) && (
                              <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200 font-medium">
                                All Leads Table
                              </Badge>
                            )}
                            {(item.metadata?.is_leads_board || item.metadata?.source_tab === 'Leads Board' || item.metadata?.source_view === 'kanban' || (item.title && item.title.toLowerCase().includes('leads board'))) && (
                              <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-800 border-amber-200 font-semibold">
                                Leads Board
                              </Badge>
                            )}
                            {item.salesperson_name && (
                              <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-600 border-slate-200">
                                Rep: {item.salesperson_name}
                              </Badge>
                            )}
                            {(item.activity_type === 'whatsapp' || item.message_status || item.metadata?.status) && (
                              renderWhatsAppStatusBadge(item)
                            )}
                            {(item.metadata?.previous_stage || item.metadata?.old_stage) && item.metadata?.new_stage && (
                              <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-700 border-purple-200 font-semibold">
                                {item.metadata.previous_stage || item.metadata.old_stage} &rarr; <b>{item.metadata.new_stage}</b>
                              </Badge>
                            )}
                          </div>

                          {item.details && (
                            <p className="text-xs text-slate-600 mt-1 bg-slate-50 p-2 rounded border border-slate-100 leading-relaxed">
                              {item.details}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Right: Duration, Relative Time, and Exact Timestamp */}
                      <div className="flex flex-col items-end text-right flex-shrink-0">
                        {item.duration_display && item.duration_display !== '—' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <Clock className="w-3 h-3" />
                            {item.duration_display}
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400 font-mono">—</span>
                        )}

                        <div className="flex items-center gap-1.5 mt-1.5">
                          {item.relative_time && (
                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                              item.relative_time.includes('now') || item.relative_time.includes('m ago')
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                            }`}>
                              {item.relative_time}
                            </span>
                          )}
                          <span className="text-[11px] font-medium text-slate-700">
                            {formatDateOnly(item.timestamp, item.date)}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono font-medium mt-0.5">
                          {formatTimeOnly(item.timestamp, item.time || item.exact_timestamp_formatted)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </Card>
            )
          )}
        </div>
      )}
    </div>
  );
}
