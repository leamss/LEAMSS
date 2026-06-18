/**
 * Phase 19.6 — Recent Imports Panel (reusable)
 *
 * Shows the most-recent `import_batches` registered across all bulk-ingestion
 * paths (Phase 6.9.2 bulk, Phase 17 kb_unified, Phase 19.4 data_import).
 * Admin can:
 *   - View batch metadata (uploader, file, counts, status)
 *   - REVOKE a fully-tracked batch within 24h (single-confirm)
 *   - FORCE-REVOKE expired batches (double-confirm + min-10-char reason)
 *   - FINALISE early to lock-in a batch before 24h
 *
 * Mounted on:
 *   - /admin/verify-hub (VerificationHub.jsx)
 *   - /admin/data-import (DataImportHub.jsx)
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  AlertTriangle, Clock, FileText, History, Loader2, Lock, RefreshCw, ShieldOff, Undo2,
} from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function relTime(iso) {
  if (!iso) return '—';
  try {
    const dt = (Date.now() - new Date(iso).getTime()) / 1000;
    if (dt < 60) return 'just now';
    if (dt < 3600) return `${Math.floor(dt / 60)} min ago`;
    if (dt < 86400) return `${Math.floor(dt / 3600)} hr ago`;
    return `${Math.floor(dt / 86400)} d ago`;
  } catch { return '—'; }
}

function hoursRemaining(iso) {
  if (!iso) return null;
  const elapsed = (Date.now() - new Date(iso).getTime()) / 3600000;
  const left = 24 - elapsed;
  return left > 0 ? Math.ceil(left) : 0;
}

function fmtBytes(n) {
  if (!n) return '—';
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${(n / (1024 * 1024)).toFixed(1)}MB`;
}

const PATH_LABELS = {
  'phase_6.9.2_bulk': { name: 'Bulk Excel · Occupation Master', color: 'bg-rose-100 text-rose-800 border-rose-200' },
  'phase_17_kb_unified': { name: 'KB Unified · ANZSCO 4-digit', color: 'bg-blue-100 text-blue-800 border-blue-200' },
  'phase_19.4_data_import.occupation_profiles': { name: 'JSA · Occupation Profiles', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  'phase_19.4_data_import.employment_projections': { name: 'JSA · Employment Projections', color: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
  'phase_19.4_data_import.sa4_ratings': { name: 'JSA · SA4 Ratings', color: 'bg-purple-100 text-purple-800 border-purple-200' },
  'phase_19.4_data_import.industry_data': { name: 'JSA · Industry Data', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  'phase_19.4_data_import.vacancy_report': { name: 'JSA · Vacancy Report', color: 'bg-pink-100 text-pink-800 border-pink-200' },
};

function pathLabel(p) {
  return PATH_LABELS[p] || { name: p, color: 'bg-slate-100 text-slate-700 border-slate-200' };
}

export function RecentImportsPanel({ limit = 8 }) {
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  // Revoke modal state
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revokeBatch, setRevokeBatch] = useState(null);
  const [revokeReason, setRevokeReason] = useState('');

  // Force-revoke modal state (extra-strict)
  const [forceOpen, setForceOpen] = useState(false);
  const [forceBatch, setForceBatch] = useState(null);
  const [forceReason, setForceReason] = useState('');
  const [forceConfirmTyped, setForceConfirmTyped] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/import-batches?limit=${limit}`, { headers });
      setItems(r.data?.items || []);
    } catch (e) {
      toast.error('Failed to load Recent Imports');
    } finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  useEffect(() => { load(); }, [load]);

  const openRevoke = (b) => {
    setRevokeBatch(b);
    setRevokeReason('');
    setRevokeOpen(true);
  };

  const doRevoke = async () => {
    if (!revokeBatch) return;
    if (revokeReason.trim().length < 3) { toast.error('Reason must be at least 3 characters'); return; }
    setBusyId(revokeBatch.batch_id);
    try {
      const r = await axios.post(
        `${API}/import-batches/${revokeBatch.batch_id}/revoke`,
        { reason: revokeReason.trim() }, { headers },
      );
      toast.success(`Revoked · deleted ${r.data?.deleted || 0}, restored ${r.data?.restored || 0}`);
      setRevokeOpen(false);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Revoke failed');
    } finally { setBusyId(null); }
  };

  const openForce = (b) => {
    setForceBatch(b);
    setForceReason('');
    setForceConfirmTyped('');
    setForceOpen(true);
  };

  const doForce = async () => {
    if (!forceBatch) return;
    if (forceReason.trim().length < 10) { toast.error('Reason must be at least 10 characters'); return; }
    if (forceConfirmTyped !== 'FORCE REVOKE') { toast.error('Type FORCE REVOKE exactly to confirm'); return; }
    setBusyId(forceBatch.batch_id);
    try {
      const r = await axios.post(
        `${API}/import-batches/${forceBatch.batch_id}/force-revoke`,
        { reason: forceReason.trim(), admin_override: true }, { headers },
      );
      toast.success(`Force-revoked · deleted ${r.data?.deleted || 0}, restored ${r.data?.restored || 0}`);
      setForceOpen(false);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Force-revoke failed');
    } finally { setBusyId(null); }
  };

  const doFinalise = async (b) => {
    if (!window.confirm(`Finalise batch ${b.batch_id}? This will lock it in permanently — it cannot be revoked after this.`)) return;
    setBusyId(b.batch_id);
    try {
      await axios.post(`${API}/import-batches/${b.batch_id}/finalise`, {}, { headers });
      toast.success('Batch finalised — locked in permanently');
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Finalise failed');
    } finally { setBusyId(null); }
  };

  return (
    <>
      <Card className="p-4 border-l-4 border-l-amber-500 bg-amber-50/30" data-testid="recent-imports-panel">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-amber-900 flex items-center gap-2">
            <History className="h-4 w-4" />
            Recent Imports <span className="text-xs font-normal text-slate-500">(Phase 19.6 · last {limit})</span>
          </h3>
          <Button size="sm" variant="ghost" onClick={load} disabled={loading} data-testid="recent-imports-refresh">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} />Refresh
          </Button>
        </div>

        {loading ? (
          <div className="text-xs text-slate-500 flex items-center gap-2 py-4">
            <Loader2 className="h-3 w-3 animate-spin" />Loading…
          </div>
        ) : items.length === 0 ? (
          <div className="text-xs text-slate-500 py-4 italic" data-testid="recent-imports-empty">
            No bulk imports tracked yet. Future uploads via Phase 6.9.2, JSA Data Import, or KB Unified ANZSCO will appear here.
          </div>
        ) : (
          <div className="space-y-2" data-testid="recent-imports-list">
            {items.map((b) => {
              const pl = pathLabel(b.ingestion_path);
              const hrs = hoursRemaining(b.uploaded_at);
              const isRevoked = b.status === 'revoked' || b.status === 'partially_revoked';
              const isFinalised = !!b.finalised_at;
              const isAuditOnly = !!b.audit_only;
              const canRevoke = !isRevoked && !isFinalised && !isAuditOnly && b.is_revocable && hrs > 0;
              const canFinalise = !isRevoked && !isFinalised && b.is_revocable;
              const canForceRevoke = !isRevoked && !isFinalised && !isAuditOnly && hrs === 0;

              let statusBadge = null;
              if (isRevoked) {
                statusBadge = <Badge className="bg-rose-600 text-white text-[9px]" data-testid="batch-status-revoked">Revoked</Badge>;
              } else if (isFinalised) {
                statusBadge = <Badge className="bg-amber-600 text-white text-[9px]" data-testid="batch-status-finalised"><Lock className="h-2.5 w-2.5 mr-0.5" />Finalised</Badge>;
              } else if (isAuditOnly) {
                statusBadge = <Badge className="bg-slate-500 text-white text-[9px]" data-testid="batch-status-audit-only">Audit-Only</Badge>;
              } else if (hrs > 0) {
                statusBadge = <Badge className="bg-emerald-600 text-white text-[9px]" data-testid="batch-status-revocable">Revocable · {hrs}h left</Badge>;
              } else {
                statusBadge = <Badge className="bg-slate-400 text-white text-[9px]" data-testid="batch-status-expired">Expired</Badge>;
              }

              return (
                <div key={b.batch_id} className="bg-white border border-slate-200 rounded-md p-2.5 text-xs"
                     data-testid={`batch-row-${b.batch_id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <Badge variant="outline" className={`text-[9px] ${pl.color}`}>{pl.name}</Badge>
                        {statusBadge}
                        <span className="text-[10px] text-slate-400 font-mono">{b.batch_id}</span>
                      </div>
                      <div className="font-medium text-slate-800 truncate" title={b.file_name}>
                        <FileText className="inline h-3 w-3 mr-1 text-slate-500" />{b.file_name}
                        <span className="text-slate-400 font-normal"> · {fmtBytes(b.file_size_bytes)}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        <Clock className="inline h-2.5 w-2.5 mr-0.5" />{relTime(b.uploaded_at)} · by {b.uploaded_by_name || 'admin'}
                        {' · '}
                        <span className="font-mono">→ {b.target_collection}</span>
                      </div>
                      <div className="text-[10px] mt-1 flex gap-3">
                        <span className="text-emerald-700">+{b.counts?.created ?? 0} created</span>
                        <span className="text-blue-700">↻{b.counts?.updated ?? 0} updated</span>
                        <span className="text-slate-500">⏭{b.counts?.skipped ?? 0} skipped</span>
                        {b.counts?.total_rows != null && <span className="text-slate-400">/ {b.counts.total_rows} rows</span>}
                      </div>
                      {isRevoked && b.revoke_reason && (
                        <div className="text-[10px] text-rose-700 mt-1 italic">
                          Revoked: {b.revoke_reason} · by {b.revoked_by || 'admin'}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      {canRevoke && (
                        <Button size="sm" variant="outline" className="h-7 text-[10px] border-rose-300 text-rose-700 hover:bg-rose-50"
                                disabled={busyId === b.batch_id}
                                onClick={() => openRevoke(b)}
                                data-testid={`revoke-btn-${b.batch_id}`}>
                          <Undo2 className="h-3 w-3 mr-1" />Revoke
                        </Button>
                      )}
                      {canForceRevoke && (
                        <Button size="sm" variant="outline" className="h-7 text-[10px] border-rose-400 text-rose-800 hover:bg-rose-100"
                                disabled={busyId === b.batch_id}
                                onClick={() => openForce(b)}
                                data-testid={`force-revoke-btn-${b.batch_id}`}>
                          <ShieldOff className="h-3 w-3 mr-1" />Force…
                        </Button>
                      )}
                      {canFinalise && (
                        <Button size="sm" variant="ghost" className="h-7 text-[10px] text-amber-700 hover:bg-amber-50"
                                disabled={busyId === b.batch_id}
                                onClick={() => doFinalise(b)}
                                data-testid={`finalise-btn-${b.batch_id}`}>
                          <Lock className="h-3 w-3 mr-1" />Lock in
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Revoke modal — basic confirm */}
      {revokeOpen && revokeBatch && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="revoke-modal">
          <Card className="w-full max-w-md p-5">
            <h4 className="text-base font-bold text-rose-900 flex items-center gap-2 mb-2">
              <Undo2 className="h-4 w-4" />Revoke Import Batch
            </h4>
            <p className="text-xs text-slate-600 mb-3">
              This will reverse the bulk operation tracked under <span className="font-mono">{revokeBatch.batch_id}</span>:
              <strong className="block mt-1 text-slate-800">
                Delete {revokeBatch.counts?.created || 0} created rows · Restore {revokeBatch.counts?.updated || 0} updated rows · in <code>{revokeBatch.target_collection}</code>.
              </strong>
            </p>
            <label className="text-[10px] font-semibold text-slate-700 block mb-1">Reason (min 3 chars):</label>
            <textarea
              className="w-full border border-slate-300 rounded text-xs p-2 h-20"
              placeholder="Why are you revoking? (audit trail)"
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.target.value)}
              data-testid="revoke-reason-input"
            />
            <div className="flex justify-end gap-2 mt-3">
              <Button size="sm" variant="ghost" onClick={() => setRevokeOpen(false)} data-testid="revoke-cancel">Cancel</Button>
              <Button size="sm" className="bg-rose-600 hover:bg-rose-700" onClick={doRevoke}
                      disabled={revokeReason.trim().length < 3 || busyId === revokeBatch.batch_id}
                      data-testid="revoke-confirm">
                {busyId === revokeBatch.batch_id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Undo2 className="h-3 w-3 mr-1" />}
                Confirm Revoke
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Force-revoke modal — extra strict */}
      {forceOpen && forceBatch && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="force-revoke-modal">
          <Card className="w-full max-w-md p-5 border-2 border-rose-500">
            <h4 className="text-base font-bold text-rose-900 flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4" />Force-Revoke (Override 24h Window)
            </h4>
            <div className="bg-rose-50 border border-rose-300 p-2 rounded text-[11px] text-rose-900 mb-3">
              <strong>Caution Sir:</strong> This batch is outside the standard 24h revocation window.
              Force-revoke bypasses the safety lock and is logged with <code>critical</code> severity.
            </div>
            <p className="text-xs text-slate-600 mb-2">
              Target: <code>{forceBatch.target_collection}</code> · Batch <span className="font-mono">{forceBatch.batch_id}</span><br />
              Will delete <strong>{forceBatch.counts?.created || 0}</strong> created rows + restore <strong>{forceBatch.counts?.updated || 0}</strong> updated rows.
            </p>
            <label className="text-[10px] font-semibold text-slate-700 block mb-1">Reason (min 10 chars):</label>
            <textarea
              className="w-full border border-slate-300 rounded text-xs p-2 h-20"
              placeholder="Detailed justification for force-override…"
              value={forceReason}
              onChange={(e) => setForceReason(e.target.value)}
              data-testid="force-reason-input"
            />
            <label className="text-[10px] font-semibold text-slate-700 block mt-2 mb-1">
              Type <code>FORCE REVOKE</code> exactly to confirm:
            </label>
            <input
              type="text"
              className="w-full border border-rose-300 rounded text-xs p-2"
              placeholder="FORCE REVOKE"
              value={forceConfirmTyped}
              onChange={(e) => setForceConfirmTyped(e.target.value)}
              data-testid="force-confirm-input"
            />
            <div className="flex justify-end gap-2 mt-3">
              <Button size="sm" variant="ghost" onClick={() => setForceOpen(false)} data-testid="force-cancel">Cancel</Button>
              <Button size="sm" className="bg-rose-700 hover:bg-rose-800"
                      onClick={doForce}
                      disabled={forceReason.trim().length < 10 || forceConfirmTyped !== 'FORCE REVOKE' || busyId === forceBatch.batch_id}
                      data-testid="force-confirm-btn">
                {busyId === forceBatch.batch_id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ShieldOff className="h-3 w-3 mr-1" />}
                Force Revoke
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}

export default RecentImportsPanel;
