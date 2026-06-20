/**
 * Bonus C — Funnel Health Dashboard
 *
 * Aggregates the universal funnel: Lead → Payment → Review → Approved → Proposal → Accepted.
 * Shows horizontal bars, KPIs, top reject/decline reasons, avg time-in-stage.
 * Brand: leamss-teal (positive), leamss-orange (waiting), leamss-red (lost).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Activity, TrendingUp, DollarSign, Users, Clock, AlertTriangle, RefreshCw } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;
const tokenHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('token') || ''}` });

const STAGE_COLORS = {
  'leamss-teal': 'bg-leamss-teal',
  'leamss-orange': 'bg-leamss-orange',
  'leamss-red': 'bg-leamss-red',
};

export default function FunnelDashboard() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/funnel-metrics?days=${days}`, { headers: tokenHeaders() });
      if (r.ok) setData(await r.json());
    } finally { setLoading(false); }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (!data) {
    return (
      <div className="min-h-screen bg-leamss-bg_white p-6 flex items-center justify-center">
        <div className="text-slate-400 flex items-center gap-2">
          <RefreshCw className="h-5 w-5 animate-spin" /> Loading funnel...
        </div>
      </div>
    );
  }

  const maxCount = Math.max(...(data.funnel || []).map(s => s.count), 1);

  return (
    <div className="min-h-screen bg-leamss-bg_white p-6" data-testid="funnel-dashboard">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-leamss-teal flex items-center gap-2">
              <Activity className="h-7 w-7" /> Funnel Health Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Bonus C · Universal pipeline visibility · {data.kpis.total_leads} leads (last {days}d)
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
              <SelectTrigger className="w-32" data-testid="period-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="180">Last 180 days</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={load} data-testid="refresh-funnel-btn">
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-5 gap-3 mb-6" data-testid="kpi-cards">
          <Kpi icon={Users} label="Total Leads" value={data.kpis.total_leads} color="leamss-teal" />
          <Kpi icon={TrendingUp} label="Paid PAs" value={data.kpis.paid_pas} color="leamss-teal" />
          <Kpi icon={Activity} label="Approved" value={data.kpis.approved_reviews} color="leamss-teal" />
          <Kpi icon={TrendingUp} label="Sent Proposals" value={data.kpis.sent_proposals} color="leamss-orange" />
          <Kpi icon={DollarSign} label="Revenue (Accepted)"
               value={inrFmt(data.kpis.revenue_inr)} color="leamss-orange" big />
        </div>

        {/* Funnel Horizontal Bars */}
        <Card className="p-6 mb-6">
          <h2 className="text-lg font-bold text-leamss-teal mb-4">Conversion Funnel</h2>
          <div className="space-y-3" data-testid="funnel-stages">
            {data.funnel.map((stg, i) => {
              const widthPct = Math.max((stg.count / maxCount) * 100, 4);
              return (
                <div key={i} className="flex items-center gap-3" data-testid={`funnel-stage-${i}`}>
                  <div className="w-48 text-sm font-medium text-slate-700">{stg.stage}</div>
                  <div className="flex-1 h-9 bg-slate-100 rounded overflow-hidden relative">
                    <div
                      className={`h-full ${STAGE_COLORS[stg.color] || 'bg-leamss-teal'} transition-all duration-500 flex items-center pl-3`}
                      style={{ width: `${widthPct}%` }}
                    >
                      <span className="text-white text-xs font-bold">{stg.count}</span>
                    </div>
                  </div>
                  <div className="w-32 text-right text-xs">
                    <div className="text-slate-700">{stg.pct_of_leads}% of leads</div>
                    {stg.conversion_from_prev != null && (
                      <div className="text-leamss-orange">{stg.conversion_from_prev}% from prev</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Reject Reasons */}
          <Card className="p-5">
            <h3 className="font-bold text-leamss-red flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4" /> Top Reject Reasons (PA Reviews)
            </h3>
            {data.reject_reasons_top.length === 0 ? (
              <p className="text-sm text-slate-400">None in this period — great quality!</p>
            ) : (
              <ul className="space-y-2" data-testid="reject-reasons">
                {data.reject_reasons_top.map((r, i) => (
                  <li key={i} className="flex justify-between text-sm">
                    <span>{r.action || 'Unspecified'}</span>
                    <span className="font-bold text-leamss-red">{r.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Avg Time in Stage */}
          <Card className="p-5">
            <h3 className="font-bold text-leamss-orange flex items-center gap-2 mb-3">
              <Clock className="h-4 w-4" /> Avg Time in Stage
            </h3>
            <ul className="space-y-2" data-testid="time-in-stage">
              {Object.entries(data.avg_time_in_stage || {}).map(([key, val]) => (
                <li key={key} className="flex justify-between text-sm">
                  <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
                  <span className="font-bold text-leamss-orange">{val}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        {/* Raw breakdowns */}
        <Card className="p-5">
          <h3 className="font-bold text-leamss-teal mb-3">Stage Breakdowns</h3>
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div>
              <p className="uppercase text-slate-500 font-bold mb-2">By PA Stage</p>
              {Object.entries(data.by_pa_stage || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between py-1 border-b border-slate-100">
                  <span>{k}</span><span className="font-bold">{v}</span>
                </div>
              ))}
            </div>
            <div>
              <p className="uppercase text-slate-500 font-bold mb-2">By Review Status</p>
              {Object.entries(data.by_review_status || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between py-1 border-b border-slate-100">
                  <span>{k}</span><span className="font-bold">{v}</span>
                </div>
              ))}
            </div>
            <div>
              <p className="uppercase text-slate-500 font-bold mb-2">By Proposal Status</p>
              {Object.entries(data.by_proposal_status || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between py-1 border-b border-slate-100">
                  <span>{k}</span><span className="font-bold">{v}</span>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[10px] text-slate-400 mt-4 text-right">
            Computed at {(data.computed_at || '').slice(11, 16)} UTC · Period {data.period_days}d
          </p>
        </Card>
      </div>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, color = 'leamss-teal', big = false }) {
  return (
    <Card className={`p-4 border-l-4 border-${color}`} data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-center gap-2 text-xs uppercase text-slate-500 font-bold">
        <Icon className={`h-3 w-3 text-${color}`} /> {label}
      </div>
      <p className={`mt-1 font-bold text-${color} ${big ? 'text-lg' : 'text-2xl'}`}>
        {value}
      </p>
    </Card>
  );
}
