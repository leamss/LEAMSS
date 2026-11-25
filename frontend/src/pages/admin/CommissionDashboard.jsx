/**
 * Sales Commission & Incentive Management Dashboard (Admin).
 * Tabs:
 *  1. Commission Entries & Payouts (Leaderboard + Entries Table + Approve/Pay/Reverse)
 *  2. Salesperson Rates & Rules (All salespersons, mode/rate configuration, earnings stats)
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  ArrowLeft, Trophy, CheckCircle, IndianRupee, Crown, TrendingUp, Trash2,
  Users, Settings, Clock, Search, ShieldCheck, AlertCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const currentPeriod = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const STATUS_COLOR = {
  pending: 'bg-amber-100 text-amber-700 border-amber-300',
  approved: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300',
  paid: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  reversed: 'bg-rose-100 text-rose-700 border-rose-300',
};

export default function CommissionDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('salespersons'); // 'salespersons' | 'entries'
  const [period, setPeriod] = useState(currentPeriod());
  
  // Entries & Leaderboard
  const [entries, setEntries] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [stats, setStats] = useState({ total_revenue: 0, total_commission: 0 });
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  // Salespersons list & config
  const [salespersons, setSalespersons] = useState([]);
  const [loadingSalespersons, setLoadingSalespersons] = useState(true);
  const [repSearch, setRepSearch] = useState('');
  
  // Rate config modal
  const [selectedRep, setSelectedRep] = useState(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configDraft, setConfigDraft] = useState({
    commission_mode: 'slab',
    commission_rate: 5,
    is_commission_active: true,
    reason: '',
  });
  const [savingConfig, setSavingConfig] = useState(false);

  // History modal
  const [historyModalRep, setHistoryModalRep] = useState(null);

  // Pay reference modal
  const [payModalEntry, setPayModalEntry] = useState(null);
  const [payReference, setPayReference] = useState('');

  const getHeaders = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  });

  const loadEntriesData = async () => {
    setLoadingEntries(true);
    try {
      const [eRes, lRes] = await Promise.all([
        axios.get(`${API}/sales-commission/all?period=${period}${statusFilter ? `&status=${statusFilter}` : ''}`, getHeaders()),
        axios.get(`${API}/sales-commission/leaderboard?period=${period}`, getHeaders()),
      ]);
      setEntries(eRes.data.entries || []);
      setLeaderboard(lRes.data.leaderboard || []);
      setStats({ total_revenue: eRes.data.total_revenue || 0, total_commission: eRes.data.total_commission || 0 });
    } catch (e) {
      toast.error('Failed to load commission entries');
    } finally {
      setLoadingEntries(false);
    }
  };

  const loadSalespersonsData = async () => {
    setLoadingSalespersons(true);
    try {
      const res = await axios.get(`${API}/sales-commission/salespersons?period=${period}`, getHeaders());
      setSalespersons(res.data.salespersons || []);
    } catch (e) {
      toast.error('Failed to load salespersons list');
    } finally {
      setLoadingSalespersons(false);
    }
  };

  useEffect(() => {
    loadSalespersonsData();
    loadEntriesData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  useEffect(() => {
    loadEntriesData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const handleEntryAction = async (entryId, type, payload = {}) => {
    try {
      await axios.post(`${API}/sales-commission/entries/${entryId}/${type}`, payload, getHeaders());
      toast.success(`Commission ${type} successful`);
      loadEntriesData();
      loadSalespersonsData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || `Failed to ${type}`);
    }
  };

  const openConfigModal = (rep) => {
    setSelectedRep(rep);
    setConfigDraft({
      commission_mode: rep.commission_mode || 'slab',
      commission_rate: rep.commission_rate != null ? rep.commission_rate : 5,
      is_commission_active: rep.is_commission_active !== false,
      reason: '',
    });
    setConfigModalOpen(true);
  };

  const saveRepConfig = async () => {
    if (!selectedRep) return;
    setSavingConfig(true);
    try {
      await axios.put(
        `${API}/sales-commission/salespersons/${selectedRep.id}/config`,
        {
          commission_mode: configDraft.commission_mode,
          commission_rate: parseFloat(configDraft.commission_rate) || 0,
          is_commission_active: configDraft.is_commission_active,
          reason: configDraft.reason || 'Admin commission rate update',
        },
        getHeaders()
      );
      toast.success(`Commission configuration updated for ${selectedRep.name}`);
      setConfigModalOpen(false);
      loadSalespersonsData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to update commission settings');
    } finally {
      setSavingConfig(false);
    }
  };

  const filteredSalespersons = salespersons.filter((sp) => {
    const q = repSearch.toLowerCase();
    return (
      (sp.name && sp.name.toLowerCase().includes(q)) ||
      (sp.email && sp.email.toLowerCase().includes(q)) ||
      (sp.role && sp.role.toLowerCase().includes(q))
    );
  });

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="commission-dashboard-page">
      <div className="max-w-7xl mx-auto">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/admin')}
              className="p-2 rounded-lg hover:bg-slate-200 transition"
              data-testid="back-to-admin"
            >
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <IndianRupee className="h-7 w-7 text-emerald-600" />
                Sales Commission & Incentives
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Admin incentive management, individual rep rates, eligible payout tracking and approval.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="month"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-44 bg-white"
              data-testid="period-picker"
            />
            <Button
              variant="outline"
              onClick={() => navigate('/admin/sales/commission-slabs')}
              data-testid="manage-slabs-btn"
              className="bg-white"
            >
              <Trophy className="h-4 w-4 mr-1.5 text-amber-500" />
              Manage Slabs
            </Button>
          </div>
        </div>

        {/* Global Period KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-4 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-300">
            <p className="text-xs font-bold uppercase text-emerald-800">Total Period Revenue</p>
            <p className="text-2xl font-extrabold text-emerald-900 mt-1" data-testid="total-revenue">
              {formatINR(stats.total_revenue)}
            </p>
            <p className="text-[11px] text-emerald-700 mt-1">Period: {period}</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-cyan-50 to-cyan-100 border-cyan-300">
            <p className="text-xs font-bold uppercase text-cyan-800">Total Commission Earned</p>
            <p className="text-2xl font-extrabold text-cyan-900 mt-1" data-testid="total-commission">
              {formatINR(stats.total_commission)}
            </p>
            <p className="text-[11px] text-cyan-700 mt-1">{entries.length} eligible deal entries</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-300">
            <p className="text-xs font-bold uppercase text-amber-800">Avg Commission Rate</p>
            <p className="text-2xl font-extrabold text-amber-900 mt-1">
              {stats.total_revenue > 0 ? `${((stats.total_commission / stats.total_revenue) * 100).toFixed(1)}%` : '—'}
            </p>
            <p className="text-[11px] text-amber-700 mt-1">Team-wide effective</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 border-slate-300">
            <p className="text-xs font-bold uppercase text-slate-800">Total Salespersons</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1" data-testid="salesperson-count">
              {salespersons.length}
            </p>
            <p className="text-[11px] text-slate-600 mt-1">Active in CRM</p>
          </Card>
        </div>

        {/* Tab Controls */}
        <div className="flex gap-2 border-b border-slate-200 mb-6 pb-2">
          <button
            onClick={() => setActiveTab('salespersons')}
            className={`flex items-center gap-2 px-4 py-2 font-semibold text-sm rounded-lg transition ${
              activeTab === 'salespersons'
                ? 'bg-[#2a777a] text-white shadow'
                : 'text-slate-600 hover:bg-slate-200'
            }`}
            data-testid="tab-salespersons"
          >
            <Users className="h-4 w-4" />
            Salesperson Rates & Rules ({salespersons.length})
          </button>
          <button
            onClick={() => setActiveTab('entries')}
            className={`flex items-center gap-2 px-4 py-2 font-semibold text-sm rounded-lg transition ${
              activeTab === 'entries'
                ? 'bg-[#2a777a] text-white shadow'
                : 'text-slate-600 hover:bg-slate-200'
            }`}
            data-testid="tab-entries"
          >
            <Clock className="h-4 w-4" />
            Commission Entries & Payouts ({entries.length})
          </button>
        </div>

        {/* TAB 1: SALESPERSON RATES & RULES */}
        {activeTab === 'salespersons' && (
          <div className="space-y-6" data-testid="salespersons-view">
            <Card className="p-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-[#2a777a]" />
                    Salesperson Incentive Configuration & Performance
                  </h2>
                  <p className="text-xs text-slate-500">
                    All salespersons automatically sync here upon creation. Configure custom flat rates or standard revenue slabs.
                  </p>
                </div>
                <div className="w-full sm:w-64">
                  <div className="relative">
                    <Search className="h-4 w-4 text-slate-400 absolute left-3 top-3" />
                    <Input
                      placeholder="Search salesperson..."
                      value={repSearch}
                      onChange={(e) => setRepSearch(e.target.value)}
                      className="pl-9 text-xs"
                      data-testid="rep-search-input"
                    />
                  </div>
                </div>
              </div>

              {loadingSalespersons ? (
                <p className="text-sm text-slate-500 text-center py-8">Loading salespersons...</p>
              ) : filteredSalespersons.length === 0 ? (
                <p className="text-sm text-slate-400 italic text-center py-8">No salespersons found matching search</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                        <th className="text-left py-3 px-3">Salesperson</th>
                        <th className="text-left py-3 px-3">Role</th>
                        <th className="text-center py-3 px-3">Commission Mode</th>
                        <th className="text-center py-3 px-3">Effective Rate</th>
                        <th className="text-center py-3 px-3">Status</th>
                        <th className="text-right py-3 px-3">Period Revenue</th>
                        <th className="text-right py-3 px-3">Total Earned</th>
                        <th className="text-right py-3 px-3">Pending</th>
                        <th className="text-right py-3 px-3">Paid</th>
                        <th className="text-center py-3 px-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSalespersons.map((sp) => (
                        <tr
                          key={sp.id}
                          className="border-b last:border-b-0 hover:bg-slate-50/70 transition"
                          data-testid={`salesperson-row-${sp.id}`}
                        >
                          <td className="py-3 px-3">
                            <p className="font-semibold text-slate-900">{sp.name}</p>
                            <p className="text-[11px] text-slate-500">{sp.email}</p>
                          </td>
                          <td className="py-3 px-3">
                            <Badge variant="outline" className="text-[10px] capitalize bg-slate-100 text-slate-700">
                              {(sp.role || sp.rbac_role || '').replace('_', ' ')}
                            </Badge>
                          </td>
                          <td className="py-3 px-3 text-center">
                            {sp.commission_mode === 'flat' ? (
                              <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px]">
                                Custom Flat ({sp.commission_rate}%)
                              </Badge>
                            ) : (
                              <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-[10px]">
                                Tiered Slabs ({sp.current_slab?.name || 'Bronze'})
                              </Badge>
                            )}
                          </td>
                          <td className="py-3 px-3 text-center font-bold text-slate-800">
                            {sp.effective_rate_pct}%
                          </td>
                          <td className="py-3 px-3 text-center">
                            {sp.is_commission_active ? (
                              <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px]">
                                Active
                              </Badge>
                            ) : (
                              <Badge className="bg-slate-200 text-slate-700 text-[10px]">
                                Inactive
                              </Badge>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right font-medium text-slate-700">
                            {formatINR(sp.total_revenue)}
                          </td>
                          <td className="py-3 px-3 text-right font-bold text-emerald-700">
                            {formatINR(sp.total_commission)}
                          </td>
                          <td className="py-3 px-3 text-right font-medium text-amber-700">
                            {formatINR(sp.pending)}
                          </td>
                          <td className="py-3 px-3 text-right font-medium text-emerald-600">
                            {formatINR(sp.paid)}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <div className="flex items-center justify-center gap-1.5">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs px-2.5 bg-white hover:bg-slate-100 text-slate-700 border-slate-300"
                                onClick={() => openConfigModal(sp)}
                                data-testid={`edit-rate-${sp.id}`}
                              >
                                <Settings className="h-3 w-3 mr-1 text-[#2a777a]" />
                                Configure
                              </Button>
                              {sp.commission_rate_history && sp.commission_rate_history.length > 0 && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 text-xs px-2 text-slate-500 hover:text-slate-800"
                                  title="View rate change history"
                                  onClick={() => setHistoryModalRep(sp)}
                                  data-testid={`history-${sp.id}`}
                                >
                                  <Clock className="h-3.5 w-3.5" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* TAB 2: COMMISSION ENTRIES & PAYOUTS */}
        {activeTab === 'entries' && (
          <div className="space-y-6" data-testid="entries-view">
            {/* Top Performers Leaderboard */}
            <Card className="p-5" data-testid="leaderboard-card">
              <h2 className="font-bold flex items-center gap-2 mb-4 text-slate-800">
                <Crown className="h-5 w-5 text-amber-500" />
                Top Performers Leaderboard ({period})
              </h2>
              {leaderboard.length === 0 ? (
                <p className="text-sm text-slate-400 italic text-center py-4">No deals recorded for {period}</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {leaderboard.slice(0, 6).map((l, i) => (
                    <div
                      key={l.user_id}
                      className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200"
                      data-testid={`lb-row-${i}`}
                    >
                      <span
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                          i === 0
                            ? 'bg-amber-500 text-white'
                            : i === 1
                            ? 'bg-slate-400 text-white'
                            : i === 2
                            ? 'bg-orange-500 text-white'
                            : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm truncate text-slate-900">{l.user_name || l.user_email}</p>
                        <p className="text-[11px] text-slate-500">{l.deal_count} deal{l.deal_count !== 1 ? 's' : ''}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-bold text-slate-700">{formatINR(l.total_revenue)}</p>
                        <p className="text-xs text-emerald-600 font-semibold">
                          <TrendingUp className="h-3 w-3 inline mr-0.5" />
                          {formatINR(l.total_commission)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Entries Table */}
            <Card className="p-5" data-testid="entries-card">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
                <div>
                  <h2 className="font-bold text-slate-800">Eligible Commission Entries</h2>
                  <p className="text-xs text-slate-500">
                    Breakdown of deals and payments triggering commissions, with approval and payout controls.
                  </p>
                </div>
                <div className="flex gap-1.5 text-xs">
                  {['', 'pending', 'approved', 'paid', 'reversed'].map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-1 rounded transition text-xs font-medium ${
                        statusFilter === s
                          ? 'bg-[#2a777a] text-white shadow-sm'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                      data-testid={`filter-${s || 'all'}`}
                    >
                      {s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'}
                    </button>
                  ))}
                </div>
              </div>

              {loadingEntries ? (
                <p className="text-sm text-slate-500 text-center py-6">Loading entries…</p>
              ) : entries.length === 0 ? (
                <p className="text-sm text-slate-400 italic text-center py-6">No commission entries found for {period}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-slate-50 text-[10px] uppercase text-slate-500 tracking-wider">
                        <th className="text-left py-2.5 px-2">Salesperson</th>
                        <th className="text-left py-2.5 px-2">Source / Deal</th>
                        <th className="text-right py-2.5 px-2">Eligible Revenue</th>
                        <th className="text-center py-2.5 px-2">Rule / Rate</th>
                        <th className="text-right py-2.5 px-2">Commission</th>
                        <th className="text-center py-2.5 px-2">Status</th>
                        <th className="text-right py-2.5 px-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map((e) => (
                        <tr
                          key={e.id}
                          className="border-b last:border-b-0 hover:bg-slate-50/70 transition"
                          data-testid={`entry-${e.id}`}
                        >
                          <td className="py-2.5 px-2">
                            <p className="font-semibold text-slate-900">{e.user_name}</p>
                            <p className="text-[10px] text-slate-500">{e.user_email}</p>
                          </td>
                          <td className="py-2.5 px-2">
                            <p className="font-medium text-xs text-slate-800">{e.client_name || 'Client Payment'}</p>
                            <p className="text-[10px] text-slate-500">
                              {e.pa_number || e.receipt_number || e.source_id || 'Direct'} ({e.source_type || 'pa'})
                            </p>
                          </td>
                          <td className="py-2.5 px-2 text-right font-medium text-slate-700">
                            {formatINR(e.revenue)}
                          </td>
                          <td className="py-2.5 px-2 text-center">
                            <Badge className="bg-amber-100 text-amber-800 text-[10px] border border-amber-300">
                              {e.slab_name || 'Tier'} ({e.rate_pct}%)
                            </Badge>
                          </td>
                          <td className="py-2.5 px-2 text-right font-bold text-emerald-700">
                            {formatINR(e.commission_amount)}
                          </td>
                          <td className="py-2.5 px-2 text-center">
                            <Badge className={`${STATUS_COLOR[e.status] || ''} text-[10px] capitalize border`}>
                              {e.status}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-2 text-right">
                            <div className="flex gap-1 justify-end items-center">
                              {e.status === 'pending' && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-[10px] px-2.5 border-slate-300 hover:bg-slate-100"
                                  onClick={() => handleEntryAction(e.id, 'approve')}
                                  data-testid={`approve-${e.id}`}
                                >
                                  Approve
                                </Button>
                              )}
                              {(e.status === 'pending' || e.status === 'approved') && (
                                <Button
                                  size="sm"
                                  className="h-6 text-[10px] px-2.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                                  onClick={() => {
                                    setPayModalEntry(e);
                                    setPayReference('');
                                  }}
                                  data-testid={`pay-${e.id}`}
                                >
                                  <CheckCircle className="h-3 w-3 mr-0.5" />
                                  Mark Paid
                                </Button>
                              )}
                              {e.status !== 'reversed' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 text-rose-600 px-1.5 hover:bg-rose-50"
                                  title="Reverse Commission"
                                  onClick={() => {
                                    if (window.confirm('Reverse this commission entry? This will write a cancellation audit record.')) {
                                      handleEntryAction(e.id, 'reverse');
                                    }
                                  }}
                                  data-testid={`reverse-${e.id}`}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* DIALOG: CONFIGURE SALESPERSON COMMISSION */}
        <Dialog open={configModalOpen} onOpenChange={setConfigModalOpen}>
          <DialogContent className="max-w-md" data-testid="salesperson-config-modal">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-[#2a777a]" />
                Configure Commission: {selectedRep?.name}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="p-3 bg-slate-50 rounded-lg text-xs space-y-1 border border-slate-200">
                <p><strong>Email:</strong> {selectedRep?.email}</p>
                <p><strong>Current Role:</strong> {selectedRep?.role || selectedRep?.rbac_role}</p>
              </div>

              <div>
                <Label className="text-xs font-semibold">Commission Calculation Mode *</Label>
                <Select
                  value={configDraft.commission_mode}
                  onValueChange={(val) => setConfigDraft({ ...configDraft, commission_mode: val })}
                >
                  <SelectTrigger data-testid="commission-mode-select" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="slab">Tiered Revenue Slabs (Bronze, Silver, Gold)</SelectItem>
                    <SelectItem value="flat">Individual Flat Rate (%)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-slate-500 mt-1">
                  {configDraft.commission_mode === 'slab'
                    ? 'Salesperson progresses through company-wide revenue slabs.'
                    : 'Salesperson receives a fixed custom percentage on all verified deals.'}
                </p>
              </div>

              {configDraft.commission_mode === 'flat' && (
                <div>
                  <Label className="text-xs font-semibold">Custom Commission Rate (%) *</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={configDraft.commission_rate}
                    onChange={(e) => setConfigDraft({ ...configDraft, commission_rate: e.target.value })}
                    className="mt-1"
                    data-testid="flat-rate-input"
                  />
                </div>
              )}

              <div>
                <Label className="text-xs font-semibold">Commission Eligibility</Label>
                <Select
                  value={configDraft.is_commission_active ? 'active' : 'inactive'}
                  onValueChange={(val) => setConfigDraft({ ...configDraft, is_commission_active: val === 'active' })}
                >
                  <SelectTrigger data-testid="active-status-select" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active (Eligible for Commission)</SelectItem>
                    <SelectItem value="inactive">Disabled (No Commission Calculated)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-semibold">Audit Reason / Rationale</Label>
                <Input
                  placeholder="e.g. Senior promotion incentive rate"
                  value={configDraft.reason}
                  onChange={(e) => setConfigDraft({ ...configDraft, reason: e.target.value })}
                  className="mt-1 text-xs"
                  data-testid="config-reason-input"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setConfigModalOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={saveRepConfig}
                disabled={savingConfig}
                className="bg-[#2a777a] hover:bg-[#236466] text-white"
                data-testid="save-config-btn"
              >
                {savingConfig ? 'Saving...' : 'Save Configuration'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* DIALOG: VIEW COMMISSION RATE CHANGE HISTORY */}
        <Dialog open={!!historyModalRep} onOpenChange={() => setHistoryModalRep(null)}>
          <DialogContent className="max-w-lg" data-testid="rate-history-modal">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-amber-500" />
                Rate History: {historyModalRep?.name}
              </DialogTitle>
            </DialogHeader>

            <div className="py-2 space-y-2 max-h-80 overflow-y-auto">
              {!historyModalRep?.commission_rate_history || historyModalRep.commission_rate_history.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No historical changes logged yet.</p>
              ) : (
                historyModalRep.commission_rate_history.map((h, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-slate-800">
                        {h.new_mode === 'flat' ? `Flat ${h.new_rate}%` : (h.new_rate != null ? `${h.new_rate}%` : 'Tiered Slabs')}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(h.changed_at).toLocaleString()}
                      </span>
                    </div>
                    {h.reason && <p className="text-slate-600 italic">"{h.reason}"</p>}
                    <p className="text-[10px] text-slate-400">Changed by Admin: {h.changed_by}</p>
                  </div>
                ))
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setHistoryModalRep(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* DIALOG: RECORD PAYOUT TRANSACTION REFERENCE */}
        <Dialog open={!!payModalEntry} onOpenChange={() => setPayModalEntry(null)}>
          <DialogContent className="max-w-md" data-testid="payout-modal">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-emerald-700">
                <CheckCircle className="h-5 w-5" />
                Confirm Commission Payout
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-3 py-2 text-sm">
              <p>
                Marking commission payout of <strong>{formatINR(payModalEntry?.commission_amount)}</strong> for{' '}
                <strong>{payModalEntry?.user_name}</strong> as Paid.
              </p>
              <div>
                <Label className="text-xs font-semibold">Payment / Transfer Reference</Label>
                <Input
                  placeholder="e.g. NEFT-98421048 or UPI-REF-4821"
                  value={payReference}
                  onChange={(e) => setPayReference(e.target.value)}
                  className="mt-1"
                  data-testid="pay-ref-input"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setPayModalEntry(null)}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  const entry = payModalEntry;
                  setPayModalEntry(null);
                  handleEntryAction(entry.id, 'mark-paid', { payment_reference: payReference });
                }}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="confirm-pay-btn"
              >
                Confirm Payout
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
