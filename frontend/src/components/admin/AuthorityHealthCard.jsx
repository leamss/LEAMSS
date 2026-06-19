/**
 * Phase 19.9 — Authority Health Card widget.
 *
 * Mounted on Verification Hub. Shows:
 *   - TBD bucket count + 1-click enrichment trigger
 *   - Draft bodies count + Verify Wizard link
 *   - Placeholder bodies count + review link
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Sparkles, Shield, AlertTriangle, Loader2 } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token')}` };
}

export function AuthorityHealthCard() {
  const navigate = useNavigate();
  const [coverage, setCoverage] = useState(null);
  const [authStats, setAuthStats] = useState(null);
  const [enriching, setEnriching] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cov, list] = await Promise.all([
        axios.get(`${API}/enrichment/coverage?country_code=AU`, { headers: authHeaders() }),
        axios.get(`${API}/assessing-authorities?country=AU&include_drafts=true`, { headers: authHeaders() }),
      ]);
      setCoverage(cov.data);
      const items = list.data.items || [];
      setAuthStats({
        total: items.length,
        active: items.filter(b => b.status === 'active').length,
        draft: items.filter(b => b.status === 'draft').length,
        placeholder: items.filter(b => b._seed_quality === 'placeholder').length,
      });
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!coverage || !authStats) return null;

  const tbdCount = (coverage.total || 0) - (coverage.per_field?.assessing_authority_id?.filled || 0);

  const runEnrich = async () => {
    if (!window.confirm(`Run bulk enrichment for AU? This will re-cross-pollinate description, tasks, profile from 4-digit master. Idempotent — safe to re-run. Revocable 24h.`)) return;
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
    <Card className="p-4 border-l-4 border-l-indigo-500 bg-indigo-50/30" data-testid="authority-health-card">
      <h3 className="text-sm font-bold text-indigo-900 flex items-center gap-2 mb-3">
        <Shield className="h-4 w-4" />Authority Health Card <span className="text-xs font-normal text-slate-500">(Phase 19.9)</span>
      </h3>
      <div className="grid grid-cols-3 gap-3">
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
      </div>
    </Card>
  );
}

export default AuthorityHealthCard;
