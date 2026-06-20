import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Plus, CreditCard, FileText, Eye, CheckCircle, Send, XCircle,
  RefreshCw, User, Globe, Clock, ArrowRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const KANBAN_STAGES = [
  { key: 'new', label: 'New Leads', color: 'bg-slate-500', borderColor: 'border-slate-300', headerBg: 'bg-slate-50', icon: Plus },
  { key: 'payment_pending', label: 'Payment Pending', color: 'bg-amber-500', borderColor: 'border-amber-300', headerBg: 'bg-amber-50', icon: Clock },
  { key: 'payment_received', label: 'Paid', color: 'bg-blue-500', borderColor: 'border-blue-300', headerBg: 'bg-blue-50', icon: CreditCard },
  { key: 'under_review', label: 'Under Review', color: 'bg-leamss-orange-500', borderColor: 'border-leamss-orange-300', headerBg: 'bg-leamss-orange-50', icon: Eye },
  { key: 'approved', label: 'Approved', color: 'bg-emerald-500', borderColor: 'border-emerald-300', headerBg: 'bg-emerald-50', icon: CheckCircle },
  { key: 'proposal_sent', label: 'Proposal Sent', color: 'bg-teal-500', borderColor: 'border-teal-300', headerBg: 'bg-teal-50', icon: Send },
];

const LeadPipeline = () => {
  const [pipeline, setPipeline] = useState({});
  const [loading, setLoading] = useState(true);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/partner-analytics/pipeline-summary`, getAuthHeader());
      setPipeline(res.data || {});
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  const totalLeads = Object.values(pipeline).reduce((s, v) => s + (v?.count || 0), 0);

  return (
    <div className="space-y-4" data-testid="lead-pipeline">
      {/* Pipeline Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-800">Lead Pipeline</h3>
          <p className="text-sm text-slate-500">{totalLeads} total leads across all stages</p>
        </div>
        <button onClick={() => { setLoading(true); loadData(); }} className="text-sm text-[#2a777a] hover:underline flex items-center gap-1">
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: '400px' }}>
        {KANBAN_STAGES.map(stage => {
          const StageIcon = stage.icon;
          const stageData = pipeline[stage.key] || { count: 0, items: [] };
          const items = stageData.items || [];

          return (
            <div key={stage.key} className="flex-shrink-0 w-64" data-testid={`kanban-${stage.key}`}>
              {/* Column Header */}
              <div className={`${stage.headerBg} rounded-t-xl p-3 border ${stage.borderColor} border-b-0`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-6 h-6 ${stage.color} rounded-md flex items-center justify-center`}>
                      <StageIcon className="h-3.5 w-3.5 text-white" />
                    </div>
                    <span className="font-semibold text-sm text-slate-700">{stage.label}</span>
                  </div>
                  <Badge variant="outline" className="text-xs h-5">{stageData.count}</Badge>
                </div>
              </div>

              {/* Column Body */}
              <div className={`border ${stage.borderColor} border-t-0 rounded-b-xl bg-white p-2 space-y-2 min-h-[350px]`}>
                {items.length === 0 ? (
                  <div className="flex items-center justify-center h-32 text-slate-300">
                    <p className="text-xs">No leads</p>
                  </div>
                ) : (
                  items.map(item => (
                    <div key={item.id} className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer" data-testid={`lead-card-${item.id}`}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-7 h-7 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {(item.client_name || 'C')[0]}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-sm text-slate-800 truncate">{item.client_name}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
                        <Globe className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{item.country}</span>
                        <span className="text-slate-300">|</span>
                        <span className="truncate">{item.service_type}</span>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <Badge className="bg-slate-100 text-slate-600 text-xs h-5">{item.pa_number}</Badge>
                        <span className="text-xs text-slate-400">{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pipeline Summary Row */}
      <div className="flex items-center gap-2 px-2">
        {KANBAN_STAGES.map((stage, idx) => {
          const count = pipeline[stage.key]?.count || 0;
          return (
            <div key={stage.key} className="flex items-center">
              <div className={`h-2 rounded-full ${stage.color}`} style={{ width: `${Math.max(count * 20, 8)}px` }} />
              {idx < KANBAN_STAGES.length - 1 && <ArrowRight className="h-3 w-3 text-slate-300 mx-1" />}
            </div>
          );
        })}
        <span className="text-xs text-slate-400 ml-2">Pipeline flow</span>
      </div>
    </div>
  );
};

export default LeadPipeline;
