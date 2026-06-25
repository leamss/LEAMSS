import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  ArrowLeft, Globe, Play, RefreshCw, ChevronRight, AlertCircle, CheckCircle2,
  AlertTriangle, Loader2,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_CHIP = {
  pass: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warn: 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-200',
  fail: 'bg-leamss-red-100 text-leamss-red-700 border-leamss-red-200',
};

const STATUS_ICON = { pass: CheckCircle2, warn: AlertTriangle, fail: AlertCircle };

const CHECK_LABELS = {
  meta_tags: 'Meta tags',
  json_ld: 'JSON-LD schema',
  h_hierarchy: 'H1 / H2 hierarchy',
  image_alt: 'Image alt coverage',
  internal_links: 'Internal link health',
};

/**
 * Phase 21 Slice 4 Sub-Slice A.1 — IT Site Audit Hub.
 * Kick off audits, browse run history, drill into per-check results.
 */
export default function SiteAuditHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState('all');
  const [sampleSize, setSampleSize] = useState(5);
  const [kicking, setKicking] = useState(false);
  const [openRun, setOpenRun] = useState(null);
  const [runDetail, setRunDetail] = useState(null);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/site-audit/runs`, auth);
      setRuns(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load audit runs');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, []);

  useEffect(() => { if (!token) { navigate('/'); return; } loadRuns(); /* eslint-disable-next-line */ }, []);

  // Auto-poll while any run is "running"
  useEffect(() => {
    const hasRunning = runs.some(r => r.status === 'running');
    if (!hasRunning) return;
    const id = setInterval(loadRuns, 4000);
    return () => clearInterval(id);
  }, [runs, loadRuns]);

  const kickOff = async () => {
    setKicking(true);
    try {
      const { data } = await axios.post(`${API}/site-audit/run`, { scope, sample_size: sampleSize }, auth);
      toast.success(`Audit started — ${data.run_id.slice(0, 8)}`);
      await loadRuns();
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail || 'Failed to start audit';
      if (status === 409) toast.warning(msg);
      else if (status === 429) toast.warning(msg);
      else toast.error(msg);
    } finally {
      setKicking(false);
    }
  };

  const openDetail = async (run) => {
    setOpenRun(run);
    setRunDetail(null);
    try {
      const { data } = await axios.get(`${API}/site-audit/runs/${run.id}`, auth);
      setRunDetail(data);
    } catch {
      toast.error('Failed to load report');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="site-audit-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="audit-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-leamss-teal-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">Site Audit</h1>
                <p className="text-xs text-slate-500">Meta · JSON-LD · H-hierarchy · alt · link health</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Select value={scope} onValueChange={setScope}>
              <SelectTrigger className="w-32 h-9" data-testid="audit-scope">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All surfaces</SelectItem>
                <SelectItem value="atlas">Atlas pages</SelectItem>
                <SelectItem value="start">/start funnel</SelectItem>
              </SelectContent>
            </Select>
            <Select value={String(sampleSize)} onValueChange={v => setSampleSize(Number(v))}>
              <SelectTrigger className="w-24 h-9" data-testid="audit-sample">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3</SelectItem>
                <SelectItem value="5">5</SelectItem>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" variant="outline" onClick={loadRuns} data-testid="audit-refresh">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              onClick={kickOff}
              disabled={kicking}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
              data-testid="audit-run-btn"
            >
              {kicking ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
              Run audit
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-3">
        {loading && <p className="text-sm text-slate-500">Loading runs…</p>}
        {!loading && runs.length === 0 && (
          <Card className="p-10 text-center" data-testid="audit-empty">
            <Globe className="h-10 w-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500 italic mb-2">Koi audit run abhi tak nahi hua hai.</p>
            <p className="text-xs text-slate-400">Top-right ke "Run audit" se shuru kijiye.</p>
          </Card>
        )}
        {runs.map(r => {
          const total = r.summary ? (r.summary.pass + r.summary.warn + r.summary.fail) : 0;
          return (
            <Card
              key={r.id}
              className="p-4 cursor-pointer hover:shadow-md transition-all"
              onClick={() => openDetail(r)}
              data-testid={`audit-run-${r.id}`}
            >
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={r.status === 'running' ? 'bg-leamss-orange-100 text-leamss-orange-700 animate-pulse'
                      : r.status === 'complete' ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-leamss-red-100 text-leamss-red-700'}>
                      {r.status === 'running' && <Loader2 className="h-3 w-3 mr-1 inline animate-spin" />}
                      {r.status}
                    </Badge>
                    <Badge variant="outline" className="capitalize text-[10px]">scope: {r.scope}</Badge>
                    <Badge variant="outline" className="text-[10px]">sample {r.sample_size}</Badge>
                    <span className="text-[10px] text-slate-400">by {r.started_by_name}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1.5 font-mono">
                    {r.id.slice(0, 8)} · started {new Date(r.started_at).toLocaleString()}
                  </p>
                </div>
                {r.summary && (
                  <div className="flex items-center gap-2">
                    <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200">PASS {r.summary.pass}</Badge>
                    <Badge className="bg-leamss-orange-50 text-leamss-orange-700 border border-leamss-orange-200">WARN {r.summary.warn}</Badge>
                    <Badge className="bg-leamss-red-50 text-leamss-red-700 border border-leamss-red-200">FAIL {r.summary.fail}</Badge>
                    <span className="text-[10px] text-slate-400">/ {total}</span>
                  </div>
                )}
                <ChevronRight className="h-4 w-4 text-slate-300" />
              </div>
            </Card>
          );
        })}
      </div>

      {/* Detail drawer */}
      <Dialog open={!!openRun} onOpenChange={(o) => { if (!o) { setOpenRun(null); setRunDetail(null); } }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" data-testid="audit-detail-dialog">
          <DialogHeader>
            <DialogTitle>Audit Report</DialogTitle>
            {openRun && (
              <p className="text-xs text-slate-500 font-mono">{openRun.id} · scope {openRun.scope} · {new Date(openRun.started_at).toLocaleString()}</p>
            )}
          </DialogHeader>
          {!runDetail && <p className="text-sm text-slate-500 italic">Loading…</p>}
          {runDetail?.status === 'running' && (
            <Card className="p-6 text-center bg-leamss-orange-50 border-leamss-orange-200">
              <Loader2 className="h-6 w-6 text-leamss-orange-600 mx-auto mb-2 animate-spin" />
              <p className="text-sm text-slate-700">Audit chal raha hai…</p>
              <p className="text-xs text-slate-400 mt-1">Page re-fresh hote rahega 4 second mein.</p>
            </Card>
          )}
          {runDetail?.status === 'failed' && (
            <Card className="p-4 bg-leamss-red-50 border-leamss-red-200">
              <p className="text-sm text-leamss-red-700">Failed: {runDetail.error}</p>
            </Card>
          )}
          {runDetail?.pages && runDetail.pages.length === 0 && (
            <p className="text-sm text-slate-500 italic">No pages were audited.</p>
          )}
          {runDetail?.pages?.map((p, pageIdx) => (
            <Card key={pageIdx} className="p-3 mb-3" data-testid={`audit-page-${pageIdx}`}>
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <code className="text-xs text-leamss-teal-700 break-all">{p.page_url}</code>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {Object.entries(CHECK_LABELS).map(([key, label]) => {
                  const check = p[key];
                  if (!check) return null;
                  const Icon = STATUS_ICON[check.status];
                  return (
                    <div key={key} className={`p-2.5 rounded border ${STATUS_CHIP[check.status]}`} data-testid={`check-${key}-${pageIdx}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold flex items-center gap-1.5">
                          <Icon className="h-3.5 w-3.5" /> {label}
                        </span>
                        <Badge className={STATUS_CHIP[check.status]}>{check.status.toUpperCase()}</Badge>
                      </div>
                      {check.issues && check.issues.length > 0 ? (
                        <ul className="text-[11px] text-slate-700 list-disc ml-4">
                          {check.issues.map((iss, i) => <li key={i}>{iss}</li>)}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-slate-600">All checks pass</p>
                      )}
                      {check.found_types && check.found_types.length > 0 && (
                        <p className="text-[10px] text-slate-500 mt-1">Found: {check.found_types.join(', ')}</p>
                      )}
                      {check.coverage_pct !== undefined && (
                        <p className="text-[10px] text-slate-500 mt-1">Coverage: {check.coverage_pct}% · {check.missing_alt}/{check.total_imgs} missing</p>
                      )}
                      {check.broken && check.broken.length > 0 && (
                        <ul className="text-[10px] text-leamss-red-700 mt-1 ml-4 list-disc">
                          {check.broken.slice(0, 3).map((b, i) => <li key={i}><code>{b.path}</code> → {b.status_code}</li>)}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </DialogContent>
      </Dialog>
    </div>
  );
}
