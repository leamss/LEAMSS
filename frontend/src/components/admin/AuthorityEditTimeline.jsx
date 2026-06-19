/**
 * Phase 19.9.1 — Authority Edit Timeline side-panel.
 *
 * Shows chronological audit trail of authority write events.
 * Mounted as overlay panel from Authority Health Card's 4th tile.
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { X, Clock, Edit3, CheckCircle, Trash2, Split, RefreshCw, ArrowRight } from 'lucide-react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token')}` };
}

const ACTION_ICONS = {
  'authority.create': Edit3,
  'authority.patch': Edit3,
  'authority.verify': CheckCircle,
  'authority.bulk_verify': CheckCircle,
  'authority.split_laa': Split,
  'authority.delete': Trash2,
  'authority.migrate_occupation': ArrowRight,
};

const ACTION_COLORS = {
  'authority.create': 'bg-emerald-100 text-emerald-700 border-emerald-300',
  'authority.patch': 'bg-leamss-teal_50 text-leamss-teal border-leamss-teal_50',
  'authority.verify': 'bg-emerald-100 text-emerald-700 border-emerald-300',
  'authority.bulk_verify': 'bg-emerald-100 text-emerald-700 border-emerald-300',
  'authority.split_laa': 'bg-amber-100 text-amber-700 border-amber-300',
  'authority.delete': 'bg-rose-100 text-rose-700 border-rose-300',
  'authority.migrate_occupation': 'bg-leamss-teal_50 text-leamss-teal border-leamss-teal_50',
};

function relativeTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function AuthorityEditTimeline({ open, onClose, code = null }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = code
        ? `${API}/assessing-authorities/${code}/audit-trail?limit=50`
        : `${API}/assessing-authorities/audit-trail/recent?limit=50`;
      const r = await axios.get(url, { headers: authHeaders() });
      setItems(r.data.items || []);
    } catch (e) { /* silent */ }
    finally { setLoading(false); }
  }, [code]);

  useEffect(() => { if (open) load(); }, [open, load]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex justify-end" data-testid="authority-edit-timeline">
      <Card className="w-full max-w-md h-full overflow-y-auto rounded-none border-l-4 border-l-leamss-teal">
        <div className="sticky top-0 bg-white border-b p-3 flex justify-between items-center">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              {code ? `${code} · Edit History` : 'Recent Authority Edits'}
            </h3>
            <p className="text-[10px] text-slate-500">Last {items.length} events from audit_logs</p>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={load} disabled={loading} data-testid="timeline-refresh">
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose} data-testid="timeline-close">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="p-3 space-y-2">
          {items.length === 0 && !loading && (
            <p className="text-xs text-slate-500 italic">No audit events yet for this filter.</p>
          )}
          {items.map((ev, i) => {
            const Icon = ACTION_ICONS[ev.action] || Edit3;
            const color = ACTION_COLORS[ev.action] || 'bg-slate-100 text-slate-600';
            return (
              <div key={i} className="border-l-2 border-slate-200 pl-3 pb-2" data-testid={`timeline-event-${i}`}>
                <div className="flex items-start gap-2">
                  <Badge className={`text-[9px] border ${color}`}>
                    <Icon className="h-2.5 w-2.5 inline mr-1" />
                    {ev.action.replace('authority.', '')}
                  </Badge>
                  <span className="text-[10px] text-slate-500" title={ev.at}>{relativeTime(ev.at)}</span>
                </div>
                <div className="text-[11px] mt-1">
                  <strong>{ev.summary?.code || ev.summary?.occupation_id || '—'}</strong>
                  {ev.summary?.fields_changed && (
                    <span className="text-slate-600 ml-1">· fields: {ev.summary.fields_changed.join(', ')}</span>
                  )}
                  {ev.summary?.new_code && (
                    <span className="text-slate-600 ml-1">→ {ev.summary.new_code}</span>
                  )}
                  {ev.summary?.verified && ev.summary.verified.length > 0 && (
                    <span className="text-slate-600 ml-1">· {ev.summary.verified.length} verified</span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  by {ev.user_name || ev.user_id || 'system'}
                  {ev.summary?.batch_id && <span className="ml-2 font-mono">[{ev.summary.batch_id.slice(-8)}]</span>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

export default AuthorityEditTimeline;
