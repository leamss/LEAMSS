import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, CreditCard, CheckCircle, Clock, AlertTriangle, IndianRupee } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EMITracker = ({ token }) => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadPlans = async () => {
    try {
      const res = await axios.get(`${API}/client-tools/emi/my-plans`, { headers });
      setPlans(res.data || []);
    } catch (e) {
      toast.error('Failed to load EMI plans');
    }
    setLoading(false);
  };

  useEffect(() => { loadPlans(); }, []);

  const handlePay = async (planId, installmentNo) => {
    setPaying(`${planId}-${installmentNo}`);
    try {
      await axios.post(`${API}/client-tools/emi/${planId}/pay-installment?installment_no=${installmentNo}`, {}, { headers });
      toast.success(`Installment #${installmentNo} paid!`);
      loadPlans();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Payment failed');
    }
    setPaying(null);
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (plans.length === 0) {
    return (
      <Card className="p-12 text-center" data-testid="emi-tracker">
        <CreditCard className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <p className="text-lg font-semibold text-slate-600">No EMI Plans</p>
        <p className="text-sm text-slate-400 mt-1">EMI payment plans will appear here when created by your administrator</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6" data-testid="emi-tracker">
      {plans.map((plan, pIdx) => {
        const progress = plan.installments > 0 ? (plan.paid_count / plan.installments * 100) : 0;
        return (
          <Card key={plan.id} className="p-6" data-testid={`emi-plan-${pIdx}`}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CreditCard className="h-5 w-5 text-[#2a777a]" />
                  <h4 className="font-semibold text-slate-800">EMI Plan — {plan.client_name}</h4>
                  <Badge className={plan.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}>{plan.status}</Badge>
                </div>
                <p className="text-sm text-slate-500">{plan.installments} installments of ₹{(plan.emi_amount || 0).toLocaleString()}/month</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-slate-800">₹{(plan.total_amount || 0).toLocaleString()}</p>
                <p className="text-xs text-emerald-600">Paid: ₹{(plan.total_paid || 0).toLocaleString()}</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex justify-between text-xs text-slate-500 mb-1">
                <span>{plan.paid_count}/{plan.installments} installments</span>
                <span>{progress.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div className="h-2.5 rounded-full bg-emerald-500 transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
            </div>

            {/* Schedule */}
            <div className="space-y-2">
              {(plan.schedule || []).map((s, idx) => {
                const isOverdue = s.status === 'pending' && s.due_date && new Date(s.due_date) < new Date();
                return (
                  <div key={idx} className={`flex items-center justify-between p-3 rounded-lg border ${
                    s.status === 'paid' ? 'bg-emerald-50 border-emerald-200' : isOverdue ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'
                  }`} data-testid={`installment-${pIdx}-${idx}`}>
                    <div className="flex items-center gap-3">
                      {s.status === 'paid' ? <CheckCircle className="h-5 w-5 text-emerald-500" /> : isOverdue ? <AlertTriangle className="h-5 w-5 text-red-500" /> : <Clock className="h-5 w-5 text-slate-400" />}
                      <div>
                        <p className="text-sm font-medium text-slate-800">Installment #{s.installment_no}</p>
                        <p className="text-xs text-slate-500">Due: {s.due_date ? new Date(s.due_date).toLocaleDateString() : '-'}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="font-semibold text-slate-800">₹{(s.amount || 0).toLocaleString()}</p>
                      {s.status === 'paid' ? (
                        <Badge className="bg-emerald-100 text-emerald-700">Paid</Badge>
                      ) : (
                        <Button size="sm" onClick={() => handlePay(plan.id, s.installment_no)}
                          disabled={paying === `${plan.id}-${s.installment_no}`}
                          className="bg-[#2a777a] hover:bg-[#236466] text-white"
                          data-testid={`pay-btn-${pIdx}-${idx}`}
                        >
                          {paying === `${plan.id}-${s.installment_no}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <IndianRupee className="h-4 w-4 mr-1" />}
                          Pay
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        );
      })}
    </div>
  );
};

export default EMITracker;
