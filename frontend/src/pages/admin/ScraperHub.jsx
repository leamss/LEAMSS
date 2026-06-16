/**
 * Phase 19.2a-Lite — Scraper Hub admin page
 * Route: /admin/scrapers (linked from /admin/verify-hub via a tile)
 *
 * Lists all registered scrapers (ACS, VETASSESS, Engineers AU, NZQA, WES,
 * ABS Census) with their last-run status, lets admin trigger one-off runs.
 */
import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import { Play, ArrowLeft, RefreshCw, AlertTriangle, CheckCircle, MinusCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TOKEN_KEY = 'token';

function statusBadge(latest) {
  if (!latest) return <Badge variant="outline" data-testid="scraper-tile-status-never">Never run</Badge>;
  const s = latest.status;
  if (s === 'success') return <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100" data-testid={`scraper-tile-status-${latest.scraper_id || ''}`}><CheckCircle className="w-3 h-3 mr-1"/>Success</Badge>;
  if (s === 'partial') return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100"><AlertTriangle className="w-3 h-3 mr-1"/>Partial</Badge>;
  if (s === 'skipped') return <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100"><MinusCircle className="w-3 h-3 mr-1"/>Skipped</Badge>;
  return <Badge variant="destructive">{s}</Badge>;
}

function relTime(iso) {
  if (!iso) return '—';
  try {
    const t = new Date(iso).getTime();
    const dt = (Date.now() - t) / 1000;
    if (dt < 60) return `${Math.round(dt)}s ago`;
    if (dt < 3600) return `${Math.round(dt / 60)}m ago`;
    if (dt < 86400) return `${Math.round(dt / 3600)}h ago`;
    return `${Math.round(dt / 86400)}d ago`;
  } catch { return '—'; }
}

export default function ScraperHub() {
  const navigate = useNavigate();
  const [scrapers, setScrapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/scrapers/all-status`, {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
      });
      setScrapers(r.data.scrapers || []);
    } catch (e) {
      toast.error(`Failed to load scrapers: ${e.response?.data?.detail || e.message}`);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runOne = async (sid, label) => {
    setRunning((r) => ({ ...r, [sid]: true }));
    const toastId = toast.loading(`Running ${label}…`);
    try {
      const r = await axios.post(`${API}/scrapers/${sid}/run`, {}, {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
        timeout: 90_000,
      });
      const d = r.data;
      toast.success(
        `${label}: ${d.status} · ${d.records_updated}/${d.records_attempted} updated · ${d.duration_ms}ms`,
        { id: toastId, duration: 5000 },
      );
      await load();
    } catch (e) {
      toast.error(`${label} failed: ${e.response?.data?.detail || e.message}`, { id: toastId });
    } finally {
      setRunning((r) => ({ ...r, [sid]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8" data-testid="scraper-hub-page">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <button onClick={() => navigate('/admin/verify-hub')} className="text-sm text-slate-600 hover:text-slate-900 flex items-center gap-1 mb-2" data-testid="back-to-verify-hub">
              <ArrowLeft className="w-4 h-4"/>Back to Verify Hub
            </button>
            <h1 className="text-3xl font-bold text-slate-900">🔧 Scraper Hub</h1>
            <p className="text-sm text-slate-600 mt-1">
              Phase 19.2a-Lite · 6 registered data sources · scheduled monthly · manual triggers below.
            </p>
          </div>
          <Button variant="outline" onClick={load} disabled={loading} data-testid="refresh-scrapers">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`}/>Refresh
          </Button>
        </div>

        {/* Honest disclosure banner */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-900" data-testid="phase-19-2b-deferral-banner">
          <strong>⚠️ Phase 19.2b deferred:</strong> JSA labour-market data, TRA and ESCC scrapers are blocked
          at the preview-env Cloudflare WAF (HTTP 000 on <code>*.gov.au</code> direct domains).
          ABS Census per-ANZSCO dataflow-ID discovery is also deferred to 19.2b. These will activate
          on production cutover (or via a paid scraping vendor).
        </div>

        {loading ? (
          <p className="text-center text-slate-500 py-12">Loading scraper hub…</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="scraper-hub-grid">
            {scrapers.map((s) => (
              <Card key={s.scraper_id} className="bg-white" data-testid={`scraper-tile-${s.scraper_id}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base font-bold text-slate-900">{s.display_name}</CardTitle>
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{s.description}</p>
                    </div>
                    {statusBadge(s.latest_run)}
                  </div>
                </CardHeader>
                <CardContent className="text-xs text-slate-600 space-y-1">
                  <div className="flex justify-between"><span>Countries</span><span className="font-mono">{(s.countries || []).join(', ') || '—'}</span></div>
                  <div className="flex justify-between"><span>Last run</span><span>{relTime(s.latest_run?.created_at || s.latest_run?.finished_at)}</span></div>
                  <div className="flex justify-between"><span>Updated</span><span className="font-mono">{s.latest_run?.records_updated ?? '—'} / {s.latest_run?.records_attempted ?? '—'}</span></div>
                  <div className="flex justify-between"><span>Duration</span><span className="font-mono">{s.latest_run?.duration_ms ?? '—'} ms</span></div>
                  {s.latest_run?.notes && (
                    <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-100 mt-2 line-clamp-3">
                      {s.latest_run.notes}
                    </p>
                  )}
                  <Button
                    size="sm"
                    className="w-full mt-3 bg-emerald-700 hover:bg-emerald-800"
                    disabled={!!running[s.scraper_id]}
                    onClick={() => runOne(s.scraper_id, s.display_name)}
                    data-testid={`scraper-run-now-btn-${s.scraper_id}`}
                  >
                    <Play className="w-3 h-3 mr-2"/>
                    {running[s.scraper_id] ? 'Running…' : 'Run Now'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
