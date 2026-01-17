import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import NotificationBell from '@/components/NotificationBell';
import CreateTicket from '@/components/CreateTicket';
import TicketSection from '@/components/TicketSection';
import { Briefcase, FileText, CheckCircle, AlertCircle, LogOut, Download, Plus, Send, ArrowLeft, MessageSquare, Search, Filter, Clock, Eye } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Return to Admin Banner Component
const AdminReturnBanner = () => {
  const adminToken = localStorage.getItem('admin_token');
  const adminUserData = localStorage.getItem('admin_user');
  
  if (!adminToken || !adminUserData) return null;
  
  let adminUser = null;
  try {
    adminUser = JSON.parse(adminUserData);
  } catch (e) {
    console.error('Failed to parse admin user data');
  }

  const handleReturnToAdmin = () => {
    localStorage.setItem('token', adminToken);
    localStorage.setItem('user', adminUserData);
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    toast.success('Returned to Admin account');
    window.location.assign('/admin');
  };

  return (
    <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-4 py-2 flex items-center justify-between shadow-lg" data-testid="admin-return-banner">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">🔒 Viewing as impersonated user</span>
        {adminUser && <span className="text-xs opacity-80">(Admin: {adminUser.name})</span>}
      </div>
      <Button 
        onClick={handleReturnToAdmin} 
        size="sm" 
        className="bg-white text-orange-600 hover:bg-orange-50 font-medium"
        data-testid="return-to-admin-btn"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Return to Admin
      </Button>
    </div>
  );
};

const CaseManagerDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseDocuments, setCaseDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [reviewDialog, setReviewDialog] = useState({ open: false, document: null, status: '', comment: '' });
  const [additionalDocDialog, setAdditionalDocDialog] = useState({ 
    open: false, 
    document_name: '', 
    description: '', 
    due_date: '',
    expiry_date: '',
    validity_months: '',
    doc_type: '',
    step_order: null
  });
  const [canCustomizeWorkflow, setCanCustomizeWorkflow] = useState(false);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [pendingReviewDocs, setPendingReviewDocs] = useState([]);
  const [documentSearch, setDocumentSearch] = useState({ query: '', type: 'all', status: 'all' });
  const [allDocuments, setAllDocuments] = useState([]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadData = async () => {
    try {
      const authHeader = getAuthHeader();
      const [statsRes, casesRes, settingsRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, authHeader),
        axios.get(`${API}/cases/my-cases`, authHeader),
        axios.get(`${API}/settings`, authHeader).catch(() => ({ data: { allow_case_manager_workflow_customization: false } }))
      ]);
      setStats(statsRes.data);
      setCases(casesRes.data);
      setCanCustomizeWorkflow(settingsRes.data?.allow_case_manager_workflow_customization || false);
      
      // Load all documents across all cases to find pending reviews
      const allCases = casesRes.data;
      let allDocs = [];
      let pendingDocs = [];
      
      for (const c of allCases) {
        try {
          const docsRes = await axios.get(`${API}/documents/case/${c.id}`, authHeader);
          const caseDocs = docsRes.data.map(d => ({ ...d, case_id: c.case_id, client_name: c.client_name }));
          allDocs = [...allDocs, ...caseDocs];
          pendingDocs = [...pendingDocs, ...caseDocs.filter(d => d.status === 'uploaded' || d.status === 'pending')];
        } catch (e) {
          // Skip if can't load docs for this case
        }
      }
      
      setAllDocuments(allDocs);
      setPendingReviewDocs(pendingDocs);
      setPendingReviewCount(pendingDocs.length);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData || userData.role !== 'case_manager') {
      navigate('/');
      return;
    }
    setUser(userData);
  }, [navigate]);

  useEffect(() => {
    if (user) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadCaseDetails = async (caseId) => {
    try {
      const [caseRes, docsRes] = await Promise.all([
        axios.get(`${API}/cases/${caseId}`, getAuthHeader()),
        axios.get(`${API}/documents/case/${caseId}`, getAuthHeader())
      ]);
      setSelectedCase(caseRes.data);
      setCaseDocuments(docsRes.data);
    } catch (error) {
      toast.error('Failed to load case details');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleUpdateStep = async (stepName, status, notes = '') => {
    try {
      await axios.post(`${API}/cases/update-step`, {
        case_id: selectedCase.id,
        step_name: stepName,
        status,
        notes
      }, getAuthHeader());
      toast.success('Step updated!');
      loadCaseDetails(selectedCase.id);
      loadData();
    } catch (error) {
      toast.error('Failed to update step');
    }
  };

  const handleReviewDocument = async () => {
    try {
      await axios.post(`${API}/documents/review`, {
        document_id: reviewDialog.document.id,
        status: reviewDialog.status,
        comment: reviewDialog.comment
      }, getAuthHeader());
      toast.success('Document reviewed!');
      setReviewDialog({ open: false, document: null, status: '', comment: '' });
      loadCaseDetails(selectedCase.id);
    } catch (error) {
      toast.error('Failed to review document');
    }
  };

  const handleRequestAdditionalDoc = async () => {
    if (!additionalDocDialog.document_name || !additionalDocDialog.description) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      // Use the new custom document request endpoint if step_order is specified
      const endpoint = additionalDocDialog.step_order !== null 
        ? `${API}/cases/${selectedCase.id}/custom-document-request`
        : `${API}/cases/request-additional-document`;
      
      const requestData = {
        case_id: selectedCase.id,
        document_name: additionalDocDialog.document_name,
        description: additionalDocDialog.description,
        due_date: additionalDocDialog.due_date || null,
        expiry_date: additionalDocDialog.expiry_date || null,
        validity_months: additionalDocDialog.validity_months ? parseInt(additionalDocDialog.validity_months) : null,
        doc_type: additionalDocDialog.doc_type || null,
        step_order: additionalDocDialog.step_order
      };

      await axios.post(endpoint, requestData, getAuthHeader());
      toast.success('Additional document requested!');
      setAdditionalDocDialog({ 
        open: false, document_name: '', description: '', due_date: '',
        expiry_date: '', validity_months: '', doc_type: '', step_order: null
      });
      loadCaseDetails(selectedCase.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to request document');
    }
  };

  const openCustomDocDialog = (stepOrder) => {
    if (!canCustomizeWorkflow) {
      toast.error('Workflow customization is not enabled. Please contact Admin.');
      return;
    }
    setAdditionalDocDialog({
      open: true,
      document_name: '',
      description: '',
      due_date: '',
      expiry_date: '',
      validity_months: '',
      doc_type: '',
      step_order: stepOrder
    });
  };

  const downloadDocument = async (docId, filename) => {
    try {
      const response = await axios.get(`${API}/documents/download/${docId}`, {
        ...getAuthHeader(),
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Document downloaded');
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Pending</Badge>,
      completed: <Badge className="bg-emerald-600">Completed</Badge>,
      in_progress: <Badge className="bg-blue-600">In Progress</Badge>,
      locked: <Badge variant="outline" className="bg-slate-100 text-slate-600">Locked</Badge>,
      approved: <Badge className="bg-emerald-600">Approved</Badge>,
      rejected: <Badge variant="destructive">Rejected</Badge>,
      pending_review: <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Pending Review</Badge>,
      revision_required: <Badge className="bg-blue-600">Revision Required</Badge>
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  return (
    <div className="flex min-h-screen bg-[#F5F7FA]" data-testid="case-manager-dashboard">
      <AdminReturnBanner />
      
      {/* Modern White Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col fixed h-screen" data-testid="case-manager-sidebar">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-[#2a777a] flex items-center justify-center">
              <span className="text-white font-bold text-lg">L</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-800">LEAMSS</h1>
              <p className="text-xs text-slate-500">Case Manager</p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <button
            onClick={() => { setActiveTab('dashboard'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'dashboard' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-dashboard"
          >
            <Briefcase className="h-5 w-5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => { setActiveTab('cases'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'cases' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-cases"
          >
            <FileText className="h-5 w-5" />
            <span>My Cases</span>
          </button>
          <button
            onClick={() => { setActiveTab('pending-review'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'pending-review' 
                ? 'bg-orange-50 text-[#f7620b]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-pending-review"
          >
            <AlertCircle className="h-5 w-5" />
            <span>Pending Review</span>
            {pendingReviewCount > 0 && (
              <span className="ml-auto bg-[#f7620b] text-white text-xs px-2 py-0.5 rounded-full animate-pulse">
                {pendingReviewCount}
              </span>
            )}
          </button>
          <button
            onClick={() => { setActiveTab('documents'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'documents' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-documents"
          >
            <Download className="h-5 w-5" />
            <span>All Documents</span>
          </button>
          <button
            onClick={() => { setActiveTab('tickets'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'tickets' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-tickets"
          >
            <MessageSquare className="h-5 w-5" />
            <span>Support</span>
          </button>
        </nav>
        
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2 mb-3">
            <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center">
              <span className="text-slate-600 font-medium text-sm">{user?.name?.charAt(0) || 'C'}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="w-full justify-start text-slate-600 hover:text-slate-800 hover:bg-slate-50"
            data-testid="logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>

      <main className="flex-1 ml-64">
        {/* Header */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 py-4">
          <div className="flex justify-between items-center max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              {selectedCase && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={() => { setSelectedCase(null); setActiveTab('cases'); }}
                  className="mr-2"
                >
                  <ArrowLeft className="h-5 w-5" />
                </Button>
              )}
              <h2 className="text-2xl font-bold text-slate-800">
                {activeTab === 'dashboard' && 'Dashboard'}
                {activeTab === 'cases' && !selectedCase && 'My Cases'}
                {activeTab === 'pending-review' && 'Pending Review'}
                {activeTab === 'documents' && 'All Documents'}
                {activeTab === 'tickets' && 'Support'}
                {selectedCase && `Case: ${selectedCase.case_id}`}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              {selectedCase && <CreateTicket caseId={selectedCase.id} />}
              <NotificationBell />
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-8">
          <div className="max-w-7xl mx-auto">
          {activeTab === 'dashboard' && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" data-testid="case-manager-stats">
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">My Cases</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.my_cases || 0}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Pending Review</p>
                  <p className="text-3xl font-bold text-[#f7620b] mt-2">{pendingReviewCount}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Documents</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{allDocuments.length}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Approved</p>
                  <p className="text-3xl font-bold text-emerald-600 mt-2">
                    {allDocuments.filter(d => d.status === 'approved').length}
                  </p>
                </Card>
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card 
                  className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => setActiveTab('pending-review')}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-lg">
                      <AlertCircle className="h-6 w-6 text-amber-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-800">Pending Reviews</h3>
                      <p className="text-sm text-slate-500">{pendingReviewCount} documents need your attention</p>
                    </div>
                  </div>
                </Card>
                <Card 
                  className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => setActiveTab('cases')}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-teal-100 rounded-lg">
                      <FileText className="h-6 w-6 text-[#2a777a]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-800">View All Cases</h3>
                      <p className="text-sm text-slate-500">Manage your assigned cases</p>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {activeTab === 'cases' && !selectedCase && (
            <div className="space-y-4" data-testid="cases-list">
              {cases.map((caseItem) => (
                <Card
                  key={caseItem.id}
                  className="p-6 cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => loadCaseDetails(caseItem.id)}
                  data-testid={`case-card-${caseItem.id}`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{caseItem.case_id}</h3>
                      <p className="text-sm text-slate-600 mt-1">Client: {caseItem.client_name}</p>
                      <p className="text-sm text-slate-600">{caseItem.client_email}</p>
                      <p className="text-sm text-slate-600 mt-2">Product: {caseItem.product_name}</p>
                      <p className="text-sm text-slate-500">Partner: {caseItem.partner_name}</p>
                    </div>
                    <div className="text-right">
                      {getStatusBadge('in_progress')}
                      <p className="text-sm text-slate-600 mt-2">{caseItem.current_step}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {selectedCase && (
            <div className="space-y-6">
              <Card className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Case Information</h3>
                  </div>
                  <Button
                    onClick={() => setAdditionalDocDialog({ ...additionalDocDialog, open: true })}
                    size="sm"
                    className="bg-[#2a777a] hover:bg-[#236466]"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Request Additional Document
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-600">Client Name</p>
                    <p className="font-medium text-gray-900">{selectedCase.client_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Email</p>
                    <p className="font-medium text-gray-900">{selectedCase.client_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Product</p>
                    <p className="font-medium text-gray-900">{selectedCase.product_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Partner</p>
                    <p className="font-medium text-gray-900">{selectedCase.partner_name}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Workflow Steps</h3>
                  {canCustomizeWorkflow && (
                    <Badge className="bg-green-100 text-green-700">Customization Enabled</Badge>
                  )}
                </div>
                <div className="space-y-4" data-testid="workflow-steps">
                  {selectedCase.steps && selectedCase.steps.map((step, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-semibold text-gray-900">{step.step_order}. {step.step_name}</h4>
                          {step.notes && <p className="text-sm text-slate-600 mt-1">{step.notes}</p>}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2 text-xs text-slate-600">
                              <p className="font-medium">Required: {step.required_documents.map(d => d.doc_name).join(', ')}</p>
                            </div>
                          )}
                        </div>
                        {getStatusBadge(step.status)}
                      </div>
                      <div className="flex gap-2">
                        <Select onValueChange={(value) => handleUpdateStep(step.step_name, value, step.notes)}>
                          <SelectTrigger className="w-40" data-testid={`update-step-${index}`}>
                            <SelectValue placeholder="Update status" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="in_progress">In Progress</SelectItem>
                            <SelectItem value="completed">Mark Complete</SelectItem>
                          </SelectContent>
                        </Select>
                        {canCustomizeWorkflow && (
                          (() => {
                            // Check if previous step is completed (for step_order > 1)
                            const prevStepCompleted = step.step_order === 1 || 
                              selectedCase.steps.find(s => s.step_order === step.step_order - 1)?.status === 'completed';
                            return (
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => openCustomDocDialog(step.step_order)}
                                disabled={!prevStepCompleted}
                                title={!prevStepCompleted ? 'Previous step must be completed first' : 'Add custom document'}
                                data-testid={`add-doc-step-${index}`}
                              >
                                <Plus className="h-4 w-4 mr-1" />Add Doc
                              </Button>
                            );
                          })()
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Documents</h3>
                <div className="space-y-3" data-testid="case-documents">
                  {caseDocuments.map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{doc.filename}</p>
                        <p className="text-sm text-slate-600">Step: {doc.step_name}</p>
                        <p className="text-sm text-slate-500">Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</p>
                        {doc.review_comment && <p className="text-sm text-slate-600 mt-1">Comment: {doc.review_comment}</p>}
                      </div>
                      <div className="flex items-center gap-3">
                        {getStatusBadge(doc.status)}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => downloadDocument(doc.id, doc.filename)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        {doc.status === 'pending_review' && (
                          <Button
                            size="sm"
                            onClick={() => setReviewDialog({ open: true, document: doc, status: '', comment: '' })}
                            data-testid={`review-doc-${doc.id}`}
                            className="bg-[#2a777a] hover:bg-[#236466]"
                          >
                            Review
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  {caseDocuments.length === 0 && (
                    <p className="text-center text-slate-500 py-8">No documents uploaded yet</p>
                  )}
                </div>
              </Card>

              {selectedCase.additional_doc_requests && selectedCase.additional_doc_requests.length > 0 && (
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Additional Document Requests</h3>
                  <div className="space-y-3">
                    {selectedCase.additional_doc_requests.map((req) => (
                      <div key={req.id} className="p-3 border rounded-lg bg-blue-50">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{req.doc_name || req.document_name}</p>
                            <p className="text-sm text-slate-600">{req.description}</p>
                            {req.step_name && (
                              <p className="text-xs text-blue-600 mt-1">Step: {req.step_name}</p>
                            )}
                            <div className="flex flex-wrap gap-2 mt-2">
                              {req.doc_type && (
                                <Badge variant="outline" className="text-xs">Type: {req.doc_type}</Badge>
                              )}
                              {req.due_date && (
                                <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700">Due: {new Date(req.due_date).toLocaleDateString()}</Badge>
                              )}
                              {req.expiry_date && (
                                <Badge variant="outline" className="text-xs bg-red-50 text-red-700">Expiry: {new Date(req.expiry_date).toLocaleDateString()}</Badge>
                              )}
                              {req.validity_months && (
                                <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700">Valid: {req.validity_months} months</Badge>
                              )}
                            </div>
                            <p className="text-xs text-slate-500 mt-1">
                              Requested by {req.requested_by_name} on {new Date(req.requested_at).toLocaleDateString()}
                            </p>
                          </div>
                          {getStatusBadge(req.status)}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Tickets Section */}
          {activeTab === 'tickets' && (
            <TicketSection />
          )}

          {/* Pending Review Section */}
          {activeTab === 'pending-review' && (
            <div className="space-y-6" data-testid="pending-review-section">
              <Card className="p-6 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-amber-100 rounded-full">
                    <AlertCircle className="h-8 w-8 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-amber-800">{pendingReviewCount} Documents Awaiting Review</h3>
                    <p className="text-sm text-amber-600">These documents need your attention</p>
                  </div>
                </div>
              </Card>

              {pendingReviewDocs.length === 0 ? (
                <Card className="p-12 text-center">
                  <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
                  <h3 className="text-lg font-semibold text-gray-700">All Caught Up!</h3>
                  <p className="text-gray-500">No documents pending review</p>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {pendingReviewDocs.map((doc) => (
                    <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow border-l-4 border-l-amber-500" data-testid={`pending-doc-${doc.id}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="p-2 bg-amber-100 rounded-lg">
                            <FileText className="h-5 w-5 text-amber-600" />
                          </div>
                          <div>
                            <p className="font-semibold text-gray-800">{doc.filename || doc.document_type}</p>
                            <div className="flex items-center gap-2 text-sm text-gray-500">
                              <span className="font-medium text-[#2a777a]">{doc.client_name}</span>
                              <span>•</span>
                              <span>Case: {doc.case_id}</span>
                              <span>•</span>
                              <Clock className="h-3 w-3" />
                              <span>{new Date(doc.uploaded_at || doc.created_at).toLocaleDateString()}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className="bg-amber-100 text-amber-700">{doc.status}</Badge>
                          <Button size="sm" variant="outline" onClick={() => window.open(`${API.replace('/api', '')}${doc.file_path}`, '_blank')}>
                            <Eye className="h-4 w-4 mr-1" />View
                          </Button>
                          <Button 
                            size="sm" 
                            className="bg-[#2a777a] hover:bg-[#236466]"
                            onClick={() => {
                              // Find the case and load its details
                              const caseInfo = cases.find(c => c.case_id === doc.case_id);
                              if (caseInfo) {
                                loadCaseDetails(caseInfo.id);
                                setActiveTab('cases');
                                setReviewDialog({ open: true, document: doc, status: '', comment: '' });
                              }
                            }}
                          >
                            Review
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* All Documents Section with Search */}
          {activeTab === 'documents' && (
            <div className="space-y-6" data-testid="documents-section">
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Filter className="h-4 w-4 text-slate-500" />
                  <span className="text-sm font-medium text-slate-700">Search & Filter Documents</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="relative md:col-span-2">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Search by document name, type, or client..."
                      value={documentSearch.query}
                      onChange={(e) => setDocumentSearch({ ...documentSearch, query: e.target.value })}
                      className="pl-10"
                      data-testid="document-search-input"
                    />
                  </div>
                  <Select value={documentSearch.type} onValueChange={(v) => setDocumentSearch({ ...documentSearch, type: v })}>
                    <SelectTrigger data-testid="document-type-filter">
                      <SelectValue placeholder="Document Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="passport">Passport</SelectItem>
                      <SelectItem value="visa">Visa</SelectItem>
                      <SelectItem value="bank_statement">Bank Statement</SelectItem>
                      <SelectItem value="educational">Educational</SelectItem>
                      <SelectItem value="employment">Employment</SelectItem>
                      <SelectItem value="financial">Financial</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={documentSearch.status} onValueChange={(v) => setDocumentSearch({ ...documentSearch, status: v })}>
                    <SelectTrigger data-testid="document-status-filter">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="uploaded">Uploaded/Pending</SelectItem>
                      <SelectItem value="approved">Approved</SelectItem>
                      <SelectItem value="rejected">Rejected</SelectItem>
                      <SelectItem value="revision_required">Revision Required</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </Card>

              <div className="text-sm text-slate-500 mb-2">
                Showing {allDocuments.filter(d => {
                  const matchesQuery = !documentSearch.query || 
                    d.filename?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                    d.document_type?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                    d.client_name?.toLowerCase().includes(documentSearch.query.toLowerCase());
                  const matchesType = documentSearch.type === 'all' || d.document_type === documentSearch.type;
                  const matchesStatus = documentSearch.status === 'all' || 
                    (documentSearch.status === 'uploaded' ? ['uploaded', 'pending'].includes(d.status) : d.status === documentSearch.status);
                  return matchesQuery && matchesType && matchesStatus;
                }).length} of {allDocuments.length} documents
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="documents-table">
                  <thead>
                    <tr className="bg-slate-100">
                      <th className="text-left p-3">Document</th>
                      <th className="text-left p-3">Client</th>
                      <th className="text-left p-3">Case</th>
                      <th className="text-left p-3">Type</th>
                      <th className="text-center p-3">Status</th>
                      <th className="text-left p-3">Uploaded</th>
                      <th className="text-center p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allDocuments
                      .filter(d => {
                        const matchesQuery = !documentSearch.query || 
                          d.filename?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                          d.document_type?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                          d.client_name?.toLowerCase().includes(documentSearch.query.toLowerCase());
                        const matchesType = documentSearch.type === 'all' || d.document_type === documentSearch.type;
                        const matchesStatus = documentSearch.status === 'all' || 
                          (documentSearch.status === 'uploaded' ? ['uploaded', 'pending'].includes(d.status) : d.status === documentSearch.status);
                        return matchesQuery && matchesType && matchesStatus;
                      })
                      .map((doc) => (
                        <tr key={doc.id} className="border-b hover:bg-slate-50">
                          <td className="p-3 font-medium">{doc.filename || 'Unknown'}</td>
                          <td className="p-3 text-[#2a777a]">{doc.client_name}</td>
                          <td className="p-3">{doc.case_id}</td>
                          <td className="p-3 capitalize">{doc.document_type?.replace(/_/g, ' ')}</td>
                          <td className="p-3 text-center">
                            <Badge className={getStatusBadge(doc.status)}>{doc.status}</Badge>
                          </td>
                          <td className="p-3 text-slate-500">{new Date(doc.uploaded_at || doc.created_at).toLocaleDateString()}</td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Button size="sm" variant="ghost" onClick={() => window.open(`${API.replace('/api', '')}${doc.file_path}`, '_blank')}>
                                <Eye className="h-4 w-4" />
                              </Button>
                              {['uploaded', 'pending'].includes(doc.status) && (
                                <Button 
                                  size="sm" 
                                  className="bg-[#2a777a] hover:bg-[#236466]"
                                  onClick={() => {
                                    const caseInfo = cases.find(c => c.case_id === doc.case_id);
                                    if (caseInfo) {
                                      loadCaseDetails(caseInfo.id);
                                      setActiveTab('cases');
                                      setReviewDialog({ open: true, document: doc, status: '', comment: '' });
                                    }
                                  }}
                                >
                                  Review
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          </div>
        </div>
      </main>

      {/* Review Document Dialog */}
      <Dialog open={reviewDialog.open} onOpenChange={(open) => setReviewDialog({ ...reviewDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Review Document</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <p className="font-medium mb-2 text-gray-900">{reviewDialog.document?.filename}</p>
              <Label>Review Status</Label>
              <Select value={reviewDialog.status} onValueChange={(value) => setReviewDialog({ ...reviewDialog, status: value })}>
                <SelectTrigger data-testid="review-status-select">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="approved">Approve</SelectItem>
                  <SelectItem value="rejected">Reject</SelectItem>
                  <SelectItem value="revision_required">Revision Required</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Comment</Label>
              <Textarea
                value={reviewDialog.comment}
                onChange={(e) => setReviewDialog({ ...reviewDialog, comment: e.target.value })}
                placeholder="Add review comments..."
                rows={4}
                data-testid="review-comment-textarea"
              />
            </div>
            <Button onClick={handleReviewDocument} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="submit-review-button">
              Submit Review
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Request Additional Document Dialog */}
      <Dialog open={additionalDocDialog.open} onOpenChange={(open) => setAdditionalDocDialog({ ...additionalDocDialog, open })}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {additionalDocDialog.step_order !== null 
                ? `Request Document for Step ${additionalDocDialog.step_order}` 
                : 'Request Additional Document'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Document Name *</Label>
                <Input
                  value={additionalDocDialog.document_name}
                  onChange={(e) => setAdditionalDocDialog({ ...additionalDocDialog, document_name: e.target.value })}
                  placeholder="e.g., Updated Bank Statement"
                />
              </div>
              <div>
                <Label>Document Type</Label>
                <Select value={additionalDocDialog.doc_type || ''} onValueChange={(value) => setAdditionalDocDialog({ ...additionalDocDialog, doc_type: value === 'none' ? '' : value })}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="passport">Passport</SelectItem>
                    <SelectItem value="visa">Visa</SelectItem>
                    <SelectItem value="certificate">Certificate</SelectItem>
                    <SelectItem value="id_card">ID Card</SelectItem>
                    <SelectItem value="photo">Photo</SelectItem>
                    <SelectItem value="financial">Financial Document</SelectItem>
                    <SelectItem value="medical">Medical Document</SelectItem>
                    <SelectItem value="legal">Legal Document</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Description *</Label>
              <Textarea
                value={additionalDocDialog.description}
                onChange={(e) => setAdditionalDocDialog({ ...additionalDocDialog, description: e.target.value })}
                placeholder="Explain why this document is needed..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Due Date</Label>
                <Input
                  type="date"
                  value={additionalDocDialog.due_date}
                  onChange={(e) => setAdditionalDocDialog({ ...additionalDocDialog, due_date: e.target.value })}
                />
              </div>
              <div>
                <Label>Expiry Date</Label>
                <Input
                  type="date"
                  value={additionalDocDialog.expiry_date}
                  onChange={(e) => setAdditionalDocDialog({ ...additionalDocDialog, expiry_date: e.target.value, validity_months: '' })}
                />
              </div>
              <div>
                <Label>Validity (months)</Label>
                <Input
                  type="number"
                  placeholder="e.g., 6"
                  value={additionalDocDialog.validity_months}
                  onChange={(e) => setAdditionalDocDialog({ ...additionalDocDialog, validity_months: e.target.value, expiry_date: '' })}
                />
              </div>
            </div>
            <p className="text-xs text-slate-500">* Set either Expiry Date OR Validity in months (not both)</p>
            <Button onClick={handleRequestAdditionalDoc} className="w-full bg-emerald-600 hover:bg-emerald-700">
              <Send className="mr-2 h-4 w-4" />
              Send Request
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CaseManagerDashboard;
