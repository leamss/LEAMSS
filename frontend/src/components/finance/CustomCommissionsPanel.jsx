/**
 * Custom Per-Partner Product Commissions Panel
 *
 * Relocated from AdminDashboard.jsx (commissions tab) to live inside the
 * Finance Center. Lets admin set a per-partner override commission rate
 * for a specific product (overrides the partner's default rate).
 */
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/select';
import {
  Settings, Plus, Edit, Trash2, CheckCircle, XCircle, AlertCircle, Sparkles,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CustomCommissionsPanel() {
  const [partners, setPartners] = useState([]);
  const [products, setProducts] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState({ partner_id: '', product_id: '', commission_rate: 5 });
  const [saving, setSaving] = useState(false);

  const headers = useCallback(() => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  }), []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [u, p, c] = await Promise.all([
        axios.get(`${API}/users`, headers()),
        axios.get(`${API}/products`, headers()),
        axios.get(`${API}/partner-commissions`, headers()),
      ]);
      setPartners((u.data || []).filter(x => x.role === 'partner'));
      setProducts(p.data || []);
      setRows(c.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load custom rates');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!draft.partner_id || !draft.product_id) {
      toast.error('Select a partner and product first');
      return;
    }
    const rate = Number(draft.commission_rate);
    if (!Number.isFinite(rate) || rate < 0 || rate > 100) {
      toast.error('Rate must be 0–100');
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/partner-commissions`, {
        partner_id: draft.partner_id,
        product_id: draft.product_id,
        commission_rate: rate,
      }, headers());
      toast.success('Custom rate saved');
      setDraft({ partner_id: '', product_id: '', commission_rate: 5 });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally { setSaving(false); }
  };

  const updateRate = async (row, newRate) => {
    try {
      await axios.post(`${API}/partner-commissions`, {
        partner_id: row.partner_id,
        product_id: row.product_id,
        commission_rate: Number(newRate),
      }, headers());
      toast.success('Rate updated');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Update failed'); }
  };

  const remove = async (row) => {
    if (!window.confirm(`Remove custom ${row.commission_rate}% rate for ${row.partner_name} on ${row.product_name}? Partner will fall back to their default rate.`)) return;
    try {
      await axios.delete(`${API}/partner-commissions`, {
        ...headers(),
        data: { partner_id: row.partner_id, product_id: row.product_id },
      });
      toast.success('Rate removed');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Delete failed'); }
  };

  return (
    <Card className="p-5" data-testid="custom-commissions-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-indigo-600" />
          <div>
            <h2 className="font-bold text-slate-800">Custom Rates · Per Partner × Product</h2>
            <p className="text-xs text-slate-500">
              Override the partner&apos;s default commission rate for specific products.
              Useful for premium/VIP deals or strategic partnerships.
            </p>
          </div>
        </div>
      </div>

      {/* Add new row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5 p-4 bg-indigo-50/60 border border-indigo-200 rounded-lg" data-testid="add-custom-rate-row">
        <div>
          <Label className="text-[11px] font-semibold text-slate-600">Partner</Label>
          <Select value={draft.partner_id} onValueChange={v => setDraft({ ...draft, partner_id: v })}>
            <SelectTrigger data-testid="cc-partner-select"><SelectValue placeholder="Select partner" /></SelectTrigger>
            <SelectContent>
              {partners.length === 0 ? (
                <div className="p-2 text-xs text-slate-400">No partners found</div>
              ) : partners.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-[11px] font-semibold text-slate-600">Product</Label>
          <Select value={draft.product_id} onValueChange={v => setDraft({ ...draft, product_id: v })}>
            <SelectTrigger data-testid="cc-product-select"><SelectValue placeholder="Select product" /></SelectTrigger>
            <SelectContent>
              {products.length === 0 ? (
                <div className="p-2 text-xs text-slate-400">No products found</div>
              ) : products.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-[11px] font-semibold text-slate-600">Rate (%)</Label>
          <Input
            type="number" min={0} max={100} step={0.5}
            value={draft.commission_rate}
            onChange={e => setDraft({ ...draft, commission_rate: e.target.value })}
            data-testid="cc-rate-input"
          />
        </div>
        <div className="flex items-end">
          <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700 w-full" data-testid="cc-save-btn">
            <Plus className="h-4 w-4 mr-1" /> {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Existing rows */}
      {loading ? (
        <p className="text-sm text-slate-500 text-center py-8">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed border-slate-200 rounded-lg">
          <Sparkles className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No custom rates yet.</p>
          <p className="text-xs text-slate-400 mt-1">All partners are using their default commission rates.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="cc-table">
            <thead className="bg-slate-100">
              <tr className="text-[10px] uppercase text-slate-500">
                <th className="text-left px-3 py-2">Partner</th>
                <th className="text-left px-3 py-2">Product</th>
                <th className="text-center px-3 py-2">Custom Rate</th>
                <th className="text-right px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <CustomRateRow key={`${r.partner_id}-${r.product_id}`} row={r} index={i} onSave={updateRate} onRemove={remove} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <span>
          These per-partner-per-product rates <strong>override</strong> the partner&apos;s default commission percentage.
          Remove the row to fall back to the default rate.
        </span>
      </div>
    </Card>
  );
}


function CustomRateRow({ row, index, onSave, onRemove }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(row.commission_rate);

  return (
    <tr className="border-t hover:bg-slate-50" data-testid={`cc-row-${index}`}>
      <td className="px-3 py-2 font-medium">{row.partner_name}</td>
      <td className="px-3 py-2">{row.product_name}</td>
      <td className="px-3 py-2 text-center">
        {editing ? (
          <Input
            type="number" min={0} max={100} step={0.5}
            value={val}
            onChange={e => setVal(e.target.value)}
            className="w-20 mx-auto h-7 text-center"
            data-testid={`cc-edit-input-${index}`}
          />
        ) : (
          <Badge className="bg-indigo-100 text-indigo-700">{row.commission_rate}%</Badge>
        )}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex gap-1 justify-end">
          {editing ? (
            <>
              <Button size="sm" className="h-7 px-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => { onSave(row, val); setEditing(false); }} data-testid={`cc-save-edit-${index}`}>
                <CheckCircle className="h-3.5 w-3.5" />
              </Button>
              <Button size="sm" variant="outline" className="h-7 px-2" onClick={() => { setEditing(false); setVal(row.commission_rate); }} data-testid={`cc-cancel-edit-${index}`}>
                <XCircle className="h-3.5 w-3.5" />
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" variant="outline" className="h-7 px-2" onClick={() => setEditing(true)} data-testid={`cc-edit-${index}`}>
                <Edit className="h-3.5 w-3.5" />
              </Button>
              <Button size="sm" variant="outline" className="h-7 px-2 text-rose-600 border-rose-200 hover:bg-rose-50" onClick={() => onRemove(row)} data-testid={`cc-delete-${index}`}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
