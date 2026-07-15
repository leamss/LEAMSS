// import { useState, useEffect, useCallback } from 'react';
// import axios from 'axios';
// import { Card } from '@/components/ui/card';
// import { Badge } from '@/components/ui/badge';
// import { 
//   Plus, CreditCard, FileText, Eye, CheckCircle, Send, XCircle,
//   RefreshCw, User, Globe, Clock, ArrowRight
// } from 'lucide-react';

// const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// // const KANBAN_STAGES = [
// //   { key: 'new', label: 'New Leads', color: 'bg-slate-500', borderColor: 'border-slate-300', headerBg: 'bg-slate-50', icon: Plus },
// //   { key: 'payment_pending', label: 'Payment Pending', color: 'bg-amber-500', borderColor: 'border-amber-300', headerBg: 'bg-amber-50', icon: Clock },
// //   { key: 'payment_received', label: 'Paid', color: 'bg-blue-500', borderColor: 'border-blue-300', headerBg: 'bg-blue-50', icon: CreditCard },
// //   { key: 'under_review', label: 'Under Review', color: 'bg-leamss-orange-500', borderColor: 'border-leamss-orange-300', headerBg: 'bg-leamss-orange-50', icon: Eye },
// //   { key: 'approved', label: 'Approved', color: 'bg-emerald-500', borderColor: 'border-emerald-300', headerBg: 'bg-emerald-50', icon: CheckCircle },
// //   { key: 'proposal_sent', label: 'Proposal Sent', color: 'bg-teal-500', borderColor: 'border-teal-300', headerBg: 'bg-teal-50', icon: Send },
// // ];
// const KANBAN_STAGES = [
//   { key: 'new', label: 'New Leads', color: 'bg-slate-500', borderColor: 'border-slate-300', headerBg: 'bg-slate-50', icon: Plus },
//   { key: 'payment_pending', label: 'Payment Pending', color: 'bg-amber-500', borderColor: 'border-amber-300', headerBg: 'bg-amber-50', icon: Clock },
//   { key: 'payment_received', label: 'Paid', color: 'bg-blue-500', borderColor: 'border-blue-300', headerBg: 'bg-blue-50', icon: CreditCard },
//   { key: 'under_review', label: 'Under Review', color: 'bg-leamss-orange-500', borderColor: 'border-leamss-orange-300', headerBg: 'bg-leamss-orange-50', icon: Eye },
//   { key: 'approved', label: 'Approved', color: 'bg-emerald-500', borderColor: 'border-emerald-300', headerBg: 'bg-emerald-50', icon: CheckCircle },
//   { key: 'proposal_sent', label: 'Proposal Sent', color: 'bg-teal-500', borderColor: 'border-teal-300', headerBg: 'bg-teal-50', icon: Send },
//   { key: 'proposal_paid', label: 'Proposal Paid', color: 'bg-cyan-500', borderColor: 'border-cyan-300', headerBg: 'bg-cyan-50', icon: CreditCard },
//   { key: 'awaiting_final_approval', label: 'Awaiting Final Approval', color: 'bg-indigo-500', borderColor: 'border-indigo-300', headerBg: 'bg-indigo-50', icon: Clock },
//   { key: 'case_created', label: 'Case Created', color: 'bg-green-600', borderColor: 'border-green-300', headerBg: 'bg-green-50', icon: CheckCircle },
//   { key: 'rejected', label: 'Rejected', color: 'bg-rose-500', borderColor: 'border-rose-300', headerBg: 'bg-rose-50', icon: XCircle },
//   { key: 'refunded', label: 'Refunded', color: 'bg-gray-500', borderColor: 'border-gray-300', headerBg: 'bg-gray-50', icon: XCircle },
// ];

// const LeadPipeline = () => {
//   const [pipeline, setPipeline] = useState({});
//   const [loading, setLoading] = useState(true);

//   const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

//   const loadData = useCallback(async () => {
//     try {
//       const res = await axios.get(`${API}/partner-analytics/pipeline-summary`, getAuthHeader());
//       setPipeline(res.data || {});
//     } catch (e) { console.error(e); }
//     setLoading(false);
//   }, []);

//   useEffect(() => { loadData(); }, [loadData]);

//   if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

//   const totalLeads = Object.values(pipeline).reduce((s, v) => s + (v?.count || 0), 0);

//   return (
//     <div className="space-y-4" data-testid="lead-pipeline">
//       {/* Pipeline Header */}
//       <div className="flex items-center justify-between">
//         <div>
//           <h3 className="text-lg font-bold text-slate-800">Lead Pipeline</h3>
//           <p className="text-sm text-slate-500">{totalLeads} total leads across all stages</p>
//         </div>
//         <button onClick={() => { setLoading(true); loadData(); }} className="text-sm text-[#2a777a] hover:underline flex items-center gap-1">
//           <RefreshCw className="h-3 w-3" /> Refresh
//         </button>
//       </div>

//       {/* Kanban Board */}
//       <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: '900px' }}>
  
//         {KANBAN_STAGES.map(stage => {
//           const StageIcon = stage.icon;
//           const stageData = pipeline[stage.key] || { count: 0, items: [] };
//           const items = stageData.items || [];

//           return (
//             <div key={stage.key} className="flex-shrink-0 w-64" data-testid={`kanban-${stage.key}`}>
//               {/* Column Header */}
//               <div className={`${stage.headerBg} rounded-t-xl p-3 border ${stage.borderColor} border-b-0`}>
//                 <div className="flex items-center justify-between">
//                   <div className="flex items-center gap-2">
//                     <div className={`w-6 h-6 ${stage.color} rounded-md flex items-center justify-center`}>
//                       <StageIcon className="h-3.5 w-3.5 text-white" />
//                     </div>
//                     <span className="font-semibold text-sm text-slate-700">{stage.label}</span>
//                   </div>
//                   <Badge variant="outline" className="text-xs h-5">{stageData.count}</Badge>
//                 </div>
//               </div>

//               {/* Column Body */}
//               <div className={`border ${stage.borderColor} border-t-0 rounded-b-xl bg-white p-2 space-y-2 min-h-[850px]`}>
//                 {items.length === 0 ? (
//                   <div className="flex items-center justify-center h-32 text-slate-300">
//                     <p className="text-xs">No leads</p>
//                   </div>
//                 ) : (
//                   items.map(item => (
//                     <div key={item.id} className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer" data-testid={`lead-card-${item.id}`}>
//                       <div className="flex items-center gap-2 mb-1.5">
//                         <div className="w-7 h-7 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
//                           {(item.client_name || 'C')[0]}
//                         </div>
//                         <div className="min-w-0">
//                           <p className="font-semibold text-sm text-slate-800 truncate">{item.client_name}</p>
//                         </div>
//                       </div>
//                       <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
//                         <Globe className="h-3 w-3 flex-shrink-0" />
//                         <span className="truncate">{item.country}</span>
//                         <span className="text-slate-300">|</span>
//                         <span className="truncate">{item.service_type}</span>
//                       </div>
//                       <div className="flex items-center justify-between mt-2">
//                         <Badge className="bg-slate-100 text-slate-600 text-xs h-5">{item.pa_number}</Badge>
//                         <span className="text-xs text-slate-400">{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</span>
//                       </div>
//                     </div>
//                   ))
//                 )}
//               </div>
//             </div>
//           );
//         })}
//       </div>

//       {/* Pipeline Summary Row */}
//       <div className="flex items-center gap-2 px-2">
//         {KANBAN_STAGES.map((stage, idx) => {
//           const count = pipeline[stage.key]?.count || 0;
//           return (
//             <div key={stage.key} className="flex items-center">
//               <div className={`h-2 rounded-full ${stage.color}`} style={{ width: `${Math.max(count * 20, 8)}px` }} />
//               {idx < KANBAN_STAGES.length - 1 && <ArrowRight className="h-3 w-3 text-slate-300 mx-1" />}
//             </div>
//           );
//         })}
//         <span className="text-xs text-slate-400 ml-2">Pipeline flow</span>
//       </div>
//     </div>
//   );
// };

// export default LeadPipeline;
import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Plus, CreditCard, FileText, Eye, CheckCircle, Send, XCircle,
  RefreshCw, Globe, Clock, LayoutGrid, List as ListIcon, Search, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGES = [
  { key: 'new', label: 'New Leads', color: 'bg-slate-500', text: 'text-slate-700', border: 'border-slate-300', bg: 'bg-slate-50', dot: 'bg-slate-500', icon: Plus },
  { key: 'payment_pending', label: 'Payment Pending', color: 'bg-amber-500', text: 'text-amber-700', border: 'border-amber-300', bg: 'bg-amber-50', dot: 'bg-amber-500', icon: Clock },
  { key: 'payment_received', label: 'Paid', color: 'bg-blue-500', text: 'text-blue-700', border: 'border-blue-300', bg: 'bg-blue-50', dot: 'bg-blue-500', icon: CreditCard },
  { key: 'under_review', label: 'Under Review', color: 'bg-orange-500', text: 'text-orange-700', border: 'border-orange-300', bg: 'bg-orange-50', dot: 'bg-orange-500', icon: Eye },
  { key: 'approved', label: 'Approved', color: 'bg-emerald-500', text: 'text-emerald-700', border: 'border-emerald-300', bg: 'bg-emerald-50', dot: 'bg-emerald-500', icon: CheckCircle },
  { key: 'proposal_sent', label: 'Proposal Sent', color: 'bg-red-500', text: 'text-teal-700', border: 'border-teal-300', bg: 'bg-teal-50', dot: 'bg-teal-500', icon: Send },
  { key: 'proposal_paid', label: 'Proposal Paid', color: 'bg-cyan-500', text: 'text-cyan-700', border: 'border-cyan-300', bg: 'bg-cyan-50', dot: 'bg-cyan-500', icon: CreditCard },
  { key: 'awaiting_final_approval', label: 'Awaiting Approval', color: 'bg-indigo-500', text: 'text-indigo-700', border: 'border-indigo-300', bg: 'bg-indigo-50', dot: 'bg-indigo-500', icon: Clock },
  { key: 'case_created', label: 'Case Created', color: 'bg-green-600', text: 'text-green-700', border: 'border-green-300', bg: 'bg-green-50', dot: 'bg-green-600', icon: CheckCircle },
  { key: 'rejected', label: 'Rejected', color: 'bg-rose-500', text: 'text-rose-700', border: 'border-rose-300', bg: 'bg-rose-50', dot: 'bg-rose-500', icon: XCircle },
  { key: 'refunded', label: 'Refunded', color: 'bg-gray-500', text: 'text-gray-700', border: 'border-gray-300', bg: 'bg-gray-50', dot: 'bg-gray-500', icon: XCircle },
];

const STAGE_MAP = Object.fromEntries(STAGES.map(s => [s.key, s]));

const LeadPipeline = ({ onLeadClick }) => {
  const [pipeline, setPipeline] = useState({});
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('list'); // 'list' | 'board'
  const [activeStage, setActiveStage] = useState('all');
  const [search, setSearch] = useState('');

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/partner-analytics/pipeline-summary`, getAuthHeader());
      setPipeline(res.data || {});
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const totalLeads = useMemo(() => Object.values(pipeline).reduce((s, v) => s + (v?.count || 0), 0), [pipeline]);

  // Flatten all leads into one list, each tagged with its stage
  const allLeads = useMemo(() => {
    const rows = [];
    STAGES.forEach(stage => {
      const items = pipeline[stage.key]?.items || [];
      items.forEach(item => rows.push({ ...item, _stage: stage.key }));
    });
    return rows.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [pipeline]);

  const filteredLeads = useMemo(() => {
    return allLeads.filter(lead => {
      if (activeStage !== 'all' && lead._stage !== activeStage) return false;
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const hay = `${lead.client_name || ''} ${lead.country || ''} ${lead.service_type || ''} ${lead.pa_number || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [allLeads, activeStage, search]);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-4" data-testid="lead-pipeline">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-800">Lead Pipeline</h3>
          <p className="text-sm text-slate-500">{totalLeads} total leads across all stages</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex items-center bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setView('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'list' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid="view-list-btn"
            >
              <ListIcon className="h-3.5 w-3.5" /> List
            </button>
            <button
              onClick={() => setView('board')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${view === 'board' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid="view-board-btn"
            >
              <LayoutGrid className="h-3.5 w-3.5" /> Board
            </button>
          </div>
          <button onClick={() => { setLoading(true); loadData(); }} className="text-sm text-[#2a777a] hover:underline flex items-center gap-1">
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        </div>
      </div>

      {/* Stage filter pills + search — shared across both views */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setActiveStage('all')}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${activeStage === 'all' ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'}`}
        >
          All ({totalLeads})
        </button>
        {STAGES.map(stage => {
          const count = pipeline[stage.key]?.count || 0;
          if (count === 0) return null;
          const active = activeStage === stage.key;
          return (
            <button
              key={stage.key}
              onClick={() => setActiveStage(active ? 'all' : stage.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${active ? `${stage.color} text-white border-transparent` : `bg-white ${stage.text} ${stage.border} hover:opacity-80`}`}
              data-testid={`filter-${stage.key}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-white' : stage.dot}`} />
              {stage.label} ({count})
            </button>
          );
        })}
        <div className="relative ml-auto w-full sm:w-56">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search leads..."
            className="pl-8 h-8 text-xs"
            data-testid="lead-search-input"
          />
        </div>
      </div>

      {/* LIST VIEW — scales to any number of leads without breaking layout */}
      {view === 'list' && (
        <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div className="hidden sm:grid grid-cols-[1fr_140px_160px_120px_110px] gap-3 px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <span>Client</span>
            <span>Stage</span>
            <span>Country / Type</span>
            <span>PA Number</span>
            <span>Date</span>
          </div>
          <div className="max-h-[560px] overflow-y-auto divide-y divide-slate-100">
            {filteredLeads.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-300">
                <FileText className="h-10 w-10 mb-2" />
                <p className="text-sm">No leads match this filter</p>
              </div>
            ) : (
              filteredLeads.map(lead => {
                const stage = STAGE_MAP[lead._stage] || STAGES[0];
                const StageIcon = stage.icon;
                return (
                  <div
                    key={lead.id}
                    onClick={() => onLeadClick && onLeadClick(lead)}
                    className="grid grid-cols-1 sm:grid-cols-[1fr_140px_160px_120px_110px] gap-2 sm:gap-3 items-center px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer"
                    data-testid={`lead-row-${lead.id}`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                        {(lead.client_name || 'C')[0].toUpperCase()}
                      </div>
                      <span className="font-semibold text-sm text-slate-800 truncate">{lead.client_name}</span>
                    </div>
                    <div>
                      <Badge className={`${stage.bg} ${stage.text} border-0 text-xs gap-1`}>
                        <StageIcon className="h-3 w-3" /> {stage.label}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 min-w-0">
                      <Globe className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{lead.country} · {lead.service_type}</span>
                    </div>
                    <div>
                      <span className="text-xs font-mono text-slate-500">{lead.pa_number}</span>
                    </div>
                    <div className="flex items-center justify-between sm:justify-start gap-2">
                      <span className="text-xs text-slate-400">{lead.created_at ? new Date(lead.created_at).toLocaleDateString() : ''}</span>
                      <ChevronRight className="h-3.5 w-3.5 text-slate-300 hidden sm:block" />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* BOARD VIEW — improved kanban, fixed-height scrollable columns */}
      {view === 'board' && (
        <div className="flex items-start gap-3 overflow-x-auto pb-4" style={{ minHeight: '400px' }}>
          {STAGES.filter(s => activeStage === 'all' || activeStage === s.key).map(stage => {
            const StageIcon = stage.icon;
            const stageData = pipeline[stage.key] || { count: 0, items: [] };
            const items = search.trim()
              ? (stageData.items || []).filter(item => `${item.client_name || ''} ${item.country || ''} ${item.service_type || ''} ${item.pa_number || ''}`.toLowerCase().includes(search.trim().toLowerCase()))
              : (stageData.items || []);

            return (
              <div key={stage.key} className="flex-shrink-0 w-64" data-testid={`kanban-${stage.key}`}>
                <div className={`${stage.bg} rounded-t-xl p-3 border ${stage.border} border-b-0`}>
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
                <div className={`border ${stage.border} border-t-0 rounded-b-xl bg-slate-50/50 p-2 space-y-2 min-h-[350px] max-h-[500px] overflow-y-auto`}>
                  {items.length === 0 ? (
                    <div className="flex items-center justify-center h-32 text-slate-300">
                      <p className="text-xs">No leads</p>
                    </div>
                  ) : (
                    items.map(item => (
                      <div key={item.id} onClick={() => onLeadClick && onLeadClick(item)} className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer" data-testid={`lead-card-${item.id}`}>
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
      )}
    </div>
  );
};

export default LeadPipeline;