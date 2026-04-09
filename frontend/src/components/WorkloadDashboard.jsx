import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertTriangle, FileText, Clock, CheckCircle, Eye, Calendar, Briefcase,
  TrendingUp, Loader2, RefreshCw
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TASK_CONFIG = {
  doc_review: { icon: Eye, color: 'border-l-blue-500 bg-blue-50', badge: 'bg-blue-500' },
  additional_doc: { icon: Clock, color: 'border-l-amber-500 bg-amber-50', badge: 'bg-amber-500' },
  expiry_alert: { icon: Calendar, color: 'border-l-red-500 bg-red-50', badge: 'bg-red-500' },
};

const PRIORITY_COLORS = {
  critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-amber-500', low: 'bg-gray-400',
};

const WorkloadDashboard = ({ onNavigateToCase, onNavigateToTab }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const fetchWorkload = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/cases/workload/summary`, getAuthHeader());
      setData(res.data);
    } catch (err) {
      console.error('Failed to load workload:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchWorkload(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6" data-testid="workload-dashboard">
      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-4 border border-gray-200 cursor-pointer hover:border-[#2a777a]/30 transition-all"
              onClick={() => onNavigateToTab?.('cases')}>
          <p className="text-xs font-semibold uppercase text-gray-500">Active Cases</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{data.active_cases}</p>
        </Card>
        <Card className="p-4 border border-gray-200 cursor-pointer hover:border-blue-300 transition-all"
              onClick={() => onNavigateToTab?.('pending-review')}>
          <p className="text-xs font-semibold uppercase text-gray-500">Pending Reviews</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{data.pending_reviews}</p>
        </Card>
        <Card className="p-4 border border-gray-200 cursor-pointer hover:border-red-300 transition-all"
              onClick={() => onNavigateToTab?.('expiry-alerts')}>
          <p className="text-xs font-semibold uppercase text-gray-500">Expiring Docs</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{data.expiring_documents}</p>
        </Card>
        <Card className="p-4 border border-gray-200">
          <p className="text-xs font-semibold uppercase text-gray-500">Awaiting Client</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{data.pending_additional_docs}</p>
        </Card>
        <Card className="p-4 border border-gray-200">
          <p className="text-xs font-semibold uppercase text-gray-500">Steps In Progress</p>
          <p className="text-2xl font-bold text-[#2a777a] mt-1">{data.in_progress_steps}</p>
        </Card>
      </div>

      {/* Urgent Tasks */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[#f7620b]" />
            Priority Tasks
            <Badge className="bg-[#f7620b] text-white text-xs">{data.total_urgent}</Badge>
          </h3>
          <Button variant="ghost" size="sm" onClick={fetchWorkload} className="h-7 text-xs text-gray-500">
            <RefreshCw className="h-3 w-3 mr-1" /> Refresh
          </Button>
        </div>
        {data.urgent_tasks.length === 0 ? (
          <Card className="p-8 text-center border border-gray-200">
            <CheckCircle className="h-10 w-10 mx-auto mb-2 text-green-400" />
            <p className="text-sm text-gray-500">All caught up! No urgent tasks.</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {data.urgent_tasks.map((task, idx) => {
              const cfg = TASK_CONFIG[task.type] || TASK_CONFIG.doc_review;
              const TaskIcon = cfg.icon;
              return (
                <Card key={idx}
                      className={`p-3 border-l-4 ${cfg.color} cursor-pointer hover:shadow-md transition-all`}
                      onClick={() => task.case_id && onNavigateToCase?.(task.case_id)}
                      data-testid={`task-${idx}`}
                >
                  <div className="flex items-center gap-3">
                    <TaskIcon className="h-4 w-4 flex-shrink-0 text-gray-600" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{task.title}</p>
                      <p className="text-xs text-gray-500">{task.subtitle}</p>
                    </div>
                    <Badge className={`${PRIORITY_COLORS[task.priority]} text-white text-[10px] px-1.5`}>
                      {task.priority}
                    </Badge>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Case Distribution */}
      {data.case_distribution && Object.keys(data.case_distribution).length > 0 && (
        <Card className="p-4 border border-gray-200">
          <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-[#2a777a]" /> Case Distribution
          </h3>
          <div className="flex gap-4">
            {Object.entries(data.case_distribution).map(([status, count]) => (
              <div key={status} className="flex-1 text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-xl font-bold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500 capitalize">{status.replace('_', ' ')}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default WorkloadDashboard;
