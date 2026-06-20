import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import HRSettingsLayout from '@/components/hr/HRSettingsLayout';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SCOPE_FILTERS = [
  { key: '', label: 'All' },
  { key: 'attendance_settings', label: 'Attendance Settings' },
  { key: 'leave_type', label: 'Leave Types' },
  { key: 'holiday', label: 'Holidays' },
  { key: 'approver_config', label: 'Approver Config' },
];

const ACTION_COLOR = {
  create: 'bg-emerald-100 text-emerald-800',
  update: 'bg-blue-100 text-blue-800',
  delete: 'bg-rose-100 text-rose-800',
  bulk_import: 'bg-leamss-orange-100 text-leamss-orange-800',
};

export default function HRAuditLog() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [expanded, setExpanded] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const url = filter ? `${API}/hr/audit-log?scope=${filter}&limit=100` : `${API}/hr/audit-log?limit=100`;
      const r = await axios.get(url, { headers: { Authorization: `Bearer ${token}` } });
      setItems(r.data || []);
    } catch (e) {
      toast.error('Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  return (
    <HRSettingsLayout title="Audit Log" subtitle="Track every HR policy change" breadcrumb="Audit Log">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {SCOPE_FILTERS.map((f) => (
            <Button
              key={f.key}
              size="sm"
              variant={filter === f.key ? 'default' : 'outline'}
              onClick={() => setFilter(f.key)}
              data-testid={`filter-${f.key || 'all'}`}
            >
              {f.label}
            </Button>
          ))}
        </div>
        <Badge variant="outline" className="text-xs">{items.length} entries</Badge>
      </div>

      {loading ? (
        <p className="text-slate-500 text-sm">Loading...</p>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center" data-testid="empty-audit">
          <p className="text-sm text-slate-500">No audit entries yet</p>
        </Card>
      ) : (
        <div className="space-y-2" data-testid="audit-list">
          {items.map((a) => (
            <Card key={a.id} className="p-3 hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded({ ...expanded, [a.id]: !expanded[a.id] })} data-testid={`audit-${a.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-[250px]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={`text-[10px] ${ACTION_COLOR[a.action] || 'bg-slate-100'}`}>{a.action}</Badge>
                    <span className="text-sm font-semibold text-slate-800 font-mono">{a.scope}</span>
                    <span className="text-xs text-slate-500">by {a.actor_name || a.actor_id?.slice(0, 8)}</span>
                  </div>
                  {expanded[a.id] && (
                    <div className="mt-2 text-xs space-y-1">
                      <div className="bg-rose-50 p-2 rounded">
                        <p className="font-bold text-rose-800 text-[10px] uppercase mb-0.5">Before</p>
                        <pre className="text-rose-700 whitespace-pre-wrap text-[11px]">{JSON.stringify(a.before, null, 2) || '(empty)'}</pre>
                      </div>
                      <div className="bg-emerald-50 p-2 rounded">
                        <p className="font-bold text-emerald-800 text-[10px] uppercase mb-0.5">After</p>
                        <pre className="text-emerald-700 whitespace-pre-wrap text-[11px]">{JSON.stringify(a.after, null, 2) || '(empty)'}</pre>
                      </div>
                    </div>
                  )}
                </div>
                <span className="text-[10px] text-slate-400 whitespace-nowrap">
                  {new Date(a.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </HRSettingsLayout>
  );
}
