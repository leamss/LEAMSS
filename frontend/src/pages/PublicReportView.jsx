/**
 * Phase 6.10 Part 2 — Public Report View
 *
 * Route: /reports/view/:token
 * No login required. Renders a branded preview + Download PDF.
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, Loader2, ShieldCheck, AlertCircle, Trophy, Globe2, Mail } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicReportView() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/assessment-reports/public/${token}`)
      .then(r => setMeta(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Could not load report'))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400" data-testid="report-loading">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading your report…
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6" data-testid="report-error">
        <Card className="max-w-md w-full p-8 text-center">
          <AlertCircle className="h-12 w-12 mx-auto mb-3 text-rose-500" />
          <h2 className="text-base font-bold">{error}</h2>
          <p className="text-xs text-slate-500 mt-1">
            If you believe this is an error, please contact LEAMSS at rohit@leamss.com
          </p>
        </Card>
      </div>
    );
  }

  const best = meta?.best_country || {};

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-blue-50" data-testid="public-report-view">
      {/* Brand banner */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-800 text-white p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-3xl font-bold">LEAMSS</h1>
              <p className="text-xs text-amber-300 italic">{meta?.tagline || 'We Value Emotions'}</p>
              <p className="text-[10px] text-blue-200 mt-1">{meta?.company}</p>
            </div>
            <div className="text-right">
              <Badge className="bg-amber-500 text-white text-[10px]">
                <ShieldCheck className="h-3 w-3 mr-1" />Verified Snapshot
              </Badge>
              <p className="text-[10px] text-blue-200 mt-1 font-mono">
                {meta?.snapshot_id}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6 space-y-4">
        {/* Title */}
        <Card className="p-6 border-l-4 border-l-amber-500" data-testid="report-title">
          <h2 className="text-2xl font-bold text-slate-900">
            Assessment Report for <span className="text-blue-800">{meta?.client_name}</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Generated on {meta?.generated_at ? new Date(meta.generated_at).toLocaleString() : '—'}
          </p>
        </Card>

        {/* Best country */}
        {best?.country_name && (
          <Card className="p-5" data-testid="best-country">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-500">Top Recommendation</p>
                <h3 className="text-2xl font-bold flex items-center gap-2 mt-1">
                  <Trophy className="h-7 w-7 text-amber-500" />
                  {best.flag} {best.country_name}
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {meta?.countries_count} country option{meta?.countries_count !== 1 ? 's' : ''} included
                </p>
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase font-bold text-slate-500">Indicative Score</p>
                <p className="text-5xl font-bold text-blue-800">{best.total}</p>
                <p className="text-xs text-slate-600">pass mark {best.pass_mark}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Download CTA */}
        <Card className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-base font-bold flex items-center gap-2">
                <Globe2 className="h-5 w-5 text-amber-700" />Full Branded Report
              </h3>
              <p className="text-xs text-slate-600 mt-1">
                Download the complete professional PDF with all sections (Cover · Client Profile · Per-Country Details ·
                Visa Pathways · Points Breakdown · Cost & Process · Indicative Checklist · Disclaimer).
              </p>
            </div>
            <Button
              size="lg"
              className="bg-blue-800 hover:bg-blue-900 text-white"
              onClick={() => window.open(`${API}/assessment-reports/public/${token}/pdf`, '_blank')}
              data-testid="download-pdf-btn"
            >
              <Download className="h-4 w-4 mr-2" />Download PDF
            </Button>
          </div>
        </Card>

        {/* Integrity proof */}
        <Card className="p-3 bg-slate-50 border-slate-200">
          <p className="text-[10px] text-slate-500">
            <ShieldCheck className="h-3 w-3 inline mr-1 text-emerald-600" />
            <strong>Tamper-evident integrity hash:</strong> <code className="font-mono">{meta?.integrity_hash?.slice(0, 32)}…</code>
          </p>
          <p className="text-[10px] text-slate-400 mt-0.5">
            This report is a permanent snapshot — its data will not change even if our Knowledge Base is later updated.
          </p>
        </Card>

        {/* Contact */}
        <Card className="p-5 bg-blue-900 text-white">
          <h3 className="text-base font-bold mb-2 flex items-center gap-2">
            <Mail className="h-5 w-5 text-amber-300" />Have questions?
          </h3>
          <p className="text-xs text-blue-100 mb-2">
            Get in touch with your dedicated LEAMSS counsellor:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
            <div><strong>Website:</strong> www.leamss.com</div>
            <div><strong>Email:</strong> rohit@leamss.com</div>
            <div><strong>Phone:</strong> 1800-210-2427</div>
          </div>
        </Card>
      </div>

      <footer className="bg-slate-900 text-slate-400 text-center text-[10px] p-3 mt-6">
        © Ladhani Education & Migration Services Pvt. Ltd. · We Value Emotions
      </footer>
    </div>
  );
}
