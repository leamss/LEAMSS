import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertTriangle, Clock, CheckCircle, Loader2, FileText,
  ArrowRight, Calendar, AlertCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SmartWorkload = ({ token, onSelectCase }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/cm-tools/workload`, { headers });
        setData(res.data);
      } catch (e) {
        toast.error('Failed to load workload');
      }
      setLoading(false);
    };
    load();
  }, []);

  if (loading || !data) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  const s = data.summary || {};

  const scoreColor = s.workload_score > 70 ? 'text-red-600' : s.workload_score > 40 ? 'text-amber-600' : 'text-emerald-600';
  const scoreBg = s.workload_score > 70 ? 'bg-red-50 border-red-200' : s.workload_score > 40 ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200';

  const CaseCard = ({ caseItem, color }) => (
    <Card className={`p-4 border-l-4 hover:shadow-md transition-shadow cursor-pointer`} style={{ borderLeftColor: color }}
      onClick={() => onSelectCase && onSelectCase(caseItem.id)}
      data-testid={`workload-case-${caseItem.case_id}`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-slate-800">{caseItem.case_id}</h4>
            <Badge className={
              caseItem.priority === 'overdue' ? 'bg-red-500 text-white' :
              caseItem.priority === 'due_today' ? 'bg-amber-500 text-white' :
              caseItem.priority === 'action_needed' ? 'bg-blue-500 text-white' :
              caseItem.priority === 'upcoming' ? 'bg-purple-100 text-purple-700' :
              'bg-emerald-100 text-emerald-700'
            }>{caseItem.priority?.replace('_', ' ')}</Badge>
          </div>
          <p className="text-sm text-slate-600">{caseItem.client_name} - {caseItem.product_name}</p>
          <p className="text-xs text-slate-500 mt-1">Step: {caseItem.current_step} ({caseItem.current_step_order}/{caseItem.total_steps})</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
            {caseItem.pending_docs > 0 && <span className="flex items-center gap-1 text-blue-600"><FileText className="h-3 w-3" />{caseItem.pending_docs} docs pending</span>}
            {caseItem.nearest_deadline && <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{caseItem.nearest_deadline}</span>}
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-slate-400" />
      </div>
    </Card>
  );

  const Section = ({ title, icon: Icon, cases, color, emptyMsg }) => (
    cases.length > 0 && (
      <div>
        <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color }} />{title}
          <Badge className="bg-slate-100 text-slate-700">{cases.length}</Badge>
        </h4>
        <div className="space-y-2">
          {cases.map(c => <CaseCard key={c.id} caseItem={c} color={color} />)}
        </div>
      </div>
    )
  );

  return (
    <div className="space-y-6" data-testid="smart-workload">
      {/* Workload Score + Summary */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <Card className={`p-4 text-center ${scoreBg} col-span-2 md:col-span-1`}>
          <p className="text-xs text-slate-600 mb-1">Workload</p>
          <p className={`text-3xl font-bold ${scoreColor}`}>{s.workload_score}</p>
          <p className="text-xs text-slate-500">/100</p>
        </Card>
        <Card className="p-3 text-center bg-red-50 border-red-200">
          <p className="text-xs text-red-600">Overdue</p>
          <p className="text-xl font-bold text-red-700">{s.overdue_count}</p>
        </Card>
        <Card className="p-3 text-center bg-amber-50 border-amber-200">
          <p className="text-xs text-amber-600">Due Today</p>
          <p className="text-xl font-bold text-amber-700">{s.due_today_count}</p>
        </Card>
        <Card className="p-3 text-center bg-blue-50 border-blue-200">
          <p className="text-xs text-blue-600">Action Needed</p>
          <p className="text-xl font-bold text-blue-700">{s.action_needed_count}</p>
        </Card>
        <Card className="p-3 text-center bg-purple-50 border-purple-200">
          <p className="text-xs text-purple-600">Upcoming</p>
          <p className="text-xl font-bold text-purple-700">{s.upcoming_count}</p>
        </Card>
        <Card className="p-3 text-center bg-emerald-50 border-emerald-200">
          <p className="text-xs text-emerald-600">On Track</p>
          <p className="text-xl font-bold text-emerald-700">{s.on_track_count}</p>
        </Card>
      </div>

      {/* Case Lists */}
      <div className="space-y-6">
        <Section title="Overdue" icon={AlertTriangle} cases={data.overdue} color="#dc2626" />
        <Section title="Due Today" icon={Clock} cases={data.due_today} color="#d97706" />
        <Section title="Action Needed" icon={AlertCircle} cases={data.action_needed} color="#2563eb" />
        <Section title="Upcoming (7 days)" icon={Calendar} cases={data.upcoming} color="#7c3aed" />
        <Section title="On Track" icon={CheckCircle} cases={data.on_track} color="#059669" />
      </div>

      {s.total_active === 0 && (
        <Card className="p-12 text-center">
          <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
          <p className="text-lg font-semibold text-slate-700">No Active Cases</p>
          <p className="text-slate-500">You're all caught up!</p>
        </Card>
      )}
    </div>
  );
};

export default SmartWorkload;
