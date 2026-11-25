import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import {
  ArrowLeft, RefreshCw, CheckCircle2, XCircle, Clock, AlertCircle,
  Search, Filter, Trash2, Edit3, Layers, Building2, User, Mail,
  Calendar, ShieldAlert, Sparkles, Database, ExternalLink, Check, MessageSquare
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const CATEGORY_LABELS = {
  all: 'All Categories',
  lead_capture: 'Lead Capture & Ads',
  communication: 'Communication & Meetings',
  payments: 'Payments & Billing',
  storage: 'Storage & Docs',
  analytics: 'Analytics & SEO',
  automation: 'Automation & APIs',
  ai: 'AI Tools',
  other: 'Other'
};

export default function IntegrationRequests() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [counts, setCounts] = useState({ total: 0, pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

  // Review Modal State
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [reviewStatus, setReviewStatus] = useState('approved');
  const [reviewPriority, setReviewPriority] = useState('medium');
  const [adminNotes, setAdminNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  const authHeaders = useMemo(() => {
    const token = localStorage.getItem('token');
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  }, []);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/integrations/requests`, authHeaders);
      if (res.data?.success) {
        setRequests(res.data.requests || []);
        if (res.data.counts) {
          setCounts(res.data.counts);
        }
      }
    } catch (e) {
      toast.error('Failed to load integration requests from database.');
    } finally {
      setLoading(false);
    }
  }, [authHeaders]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleOpenReview = (req) => {
    setSelectedRequest(req);
    setReviewStatus(req.status === 'pending_review' ? 'approved' : req.status);
    setReviewPriority(req.priority || 'medium');
    setAdminNotes(req.admin_notes || '');
    setReviewModalOpen(true);
  };

  const handleQuickStatusChange = async (reqId, newStatus) => {
    try {
      const res = await axios.patch(`${API}/integrations/requests/${reqId}`, {
        status: newStatus,
        admin_notes: newStatus === 'approved' ? 'Approved by Admin for CRM engineering evaluation.' : 'Request rejected by Admin.'
      }, authHeaders);

      if (res.data?.success) {
        toast.success(`Request marked as ${newStatus.toUpperCase()}`);
        fetchRequests();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update request status');
    }
  };

  const handleSaveReview = async () => {
    if (!selectedRequest) return;
    setSubmittingReview(true);
    try {
      const res = await axios.patch(`${API}/integrations/requests/${selectedRequest.id}`, {
        status: reviewStatus,
        priority: reviewPriority,
        admin_notes: adminNotes
      }, authHeaders);

      if (res.data?.success) {
        toast.success(`Request for "${selectedRequest.tool_name}" updated to ${reviewStatus.toUpperCase()}!`);
        setReviewModalOpen(false);
        fetchRequests();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save review');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleDeleteRequest = async (reqId, toolName) => {
    if (!window.confirm(`Are you sure you want to permanently delete the request for "${toolName}"?`)) {
      return;
    }
    try {
      const res = await axios.delete(`${API}/integrations/requests/${reqId}`, authHeaders);
      if (res.data?.success) {
        toast.success(`Request for "${toolName}" deleted.`);
        fetchRequests();
      }
    } catch (e) {
      toast.error('Failed to delete request');
    }
  };

  // Filter requests locally by search, status, and category
  const filteredRequests = useMemo(() => {
    return requests.filter(r => {
      if (statusFilter !== 'all') {
        if (statusFilter === 'pending') {
          if (r.status !== 'pending' && r.status !== 'pending_review') return false;
        } else if (r.status !== statusFilter) {
          return false;
        }
      }
      if (categoryFilter !== 'all' && r.category !== categoryFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = (r.tool_name || '').toLowerCase().includes(q);
        const matchesRequester = (r.requested_by_name || '').toLowerCase().includes(q) || (r.requested_by || '').toLowerCase().includes(q);
        const matchesUseCase = (r.use_case || '').toLowerCase().includes(q);
        const matchesCategory = (r.category || '').toLowerCase().includes(q);
        if (!matchesName && !matchesRequester && !matchesUseCase && !matchesCategory) {
          return false;
        }
      }
      return true;
    });
  }, [requests, statusFilter, categoryFilter, searchQuery]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* ── TOP HEADER ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/sales/integrations')}
                className="h-8 w-8 p-0 text-slate-500 hover:text-slate-800"
                title="Return to Integrations Hub"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                <span>Integration Requests</span>
                <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 font-semibold text-xs border-indigo-200">
                  Admin Review Queue
                </Badge>
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 pl-11">
              Review, approve, or reject third-party platforms requested by team members and sales executives.
            </p>
          </div>

          <div className="flex items-center gap-3 pl-11 md:pl-0 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/sales/integrations')}
              className="h-9 text-xs gap-1.5 border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              <Layers className="w-3.5 h-3.5 text-indigo-600" /> Integrations Hub
            </Button>
            <Button
              size="sm"
              onClick={fetchRequests}
              disabled={loading}
              className="h-9 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </div>

        {/* ── STORAGE VERIFICATION BANNER ── */}
        <div className="bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/50 p-4 rounded-xl flex items-start gap-3">
          <Database className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-blue-900 dark:text-blue-300">
              Verified Database Storage & Delivery
            </p>
            <p className="text-blue-700 dark:text-blue-400">
              Every request submitted via the Integrations Hub is permanently recorded in MongoDB database <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/60 rounded text-blue-900 dark:text-blue-200 font-mono font-semibold">leamss</code>, collection <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/60 rounded text-blue-900 dark:text-blue-200 font-mono font-semibold">integration_requests</code>. Upon submission, an instant in-app notification is routed to Administrators and CRM Engineering.
            </p>
          </div>
        </div>

        {/* ── KPI METRICS CARDS ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">Total Requests</p>
                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{counts.total}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300">
                <Layers className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-amber-200 bg-amber-50/40 dark:bg-amber-950/20 shadow-sm">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-amber-700 dark:text-amber-400">Pending Review</p>
                <h3 className="text-2xl font-bold text-amber-900 dark:text-amber-200 mt-1">{counts.pending}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center text-amber-700 dark:text-amber-300">
                <Clock className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-emerald-200 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-sm">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400">Approved</p>
                <h3 className="text-2xl font-bold text-emerald-900 dark:text-emerald-200 mt-1">{counts.approved}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-rose-200 bg-rose-50/40 dark:bg-rose-950/20 shadow-sm">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-rose-700 dark:text-rose-400">Rejected</p>
                <h3 className="text-2xl font-bold text-rose-900 dark:text-rose-200 mt-1">{counts.rejected}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-rose-100 dark:bg-rose-900/40 flex items-center justify-center text-rose-700 dark:text-rose-300">
                <XCircle className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── SEARCH & FILTER CONTROLS ── */}
        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <Input
              placeholder="Search by tool name, requester name, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9 text-xs bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Status Filter */}
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
              {['all', 'pending', 'approved', 'rejected'].map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                    statusFilter === st
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {st === 'all' ? 'All' : st === 'pending' ? 'Pending' : st.charAt(0).toUpperCase() + st.slice(1)}
                </button>
              ))}
            </div>

            {/* Category Filter */}
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-40 h-8 text-xs">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(CATEGORY_LABELS).map(([k, label]) => (
                  <SelectItem key={k} value={k} className="text-xs">{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* ── REQUESTS LIST / TABLE ── */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>Submitted Requests</span>
              <Badge variant="outline" className="text-[10px] font-semibold">{filteredRequests.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
                <span>Loading integration requests from database...</span>
              </div>
            ) : filteredRequests.length === 0 ? (
              <div className="py-16 text-center text-slate-400 text-xs">
                <Layers className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                <p className="font-semibold text-slate-600 dark:text-slate-300">No integration requests found</p>
                <p className="mt-1">When team members click "Request Tool" in the Integrations Hub, their requests will appear here.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredRequests.map((req) => {
                  const isPending = req.status === 'pending' || req.status === 'pending_review';
                  const isApproved = req.status === 'approved';
                  const isRejected = req.status === 'rejected';

                  const priorityColor =
                    req.priority === 'high' ? 'bg-red-50 text-red-700 border-red-200' :
                    req.priority === 'medium' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    'bg-slate-100 text-slate-600 border-slate-200';

                  const formattedDate = req.created_at ? new Date(req.created_at).toLocaleString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  }) : 'Unknown';

                  return (
                    <div key={req.id} className="p-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        {/* Left Details */}
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                              {req.tool_name}
                            </h3>
                            <Badge variant="outline" className="text-[11px] font-medium border-slate-200">
                              {CATEGORY_LABELS[req.category] || req.category}
                            </Badge>
                            <Badge variant="outline" className={`text-[10px] uppercase font-bold tracking-wider ${priorityColor}`}>
                              {req.priority || 'medium'} Priority
                            </Badge>

                            {/* Status Badge */}
                            {isPending && (
                              <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 gap-1 text-[11px] font-semibold">
                                <Clock className="w-3 h-3" /> Pending Review
                              </Badge>
                            )}
                            {isApproved && (
                              <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 gap-1 text-[11px] font-semibold">
                                <CheckCircle2 className="w-3 h-3" /> Approved
                              </Badge>
                            )}
                            {isRejected && (
                              <Badge className="bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 gap-1 text-[11px] font-semibold">
                                <XCircle className="w-3 h-3" /> Rejected
                              </Badge>
                            )}
                          </div>

                          {/* Use Case */}
                          {req.use_case && (
                            <p className="text-xs text-slate-600 dark:text-slate-300 italic bg-slate-50 dark:bg-slate-900/40 p-2 rounded-md border border-slate-100 dark:border-slate-800">
                              "{req.use_case}"
                            </p>
                          )}

                          {/* Requester Info & Date */}
                          <div className="flex items-center gap-4 text-[11px] text-slate-500 flex-wrap pt-0.5">
                            <span className="inline-flex items-center gap-1 font-medium text-slate-700 dark:text-slate-300">
                              <User className="w-3.5 h-3.5 text-slate-400" />
                              {req.requested_by_name || 'User'}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Mail className="w-3.5 h-3.5 text-slate-400" />
                              {req.requested_by}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5 text-slate-400" />
                              {formattedDate}
                            </span>
                            {req.company_id && (
                              <span className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-400">
                                <Building2 className="w-3 h-3" />
                                {req.company_id}
                              </span>
                            )}
                          </div>

                          {/* Admin Notes If Reviewed */}
                          {req.admin_notes && (
                            <div className="mt-2 text-xs text-indigo-900 dark:text-indigo-200 bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/40 p-2 rounded-lg flex items-start gap-2">
                              <MessageSquare className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" />
                              <div>
                                <span className="font-semibold text-indigo-950 dark:text-indigo-100">
                                  Admin Note ({req.reviewed_by_name || req.reviewed_by || 'Admin'}):
                                </span>{' '}
                                {req.admin_notes}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Right Actions */}
                        <div className="flex items-center gap-2 self-end lg:self-center shrink-0">
                          {isPending && (
                            <>
                              <Button
                                size="sm"
                                onClick={() => handleQuickStatusChange(req.id, 'approved')}
                                className="h-8 px-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1"
                                title="Approve Request"
                              >
                                <Check className="w-3.5 h-3.5" /> Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleQuickStatusChange(req.id, 'rejected')}
                                className="h-8 px-3 text-xs border-rose-200 text-rose-700 hover:bg-rose-50 font-semibold gap-1"
                                title="Reject Request"
                              >
                                <XCircle className="w-3.5 h-3.5" /> Reject
                              </Button>
                            </>
                          )}

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleOpenReview(req)}
                            className="h-8 text-xs gap-1 border-slate-200 text-slate-700 hover:bg-slate-100"
                            title="Edit Review & Notes"
                          >
                            <Edit3 className="w-3.5 h-3.5 text-slate-500" /> Review
                          </Button>

                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteRequest(req.id, req.tool_name)}
                            className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600"
                            title="Delete Request"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── REVIEW & NOTES DIALOG ── */}
        <Dialog open={reviewModalOpen} onOpenChange={setReviewModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-indigo-600" /> Review Integration Request
              </DialogTitle>
              <DialogDescription className="text-xs">
                Update status, engineering priority, and feedback notes for <strong>{selectedRequest?.tool_name}</strong>.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 pt-2">
              <div>
                <Label className="text-xs font-semibold">Review Status</Label>
                <Select value={reviewStatus} onValueChange={setReviewStatus}>
                  <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending_review">Pending Review (Under Evaluation)</SelectItem>
                    <SelectItem value="approved">Approved (Scheduled for Implementation)</SelectItem>
                    <SelectItem value="rejected">Rejected (Not Feasible / Redundant)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-semibold">Engineering Priority</Label>
                <Select value={reviewPriority} onValueChange={setReviewPriority}>
                  <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">High — Critical for daily sales/operations</SelectItem>
                    <SelectItem value="medium">Medium — Helpful addition</SelectItem>
                    <SelectItem value="low">Low — Exploratory backlog</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-semibold">Admin / Engineering Notes</Label>
                <Textarea
                  placeholder="Provide feedback on API evaluation, scheduled sprint, or reason for rejection..."
                  value={adminNotes}
                  onChange={(e) => setAdminNotes(e.target.value)}
                  className="text-xs h-24 mt-1"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  This note will be recorded permanently in the database and visible to administrators and the requester.
                </p>
              </div>
            </div>

            <DialogFooter className="mt-4">
              <Button size="sm" variant="outline" onClick={() => setReviewModalOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveReview}
                disabled={submittingReview}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold gap-1"
              >
                {submittingReview ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save & Update Status
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </div>
  );
}
