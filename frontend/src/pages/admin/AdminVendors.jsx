/**
 * Phase 4C.1 — Admin Vendors Management page.
 * Lists all vendors with filters, search, stats. Click card → vendor detail.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { ArrowLeft, Briefcase, Plus, Search, Mail, Phone, Eye, Send, Power, PowerOff, Layers, Users, IndianRupee, Filter, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_COLORS = {
  sales_commission: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300',
  case_manager:     'bg-emerald-100 text-emerald-700 border-emerald-300',
  tutor:            'bg-blue-100 text-blue-700 border-blue-300',
  lawyer:           'bg-slate-100 text-slate-700 border-slate-300',
  translator:       'bg-amber-100 text-amber-700 border-amber-300',
  consultant:       'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-300',
  medical_examiner: 'bg-rose-100 text-rose-700 border-rose-300',
  courier:          'bg-orange-100 text-orange-700 border-orange-300',
  other:            'bg-neutral-100 text-neutral-700 border-neutral-300',
};

const TYPE_BADGE = { internal: 'bg-leamss-red-100 text-leamss-red-700', external: 'bg-cyan-100 text-cyan-700', freelancer: 'bg-pink-100 text-pink-700' };

const VendorCreateModal = ({ open, onClose, categories, onCreated, editing }) => {
  const [form, setForm] = useState({
    name: '', email: '', phone: '', category: '',
    vendor_type: 'external', specialization: '',
    default_payment_terms: { payment_type: 'flat', default_amount: 0, currency: 'INR' },
    bank_details: { account_holder: '', account_number: '', ifsc: '', bank_name: '' },
    pan_number: '', gst_number: '',
    tds_applicable: true, tds_rate: 10,
    can_login: false, notes: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      if (editing) {
        setForm({
          ...editing,
          specialization: (editing.specialization || []).join(', '),
          default_payment_terms: editing.default_payment_terms || { payment_type: 'flat', default_amount: 0, currency: 'INR' },
          bank_details: editing.bank_details || { account_holder: '', account_number: '', ifsc: '', bank_name: '' },
        });
      } else {
        setForm({
          name: '', email: '', phone: '', category: '',
          vendor_type: 'external', specialization: '',
          default_payment_terms: { payment_type: 'flat', default_amount: 0, currency: 'INR' },
          bank_details: { account_holder: '', account_number: '', ifsc: '', bank_name: '' },
          pan_number: '', gst_number: '',
          tds_applicable: true, tds_rate: 10,
          can_login: false, notes: '',
        });
      }
    }
  }, [open, editing]);

  const handleSave = async () => {
    if (!form.name || !form.email || !form.category) { toast.error('Name, email, category required'); return; }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        ...form,
        specialization: form.specialization ? form.specialization.split(',').map(s => s.trim()).filter(Boolean) : [],
        tds_rate: parseFloat(form.tds_rate) || 0,
        default_payment_terms: {
          ...form.default_payment_terms,
          default_amount: parseFloat(form.default_payment_terms.default_amount) || 0,
        },
      };
      if (editing) {
        await axios.patch(`${API}/vendors/${editing.id}`, payload, { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Vendor updated');
      } else {
        const resp = await axios.post(`${API}/vendors`, payload, { headers: { Authorization: `Bearer ${token}` } });
        toast.success('Vendor created');
        // Phase 4C — Show auto-created user credentials prominently
        if (resp.data?.auto_created_user?.temp_password) {
          const u = resp.data.auto_created_user;
          // Persistent alert + clipboard helper
          window.alert(
            `✅ Internal user auto-created!\n\n` +
            `📧 Email: ${u.email}\n` +
            `🔑 Temp Password: ${u.temp_password}\n\n` +
            `Please share these credentials with the user. They will be asked to change the password on first login.`
          );
        } else if (resp.data?.auto_created_user) {
          toast.info(resp.data.auto_created_user.message || 'Linked to existing user account');
        }
      }
      onCreated();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="vendor-modal">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Briefcase className="h-5 w-5 text-leamss-teal-600" />{editing ? 'Edit Vendor' : 'Add New Vendor'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div><Label className="text-sm font-bold">Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="vendor-name" /></div>
            <div><Label className="text-sm font-bold">Email *</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} data-testid="vendor-email" disabled={!!editing} /></div>
            <div><Label className="text-sm font-bold">Phone</Label><Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} data-testid="vendor-phone" /></div>
            <div>
              <Label className="text-sm font-bold">Category *</Label>
              <Select value={form.category} onValueChange={v => setForm({ ...form, category: v })} data-testid="vendor-category">
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>{categories.map(c => <SelectItem key={c.key} value={c.key}>{c.name} ({c.is_internal ? 'Internal' : 'External'})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-sm font-bold">Type</Label>
              <Select value={form.vendor_type} onValueChange={v => setForm({ ...form, vendor_type: v })} data-testid="vendor-type">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="external">External</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                  <SelectItem value="freelancer">Freelancer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label className="text-sm font-bold">Specialization (comma-sep)</Label><Input value={form.specialization} onChange={e => setForm({ ...form, specialization: e.target.value })} placeholder="canada_pr, australia" data-testid="vendor-specialization" /></div>
          </div>

          <div className="p-3 bg-slate-50 rounded-md border">
            <p className="text-xs font-bold uppercase text-slate-700 mb-2">Default Payment Terms</p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Type</Label>
                <Select value={form.default_payment_terms.payment_type} onValueChange={v => setForm({ ...form, default_payment_terms: { ...form.default_payment_terms, payment_type: v } })}>
                  <SelectTrigger data-testid="payment-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="flat">Flat</SelectItem>
                    <SelectItem value="percentage">Percentage</SelectItem>
                    <SelectItem value="hourly">Hourly</SelectItem>
                    <SelectItem value="per_document">Per Document</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Default Amount (₹)</Label><Input type="number" value={form.default_payment_terms.default_amount} onChange={e => setForm({ ...form, default_payment_terms: { ...form.default_payment_terms, default_amount: e.target.value } })} data-testid="payment-amount" /></div>
              <div><Label className="text-xs">Currency</Label><Input value={form.default_payment_terms.currency} disabled /></div>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-md border">
            <p className="text-xs font-bold uppercase text-slate-700 mb-2">Bank Details (encrypted at rest — masked on read)</p>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs">Account Holder</Label><Input value={form.bank_details.account_holder} onChange={e => setForm({ ...form, bank_details: { ...form.bank_details, account_holder: e.target.value } })} data-testid="bank-holder" /></div>
              <div><Label className="text-xs">Account #</Label><Input value={form.bank_details.account_number} onChange={e => setForm({ ...form, bank_details: { ...form.bank_details, account_number: e.target.value } })} data-testid="bank-account" /></div>
              <div><Label className="text-xs">IFSC</Label><Input value={form.bank_details.ifsc} onChange={e => setForm({ ...form, bank_details: { ...form.bank_details, ifsc: e.target.value } })} data-testid="bank-ifsc" /></div>
              <div><Label className="text-xs">Bank Name</Label><Input value={form.bank_details.bank_name} onChange={e => setForm({ ...form, bank_details: { ...form.bank_details, bank_name: e.target.value } })} data-testid="bank-name" /></div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div><Label className="text-xs">PAN</Label><Input value={form.pan_number} onChange={e => setForm({ ...form, pan_number: e.target.value })} placeholder="ABCDE1234F" /></div>
            <div><Label className="text-xs">GST (optional)</Label><Input value={form.gst_number} onChange={e => setForm({ ...form, gst_number: e.target.value })} /></div>
            <div><Label className="text-xs">TDS Rate %</Label><Input type="number" value={form.tds_rate} onChange={e => setForm({ ...form, tds_rate: e.target.value })} /></div>
            <div className="flex items-end gap-2 text-sm">
              <input type="checkbox" checked={form.can_login} onChange={e => setForm({ ...form, can_login: e.target.checked })} data-testid="can-login" />
              <span>Portal access</span>
            </div>
          </div>

          <div><Label className="text-xs">Notes</Label><Textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2} /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-vendor">{saving ? 'Saving…' : (editing ? 'Update' : 'Create')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const InviteDialog = ({ open, onClose, vendor }) => {
  const [link, setLink] = useState(null);
  const [sending, setSending] = useState(false);
  useEffect(() => { if (open) setLink(null); }, [open]);

  const send = async () => {
    setSending(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/vendors/${vendor.id}/send-portal-invite`, {}, { headers: { Authorization: `Bearer ${token}` } });
      // Phase 4C — Prefix with window origin if backend returned a relative path
      let url = r.data.invite_url || '';
      if (url.startsWith('/')) {
        url = `${window.location.origin}${url}`;
      }
      setLink(url);
      toast.success('Invite generated (email is MOCKED — copy link manually)');
    } catch (e) { toast.error(e?.response?.data?.detail || 'Invite failed'); } finally { setSending(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="invite-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Send className="h-5 w-5 text-leamss-teal-600" />Send Portal Invite</DialogTitle></DialogHeader>
        <p className="text-sm text-slate-600">
          Generate a 72h magic link for <strong>{vendor?.name}</strong> ({vendor?.email}).
          Email delivery is currently <Badge className="bg-amber-100 text-amber-700 text-[10px] uppercase">MOCKED</Badge> — copy link manually.
        </p>
        {link && (
          <div className="bg-emerald-50 border border-emerald-200 rounded p-3">
            <p className="text-xs font-bold text-emerald-800 mb-1">Invite link (valid 72h):</p>
            <input
              readOnly
              value={link}
              data-testid="invite-link-input"
              onFocus={(e) => e.target.select()}
              className="w-full bg-white border border-emerald-300 rounded px-2 py-1 text-xs font-mono text-slate-700 break-all"
            />
            <p className="text-[11px] text-emerald-700 mt-2">👆 Click on the link above and press <kbd className="bg-white px-1 rounded text-[10px] border">Ctrl+C</kbd> to copy. Then send it to the vendor.</p>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              data-testid="copy-invite-btn"
              onClick={async () => {
                try {
                  if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(link);
                    toast.success('Copied to clipboard');
                  } else {
                    // Fallback for sandboxed iframes / older browsers
                    const ta = document.createElement('textarea');
                    ta.value = link;
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    const ok = document.execCommand('copy');
                    document.body.removeChild(ta);
                    if (ok) toast.success('Copied to clipboard');
                    else toast.error('Clipboard blocked — please select the link above and press Ctrl+C');
                  }
                } catch {
                  toast.error('Clipboard blocked — please select the link above and press Ctrl+C');
                }
              }}
            >Copy</Button>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
          {!link && <Button onClick={send} disabled={sending} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="confirm-invite">{sending ? 'Sending…' : 'Generate Link'}</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default function AdminVendors() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [vendors, setVendors] = useState([]);
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState({ total: 0, active: 0, by_category: {} });
  const [filters, setFilters] = useState({ category: '', status: '', vendor_type: '', q: '' });
  const [editVendor, setEditVendor] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [inviteVendor, setInviteVendor] = useState(null);
  const [viewVendor, setViewVendor] = useState(null);  // Phase 4C — inline view dialog

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
      const [vRes, cRes] = await Promise.all([
        axios.get(`${API}/vendors?${params}`, { headers }),
        axios.get(`${API}/vendors/categories`, { headers }),
      ]);
      setVendors(vRes.data.vendors || []);
      setStats(vRes.data.stats || {});
      setCategories(cRes.data.categories || []);
    } catch (e) { toast.error('Failed to load vendors'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filters]);

  const toggleStatus = async (v) => {
    try {
      const token = localStorage.getItem('token');
      const action = v.status === 'active' ? 'deactivate' : 'activate';
      await axios.post(`${API}/vendors/${v.id}/${action}`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Vendor ${action}d`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Action failed'); }
  };

  const categoryMap = useMemo(() => categories.reduce((acc, c) => ({ ...acc, [c.key]: c }), {}), [categories]);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="admin-vendors-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Briefcase className="h-7 w-7 text-leamss-teal-600" /> Vendor Management
              </h1>
              <p className="text-sm text-slate-500 mt-1">Manage all internal & external vendors (sales commission, case managers, tutors, lawyers, …)</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => navigate('/admin/vendors/categories')} variant="outline" data-testid="manage-categories">
              <Layers className="h-4 w-4 mr-1.5" /> Categories
            </Button>
            <Button onClick={() => setCreateOpen(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="add-vendor-btn">
              <Plus className="h-4 w-4 mr-1.5" /> Add Vendor
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Card className="p-3" data-testid="stat-total"><p className="text-xs text-slate-500 uppercase font-bold">Total Vendors</p><p className="text-2xl font-extrabold text-slate-800">{stats.total || 0}</p></Card>
          <Card className="p-3 border-emerald-200" data-testid="stat-active"><p className="text-xs text-emerald-700 uppercase font-bold">Active</p><p className="text-2xl font-extrabold text-emerald-700">{stats.active || 0}</p></Card>
          <Card className="p-3 border-leamss-red-200" data-testid="stat-internal"><p className="text-xs text-leamss-red-700 uppercase font-bold">Internal</p><p className="text-2xl font-extrabold text-leamss-red-700">{(stats.by_category?.sales_commission || 0) + (stats.by_category?.case_manager || 0)}</p></Card>
          <Card className="p-3 border-cyan-200" data-testid="stat-external"><p className="text-xs text-cyan-700 uppercase font-bold">External</p><p className="text-2xl font-extrabold text-cyan-700">{Object.entries(stats.by_category || {}).filter(([k]) => !['sales_commission','case_manager'].includes(k)).reduce((a, [_, v]) => a + v, 0)}</p></Card>
        </div>

        {/* Filters */}
        <Card className="p-3 mb-4 flex flex-wrap items-center gap-3" data-testid="filters-bar">
          <Filter className="h-4 w-4 text-slate-500" />
          <Select value={filters.category || 'all'} onValueChange={v => setFilters({ ...filters, category: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-44" data-testid="filter-category"><SelectValue placeholder="All categories" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map(c => <SelectItem key={c.key} value={c.key}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filters.status || 'all'} onValueChange={v => setFilters({ ...filters, status: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-36" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
              <SelectItem value="blacklisted">Blacklisted</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filters.vendor_type || 'all'} onValueChange={v => setFilters({ ...filters, vendor_type: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-36" data-testid="filter-type"><SelectValue placeholder="Type" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="internal">Internal</SelectItem>
              <SelectItem value="external">External</SelectItem>
              <SelectItem value="freelancer">Freelancer</SelectItem>
            </SelectContent>
          </Select>
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <Input value={filters.q} onChange={e => setFilters({ ...filters, q: e.target.value })} placeholder="Search name/email/code..." className="pl-8" data-testid="filter-q" />
          </div>
        </Card>

        {/* Vendor cards */}
        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : vendors.length === 0 ? (
          <Card className="p-12 text-center" data-testid="empty-vendors">
            <Briefcase className="h-12 w-12 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-600 font-semibold">No vendors yet</p>
            <p className="text-sm text-slate-400 mt-1">Click "Add Vendor" to create the first one</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="vendors-grid">
            {vendors.map(v => {
              const cat = categoryMap[v.category];
              const catColor = CATEGORY_COLORS[v.category] || CATEGORY_COLORS.other;
              return (
                <Card key={v.id} className="p-5 hover:shadow-lg transition" data-testid={`vendor-card-${v.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-full bg-gradient-to-br from-leamss-teal-100 to-leamss-orange-100 flex items-center justify-center font-bold text-leamss-teal-700">
                        {(v.name || 'V')[0]}
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-800 leading-tight">{v.name}</h3>
                        <p className="text-[11px] text-slate-500 mt-0.5">{v.vendor_code}</p>
                      </div>
                    </div>
                    <Badge className={v.status === 'active' ? 'bg-emerald-100 text-emerald-700 text-[10px] uppercase font-bold' : 'bg-rose-100 text-rose-700 text-[10px] uppercase font-bold'} data-testid={`status-${v.id}`}>
                      {v.status}
                    </Badge>
                  </div>
                  <div className="space-y-1.5 text-sm mb-3">
                    <Badge className={`${catColor} text-[11px] uppercase font-bold border`}>{cat?.name || v.category}</Badge>
                    <Badge className={`${TYPE_BADGE[v.vendor_type] || 'bg-slate-100'} text-[10px] uppercase font-bold ml-1`}>{v.vendor_type}</Badge>
                    <p className="text-slate-700 flex items-center gap-1 mt-1"><Mail className="h-3.5 w-3.5 text-slate-400" />{v.email}</p>
                    {v.phone && <p className="text-slate-700 flex items-center gap-1"><Phone className="h-3.5 w-3.5 text-slate-400" />{v.phone}</p>}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 rounded p-2 mb-3">
                    <div><p className="text-slate-500 font-bold">This month</p><p className="text-slate-800 font-bold">₹{((v.performance || {}).total_paid_lifetime || 0).toLocaleString('en-IN')}</p></div>
                    <div><p className="text-slate-500 font-bold">Cases</p><p className="text-slate-800 font-bold">{(v.performance || {}).total_cases_handled || 0}</p></div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setViewVendor(v)} data-testid={`view-${v.id}`}><Eye className="h-3.5 w-3.5 mr-1" /> View</Button>
                    <Button size="sm" variant="outline" onClick={() => setEditVendor(v)} data-testid={`edit-${v.id}`}>Edit</Button>
                    {v.can_login && <Button size="sm" variant="outline" onClick={() => setInviteVendor(v)} data-testid={`invite-${v.id}`}><Send className="h-3.5 w-3.5" /></Button>}
                    <Button size="sm" variant={v.status === 'active' ? 'destructive' : 'outline'} onClick={() => toggleStatus(v)} data-testid={`toggle-${v.id}`}>
                      {v.status === 'active' ? <PowerOff className="h-3.5 w-3.5" /> : <Power className="h-3.5 w-3.5" />}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <VendorCreateModal
        open={createOpen || !!editVendor}
        onClose={() => { setCreateOpen(false); setEditVendor(null); }}
        categories={categories}
        editing={editVendor}
        onCreated={load}
      />
      {inviteVendor && <InviteDialog open={!!inviteVendor} onClose={() => setInviteVendor(null)} vendor={inviteVendor} />}
      {viewVendor && <VendorDetailDialog vendor={viewVendor} onClose={() => setViewVendor(null)} onEdit={() => { setEditVendor(viewVendor); setViewVendor(null); }} onInvite={() => { setInviteVendor(viewVendor); setViewVendor(null); }} categoryMap={categoryMap} />}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// Vendor Detail (inline dialog — no separate route, no admin logout)
// ═══════════════════════════════════════════════════════════════════════
function VendorDetailDialog({ vendor, onClose, onEdit, onInvite, categoryMap }) {
  const [assignments, setAssignments] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = localStorage.getItem('token');
        // Admin endpoint to inspect a vendor's assignments (uses payouts queue with vendor filter)
        const r = await axios.get(`${API}/payouts/queue?vendor_id=${vendor.id}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!cancelled) setAssignments(r.data);
      } catch (_) {
        // Silently fail — show basic info only
      } finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [vendor.id]);

  const cat = categoryMap[vendor.category];
  const bank = vendor.bank_details || {};
  const perf = vendor.performance || {};

  return (
    <Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-3xl" data-testid="vendor-detail-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <Briefcase className="h-5 w-5 text-leamss-teal-600" />
            {vendor.name}
            <Badge className="bg-slate-100 text-slate-700 font-mono text-[10px]">{vendor.vendor_code}</Badge>
            <Badge className={vendor.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}>{vendor.status}</Badge>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {/* Identity */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><p className="text-[10px] font-bold uppercase text-slate-500">Email</p><p className="text-slate-800 flex items-center gap-1"><Mail className="h-3.5 w-3.5 text-slate-400" />{vendor.email}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">Phone</p><p className="text-slate-800 flex items-center gap-1"><Phone className="h-3.5 w-3.5 text-slate-400" />{vendor.phone || '—'}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">Category</p><p>{cat?.name || vendor.category} {cat?.is_internal && <Badge className="bg-leamss-red-100 text-leamss-red-700 text-[10px] ml-1">internal</Badge>}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">Type</p><p className="capitalize">{vendor.vendor_type || '—'}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">PAN</p><p className="font-mono">{vendor.pan_number || '—'}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">GST</p><p className="font-mono">{vendor.gst_number || '—'}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">TDS Applicable</p><p>{vendor.tds_applicable ? `Yes (${vendor.tds_rate}%)` : 'No'}</p></div>
            <div><p className="text-[10px] font-bold uppercase text-slate-500">Linked User ID</p><p className="font-mono text-xs">{vendor.user_id || <span className="italic text-slate-400">— not linked —</span>}</p></div>
          </div>

          {/* Bank */}
          {(bank.account_number || bank.ifsc) && (
            <Card className="p-3 bg-slate-50">
              <p className="text-[10px] font-bold uppercase text-slate-500 mb-2 flex items-center gap-1"><IndianRupee className="h-3 w-3" />Bank Details</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-slate-500">Account Holder: </span><strong>{bank.account_holder || '—'}</strong></div>
                <div><span className="text-slate-500">Account #: </span><strong className="font-mono">{bank.account_number || '—'}</strong></div>
                <div><span className="text-slate-500">IFSC: </span><strong className="font-mono">{bank.ifsc || '—'}</strong></div>
                <div><span className="text-slate-500">Bank: </span><strong>{bank.bank_name || '—'}</strong></div>
              </div>
            </Card>
          )}

          {/* Performance */}
          <Card className="p-3 bg-gradient-to-br from-leamss-teal-50 to-emerald-50">
            <p className="text-[10px] font-bold uppercase text-slate-500 mb-2">Lifetime Performance</p>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div><p className="text-slate-500">Cases Handled</p><p className="text-lg font-extrabold text-leamss-teal-800">{perf.total_cases_handled || 0}</p></div>
              <div><p className="text-slate-500">Total Paid</p><p className="text-lg font-extrabold text-emerald-800">₹{(perf.total_paid_lifetime || 0).toLocaleString('en-IN')}</p></div>
              <div><p className="text-slate-500">Rating</p><p className="text-lg font-extrabold text-amber-700">{(perf.rating || 0).toFixed(1)} ★</p></div>
            </div>
          </Card>

          {/* Assignments */}
          <Card className="p-3">
            <p className="text-[10px] font-bold uppercase text-slate-500 mb-2 flex items-center gap-1"><Layers className="h-3 w-3" />Current Assignments</p>
            {loading ? <p className="text-xs text-slate-400">Loading…</p> :
              !assignments || assignments.count === 0 ? <p className="text-xs italic text-slate-400">No allocations assigned to this vendor yet.</p> :
              <div className="space-y-1">
                {assignments.rows.slice(0, 10).map((r, i) => (
                  <div key={i} className="flex justify-between items-center text-xs p-1.5 bg-slate-50 rounded">
                    <span><strong>{r.client_name}</strong> · {r.pa_number} · {r.label}</span>
                    <span className="flex items-center gap-1">
                      <Badge className={`text-[9px] ${r.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : r.status === 'approved' ? 'bg-leamss-teal-100 text-leamss-teal-700' : 'bg-amber-100 text-amber-700'}`}>{r.status}</Badge>
                      <strong>₹{r.amount.toLocaleString('en-IN')}</strong>
                    </span>
                  </div>
                ))}
                {assignments.count > 10 && <p className="text-[11px] text-slate-400 mt-1">… and {assignments.count - 10} more</p>}
              </div>
            }
          </Card>

          {vendor.notes && (
            <Card className="p-3 bg-amber-50/50">
              <p className="text-[10px] font-bold uppercase text-amber-700 mb-1">Internal Notes</p>
              <p className="text-xs text-slate-700 whitespace-pre-wrap">{vendor.notes}</p>
            </Card>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
          {vendor.can_login && <Button variant="outline" onClick={onInvite} data-testid="vd-invite"><Send className="h-3.5 w-3.5 mr-1" />Send Invite</Button>}
          <Button onClick={onEdit} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="vd-edit">Edit Vendor</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
