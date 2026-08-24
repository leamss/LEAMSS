/**
 * SkillSelect EOI Backlog Admin.
 *
 * The official DHA SkillSelect EOI dashboard has no public API/CSV. Consultants export
 * the "EOI data" spreadsheet from the dashboard and upload it here (monthly). We store it
 * and surface the SUBMITTED (pool) backlog per occupation in the client Assessment Report.
 *
 * Route: /admin/kb/eoi-backlog
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Upload, Loader2, RefreshCw, Database, CalendarDays,
  Search, Users, ExternalLink, Info,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const OFFICIAL_URL = 'https://api.dynamic.reports.employment.gov.au/anonap/extensions/hSKLS02_SkillSelect_EOI_Data/hSKLS02_SkillSelect_EOI_Data.html';

export default function EOIBacklogAdmin() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const [previewCode, setPreviewCode] = useState('');
  const [previewPoints, setPreviewPoints] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/eoi-backlog/status`, { headers });
      setStatus(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load EOI status'));
    } finally { setLoading(false); }
  }, [headers]);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/eoi-backlog/import`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Imported ${r.data.rows_imported.toLocaleString()} rows · ${r.data.distinct_occupations} occupations · ${(r.data.months || []).join(', ')}`);
      await loadStatus();
    } catch (e) {
      toast.error(formatApiError(e, 'Import failed'));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const runPreview = async () => {
    if (!previewCode.trim()) { toast.error('Enter an ANZSCO code'); return; }
    setPreviewing(true); setPreview(null);
    try {
      const params = {};
      if (previewPoints) params.client_points = previewPoints;
      const r = await axios.get(`${API}/eoi-backlog/occupation/${previewCode.trim()}`, { headers, params });
      setPreview(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'No EOI data for this occupation'));
    } finally { setPreviewing(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="eoi-admin-page">
      <div className="max-w-6xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin/kb/occupation-master')} data-testid="eoi-back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Occupation Master
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Database className="h-7 w-7 text-teal-600" />
              SkillSelect EOI Backlog
              <Badge className="bg-teal-600 text-white text-[9px]">Australia</Badge>
            </h1>
            <p className="text-sm text-slate-500">Upload the monthly EOI export · reflected in client Assessment Reports</p>
          </div>
          <Button variant="outline" size="sm" className="ml-auto" onClick={loadStatus} data-testid="eoi-refresh-btn">
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />Refresh
          </Button>
        </div>

        {/* Status */}
        <Card className="p-4" data-testid="eoi-status-card">
          {loading ? (
            <div className="flex items-center gap-2 text-slate-500 text-sm"><Loader2 className="h-4 w-4 animate-spin" />Loading…</div>
          ) : status?.has_data ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Stat icon={<CalendarDays className="h-4 w-4" />} label="As At Month" value={status.latest_month} testid="eoi-stat-month" />
              <Stat icon={<Database className="h-4 w-4" />} label="Total Rows" value={status.total_rows?.toLocaleString()} testid="eoi-stat-rows" />
              <Stat icon={<Users className="h-4 w-4" />} label="Occupations" value={status.distinct_occupations?.toLocaleString()} testid="eoi-stat-occ" />
              <Stat label="189 (SUBMITTED)" value={status.submitted_rows_by_subclass?.['189']?.toLocaleString()} />
              <Stat label="190 / 491 rows" value={`${status.submitted_rows_by_subclass?.['190']?.toLocaleString()} / ${status.submitted_rows_by_subclass?.['491']?.toLocaleString()}`} />
            </div>
          ) : (
            <div className="text-sm text-slate-500" data-testid="eoi-no-data">No EOI data yet. Upload the SkillSelect EOI export below to get started.</div>
          )}
        </Card>

        {/* Upload */}
        <Card className="p-4 space-y-3" data-testid="eoi-upload-card">
          <h2 className="text-base font-bold flex items-center gap-2"><Upload className="h-4 w-4 text-teal-600" />Upload EOI Export (monthly)</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => handleUpload(e.target.files?.[0])}
              disabled={uploading}
              className="text-sm"
              data-testid="eoi-file-input"
            />
            {uploading && <span className="flex items-center gap-1 text-sm text-teal-700"><Loader2 className="h-4 w-4 animate-spin" />Importing… (large files take a few seconds)</span>}
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-[12px] text-amber-900 space-y-1" data-testid="eoi-help">
            <p className="flex items-center gap-1 font-semibold"><Info className="h-3.5 w-3.5" />How to get this file</p>
            <ol className="list-decimal ml-5 space-y-0.5">
              <li>Open the official SkillSelect EOI dashboard and set dimensions to <b>Visa Type, Occupation, EOI Status, Points</b>.</li>
              <li>Export the table (columns: As At Month, Visa Type, Occupation, EOI Status, Points, Count EOIs).</li>
              <li>Upload the .xlsx / .csv here. We keep only the GSM subclasses (189, 190, 491) with an occupation code.</li>
            </ol>
            <a href={OFFICIAL_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-teal-700 underline mt-1" data-testid="eoi-official-link">
              Open official SkillSelect EOI dashboard <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </Card>

        {/* Preview */}
        <Card className="p-4 space-y-3" data-testid="eoi-preview-card">
          <h2 className="text-base font-bold flex items-center gap-2"><Search className="h-4 w-4 text-teal-600" />Preview by Occupation</h2>
          <div className="flex items-end gap-2 flex-wrap">
            <div>
              <Label className="text-xs">ANZSCO Code</Label>
              <Input value={previewCode} onChange={(e) => setPreviewCode(e.target.value)} placeholder="e.g. 261313" className="h-9 w-40" data-testid="eoi-preview-code" />
            </div>
            <div>
              <Label className="text-xs">Client Points (optional)</Label>
              <Input value={previewPoints} onChange={(e) => setPreviewPoints(e.target.value)} placeholder="e.g. 75" type="number" className="h-9 w-40" data-testid="eoi-preview-points" />
            </div>
            <Button onClick={runPreview} disabled={previewing} className="bg-teal-600 hover:bg-teal-700 h-9" data-testid="eoi-preview-btn">
              {previewing ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Preview'}
            </Button>
          </div>

          {preview && (
            <div className="space-y-3" data-testid="eoi-preview-result">
              <p className="text-sm font-semibold">{preview.occupation_code} · {preview.occupation_title}
                <span className="text-xs text-slate-500 font-normal"> · as at {preview.as_at_month}</span>
              </p>
              <div className="overflow-x-auto">
                <table className="text-xs w-full border">
                  <thead className="bg-teal-700 text-white">
                    <tr>
                      <th className="p-1.5 text-left">Points</th>
                      {preview.unified.subclasses.map(sc => <th key={sc} className="p-1.5">{sc}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.unified.rows.map((row) => (
                      <tr key={row.points} className={row.is_client_bracket ? 'bg-amber-100 font-bold' : ''} data-testid={`eoi-preview-row-${row.points}`}>
                        <td className="p-1.5 font-semibold">{row.points}{row.is_client_bracket ? ' ← YOU' : ''}</td>
                        {preview.unified.subclasses.map(sc => (
                          <td key={sc} className="p-1.5 text-center">{row.cells[sc]?.raw ?? '—'}</td>
                        ))}
                      </tr>
                    ))}
                    <tr className="bg-teal-50 font-bold border-t-2 border-teal-600">
                      <td className="p-1.5">Total in pool</td>
                      {preview.subclasses.map(s => (
                        <td key={s.subclass} className="p-1.5 text-center">{s.total.toLocaleString()}{s.total_suppressed ? '+' : ''}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Stat({ icon, label, value, testid }) {
  return (
    <div className="bg-slate-50 rounded p-2.5" data-testid={testid}>
      <p className="text-[10px] uppercase tracking-wide text-slate-500 flex items-center gap-1">{icon}{label}</p>
      <p className="text-lg font-bold text-teal-800">{value ?? '—'}</p>
    </div>
  );
}
