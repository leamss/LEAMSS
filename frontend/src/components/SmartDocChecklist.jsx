import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { CheckCircle, Circle, ListChecks } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * SmartDocChecklist — based on /api/intelligence/checklist/{pa_id}
 * Country-aware recommended-docs list with completion %.
 */
export default function SmartDocChecklist({ paId, initialData = null }) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    if (!paId) return;
    try {
      setLoading(true);
      const r = await axios.get(`${API}/intelligence/checklist/${paId}`, getAuth());
      setData(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, [paId]);

  useEffect(() => {
    if (initialData) { setData(initialData); setLoading(false); }
    else { load(); }
  }, [initialData, load]);

  if (loading || !data) return null;

  const pct = data.stats.completion_pct || 0;

  return (
    <div className="space-y-3" data-testid={`smart-checklist-${paId}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5"><ListChecks className="h-4 w-4 text-indigo-600" /> Smart Doc Checklist</p>
        <Badge className="bg-indigo-100 text-indigo-700 h-5 text-[11px]">{data.stats.done}/{data.stats.total} · {pct}%</Badge>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div className="h-2 bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[11px] text-slate-500">Template: <span className="font-semibold text-slate-700 capitalize">{(data.template || '').replace(/_/g, ' ')}</span> · {data.country} · {data.service_type}</p>
      <div className="grid md:grid-cols-2 gap-1.5">
        {data.items.map((it, i) => (
          <div key={i} className={`flex items-center gap-2 text-xs rounded-md px-2 py-1.5 border ${it.uploaded ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-slate-200'}`}>
            {it.uploaded
              ? <CheckCircle className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
              : <Circle className="h-3.5 w-3.5 text-slate-400 shrink-0" />}
            <span className={`flex-1 truncate ${it.uploaded ? 'text-emerald-800' : 'text-slate-700'}`}>{it.name}</span>
            {it.required && <Badge className="bg-red-50 text-red-600 h-4 text-[9px] px-1">Req</Badge>}
          </div>
        ))}
      </div>
    </div>
  );
}
