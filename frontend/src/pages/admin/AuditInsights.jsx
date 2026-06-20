/**
 * Audit Insights Dashboard — Phase 6.9b
 *
 * Route: /admin/audit-insights
 * Admin-only. Standalone page surfacing aggregate insights from share-audit log.
 *
 * Sections:
 *   • Top stats (total events / unique tokens / IPs / anomalies summary)
 *   • Daily trend chart (recharts — events/day stacked by type)
 *   • Anomaly Alerts Feed (Slack-independent internal alerts with acknowledge)
 *   • Top-flagging IPs table
 *   • Top-10 Anomaly Tokens with severity badges
 *   • Share Type breakdown
 *   • Export "Quarterly Compliance Report" PDF
 */
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Activity, AlertTriangle, BarChart3, Download, Eye, Flame, Globe2,
  Loader2, RefreshCw, Shield, ShieldAlert, ShieldCheck,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SHARE_TYPE_COLORS = {
  sales_report: '#6366f1',
  magic_portal: '#10b981',
  public_pa_fee: '#f59e0b',
  '?': '#94a3b8',
};

export default function AuditInsights() {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  const auth = useMemo(() => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }), []);

  const load = async () => {
    setLoading(true);
    try {
      const [overview, alertFeed] = await Promise.all([
        axios.get(`${API}/audit-insights/overview?days=${days}`, auth),
        axios.get(`${API}/share-links/anomaly-alerts?limit=20`, auth),
      ]);
      setData(overview.data);
      setAlerts(alertFeed.data.items || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load insights');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  const acknowledgeAlert = async (id) => {
    try {
      await axios.post(`${API}/share-links/anomaly-alerts/${id}/acknowledge`, {}, auth);
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
      toast.success('Alert acknowledged');
    } catch {
      toast.error('Acknowledge failed');
    }
  };

  const downloadCompliancePdf = async () => {
    setPdfDownloading(true);
    try {
      const r = await axios.get(`${API}/audit-insights/compliance-report.pdf?days=90`, { ...auth, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `leamss_compliance_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Compliance report downloaded');
    } catch {
      toast.error('PDF generation failed');
    } finally {
      setPdfDownloading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-leamss-teal-600" />
      </div>
    );
  }

  const shareTypePie = Object.entries(data.by_share_type).map(([k, v]) => ({ name: k, value: v }));
  const totalAnomalies = data.anomaly_summary.high + data.anomaly_summary.medium + data.anomaly_summary.low;
  const unackedAlerts = alerts.filter(a => !a.acknowledged);

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="audit-insights-page">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="h-7 w-7 text-leamss-teal-600" />Audit Insights Dashboard
            </h1>
            <p className="text-sm text-slate-500">Share-link audit log analytics · SOC-2 ready</p>
          </div>
          <div className="flex gap-2">
            <select
              value={days}
              onChange={e => setDays(parseInt(e.target.value, 10))}
              className="border border-slate-200 rounded px-3 py-1.5 text-xs bg-white"
              data-testid="ai-window-select"
            >
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
            </select>
            <Button variant="outline" size="sm" onClick={load} className="h-8" data-testid="ai-refresh">
              <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
            </Button>
            <Button size="sm" className="h-8 bg-leamss-teal-600 hover:bg-leamss-teal-700" onClick={downloadCompliancePdf} disabled={pdfDownloading} data-testid="ai-pdf">
              {pdfDownloading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Download className="h-3.5 w-3.5 mr-1" />}
              Export 90-Day Compliance PDF
            </Button>
          </div>
        </div>

        {/* Top Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="ai-stat-cards">
          <StatCard icon={Activity} label="Total Events" value={data.total_events} color="indigo" />
          <StatCard icon={Globe2} label="Unique Tokens" value={data.unique_tokens} color="emerald" />
          <StatCard icon={Globe2} label="Unique IPs" value={data.unique_ips} color="slate" />
          <StatCard icon={Flame} label="Anomalies" value={totalAnomalies} color="amber"
            subtitle={`${data.anomaly_summary.high}H · ${data.anomaly_summary.medium}M · ${data.anomaly_summary.low}L`} />
          <StatCard icon={AlertTriangle} label="Unack Alerts" value={unackedAlerts.length} color="rose" />
        </div>

        {/* Anomaly Alerts Feed */}
        {alerts.length > 0 && (
          <Card className="p-4" data-testid="ai-alerts-feed">
            <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-600" />Recent Anomaly Alerts
              <Badge className="bg-rose-100 text-rose-700 text-[10px]">{unackedAlerts.length} unacknowledged</Badge>
            </h2>
            <div className="space-y-2">
              {alerts.slice(0, 10).map(a => (
                <div key={a.id} className={`p-2.5 rounded border-l-4 ${a.acknowledged ? 'bg-slate-50 border-l-slate-300' : 'bg-rose-50 border-l-rose-500'}`} data-testid={`ai-alert-${a.id}`}>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-800">
                        <span className={a.acknowledged ? 'text-slate-500' : 'text-rose-700'}>[{a.severity.toUpperCase()}]</span>
                        {' '}{a.client_name || '—'} · <code className="font-mono text-[10px]">{a.token_prefix}</code>
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {a.flag_types.join(' · ')} · {new Date(a.created_at).toLocaleString()}
                      </p>
                      {a.delivery && (
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Slack: {a.delivery.slack || '—'} · Email: {a.delivery.email || '—'} · Internal: {a.delivery.internal || '—'}
                        </p>
                      )}
                    </div>
                    {!a.acknowledged && (
                      <Button size="sm" variant="outline" onClick={() => acknowledgeAlert(a.id)} className="h-7 text-[11px]" data-testid={`ai-ack-${a.id}`}>
                        <ShieldCheck className="h-3 w-3 mr-1" />Acknowledge
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Trend Chart */}
        <Card className="p-4" data-testid="ai-trend-chart">
          <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-leamss-teal-600" />Daily Event Trend ({days} days)
          </h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.trend}>
              <XAxis dataKey="date" tick={{ fontSize: 9 }} tickFormatter={(d) => d.slice(5)} interval={Math.floor(days / 12)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="generated" stackId="a" fill="#10b981" name="Generated" />
              <Bar dataKey="accessed" stackId="a" fill="#6366f1" name="Accessed" />
              <Bar dataKey="denied" stackId="a" fill="#f59e0b" name="Denied" />
              <Bar dataKey="revoked" stackId="a" fill="#dc2626" name="Revoked" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Top Anomalies */}
          <Card className="p-4" data-testid="ai-top-anomalies">
            <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Flame className="h-4 w-4 text-rose-600" />Top Anomaly Tokens
            </h2>
            {data.top_anomalies.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-4 text-center">No anomalies detected in the window.</p>
            ) : (
              <div className="space-y-1.5 max-h-80 overflow-y-auto">
                {data.top_anomalies.map(a => (
                  <div key={a.share_token} className="text-xs p-2 bg-slate-50 rounded border">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold truncate flex-1">
                        <Badge className={a.severity === 'high' ? 'bg-rose-100 text-rose-700 text-[9px] mr-1' : a.severity === 'medium' ? 'bg-amber-100 text-amber-700 text-[9px] mr-1' : 'bg-yellow-100 text-yellow-700 text-[9px] mr-1'}>
                          {a.severity}
                        </Badge>
                        {a.client_name || '—'}
                      </p>
                      <code className="text-[10px] font-mono text-slate-400">{a.token_prefix}</code>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {a.flags.map(f => f.type.replace(/_/g, ' ')).join(' · ')} ({a.total_events} events)
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Share Type Breakdown */}
          <Card className="p-4" data-testid="ai-share-type">
            <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Shield className="h-4 w-4 text-leamss-teal-600" />Events by Share Type
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={shareTypePie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={(e) => `${e.name}: ${e.value}`}>
                  {shareTypePie.map((entry) => (
                    <Cell key={entry.name} fill={SHARE_TYPE_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Top Flagging IPs */}
        <Card className="p-4" data-testid="ai-top-ips">
          <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
            <Eye className="h-4 w-4 text-amber-600" />Top Active IPs
          </h2>
          {data.top_ips.length === 0 ? (
            <p className="text-xs text-slate-400 italic py-4 text-center">No IP activity recorded.</p>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-[10px] uppercase font-bold text-slate-500 border-b">
                <tr><th className="text-left p-2">IP</th><th className="text-right p-2">Total Events</th><th className="text-right p-2">Distinct Tokens</th><th className="text-right p-2">Denied</th><th className="text-right p-2">Risk</th></tr>
              </thead>
              <tbody>
                {data.top_ips.map(ip => {
                  const risk = ip.denied_count >= 5 || ip.distinct_tokens >= 5 ? 'high' : ip.denied_count >= 2 ? 'medium' : 'low';
                  return (
                    <tr key={ip.ip} className="border-b hover:bg-slate-50" data-testid={`ai-ip-row-${ip.ip}`}>
                      <td className="p-2 font-mono">{ip.ip}</td>
                      <td className="p-2 text-right">{ip.total_events}</td>
                      <td className="p-2 text-right">{ip.distinct_tokens}</td>
                      <td className="p-2 text-right">{ip.denied_count}</td>
                      <td className="p-2 text-right">
                        <Badge className={risk === 'high' ? 'bg-rose-100 text-rose-700 text-[9px]' : risk === 'medium' ? 'bg-amber-100 text-amber-700 text-[9px]' : 'bg-emerald-100 text-emerald-700 text-[9px]'}>
                          {risk.toUpperCase()}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>

        <p className="text-[10px] text-slate-400 text-center pt-2">
          LEAMSS Audit Engine · Phase 6.9b · All events SHA-256 chained · Stored in Legal Archive
        </p>
      </div>
    </div>
  );
}


function StatCard({ icon: Icon, label, value, color, subtitle }) {
  const colorMap = {
    indigo: 'border-leamss-teal-200 bg-leamss-teal-50 text-leamss-teal-700',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-600',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    rose: 'border-rose-200 bg-rose-50 text-rose-700',
  };
  return (
    <Card className={`p-3 border-l-4 ${colorMap[color] || colorMap.slate}`}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" />
        <p className="text-[10px] uppercase font-bold">{label}</p>
      </div>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtitle && <p className="text-[10px] text-slate-500 mt-0.5">{subtitle}</p>}
    </Card>
  );
}
