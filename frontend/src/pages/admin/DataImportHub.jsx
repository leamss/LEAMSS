/**
 * Phase 19.4 — Universal Data Import Hub admin page
 * Route: /admin/data-import
 *
 * Full upload + dry-run preview + idempotent commit + history flow for the
 * Jobs and Skills Australia (JSA) Feb 2026 data drops. Supports:
 *   - occupation_profiles (4-digit ANZSCO × ABS data)
 *   - employment_projections (4-digit ANZSCO × 10y growth)
 *   - sa4_ratings (94 SA4 regions × labour-market strength)
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import {
  ArrowLeft, RefreshCw, Upload, Trash2, FileText,
  CheckCircle, AlertTriangle, Database,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TOKEN_KEY = 'token';

const TYPE_LABELS = {
  occupation_profiles: { label: 'Occupation Profiles (ABS)', color: 'bg-emerald-100 text-emerald-800' },
  employment_projections: { label: '10-year Employment Projections', color: 'bg-blue-100 text-blue-800' },
  sa4_ratings: { label: 'SA4 Regional Ratings', color: 'bg-purple-100 text-purple-800' },
  industry_data: { label: 'Industry Data (ANZSIC)', color: 'bg-orange-100 text-orange-800' },
  vacancy_report: { label: 'Vacancy Report (IVI)', color: 'bg-rose-100 text-rose-800' },
  unknown: { label: 'Unknown / Unsupported', color: 'bg-slate-100 text-slate-700' },
};

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

function fmtBytes(n) {
  if (!n) return '—';
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${(n / (1024 * 1024)).toFixed(1)}MB`;
}

export default function DataImportHub() {
  const nav = useNavigate();
  const [history, setHistory] = useState([]);
  const [vacancy, setVacancy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [committing, setCommitting] = useState(false);
  const [regenLoading, setRegenLoading] = useState(false);
  const fileInputRef = useRef(null);
  const token = localStorage.getItem(TOKEN_KEY);
  const authH = { headers: { Authorization: `Bearer ${token}` } };

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      const r = await axios.get(`${API}/data-import/history?limit=20`, authH);
      setHistory(r.data.items || []);
      // Phase 19.4c — also fetch latest vacancy snapshot
      const v = await axios.get(`${API}/data-import/vacancy/latest`, authH);
      setVacancy(v.data.snapshot);
    } catch (e) {
      toast.error(`History fetch failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setPreview(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/data-import/upload`, fd, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success(`Uploaded: ${r.data.filename} → detected as ${r.data.detected_type}`);
      // Auto-trigger preview
      const pr = await axios.post(`${API}/data-import/${r.data.file_id}/parse-preview`, {}, authH);
      setPreview(pr.data);
      fetchHistory();
    } catch (e) {
      toast.error(`Upload failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleCommit = async () => {
    if (!preview?.file_id) return;
    if (!window.confirm(`Commit ${preview.row_count} ${preview.detected_type} records to DB?`)) return;
    setCommitting(true);
    try {
      const r = await axios.post(`${API}/data-import/${preview.file_id}/commit`, {}, authH);
      toast.success(`Committed ✓ — ${JSON.stringify(r.data.summary)}`);
      setPreview(null);
      fetchHistory();
    } catch (e) {
      toast.error(`Commit failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setCommitting(false);
    }
  };

  const handleDelete = async (fileId) => {
    if (!window.confirm('Delete this import record + file on disk? (Does NOT rollback committed data.)')) return;
    try {
      await axios.delete(`${API}/data-import/${fileId}`, authH);
      toast.success('Deleted');
      fetchHistory();
    } catch (e) {
      toast.error(`Delete failed: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const handleSSGRegen = async () => {
    setRegenLoading(true);
    try {
      const r = await axios.post(`${API}/seo-ssg/regenerate-all`, {}, authH);
      toast.success(`SSG regen complete — ${r.data.occupations_written} occupations, ${r.data.duration_ms}ms`);
    } catch (e) {
      toast.error(`SSG regen failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRegenLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6" data-testid="data-import-hub">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <Button variant="ghost" onClick={() => nav('/admin/verify-hub')} className="-ml-2" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4 mr-1" /> Verify Hub
            </Button>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">Universal Data Import Hub</h1>
            <p className="text-sm text-slate-600">
              Phase 19.4 — JSA data drops (Occupation Profiles, Employment Projections, SA4 Ratings)
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchHistory} disabled={loading} data-testid="refresh-btn">
              <RefreshCw className="w-4 h-4 mr-1" /> Refresh
            </Button>
            <Button onClick={handleSSGRegen} disabled={regenLoading} data-testid="ssg-regen-btn">
              <Database className="w-4 h-4 mr-1" /> Regenerate Atlas SSG
            </Button>
          </div>
        </div>

        {/* Phase 19.4c — Latest Vacancy Snapshot panel */}
        {vacancy && (
          <Card className="mb-6 border-rose-200 bg-rose-50/30" data-testid="vacancy-snapshot-panel">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <span>📊 Latest Vacancy Snapshot — {vacancy.period}</span>
                <Badge className="bg-rose-100 text-rose-800">JSA IVI</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div data-testid="vac-national">
                  <div className="text-xs uppercase tracking-wider text-slate-500">National Ads</div>
                  <div className="text-xl font-bold text-slate-900">{vacancy.national_ads?.toLocaleString() || '—'}</div>
                </div>
                <div data-testid="vac-mom">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Month-on-Month</div>
                  <div className={`text-xl font-bold ${(vacancy.monthly_change_pct || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {vacancy.monthly_change_pct >= 0 ? '+' : ''}{vacancy.monthly_change_pct?.toFixed(1) || '—'}%
                  </div>
                </div>
                <div data-testid="vac-yoy">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Year-on-Year</div>
                  <div className={`text-xl font-bold ${(vacancy.annual_change_pct || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {vacancy.annual_change_pct >= 0 ? '+' : ''}{vacancy.annual_change_pct?.toFixed(1) || '—'}%
                  </div>
                </div>
                <div data-testid="vac-states">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Top 3 States</div>
                  <div className="text-sm font-mono text-slate-700">
                    {Object.entries(vacancy.by_state || {})
                      .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                      .slice(0, 3)
                      .map(([s, n]) => `${s} ${(n / 1000).toFixed(0)}k`)
                      .join(' · ')}
                  </div>
                </div>
              </div>
              {vacancy.featured_occupation?.title && (
                <p className="text-xs text-slate-600 mt-3" data-testid="vac-featured">
                  <strong>Featured:</strong> {vacancy.featured_occupation.title}
                  {vacancy.next_release_date && <span className="ml-3 text-slate-400">Next release: {vacancy.next_release_date}</span>}
                </p>
              )}
              <p className="text-xs text-slate-400 mt-2">Source: {vacancy.source} · Imported {String(vacancy.last_imported_at).slice(0, 10)}</p>
            </CardContent>
          </Card>
        )}

        {/* Upload zone */}
        <Card className="mb-6" data-testid="data-import-upload">
          <CardHeader>
            <CardTitle className="text-lg">Upload new file</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:bg-slate-50 transition-colors">
              <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
              <p className="text-sm text-slate-600 mb-3">Drop an .xlsx file or click to browse</p>
              <input
                type="file"
                accept=".xlsx,.xls"
                ref={fileInputRef}
                onChange={(e) => handleFile(e.target.files?.[0])}
                className="hidden"
                data-testid="file-input"
              />
              <Button onClick={() => fileInputRef.current?.click()} disabled={uploading} data-testid="upload-btn">
                {uploading ? 'Uploading…' : 'Choose file'}
              </Button>
              <p className="text-xs text-slate-400 mt-3">
                Supported: occupation_profiles · employment_projections · sa4_ratings · industry_data · vacancy_report (PDF)
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Preview */}
        {preview && (
          <Card className="mb-6 border-emerald-300 bg-emerald-50/30" data-testid="data-import-preview-table">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-700" />
                Preview — {preview.filename}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 mb-3 text-sm">
                <span><strong>Type:</strong> <Badge className={TYPE_LABELS[preview.detected_type]?.color || ''}>{TYPE_LABELS[preview.detected_type]?.label || preview.detected_type}</Badge></span>
                <span><strong>Rows parsed:</strong> {preview.row_count.toLocaleString()}</span>
                <span><strong>Source:</strong> {preview.source}</span>
              </div>
              {preview.honest_note && (
                <div className="bg-amber-50 border-l-4 border-amber-400 p-3 mb-3 text-xs text-amber-900 rounded" data-testid="honest-note">
                  <strong>⚠️ Honest note:</strong> {preview.honest_note}
                </div>
              )}
              <details className="mb-3">
                <summary className="cursor-pointer text-sm font-semibold text-slate-700">Sample (first 5 records)</summary>
                <pre className="mt-2 bg-slate-900 text-emerald-300 text-xs p-3 rounded overflow-auto max-h-96">{JSON.stringify(preview.sample, null, 2)}</pre>
              </details>
              <div className="flex gap-2">
                <Button onClick={handleCommit} disabled={committing} className="bg-emerald-700 hover:bg-emerald-800" data-testid="data-import-commit-btn">
                  {committing ? 'Committing…' : `Commit ${preview.row_count.toLocaleString()} records to DB`}
                </Button>
                <Button variant="outline" onClick={() => setPreview(null)} data-testid="cancel-preview-btn">
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* History */}
        <Card data-testid="data-import-history">
          <CardHeader>
            <CardTitle className="text-lg">Import history ({history.length})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="text-sm text-slate-500 p-4">Loading…</p>
            ) : history.length === 0 ? (
              <p className="text-sm text-slate-500 p-4">No imports yet. Upload your first file above.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-left text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Filename</th>
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Size</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Uploaded</th>
                      <th className="px-3 py-2">Summary</th>
                      <th className="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => (
                      <tr key={h.id} className="border-t hover:bg-slate-50" data-testid={`import-row-${h.id}`}>
                        <td className="px-3 py-2 font-mono text-xs">{h.filename}</td>
                        <td className="px-3 py-2"><Badge className={TYPE_LABELS[h.detected_type]?.color}>{h.detected_type}</Badge></td>
                        <td className="px-3 py-2 text-slate-600">{fmtBytes(h.size_bytes)}</td>
                        <td className="px-3 py-2">
                          {h.status === 'committed' ? (
                            <Badge className="bg-emerald-100 text-emerald-800"><CheckCircle className="w-3 h-3 mr-1"/>Committed</Badge>
                          ) : h.status === 'failed' ? (
                            <Badge variant="destructive">Failed</Badge>
                          ) : (
                            <Badge className="bg-amber-100 text-amber-800"><AlertTriangle className="w-3 h-3 mr-1"/>{h.status}</Badge>
                          )}
                        </td>
                        <td className="px-3 py-2 text-slate-500 text-xs">{relTime(h.uploaded_at)}</td>
                        <td className="px-3 py-2 text-xs font-mono text-slate-600 max-w-md truncate">
                          {h.commit_summary ? JSON.stringify(h.commit_summary) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(h.id)} data-testid={`delete-btn-${h.id}`}>
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
