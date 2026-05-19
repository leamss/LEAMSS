/**
 * Phase 6.7 Part 2 — Pre-Analysis Verification Page
 *
 * Route: /eligibility/profile/:profileId/verify
 *
 * Shows profile completeness (per-section scores + warnings/blockers) so the
 * user can review BEFORE running the AI analysis. Click "Confirm and Run" →
 * navigates to the existing /assess runner.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  ArrowLeft, Sparkles, CheckCircle2, AlertTriangle, AlertCircle, Loader2, Pencil, Zap, ChevronRight,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function EligibilityProfileVerify() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [profile, setProfile] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [p, c] = await Promise.all([
          axios.get(`${API}/eligibility/profiles/${profileId}`, { headers }),
          axios.get(`${API}/eligibility/profiles/${profileId}/completeness`, { headers }),
        ]);
        if (!mounted) return;
        setProfile(p.data);
        setCompleteness(c.data);
      } catch (e) {
        toast.error(formatApiError(e, 'Failed to load verification data'));
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading verification…
      </div>
    );
  }
  if (!completeness || !profile) return null;

  const score = completeness.score || 0;
  const blockers = completeness.blockers || [];
  const sections = completeness.sections || [];
  const ready = completeness.ready_for_assessment;

  const scoreColor =
    score >= 80 ? 'text-emerald-600 border-emerald-500'
    : score >= 60 ? 'text-amber-600 border-amber-500'
    : 'text-rose-600 border-rose-500';

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="profile-verify-page">
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(`/eligibility/profile/${profileId}/edit`)}>
              <ArrowLeft className="h-4 w-4 mr-1" />Edit Profile
            </Button>
            <div>
              <h1 className="text-xl font-bold">
                <Sparkles className="inline h-5 w-5 text-indigo-600 mr-1" />
                Pre-Analysis Verification · {profile.name}
              </h1>
              <p className="text-[11px] text-slate-500">{profileId} · Review the profile completeness before running the AI analysis</p>
            </div>
          </div>
        </div>

        {/* Overall Score Hero */}
        <Card className={`p-6 border-l-4 ${scoreColor} bg-gradient-to-br from-white to-slate-50`} data-testid="completeness-score-hero">
          <div className="flex items-center gap-6">
            <div className={`text-6xl font-bold ${scoreColor.split(' ')[0]}`} data-testid="completeness-score">{score}<span className="text-2xl text-slate-400">/100</span></div>
            <div className="flex-1">
              <h2 className="text-lg font-bold">Profile Completeness</h2>
              <p className="text-sm text-slate-600 mt-1">
                {score >= 80 ? 'Excellent — profile is thorough and ready for high-quality AI analysis.'
                  : score >= 60 ? 'Good — analysis will run, but adding the highlighted missing fields will improve accuracy.'
                  : score >= 40 ? 'Partial — analysis can run but quality will be limited. Please review the missing fields below.'
                  : 'Insufficient — please complete more sections before running the analysis.'}
              </p>
              {ready ? (
                <Badge className="mt-3 bg-emerald-100 text-emerald-700"><CheckCircle2 className="h-3 w-3 mr-1" />Ready for AI Analysis</Badge>
              ) : (
                <Badge className="mt-3 bg-rose-100 text-rose-700"><AlertCircle className="h-3 w-3 mr-1" />Blockers present — please fix before running</Badge>
              )}
            </div>
          </div>
        </Card>

        {/* Blockers (if any) */}
        {blockers.length > 0 && (
          <Card className="p-4 bg-rose-50 border-l-4 border-l-rose-500" data-testid="blockers-card">
            <h3 className="text-sm font-bold text-rose-900 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />Critical Issues ({blockers.length})
            </h3>
            <ul className="mt-2 text-xs space-y-1">
              {blockers.map((b, i) => <li key={i} className="text-rose-700">✗ {b}</li>)}
            </ul>
          </Card>
        )}

        {/* Section grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="completeness-sections">
          {sections.map(sec => (
            <Card key={sec.key} className="p-4" data-testid={`section-${sec.key}`}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-bold">{sec.label}</p>
                  <p className="text-[10px] text-slate-500">Weight: {sec.weight}%</p>
                </div>
                <Badge className={
                  sec.score >= 80 ? 'bg-emerald-100 text-emerald-700'
                  : sec.score >= 50 ? 'bg-amber-100 text-amber-700'
                  : 'bg-rose-100 text-rose-700'
                }>{sec.score}/100</Badge>
              </div>
              <Progress value={sec.score} className="h-1.5 mb-2" />
              {sec.warnings.length === 0 ? (
                <p className="text-[11px] text-emerald-600 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" />Complete</p>
              ) : (
                <ul className="text-[11px] text-slate-600 space-y-0.5">
                  {sec.warnings.map((w, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <AlertTriangle className="h-2.5 w-2.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      {w}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>

        {/* Action footer */}
        <Card className="p-4 bg-indigo-50 border-l-4 border-l-indigo-500 flex flex-col md:flex-row items-start md:items-center justify-between gap-3" data-testid="action-footer">
          <div>
            <h3 className="text-sm font-bold text-indigo-900">Ready to proceed?</h3>
            <p className="text-[11px] text-indigo-700 mt-0.5">
              {ready
                ? 'Click below to start the AI analysis. This typically takes 25–35 seconds.'
                : 'Please fix the blockers above before running the analysis.'}
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/eligibility/profile/${profileId}/edit`)}
              data-testid="edit-profile-btn"
            >
              <Pencil className="h-4 w-4 mr-1" />Edit Profile
            </Button>
            <Button
              size="sm"
              className="bg-indigo-600 hover:bg-indigo-700"
              disabled={!ready}
              onClick={() => navigate(`/eligibility/profile/${profileId}/assess`)}
              data-testid="confirm-and-run-btn"
            >
              <Zap className="h-4 w-4 mr-1" />Confirm and Run AI Analysis<ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
