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

const BACKEND_URL = (() => {
  if (typeof window === 'undefined') return process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
  const h = window.location.hostname;
  if (h.includes('leamss.com')) return 'https://api.leamss.com';
  if (h !== 'localhost' && h !== '127.0.0.1') return `${window.location.protocol}//${h}:8001`;
  return process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
})();
const API = `${BACKEND_URL}/api`;

export default function PublicReportView() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

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

  const handleDownloadPdf = () => {
    const liveApi = (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com'))
      ? 'https://api.leamss.com'
      : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001');
    const pdfUrl = `${liveApi}/api/assessment-reports/public/${token}/pdf`;
    window.location.href = pdfUrl;
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-between" data-testid="public-report-view">
      {/* Header banner */}
      <header className="bg-blue-900 text-white p-4 shadow">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">LEAMSS</h1>
            <p className="text-[10px] text-amber-300">We Value Emotions</p>
            <p className="text-[10px] text-blue-200">Ladhani Education &amp; Migration Services Pvt. Ltd.</p>
          </div>
          <Badge className="bg-emerald-600 text-white text-xs">
            <ShieldCheck className="h-3.5 w-3.5 mr-1 inline" />Verified Snapshot
          </Badge>
        </div>
      </header>

      <div className="max-w-4xl mx-auto w-full p-4 space-y-4 my-4 flex-1">
        {/* Title card */}
        <Card className="p-6 border-l-4 border-l-amber-500 shadow-sm">
          <p className="text-[10px] uppercase font-bold text-slate-400">
            Report Reference: {meta?.snapshot_id || meta?.assessment_id}
          </p>
          <h2 className="text-2xl font-bold text-slate-900 mt-1">
            Assessment Report for {meta?.client_name || 'Client'}
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Generated on {new Date(meta?.created_at).toLocaleString()}
          </p>
        </Card>

        {/* Top outcome summary */}
        {best && (
          <Card className="p-6 bg-white border-slate-200">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Top Recommendation</p>
                <div className="flex items-center gap-2 mt-1">
                  <Trophy className="h-6 w-6 text-amber-500" />
                  <h3 className="text-xl font-bold text-slate-900">
                    {best.country_code} {best.country_name}
                  </h3>
                </div>
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
                Visa Pathways · Points Breakdown · Cost &amp; Process · Indicative Checklist · Disclaimer).
              </p>
            </div>
            <Button
              size="lg"
              className="bg-blue-800 hover:bg-blue-900 text-white"
              onClick={handleDownloadPdf}
              disabled={downloading}
              data-testid="download-pdf-btn"
            >
              {downloading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
              {downloading ? 'Downloading…' : 'Download PDF'}
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
        © Ladhani Education &amp; Migration Services Pvt. Ltd. · We Value Emotions
      </footer>
    </div>
  );
}
