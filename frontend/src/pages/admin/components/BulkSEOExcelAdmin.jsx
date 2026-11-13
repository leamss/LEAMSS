import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  FileSpreadsheet, Download, Upload, CheckCircle2, AlertCircle,
  Loader2, Search, ExternalLink, Globe2, Sparkles, RefreshCw,
  FileCheck, HelpCircle, Check, Info, ArrowRight,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BulkSEOExcelAdmin({ headers }) {
  const [country, setCountry] = useState('AU');
  const [file, setFile] = useState(null);
  const [publishLive, setPublishLive] = useState(true);
  const [downloading, setDownloading] = useState(null); // 'template' | 'export' | null
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [showGuide, setShowGuide] = useState(false);

  // ─── 1. Download Blank Template or Pre-filled Export ─────────────────────
  const handleDownload = async (mode) => {
    setDownloading(mode);
    try {
      const resp = await axios.get(`${API}/occupation-master/import/seo/template`, {
        params: { country, mode },
        headers,
        responseType: 'blob',
      });
      const blob = new Blob([resp.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LEAMSS_SEO_${country}_${mode}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(
        mode === 'export'
          ? `✓ Downloaded existing ${country} occupations SEO export`
          : `✓ Downloaded blank SEO Excel template for ${country}`
      );
    } catch (e) {
      toast.error(formatApiError(e, 'Download failed'));
    } finally {
      setDownloading(null);
    }
  };

  // ─── 2. Preview File Upload ──────────────────────────────────────────────
  const handlePreview = async () => {
    if (!file) {
      toast.error('Please pick an Excel or CSV file first');
      return;
    }
    setLoading(true);
    setCommitResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('country_code', country);
      const resp = await axios.post(`${API}/occupation-master/import/seo/preview`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setPreview(resp.data);
      if (resp.data.ok) {
        toast.success(`Parsed ${resp.data.total_rows} rows (${resp.data.matched_count} matched in DB)`);
      }
    } catch (e) {
      toast.error(formatApiError(e, 'Preview failed'));
      setPreview(null);
    } finally {
      setLoading(false);
    }
  };

  // ─── 3. Commit SEO Updates to DB & Live Public Atlas ────────────────────
  const handleCommit = async () => {
    if (!file || !preview?.ok) return;
    setCommitting(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('country_code', country);
      fd.append('publish_live', String(publishLive));
      const resp = await axios.post(`${API}/occupation-master/import/seo/commit`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setCommitResult(resp.data);
      toast.success(`✓ Updated SEO for ${resp.data.updated_count} occupations!`, {
        description: publishLive
          ? `${resp.data.live_rebuilt_count} live public atlas pages rebuilt immediately.`
          : 'Saved changes as updated draft in database.',
      });
    } catch (e) {
      toast.error(formatApiError(e, 'Bulk commit failed'));
    } finally {
      setCommitting(false);
    }
  };

  const countries = [
    { code: 'AU', label: '🇦🇺 Australia', subtitle: 'ANZSCO 2013 / OSCA' },
    { code: 'CA', label: '🇨🇦 Canada', subtitle: 'NOC 2021 (TEER)' },
    { code: 'NZ', label: '🇳🇿 New Zealand', subtitle: 'ANZSCO v1.3 Green List' },
    { code: 'ALL', label: '🌐 All Countries', subtitle: 'Global Multi-Country' },
  ];

  return (
    <div className="space-y-5 max-w-5xl mx-auto pb-12" data-testid="bulk-seo-excel-admin">
      {/* ── Header Banner ── */}
      <div className="rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-50 via-teal-50 to-white p-5 shadow-xs">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-700 text-white flex items-center justify-center shadow-sm shrink-0">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-extrabold text-slate-900">Bulk SEO Attributes Manager (Excel / CSV)</h2>
                <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 text-[10px] font-bold">
                  Code-Wise &amp; Page-Wise
                </Badge>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Upload SEO attributes (Meta Title, Description, Keywords, Social Cards &amp; Schema) code-wise in bulk and update live on Public Atlas pages.
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowGuide(!showGuide)}
            className="text-xs border-emerald-300 text-emerald-900 hover:bg-emerald-100/60 font-semibold h-8"
          >
            <HelpCircle className="w-3.5 h-3.5 mr-1 text-emerald-700" />
            {showGuide ? 'Hide Guidelines' : 'SEO Columns & Guidelines'}
          </Button>
        </div>

        {/* Expandable Guidelines Box */}
        {showGuide && (
          <div className="mt-4 pt-4 border-t border-emerald-200 text-xs text-slate-700 space-y-2 bg-white/70 p-3.5 rounded-lg border">
            <p className="font-bold text-slate-900">📋 Recommended Columns &amp; Best Practices:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              <div><strong>Code:</strong> Mandatory ANZSCO/NOC code (e.g. <code>261313</code> or <code>21231</code>)</div>
              <div><strong>Country:</strong> <code>AU</code>, <code>CA</code>, or <code>NZ</code></div>
              <div><strong>Meta_Title:</strong> 50–60 chars (e.g. <em>Software Engineer (261313) — Australia PR Guide \| LEAMSS</em>)</div>
              <div><strong>Meta_Description:</strong> 140–160 chars summary for Google Search result snippets</div>
              <div><strong>Keywords:</strong> Comma-separated search terms and visa subclasses</div>
              <div><strong>Focus_Keyword:</strong> Primary keyword target (e.g. <em>Software Engineer Australia PR</em>)</div>
              <div><strong>OG_Title / OG_Description:</strong> Rich card previews when shared on LinkedIn, WhatsApp, X</div>
              <div><strong>Meta_Robots:</strong> <code>index, follow, max-image-preview:large, max-snippet:-1</code></div>
            </div>
          </div>
        )}
      </div>

      {/* ── Step 1: Select Country & Download Templates ── */}
      <Card className="p-5 border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">1</span>
            <h3 className="text-sm font-bold text-slate-900">Select Country &amp; Download Excel Template</h3>
          </div>
          <span className="text-[11px] text-slate-400">Step 1 of 3</span>
        </div>

        {/* Country Selector Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {countries.map((c) => (
            <button
              key={c.code}
              type="button"
              onClick={() => setCountry(c.code)}
              className={`p-3 rounded-lg border text-left transition-all ${
                country === c.code
                  ? 'bg-emerald-50/90 border-emerald-600 ring-2 ring-emerald-500/20 shadow-xs'
                  : 'bg-white border-slate-200 hover:bg-slate-50'
              }`}
            >
              <span className={`text-xs font-bold block ${country === c.code ? 'text-emerald-950' : 'text-slate-800'}`}>
                {c.label}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">{c.subtitle}</span>
            </button>
          ))}
        </div>

        {/* Template Download Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          {/* Option A: Blank Template */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                <h4 className="text-xs font-bold text-slate-900">Blank SEO Excel Template</h4>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                Formatted Excel spreadsheet with all 16 SEO columns pre-styled with column headers and 3 sample rows.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleDownload('template')}
              disabled={downloading !== null}
              className="text-xs border-emerald-600 text-emerald-900 hover:bg-emerald-50 font-bold h-9 w-full shadow-2xs"
            >
              {downloading === 'template' ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1.5" />}
              Download Blank Template (.xlsx)
            </Button>
          </div>

          {/* Option B: Pre-Filled Export for Editing */}
          <div className="p-4 rounded-xl border border-teal-200 bg-teal-50/40 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-teal-700" />
                <h4 className="text-xs font-bold text-slate-900">Export Existing Occupations for Editing</h4>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                Downloads all verified occupations for <strong>{country}</strong> with their current titles and SEO metadata pre-filled. Edit in Excel and re-upload!
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              onClick={() => handleDownload('export')}
              disabled={downloading !== null}
              className="text-xs bg-teal-700 hover:bg-teal-800 text-white font-bold h-9 w-full shadow-xs"
            >
              {downloading === 'export' ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1.5" />}
              Export &amp; Edit Existing Occupations (.xlsx)
            </Button>
          </div>
        </div>
      </Card>

      {/* ── Step 2: Upload File & Preview ── */}
      <Card className="p-5 border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">2</span>
            <h3 className="text-sm font-bold text-slate-900">Upload Filled Excel / CSV File</h3>
          </div>
          <span className="text-[11px] text-slate-400">Step 2 of 3</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div className="md:col-span-2 space-y-1">
            <label className="text-xs font-bold text-slate-700 block">
              Choose Excel or CSV File (.xlsx, .xls, .csv)
            </label>
            <Input
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setPreview(null);
                setCommitResult(null);
              }}
              className="h-10 text-xs bg-white file:text-xs file:font-bold file:bg-slate-100 file:border-0 file:rounded file:px-2.5 file:py-1 file:mr-2"
            />
            {file && (
              <p className="text-[11px] text-emerald-800 font-medium">
                Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div>
            <Button
              type="button"
              onClick={handlePreview}
              disabled={!file || loading}
              className="w-full h-10 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs shadow-xs"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Search className="w-3.5 h-3.5 mr-1.5" />}
              Preview SEO Changes
            </Button>
          </div>
        </div>

        {/* Live Publish Toggle */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2">
          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-800">
            <input
              type="checkbox"
              checked={publishLive}
              onChange={(e) => setPublishLive(e.target.checked)}
              className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 cursor-pointer"
            />
            <span>🚀 Publish Live Immediately (Rebuilds live public atlas HTML pages upon commit)</span>
          </label>
          <span className="text-[11px] text-slate-500 italic">Recommended: keeps public website 100% in sync</span>
        </div>
      </Card>

      {/* ── Step 3: Preview Results & Diff Table ── */}
      {preview && (
        <Card className="p-5 border-slate-200 shadow-xs space-y-4" data-testid="seo-preview-card">
          <div className="flex items-center justify-between border-b pb-3 flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-emerald-700 text-white text-xs font-bold flex items-center justify-center">3</span>
                <h3 className="text-sm font-bold text-slate-900">Review Changes ({preview.total_rows} Rows Detected)</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Verify detected column mappings and matched occupation records before saving to database.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-mono text-xs">
                {preview.matched_count} Matched in DB
              </Badge>
              {preview.not_found_count > 0 && (
                <Badge className="bg-amber-100 text-amber-900 border-amber-300 font-mono text-xs">
                  {preview.not_found_count} Not Found
                </Badge>
              )}
            </div>
          </div>

          {/* Missing Codes Warning Alert */}
          {preview.not_found_count > 0 && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong>{preview.not_found_count} codes</strong> in your file do not match an existing occupation in the database:
                <p className="font-mono text-[11px] mt-1 text-amber-900 bg-amber-100/70 p-1.5 rounded">
                  {preview.not_found_codes.join(', ')}
                  {preview.not_found_count > 20 && ` ...and ${preview.not_found_count - 20} more`}
                </p>
                <p className="text-[11px] mt-1 text-amber-800">
                  These rows will be skipped. Only matched codes will have their SEO attributes updated.
                </p>
              </div>
            </div>
          )}

          {/* Sample Rows Table */}
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Row</th>
                  <th className="py-2.5 px-3">Country &amp; Code</th>
                  <th className="py-2.5 px-3">Title</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">New Meta Title</th>
                  <th className="py-2.5 px-3">New Meta Description</th>
                  <th className="py-2.5 px-3">Focus Keyword</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {preview.sample_rows.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50/70">
                    <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">{r.row_index}</td>
                    <td className="py-2 px-3 font-mono font-bold text-slate-900">
                      {r.country} · {r.code}
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-800 max-w-[140px] truncate" title={r.title}>
                      {r.title}
                    </td>
                    <td className="py-2 px-3">
                      {r.status === 'matched' ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono">
                          <Check className="w-3 h-3" /> Matched
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-mono">
                          Not Found
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-slate-700 max-w-[200px] truncate" title={r.new_meta_title}>
                      {r.new_meta_title}
                    </td>
                    <td className="py-2 px-3 text-slate-500 max-w-[240px] truncate text-[11px]" title={r.new_meta_description}>
                      {r.new_meta_description}
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px] text-teal-800">
                      {r.focus_keyword || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {preview.total_rows > 30 && (
            <p className="text-[11px] text-slate-400 text-center italic">
              Showing first 30 of {preview.total_rows} rows previewed. All matched rows will be committed.
            </p>
          )}

          {/* Commit Button Bar */}
          <div className="pt-3 border-t border-slate-200 flex items-center justify-between flex-wrap gap-3">
            <span className="text-xs text-slate-600 font-medium">
              Ready to commit {preview.matched_count} verified updates to live?
            </span>
            <Button
              type="button"
              onClick={handleCommit}
              disabled={committing || preview.matched_count === 0}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs h-10 px-6 shadow-md"
              data-testid="seo-commit-btn"
            >
              {committing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
              {publishLive ? 'Confirm & Update Live Public Pages' : 'Save SEO Drafts in Database'}
            </Button>
          </div>
        </Card>
      )}

      {/* ── Step 4: Success Results Card ── */}
      {commitResult && (
        <Card className="p-5 border-emerald-300 bg-emerald-50/50 shadow-sm space-y-3" data-testid="seo-commit-result">
          <div className="flex items-center gap-2.5 text-emerald-950">
            <div className="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold">
              ✓
            </div>
            <div>
              <h3 className="text-sm font-extrabold">SEO Attributes Updated Successfully!</h3>
              <p className="text-xs text-emerald-800">
                All matched records in the database have been updated with your new SEO meta attributes.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
            <div className="p-3 bg-white rounded-lg border border-emerald-200 text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Total In File</span>
              <span className="text-lg font-black text-slate-900 mt-0.5 block">{commitResult.total_rows}</span>
            </div>
            <div className="p-3 bg-white rounded-lg border border-emerald-200 text-center">
              <span className="text-[10px] uppercase font-bold text-emerald-700 block">Updated In DB</span>
              <span className="text-lg font-black text-emerald-700 mt-0.5 block">{commitResult.updated_count}</span>
            </div>
            <div className="p-3 bg-white rounded-lg border border-emerald-200 text-center">
              <span className="text-[10px] uppercase font-bold text-teal-700 block">Live Rebuilt</span>
              <span className="text-lg font-black text-teal-800 mt-0.5 block">{commitResult.live_rebuilt_count}</span>
            </div>
            <div className="p-3 bg-white rounded-lg border border-emerald-200 text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Skipped / Missing</span>
              <span className="text-lg font-black text-slate-500 mt-0.5 block">{commitResult.skipped_count}</span>
            </div>
          </div>

          {commitResult.errors && commitResult.errors.length > 0 && (
            <div className="p-3 bg-white rounded-lg border border-amber-200 text-xs text-amber-900 space-y-1">
              <p className="font-bold">⚠️ Notices during live rebuild ({commitResult.errors.length}):</p>
              <ul className="list-disc list-inside text-[11px] text-slate-600 space-y-0.5 max-h-28 overflow-y-auto">
                {commitResult.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setFile(null);
                setPreview(null);
                setCommitResult(null);
              }}
              className="text-xs bg-white text-emerald-900 border-emerald-300 hover:bg-emerald-100 font-semibold h-8"
            >
              Upload Another File
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
