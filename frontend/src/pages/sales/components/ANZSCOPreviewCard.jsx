/**
 * Phase 7.2 — ANZSCO 4-digit KB Profile Preview
 *
 * Sir's complaint: "Code select kiya, task description blank PDF mein"
 *
 * When user selects an ANZSCO 6-digit code in the wizard, this component
 * fetches the 4-digit parent profile (1,236 codes from ABS Feb 2026)
 * and shows a compact preview: salary, demographics, top industries, top states.
 *
 * Used by: Step3Profile, Step4Countries (and downstream Phase 7.3 PDF renderer).
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, DollarSign, Users, MapPin, Briefcase, GraduationCap, TrendingUp, Database } from 'lucide-react';
import { API } from '../lib/constants';

export default function ANZSCOPreviewCard({ code, occupationTitle, headers }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!code || code.length < 4) return;
    const parentCode = code.slice(0, 4);
    setLoading(true);
    setError(null);
    axios.get(`${API}/kb-unified/anzsco/${parentCode}`, { headers })
      .then(r => setProfile(r.data))
      .catch(e => setError(e.response?.status === 404 ? 'not-found' : 'error'))
      .finally(() => setLoading(false));
  }, [code, headers]);

  if (!code) return null;

  if (loading) {
    return (
      <Card className="p-3 bg-slate-50 flex items-center gap-2 text-xs text-slate-500" data-testid="anzsco-preview-loading">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />Loading ANZSCO 4-digit profile…
      </Card>
    );
  }

  if (error === 'not-found') {
    return (
      <Card className="p-3 bg-amber-50 border-l-4 border-l-amber-400 text-xs text-amber-800" data-testid="anzsco-preview-missing">
        <strong>ANZSCO 4-digit profile not in KB yet.</strong> Admin can import Feb 2026 ABS data
        via <a href="/admin/verify-hub" className="underline">Verification Hub</a>.
      </Card>
    );
  }

  if (!profile) return null;

  const ap = profile.anzsco_profile || {};
  const topStates = Object.entries(profile.state_distribution || {})
    .filter(([, v]) => v != null)
    .sort((a, b) => (b[1] || 0) - (a[1] || 0))
    .slice(0, 4);
  const topIndustries = (profile.industries_ranked || []).slice(0, 3);
  const topEducation = Object.entries(profile.education_distribution || {})
    .filter(([, v]) => v != null)
    .sort((a, b) => (b[1] || 0) - (a[1] || 0))
    .slice(0, 3);

  return (
    <Card className="p-4 bg-gradient-to-br from-leamss-teal-50/50 via-white to-blue-50/30 border-l-4 border-l-leamss-teal-500" data-testid="anzsco-preview-card">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div>
          <p className="text-[10px] uppercase font-bold tracking-wider text-leamss-teal-700 flex items-center gap-1">
            <Database className="h-3 w-3" />ANZSCO 4-digit Profile · {profile.code}
          </p>
          <p className="text-sm font-bold text-slate-800">{profile.title}</p>
        </div>
        <Badge className="bg-leamss-teal-100 text-leamss-teal-700 text-[9px]">ABS Feb 2026 · KB Verified</Badge>
      </div>

      {profile.description && (
        <p className="text-[11px] text-slate-600 italic mb-3 line-clamp-2">{profile.description}</p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3" data-testid="anzsco-stats-grid">
        <Stat
          icon={DollarSign}
          label="Median Weekly"
          value={ap.median_weekly_earnings_aud ? `AUD ${ap.median_weekly_earnings_aud.toLocaleString()}` : '—'}
          color="emerald"
        />
        <Stat
          icon={Users}
          label="Employed"
          value={ap.employed_count ? `${(ap.employed_count / 1000).toFixed(0)}k` : '—'}
          color="blue"
        />
        <Stat
          icon={TrendingUp}
          label="Median Age"
          value={ap.median_age || '—'}
          color="amber"
        />
        <Stat
          icon={Users}
          label="Female %"
          value={ap.female_share_pct ? `${ap.female_share_pct}%` : '—'}
          color="violet"
        />
      </div>

      {topStates.length > 0 && (
        <div className="mb-3" data-testid="anzsco-top-states">
          <p className="text-[10px] uppercase font-bold text-slate-600 flex items-center gap-1 mb-1">
            <MapPin className="h-3 w-3" />Top States (by employment share)
          </p>
          <div className="flex flex-wrap gap-1">
            {topStates.map(([s, v]) => (
              <Badge key={s} className="bg-blue-100 text-blue-800 text-[10px]">
                {s} {v}%
              </Badge>
            ))}
          </div>
        </div>
      )}

      {topIndustries.length > 0 && (
        <div className="mb-3" data-testid="anzsco-top-industries">
          <p className="text-[10px] uppercase font-bold text-slate-600 flex items-center gap-1 mb-1">
            <Briefcase className="h-3 w-3" />Top Industries
          </p>
          <ul className="text-[11px] text-slate-700 list-decimal list-inside">
            {topIndustries.map((ind, i) => <li key={i}>{ind}</li>)}
          </ul>
        </div>
      )}

      {topEducation.length > 0 && (
        <div className="mb-2" data-testid="anzsco-top-education">
          <p className="text-[10px] uppercase font-bold text-slate-600 flex items-center gap-1 mb-1">
            <GraduationCap className="h-3 w-3" />Education Profile
          </p>
          <div className="flex flex-wrap gap-1">
            {topEducation.map(([k, v]) => (
              <Badge key={k} className="bg-leamss-red-100 text-leamss-red-800 text-[10px]">
                {k.replace(/_/g, ' ')} {v}%
              </Badge>
            ))}
          </div>
        </div>
      )}

      {(profile.tasks || []).length > 0 && (
        <details className="mt-3" data-testid="anzsco-tasks">
          <summary className="text-[10px] uppercase font-bold text-slate-600 cursor-pointer hover:text-slate-800">
            📋 Tasks ({profile.tasks.length}) — click to expand
          </summary>
          <ul className="text-[11px] text-slate-700 mt-2 space-y-1 list-disc list-inside pl-2">
            {profile.tasks.slice(0, 8).map((t, i) => <li key={i}>{t}</li>)}
            {profile.tasks.length > 8 && (
              <li className="text-slate-400 italic">…and {profile.tasks.length - 8} more</li>
            )}
          </ul>
        </details>
      )}

      <p className="text-[9px] text-slate-400 mt-3 font-mono">
        Source: {profile.data_source?.label || 'ABS ANZSCO'}
      </p>
    </Card>
  );
}

function Stat({ icon: Icon, label, value, color }) {
  const colorClass = {
    emerald: 'text-emerald-600 bg-emerald-50',
    blue: 'text-blue-600 bg-blue-50',
    amber: 'text-amber-600 bg-amber-50',
    violet: 'text-leamss-red-600 bg-leamss-red-50',
  }[color] || 'text-slate-600 bg-slate-50';
  return (
    <div className="rounded p-2 bg-white border" data-testid={`stat-${label.replace(/\s+/g, '-').toLowerCase()}`}>
      <div className={`inline-flex items-center justify-center w-6 h-6 rounded ${colorClass}`}>
        <Icon className="h-3 w-3" />
      </div>
      <p className="text-[9px] uppercase text-slate-500 mt-1">{label}</p>
      <p className="text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}
