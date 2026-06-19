/**
 * Phase 19.9 + 19.9.1 — Authority Health Card widget.
 *
 * 4-tile layout: TBD Bucket · Draft Bodies · Placeholder Fees · Last Authority Edit
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Sparkles, Shield, AlertTriangle, Loader2, Clock, History } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { AuthorityEditTimeline } from './AuthorityEditTimeline';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token')}` };
}

function relTime(iso) {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function AuthorityHealthCard() {
  const navigate = useNavigate();
  const [coverage, setCoverage] = useState(null);
  const [authStats, setAuthStats] = useState(null);
  const [recentEdit, setRecentEdit] = useState(null);
  const [enriching, setEnriching] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cov, list, audit] = await Promise.all([
        axios.get(`${API}/enrichment/coverage?country_code=AU`, { headers: authHeaders() }),
        axios.get(`${API}/assessing-authorities?country=AU&include_drafts=true`, { headers: authHeaders() }),
        axios.get(`${API}/assessing-authorities/audit-trail/recent?limit=1`, { headers: authHeaders() }),
      ]);
      setCoverage(cov.data);
      const items = list.data.items || [];
      setAuthStats({
        total: items.length,
        active: items.filter(b => b.status === 'active').length,
        draft: items.filter(b => b.status === 'draft').length,
        placeholder: items.filter(b => b._seed_quality === 'placeholder').length,
      });
      setRecentEdit({
        at: audit.data.latest_at,
        action: audit.data.latest_action,
        summary: audit.data.latest_summary,
      });
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!coverage || !authStats) return null;

  const tbdCount = (coverage.total || 0) - (coverage.per_field?.assessing_authority_id?.filled || 0);

  const runEnrich = async () => {
    if (!window.confirm(`Run bulk enrichment for AU? Idempotent — safe to re-run. Revocable 24h.`)) return;
    setEnriching(true);
    try {
      const r = await axios.post(`${API}/enrichment/run`, { country_code: 'AU', dry_run: false }, { headers: authHeaders() });
      toast.success(`Enrichment ran · ${r.data.occupations_with_changes}/${r.data.total_occupations} updated · batch ${r.data.batch_id}`);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Enrichment failed');
    } finally { setEnriching(false); }
  };

  return (
    <>
      <Card className="p-4 border-l-4 border-l-leamss-teal bg-leamss-teal_50/30" data-testid="authority-health-card">
        <h3 className="text-sm font-bold text-leamss-teal flex items-center gap-2 mb-3">
          <Shield className="h-4 w-4" />Authority Health Card
          <span className="text-xs font-normal text-slate-500">(Phase 19.9 + 19.9.1)</span>
        </h3>
        <div className="grid grid-cols-4 gap-3">
          {/* TBD bucket */}
          <div className="bg-white rounded p-3 border border-amber-200">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">TBD Bucket</p>
            <p className="text-2xl font-bold text-amber-700 mt-1" data-testid="health-tbd-count">{tbdCount}</p>
            <p className="text-[10px] text-slate-500 mb-2">occupations need authority FK</p>
            <Button size="sm" onClick={runEnrich} disabled={enriching} className="w-full h-7 text-[10px] bg-amber-600 hover:bg-amber-700" data-testid="health-card-resolve-tbd">
              {enriching ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Sparkles className="h-3 w-3 mr-1" />}
              Bulk Enrich AU
            </Button>
          </div>

          {/* Draft bodies */}
          <div className="bg-white rounded p-3 border border-amber-200">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Draft Bodies</p>
            <p className="text-2xl font-bold text-amber-700 mt-1" data-testid="health-draft-count">{authStats.draft}</p>
            <p className="text-[10px] text-slate-500 mb-2">of {authStats.total} awaiting verification</p>
            <Button size="sm" onClick={() => navigate('/admin/authorities?wizard=true')} className="w-full h-7 text-[10px]" data-testid="health-card-verify-wizard">
              <Shield className="h-3 w-3 mr-1" />Verify Wizard
            </Button>
          </div>

          {/* Placeholder bodies */}
          <div className="bg-white rounded p-3 border border-rose-200">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Placeholder Fees</p>
            <p className="text-2xl font-bold text-rose-700 mt-1" data-testid="health-placeholder-count">{authStats.placeholder}</p>
            <p className="text-[10px] text-slate-500 mb-2">bodies need real fees</p>
            <Button size="sm" variant="outline" onClick={() => navigate('/admin/authorities?status=placeholder')} className="w-full h-7 text-[10px] border-rose-300 text-rose-700" data-testid="health-card-review-placeholder">
              <AlertTriangle className="h-3 w-3 mr-1" />Review Now
            </Button>
          </div>

          {/* Phase 19.9.1 — Last Authority Edit tile */}
          <div className="bg-white rounded p-3 border border-leamss-teal_50" data-testid="health-last-edit-tile">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Last Authority Edit</p>
            <p className="text-sm font-bold text-leamss-teal mt-1 truncate" data-testid="health-last-edit-action">
              {recentEdit?.action ? recentEdit.action.replace('authority.', '') : 'No edits yet'}
            </p>
            <p className="text-[10px] text-slate-500 mb-2" data-testid="health-last-edit-time">
              {recentEdit?.at ? (
                <>
                  {relTime(recentEdit.at)} · <span className="font-mono">{recentEdit.summary?.code || ''}</span>
                </>
              ) : '—'}
            </p>
            <Button size="sm" variant="outline" onClick={() => setTimelineOpen(true)} className="w-full h-7 text-[10px] border-leamss-teal_50 text-leamss-teal" data-testid="health-show-diff-trail">
              <History className="h-3 w-3 mr-1" />Show Diff Trail
            </Button>
          </div>
        </div>
      </Card>
      <AuthorityEditTimeline open={timelineOpen} onClose={() => setTimelineOpen(false)} />
    </>
  );
}

export default AuthorityHealthCard;
