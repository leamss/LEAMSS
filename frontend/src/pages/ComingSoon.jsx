import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Rocket, Target, IndianRupee, Trophy, PhoneCall } from 'lucide-react';

const FEATURE_INFO = {
  targets: {
    icon: Target,
    title: 'Targets & Goals',
    phase: '4B',
    eta: 'Next sprint',
    description: 'Admin will set monthly / quarterly / yearly targets per sales executive. You will see live progress against those targets here, with visual progress bars and milestone celebrations.',
    color: 'indigo',
  },
  commission: {
    icon: IndianRupee,
    title: 'Commission Engine',
    phase: '4C',
    eta: 'After targets',
    description: 'Configurable commission slabs per role with auto-calculation when PAs close. Manager → HR approval workflow. Includes TDS, bonuses, and deductions.',
    color: 'emerald',
  },
  leaderboard: {
    icon: Trophy,
    title: 'Leaderboard & Reports',
    phase: '4E',
    eta: 'Sales module finale',
    description: 'See your rank against team mates. Monthly / quarterly leaderboards. Department-wide reports for managers and heads.',
    color: 'amber',
  },
  call_log: {
    icon: PhoneCall,
    title: 'Call Log & Activity',
    phase: '4D',
    eta: 'After commission',
    description: 'Log every client touchpoint. Schedule follow-ups. Linked to PAs for full activity history. AI-powered call summaries (optional).',
    color: 'rose',
  },
};


export default function ComingSoon() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const feature = params.get('feature') || 'feature';
  const info = FEATURE_INFO[feature] || {
    icon: Rocket,
    title: 'Feature Coming Soon',
    phase: '?',
    eta: 'TBD',
    description: 'This feature is on our roadmap and will be available soon.',
    color: 'slate',
  };

  const Icon = info.icon;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="coming-soon-page">
      <header className="bg-white border-b border-slate-200 px-6 py-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/sales/dashboard')} data-testid="back-btn">
          <ArrowLeft className="h-4 w-4 mr-1.5" /> Back to Sales Dashboard
        </Button>
      </header>

      <main className="max-w-3xl mx-auto p-6 mt-6">
        <Card className="p-8 text-center">
          <div className={`w-20 h-20 rounded-full bg-${info.color}-100 flex items-center justify-center mx-auto mb-4`}>
            <Icon className={`h-10 w-10 text-${info.color}-600`} />
          </div>
          <Badge className="bg-amber-100 text-amber-800 font-bold uppercase tracking-wide mb-3">
            Phase {info.phase}
          </Badge>
          <h1 className="text-2xl font-bold text-slate-900 mb-2" data-testid="title">{info.title} — Coming Soon</h1>
          <p className="text-sm text-slate-500 mb-1">Estimated: <strong>{info.eta}</strong></p>
          <p className="text-sm text-slate-700 max-w-xl mx-auto mt-4 leading-relaxed">{info.description}</p>

          <div className="mt-8 pt-6 border-t border-slate-200">
            <h3 className="text-xs uppercase tracking-wide text-slate-500 font-bold mb-3">What's Available Now</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg mx-auto text-sm">
              <Button variant="outline" size="sm" onClick={() => navigate('/sales/dashboard')} data-testid="link-dashboard">📊 Sales Dashboard</Button>
              <Button variant="outline" size="sm" onClick={() => navigate('/portal/attendance')} data-testid="link-attendance">⏰ My Attendance</Button>
              <Button variant="outline" size="sm" onClick={() => navigate('/portal/leaves')} data-testid="link-leaves">🏖️ My Leaves</Button>
              <Button variant="outline" size="sm" onClick={() => navigate('/portal/welcome')} data-testid="link-portal">🏠 Portal Home</Button>
            </div>
          </div>
        </Card>
      </main>
    </div>
  );
}
