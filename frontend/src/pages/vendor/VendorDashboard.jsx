/**
 * Phase 4C.6 — Vendor Portal Dashboard.
 * Self-service view for external vendors (tutors, lawyers, etc.) showing their assignments + payments.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LogOut, Briefcase, IndianRupee, FileText, Clock, CheckCircle, Sparkles, Building2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const STATUS_BADGE = {
  unassigned: 'bg-slate-100 text-slate-700',
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-indigo-100 text-indigo-700',
  paid: 'bg-emerald-100 text-emerald-700',
  disputed: 'bg-rose-100 text-rose-700',
};


export default function VendorDashboard() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [assignments, setAssignments] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    (async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [me, asg] = await Promise.all([
          axios.get(`${API}/vendor-portal/me`, { headers }),
          axios.get(`${API}/vendor-portal/my-assignments`, { headers }),
        ]);
        setProfile(me.data);
        setAssignments(asg.data);
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Failed to load portal');
        if (e?.response?.status === 401 || e?.response?.status === 403) navigate('/');
      } finally { setLoading(false); }
    })();
  }, [navigate]);

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Sparkles className="h-10 w-10 text-indigo-400 animate-pulse" /></div>;
  }
  if (!profile || !assignments) return null;

  const totals = assignments.totals || {};

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top bar */}
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center"><Briefcase className="h-5 w-5 text-indigo-600" /></div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Vendor Portal</p>
              <p className="font-bold text-slate-800">{profile.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className="bg-emerald-100 text-emerald-700">{profile.vendor_code}</Badge>
            <Button variant="outline" size="sm" onClick={logout} data-testid="logout-btn"><LogOut className="h-4 w-4 mr-1" />Logout</Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        {/* Greeting + headline */}
        <Card className="p-6 mb-4 bg-gradient-to-br from-indigo-50 via-blue-50 to-emerald-50 border-indigo-200" data-testid="vendor-greeting">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-extrabold text-slate-800">Hello, {profile.name.split(' ')[0]}!</h1>
              <p className="text-sm text-slate-600 mt-1">Here&apos;s an overview of your assignments and earnings with LEAMSS.</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                <Building2 className="h-3.5 w-3.5" />
                <span>{profile.category}</span>
                {profile.vendor_type && <Badge className="bg-slate-100 text-slate-700 text-[10px]">{profile.vendor_type}</Badge>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Lifetime Paid</p>
              <p className="text-4xl font-extrabold text-emerald-700" data-testid="lifetime-paid">{formatINR(assignments.lifetime_paid)}</p>
            </div>
          </div>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <Card className="p-4 bg-amber-50/50 border-amber-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-bold uppercase text-amber-700">Pending</p>
              <Clock className="h-4 w-4 text-amber-500" />
            </div>
            <p className="text-2xl font-extrabold text-amber-800" data-testid="pending-total">{formatINR(totals.pending)}</p>
          </Card>
          <Card className="p-4 bg-indigo-50/50 border-indigo-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-bold uppercase text-indigo-700">Approved</p>
              <FileText className="h-4 w-4 text-indigo-500" />
            </div>
            <p className="text-2xl font-extrabold text-indigo-800" data-testid="approved-total">{formatINR(totals.approved)}</p>
          </Card>
          <Card className="p-4 bg-emerald-50/50 border-emerald-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-bold uppercase text-emerald-700">Paid</p>
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-extrabold text-emerald-800" data-testid="paid-total">{formatINR(totals.paid)}</p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-bold uppercase text-slate-500">Active Cases</p>
              <IndianRupee className="h-4 w-4 text-slate-400" />
            </div>
            <p className="text-2xl font-extrabold text-slate-800" data-testid="active-cases">{assignments.count || 0}</p>
          </Card>
        </div>

        {/* Assignments table */}
        <Card className="p-5" data-testid="assignments-card">
          <h2 className="font-bold text-slate-800 mb-3">My Assignments</h2>
          {assignments.assignments.length === 0 ? (
            <div className="text-center py-10">
              <Briefcase className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No assignments yet. Once an admin assigns you to a case, it&apos;ll appear here.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-[10px] uppercase text-slate-500">
                    <th className="text-left py-2">PA / Client</th>
                    <th className="text-left py-2">Role</th>
                    <th className="text-right py-2">Amount</th>
                    <th className="text-center py-2">Status</th>
                    <th className="text-left py-2">Paid At</th>
                    <th className="text-left py-2">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.assignments.map((a, i) => (
                    <tr key={i} className="border-b last:border-b-0 hover:bg-slate-50" data-testid={`asg-row-${i}`}>
                      <td className="py-2"><p className="font-medium">{a.client_name}</p><p className="text-[10px] text-slate-500">{a.pa_number}</p></td>
                      <td className="py-2 text-xs">{a.label}</td>
                      <td className="py-2 text-right font-bold text-emerald-700">{formatINR(a.amount)}</td>
                      <td className="py-2 text-center"><Badge className={`${STATUS_BADGE[a.status]} text-[10px]`}>{a.status}</Badge></td>
                      <td className="py-2 text-[11px] text-slate-500">{a.paid_at ? new Date(a.paid_at).toLocaleDateString() : '—'}</td>
                      <td className="py-2 text-[11px] text-slate-500 font-mono">{a.payment_reference || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Bank details info */}
        {profile.bank_details && profile.bank_details.account_number && (
          <Card className="p-5 mt-4 bg-slate-50" data-testid="bank-details-card">
            <h3 className="font-bold text-sm text-slate-700 mb-2 flex items-center gap-2"><Building2 className="h-4 w-4" />Payment Account on File</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><p className="text-slate-500">Account Holder</p><p className="font-medium">{profile.bank_details.account_holder || '—'}</p></div>
              <div><p className="text-slate-500">Account #</p><p className="font-mono">{profile.bank_details.account_number}</p></div>
              <div><p className="text-slate-500">IFSC</p><p className="font-mono">{profile.bank_details.ifsc || '—'}</p></div>
              <div><p className="text-slate-500">Bank</p><p>{profile.bank_details.bank_name || '—'}</p></div>
            </div>
            <p className="text-[11px] text-slate-400 mt-3">To update bank details, please contact your administrator.</p>
          </Card>
        )}
      </main>
    </div>
  );
}
