import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  TrendingUp, Target, Award, Users, BarChart3, IndianRupee,
  ArrowUpRight, ArrowDownRight, Globe, Package, Trophy, Percent,
  RefreshCw, Calendar
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PartnerPerformance = () => {
  const [perf, setPerf] = useState(null);
  const [targets, setTargets] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const [pRes, tRes, lRes] = await Promise.all([
        axios.get(`${API}/partner-analytics/performance`, getAuthHeader()),
        axios.get(`${API}/partner-analytics/targets`, getAuthHeader()),
        axios.get(`${API}/partner-analytics/leaderboard`, getAuthHeader()),
      ]);
      setPerf(pRes.data);
      setTargets(tRes.data);
      setLeaderboard(lRes.data || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;
  if (!perf || !targets) return null;

  const { sales, revenue, leads, monthly_trend, top_products, top_countries } = perf;
  const maxBarRevenue = Math.max(...(monthly_trend || []).map(m => m.revenue), 1);

  return (
    <div className="space-y-6" data-testid="partner-performance">
      {/* Monthly Targets */}
      <Card className="p-6 bg-white border-0 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Target className="h-5 w-5 text-[#f7620b]" /> Monthly Targets — {targets.current_month}
          </h3>
          <Badge className="bg-[#2a777a]/10 text-[#2a777a]"><Calendar className="h-3 w-3 mr-1" /> This Month</Badge>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Sales', current: targets.progress.sales, target: targets.targets.monthly_sales_target, pct: Math.min(targets.completion.sales, 100), color: '#2a777a', icon: TrendingUp },
            { label: 'Revenue', current: `₹${(targets.progress.revenue / 1000).toFixed(0)}K`, target: `₹${(targets.targets.monthly_revenue_target / 1000).toFixed(0)}K`, pct: Math.min(targets.completion.revenue, 100), color: '#f7620b', icon: IndianRupee },
            { label: 'Leads', current: targets.progress.leads, target: targets.targets.monthly_leads_target, pct: Math.min(targets.completion.leads, 100), color: '#6366f1', icon: Users },
            { label: 'Commission', current: `₹${(targets.progress.commission / 1000).toFixed(0)}K`, target: `₹${(targets.targets.monthly_commission_target / 1000).toFixed(0)}K`, pct: Math.min(targets.completion.commission, 100), color: '#10b981', icon: Award },
          ].map((item, idx) => (
            <div key={idx} className="bg-slate-50 rounded-xl p-4" data-testid={`target-${item.label.toLowerCase()}`}>
              <div className="flex items-center justify-between mb-2">
                <item.icon className="h-5 w-5" style={{ color: item.color }} />
                <span className="text-xs font-bold" style={{ color: item.color }}>{item.pct.toFixed(0)}%</span>
              </div>
              <Progress value={item.pct} className="h-2 mb-2" style={{ '--progress-color': item.color }} />
              <p className="text-lg font-bold text-slate-800">{item.current}</p>
              <p className="text-xs text-slate-500">Target: {item.target}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Revenue', value: `₹${(revenue.total_fee / 1000).toFixed(0)}K`, sub: `Collected: ₹${(revenue.total_received / 1000).toFixed(0)}K`, color: 'from-[#2a777a] to-[#236466]', icon: IndianRupee },
          { label: 'Approval Rate', value: `${sales.approval_rate}%`, sub: `${sales.approved}/${sales.total} sales`, color: 'from-emerald-500 to-emerald-600', icon: Percent },
          { label: 'Avg Deal Size', value: `₹${(revenue.avg_deal_size / 1000).toFixed(0)}K`, sub: `Collection: ${revenue.collection_rate}%`, color: 'from-leamss-teal-500 to-leamss-teal-600', icon: BarChart3 },
          { label: 'Lead Conversion', value: `${leads.approved}/${leads.total}`, sub: `${leads.rejected} rejected`, color: 'from-amber-500 to-amber-600', icon: TrendingUp },
        ].map((m, i) => (
          <Card key={i} className={`bg-gradient-to-br ${m.color} text-white p-5 border-0 shadow-lg`}>
            <div className="flex items-center justify-between mb-2">
              <m.icon className="h-5 w-5 text-white/80" />
            </div>
            <p className="text-2xl font-bold">{m.value}</p>
            <p className="text-xs text-white/70 mt-1">{m.label}</p>
            <p className="text-xs text-white/50 mt-0.5">{m.sub}</p>
          </Card>
        ))}
      </div>

      {/* Revenue Trend Chart */}
      {monthly_trend && monthly_trend.length > 0 && (
        <Card className="p-6 bg-white border-0 shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[#2a777a]" /> Revenue Trend (6 Months)
          </h3>
          <div className="flex items-end gap-3 h-48">
            {monthly_trend.map((m, idx) => {
              const height = maxBarRevenue > 0 ? (m.revenue / maxBarRevenue) * 100 : 0;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2" data-testid={`trend-${idx}`}>
                  <p className="text-xs font-bold text-slate-700">₹{(m.revenue / 1000).toFixed(0)}K</p>
                  <div className="w-full relative" style={{ height: '140px' }}>
                    <div className="absolute bottom-0 w-full rounded-t-lg bg-gradient-to-t from-[#2a777a] to-[#2a777a]/60 transition-all duration-700"
                      style={{ height: `${Math.max(height, 3)}%` }}>
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500 font-medium">{m.month.split(' ')[0]}</p>
                    <p className="text-xs text-slate-400">{m.sales} sales</p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Products */}
        <Card className="p-6 bg-white border-0 shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Package className="h-5 w-5 text-[#f7620b]" /> Top Products
          </h3>
          {top_products.length === 0 ? (
            <p className="text-slate-400 text-sm text-center py-4">No data yet</p>
          ) : (
            <div className="space-y-3">
              {top_products.filter(p => p.name !== 'Unknown').map((p, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-[#f7620b]/10 rounded-lg flex items-center justify-center text-[#f7620b] font-bold text-sm">{idx + 1}</div>
                  <div className="flex-1">
                    <p className="font-medium text-slate-800 text-sm">{p.name}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>{p.count} sales</span>
                      <span>₹{(p.revenue / 1000).toFixed(0)}K revenue</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Top Countries */}
        <Card className="p-6 bg-white border-0 shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Globe className="h-5 w-5 text-[#2a777a]" /> Top Countries
          </h3>
          {top_countries.length === 0 ? (
            <p className="text-slate-400 text-sm text-center py-4">No data yet</p>
          ) : (
            <div className="space-y-3">
              {top_countries.map((c, idx) => {
                const maxCount = Math.max(...top_countries.map(x => x.count), 1);
                return (
                  <div key={idx} className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-[#2a777a]/10 rounded-lg flex items-center justify-center text-[#2a777a] font-bold text-sm">{idx + 1}</div>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <p className="font-medium text-slate-800 text-sm">{c.name}</p>
                        <span className="text-xs text-slate-500">{c.count} leads</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-[#2a777a] rounded-full transition-all" style={{ width: `${(c.count / maxCount) * 100}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* Leaderboard */}
      {leaderboard.length > 0 && (
        <Card className="p-6 bg-white border-0 shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Trophy className="h-5 w-5 text-amber-500" /> Partner Leaderboard
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b">
                  <th className="p-3 text-left">Rank</th>
                  <th className="p-3 text-left">Partner</th>
                  <th className="p-3 text-right">Sales</th>
                  <th className="p-3 text-right">Revenue</th>
                  <th className="p-3 text-right">Commission</th>
                  <th className="p-3 text-right">Leads</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map(l => (
                  <tr key={l.rank} className={`border-b hover:bg-slate-50 ${l.is_you ? 'bg-[#2a777a]/5 font-semibold' : ''}`} data-testid={`leader-${l.rank}`}>
                    <td className="p-3">
                      {l.rank <= 3 ? (
                        <span className={`text-lg ${l.rank === 1 ? 'text-amber-500' : l.rank === 2 ? 'text-slate-400' : 'text-amber-700'}`}>
                          {l.rank === 1 ? '🥇' : l.rank === 2 ? '🥈' : '🥉'}
                        </span>
                      ) : <span className="text-slate-400">#{l.rank}</span>}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span>{l.partner_name || 'Partner'}</span>
                        {l.is_you && <Badge className="bg-[#2a777a] text-white text-xs">You</Badge>}
                      </div>
                    </td>
                    <td className="p-3 text-right">{l.total_sales}</td>
                    <td className="p-3 text-right">₹{(l.total_revenue / 1000).toFixed(0)}K</td>
                    <td className="p-3 text-right text-emerald-600 font-bold">₹{(l.total_commission / 1000).toFixed(0)}K</td>
                    <td className="p-3 text-right">{l.total_leads}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

export default PartnerPerformance;
