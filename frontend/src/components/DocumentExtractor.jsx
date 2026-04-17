import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Upload, FileSearch, Sparkles, Loader2, CheckCircle2, AlertTriangle,
  ImageIcon, X, Copy, Download, Eye, RefreshCw, Zap, FileText,
  ShieldCheck, Scan, Pencil, Save
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CONFIDENCE_COLOR = (c) => {
  if (c >= 0.9) return { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-200', bar: 'bg-emerald-500', label: 'High' };
  if (c >= 0.7) return { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-200', bar: 'bg-amber-500', label: 'Med' };
  return { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-200', bar: 'bg-red-500', label: 'Low' };
};

const pretty = (v) => {
  if (v == null) return '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
};

const humanKey = (k) => (k || '').replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());

const DOC_TYPE_HINTS = [
  { value: '', label: 'Auto-detect (recommended)' },
  { value: 'passport', label: 'Passport' },
  { value: 'visa', label: 'Visa' },
  { value: 'educational_certificate', label: 'Educational Certificate' },
  { value: 'academic_transcript', label: 'Academic Transcript / Marksheet' },
  { value: 'ielts_scorecard', label: 'IELTS Scorecard' },
  { value: 'bank_statement', label: 'Bank Statement' },
  { value: 'police_clearance', label: 'Police Clearance (PCC)' },
  { value: 'marriage_certificate', label: 'Marriage Certificate' },
  { value: 'birth_certificate', label: 'Birth Certificate' },
  { value: 'driver_license', label: "Driver's License" },
  { value: 'offer_letter', label: 'Offer / Admission Letter' },
];

/**
 * DocumentExtractor — Upload or demo, get structured AI extraction.
 *
 * Props:
 *   token — auth (required for real extraction)
 *   role  — 'client' | 'partner' | 'case_manager' | 'admin'
 *   caseId — optional, enables "Save to Case"
 *   compact — boolean; hides heading/intro for embedded use
 *   defaultTab — 'upload' | 'demo'
 */
export default function DocumentExtractor({ token, role = 'client', caseId = null, compact = false, defaultTab = 'upload' }) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [samples, setSamples] = useState([]);
  const [hintDocType, setHintDocType] = useState('');
  const [previewUrl, setPreviewUrl] = useState(null);
  const [fileMeta, setFileMeta] = useState(null);
  const [fileBase64, setFileBase64] = useState(null); // cache for save
  const [extracting, setExtracting] = useState(false);
  const [progress, setProgress] = useState(0); // animated progress 0-100
  const [stageText, setStageText] = useState('');
  const [result, setResult] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editedFields, setEditedFields] = useState({});
  const [history, setHistory] = useState([]);
  const [viewingExtraction, setViewingExtraction] = useState(null);
  const fileInputRef = useRef(null);
  const progressTimerRef = useRef(null);

  // Load sample docs once
  useEffect(() => {
    axios.get(`${API}/doc-extraction/sample-docs`)
      .then(r => setSamples(r.data.samples || []))
      .catch(() => { /* ignore */ });
  }, []);

  // Cleanup preview URL
  useEffect(() => () => {
    if (previewUrl && previewUrl.startsWith('blob:')) URL.revokeObjectURL(previewUrl);
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
  }, [previewUrl]);

  const startProgressAnimation = (stages) => {
    setProgress(5);
    let pct = 5;
    let i = 0;
    setStageText(stages[0]?.text || '');
    progressTimerRef.current = setInterval(() => {
      pct = Math.min(pct + 3, 92);
      setProgress(pct);
      const currentStage = stages.findIndex(s => pct < s.pctEnd);
      if (currentStage !== -1 && currentStage !== i) {
        i = currentStage;
        setStageText(stages[i].text);
      }
    }, 220);
  };

  const finishProgress = () => {
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    setProgress(100);
    setStageText('Complete');
    setTimeout(() => {
      setProgress(0);
      setStageText('');
    }, 800);
  };

  const handleFileSelect = (file) => {
    if (!file) return;
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    if (!allowed.includes(file.type)) {
      toast.error('Use JPEG, PNG, or WEBP only');
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      toast.error('Image too large (max 8 MB)');
      return;
    }
    if (previewUrl && previewUrl.startsWith('blob:')) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    setFileMeta({ name: file.name, type: file.type, size: file.size, rawFile: file });
    // Cache base64 for later save
    const reader = new FileReader();
    reader.onloadend = () => setFileBase64(reader.result);
    reader.readAsDataURL(file);
    setResult(null);
  };

  const loadHistory = useCallback(async () => {
    if (!token) return;
    try {
      const params = caseId ? { case_id: caseId } : {};
      const r = await axios.get(`${API}/doc-extraction/history`, {
        headers: { Authorization: `Bearer ${token}` }, params,
      });
      setHistory(r.data.extractions || []);
    } catch { /* ignore */ }
  }, [token, caseId]);

  useEffect(() => { if (activeTab === 'history') loadHistory(); }, [activeTab, loadHistory]);

  const runExtraction = async () => {
    if (!fileMeta?.rawFile) { toast.error('Upload an image first'); return; }
    if (!token) { toast.error('Please log in to run extraction'); return; }
    setExtracting(true);
    setResult(null);
    startProgressAnimation([
      { text: 'Uploading image…', pctEnd: 25 },
      { text: 'Analyzing pixels with AI vision…', pctEnd: 55 },
      { text: 'Detecting document type…', pctEnd: 75 },
      { text: 'Extracting structured fields…', pctEnd: 90 },
      { text: 'Verifying confidence scores…', pctEnd: 100 },
    ]);
    try {
      const fd = new FormData();
      fd.append('file', fileMeta.rawFile);
      if (hintDocType) fd.append('hint_doc_type', hintDocType);
      const r = await axios.post(`${API}/doc-extraction/extract-upload`, fd, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setResult({ ...r.data, demo: false });
      setEditedFields({ ...(r.data.extraction?.fields || {}) });
      finishProgress();
      toast.success('Extraction complete');
    } catch (e) {
      finishProgress();
      toast.error(e?.response?.data?.detail || 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  const runDemo = async (sampleId) => {
    setExtracting(true);
    setResult(null);
    const sample = samples.find(s => s.id === sampleId);
    if (sample) setPreviewUrl(null);
    startProgressAnimation([
      { text: 'Loading specimen document…', pctEnd: 25 },
      { text: 'Scanning pixels with AI vision…', pctEnd: 55 },
      { text: 'Detecting document type…', pctEnd: 75 },
      { text: 'Extracting structured fields…', pctEnd: 90 },
      { text: 'Verifying confidence scores…', pctEnd: 100 },
    ]);
    try {
      // Artificial delay so user can see the animation for demo feel
      await new Promise(res => setTimeout(res, 2200));
      const r = await axios.get(`${API}/doc-extraction/sample-docs/${sampleId}/extraction`);
      const demo = { ...r.data, demo: true };
      setResult(demo);
      setEditedFields({ ...(demo.extraction?.fields || {}) });
      setFileMeta({ name: sample?.name || 'Sample Document', type: 'demo', size: 0 });
      finishProgress();
    } catch (e) {
      finishProgress();
      toast.error('Could not load demo');
    } finally {
      setExtracting(false);
    }
  };

  const saveExtraction = async () => {
    if (!result || !token) return;
    try {
      const payload = {
        ...result.extraction,
        fields: editMode ? { ...result.extraction.fields, ...editedFields } : result.extraction.fields,
      };
      await axios.post(`${API}/doc-extraction/save`, {
        extraction: payload,
        case_id: caseId,
        filename: fileMeta?.name,
        image_base64: fileBase64 || null,
        mime_type: fileMeta?.type,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Saved to records — view in "Saved Extractions" tab');
      setEditMode(false);
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    }
  };

  const deleteHistoryItem = async (id) => {
    if (!window.confirm('Delete this saved extraction?')) return;
    try {
      await axios.delete(`${API}/doc-extraction/history/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Deleted');
      loadHistory();
      if (viewingExtraction?.id === id) setViewingExtraction(null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Delete failed');
    }
  };

  const copyAll = () => {
    if (!result) return;
    const ex = result.extraction;
    const lines = [
      `Document: ${ex.doc_type_name || ex.doc_type}`,
      `Confidence: ${Math.round((ex.overall_confidence || 0) * 100)}%`,
      '',
      ...Object.entries(ex.fields || {}).map(([k, v]) => `${humanKey(k)}: ${pretty(v)}`),
    ];
    navigator.clipboard.writeText(lines.join('\n')).then(() => toast.success('Copied'));
  };

  const reset = () => {
    if (previewUrl && previewUrl.startsWith('blob:')) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setFileMeta(null);
    setFileBase64(null);
    setResult(null);
    setEditedFields({});
    setEditMode(false);
  };

  // ----- UI -----
  return (
    <div className="space-y-4" data-testid="document-extractor">
      {!compact && (
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <div className="p-2 bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] rounded-lg text-white">
                <Scan className="h-5 w-5" />
              </div>
              AI Document Scanner
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Upload any identity / academic / financial document — our AI extracts the fields automatically with confidence scores.
            </p>
          </div>
          <Badge className="bg-[#2a777a]/10 text-[#2a777a] border-[#2a777a]/30 hidden sm:inline-flex">
            <Sparkles className="h-3 w-3 mr-1" /> Powered by GPT-4o Vision
          </Badge>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-slate-100">
          <TabsTrigger value="upload" data-testid="dx-tab-upload">
            <Upload className="h-4 w-4 mr-1.5" /> Upload & Extract
          </TabsTrigger>
          <TabsTrigger value="demo" data-testid="dx-tab-demo">
            <Zap className="h-4 w-4 mr-1.5" /> Try Demo
          </TabsTrigger>
          <TabsTrigger value="history" data-testid="dx-tab-history">
            <FileText className="h-4 w-4 mr-1.5" /> Saved Extractions
            {history.length > 0 && <Badge className="ml-1.5 bg-[#2a777a] text-white text-xs h-5 px-1.5">{history.length}</Badge>}
          </TabsTrigger>
        </TabsList>

        {/* UPLOAD TAB */}
        <TabsContent value="upload" className="mt-0">
          <div className="grid lg:grid-cols-5 gap-4">
            {/* Left: upload */}
            <Card className="lg:col-span-2 p-5 bg-white border-slate-200 space-y-3">
              {!previewUrl ? (
                <label htmlFor="dx-file" className="block border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-[#2a777a] hover:bg-slate-50/80 transition-colors" data-testid="dx-dropzone">
                  <div className="w-14 h-14 mx-auto bg-[#2a777a]/10 rounded-full flex items-center justify-center mb-3">
                    <Upload className="h-6 w-6 text-[#2a777a]" />
                  </div>
                  <p className="font-semibold text-slate-800">Drop or click to upload</p>
                  <p className="text-xs text-slate-500 mt-1">JPEG, PNG, or WEBP · Max 8 MB</p>
                </label>
              ) : (
                <div className="relative border border-slate-200 rounded-xl overflow-hidden bg-slate-50 aspect-[4/3]">
                  <img src={previewUrl} alt="preview" className="w-full h-full object-contain" />
                  <button onClick={reset} className="absolute top-2 right-2 w-8 h-8 bg-white/90 hover:bg-white rounded-full flex items-center justify-center shadow"
                    data-testid="dx-reset-btn">
                    <X className="h-4 w-4" />
                  </button>
                  {extracting && (
                    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center">
                      <div className="text-center text-white">
                        <Scan className="h-10 w-10 animate-pulse mx-auto mb-2" />
                        <p className="font-semibold text-sm">{stageText}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
              <input id="dx-file" type="file" ref={fileInputRef} accept="image/jpeg,image/png,image/webp"
                className="hidden" onChange={e => handleFileSelect(e.target.files?.[0])} data-testid="dx-file-input" />

              {fileMeta && fileMeta.type !== 'demo' && (
                <p className="text-xs text-slate-500 truncate flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" /> {fileMeta.name} · {(fileMeta.size / 1024).toFixed(1)} KB
                </p>
              )}

              <div>
                <Label className="text-xs font-semibold text-slate-600">Document type hint (optional)</Label>
                <Select value={hintDocType} onValueChange={setHintDocType}>
                  <SelectTrigger className="mt-1" data-testid="dx-hint-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-64">
                    {DOC_TYPE_HINTS.map(d => <SelectItem key={d.value || 'auto'} value={d.value || 'auto'}>{d.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <p className="text-[10px] text-slate-400 mt-1">AI auto-detects, but a hint improves accuracy</p>
              </div>

              <Button onClick={runExtraction} disabled={!fileMeta?.rawFile || extracting}
                className="w-full bg-[#f7620b] hover:bg-[#e55a09]" data-testid="dx-extract-btn">
                {extracting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
                {extracting ? 'Extracting…' : 'Run AI Extraction'}
              </Button>

              {progress > 0 && (
                <div className="space-y-1">
                  <Progress value={progress} className="h-2" />
                  <p className="text-[11px] text-slate-500 text-center">{stageText}</p>
                </div>
              )}
            </Card>

            {/* Right: result */}
            <div className="lg:col-span-3">
              <ResultPanel
                result={result}
                editMode={editMode}
                editedFields={editedFields}
                setEditedFields={setEditedFields}
                setEditMode={setEditMode}
                onSave={saveExtraction}
                onCopy={copyAll}
                canSave={role !== 'client' || !!caseId}
              />
            </div>
          </div>
        </TabsContent>

        {/* DEMO TAB */}
        <TabsContent value="demo" className="mt-0 space-y-4">
          <Card className="p-4 bg-gradient-to-br from-[#f7620b]/5 to-[#2a777a]/5 border-[#2a777a]/20">
            <p className="text-sm text-slate-700 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#f7620b]" />
              <span><strong>How this works:</strong> Click any specimen below to see exactly what our AI extracts — fast, free, no real document needed.</span>
            </p>
          </Card>

          <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-3">
            {samples.map(s => (
              <Card key={s.id} className="p-4 bg-white border-slate-200 hover:border-[#2a777a] hover:shadow-md transition-all cursor-pointer"
                onClick={() => !extracting && runDemo(s.id)} data-testid={`dx-sample-${s.id}`}>
                <div className="text-4xl mb-2 text-center">{s.thumbnail}</div>
                <h4 className="font-semibold text-sm text-slate-800 leading-tight">{s.name}</h4>
                <p className="text-[10px] text-slate-500 mt-1 leading-snug">{s.description}</p>
                <Button variant="outline" size="sm" className="w-full mt-2 h-7 text-xs" disabled={extracting}>
                  <Zap className="h-3 w-3 mr-1" /> Try this
                </Button>
              </Card>
            ))}
          </div>

          {extracting && (
            <Card className="p-5 bg-white border-slate-200 text-center">
              <Scan className="h-10 w-10 text-[#2a777a] animate-pulse mx-auto mb-2" />
              <p className="font-semibold text-slate-800">{stageText}</p>
              <Progress value={progress} className="h-2 mt-3 max-w-md mx-auto" />
            </Card>
          )}

          {result && !extracting && (
            <ResultPanel
              result={result}
              editMode={editMode}
              editedFields={editedFields}
              setEditedFields={setEditedFields}
              setEditMode={setEditMode}
              onSave={saveExtraction}
              onCopy={copyAll}
              canSave={false}
            />
          )}
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history" className="mt-0 space-y-4">
          {history.length === 0 ? (
            <Card className="p-12 text-center bg-white border-slate-200 border-dashed">
              <FileText className="h-12 w-12 text-slate-200 mx-auto mb-3" />
              <p className="font-semibold text-slate-600">No saved extractions yet</p>
              <p className="text-sm text-slate-400 mt-1">Upload a document, extract, and click "Save to Records" to see it here.</p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {history.map(h => {
                const ex = h.extraction || {};
                const conf = ex.overall_confidence || 0;
                const color = CONFIDENCE_COLOR(conf);
                const imgUrl = h.has_image ? `${API}/doc-extraction/image/${h.id}` : null;
                return (
                  <Card key={h.id} className="p-3 bg-white border-slate-200 hover:border-[#2a777a] hover:shadow-md transition-all cursor-pointer"
                    onClick={() => setViewingExtraction(h)} data-testid={`dx-hist-${h.id}`}>
                    {imgUrl ? (
                      <div className="w-full aspect-[4/3] bg-slate-100 rounded overflow-hidden mb-2">
                        <img src={imgUrl} alt={h.filename} className="w-full h-full object-cover"
                          onError={(e) => { e.target.style.display = 'none'; }}
                          crossOrigin="anonymous" />
                      </div>
                    ) : (
                      <div className="w-full aspect-[4/3] bg-slate-50 rounded mb-2 flex items-center justify-center">
                        <FileText className="h-10 w-10 text-slate-300" />
                      </div>
                    )}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="outline" className="text-xs">{ex.doc_type_name || ex.doc_type || 'Document'}</Badge>
                        <span className={`text-xs font-bold ${color.text}`}>{Math.round(conf * 100)}%</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-800 truncate">{h.filename || 'Untitled'}</p>
                      <p className="text-xs text-slate-500 line-clamp-2">{ex.summary || '—'}</p>
                      <p className="text-[11px] text-slate-400">{new Date(h.created_at).toLocaleString()}</p>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* History detail dialog */}
      {viewingExtraction && (
        <HistoryDetailDialog
          item={viewingExtraction}
          token={token}
          onClose={() => setViewingExtraction(null)}
          onDelete={() => deleteHistoryItem(viewingExtraction.id)}
        />
      )}
    </div>
  );
}

function HistoryDetailDialog({ item, token, onClose, onDelete }) {
  const ex = item.extraction || {};
  const fields = ex.fields || {};
  const confidences = ex.confidences || {};
  const overall = ex.overall_confidence || 0;
  const overallPct = Math.round(overall * 100);
  const overallColor = CONFIDENCE_COLOR(overall);
  const [authedImgUrl, setAuthedImgUrl] = useState(null);

  useEffect(() => {
    if (!item.has_image || !token) return;
    let revoked = false;
    (async () => {
      try {
        const resp = await axios.get(`${API}/doc-extraction/image/${item.id}`, {
          headers: { Authorization: `Bearer ${token}` }, responseType: 'blob',
        });
        if (!revoked) setAuthedImgUrl(URL.createObjectURL(resp.data));
      } catch { /* ignore */ }
    })();
    return () => { revoked = true; if (authedImgUrl) URL.revokeObjectURL(authedImgUrl); };
    // eslint-disable-next-line
  }, [item.id, item.has_image, token]);

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose} data-testid="dx-history-dialog">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-5 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-[#2a777a]" />
              {item.filename || 'Saved Extraction'}
            </h3>
            <p className="text-xs text-slate-500">Saved {new Date(item.created_at).toLocaleString()} by {item.created_by_name}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="border-red-200 text-red-600 hover:bg-red-50" onClick={onDelete} data-testid="dx-hist-delete">
              <X className="h-3.5 w-3.5 mr-1" /> Delete
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="p-5 grid md:grid-cols-2 gap-5">
          {/* Image */}
          <div>
            {authedImgUrl ? (
              <img src={authedImgUrl} alt={item.filename} className="w-full rounded-lg border border-slate-200" />
            ) : item.has_image ? (
              <div className="aspect-[4/3] bg-slate-100 rounded-lg animate-pulse" />
            ) : (
              <div className="aspect-[4/3] bg-slate-50 rounded-lg flex items-center justify-center border border-dashed border-slate-200">
                <div className="text-center text-slate-400">
                  <FileText className="h-10 w-10 mx-auto mb-2" />
                  <p className="text-xs">Image not stored</p>
                </div>
              </div>
            )}
          </div>

          {/* Extraction */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Badge className="bg-[#2a777a] text-white">
                <FileText className="h-3 w-3 mr-1" /> {ex.doc_type_name || ex.doc_type}
              </Badge>
              <div className={`px-3 py-1 rounded-lg ring-1 ${overallColor.bg} ${overallColor.ring}`}>
                <span className={`text-sm font-bold ${overallColor.text}`}>{overallPct}% confidence</span>
              </div>
            </div>
            {ex.summary && <p className="text-sm text-slate-600">{ex.summary}</p>}
            <div className="space-y-1.5">
              {Object.entries(fields).map(([k, v]) => {
                const c = confidences[k] || 0;
                const cc = CONFIDENCE_COLOR(c);
                return (
                  <div key={k} className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-100">
                    <span className="text-xs uppercase text-slate-500 font-semibold">{humanKey(k)}</span>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm text-slate-800 font-medium truncate max-w-[200px]">{pretty(v)}</span>
                      <span className={`text-[10px] font-semibold ${cc.text} shrink-0`}>{Math.round(c * 100)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultPanel({ result, editMode, editedFields, setEditedFields, setEditMode, onSave, onCopy, canSave }) {
  if (!result) {
    return (
      <Card className="p-12 bg-white border-slate-200 border-dashed text-center h-full flex flex-col items-center justify-center">
        <FileSearch className="h-12 w-12 text-slate-200 mb-3" />
        <p className="font-semibold text-slate-600">No extraction yet</p>
        <p className="text-sm text-slate-400 mt-1">Upload a document on the left and click "Run AI Extraction"</p>
      </Card>
    );
  }

  const ex = result.extraction || {};
  const fields = ex.fields || {};
  const confidences = ex.confidences || {};
  const overall = ex.overall_confidence || 0;
  const overallPct = Math.round(overall * 100);
  const overallColor = CONFIDENCE_COLOR(overall);

  return (
    <Card className="p-5 bg-white border-slate-200 space-y-4" data-testid="dx-result">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className="bg-[#2a777a] text-white border-0">
              <ShieldCheck className="h-3 w-3 mr-1" /> AI Verified
            </Badge>
            <Badge variant="outline" className="text-xs">
              <FileText className="h-3 w-3 mr-1" /> {ex.doc_type_name || ex.doc_type}
            </Badge>
            {result.demo && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-xs">
                <Zap className="h-3 w-3 mr-1" /> Demo Specimen
              </Badge>
            )}
          </div>
          {ex.summary && (
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">{ex.summary}</p>
          )}
        </div>
        <div className={`text-right px-3 py-2 rounded-lg ring-1 ${overallColor.bg} ${overallColor.ring}`}>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Overall Confidence</p>
          <p className={`text-2xl font-bold ${overallColor.text}`} data-testid="dx-overall-conf">{overallPct}%</p>
        </div>
      </div>

      {ex.warnings?.length > 0 && (
        <div className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800">
            <p className="font-semibold">Quality warnings</p>
            <ul className="list-disc list-inside mt-0.5">
              {ex.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        </div>
      )}

      {/* Fields */}
      <div className="space-y-2">
        {Object.entries(fields).map(([key, value]) => {
          const conf = confidences[key] || 0;
          const color = CONFIDENCE_COLOR(conf);
          const currentValue = editMode ? editedFields[key] : value;
          return (
            <div key={key} className="grid grid-cols-12 gap-2 items-start p-2.5 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200" data-testid={`dx-field-${key}`}>
              <div className="col-span-4">
                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">{humanKey(key)}</p>
              </div>
              <div className="col-span-6">
                {editMode ? (
                  <Input value={currentValue ?? ''}
                    onChange={e => setEditedFields({ ...editedFields, [key]: e.target.value })}
                    className="h-8 text-sm" data-testid={`dx-field-edit-${key}`} />
                ) : (
                  <p className="text-sm text-slate-800 font-medium break-words">{pretty(currentValue)}</p>
                )}
              </div>
              <div className="col-span-2">
                <div className="flex items-center gap-1.5">
                  <div className={`flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden`}>
                    <div className={`h-full ${color.bar}`} style={{ width: `${Math.round(conf * 100)}%` }} />
                  </div>
                  <span className={`text-[10px] font-semibold ${color.text}`}>{Math.round(conf * 100)}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-slate-100">
        {editMode ? (
          <>
            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => setEditMode(false)} data-testid="dx-edit-done">
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Done Editing
            </Button>
            <Button variant="outline" size="sm" onClick={() => setEditedFields({ ...(result.extraction?.fields || {}) })} data-testid="dx-edit-revert">
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Revert
            </Button>
          </>
        ) : (
          <Button variant="outline" size="sm" onClick={() => setEditMode(true)} data-testid="dx-edit-btn">
            <Pencil className="h-3.5 w-3.5 mr-1" /> Edit Fields
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={onCopy} data-testid="dx-copy-btn">
          <Copy className="h-3.5 w-3.5 mr-1" /> Copy All
        </Button>
        {canSave && !result.demo && (
          <Button size="sm" className="bg-[#2a777a] hover:bg-[#236466]" onClick={onSave} data-testid="dx-save-btn">
            <Save className="h-3.5 w-3.5 mr-1" /> Save to Records
          </Button>
        )}
      </div>
    </Card>
  );
}
