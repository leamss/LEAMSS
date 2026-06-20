import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  AlertTriangle, MessageSquare, FileText, Clock, CheckCircle, 
  DollarSign, Users, ChevronRight, Zap, RefreshCw
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const QuickActions = ({ userRole, onNavigate, caseId = null }) => {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadQuickActions = async () => {
    setLoading(true);
    const quickActions = [];

    try {
      // Load tickets for all roles
      const ticketsRes = await axios.get(`${API}/tickets/my-tickets`, getAuthHeader());
      const openTickets = ticketsRes.data.filter(t => t.status === 'open' || t.status === 'in_progress');
      if (openTickets.length > 0) {
        quickActions.push({
          id: 'open-tickets',
          icon: MessageSquare,
          label: 'Open Tickets',
          count: openTickets.length,
          color: 'bg-blue-500',
          bgColor: 'bg-blue-50',
          textColor: 'text-blue-700',
          action: 'tickets',
          filter: { status: 'open', priority: '' },
          priority: openTickets.some(t => t.priority === 'urgent' || t.priority === 'high') ? 'high' : 'normal'
        });
      }

      // Role-specific actions
      if (userRole === 'admin') {
        // Pending sales approvals
        const salesRes = await axios.get(`${API}/sales/pending`, getAuthHeader());
        if (salesRes.data.length > 0) {
          quickActions.push({
            id: 'pending-sales',
            icon: DollarSign,
            label: 'Pending Sales',
            count: salesRes.data.length,
            color: 'bg-amber-500',
            bgColor: 'bg-amber-50',
            textColor: 'text-amber-700',
            action: 'sales',
            priority: 'high'
          });
        }

        // Expiring documents
        try {
          const expiringRes = await axios.get(`${API}/scheduler/expiring-documents`, getAuthHeader());
          const expiringDocs = expiringRes.data.documents || [];
          if (expiringDocs.length > 0) {
            quickActions.push({
              id: 'expiring-docs',
              icon: AlertTriangle,
              label: 'Expiring Documents',
              count: expiringDocs.length,
              color: 'bg-red-500',
              bgColor: 'bg-red-50',
              textColor: 'text-red-700',
              action: 'expiring',
              priority: 'urgent'
            });
          }
        } catch (e) {
          // Expiring docs endpoint may not exist
        }

        // All tickets stats
        try {
          const ticketStatsRes = await axios.get(`${API}/tickets/stats`, getAuthHeader());
          const urgentTickets = ticketStatsRes.data.high_priority || 0;
          if (urgentTickets > 0) {
            quickActions.push({
              id: 'urgent-tickets',
              icon: Zap,
              label: 'High Priority Tickets',
              count: urgentTickets,
              color: 'bg-orange-500',
              bgColor: 'bg-orange-50',
              textColor: 'text-orange-700',
              action: 'tickets',
              filter: { status: '', priority: 'high' },
              priority: 'urgent'
            });
          }
        } catch (e) {
          // Stats endpoint may fail
        }
      }

      if (userRole === 'case_manager') {
        // Pending document reviews
        const casesRes = await axios.get(`${API}/cases/my-cases`, getAuthHeader());
        let pendingReviews = 0;
        
        for (const c of casesRes.data) {
          try {
            const docsRes = await axios.get(`${API}/documents/case/${c.id}`, getAuthHeader());
            pendingReviews += docsRes.data.filter(d => d.status === 'uploaded' || d.status === 'pending' || d.status === 'pending_review').length;
          } catch (e) {
            // Skip if can't load docs
          }
        }
        
        if (pendingReviews > 0) {
          quickActions.push({
            id: 'pending-reviews',
            icon: FileText,
            label: 'Documents to Review',
            count: pendingReviews,
            color: 'bg-leamss-orange-500',
            bgColor: 'bg-leamss-orange-50',
            textColor: 'text-leamss-orange-700',
            action: 'pending-review',
            priority: 'high'
          });
        }

        // Cases in progress
        const activeCases = casesRes.data.filter(c => c.status === 'active' || c.status === 'in_progress');
        if (activeCases.length > 0) {
          quickActions.push({
            id: 'active-cases',
            icon: Users,
            label: 'Active Cases',
            count: activeCases.length,
            color: 'bg-teal-500',
            bgColor: 'bg-teal-50',
            textColor: 'text-teal-700',
            action: 'cases',
            priority: 'normal'
          });
        }
      }

      if (userRole === 'partner') {
        // Pending sales (submitted but not approved)
        const salesRes = await axios.get(`${API}/sales/my-sales`, getAuthHeader());
        const pendingSales = salesRes.data.filter(s => s.status === 'pending');
        if (pendingSales.length > 0) {
          quickActions.push({
            id: 'pending-sales',
            icon: Clock,
            label: 'Awaiting Approval',
            count: pendingSales.length,
            color: 'bg-amber-500',
            bgColor: 'bg-amber-50',
            textColor: 'text-amber-700',
            action: 'sales',
            priority: 'normal'
          });
        }

        // Approved sales this month
        const approvedSales = salesRes.data.filter(s => s.status === 'approved');
        if (approvedSales.length > 0) {
          quickActions.push({
            id: 'approved-sales',
            icon: CheckCircle,
            label: 'Approved Sales',
            count: approvedSales.length,
            color: 'bg-green-500',
            bgColor: 'bg-green-50',
            textColor: 'text-green-700',
            action: 'commission',
            priority: 'normal'
          });
        }
      }

      if (userRole === 'client') {
        // Pending document requests
        const casesRes = await axios.get(`${API}/cases/my-cases`, getAuthHeader());
        if (casesRes.data.length > 0) {
          const myCase = casesRes.data[0];
          const pendingDocs = (myCase.additional_doc_requests || []).filter(r => r.status === 'pending');
          
          if (pendingDocs.length > 0) {
            quickActions.push({
              id: 'pending-uploads',
              icon: AlertTriangle,
              label: 'Documents Required',
              count: pendingDocs.length,
              color: 'bg-orange-500',
              bgColor: 'bg-orange-50',
              textColor: 'text-orange-700',
              action: 'action',
              priority: 'high'
            });
          }

          // Documents under review
          const docsRes = await axios.get(`${API}/documents/case/${myCase.id}`, getAuthHeader());
          const underReview = docsRes.data.filter(d => d.status === 'pending_review' || d.status === 'uploaded');
          if (underReview.length > 0) {
            quickActions.push({
              id: 'under-review',
              icon: Clock,
              label: 'Under Review',
              count: underReview.length,
              color: 'bg-blue-500',
              bgColor: 'bg-blue-50',
              textColor: 'text-blue-700',
              action: 'uploaded',
              priority: 'normal'
            });
          }

          // Workflow progress
          const completedSteps = myCase.steps?.filter(s => s.status === 'completed').length || 0;
          const totalSteps = myCase.steps?.length || 1;
          if (completedSteps < totalSteps) {
            quickActions.push({
              id: 'workflow-progress',
              icon: CheckCircle,
              label: 'Workflow Progress',
              count: `${completedSteps}/${totalSteps}`,
              color: 'bg-teal-500',
              bgColor: 'bg-teal-50',
              textColor: 'text-teal-700',
              action: 'documents',
              priority: 'normal'
            });
          }
        }
      }

      // Sort by priority
      const priorityOrder = { urgent: 0, high: 1, normal: 2 };
      quickActions.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

      setActions(quickActions);
    } catch (error) {
      console.error('Failed to load quick actions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuickActions();
    // Refresh every 60 seconds
    const interval = setInterval(loadQuickActions, 60000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userRole]);

  if (loading) {
    return (
      <Card className="p-4 bg-gradient-to-r from-slate-50 to-white border-0 shadow-md">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="h-5 w-5 text-[#f7620b]" />
          <h3 className="font-semibold text-slate-800">Quick Actions</h3>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse flex-shrink-0 w-40 h-20 bg-slate-100 rounded-xl" />
          ))}
        </div>
      </Card>
    );
  }

  if (actions.length === 0) {
    return (
      <Card className="p-4 bg-gradient-to-r from-green-50 to-white border-0 shadow-md">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-500" />
          <h3 className="font-semibold text-slate-800">All Caught Up!</h3>
        </div>
        <p className="text-sm text-slate-500 mt-1">No pending actions at the moment.</p>
      </Card>
    );
  }

  return (
    <Card className="p-4 bg-gradient-to-r from-slate-50 to-white border-0 shadow-md" data-testid="quick-actions-widget">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-[#f7620b]" />
          <h3 className="font-semibold text-slate-800">Quick Actions</h3>
          <Badge className="bg-slate-100 text-slate-600 text-xs">{actions.length}</Badge>
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={loadQuickActions}
          className="text-slate-500 hover:text-slate-700"
          data-testid="refresh-quick-actions"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-200">
        {actions.map((action) => {
          const IconComponent = action.icon;
          return (
            <div
              key={action.id}
              onClick={() => onNavigate(action.action, action.filter || null)}
              className={`flex-shrink-0 p-3 rounded-xl cursor-pointer transition-all hover:scale-105 hover:shadow-md ${action.bgColor} border border-transparent hover:border-slate-200`}
              data-testid={`quick-action-${action.id}`}
            >
              <div className="flex items-center gap-3 min-w-[140px]">
                <div className={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center`}>
                  <IconComponent className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className={`text-lg font-bold ${action.textColor}`}>{action.count}</p>
                  <p className="text-xs text-slate-600 whitespace-nowrap">{action.label}</p>
                </div>
                <ChevronRight className={`h-4 w-4 ${action.textColor} opacity-50 ml-auto`} />
              </div>
              {action.priority === 'urgent' && (
                <div className="mt-2">
                  <Badge className="bg-red-500 text-white text-xs animate-pulse">Urgent</Badge>
                </div>
              )}
              {action.priority === 'high' && (
                <div className="mt-2">
                  <Badge className="bg-orange-500 text-white text-xs">Action Needed</Badge>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default QuickActions;
