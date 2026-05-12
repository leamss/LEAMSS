import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ClipboardCheck, Send, Users, TrendingUp, ArrowRight,
  Sparkles, Clock, CheckCircle, AlertCircle, Plus, IndianRupee
} from 'lucide-react';
import DropoffRecoveryWidget from '@/components/DropoffRecoveryWidget';
import IncentiveTierWidget from '@/components/sales/IncentiveTierWidget';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const ActionCard = ({ icon: Icon, title, count, description, cta, color, onClick, testId, highlight }) => (
  <Card
    className={`p-5 border-0 shadow-lg bg-gradient-to-br ${color} text-white cursor-pointer transition-all hover:shadow-xl hover:-translate-y-0.5 ${highlight ? 'ring-2 ring-pink-300 ring-offset-2 animate-pulse' : ''}`}
    onClick={onClick}
    data-testid={testId}
  >
    <div className="flex items-start justify-between">
      <div>
        <Icon className="h-8 w-8 opacity-80 mb-3" />
        <p className="text-4xl font-bold tabular-nums">{count}</p>
        <p className="text-sm font-semibold mt-1">{title}</p>
        <p className="text-xs opacity-80 mt-1 leading-relaxed">{description}</p>
      </div>
      <ArrowRight className="h-5 w-5 opacity-60" />
    </div>
    <div className="flex items-center gap-1 text-xs font-semibold mt-3 pt-3 border-t border-white/20">
      {cta} <ArrowRight className="h-3 w-3" />
    </div>
  </Card>
);

export default function PartnerHome({ user, onNavigate }) {
  const [data, setData] = useState({
    partner_review: 0,
    approved: 0,
    proposal_sent: 0,
    proposal_paid: 0,
    new_leads: 0,
    active_sales: 0,
    pending_amount: 0,
    this_month_revenue: 0,
    total_clients: 0,
    conversion_rate: 0,
  });
  const [recentPAs, setRecentPAs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [paRes, statsRes] = await Promise.all([
          axios.get(`${API}/pre-assessment/my-assessments`, getAuth()),
          axios.get(`${API}/pre-assessment/stats/overview`, getAuth()).catch(() => ({ data: {} })),
        ]);
        const pas = paRes.data || [];
        const partner_review = pas.filter(p => p.stage === 'partner_review').length;
        const approved = pas.filter(p => p.stage === 'approved').length;
        const proposal_sent = pas.filter(p => p.stage === 'proposal_sent').length;
        const proposal_paid = pas.filter(p => p.stage === 'proposal_paid').length;
        const new_leads = pas.filter(p => ['new', 'payment_pending'].includes(p.stage)).length;
        setRecentPAs(pas.slice(0, 5));
        setData(d => ({
          ...d,
          partner_review, approved, proposal_sent, proposal_paid, new_leads,
          conversion_rate: statsRes.data?.conversion_rate || 0,
          total_clients: pas.length,
        }));
      } catch (e) { /* graceful */ }
      setLoading(false);
    })();
  }, []);

  const greeting = (() => {
    const h = new Date().getHours();
    return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
  })();

  const totalActions = data.partner_review + data.approved + data.new_leads + data.proposal_paid;

  return (
    <div className="space-y-6" data-testid="partner-home">
      {/* Greeting + summary */}
      <div className="bg-gradient-to-r from-[#2a777a] to-[#1f5c5f] rounded-2xl p-6 text-white shadow-xl">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm opacity-80">{greeting}, Partner 👋</p>
            <h1 className="text-3xl font-bold mt-1">{user?.name?.split(' ')[0] || 'there'}!</h1>
            <p className="text-sm opacity-90 mt-2">
              {totalActions > 0
                ? <>You have <span className="font-bold text-[#f7620b] bg-white px-1.5 py-0.5 rounded">{totalActions}</span> pending actions today.</>
                : <>All caught up! Start a new pre-assessment to grow your pipeline.</>
              }
            </p>
          </div>
          <Button onClick={() => onNavigate?.('pre-assessment')} className="bg-[#f7620b] hover:bg-[#e55a09] shadow-lg" data-testid="home-create-pa">
            <Plus className="h-4 w-4 mr-1.5" /> New Pre-Assessment
          </Button>
        </div>
      </div>

      {/* Action cards */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-3 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[#f7620b]" /> Actions waiting for you
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.partner_review > 0 && (
            <ActionCard
              icon={AlertCircle}
              title="Review client docs"
              count={data.partner_review}
              description="Clients have uploaded documents — review & forward to Admin."
              cta="Review now"
              color="from-pink-500 to-pink-600"
              onClick={() => onNavigate?.('pre-assessment', 'partner_review')}
              testId="action-partner-review"
              highlight
            />
          )}
          {data.approved > 0 && (
            <ActionCard
              icon={Send}
              title="Send proposals"
              count={data.approved}
              description="Admin approved — send personalised proposals to clients."
              cta="Send proposals"
              color="from-emerald-500 to-emerald-600"
              onClick={() => onNavigate?.('pre-assessment', 'approved')}
              testId="action-send-proposal"
            />
          )}
          {data.new_leads > 0 && (
            <ActionCard
              icon={Users}
              title="Follow-up leads"
              count={data.new_leads}
              description="Pending payment — nudge clients via WhatsApp/Email."
              cta="Follow up"
              color="from-amber-500 to-amber-600"
              onClick={() => onNavigate?.('pre-assessment', 'payment_pending')}
              testId="action-new-leads"
            />
          )}
          {data.proposal_paid > 0 && (
            <ActionCard
              icon={CheckCircle}
              title="Payments received"
              count={data.proposal_paid}
              description="Client paid main fee — awaiting Admin case creation."
              cta="View progress"
              color="from-[#f7620b] to-orange-600"
              onClick={() => onNavigate?.('pre-assessment', 'proposal_paid')}
              testId="action-proposal-paid"
            />
          )}
          {totalActions === 0 && !loading && (
            <Card className="md:col-span-4 p-8 text-center bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
              <CheckCircle className="h-12 w-12 text-emerald-500 mx-auto mb-2" />
              <h3 className="font-bold text-slate-800">Inbox Zero! 🎉</h3>
              <p className="text-sm text-slate-500 mt-1">No pending actions. Time to create new opportunities.</p>
            </Card>
          )}
        </div>
      </div>

      {/* Quick access */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-3">Quick access</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { icon: ClipboardCheck, label: 'Pre-Assessments', tab: 'pre-assessment' },
            { icon: Users, label: 'Lead Pipeline', tab: 'lead-pipeline' },
            { icon: IndianRupee, label: 'My Sales', tab: 'sales' },
            { icon: TrendingUp, label: 'My Performance', tab: 'performance' },
          ].map(x => (
            <Card
              key={x.tab}
              onClick={() => onNavigate?.(x.tab)}
              className="p-4 cursor-pointer hover:shadow-md hover:border-[#2a777a]/30 transition-all border-slate-200"
              data-testid={`quick-${x.tab}`}
            >
              <x.icon className="h-5 w-5 text-[#2a777a] mb-2" />
              <p className="text-sm font-semibold text-slate-800">{x.label}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent assessments */}
      {recentPAs.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-slate-800">Recent pre-assessments</h2>
            <Button variant="ghost" size="sm" onClick={() => onNavigate?.('pre-assessment')} className="text-[#2a777a]">
              View all <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </div>
          <Card className="divide-y divide-slate-100 border-slate-200">
            {recentPAs.map(pa => (
              <div key={pa.id} className="p-4 flex items-center gap-4 hover:bg-slate-50 cursor-pointer" onClick={() => onNavigate?.('pre-assessment')}>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center text-sm font-bold text-slate-600 shrink-0">
                  {pa.client_name?.charAt(0).toUpperCase() || '?'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-800 truncate">{pa.client_name}</p>
                  <p className="text-xs text-slate-500">{pa.country} · {pa.service_type}</p>
                </div>
                <Badge className="bg-slate-100 text-slate-700 border-0 text-xs whitespace-nowrap capitalize">
                  {(pa.stage || '').replace(/_/g, ' ')}
                </Badge>
                <Clock className="h-3.5 w-3.5 text-slate-400 hidden sm:block" />
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* Drop-off Recovery */}
      {/* In-house Incentive Tier (employee-only, auto-hides for externals) */}
      <IncentiveTierWidget />

      <DropoffRecoveryWidget />
    </div>
  );
}
