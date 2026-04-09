import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Users, Send, Plus, Loader2, Gift, Heart, Star, CheckCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ReferralProgram({ token, role }) {
  const [referrals, setReferrals] = useState([]);
  const [stats, setStats] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ referred_name: '', referred_email: '', referred_phone: '', service_interested: '', notes: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [refsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/referrals`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/referrals/stats`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setReferrals(await refsRes.json());
      setStats(await statsRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const submitReferral = async () => {
    if (!form.referred_name || !form.referred_email) return;
    try {
      const res = await fetch(`${API}/api/referrals`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form)
      });
      if (res.ok) {
        setShowForm(false);
        setForm({ referred_name: '', referred_email: '', referred_phone: '', service_interested: '', notes: '' });
        fetchData();
      }
    } catch (e) { console.error(e); }
  };

  const updateStatus = async (id, status) => {
    await fetch(`${API}/api/referrals/${id}/status?status=${status}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` } });
    fetchData();
  };

  const statusColor = { pending: 'bg-gray-100 text-gray-700', contacted: 'bg-blue-100 text-blue-700', converted: 'bg-green-100 text-green-700', expired: 'bg-red-100 text-red-700' };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="referral-program">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card><CardContent className="pt-4 text-center"><p className="text-3xl font-bold text-blue-500">{stats.total}</p><p className="text-xs text-gray-500">Total Referrals</p></CardContent></Card>
          <Card><CardContent className="pt-4 text-center"><p className="text-3xl font-bold text-green-500">{stats.converted}</p><p className="text-xs text-gray-500">Converted</p></CardContent></Card>
          <Card><CardContent className="pt-4 text-center"><p className="text-3xl font-bold text-purple-500">{stats.conversion_rate}%</p><p className="text-xs text-gray-500">Conversion Rate</p></CardContent></Card>
          <Card><CardContent className="pt-4 text-center"><p className="text-3xl font-bold text-amber-500">{stats.by_status?.pending || 0}</p><p className="text-xs text-gray-500">Pending</p></CardContent></Card>
        </div>
      )}

      {/* Refer Button */}
      <Button onClick={() => setShowForm(!showForm)} data-testid="new-referral-btn">
        <Gift className="w-4 h-4 mr-2" /> {showForm ? 'Cancel' : 'Refer Someone'}
      </Button>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Refer a Friend</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Friend's Full Name *" value={form.referred_name} onChange={e => setForm({ ...form, referred_name: e.target.value })} data-testid="referral-name" />
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Friend's Email *" value={form.referred_email} onChange={e => setForm({ ...form, referred_email: e.target.value })} data-testid="referral-email" />
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Phone Number" value={form.referred_phone} onChange={e => setForm({ ...form, referred_phone: e.target.value })} />
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Service they're interested in (e.g., Canada PR)" value={form.service_interested} onChange={e => setForm({ ...form, service_interested: e.target.value })} />
            <textarea className="w-full border rounded-md p-2 text-sm" rows={2} placeholder="Any additional notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
            <Button onClick={submitReferral} data-testid="submit-referral-btn"><Send className="w-4 h-4 mr-2" /> Submit Referral</Button>
          </CardContent>
        </Card>
      )}

      {/* Referral List */}
      <div className="space-y-3">
        {(Array.isArray(referrals) ? referrals : []).map(r => (
          <Card key={r.id} className="hover:shadow-sm transition-shadow">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{r.referred_name}</p>
                    <Badge className={statusColor[r.status] || ''}>{r.status}</Badge>
                    {r.reward_status === 'eligible' && <Badge className="bg-green-100 text-green-700"><Star className="w-3 h-3 mr-1" /> Reward Eligible</Badge>}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{r.referred_email} {r.referred_phone && `| ${r.referred_phone}`}</p>
                  {r.service_interested && <p className="text-xs text-gray-400">Interested in: {r.service_interested}</p>}
                  <p className="text-[10px] text-gray-400 mt-1">Referred {new Date(r.created_at).toLocaleDateString()}</p>
                </div>
                {role === 'admin' && r.status !== 'converted' && (
                  <div className="flex gap-1">
                    {r.status === 'pending' && <Button size="sm" variant="outline" onClick={() => updateStatus(r.id, 'contacted')}>Mark Contacted</Button>}
                    {r.status === 'contacted' && <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white" onClick={() => updateStatus(r.id, 'converted')}><CheckCircle className="w-3 h-3 mr-1" /> Convert</Button>}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {(!referrals || referrals.length === 0) && (
        <Card><CardContent className="py-8 text-center text-gray-500"><Heart className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>{role === 'client' ? 'Refer friends and earn rewards!' : 'No referrals yet.'}</p></CardContent></Card>
      )}
    </div>
  );
}
