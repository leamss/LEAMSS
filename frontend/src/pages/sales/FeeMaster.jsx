/**
 * Skill-Assessment Fee Master — Australia.
 *
 * Central editor for each assessing authority's skill-assessment fee. Supports MULTIPLE
 * fee components per authority (e.g. TRA = Document Evidence + Technical Interview +
 * Practical Assessment). Matched occupation-code-wise via occupation_master, so a fee set
 * here flows into every occupation using that authority and every bulk report.
 *
 * Route: /sales/fee-master
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Loader2, Save, Plus, Trash2, IndianRupee, Search,
  CheckCircle2, AlertTriangle, Landmark,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmt = (n) => (Number(n) || 0).toLocaleString('en-IN');
const totalStr = (tbc) => Object.entries(tbc || {}).map(([c, v]) => `${c === 'INR' ? '₹' : c + ' '}${fmt(v)}`).join(' + ') || '—';

export default function FeeMaster() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [loading, setLoading] = useState(true);
  const [authorities, setAuthorities] = useState([]);
  const [stats, setStats] = useState({ total: 0, configured: 0, missing: 0 });
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all'); // all | set | missing
  const [drafts, setDrafts] = useState({}); // key -> {authority_name, components:[...]}
  const [savingKey, setSavingKey] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/fee-master`, { headers });
      setAuthorities(r.data.authorities || []);
      setStats({ total: r.data.total, configured: r.data.configured, missing: r.data.missing });
      const d = {};
      (r.data.authorities || []).forEach((a) => {
        d[a.key] = {
          authority_name: a.authority_name,
          components: (a.components || []).map((c) => ({ ...c })),
        };
      });
      setDrafts(d);
    } catch (e) {
      toast.error(formatApiError(e, 'Could not load Fee Master'));
    } finally { setLoading(false); }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const setComp = (key, i, field, value) => setDrafts((d) => ({
    ...d,
    [key]: { ...d[key], components: d[key].components.map((c, idx) => idx === i ? { ...c, [field]: value } : c) },
  }));
  const addComp = (key) => setDrafts((d) => ({
    ...d,
    [key]: { ...d[key], components: [...(d[key]?.components || []), { label: '', amount: '', currency: 'INR' }] },
  }));
  const removeComp = (key, i) => setDrafts((d) => ({
    ...d,
    [key]: { ...d[key], components: d[key].components.filter((_, idx) => idx !== i) },
  }));

  const draftTotal = (key) => {
    const tbc = {};
    (drafts[key]?.components || []).forEach((c) => {
      const amt = Number(c.amount) || 0;
      if (!amt) return;
      const cur = c.currency || 'INR';
      tbc[cur] = (tbc[cur] || 0) + amt;
    });
    return tbc;
  };

  const save = async (key) => {
    const draft = drafts[key];
    const comps = (draft?.components || []).filter((c) => c.amount !== '' && c.amount != null);
    if (comps.length === 0) { toast.error('Add at least one fee component with an amount'); return; }
    setSavingKey(key);
    try {
      await axios.put(`${API}/fee-master/${key}`, {
        authority_name: draft.authority_name,
        components: comps.map((c) => ({ label: c.label || 'Skill Assessment Fee', amount: Number(c.amount), currency: c.currency || 'INR' })),
      }, { headers });
      toast.success(`Saved — ${draft.authority_name}`);
      await load();
    } catch (e) {
      toast.error(formatApiError(e, 'Could not save fee'));
    } finally { setSavingKey(null); }
  };

  const filtered = authorities.filter((a) => {
    if (filter === 'set' && !a.is_set) return false;
    if (filter === 'missing' && a.is_set) return false;
    if (query && !a.authority_name.toLowerCase().includes(query.toLowerCase()) && !a.key.includes(query.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="fee-master-page">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/sales/bulk-assessment')} data-testid="fm-back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Bulk
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Landmark className="h-7 w-7 text-teal-600" />
              Skill Assessment Fee Master
              <Badge className="bg-teal-600 text-white text-[9px]">AU</Badge>
            </h1>
            <p className="text-sm text-slate-500">Set each assessing authority's fee once — it flows into every occupation & bulk report.</p>
          </div>
        </div>

        {/* Stats + filters */}
        <Card className="p-3 flex flex-wrap items-center gap-3" data-testid="fm-toolbar">
          <div className="flex items-center gap-2 text-sm">
            <Badge className="bg-slate-200 text-slate-700">{stats.total} authorities</Badge>
            <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle2 className="h-3 w-3 mr-1" />{stats.configured} set</Badge>
            <Badge className="bg-rose-100 text-rose-700"><AlertTriangle className="h-3 w-3 mr-1" />{stats.missing} missing</Badge>
          </div>
          <div className="relative flex-1 min-w-[180px]">
            <Search className="h-4 w-4 absolute left-2 top-2.5 text-slate-400" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search authority…" className="pl-8 h-9" data-testid="fm-search" />
          </div>
          <div className="flex gap-1">
            {['all', 'set', 'missing'].map((f) => (
              <Button key={f} size="sm" variant={filter === f ? 'default' : 'outline'}
                onClick={() => setFilter(f)} className={filter === f ? 'bg-teal-600 hover:bg-teal-700 h-9' : 'h-9'}
                data-testid={`fm-filter-${f}`}>{f === 'all' ? 'All' : f === 'set' ? 'Configured' : 'Missing'}</Button>
            ))}
          </div>
        </Card>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400"><Loader2 className="h-6 w-6 animate-spin mr-2" />Loading…</div>
        ) : (
          <div className="space-y-3">
            {filtered.map((a) => {
              const d = drafts[a.key] || { components: [] };
              const dirty = JSON.stringify(d.components) !== JSON.stringify(a.components || []);
              return (
                <Card key={a.key} className="p-4" data-testid={`fm-auth-${a.key}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0">
                      <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                        {a.authority_name}
                        {a.is_set
                          ? <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">set</Badge>
                          : <Badge className="bg-rose-100 text-rose-700 text-[9px]">not set</Badge>}
                      </h3>
                      <p className="text-[11px] text-slate-400">{a.occupation_count} occupation{a.occupation_count === 1 ? '' : 's'} · key: {a.key}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[9px] text-slate-400 uppercase tracking-wide">Total Skill Assessment</p>
                      <p className="text-base font-bold text-teal-800 font-mono" data-testid={`fm-total-${a.key}`}>{totalStr(draftTotal(a.key))}</p>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1.5">
                    {(d.components || []).map((c, i) => (
                      <div key={i} className="flex items-center gap-1.5" data-testid={`fm-comp-${a.key}-${i}`}>
                        <IndianRupee className="h-3.5 w-3.5 text-slate-300 shrink-0" />
                        <Input value={c.label} onChange={(e) => setComp(a.key, i, 'label', e.target.value)}
                          placeholder="Fee name (e.g. Document Evidence)" className="h-8 text-xs flex-1" data-testid={`fm-label-${a.key}-${i}`} />
                        <Input type="number" value={c.amount} onChange={(e) => setComp(a.key, i, 'amount', e.target.value)}
                          placeholder="Amount" className="h-8 text-xs w-28" data-testid={`fm-amount-${a.key}-${i}`} />
                        <select value={c.currency || 'INR'} onChange={(e) => setComp(a.key, i, 'currency', e.target.value)}
                          className="h-8 text-xs border rounded px-1" data-testid={`fm-ccy-${a.key}-${i}`}>
                          <option>INR</option><option>AUD</option>
                        </select>
                        <button onClick={() => removeComp(a.key, i)} className="text-rose-400 hover:text-rose-600 px-1" data-testid={`fm-remove-${a.key}-${i}`}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                    {(d.components || []).length === 0 && (
                      <p className="text-[11px] text-slate-400 italic">No fee set. Add a component — for authorities like TRA add all sub-fees (Document Evidence, Technical Interview, Practical Assessment).</p>
                    )}
                  </div>

                  <div className="mt-2 flex items-center justify-between">
                    <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={() => addComp(a.key)} data-testid={`fm-add-${a.key}`}>
                      <Plus className="h-3 w-3 mr-1" />Add fee component
                    </Button>
                    <Button size="sm" onClick={() => save(a.key)} disabled={!dirty || savingKey === a.key}
                      className="bg-teal-600 hover:bg-teal-700 h-7 text-[11px]" data-testid={`fm-save-${a.key}`}>
                      {savingKey === a.key ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}
                      {dirty ? 'Save' : 'Saved'}
                    </Button>
                  </div>
                </Card>
              );
            })}
            {filtered.length === 0 && <p className="text-center text-slate-400 py-10 text-sm">No authorities match.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
