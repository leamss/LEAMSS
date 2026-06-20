import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  CheckCircle, XCircle, Clock, FileText, Users, Search,
  Loader2, ChevronDown, ChevronRight, Eye, Download,
  ArrowRight, UserCheck, AlertTriangle, Filter
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ApprovalCenter = ({ token }) => {
  const [view, setView] = useState('pipeline'); // pipeline | items
  const [clients, setClients] = useState([]);
  const [caseManagers, setCaseManagers] = useState([]);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [expandedClient, setExpandedClient] = useState(null);
  const [actionDialog, setActionDialog] = useState({ open: false, item: null, type: '', action: '', notes: '', cmId: '' });
  const [docPreview, setDocPreview] = useState({ open: false, url: '', name: '' });
  const [processing, setProcessing] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    setLoading(true);
    try {
      const [pipelineRes, itemsRes] = await Promise.all([
        axios.get(`${API}/admin-super/approval-center/client-pipeline`, { headers }),
        axios.get(`${API}/admin-super/approval-center`, { headers }),
      ]);
      setClients(pipelineRes.data.clients || []);
      setCaseManagers(pipelineRes.data.case_managers || []);
      setItems(itemsRes.data.items || []);
      setSummary(itemsRes.data.summary || {});
    } catch (e) {
      toast.error('Failed to load data');
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async () => {
    if (actionDialog.action === 'reject' && (!actionDialog.notes || actionDialog.notes.trim().length < 5)) {
      toast.error('Rejection reason required (min 5 characters)');
      return;
    }
    setProcessing(true);
    try {
      await axios.post(`${API}/admin-super/approval-center/action`, {
        item_id: actionDialog.item.id,
        item_type: actionDialog.type,
        action: actionDialog.action,
        notes: actionDialog.notes,
        case_manager_id: actionDialog.cmId,
      }, { headers });
      toast.success(`${actionDialog.action === 'approve' ? 'Approved' : 'Rejected'} successfully`);
      setActionDialog({ open: false, item: null, type: '', action: '', notes: '', cmId: '' });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Action failed');
    }
    setProcessing(false);
  };

  const handleAssignCM = async (caseId, cmId) => {
    try {
      await axios.post(`${API}/admin-super/approval-center/assign-cm?case_id=${caseId}&case_manager_id=${cmId}`, {}, { headers });
      toast.success('Case Manager assigned');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Assignment failed');
    }
  };

  const stageInfo = {
    pre_assessment: { label: 'Pre-Assessment Review', color: 'bg-blue-500', text: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-300' },
    sale_review: { label: 'Sale Pending', color: 'bg-amber-500', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-300' },
    assign_cm: { label: 'Assign CM', color: 'bg-leamss-orange-500', text: 'text-leamss-orange-700', bg: 'bg-leamss-orange-50', border: 'border-leamss-orange-300' },
    document_review: { label: 'Document Review', color: 'bg-teal-500', text: 'text-teal-700', bg: 'bg-teal-50', border: 'border-teal-300' },
    in_progress: { label: 'In Progress', color: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300' },
    completed: { label: 'Completed', color: 'bg-slate-400', text: 'text-slate-700', bg: 'bg-slate-50', border: 'border-slate-300' },
  };

  const filtered = clients.filter(c => {
    if (stageFilter !== 'all' && c.current_stage !== stageFilter) return false;
    if (searchTerm && !c.client_name.toLowerCase().includes(searchTerm.toLowerCase()) && !c.client_email.toLowerCase().includes(searchTerm.toLowerCase()) && !c.partner_name?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const filteredItems = items.filter(i => {
    if (searchTerm && !i.title?.toLowerCase().includes(searchTerm.toLowerCase()) && !i.subtitle?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div className="space-y-5" data-testid="approval-center">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Pre-Assessments', count: summary.pending_pre_assessments || 0, color: 'from-blue-50 to-blue-100 border-blue-200', text: 'text-blue-800', filter: 'pre_assessment' },
          { label: 'Pending Sales', count: summary.pending_sales || 0, color: 'from-amber-50 to-amber-100 border-amber-200', text: 'text-amber-800', filter: 'sale_review' },
          { label: 'Documents', count: summary.pending_documents || 0, color: 'from-teal-50 to-teal-100 border-teal-200', text: 'text-teal-800', filter: 'document_review' },
          { label: 'Urgent Tickets', count: summary.urgent_tickets || 0, color: 'from-red-50 to-red-100 border-red-200', text: 'text-red-800', filter: 'all' },
          { label: 'Total Pending', count: summary.total || 0, color: 'from-slate-50 to-slate-100 border-slate-200', text: 'text-slate-800', filter: 'all' },
        ].map((s, i) => (
          <Card key={i} className={`p-3 bg-gradient-to-br ${s.color} cursor-pointer hover:shadow-md transition-shadow`} onClick={() => setStageFilter(s.filter)}>
            <p className="text-xs font-medium text-slate-600">{s.label}</p>
            <p className={`text-2xl font-bold ${s.text}`}>{s.count}</p>
          </Card>
        ))}
      </div>

      {/* View Toggle + Search + Filter */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
            <button onClick={() => setView('pipeline')} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${view === 'pipeline' ? 'bg-white dark:bg-slate-700 shadow-sm text-[#2a777a]' : 'text-slate-500'}`} data-testid="view-pipeline">Client Pipeline</button>
            <button onClick={() => setView('items')} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${view === 'items' ? 'bg-white dark:bg-slate-700 shadow-sm text-[#2a777a]' : 'text-slate-500'}`} data-testid="view-items">All Items</button>
          </div>
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Search client, email, partner..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="approval-search" />
          </div>
          {view === 'pipeline' && (
            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger className="w-[180px]" data-testid="stage-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="pre_assessment">Pre-Assessment</SelectItem>
                <SelectItem value="sale_review">Sale Review</SelectItem>
                <SelectItem value="assign_cm">Assign CM</SelectItem>
                <SelectItem value="document_review">Doc Review</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" size="sm" onClick={loadData}>Refresh</Button>
        </div>
      </Card>

      {/* === PIPELINE VIEW === */}
      {view === 'pipeline' && (
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <Card className="p-12 text-center"><CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" /><p className="text-lg font-semibold text-slate-700">All Clear!</p></Card>
          ) : (
            filtered.map((client, idx) => {
              const si = stageInfo[client.current_stage] || stageInfo.completed;
              const isExpanded = expandedClient === client.client_email;
              return (
                <Card key={client.client_email} className={`overflow-hidden border-l-4 ${si.border}`} data-testid={`client-card-${idx}`}>
                  {/* Client Header - Click to expand */}
                  <div className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors" onClick={() => setExpandedClient(isExpanded ? null : client.client_email)}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {isExpanded ? <ChevronDown className="h-5 w-5 text-slate-400" /> : <ChevronRight className="h-5 w-5 text-slate-400" />}
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-semibold text-slate-800 dark:text-white">{client.client_name}</h4>
                            <Badge className={`${si.bg} ${si.text} text-xs`}>{si.label}</Badge>
                            {client.needs_action && <Badge className="bg-red-500 text-white text-xs">Action Required</Badge>}
                          </div>
                          <p className="text-sm text-slate-500">{client.client_email} | Partner: {client.partner_name}</p>
                        </div>
                      </div>
                      {/* Progress indicators */}
                      <div className="flex items-center gap-1.5 text-xs">
                        {[
                          { key: 'pa', label: 'PA', has: client.pre_assessments.length > 0, active: client.current_stage === 'pre_assessment' },
                          { key: 'sale', label: 'Sale', has: client.sales.length > 0, active: client.current_stage === 'sale_review' },
                          { key: 'cm', label: 'CM', has: client.cases.some(c => c.case_manager_id), active: client.current_stage === 'assign_cm' },
                          { key: 'docs', label: 'Docs', has: client.documents.length > 0, active: client.current_stage === 'document_review' },
                        ].map((step, si2) => (
                          <span key={step.key} className="flex items-center gap-0.5">
                            {si2 > 0 && <ArrowRight className="h-3 w-3 text-slate-300" />}
                            <span className={`px-2 py-0.5 rounded-full ${step.active ? 'bg-[#2a777a] text-white font-bold' : step.has ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>{step.label}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="border-t p-4 space-y-4 bg-slate-50/50 dark:bg-slate-800/30">
                      {/* Pre-Assessments */}
                      {client.pre_assessments.length > 0 && (
                        <div>
                          <h5 className="text-sm font-semibold text-blue-700 mb-2 flex items-center gap-1"><FileText className="h-4 w-4" />Pre-Assessments</h5>
                          {client.pre_assessments.map((pa, pi) => (
                            <div key={pa.id} className="p-3 mb-2 bg-white dark:bg-slate-800 rounded-lg border" data-testid={`pa-item-${pi}`}>
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-slate-800 dark:text-white text-sm">{pa.pa_number}</span>
                                    <Badge className="text-xs" variant="outline">{pa.stage}</Badge>
                                    <Badge className="text-xs" variant="outline">{pa.fee_payment_status}</Badge>
                                  </div>
                                  <p className="text-xs text-slate-500 mt-1">{pa.country} - {pa.service_type} | Created: {pa.created_at ? new Date(pa.created_at).toLocaleDateString() : ''}</p>
                                  {pa.uploaded_documents?.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                      {pa.uploaded_documents.map((doc, di) => (
                                        <Button key={di} variant="outline" size="sm" className="text-xs h-7" onClick={(e) => { e.stopPropagation(); setDocPreview({ open: true, url: doc.url || doc.file_url || '', name: doc.filename || doc.name || 'Document' }); }}>
                                          <Eye className="h-3 w-3 mr-1" />{doc.filename || doc.name || `Doc ${di+1}`}
                                        </Button>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                {['under_review', 'documents_submitted'].includes(pa.stage) && (
                                  <div className="flex gap-2">
                                    <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs" onClick={(e) => { e.stopPropagation(); setActionDialog({ open: true, item: pa, type: 'pre_assessment', action: 'approve', notes: '', cmId: '' }); }} data-testid={`approve-pa-${pi}`}><CheckCircle className="h-3 w-3 mr-1" />Approve</Button>
                                    <Button size="sm" variant="destructive" className="h-8 text-xs" onClick={(e) => { e.stopPropagation(); setActionDialog({ open: true, item: pa, type: 'pre_assessment', action: 'reject', notes: '', cmId: '' }); }} data-testid={`reject-pa-${pi}`}><XCircle className="h-3 w-3 mr-1" />Reject</Button>
                                  </div>
                                )}
                              </div>
                              {pa.admin_decision && <p className="text-xs mt-2 text-slate-500">Decision: <span className="font-medium">{pa.admin_decision}</span> {pa.admin_reason && `— ${pa.admin_reason}`}</p>}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Sales */}
                      {client.sales.length > 0 && (
                        <div>
                          <h5 className="text-sm font-semibold text-amber-700 mb-2 flex items-center gap-1"><FileText className="h-4 w-4" />Sales</h5>
                          {client.sales.map((sale, si2) => (
                            <div key={sale.id} className="p-3 mb-2 bg-white dark:bg-slate-800 rounded-lg border" data-testid={`sale-item-${si2}`}>
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-slate-800 dark:text-white text-sm">{sale.product_name}</span>
                                    <Badge className={`text-xs ${sale.status === 'approved' ? 'bg-emerald-100 text-emerald-700' : sale.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{sale.status}</Badge>
                                  </div>
                                  <p className="text-xs text-slate-500 mt-1">Fee: ₹{(sale.fee_amount || 0).toLocaleString()} | Received: ₹{(sale.amount_received || 0).toLocaleString()} | {sale.payment_method}</p>
                                  {sale.rejection_reason && <p className="text-xs text-red-500 mt-1">Reason: {sale.rejection_reason}</p>}
                                </div>
                                {sale.status === 'pending' && (
                                  <div className="flex gap-2">
                                    <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs" onClick={(e) => { e.stopPropagation(); setActionDialog({ open: true, item: sale, type: 'sale', action: 'approve', notes: '', cmId: '' }); }} data-testid={`approve-sale-${si2}`}><CheckCircle className="h-3 w-3 mr-1" />Approve</Button>
                                    <Button size="sm" variant="destructive" className="h-8 text-xs" onClick={(e) => { e.stopPropagation(); setActionDialog({ open: true, item: sale, type: 'sale', action: 'reject', notes: '', cmId: '' }); }} data-testid={`reject-sale-${si2}`}><XCircle className="h-3 w-3 mr-1" />Reject</Button>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Cases + CM Assignment */}
                      {client.cases.length > 0 && (
                        <div>
                          <h5 className="text-sm font-semibold text-leamss-orange-700 mb-2 flex items-center gap-1"><Users className="h-4 w-4" />Cases & CM Assignment</h5>
                          {client.cases.map((c, ci) => (
                            <div key={c.id} className="p-3 mb-2 bg-white dark:bg-slate-800 rounded-lg border" data-testid={`case-item-${ci}`}>
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-slate-800 dark:text-white text-sm">{c.case_id}</span>
                                    <Badge variant="outline" className="text-xs">{c.status}</Badge>
                                    <span className="text-xs text-slate-500">Step: {c.current_step}</span>
                                  </div>
                                  {c.case_manager_name ? (
                                    <p className="text-xs text-emerald-600 mt-1 flex items-center gap-1"><UserCheck className="h-3 w-3" />CM: {c.case_manager_name}</p>
                                  ) : (
                                    <p className="text-xs text-red-500 mt-1 flex items-center gap-1"><AlertTriangle className="h-3 w-3" />No CM assigned</p>
                                  )}
                                </div>
                                {!c.case_manager_id && (
                                  <Select onValueChange={(cmId) => handleAssignCM(c.id, cmId)}>
                                    <SelectTrigger className="w-[180px] h-8 text-xs" data-testid={`assign-cm-${ci}`}><SelectValue placeholder="Assign CM" /></SelectTrigger>
                                    <SelectContent>
                                      {caseManagers.map(cm => <SelectItem key={cm.id} value={cm.id}>{cm.name}</SelectItem>)}
                                    </SelectContent>
                                  </Select>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Documents */}
                      {client.documents.length > 0 && (
                        <div>
                          <h5 className="text-sm font-semibold text-teal-700 mb-2 flex items-center gap-1"><FileText className="h-4 w-4" />Documents ({client.documents.length})</h5>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {client.documents.map((doc, di) => (
                              <div key={doc.id || di} className="p-2.5 bg-white dark:bg-slate-800 rounded-lg border flex items-center justify-between" data-testid={`doc-item-${di}`}>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-slate-800 dark:text-white truncate">{doc.filename || doc.document_type}</p>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    <Badge className={`text-xs ${doc.status === 'verified' ? 'bg-emerald-100 text-emerald-700' : doc.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{doc.status}</Badge>
                                    <span className="text-xs text-slate-400">{doc.document_type}</span>
                                  </div>
                                </div>
                                <div className="flex gap-1">
                                  {doc.file_url && <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setDocPreview({ open: true, url: doc.file_url, name: doc.filename })}><Eye className="h-3.5 w-3.5" /></Button>}
                                  {doc.file_url && <a href={doc.file_url} download><Button variant="ghost" size="sm" className="h-7 w-7 p-0"><Download className="h-3.5 w-3.5" /></Button></a>}
                                  {doc.status === 'pending' || doc.status === 'uploaded' ? (
                                    <>
                                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-emerald-600" onClick={() => setActionDialog({ open: true, item: doc, type: 'document', action: 'approve', notes: '', cmId: '' })}><CheckCircle className="h-3.5 w-3.5" /></Button>
                                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600" onClick={() => setActionDialog({ open: true, item: doc, type: 'document', action: 'reject', notes: '', cmId: '' })}><XCircle className="h-3.5 w-3.5" /></Button>
                                    </>
                                  ) : null}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* === ALL ITEMS VIEW === */}
      {view === 'items' && (
        <div className="space-y-2">
          {filteredItems.length === 0 ? (
            <Card className="p-12 text-center"><CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" /><p className="text-lg font-semibold text-slate-700">No Pending Items</p></Card>
          ) : (
            filteredItems.map((item, idx) => (
              <Card key={`${item.type}-${item.id}-${idx}`} className="p-3 hover:shadow-md transition-shadow border-l-4" style={{ borderLeftColor: item.type === 'sale' ? '#d97706' : item.type === 'pre_assessment' ? '#2563eb' : item.type === 'document' ? '#0d9488' : '#dc2626' }} data-testid={`item-${idx}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2"><h4 className="font-medium text-slate-800 dark:text-white text-sm">{item.title}</h4><Badge variant="outline" className="text-xs">{item.type}</Badge></div>
                    <p className="text-xs text-slate-500">{item.subtitle}</p>
                  </div>
                  {item.type !== 'ticket' && (
                    <div className="flex gap-1.5">
                      <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 text-xs" onClick={() => setActionDialog({ open: true, item, type: item.type, action: 'approve', notes: '', cmId: '' })}><CheckCircle className="h-3 w-3 mr-1" />Approve</Button>
                      <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => setActionDialog({ open: true, item, type: item.type, action: 'reject', notes: '', cmId: '' })}><XCircle className="h-3 w-3 mr-1" />Reject</Button>
                    </div>
                  )}
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Action Dialog */}
      <Dialog open={actionDialog.open} onOpenChange={(o) => setActionDialog({ ...actionDialog, open: o })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className={actionDialog.action === 'approve' ? 'text-emerald-700' : 'text-red-700'}>{actionDialog.action === 'approve' ? 'Approve' : 'Reject'}</DialogTitle>
            <DialogDescription>Review and confirm your decision</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-3">
            {actionDialog.type === 'sale' && actionDialog.action === 'approve' && (
              <div>
                <label className="text-sm font-medium text-slate-700">Assign Case Manager (optional)</label>
                <Select value={actionDialog.cmId} onValueChange={(v) => setActionDialog({ ...actionDialog, cmId: v })}>
                  <SelectTrigger data-testid="dialog-cm-select"><SelectValue placeholder="Assign later" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Assign later</SelectItem>
                    {caseManagers.map(cm => <SelectItem key={cm.id} value={cm.id}>{cm.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div>
              <label className="text-sm font-medium text-slate-700">{actionDialog.action === 'reject' ? 'Reason for rejection *' : 'Comments (optional)'}</label>
              <Textarea value={actionDialog.notes} onChange={(e) => setActionDialog({ ...actionDialog, notes: e.target.value })} placeholder={actionDialog.action === 'reject' ? 'Why are you rejecting? (min 5 chars)' : 'Any comments...'} rows={3} data-testid="action-notes" />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setActionDialog({ ...actionDialog, open: false })}>Cancel</Button>
              <Button onClick={handleAction} disabled={processing} className={actionDialog.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'} data-testid="confirm-action-btn">
                {processing && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {actionDialog.action === 'approve' ? 'Confirm Approve' : 'Confirm Reject'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Document Preview Dialog */}
      <Dialog open={docPreview.open} onOpenChange={(o) => setDocPreview({ ...docPreview, open: o })}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Document: {docPreview.name}</DialogTitle>
            <DialogDescription>Preview document before approval</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {docPreview.url ? (
              docPreview.url.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                <img src={docPreview.url} alt={docPreview.name} className="max-w-full rounded-lg" />
              ) : docPreview.url.match(/\.pdf$/i) ? (
                <iframe src={docPreview.url} className="w-full h-[60vh] rounded-lg" title="PDF Preview" />
              ) : (
                <div className="text-center py-8">
                  <p className="text-slate-500 mb-3">Preview not available for this file type</p>
                  <a href={docPreview.url} download><Button><Download className="h-4 w-4 mr-2" />Download File</Button></a>
                </div>
              )
            ) : (
              <p className="text-center text-slate-400 py-8">No file URL available</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApprovalCenter;
