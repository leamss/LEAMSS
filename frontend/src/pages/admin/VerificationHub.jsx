/**
 * Phase 7.1 — Verification Hub
 *
 * Unified admin screen showing pending verifications across 4 KB entity types:
 *   - Occupation Master
 *   - Country Templates
 *   - Country Guides
 *   - Protection Policies
 *
 * Plus a panel for one-click ANZSCO Excel re-import.
 *
 * Route: /admin/verify-hub
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, ShieldCheck, FileText, Globe2, FileBadge, Loader2,
  Upload, Database, Sparkles, AlertCircle, Clock, ExternalLink, RefreshCw,
  Cloud, Info,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ANZSCO_SOURCE_TYPE = 'anzsco_4digit';

const STATUS_PILL = {
  active: 'bg-emerald-100 text-emerald-700',
  draft: 'bg-amber-100 text-amber-700',
  verified: 'bg-emerald-100 text-emerald-700',
  outdated: 'bg-rose-100 text-rose-700',
  superseded: 'bg-rose-100 text-rose-700',
  hidden: 'bg-slate-200 text-slate-600',
};

// Phase 17.0 — Human-friendly "x minutes ago" without a heavy dep.
function relativeTime(iso) {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const diff = (Date.now() - t) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} d ago`;
  return new Date(iso).toLocaleDateString();
}

function formatBytes(n) {
  if (!n) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// Phase 17.1 — sum every status bucket so tab badges match KPI tile totals.
function sumCounts(counts) {
  if (!counts) return 0;
  return Object.values(counts).reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0);
}

export default function VerificationHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const fileInputRef = useRef(null);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [autoFetching, setAutoFetching] = useState(false);
  const [latestFile, setLatestFile] = useState(null);
  // Phase 17.0 — banner shown when /import-anzsco-default returns 409 NO_PRIOR_FILE
  const [noPriorBanner, setNoPriorBanner] = useState(null);

  const loadHub = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/kb-unified/verification-hub`, { headers });
      setData(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load Verification Hub'));
    } finally { setLoading(false); }
  }, [headers]);

  const loadLatest = useCallback(async () => {
    try {
      const r = await axios.get(
        `${API}/kb-unified/import-files/latest?source_type=${ANZSCO_SOURCE_TYPE}`,
        { headers },
      );
      setLatestFile(r.data?.file || null);
    } catch (e) {
      // Non-fatal — button will just default to upload behaviour.
      console.warn('latest-file fetch failed', e);
    }
  }, [headers]);

  useEffect(() => { loadHub(); loadLatest(); /* eslint-disable-next-line */ }, []);

  // Phase 17.0 — REIMPORT: re-runs against latest stored file. If backend says
  // NO_PRIOR_FILE (race condition or storage cleared) we surface a banner with
  // action choices rather than a toast-and-forget error.
  const reimportExcel = async () => {
    if (!latestFile) {
      // No prior file → trigger upload picker directly (no broken-error UX).
      fileInputRef.current?.click();
      return;
    }
    if (!window.confirm(`Re-import ${latestFile.filename_original}? This will upsert all ANZSCO 4-digit codes (verified data preserved).`)) return;
    setImporting(true);
    setNoPriorBanner(null);
    try {
      const r = await axios.post(`${API}/kb-unified/import-anzsco-default`, {}, { headers });
      const s = r.data?.summary || {};
      const fn = r.data?.file?.filename_original || latestFile.filename_original;
      toast.success(`✓ Re-imported ${fn} — ${s.imported || 0} new + ${s.updated || 0} updated (${s.skipped || 0} skipped, ${s.duration_seconds || 0}s)`);
      await Promise.all([loadHub(), loadLatest()]);
    } catch (e) {
      // 409 NO_PRIOR_FILE — show structured banner, not a toast.
      if (e?.response?.status === 409 && e?.response?.data?.code === 'NO_PRIOR_FILE') {
        setNoPriorBanner(e.response.data);
      } else {
        toast.error(formatApiError(e, 'Re-import failed'));
      }
    } finally { setImporting(false); }
  };

  // Phase 17.0 — UPLOAD path: multipart POST to /import-anzsco-excel which
  // both persists the file AND runs the import in one shot.
  const handleFilePicked = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      toast.error('Only .xlsx files are supported');
      return;
    }
    setUploading(true);
    setNoPriorBanner(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/kb-unified/import-anzsco-excel`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      const s = r.data?.summary || {};
      toast.success(`✓ Uploaded ${file.name} — ${s.imported || 0} new + ${s.updated || 0} updated in ${s.duration_seconds || 0}s`);
      await Promise.all([loadHub(), loadLatest()]);
    } catch (err) {
      toast.error(formatApiError(err, 'Upload failed'));
    } finally {
      setUploading(false);
      // Reset input so picking the same file again still fires `onChange`.
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Phase 17.1 — multi-country auto-fetch. Defaults to all 3 sequentially.
  const autoFetchAnzsco = async (country = 'ALL') => {
    const label = country === 'ALL' ? 'all 3 countries (AU + CA + NZ)' :
                  country === 'AU' ? 'AU (Home Affairs SOL)' :
                  country === 'CA' ? 'CA (StatCan NOC + IRCC EE)' :
                  country === 'NZ' ? 'NZ (Green List + AEWV + ANZSCO)' : country;
    if (!window.confirm(`Yeh ${label} ko live gov sources se update karega. Continue?`)) return;
    setAutoFetching(true);
    setNoPriorBanner(null);
    try {
      const r = await axios.post(`${API}/kb-unified/auto-fetch-country`,
                                 { country }, { headers });
      const d = r.data || {};
      const summary = (d.results || []).map(x =>
        `${x.country}: ${x.imported || 0}+ ${x.updated || 0}↻`
      ).join(' · ');
      toast.success(`✓ Auto-fetch complete — ${summary} (${d.totals?.duration_seconds || 0}s)`);
      await loadHub();
    } catch (e) {
      toast.error(formatApiError(e, 'Auto-fetch failed'));
    } finally { setAutoFetching(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading Verification Hub…
      </div>
    );
  }
  if (!data) return null;

  const { summary, pending_lists } = data;

  const STATS_TILES = [
    {
      label: 'Occupations',
      icon: FileText,
      color: 'indigo',
      counts: summary.occupation_master.counts,
      verifiedPct: summary.occupation_master.verified_pct,
      manageUrl: '/admin/kb/occupation-master',
    },
    {
      label: 'Country Templates',
      icon: Globe2,
      color: 'blue',
      counts: summary.country_templates.counts,
      verifiedPct: summary.country_templates.verified_pct,
      manageUrl: '/admin/kb/occupation-master?tab=templates',
    },
    {
      label: 'Country Guides',
      icon: FileBadge,
      color: 'violet',
      counts: summary.country_guides.counts,
      verifiedPct: summary.country_guides.verified_pct,
      manageUrl: '/admin/country-guides',
    },
    {
      label: 'Protection Policies',
      icon: ShieldCheck,
      color: 'emerald',
      counts: summary.protection_policies.counts,
      verifiedPct: summary.protection_policies.verified_pct,
      manageUrl: '/admin/protection-policies',
    },
  ];

  // Phase 17.0 — Dynamic primary-button label/icon based on whether a file
  // has ever been stored. NEVER renders any path-like string — only the
  // sanitised `filename_original` reaches the user.
  const primaryBtnLabel = latestFile ? 'Re-import Excel' : 'Upload Excel';
  const primaryBtnIcon = latestFile ? RefreshCw : Upload;
  const PrimaryIcon = primaryBtnIcon;
  const primaryBusy = importing || uploading;

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="verification-hub">
      <div className="max-w-7xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Admin Home
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold flex items-center gap-2 text-indigo-900">
              <ShieldCheck className="h-7 w-7 text-indigo-600" />
              Verification Hub
              <Badge className="bg-indigo-600 text-white text-[9px]">Phase 17.0</Badge>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Single dashboard for all Knowledge Base verifications — Occupations · Country Templates · Country Guides · Protection Policies
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => { loadHub(); loadLatest(); }} data-testid="refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" />Refresh
          </Button>
        </div>

        {/* Hidden file input — opened programmatically */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          onChange={handleFilePicked}
          className="hidden"
          data-testid="anzsco-file-input"
        />

        {/* 409 NO_PRIOR_FILE banner (non-modal) */}
        {noPriorBanner && (
          <Card className="p-4 border-l-4 border-l-amber-500 bg-amber-50/40" data-testid="no-prior-banner">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-amber-900">{noPriorBanner.message}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {(noPriorBanner.actions || []).map((a, i) => (
                    <Button
                      key={i}
                      size="sm"
                      variant={a.kind === 'upload' ? 'default' : 'outline'}
                      onClick={() => {
                        if (a.kind === 'upload') fileInputRef.current?.click();
                        else if (a.kind === 'fetch_latest') autoFetchAnzsco();
                        setNoPriorBanner(null);
                      }}
                      data-testid={`no-prior-action-${a.kind}`}
                    >
                      {a.kind === 'upload' ? <Upload className="h-3.5 w-3.5 mr-1" /> : <Cloud className="h-3.5 w-3.5 mr-1" />}
                      {a.label}
                    </Button>
                  ))}
                  <Button size="sm" variant="ghost" onClick={() => setNoPriorBanner(null)}>Dismiss</Button>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* ANZSCO Master Card */}
        <Card className="p-4 border-l-4 border-l-indigo-500 bg-gradient-to-r from-indigo-50/40 to-white" data-testid="anzsco-master-card">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="h-12 w-12 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
                <Database className="h-6 w-6 text-white" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base font-bold text-indigo-900">ANZSCO 4-Digit Master</h3>
                <p className="text-xs text-slate-600">
                  <strong className="text-indigo-700">{summary.anzsco_4digit_master.total_codes.toLocaleString()}</strong> codes loaded ·
                  Source: <span className="font-mono">{summary.anzsco_4digit_master.data_source}</span>
                </p>
                {latestFile ? (
                  <p
                    className="text-[10px] text-slate-500 mt-0.5 truncate"
                    data-testid="verif-hub-latest-file-meta"
                    title={latestFile.filename_original}
                  >
                    <Clock className="inline h-3 w-3 mr-0.5" />
                    Last upload: <strong>{latestFile.filename_original}</strong>
                    {' · '}{relativeTime(latestFile.uploaded_at)}
                    {latestFile.size_bytes ? ` · ${formatBytes(latestFile.size_bytes)}` : ''}
                    {latestFile.uploaded_by_name ? ` · by ${latestFile.uploaded_by_name}` : ''}
                  </p>
                ) : (
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    <Info className="inline h-3 w-3 mr-0.5" />
                    No Excel uploaded yet — click "Upload Excel" or "Fetch Latest".
                  </p>
                )}
                <a
                  href="https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations"
                  target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-indigo-600 hover:underline flex items-center gap-1 mt-0.5"
                >
                  <ExternalLink className="h-3 w-3" />jobsandskills.gov.au
                </a>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={reimportExcel}
                disabled={primaryBusy}
                className="bg-indigo-600 hover:bg-indigo-700"
                data-testid={latestFile ? 'verif-hub-reimport-btn' : 'verif-hub-upload-btn'}
              >
                {primaryBusy
                  ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  : <PrimaryIcon className="h-4 w-4 mr-2" />}
                {primaryBusy ? (importing ? 'Importing…' : 'Uploading…') : primaryBtnLabel}
              </Button>
              <Button
                onClick={() => autoFetchAnzsco('ALL')}
                disabled={autoFetching}
                variant="outline"
                className="border-indigo-300 text-indigo-700 hover:bg-indigo-50"
                data-testid="verif-hub-autofetch-btn"
                title="Live scrape AU + CA + NZ official sources"
              >
                {autoFetching ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Cloud className="h-4 w-4 mr-2" />}
                {autoFetching ? 'Fetching…' : 'Fetch All 3 Countries'}
              </Button>
              <Button onClick={() => autoFetchAnzsco('AU')} disabled={autoFetching}
                      variant="ghost" size="sm" className="text-indigo-700"
                      data-testid="verif-hub-autofetch-au">🇦🇺 AU</Button>
              <Button onClick={() => autoFetchAnzsco('CA')} disabled={autoFetching}
                      variant="ghost" size="sm" className="text-indigo-700"
                      data-testid="verif-hub-autofetch-ca">🇨🇦 CA</Button>
              <Button onClick={() => autoFetchAnzsco('NZ')} disabled={autoFetching}
                      variant="ghost" size="sm" className="text-indigo-700"
                      data-testid="verif-hub-autofetch-nz">🇳🇿 NZ</Button>
            </div>
          </div>
        </Card>

        {/* Stat Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="stat-tiles">
          {STATS_TILES.map(t => <StatTile key={t.label} tile={t} navigate={navigate} />)}
        </div>

        {/* Pending Lists tabs */}
        <Card className="p-4">
          <Tabs defaultValue="occupations" className="w-full">
            <TabsList className="bg-slate-100">
              <TabsTrigger value="occupations" data-testid="tab-occupations">
                Occupations ({sumCounts(summary.occupation_master.counts)})
              </TabsTrigger>
              <TabsTrigger value="templates" data-testid="tab-templates">
                Country Templates ({sumCounts(summary.country_templates.counts)})
              </TabsTrigger>
              <TabsTrigger value="guides" data-testid="tab-guides">
                Country Guides ({sumCounts(summary.country_guides.counts)})
              </TabsTrigger>
              <TabsTrigger value="policies" data-testid="tab-policies">
                Protection Policies ({sumCounts(summary.protection_policies.counts)})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="occupations" className="pt-3">
              <OccupationsTable headers={headers} />
            </TabsContent>
            <TabsContent value="templates" className="pt-3">
              <PendingList
                items={pending_lists.country_templates}
                emptyMessage="No country templates match the current filters. Try changing the status filter or seed defaults."
                renderItem={(it) => ({
                  primary: `${it.country_code} · ${it.country_name}`,
                  secondary: it.updated_at ? `Updated: ${new Date(it.updated_at).toLocaleDateString()}` : '—',
                  status: it.status,
                  link: `/admin/kb/occupation-master?tab=templates`,
                })}
              />
            </TabsContent>
            <TabsContent value="guides" className="pt-3">
              <PendingList
                items={pending_lists.country_guides}
                emptyMessage="No country guides match the current filters."
                renderItem={(it) => ({
                  primary: `${it.country_code} · ${it.name}`,
                  secondary: it.updated_at ? `Updated: ${new Date(it.updated_at).toLocaleDateString()}` : '—',
                  status: it.status,
                  link: `/admin/country-guides?code=${it.country_code}`,
                })}
              />
            </TabsContent>
            <TabsContent value="policies" className="pt-3">
              <PendingList
                items={pending_lists.protection_policies}
                emptyMessage="No protection policies match the current filters."
                renderItem={(it) => ({
                  primary: it.title,
                  secondary: `ID: ${it.policy_id}`,
                  status: it.status,
                  link: `/admin/protection-policies?focus=${it.policy_id}`,
                })}
              />
            </TabsContent>
          </Tabs>
        </Card>
      </div>
    </div>
  );
}

function StatTile({ tile, navigate }) {
  const Icon = tile.icon;
  const total = Object.values(tile.counts).reduce((a, b) => a + b, 0);
  const verified = tile.counts.verified || tile.counts.active || 0;
  const draft = tile.counts.draft || 0;
  const colorClass = {
    indigo: 'border-l-indigo-500 bg-indigo-50/30',
    blue: 'border-l-blue-500 bg-blue-50/30',
    violet: 'border-l-violet-500 bg-violet-50/30',
    emerald: 'border-l-emerald-500 bg-emerald-50/30',
  }[tile.color];
  return (
    <Card
      className={`p-4 border-l-4 cursor-pointer transition hover:shadow-md ${colorClass}`}
      onClick={() => navigate(tile.manageUrl)}
      data-testid={`stat-tile-${tile.label.replace(/\s+/g, '-').toLowerCase()}`}
    >
      <div className="flex items-start justify-between mb-2">
        <Icon className={`h-5 w-5 text-${tile.color}-600`} />
        <Badge className="bg-white text-slate-700 text-[9px]">{tile.verifiedPct}% verified</Badge>
      </div>
      <h4 className="text-xs uppercase tracking-wider font-bold text-slate-600">{tile.label}</h4>
      <p className="text-2xl font-bold text-slate-900 mt-1" data-testid={`stat-total-${tile.label.replace(/\s+/g, '-').toLowerCase()}`}>{total}</p>
      <div className="flex items-center gap-3 text-[10px] text-slate-500 mt-1">
        <span><strong className="text-emerald-700">{verified}</strong> verified</span>
        {draft > 0 && <span><strong className="text-amber-700">{draft}</strong> draft</span>}
      </div>
    </Card>
  );
}

function PendingList({ items, emptyMessage, renderItem }) {
  if (!items.length) {
    return (
      <div className="text-center py-10 text-slate-400">
        <ShieldCheck className="h-8 w-8 mx-auto mb-2 opacity-30" />
        <p className="text-xs">{emptyMessage}</p>
      </div>
    );
  }
  return (
    <ul className="divide-y">
      {items.map((it, i) => {
        const r = renderItem(it);
        return (
          <li key={i} className="py-2.5 flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-800 truncate">{r.primary}</p>
              <p className="text-[10px] text-slate-500">{r.secondary}</p>
            </div>
            <Badge className={`${STATUS_PILL[r.status] || 'bg-slate-100'} text-[9px]`}>
              {r.status || 'unknown'}
            </Badge>
            <Link to={r.link} className="text-xs text-indigo-600 hover:underline whitespace-nowrap">
              Open →
            </Link>
          </li>
        );
      })}
    </ul>
  );
}


// Phase 17.1 — Occupations table with country/status filter + pagination
function OccupationsTable({ headers }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [country, setCountry] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(false);

  // Debounce search input by 400ms
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const skip = (page - 1) * pageSize;
        const params = new URLSearchParams({ limit: pageSize, skip });
        if (country) params.set('country', country);
        if (status) params.set('status', status);
        if (searchDebounced) params.set('search', searchDebounced);
        const r = await axios.get(`${API}/occupation-master?${params}`, { headers });
        if (cancelled) return;
        setRows(r.data?.items || []);
        setTotal(r.data?.total || 0);
      } catch (e) {
        if (!cancelled) toast.error(formatApiError(e, 'Failed to load occupations'));
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line
  }, [country, status, searchDebounced, page, pageSize]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div data-testid="occupations-table">
      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 items-center mb-3">
        <input
          type="text"
          placeholder="Search code or title…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="px-3 py-1.5 text-sm border border-slate-300 rounded-md flex-1 min-w-[200px]"
          data-testid="occ-search"
        />
        <select
          value={country}
          onChange={(e) => { setCountry(e.target.value); setPage(1); }}
          className="px-2 py-1.5 text-sm border border-slate-300 rounded-md"
          data-testid="occ-country"
        >
          <option value="">All countries</option>
          <option value="AU">🇦🇺 Australia</option>
          <option value="CA">🇨🇦 Canada</option>
          <option value="NZ">🇳🇿 New Zealand</option>
        </select>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="px-2 py-1.5 text-sm border border-slate-300 rounded-md"
          data-testid="occ-status"
        >
          <option value="">All statuses</option>
          <option value="verified">Verified</option>
          <option value="draft">Draft</option>
          <option value="needs_review">Needs Review</option>
          <option value="archived">Archived</option>
        </select>
        <select
          value={pageSize}
          onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
          className="px-2 py-1.5 text-sm border border-slate-300 rounded-md"
          data-testid="occ-page-size"
        >
          <option value={25}>25 / page</option>
          <option value={50}>50 / page</option>
          <option value={100}>100 / page</option>
        </select>
        <span className="text-xs text-slate-500 ml-auto">
          {loading ? 'Loading…' : `${total} record${total === 1 ? '' : 's'}`}
        </span>
      </div>

      {/* Table */}
      {rows.length === 0 && !loading ? (
        <p className="text-xs text-slate-500 py-6 text-center">
          No occupations match the current filters. Try changing the country or status filter, or upload a new Excel.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 text-left text-slate-600">
                <th className="px-2 py-2">Code</th>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Country</th>
                <th className="px-2 py-2">Category</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Last Verified</th>
                <th className="px-2 py-2">Source</th>
                <th className="px-2 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={`${r.country_code}-${r.code}`} className="border-t hover:bg-slate-50">
                  <td className="px-2 py-1.5 font-mono">{r.code}</td>
                  <td className="px-2 py-1.5">{r.title}</td>
                  <td className="px-2 py-1.5">{r.country_code}</td>
                  <td className="px-2 py-1.5">
                    {r.teer_category != null ? `TEER ${r.teer_category}` :
                     r.anzsco_major_group_code ? `Major ${r.anzsco_major_group_code}` : '—'}
                  </td>
                  <td className="px-2 py-1.5">
                    <Badge className={STATUS_PILL[r.status] || 'bg-slate-200 text-slate-600'}>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-2 py-1.5">
                    {r.verification?.verified_at || r.verification?.auto_verified_at
                      ? relativeTime(r.verification.verified_at || r.verification.auto_verified_at)
                      : '—'}
                  </td>
                  <td className="px-2 py-1.5 text-slate-500 truncate max-w-[160px]">
                    {r.verification?.source || r.last_scraped_by || '—'}
                  </td>
                  <td className="px-2 py-1.5 whitespace-nowrap">
                    <Link to={`/admin/kb/occupation-master?country=${encodeURIComponent(r.country_code || '')}&code=${encodeURIComponent(r.code || '')}`}
                          className="text-indigo-600 hover:underline">
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between mt-3 text-xs">
        <span className="text-slate-500">Page {page} of {totalPages}</span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1 || loading}
                  onClick={() => setPage(p => p - 1)} data-testid="occ-prev">
            Prev
          </Button>
          <Button size="sm" variant="outline" disabled={page >= totalPages || loading}
                  onClick={() => setPage(p => p + 1)} data-testid="occ-next">
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

