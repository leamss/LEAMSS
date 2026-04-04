import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, Gift, Tag, Users, Copy, Plus, Trash2, TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const MarketingDashboard = () => {
  const navigate = useNavigate();
  const [referralStats, setReferralStats] = useState(null);
  const [promos, setPromos] = useState([]);
  const [newPromo, setNewPromo] = useState({ code: '', discount_type: 'percentage', discount_value: 10, max_uses: 100 });
  const [showPromoDialog, setShowPromoDialog] = useState(false);
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, promosRes] = await Promise.all([
        axios.get(`${API}/marketing/referral/stats`, { headers }).catch(() => ({ data: null })),
        axios.get(`${API}/marketing/promos`, { headers }).catch(() => ({ data: [] }))
      ]);
      setReferralStats(statsRes.data);
      setPromos(promosRes.data || []);
    } catch (e) { console.error(e); }
  };

  const createPromo = async () => {
    if (!newPromo.code || newPromo.code.length < 3) { toast.error('Code must be at least 3 chars'); return; }
    try {
      await axios.post(`${API}/marketing/promo`, newPromo, { headers });
      toast.success('Promo code created!');
      setShowPromoDialog(false);
      setNewPromo({ code: '', discount_type: 'percentage', discount_value: 10, max_uses: 100 });
      loadData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to create'); }
  };

  const deletePromo = async (id) => {
    try {
      await axios.delete(`${API}/marketing/promo/${id}`, { headers });
      toast.success('Promo deactivated');
      loadData();
    } catch (e) { toast.error('Failed'); }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-gradient-to-r from-[#2a777a] to-[#236466] text-white p-4 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <Button variant="ghost" className="text-white hover:bg-white/20" onClick={() => navigate(-1)} data-testid="back-btn">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">Marketing & Promotions</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <Tabs defaultValue="referrals">
          <TabsList className="mb-6">
            <TabsTrigger value="referrals"><Gift className="h-4 w-4 mr-2" /> Referrals</TabsTrigger>
            <TabsTrigger value="promos"><Tag className="h-4 w-4 mr-2" /> Promo Codes</TabsTrigger>
          </TabsList>

          <TabsContent value="referrals" className="space-y-6">
            {/* Referral Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-6 bg-gradient-to-br from-[#2a777a] to-[#236466] text-white">
                <p className="text-sm opacity-80">Total Referral Codes</p>
                <p className="text-3xl font-bold mt-2">{referralStats?.total_codes || 0}</p>
              </Card>
              <Card className="p-6 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
                <p className="text-sm opacity-80">Total Referrals Used</p>
                <p className="text-3xl font-bold mt-2">{referralStats?.total_uses || 0}</p>
              </Card>
              <Card className="p-6 bg-gradient-to-br from-[#f7620b] to-[#e55a09] text-white">
                <p className="text-sm opacity-80">Conversion Rate</p>
                <p className="text-3xl font-bold mt-2">
                  {referralStats?.total_codes > 0 ? ((referralStats.total_uses / referralStats.total_codes) * 100).toFixed(0) : 0}%
                </p>
              </Card>
            </div>

            {/* Top Referrers */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-[#2a777a]" /> Top Referrers
              </h3>
              {referralStats?.top_referrers?.length > 0 ? (
                <div className="space-y-3">
                  {referralStats.top_referrers.map((r, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-8 h-8 bg-[#2a777a] text-white rounded-full flex items-center justify-center font-bold text-sm">{idx + 1}</span>
                        <span className="font-medium">{r.name}</span>
                      </div>
                      <span className="text-[#2a777a] font-bold">{r.count} referrals</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-slate-500 py-8">No referrals yet</p>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="promos" className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Promo Codes</h3>
              <Dialog open={showPromoDialog} onOpenChange={setShowPromoDialog}>
                <DialogTrigger asChild>
                  <Button className="bg-[#2a777a] hover:bg-[#236466]" data-testid="create-promo-btn">
                    <Plus className="h-4 w-4 mr-2" /> Create Promo
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>Create Promo Code</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <div><Label>Code</Label><Input value={newPromo.code} onChange={e => setNewPromo({ ...newPromo, code: e.target.value.toUpperCase() })} placeholder="e.g., WELCOME25" data-testid="promo-code-input" /></div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Discount Type</Label>
                        <Select value={newPromo.discount_type} onValueChange={v => setNewPromo({ ...newPromo, discount_type: v })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="percentage">Percentage (%)</SelectItem>
                            <SelectItem value="fixed">Fixed Amount (₹)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div><Label>Value</Label><Input type="number" value={newPromo.discount_value} onChange={e => setNewPromo({ ...newPromo, discount_value: parseFloat(e.target.value) || 0 })} /></div>
                    </div>
                    <div><Label>Max Uses</Label><Input type="number" value={newPromo.max_uses} onChange={e => setNewPromo({ ...newPromo, max_uses: parseInt(e.target.value) || 100 })} /></div>
                    <Button onClick={createPromo} className="w-full bg-[#2a777a] hover:bg-[#236466]" data-testid="save-promo-btn">Create</Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {promos.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {promos.map(promo => (
                  <Card key={promo.id} className={`p-5 ${promo.is_active ? '' : 'opacity-50'}`} data-testid={`promo-card-${promo.code}`}>
                    <div className="flex justify-between items-start mb-3">
                      <div className="bg-[#f7620b] text-white px-3 py-1 rounded-lg font-mono font-bold text-lg">{promo.code}</div>
                      {promo.is_active && (
                        <Button size="sm" variant="ghost" className="text-red-500" onClick={() => deletePromo(promo.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <p className="text-2xl font-bold text-slate-800">
                      {promo.discount_type === 'percentage' ? `${promo.discount_value}% OFF` : `₹${promo.discount_value} OFF`}
                    </p>
                    <div className="flex justify-between mt-3 text-sm text-slate-500">
                      <span>Uses: {promo.current_uses || 0}/{promo.max_uses}</span>
                      <span className={promo.is_active ? 'text-green-600' : 'text-red-500'}>{promo.is_active ? 'Active' : 'Inactive'}</span>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <Tag className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-600 font-medium">No promo codes yet</p>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default MarketingDashboard;
