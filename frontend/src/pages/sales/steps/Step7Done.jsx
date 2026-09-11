// Step 7 — Done page: actions + Document Checklist + Save & Share Report dialog
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ArrowRight, FileText, Loader2, MessageSquare, Search, Send, Trophy, UserCheck,
  FileBadge, Link2, Mail, Copy, Lock, CheckCircle2, Circle, Clock, Paperclip, Download,
  Settings,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API } from '../lib/constants';
import EmailSettingsDialog from '../EmailSettingsDialog';

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
  const [lifecycle, setLifecycle] = useState(null);
  const [loadingLifecycle, setLoadingLifecycle] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailSent, setEmailSent] = useState(Boolean(saved?.email_status === 'sent'));
  const [whatsappDialogOpen, setWhatsappDialogOpen] = useState(false);
  const [whatsappSent, setWhatsappSent] = useState(Boolean(saved?.whatsapp_status === 'sent'));
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
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
    // Phase 6.10.3 — Unified Workflow tracker
    setLoadingLifecycle(true);
    axios.get(`${API}/sales/assessments/${saved.id}/lifecycle`, { headers })
      .then(r => setLifecycle(r.data))
      .catch(() => {})
      .finally(() => setLoadingLifecycle(false));
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
      + `📋 ${saved?.client_name || 'Applicant'}\n`
      + `🏆 Best country: ${saved?.best_country_code || 'AU'} · Score: ${saved?.best_total || 0} pts\n\n`
      + `📎 Full report (read-only): ${shareInfo.public_url}\n\n`
      + `Reply to this message to schedule a free consultation.`;
    const cleaned = (saved?.client_phone || '').replace(/[^\d]/g, '');
    const cleanPhone = cleaned.length === 10 ? `91${cleaned}` : cleaned;
    const url = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}` : `https://wa.me/?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const grouped = useMemo(() => {
    if (!checklist?.items || checklist?.is_locked) return {};
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

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
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
        <Button
          size="default"
          variant="outline"
          onClick={() => setEmailDialogOpen(true)}
          data-testid="email-client-btn"
          className={emailSent ? "border-teal-400 bg-teal-50 text-teal-800 hover:bg-teal-100 font-medium" : "border-indigo-300 text-indigo-700 hover:bg-indigo-50 font-medium"}
        >
          <Mail className="h-4 w-4 mr-1 text-indigo-600" />
          {emailSent ? 'Email Sent ✓' : 'Send Email'}
        </Button>
        <Button
          size="default"
          variant="outline"
          onClick={() => setWhatsappDialogOpen(true)}
          data-testid="whatsapp-client-btn"
          className={whatsappSent ? "border-emerald-400 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 font-medium" : "border-emerald-400 text-emerald-700 hover:bg-emerald-50 font-medium"}
        >
          <MessageSquare className="h-4 w-4 mr-1 text-emerald-600" />
          {whatsappSent ? 'WhatsApp Sent ✓' : 'Send on WhatsApp'}
        </Button>
        <Button
          size="default"
          variant="outline"
          onClick={() => setSettingsDialogOpen(true)}
          data-testid="template-settings-btn"
          className="border-slate-300 text-slate-700 hover:bg-slate-50 font-medium"
        >
          <Settings className="h-4 w-4 mr-1 text-slate-600" />
          Template Settings
        </Button>
        <Button size="default" variant="outline" onClick={() => setShareDialogOpen(true)} data-testid="save-share-btn" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
          <Send className="h-4 w-4 mr-1" />Save &amp; Share
        </Button>
        <Button size="default" variant="outline" onClick={() => window.print()} data-testid="export-pdf">
          <FileText className="h-4 w-4 mr-1" />Print / PDF
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

      {/* Phase 6.10.3 — Unified Workflow Status Tracker */}
      <Card className="p-4" data-testid="lifecycle-tracker">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold flex items-center gap-2">
            <Clock className="h-5 w-5 text-indigo-600" />Client Journey
          </h3>
          {lifecycle && (
            <Badge className="bg-indigo-100 text-indigo-700" data-testid="lifecycle-progress">
              {lifecycle.progress_pct}% complete · Step {Math.min(lifecycle.current_step_index + 1, 7)}/7
            </Badge>
          )}
        </div>
        {loadingLifecycle && !lifecycle ? (
          <div className="flex items-center justify-center py-4 text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin mr-2" />Loading journey…
          </div>
        ) : lifecycle ? (
          <ol className="relative space-y-3">
            {/* Vertical connector line */}
            <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-slate-200" aria-hidden="true" />
            {lifecycle.steps.map((s, i) => {
              const isCurrent = i === lifecycle.current_step_index;
              const Icon = s.completed ? CheckCircle2 : isCurrent ? Circle : Circle;
              const iconColor = s.completed
                ? 'text-emerald-500'
                : isCurrent
                  ? 'text-indigo-500 animate-pulse'
                  : 'text-slate-300';
              return (
                <li key={s.key} className="relative pl-8" data-testid={`lifecycle-step-${s.key}`}>
                  <div className="absolute left-0 top-0 bg-white">
                    <Icon className={`h-5 w-5 ${iconColor}`} />
                  </div>
                  <div className="flex items-baseline justify-between gap-2 flex-wrap">
                    <span className={`text-xs font-semibold ${s.completed ? 'text-slate-800' : isCurrent ? 'text-indigo-700' : 'text-slate-400'}`}>
                      {s.label}
                    </span>
                    {s.timestamp && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(s.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {s.detail && (
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {s.detail}
                      {s.link && (
                        <button
                          onClick={() => navigate(s.link)}
                          className="ml-2 text-indigo-600 hover:underline"
                          data-testid={`lifecycle-link-${s.key}`}
                        >
                          Open →
                        </button>
                      )}
                    </p>
                  )}
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="text-xs text-slate-400 italic">Journey not available.</p>
        )}
      </Card>

      <Card className="p-4" data-testid="checklist-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />Document Checklist
            {checklist?.is_locked && (
              <Lock className="h-4 w-4 text-amber-500" data-testid="checklist-lock-icon" />
            )}
          </h3>
          {checklist?.stats && (
            <div className="flex items-center gap-2 text-[11px]">
              <Badge className="bg-indigo-100 text-indigo-700" data-testid="checklist-total">{checklist.stats.total} items</Badge>
              <Badge className="bg-rose-100 text-rose-700">{checklist.stats.required} required</Badge>
              <Badge className="bg-slate-100 text-slate-600">{checklist.stats.optional} optional</Badge>
            </div>
          )}
        </div>
        {checklist?.is_locked ? (
          <div className="bg-amber-50 border-l-4 border-l-amber-500 p-4 rounded text-xs space-y-2" data-testid="checklist-locked-banner">
            <div className="flex items-center gap-2">
              <Lock className="h-5 w-5 text-amber-600" />
              <p className="text-sm font-bold text-amber-900">Detailed Checklist Locked</p>
            </div>
            <p className="text-amber-800">{checklist.unlock_reason}</p>
            <div className="bg-white/60 p-2 rounded border border-amber-200 mt-2">
              <p className="text-[10px] uppercase tracking-wide font-bold text-amber-700 mb-1">What you see now</p>
              <ul className="text-[11px] text-amber-900 space-y-0.5 list-disc list-inside">
                <li>Indicative document categories &amp; counts above</li>
                <li>Country &amp; pathway summary preserved on this page</li>
                <li>Full per-document checklist with body fees unlocks after Main Service Fee is paid</li>
              </ul>
            </div>
            {!checklist.linked_pa_id && (
              <p className="text-[11px] text-amber-700">
                <ArrowRight className="inline h-3 w-3" /> Click <strong>Create Pre-Assessment</strong> above to begin the workflow.
              </p>
            )}
          </div>
        ) : (
          <>
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
          </>
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

      {/* Send Email Modal — Same templates & engine as bulk pre-assessment */}
      {emailDialogOpen && (
        <IndividualEmailDialog
          assessment={saved}
          headers={headers}
          onClose={() => setEmailDialogOpen(false)}
          onSent={() => setEmailSent(true)}
        />
      )}

      {/* Send WhatsApp Modal — Automated Meta WhatsApp Cloud API / Direct Link */}
      {whatsappDialogOpen && (
        <IndividualWhatsAppDialog
          assessment={saved}
          headers={headers}
          onClose={() => setWhatsappDialogOpen(false)}
          onSent={() => setWhatsappSent(true)}
          onOpenSettings={() => {
            setWhatsappDialogOpen(false);
            setSettingsDialogOpen(true);
          }}
        />
      )}

      {/* Template & API Settings Modal */}
      {settingsDialogOpen && (
        <EmailSettingsDialog
          headers={headers}
          onClose={() => setSettingsDialogOpen(false)}
        />
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

  const existingSnapId = snap?.snapshot_id || saved?.report_snapshot_id || saved?.snapshot_id;

  const downloadPdf = async (snapshotId) => {
    const targetId = snapshotId || existingSnapId;
    if (!targetId) return;
    setGenerating(true);
    try {
      const pdfUrl = `${API}/assessment-reports/${targetId}/pdf`;
      const resp = await fetch(pdfUrl, { headers });
      if (!resp.ok) {
        throw new Error(`PDF download failed (${resp.status}): ${resp.statusText}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `LEAMSS_Assessment_Report_${saved?.client_name ? saved.client_name.replace(/\s+/g, '_') : 'Applicant'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      toast.success('Report downloaded successfully');
    } catch (e) {
      toast.error(formatApiError(e, 'PDF download failed'));
    } finally {
      setGenerating(false);
    }
  };

  const generateAndDownload = async () => {
    if (!saved?.id) {
      toast.error('Save the assessment first');
      return;
    }
    setGenerating(true);
    try {
      const r = await axios.post(
        `${API}/assessment-reports/generate`,
        { assessment_id: saved.id, persona: 'client', mode: 'combined', include_unverified: true },
        { headers, timeout: 120000 }
      );
      setSnap(r.data);
      await downloadPdf(r.data.snapshot_id);
    } catch (e) {
      toast.error(formatApiError(e, 'Report generation failed'));
    } finally {
      setGenerating(false);
    }
  };

  const createShare = async () => {
    const snapshotId = snap?.snapshot_id || existingSnapId;
    if (!snapshotId) {
      await generateAndDownload();
      return;
    }
    try {
      const r = await axios.post(`${API}/assessment-reports/${snapshotId}/share`,
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
      <Button
        size="default"
        className="bg-amber-600 hover:bg-amber-700 text-white font-medium"
        onClick={() => existingSnapId ? downloadPdf(existingSnapId) : generateAndDownload()}
        disabled={generating}
        data-testid="generate-report-btn"
      >
        {generating ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Download className="h-4 w-4 mr-1" />}
        {generating ? 'Downloading…' : 'Download Report'}
      </Button>

      <Button
        size="default"
        variant="outline"
        className="border-amber-400 bg-amber-50 text-amber-900 hover:bg-amber-100 font-medium"
        onClick={createShare}
        data-testid="share-report-btn"
      >
        <Link2 className="h-4 w-4 mr-1" />Public Link
      </Button>

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
              <Button size="sm" className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => {
                const cleaned = (saved?.client_phone || '').replace(/[^\d]/g, '');
                const cleanPhone = cleaned.length === 10 ? `91${cleaned}` : cleaned;
                const clientName = saved?.client_name || 'Applicant';
                const msg = `Hello ${clientName},\n\nPlease find your LEAMSS Assessment Report: ${shareUrl}\n\nReply to this message for any questions or next steps.\nLEAMSS — We Value Emotions ❤️`;
                const waUrl = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}` : `https://wa.me/?text=${encodeURIComponent(msg)}`;
                window.open(waUrl, '_blank', 'noopener');
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


// ════════════════════════════════════════════════════════════════
// Individual Assessment Email Dialog (Matches Bulk Pre-Assessment)
// ════════════════════════════════════════════════════════════════
export function IndividualEmailDialog({ assessment, headers, onClose, onSent }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [recipientEmail, setRecipientEmail] = useState(assessment?.client_email || '');
  const [selectedMailbox, setSelectedMailbox] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [bccSelf, setBccSelf] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!assessment?.id) return;
    (async () => {
      try {
        const r = await axios.get(`${API}/sales/assessments/${assessment.id}/email-preview`, { headers });
        setData(r.data);
        if (r.data.client_email) setRecipientEmail(r.data.client_email);
        if (r.data.default_sender) setSelectedMailbox(r.data.default_sender);
        else if (r.data.mailboxes?.length) setSelectedMailbox(r.data.mailboxes[0].email);
      } catch (e) {
        toast.error(formatApiError(e, 'Could not load email configuration'));
      } finally {
        setLoading(false);
      }
    })();
  }, [assessment?.id, headers]);

  const handleSend = async () => {
    if (!recipientEmail || !recipientEmail.includes('@')) {
      toast.error('Please enter a valid recipient email address');
      return;
    }
    setSending(true);
    try {
      const r = await axios.post(`${API}/sales/assessments/${assessment.id}/email`, {
        recipient_email: recipientEmail,
        sender_email: selectedMailbox || null,
        template_id: selectedTemplate || 'default',
        bcc_self: bccSelf,
        attach_report: true,
      }, { headers, timeout: 60000 });

      if (r.data?.ok === false || r.data?.error) {
        toast.error(r.data.error || 'Email could not be delivered');
        return;
      }
      toast.success(`Assessment Report sent to ${r.data.sent_to}!`);
      onSent?.();
      onClose();
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to send email'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="individual-email-dialog">
      <Card className="max-w-md w-full bg-white p-5 space-y-4 shadow-xl border-slate-200" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Send Assessment by Email</h3>
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1 block">Recipient Email *</label>
              <input
                type="email"
                value={recipientEmail}
                onChange={e => setRecipientEmail(e.target.value)}
                placeholder="client@example.com"
                className="w-full border border-slate-200 rounded px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid="email-recipient-input"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1 block">Sender Account</label>
              <select
                value={selectedMailbox}
                onChange={e => setSelectedMailbox(e.target.value)}
                className="w-full border border-slate-200 rounded px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid="email-sender-select"
              >
                {(data?.mailboxes || []).map(m => (
                  <option key={m.email} value={m.email}>{m.name ? `${m.name} <${m.email}>` : m.email}</option>
                ))}
              </select>
            </div>

            <div className="rounded border bg-slate-50/50 p-2.5 space-y-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">Attachments Included</span>
              <div className="flex flex-wrap gap-1.5">
                <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center gap-1 font-medium">
                  <FileText className="h-3 w-3" />23-Page PDF Report
                </span>
                {data?.attach_sla && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200 flex items-center gap-1 font-medium">
                    <Paperclip className="h-3 w-3" />Service Agreement (SLA)
                  </span>
                )}
                {data?.attach_qr && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 font-medium">
                    💳 Payment QR Code
                  </span>
                )}
              </div>
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer pt-1">
              <input type="checkbox" checked={bccSelf} onChange={e => setBccSelf(e.target.checked)} className="rounded border-slate-300 text-indigo-600" />
              <span>BCC myself for verification</span>
            </label>
          </div>
        )}

        <div className="flex gap-2 justify-end pt-2 border-t">
          <Button variant="outline" size="sm" onClick={onClose} disabled={sending}>Cancel</Button>
          <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={handleSend} disabled={sending || loading} data-testid="confirm-send-email-btn">
            {sending ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Send className="h-3.5 w-3.5 mr-1.5" />}
            {sending ? 'Sending…' : 'Send Email Now'}
          </Button>
        </div>
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Individual Assessment WhatsApp Dialog (Meta Cloud API + 1-Click)
// ════════════════════════════════════════════════════════════════
export function IndividualWhatsAppDialog({ assessment, headers, onClose, onSent, onOpenSettings }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [recipientPhone, setRecipientPhone] = useState(assessment?.client_phone || '');
  const [selectedTemplate, setSelectedTemplate] = useState('report_summary');
  const [customMessage, setCustomMessage] = useState('');
  const [attachReport, setAttachReport] = useState(true);
  const [attachResume, setAttachResume] = useState(true);
  const [attachSla, setAttachSla] = useState(true);
  const [attachQr, setAttachQr] = useState(true);
  const [sending, setSending] = useState(false);

  const authHeaders = useMemo(() => {
    if (headers && Object.keys(headers).length > 0) return headers;
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [headers]);

  useEffect(() => {
    if (!assessment?.id) return;
    (async () => {
      try {
        const r = await axios.get(`${API}/sales/assessments/${assessment.id}/whatsapp-preview`, { headers: authHeaders });
        setData(r.data);
        if (r.data.client_phone) setRecipientPhone(r.data.client_phone);
        if (r.data.attach_report !== undefined) setAttachReport(Boolean(r.data.attach_report));
        if (r.data.attach_resume !== undefined) setAttachResume(Boolean(r.data.attach_resume));
        if (r.data.attach_sla !== undefined) setAttachSla(Boolean(r.data.attach_sla));
        if (r.data.attach_qr !== undefined) setAttachQr(Boolean(r.data.attach_qr));
      } catch (e) {
        toast.error(formatApiError(e, 'Could not load WhatsApp configuration'));
      } finally {
        setLoading(false);
      }
    })();
  }, [assessment?.id, authHeaders]);

  const handleTemplateChange = (tmplId) => {
    setSelectedTemplate(tmplId);
    const tmpl = (data?.templates || []).find(t => t.id === tmplId);
    if (tmpl) {
      if (tmpl.attach_report !== undefined) setAttachReport(Boolean(tmpl.attach_report));
      if (tmpl.attach_resume !== undefined) setAttachResume(Boolean(tmpl.attach_resume));
      if (tmpl.attach_sla !== undefined) setAttachSla(Boolean(tmpl.attach_sla));
      if (tmpl.attach_qr !== undefined) setAttachQr(Boolean(tmpl.attach_qr));
    }
  };

  const handleDirectWebShare = (overridePhone) => {
    const raw = (overridePhone || recipientPhone || '').replace(/[^\d]/g, '');
    const cleanPhone = raw.length === 10 ? `91${raw}` : raw;
    const clientName = assessment?.client_name || 'Applicant';
    const score = assessment?.best_total || '';
    const country = assessment?.best_country_code || 'AU';
    const reportUrl = data?.public_url || `${window.location.origin}/sales/report/${assessment?.share_token || assessment?.id}`;
    const paymentUrl = data?.payment_link || 'https://rzp.io/rzp/IndepdenceJjMJwx1';

    let msg = customMessage;
    if (!msg) {
      const activeTmpl = (data?.templates || []).find(t => t.id === selectedTemplate);
      if (activeTmpl?.template_body) {
        msg = activeTmpl.template_body
          .replace(/\{name\}/g, clientName)
          .replace(/\{client_name\}/g, clientName)
          .replace(/\{id\}/g, assessment?.id || '')
          .replace(/\{country\}/g, country)
          .replace(/\{score\}/g, String(score))
          .replace(/\{points\}/g, String(score))
          .replace(/\{pass_mark\}/g, "65")
          .replace(/\{report_url\}/g, reportUrl)
          .replace(/\{payment_link\}/g, paymentUrl);
      } else if (selectedTemplate === 'sla_payment') {
        msg = `Dear ${clientName},\n\n`
          + `Thank you for completing your migration profile assessment with LEAMSS.\n\n`
          + `📋 *Assessment ID:* ${assessment?.id}\n`
          + `🏆 *Outcome:* Positive (${country} · ${score} pts)\n\n`
          + `🔗 *View Full Report:* ${reportUrl}\n`
          + `💳 *Secure Payment Link:* ${paymentUrl}\n\n`
          + `Please reply once payment is initiated to activate your dedicated Case Manager.\n`
          + `LEAMSS — Toll-Free: 1800-210-2427 · hello@leamss.com`;
      } else if (selectedTemplate === 'consultation_followup') {
        msg = `Hi ${clientName}! 🌟\n\n`
          + `Our migration experts have completed your evaluation for ${country} with a score of ${score} points.\n\n`
          + `📎 *Review your report here:* ${reportUrl}\n\n`
          + `Would you like to schedule a quick 15-minute call with our senior migration advisor to discuss your visa pathway? Reply to this message directly.\n`
          + `LEAMSS — www.leamss.com`;
      } else {
        msg = `Hello ${clientName},\n\n`
          + `🎉 Congratulations! Your migration profile assessment from LEAMSS has been completed.\n\n`
          + `📋 *Client:* ${clientName}\n`
          + `🆔 *Assessment ID:* ${assessment?.id}\n`
          + `🏆 *Best Country:* ${country} (Score: ${score} pts)\n\n`
          + `📎 *Access Your Branded Assessment Report (Read-only):*\n${reportUrl}\n\n`
          + `Our migration strategy team is available to assist with your next steps.\n`
          + `LEAMSS — Toll-Free: 1800-210-2427 · hello@leamss.com`;
      }
    }

    const url = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}` : `https://wa.me/?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleSend = async () => {
    const raw = (recipientPhone || '').replace(/[^\d]/g, '');
    const cleanPhone = raw.length === 10 ? `91${raw}` : raw;
    if (!cleanPhone || cleanPhone.length < 8) {
      toast.error('Please enter a valid recipient phone number with country code (e.g. +91 9876543210)');
      return;
    }
    setSending(true);
    try {
      const r = await axios.post(`${API}/sales/assessments/${assessment.id}/whatsapp`, {
        recipient_phone: cleanPhone,
        template_id: selectedTemplate,
        custom_message: customMessage || null,
        attach_report: attachReport,
        attach_resume: attachResume,
        attach_sla: attachSla,
        attach_qr: attachQr,
      }, { headers: authHeaders, timeout: 60000 });

      if (r.data?.ok) {
        const attCount = (r.data?.attachments_sent || []).length;
        toast.success(`Message and ${attCount} attachment(s) sent to +${r.data.sent_to || cleanPhone} on WhatsApp!`);
        onSent?.();
        onClose();
      } else {
        toast.error(r.data?.api_error || 'Failed to send WhatsApp message automatically.');
      }
    } catch (e) {
      console.error('Send WhatsApp dispatch:', e);
      const errMsg = e.response?.data?.detail || e.message || 'WhatsApp sending failed.';
      toast.error(`WhatsApp Error: ${errMsg}`);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="individual-whatsapp-dialog">
      <Card className="max-w-lg w-full bg-white p-5 space-y-4 shadow-xl border-slate-200" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Send on WhatsApp</h3>
              <p className="text-xs text-slate-500">Auto-send outcome + Report PDF, Resume, SLA, and Payment QR attachments</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 flex items-center gap-1 font-medium"
              onClick={() => { onClose(); navigate('/sales/whatsapp-templates'); }}
              data-testid="whatsapp-dialog-manage-templates-btn"
            >
              <Settings className="h-3.5 w-3.5 text-emerald-600" />
              Templates Manager
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1 block">
                Recipient WhatsApp Number (with Country Code) *
              </label>
              <input
                type="tel"
                value={recipientPhone}
                onChange={e => setRecipientPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                data-testid="whatsapp-recipient-input"
              />
              <p className="text-[10px] text-slate-400 mt-1">E.g. +91 9876543210 (India), +61 412345678 (Australia), +971 501234567 (UAE)</p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">WhatsApp Template</label>
                <button
                  type="button"
                  onClick={() => { onClose(); navigate('/sales/whatsapp-templates'); }}
                  className="text-[10px] text-emerald-600 hover:underline font-medium"
                >
                  + Create / Edit Templates
                </button>
              </div>
              <select
                value={selectedTemplate}
                onChange={e => handleTemplateChange(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-2.5 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                data-testid="whatsapp-template-select"
              >
                {(data?.templates || []).map(t => (
                  <option key={t.id} value={t.id}>{t.name} — {t.description}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1 block">Custom Note / Override Message</label>
              <textarea
                value={customMessage}
                onChange={e => setCustomMessage(e.target.value)}
                placeholder="Leave blank to use the selected template message above..."
                rows={2}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Attachments Section */}
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/30 p-3 space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-900 block">
                📎 WhatsApp Attachments to Dispatch ({[attachReport, data?.has_resume ? attachResume : false, attachSla, attachQr].filter(Boolean).length})
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachReport ? 'bg-emerald-100/70 border-emerald-400 text-emerald-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachReport}
                    onChange={e => setAttachReport(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <FileText className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                  <span className="truncate">Report (23p)</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachResume && data?.has_resume ? 'bg-amber-100/70 border-amber-400 text-amber-900 font-medium' : !data?.has_resume ? 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed opacity-60' : 'bg-white border-slate-200 text-slate-500'}`} title={data?.resume_filename || (data?.has_resume ? 'Candidate Resume' : 'No Resume Uploaded')}>
                  <input
                    type="checkbox"
                    checked={attachResume && Boolean(data?.has_resume)}
                    disabled={!data?.has_resume}
                    onChange={e => setAttachResume(e.target.checked)}
                    className="rounded text-amber-600 focus:ring-amber-500"
                  />
                  <FileText className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                  <span className="truncate">{data?.has_resume ? 'Resume' : 'No Resume'}</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachSla ? 'bg-blue-100/70 border-blue-400 text-blue-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachSla}
                    onChange={e => setAttachSla(e.target.checked)}
                    className="rounded text-blue-600 focus:ring-blue-500"
                  />
                  <Paperclip className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                  <span className="truncate">SLA</span>
                </label>

                <label className={`flex items-center gap-1.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${attachQr ? 'bg-purple-100/70 border-purple-400 text-purple-900 font-medium' : 'bg-white border-slate-200 text-slate-500'}`}>
                  <input
                    type="checkbox"
                    checked={attachQr}
                    onChange={e => setAttachQr(e.target.checked)}
                    className="rounded text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-xs">💳</span>
                  <span className="truncate">Payment QR</span>
                </label>
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2 justify-between items-center pt-2 border-t">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="border-emerald-500 text-emerald-700 hover:bg-emerald-50 text-xs font-semibold"
            onClick={() => handleDirectWebShare()}
          >
            <MessageSquare className="h-3.5 w-3.5 mr-1 text-emerald-600" />
            Open WhatsApp Web ↗
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onClose} disabled={sending}>Cancel</Button>
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-sm"
              onClick={handleSend}
              disabled={sending || loading}
              data-testid="confirm-send-whatsapp-btn"
            >
              {sending ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <MessageSquare className="h-3.5 w-3.5 mr-1.5" />}
              {sending ? 'Sending…' : 'Send on WhatsApp'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}


