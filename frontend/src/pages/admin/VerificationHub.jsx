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
import { useState, useEffect, useCallback } from 'react';
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
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_PILL = {
  active: 'bg-emerald-100 text-emerald-700',
  draft: 'bg-amber-100 text-amber-700',
  verified: 'bg-emerald-100 text-emerald-700',
  outdated: 'bg-rose-100 text-rose-700',
  superseded: 'bg-rose-100 text-rose-700',
  hidden: 'bg-slate-200 text-slate-600',
};

export default function VerificationHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/kb-unified/verification-hub`, { headers });
      setData(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load Verification Hub'));
    } finally { setLoading(false); }
  }, [headers]);

  useEffect(() => { load(); }, []);

  const reimportExcel = async () => {
    if (!window.confirm('Re-run Feb 2026 ANZSCO Excel import? This will upsert all 1,236 codes (existing data preserved, new data added).')) return;
    setImporting(true);
    try {
      const r = await axios.post(`${API}/kb-unified/import-anzsco-default`, {}, { headers });
      toast.success(`✓ Imported ${r.data.imported} new + updated ${r.data.updated} (skipped ${r.data.skipped} errors) in ${r.data.duration_seconds}s`);
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'Import failed'));
    } finally { setImporting(false); }
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
              <Badge className="bg-indigo-600 text-white text-[9px]">Phase 7.1</Badge>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Single dashboard for all Knowledge Base verifications — Occupations · Country Templates · Country Guides · Protection Policies
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" />Refresh
          </Button>
        </div>

        {/* ANZSCO Master Card */}
        <Card className="p-4 border-l-4 border-l-indigo-500 bg-gradient-to-r from-indigo-50/40 to-white" data-testid="anzsco-master-card">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-lg bg-indigo-600 flex items-center justify-center">
                <Database className="h-6 w-6 text-white" />
              </div>
              <div>
                <h3 className="text-base font-bold text-indigo-900">ANZSCO 4-Digit Master</h3>
                <p className="text-xs text-slate-600">
                  <strong className="text-indigo-700">{summary.anzsco_4digit_master.total_codes.toLocaleString()}</strong> codes loaded ·
                  Source: <span className="font-mono">{summary.anzsco_4digit_master.data_source}</span>
                </p>
                <a href="https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:underline flex items-center gap-1 mt-0.5">
                  <ExternalLink className="h-3 w-3" />jobsandskills.gov.au
                </a>
              </div>
            </div>
            <Button
              onClick={reimportExcel}
              disabled={importing}
              className="bg-indigo-600 hover:bg-indigo-700"
              data-testid="reimport-excel-btn"
            >
              {importing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              {importing ? 'Importing…' : 'Re-import Excel'}
            </Button>
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
                Occupations ({pending_lists.occupations.length})
              </TabsTrigger>
              <TabsTrigger value="templates" data-testid="tab-templates">
                Country Templates ({pending_lists.country_templates.length})
              </TabsTrigger>
              <TabsTrigger value="guides" data-testid="tab-guides">
                Country Guides ({pending_lists.country_guides.length})
              </TabsTrigger>
              <TabsTrigger value="policies" data-testid="tab-policies">
                Protection Policies ({pending_lists.protection_policies.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="occupations" className="pt-3">
              <PendingList
                items={pending_lists.occupations}
                emptyMessage="All occupations verified ✓"
                renderItem={(it) => ({
                  primary: `${it.code} · ${it.title}`,
                  secondary: it.country_code ? `Country: ${it.country_code}` : '—',
                  status: it.status,
                  link: `/admin/kb/occupation-master?focus=${it.occupation_id || it.code}`,
                })}
              />
            </TabsContent>
            <TabsContent value="templates" className="pt-3">
              <PendingList
                items={pending_lists.country_templates}
                emptyMessage="All country templates verified ✓"
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
                emptyMessage="All country guides verified ✓"
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
                emptyMessage="All policies verified ✓ · or none created yet"
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
