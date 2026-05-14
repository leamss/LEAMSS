/**
 * Phase 4C.3 — Admin Cost Allocations Dashboard.
 * Lists all PAs at case_created stage with their allocation breakdown.
 * Inline expand: shows vendors, amounts, assign vendor, approve, mark-paid.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { ArrowLeft, IndianRupee, CheckCircle, Clock, AlertTriangle, RefreshCw, Trophy, ChevronDown, ChevronRight, Search } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const STATUS_BADGE = {
  unassigned: { color: 'bg-slate-100 text-slate-700', icon: AlertTriangle, label: 'Unassigned' },
  pending: { color: 'bg-amber-100 text-amber-700', icon: Clock, label: 'Pending' },
  approved: { color: 'bg-indigo-100 text-indigo-700', icon: CheckCircle, label: 'Approved' },
  paid: { color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle, label: 'Paid' },
  disputed: { color: 'bg-rose-100 text-rose-700', icon: AlertTriangle, label: 'Disputed' },
};


function AssignVendorDialog({ open, onClose, paId, allocation, onAssigned }) {
  const [vendors, setVendors] = useState([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    (async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/vendors?category=${encodeURIComponent(allocation?.vendor_category || '')}&status=active`, { headers: { Authorization: `Bearer ${token}` } });
        setVendors(r.data.vendors || []);
      } catch (e) { toast.error('Failed to load vendors'); }
      finally { setLoading(false); }
    })();
  }, [open, allocation]);

  const handleAssign = async () => {
    if (!selected) { toast.error('Please select a vendor'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/pa/${paId}/allocations/${allocation.allocation_id}/assign-vendor`,
        { vendor_id: selected }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Vendor assigned');
      onAssigned();
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Assign failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="assign-vendor-dialog">
        <DialogHeader>
          <DialogTitle>Assign Vendor — {allocation?.label}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="bg-slate-50 p-3 rounded text-xs">
            <p>Category: <strong>{allocation?.vendor_category}</strong></p>
            <p>Amount: <strong>{formatINR(allocation?.total_amount)}</strong></p>
          </div>
          {loading ? <p className="text-sm text-slate-500">Loading vendors…</p> :
            vendors.length === 0 ? <p className="text-sm text-rose-600">No active vendors in this category. Please add one in Vendors tab first.</p> :
            <Select value={selected} onValueChange={setSelected}>
              <SelectTrigger data-testid="vendor-select"><SelectValue placeholder="Select a vendor" /></SelectTrigger>
              <SelectContent>
                {vendors.map(v => <SelectItem key={v.id} value={v.id}>{v.name} ({v.vendor_code})</SelectItem>)}
              </SelectContent>
            </Select>
          }
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleAssign} disabled={saving || !selected} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-assign-vendor">{saving ? 'Saving…' : 'Assign'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function AllocationRow({ paId, allocation, onChanged }) {
  const [assignOpen, setAssignOpen] = useState(false);
  const meta = STATUS_BADGE[allocation.status] || STATUS_BADGE.pending;
  const StatusIcon = meta.icon;

  const action = async (type, payload = {}) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/pa/${paId}/allocations/${allocation.allocation_id}/${type}`, payload,
        { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Marked as ${type}`);
      onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || `${type} failed`); }
  };

  return (
    <div className="grid grid-cols-12 gap-2 items-center py-2 border-b last:border-b-0 text-sm" data-testid={`alloc-row-${allocation.allocation_id}`}>
      <div className="col-span-3">
        <p className="font-medium text-slate-800">{allocation.label}</p>
        <p className="text-[11px] text-slate-500">{allocation.vendor_category}{allocation.is_optional && ' · Optional'}</p>
      </div>
      <div className="col-span-3">
        {allocation.vendor_name ? (
          <p className="text-xs"><span className="font-medium">{allocation.vendor_name}</span><span className="ml-1 text-slate-400">({allocation.vendor_type})</span></p>
        ) : (
          <span className="text-xs text-slate-400 italic">— unassigned —</span>
        )}
      </div>
      <div className="col-span-2 text-right">
        <p className="text-sm font-bold">{formatINR(allocation.total_amount)}</p>
        {allocation.bonus_amount > 0 && <p className="text-[10px] text-amber-600">incl. {formatINR(allocation.bonus_amount)} bonus</p>}
      </div>
      <div className="col-span-2">
        <Badge className={`${meta.color} text-[10px] flex items-center gap-1 w-fit`}><StatusIcon className="h-3 w-3" />{meta.label}</Badge>
      </div>
      <div className="col-span-2 flex gap-1 justify-end">
        {!allocation.vendor_id && (
          <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)} className="h-7 text-[11px] px-2" data-testid={`assign-${allocation.allocation_id}`}>Assign</Button>
        )}
        {allocation.vendor_id && allocation.status === 'pending' && (
          <Button size="sm" variant="outline" onClick={() => action('approve')} className="h-7 text-[11px] px-2" data-testid={`approve-${allocation.allocation_id}`}>Approve</Button>
        )}
        {allocation.vendor_id && allocation.status === 'approved' && (
          <Button size="sm" onClick={() => action('mark-paid', { payment_reference: prompt('Payment reference (NEFT/UPI/cheque):') || '' })} className="h-7 text-[11px] px-2 bg-emerald-600 hover:bg-emerald-700" data-testid={`pay-${allocation.allocation_id}`}>Pay</Button>
        )}
      </div>
      <AssignVendorDialog open={assignOpen} onClose={() => setAssignOpen(false)} paId={paId} allocation={allocation} onAssigned={onChanged} />
    </div>
  );
}


function PaAllocationCard({ pa, onChanged }) {
  const [expanded, setExpanded] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/pa/${pa.id}/allocations`, { headers: { Authorization: `Bearer ${token}` } });
      setData(r.data);
    } catch (e) { toast.error('Failed to load allocations'); }
    finally { setLoading(false); }
  };

  const toggle = () => {
    setExpanded(!expanded);
    if (!expanded && !data) load();
  };

  const handleVisaApproved = async () => {
    if (!window.confirm('Apply visa-approved success bonuses?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/pa/${pa.id}/allocations/visa-approved`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Success bonuses applied');
      load();
      onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const handleRecalc = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/pa/${pa.id}/allocations/recalculate`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Allocations recalculated');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  const allocs = data?.allocations?.allocations || [];
  const summary = data?.allocations?.summary || {};

  return (
    <Card className="p-4 mb-3" data-testid={`pa-alloc-card-${pa.id}`}>
      <div className="flex items-center justify-between cursor-pointer" onClick={toggle}>
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
          <div>
            <p className="font-semibold text-slate-800">{pa.client_name} <span className="ml-2 text-xs text-slate-500 font-normal">{pa.pa_number}</span></p>
            <p className="text-xs text-slate-500">{pa.country} · {pa.service_type} · Stage: <strong className="text-emerald-700">{pa.stage}</strong></p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Revenue</p>
          <p className="text-base font-bold text-emerald-700">{formatINR(pa.proposal_fee || pa.final_amount)}</p>
        </div>
      </div>
      {expanded && (
        <div className="mt-4 border-t pt-3" data-testid={`alloc-expand-${pa.id}`}>
          {loading ? <p className="text-sm text-slate-500">Loading…</p> :
            !data?.has_allocations ? (
              <div className="text-center p-4 text-sm">
                <p className="text-slate-500 mb-2">{data?.message || 'No allocations yet'}</p>
                <Button size="sm" onClick={handleRecalc} variant="outline" data-testid={`build-allocs-${pa.id}`}>Build Allocations</Button>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-4 gap-2 mb-3 text-xs">
                  <div className="bg-slate-50 p-2 rounded text-center"><p className="text-slate-500">Allocated</p><p className="font-bold">{formatINR(summary.total_allocated)}</p></div>
                  <div className="bg-amber-50 p-2 rounded text-center"><p className="text-amber-700">Pending</p><p className="font-bold">{formatINR(summary.total_pending)}</p></div>
                  <div className="bg-emerald-50 p-2 rounded text-center"><p className="text-emerald-700">Paid</p><p className="font-bold">{formatINR(summary.total_paid)}</p></div>
                  <div className="bg-indigo-50 p-2 rounded text-center"><p className="text-indigo-700">Company Margin</p><p className="font-bold">{formatINR(summary.company_margin)} <span className="text-[10px]">({summary.company_margin_percentage}%)</span></p></div>
                </div>
                <div className="grid grid-cols-12 gap-2 text-[10px] font-bold uppercase text-slate-500 border-b pb-1.5 mb-1">
                  <div className="col-span-3">Allocation</div>
                  <div className="col-span-3">Vendor</div>
                  <div className="col-span-2 text-right">Amount</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2 text-right">Action</div>
                </div>
                {allocs.map(a => <AllocationRow key={a.allocation_id} paId={pa.id} allocation={a} onChanged={() => { load(); onChanged(); }} />)}
                <div className="flex gap-2 mt-3 justify-end">
                  <Button size="sm" variant="outline" onClick={handleRecalc} className="text-xs h-8" data-testid={`recalc-${pa.id}`}><RefreshCw className="h-3 w-3 mr-1" />Recalc</Button>
                  {!data?.allocations?.milestones?.visa_approved && (
                    <Button size="sm" onClick={handleVisaApproved} className="text-xs h-8 bg-amber-600 hover:bg-amber-700" data-testid={`visa-approved-${pa.id}`}><Trophy className="h-3 w-3 mr-1" />Visa Approved (Apply Bonuses)</Button>
                  )}
                </div>
              </>
            )
          }
        </div>
      )}
    </Card>
  );
}


export default function AdminAllocations() {
  const navigate = useNavigate();
  const [pas, setPas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statsRefresh, setStatsRefresh] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      // Fetch case_created PAs (revenue confirmed) + proposal_paid (in case allocations exist before case)
      const r = await axios.get(`${API}/pre-assessment?stage=case_created`, { headers: { Authorization: `Bearer ${token}` } });
      const list = Array.isArray(r.data) ? r.data : (r.data.pre_assessments || r.data.items || []);
      setPas(list);
    } catch (e) { toast.error('Failed to load PAs'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [statsRefresh]);

  const filtered = pas.filter(p => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (p.client_name || '').toLowerCase().includes(s) || (p.pa_number || '').toLowerCase().includes(s);
  });

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="admin-allocations-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><IndianRupee className="h-7 w-7 text-indigo-600" />Vendor Cost Allocations</h1>
              <p className="text-sm text-slate-500 mt-1">Auto-generated when PA reaches <strong>case_created</strong>. Assign vendors → approve → mark paid.</p>
            </div>
          </div>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2 top-2.5 text-slate-400" />
            <Input placeholder="Search client / PA #" value={search} onChange={e => setSearch(e.target.value)} className="pl-8 w-64" data-testid="alloc-search" />
          </div>
        </div>

        {loading ? (
          <Card className="p-12 text-center text-slate-500">Loading active cases…</Card>
        ) : filtered.length === 0 ? (
          <Card className="p-12 text-center">
            <IndianRupee className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No active cases yet. Allocations are created when a PA reaches <strong>case_created</strong> stage.</p>
          </Card>
        ) : (
          <div data-testid="allocations-list">
            {filtered.map(pa => <PaAllocationCard key={pa.id} pa={pa} onChanged={() => setStatsRefresh(x => x + 1)} />)}
          </div>
        )}
      </div>
    </div>
  );
}
