import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Package, Plus, IndianRupee, CheckCircle, Trash2, Clock, CreditCard } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * MilestonesManager
 *  - caseId
 *  - role: 'partner' | 'admin' | 'case_manager' | 'client'
 */
export default function MilestonesManager({ caseId, role }) {
  const [items, setItems] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', amount: '', description: '', due_date: '' });
  const [loading, setLoading] = useState(true);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const r = await axios.get(`${API}/milestones/case/${caseId}`, getAuth());
      setItems(r.data || []);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  const canCreate = role === 'partner' || role === 'admin' || role === 'case_manager';
  const canPay = role === 'client';

  const create = async () => {
    if (!form.title || !form.amount || parseFloat(form.amount) <= 0) {
      toast.error('Title & valid amount required'); return;
    }
    try {
      await axios.post(`${API}/milestones/case/${caseId}/create`, {
        title: form.title, amount: parseFloat(form.amount),
        description: form.description, due_date: form.due_date || null,
      }, getAuth());
      toast.success('Milestone created');
      setShowCreate(false);
      setForm({ title: '', amount: '', description: '', due_date: '' });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const pay = async (mid) => {
    try {
      await axios.post(`${API}/milestones/${mid}/mock-pay`, {}, getAuth());
      toast.success('Paid (mock)'); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const markPaid = async (mid) => {
    try {
      await axios.post(`${API}/milestones/${mid}/mark-paid`, {}, getAuth());
      toast.success('Marked paid'); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const remove = async (mid) => {
    if (!window.confirm('Delete this milestone?')) return;
    try {
      await axios.delete(`${API}/milestones/${mid}`, getAuth());
      toast.success('Deleted'); load();
    } catch (e) { toast.error('Failed'); }
  };

  if (loading) return <p className="text-xs text-slate-400">Loading milestones…</p>;

  return (
    <div className="space-y-3" data-testid="milestones-manager">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5"><Package className="h-4 w-4 text-leamss-teal-600" /> Milestone Payments ({items.length})</p>
        {canCreate && (
          <Button size="sm" variant="outline" onClick={() => setShowCreate(!showCreate)} className="h-7 text-xs" data-testid="milestone-new-btn">
            <Plus className="h-3 w-3 mr-1" /> New Milestone
          </Button>
        )}
      </div>

      {showCreate && canCreate && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
          <Input placeholder="Title (e.g., Documentation Complete)" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="milestone-title" />
          <div className="grid grid-cols-2 gap-2">
            <Input type="number" placeholder="Amount ₹" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} data-testid="milestone-amount" />
            <Input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} data-testid="milestone-due" />
          </div>
          <Input placeholder="Description (optional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button size="sm" onClick={create} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="milestone-save-btn">Save</Button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <p className="text-xs text-slate-400 italic">No milestones defined.</p>
      ) : (
        <div className="space-y-2">
          {items.map(m => (
            <div key={m.id} className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg p-3" data-testid={`milestone-row-${m.id}`}>
              <div className={`h-9 w-9 rounded-full flex items-center justify-center shrink-0 ${m.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-leamss-teal-100 text-leamss-teal-700'}`}>
                {m.status === 'paid' ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">{m.title}</p>
                {m.description && <p className="text-xs text-slate-500 truncate">{m.description}</p>}
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  <Badge className={m.status === 'paid' ? 'bg-emerald-100 text-emerald-700 h-4 text-[10px]' : 'bg-amber-100 text-amber-700 h-4 text-[10px]'}>{m.status}</Badge>
                  {m.due_date && <span className="text-[10px] text-slate-400">Due: {m.due_date}</span>}
                  {m.paid_at && <span className="text-[10px] text-slate-400">Paid: {new Date(m.paid_at).toLocaleDateString()}</span>}
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-slate-800 flex items-center justify-end"><IndianRupee className="h-3 w-3" />{(m.amount || 0).toLocaleString('en-IN')}</p>
                <div className="flex gap-1 mt-1 justify-end">
                  {canPay && m.status === 'pending' && (
                    <Button size="sm" onClick={() => pay(m.id)} className="h-6 text-[11px] bg-[#f7620b] hover:bg-[#e55a09] text-white px-2" data-testid={`milestone-pay-${m.id}`}>
                      <CreditCard className="h-3 w-3 mr-1" /> Pay
                    </Button>
                  )}
                  {canCreate && m.status === 'pending' && (
                    <Button size="sm" variant="outline" onClick={() => markPaid(m.id)} className="h-6 text-[11px] px-2" data-testid={`milestone-mark-${m.id}`}>Mark Paid</Button>
                  )}
                  {canCreate && (
                    <Button size="sm" variant="outline" onClick={() => remove(m.id)} className="h-6 text-[11px] text-red-500 border-red-200 hover:bg-red-50 px-1.5" data-testid={`milestone-del-${m.id}`}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
