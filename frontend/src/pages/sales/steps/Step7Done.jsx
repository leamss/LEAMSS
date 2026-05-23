// Step 7 — Done page: actions + Document Checklist + Save & Share Report dialog
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ArrowRight, FileText, Loader2, MessageSquare, Search, Send, Trophy, UserCheck,
  FileBadge, Link2, Mail, Copy,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API } from '../lib/constants';

const ADMIN_ROLES = new Set(['admin', 'admin_owner', 'case_manager']);

function getCurrentRole() {
  try {
    const me = JSON.parse(localStorage.getItem('user') || '{}');
    return me.rbac_role || me.role || '';
  } catch { return ''; }
}

export default function Step7Done({ saved, createPA, navigate, headers, creatingPA }) {
  const [checklist, setChecklist] = useState(null);
  const [loadingChecklist, setLoadingChecklist] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareInfo, setShareInfo] = useState(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [expiryDays, setExpiryDays] = useState(30);

  // Phase 6.8.1 — Admin/Case Manager must pick a partner before creating PA
  const role = getCurrentRole();
  const needsPartnerPicker = ADMIN_ROLES.has(role);
  const [partnerPickerOpen, setPartnerPickerOpen] = useState(false);
  const [partnerOptions, setPartnerOptions] = useState([]);
  const [selectedPartner, setSelectedPartner] = useState('');
  const [loadingPartners, setLoadingPartners] = useState(false);

  useEffect(() => {
    if (!saved?.id) return;
    setLoadingChecklist(true);
    axios.get(`${API}/sales/assessments/${saved.id}/checklist`, { headers })
      .then(r => setChecklist(r.data))
      .catch(e => toast.error(formatApiError(e, 'Failed to load checklist')))
      .finally(() => setLoadingChecklist(false));
  }, [saved?.id, headers]);

  const openCreatePAFlow = async () => {
    if (!needsPartnerPicker) {
      // Partner/sales → direct call (self-assign on backend)
      createPA();
      return;
    }
    // Admin/Case Manager → fetch partner options + open dropdown modal
    setLoadingPartners(true);
    try {
      const r = await axios.get(`${API}/sales/assessments/partner-options`, { headers });
      setPartnerOptions(r.data.items || []);
      setSelectedPartner('');
      setPartnerPickerOpen(true);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load partner list'));
    } finally {
      setLoadingPartners(false);
    }
  };

  const confirmCreatePA = () => {
    if (!selectedPartner) {
      toast.error('Please pick a partner before creating PA');
      return;
    }
    setPartnerPickerOpen(false);
    createPA(selectedPartner);
  };

  const generateShareLink = async () => {
    setShareLoading(true);
    try {
      const r = await axios.post(`${API}/sales/assessments/${saved.id}/share`, { expires_in_days: expiryDays }, { headers });
      setShareInfo(r.data);
      toast.success('Share link generated');
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to generate share link'));
    } finally { setShareLoading(false); }
  };

  const copyLink = async () => {
    if (!shareInfo?.public_url) return;
    try {
      await navigator.clipboard.writeText(shareInfo.public_url);
      toast.success('Link copied to clipboard');
    } catch {
      toast.error('Copy failed — please select and copy manually');
    }
  };

  const shareOnWhatsapp = () => {
    if (!shareInfo?.public_url) return;
    const msg = `Hi! Here's your eligibility report from LEAMSS:\n\n`
      + `📋 ${saved?.client_name}\n`
      + `🏆 Best country: ${saved?.best_country_code} · Score: ${saved?.best_total} pts\n\n`
      + `📎 Full report (read-only): ${shareInfo.public_url}\n\n`
      + `Reply to this message to schedule a free consultation.`;
    const url = `https://wa.me/?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const grouped = useMemo(() => {
    if (!checklist?.items) return {};
    return checklist.items.reduce((acc, it) => {
      (acc[it.category] = acc[it.category] || []).push(it);
      return acc;
    }, {});
  }, [checklist]);

  return (
    <div className="max-w-4xl mx-auto space-y-5 py-4" data-testid="step-7-done">
      <div className="text-center space-y-3">
        <Trophy className="h-14 w-14 text-emerald-500 mx-auto" />
        <h2 className="text-2xl font-bold text-emerald-900">Assessment Complete!</h2>
        <p className="text-sm text-slate-600">ID: <code className="bg-slate-100 px-2 py-0.5 rounded text-xs">{saved?.id}</code></p>
        {saved?.best_country_code && (
          <p className="text-sm">
            Best country: <strong>{saved.best_country_code}</strong> · Score: <strong>{saved.best_total}</strong>
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        {saved?.linked_pa_id ? (
          <Button
            size="default"
            variant="outline"
            className="border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
            onClick={() => {
              // Route to role-appropriate pipeline
              try {
                const me = JSON.parse(localStorage.getItem('user') || '{}');
                const r = me.rbac_role || me.role;
                if (r === 'partner') navigate('/partner');
                else if (r === 'case_manager') navigate('/case-manager');
                else if (['sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head'].includes(r)) navigate('/sales/dashboard');
                else navigate('/admin');
              } catch { navigate('/admin'); }
            }}
            data-testid="linked-pa-btn"
          >
            <UserCheck className="h-4 w-4 mr-1" />
            Linked PA: {saved.linked_pa_id?.slice(0, 8)}…
          </Button>
        ) : (
          <Button size="default" className="bg-indigo-600 hover:bg-indigo-700" onClick={openCreatePAFlow} disabled={creatingPA || loadingPartners} data-testid="create-pa-btn">
            {(creatingPA || loadingPartners) ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <ArrowRight className="h-4 w-4 mr-1" />}
            {creatingPA ? 'Creating…' : loadingPartners ? 'Loading…' : 'Create Pre-Assessment'}
          </Button>
        )}
        <ReportActions saved={saved} data-testid="report-actions" />
        <Button size="default" variant="outline" onClick={() => setShareDialogOpen(true)} data-testid="save-share-btn" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
          <Send className="h-4 w-4 mr-1" />Save &amp; Share Report
        </Button>
        <Button size="default" variant="outline" onClick={() => window.print()} data-testid="export-pdf">
          <FileText className="h-4 w-4 mr-1" />Print / Export PDF
        </Button>
      </div>

      {saved?.linked_pa_id && (
        <div className="bg-emerald-50 border-l-4 border-l-emerald-500 p-3 rounded text-xs" data-testid="linked-pa-banner">
          <p className="font-semibold text-emerald-900">
            ✓ This assessment is already linked to a Pre-Assessment.
          </p>
          <p className="text-emerald-700 mt-0.5">
            Any future updates to this assessment will automatically sync to the linked PA. No duplicate PA will be created.
          </p>
        </div>
      )}

      <Card className="p-4" data-testid="checklist-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />Document Checklist
          </h3>
          {checklist && (
            <div className="flex items-center gap-2 text-[11px]">
              <Badge className="bg-indigo-100 text-indigo-700" data-testid="checklist-total">{checklist.stats.total} items</Badge>
              <Badge className="bg-rose-100 text-rose-700">{checklist.stats.required} required</Badge>
              <Badge className="bg-slate-100 text-slate-600">{checklist.stats.optional} optional</Badge>
            </div>
          )}
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          Rule-based, no AI. Generated from country ({saved?.best_country_code}), occupation, marital status, and pathway.
        </p>
        {loadingChecklist ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />Loading checklist…
          </div>
        ) : !checklist ? (
          <p className="text-xs text-slate-400 italic">No checklist available.</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} data-testid={`checklist-cat-${cat.replace(/\s+/g, '-')}`}>
                <p className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">{cat}</p>
                <ul className="space-y-1">
                  {items.map(it => (
                    <li key={`${cat}-${it.name}`} className="flex items-start gap-2 text-xs">
                      <div className={`mt-0.5 h-3.5 w-3.5 rounded-full border-2 flex-shrink-0 ${it.required ? 'border-rose-400' : 'border-slate-300'}`} />
                      <div className="flex-1">
                        <span className={it.required ? 'font-medium text-slate-700' : 'text-slate-500'}>{it.name}</span>
                        {it.required && <Badge className="ml-2 bg-rose-50 text-rose-600 text-[9px] py-0">Required</Badge>}
                        {it.fee_native && <span className="ml-2 text-[10px] text-emerald-700 font-mono">{it.fee_native}</span>}
                        {it.note && <p className="text-[10px] text-slate-400 italic mt-0.5">{it.note}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Card>

      {shareDialogOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShareDialogOpen(false)} data-testid="share-dialog">
          <Card className="max-w-md w-full bg-white p-5" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-bold flex items-center gap-2 mb-1">
              <Send className="h-5 w-5 text-emerald-600" />Save &amp; Share Report
            </h3>
            <p className="text-[11px] text-slate-500 mb-3">Generate a public read-only link for this assessment.</p>
            {!shareInfo ? (
              <>
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Link Validity</p>
                <div className="grid grid-cols-5 gap-1 mb-3">
                  {[
                    { d: 1, l: '1 day' },
                    { d: 7, l: '7 days' },
                    { d: 30, l: '30 days' },
                    { d: 90, l: '90 days' },
                    { d: 0, l: 'Never' },
                  ].map(o => (
                    <button
                      key={o.d}
                      onClick={() => setExpiryDays(o.d)}
                      className={`p-2 rounded border-2 text-[11px] ${expiryDays === o.d ? 'border-emerald-500 bg-emerald-50 font-bold' : 'border-slate-200 text-slate-600'}`}
                      data-testid={`share-expiry-${o.d}`}
                    >
                      {o.l}
                    </button>
                  ))}
                </div>
                {expiryDays === 0 && (
                  <p className="text-[10px] text-amber-700 bg-amber-50 p-2 rounded mb-3">⚠️ Never-expire links should only be shared with trusted recipients.</p>
                )}
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" size="sm" onClick={() => setShareDialogOpen(false)}>Cancel</Button>
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" disabled={shareLoading} onClick={generateShareLink} data-testid="share-generate-btn">
                    {shareLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Send className="h-3 w-3 mr-1" />}
                    Generate Link
                  </Button>
                </div>
              </>
            ) : (
              <>
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Public Link</p>
                <div className="p-2 bg-slate-50 rounded border text-[11px] break-all font-mono mb-3" data-testid="share-link-output">
                  {shareInfo.public_url}
                </div>
                {shareInfo.expires_at ? (
                  <p className="text-[10px] text-slate-500 mb-3">Expires: {new Date(shareInfo.expires_at).toLocaleString()}</p>
                ) : (
                  <p className="text-[10px] text-amber-700 mb-3">⚠️ Never expires.</p>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <Button size="sm" variant="outline" onClick={copyLink} data-testid="share-copy-btn">
                    <FileText className="h-3 w-3 mr-1" />Copy Link
                  </Button>
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={shareOnWhatsapp} data-testid="share-whatsapp-btn">
                    <MessageSquare className="h-3 w-3 mr-1" />WhatsApp Share
                  </Button>
                </div>
                <Button variant="ghost" size="sm" className="w-full mt-2 text-[11px]" onClick={() => { setShareInfo(null); setShareDialogOpen(false); }}>
                  Done
                </Button>
              </>
            )}
          </Card>
        </div>
      )}

      {/* Partner Picker Modal — Phase 6.8.1 (admin/case-manager only) */}
      {partnerPickerOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setPartnerPickerOpen(false)} data-testid="partner-picker-modal">
          <Card className="max-w-md w-full bg-white p-5" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-bold flex items-center gap-2 mb-1">
              <UserCheck className="h-5 w-5 text-indigo-600" />Assign to Partner / Sales
            </h3>
            <p className="text-[11px] text-slate-500 mb-3">
              Admin-initiated PAs must be assigned to a partner or sales person so they enter the correct pipeline.
            </p>
            <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Choose Owner *</p>
            <select
              value={selectedPartner}
              onChange={e => setSelectedPartner(e.target.value)}
              className="w-full border border-slate-200 rounded px-2 py-2 text-sm bg-white"
              data-testid="partner-picker-select"
            >
              <option value="">— Select a Partner / Sales person —</option>
              {partnerOptions.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name || p.email} · {p.role.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            {partnerOptions.length === 0 && (
              <p className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded mt-2">No active partners or sales people found. Please add them in User Management first.</p>
            )}
            <div className="flex gap-2 justify-end mt-4">
              <Button variant="outline" size="sm" onClick={() => setPartnerPickerOpen(false)}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={confirmCreatePA} disabled={!selectedPartner} data-testid="partner-picker-confirm">
                <ArrowRight className="h-3 w-3 mr-1" />Create PA
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Phase 6.10 Part 2 — Professional Report Engine actions
// ════════════════════════════════════════════════════════════════
function ReportActions({ saved }) {
  const [generating, setGenerating] = useState(false);
  const [snap, setSnap] = useState(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState('');
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const generate = async () => {
    if (!saved?.id) {
      toast.error('Save the assessment first');
      return;
    }
    setGenerating(true);
    try {
      const r = await axios.post(`${API}/assessment-reports/generate`,
        { assessment_id: saved.id, persona: 'client', mode: 'combined', include_unverified: true },
        { headers });
      setSnap(r.data);
      // Auto-open PDF in new tab
      const pdfUrl = `${API}/assessment-reports/${r.data.snapshot_id}/pdf`;
      const a = document.createElement('a');
      a.href = pdfUrl;
      a.target = '_blank';
      a.rel = 'noopener';
      // Need to use fetch+blob so the auth header is sent
      const resp = await fetch(pdfUrl, { headers });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      toast.success('Report generated', {
        description: r.data.warnings?.length
          ? `${r.data.warnings.length} verification warning(s) — admin should verify KB`
          : 'Snapshot is immutable · Branded PDF opened in new tab',
      });
    } catch (e) {
      toast.error(formatApiError(e, 'Report generation failed'));
    } finally {
      setGenerating(false);
    }
  };

  const createShare = async () => {
    if (!snap) {
      toast.error('Generate the report first');
      return;
    }
    try {
      const r = await axios.post(`${API}/assessment-reports/${snap.snapshot_id}/share`,
        { expires_in_days: 30 }, { headers });
      const url = `${window.location.origin}/reports/view/${r.data.share_token}`;
      setShareUrl(url);
      setShareOpen(true);
      navigator.clipboard?.writeText(url).then(() => {
        toast.success('Public link copied to clipboard', { description: 'Expires in 30 days' });
      }).catch(() => toast.success('Public link ready'));
    } catch (e) {
      toast.error(formatApiError(e, 'Share link failed'));
    }
  };

  return (
    <>
      {!snap ? (
        <Button size="default" className="bg-amber-600 hover:bg-amber-700"
          onClick={generate} disabled={generating} data-testid="generate-report-btn">
          {generating ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <FileBadge className="h-4 w-4 mr-1" />}
          {generating ? 'Generating…' : 'Generate Report'}
        </Button>
      ) : (
        <Button size="default" variant="outline" className="border-amber-400 bg-amber-50 text-amber-900 hover:bg-amber-100"
          onClick={createShare} data-testid="share-report-btn">
          <Link2 className="h-4 w-4 mr-1" />Public Link
        </Button>
      )}
      {shareOpen && shareUrl && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="share-modal">
          <Card className="bg-white p-5 max-w-md w-full">
            <h3 className="text-base font-bold flex items-center gap-2 mb-2">
              <Link2 className="h-4 w-4 text-amber-600" />Public Share Link
            </h3>
            <p className="text-xs text-slate-600 mb-3">
              Read-only branded report. No login required. Expires in 30 days.
            </p>
            <div className="bg-slate-50 p-2 rounded font-mono text-[10px] break-all border" data-testid="share-url">
              {shareUrl}
            </div>
            <div className="flex gap-2 mt-3">
              <Button size="sm" variant="outline" className="flex-1"
                onClick={() => { navigator.clipboard?.writeText(shareUrl); toast.success('Copied!'); }}
                data-testid="copy-share-url">
                <Copy className="h-3 w-3 mr-1" />Copy
              </Button>
              <Button size="sm" variant="outline" className="flex-1"
                onClick={() => window.open(shareUrl, '_blank', 'noopener')}>
                Open
              </Button>
              <Button size="sm" className="flex-1 bg-emerald-600" onClick={() => {
                const msg = `Hello! Please find your LEAMSS Assessment Report: ${shareUrl}`;
                window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank', 'noopener');
              }} data-testid="whatsapp-share">
                <MessageSquare className="h-3 w-3 mr-1" />WhatsApp
              </Button>
            </div>
            <Button size="sm" variant="ghost" className="w-full mt-2" onClick={() => setShareOpen(false)}>
              Close
            </Button>
          </Card>
        </div>
      )}
    </>
  );
}
