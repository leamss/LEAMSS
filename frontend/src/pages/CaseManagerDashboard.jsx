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
import QuickActions from '@/components/QuickActions';
import { Briefcase, FileText, CheckCircle, AlertCircle, LogOut, Download, Plus, Send, ArrowLeft, MessageSquare, Search, Filter, Clock, Eye, Menu, X, Lock, Calendar, AlertTriangle } from 'lucide-react';

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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [ticketFilter, setTicketFilter] = useState(null);
  const [reviewDialog, setReviewDialog] = useState({ open: false, document: null, status: '', comment: '' });
  const [aiAnalysis, setAiAnalysis] = useState({ open: false, doc: null, result: null });
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
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [initialTicketId, setInitialTicketId] = useState(null);
  const [infoSheetDialog, setInfoSheetDialog] = useState({ open: false, data: {} });
  const [infoSheetLoading, setInfoSheetLoading] = useState(false);
  const [expiringDocs, setExpiringDocs] = useState([]);
  const [expiryEditModal, setExpiryEditModal] = useState(null);
  const [expiryEditDate, setExpiryEditDate] = useState('');
  const [expiryEditNotes, setExpiryEditNotes] = useState('');

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadData = async () => {
    try {
      const authHeader = getAuthHeader();
      const [statsRes, casesRes, settingsRes] = await Promise.all([
        axios.get(`${API}/stats/case-manager-dashboard`, authHeader),
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
          // Include all statuses that need review: uploaded, pending, pending_review
          pendingDocs = [...pendingDocs, ...caseDocs.filter(d => 
            d.status === 'uploaded' || d.status === 'pending' || d.status === 'pending_review'
          )];
        } catch (e) {
          // Skip if can't load docs for this case
        }
      }
      
      setAllDocuments(allDocs);
      setPendingReviewDocs(pendingDocs);
      setPendingReviewCount(pendingDocs.length);

      // Load expiring documents
      try {
        const expiryRes = await axios.get(`${API}/documents/expiring/all`, authHeader);
        setExpiringDocs(expiryRes.data || []);
      } catch (e) { /* no expiry data */ }
      // Auto-trigger expiry reminder check (fire-and-forget)
      axios.post(`${API}/documents/check-expiry-reminders`, {}, authHeader).catch(() => {});
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
    
    // Check if there's a tab to open from notification click
    const storedTab = sessionStorage.getItem('activeTab');
    if (storedTab) {
      setActiveTab(storedTab);
      sessionStorage.removeItem('activeTab');
    }
    
    // Check if there's a ticket to open
    const storedTicketId = sessionStorage.getItem('openTicketId');
    if (storedTicketId) {
      setActiveTab('tickets');
      setInitialTicketId(storedTicketId);
      sessionStorage.removeItem('openTicketId');
    }
    
    // Check if there's a case to open
    const storedCaseId = sessionStorage.getItem('openCaseId');
    if (storedCaseId) {
      setActiveTab('cases');
      // We'll load case details after data is loaded
    }
  }, [navigate]);

  useEffect(() => {
    if (user) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Handle notification click - navigate to correct tab/item
  const handleNotificationClick = async (notification) => {
    const type = notification.type || '';
    const relatedId = notification.related_id;
    
    if (type.includes('ticket')) {
      setActiveTab('tickets');
      setInitialTicketId(relatedId);
    } else if (type.includes('expiry') || type.includes('doc') || type.includes('step') || type.includes('case')) {
      // For document/case related, try to load the case
      if (relatedId) {
        setActiveTab('cases');
        const caseItem = cases.find(c => c.id === relatedId);
        if (caseItem) {
          await loadCaseDetails(caseItem.id);
        }
      } else {
        setActiveTab('documents');
      }
    }
  };

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
      const msg = error.response?.data?.detail || 'Failed to update step';
      toast.error(msg);
    }
  };

  const handleReviewDocument = async () => {
    if (!reviewDialog.status) {
      toast.error('Please select a review status');
      return;
    }
    if ((reviewDialog.status === 'rejected' || reviewDialog.status === 'revision_required') && (!reviewDialog.comment || reviewDialog.comment.trim().length < 5)) {
      toast.error('Comment is required when rejecting or requesting revision (min 5 characters)');
      return;
    }
    try {
      await axios.post(`${API}/documents/review`, {
        document_id: reviewDialog.document.id,
        status: reviewDialog.status,
        comment: reviewDialog.comment
      }, getAuthHeader());
      toast.success('Document reviewed!');
      setReviewDialog({ open: false, document: null, status: '', comment: '' });
      
      if (selectedCase) {
        loadCaseDetails(selectedCase.id);
      }
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to review document');
    }
  };

  // Batch review multiple documents
  const handleBatchReview = async (status) => {
    if (selectedDocIds.length === 0) {
      toast.error('Please select documents to review');
      return;
    }
    let successCount = 0;
    for (const docId of selectedDocIds) {
      try {
        await axios.post(`${API}/documents/review`, {
          document_id: docId,
          status,
          comment: `Batch ${status} by Case Manager`
        }, getAuthHeader());
        successCount++;
      } catch (e) { /* skip individual failures */ }
    }
    toast.success(`${successCount} of ${selectedDocIds.length} documents ${status}`);
    setSelectedDocIds([]);
    loadData();
  };

  const toggleDocSelection = (docId) => {
    setSelectedDocIds(prev => 
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  const toggleAllDocs = (docs) => {
    if (selectedDocIds.length === docs.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(docs.map(d => d.id));
    }
  };

  const handleRequestAdditionalDoc = async () => {
    if (!additionalDocDialog.document_name || !additionalDocDialog.description) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      const endpoint = additionalDocDialog.step_order !== null 
        ? `${API}/cases/${selectedCase.id}/custom-document-request`
        : `${API}/cases/request-document`;
      
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
      
      // Also create a ticket to notify the client
      if (additionalDocDialog.createTicket !== false) {
        try {
          await axios.post(`${API}/tickets`, {
            subject: `Document Required: ${additionalDocDialog.document_name}`,
            description: `Dear ${selectedCase.client_name},\n\nPlease upload the following document for your case (${selectedCase.case_id}):\n\nDocument: ${additionalDocDialog.document_name}\nDescription: ${additionalDocDialog.description}${additionalDocDialog.due_date ? `\nDue Date: ${additionalDocDialog.due_date}` : ''}\n\nPlease upload this at your earliest convenience.`,
            priority: 'medium',
            category: 'document',
            target_user_ids: selectedCase.client_id ? [selectedCase.client_id] : [],
            case_id: selectedCase.id
          }, getAuthHeader());
        } catch (e) {
          console.error('Failed to create ticket for doc request:', e);
        }
      }
      
      toast.success('Additional document requested! Client has been notified.');
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

  const handleCMSetExpiry = async () => {
    if (!expiryEditModal || !expiryEditDate) return;
    try {
      await axios.post(`${API}/documents/${expiryEditModal.id}/set-expiry`, {
        expiry_date: expiryEditDate,
        notes: expiryEditNotes
      }, getAuthHeader());
      toast.success('Expiry date updated');
      setExpiryEditModal(null);
      setExpiryEditDate('');
      setExpiryEditNotes('');
      loadData();
    } catch (error) {
      toast.error('Failed to set expiry');
    }
  };

  const getUrgencyStyle = (urgency) => ({
    expired: 'bg-red-100 text-red-700 border-red-200',
    critical: 'bg-orange-100 text-orange-700 border-orange-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    attention: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    ok: 'bg-green-100 text-green-700 border-green-200',
  }[urgency] || 'bg-slate-100 text-slate-500');

  const loadInfoSheet = async (caseId) => {
    setInfoSheetLoading(true);
    try {
      const response = await axios.get(`${API}/cases/${caseId}/information-sheet`, getAuthHeader());
      setInfoSheetDialog({ open: true, data: response.data.data || {} });
    } catch (error) {
      setInfoSheetDialog({ open: true, data: {} });
    }
    setInfoSheetLoading(false);
  };

  const saveInfoSheet = async () => {
    try {
      await axios.post(`${API}/cases/${selectedCase.id}/information-sheet`, infoSheetDialog.data, getAuthHeader());
      toast.success('Information sheet saved!');
    } catch (error) {
      toast.error('Failed to save information sheet');
    }
  };

  const updateInfoField = (field, value) => {
    setInfoSheetDialog(prev => ({
      ...prev,
      data: { ...prev.data, [field]: value }
    }));
  };

  // View document in new tab
  const viewDocument = async (fileId, filename) => {
    try {
      toast.info('Opening document...');
      const response = await axios.get(`${API}/documents/view/${fileId}`, {
        ...getAuthHeader(),
        responseType: 'blob'
      });
      
      // Get the content type from response or guess from filename
      const contentType = response.headers['content-type'] || 'application/pdf';
      const blob = new Blob([response.data], { type: contentType });
      const blobUrl = window.URL.createObjectURL(blob);
      
      // Open in new tab
      window.open(blobUrl, '_blank');
    } catch (error) {
      console.error('View error:', error);
      toast.error('Failed to open document');
    }
  };

  // Helper function to format dates safely
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'N/A';
      return date.toLocaleDateString();
    } catch {
      return 'N/A';
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
    <div className="min-h-screen bg-[#F5F7FA]" data-testid="case-manager-dashboard">
      <AdminReturnBanner />
      
      <div className="flex">
        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}
        {/* Responsive Sidebar */}
        <aside className={`w-64 bg-white border-r border-slate-200 flex flex-col fixed h-screen top-0 left-0 z-40 transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`} data-testid="case-manager-sidebar">
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <img src="/leamss-logo.png" alt="LEAMSS" className="h-10 w-10 rounded-lg object-contain" />
              <div>
                <h1 className="text-lg font-bold text-slate-800">LEAMSS</h1>
                <p className="text-xs text-slate-500">Case Manager</p>
              </div>
            </div>
          </div>
          
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            <button
              onClick={() => { setActiveTab('dashboard'); setSelectedCase(null); setSidebarOpen(false); }}
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
              onClick={() => { setActiveTab('cases'); setSelectedCase(null); setSidebarOpen(false); }}
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
              onClick={() => { setActiveTab('pending-review'); setSelectedCase(null); setSidebarOpen(false); }}
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
            onClick={() => { setActiveTab('documents'); setSelectedCase(null); setSidebarOpen(false); }}
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
            onClick={() => { setActiveTab('tickets'); setSelectedCase(null); setSidebarOpen(false); }}
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
          <button
            onClick={() => { setActiveTab('expiry-alerts'); setSelectedCase(null); setSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'expiry-alerts' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-expiry-alerts"
          >
            <Calendar className="h-5 w-5" />
            <span>Expiry Alerts</span>
            {expiringDocs.filter(d => d.urgency === 'expired' || d.urgency === 'critical').length > 0 && (
              <Badge className="bg-red-500 text-white text-xs ml-auto">{expiringDocs.filter(d => d.urgency === 'expired' || d.urgency === 'critical').length}</Badge>
            )}
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

      <main className="flex-1 md:ml-64">
        {/* Header */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-4 md:px-8 py-4">
          <div className="flex justify-between items-center max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" className="md:hidden" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="mobile-menu-btn">
                <Menu className="h-5 w-5" />
              </Button>
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
              <h2 className="text-lg md:text-2xl font-bold text-slate-800">
                {activeTab === 'dashboard' && 'Dashboard'}
                {activeTab === 'cases' && !selectedCase && 'My Cases'}
                {activeTab === 'pending-review' && 'Pending Review'}
                {activeTab === 'documents' && 'All Documents'}
                {activeTab === 'tickets' && 'Support'}
                {activeTab === 'expiry-alerts' && 'Document Expiry Alerts'}
                {selectedCase && `Case: ${selectedCase.case_id}`}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              {selectedCase && (
                <CreateTicket 
                  caseId={selectedCase.id} 
                  clientId={selectedCase.client_id}
                  clientName={selectedCase.client_name}
                  restrictToClient={true}
                />
              )}
              <NotificationBell onNotificationClick={handleNotificationClick} />
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-4 md:p-8">
          <div className="max-w-7xl mx-auto">
          {activeTab === 'dashboard' && (
            <div>
              {/* Quick Actions Widget */}
              <div className="mb-6">
                <QuickActions 
                  userRole="case_manager" 
                  onNavigate={(tab, filter) => {
                    setActiveTab(tab);
                    if (filter && tab === 'tickets') setTicketFilter(filter);
                  }} 
                />
              </div>

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
                  <div className="flex gap-2">
                    <Button
                      onClick={() => loadInfoSheet(selectedCase.id)}
                      size="sm"
                      variant="outline"
                      data-testid="info-sheet-btn"
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      Information Sheet
                    </Button>
                    <Button
                      onClick={async () => {
                        const msg = window.prompt('Enter a message for the client:',
                          'Please fill your information sheet with complete details. All fields marked as required must be filled before your case can proceed.');
                        if (msg) {
                          try {
                            const required_fields = [
                              "full_name", "date_of_birth", "gender", "nationality",
                              "passport_number", "passport_expiry", "address", "phone", "email",
                              "education_level", "occupation", "employer", "marital_status",
                              "work_experience_years"
                            ];
                            await axios.post(`${API}/cases/${selectedCase.id}/request-info-sheet`, { message: msg, required_fields }, getAuthHeader());
                            toast.success('Information sheet request sent! Client will be notified to fill all required fields.');
                          } catch (e) { toast.error('Failed to send request'); }
                        }
                      }}
                      size="sm"
                      variant="outline"
                      className="text-amber-600 border-amber-300 hover:bg-amber-50"
                      data-testid="request-info-sheet-btn"
                    >
                      <Send className="mr-2 h-4 w-4" />
                      Request Info Sheet
                    </Button>
                    <Button
                      onClick={() => setAdditionalDocDialog({ ...additionalDocDialog, open: true })}
                      size="sm"
                      className="bg-[#2a777a] hover:bg-[#236466]"
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Request Additional Document
                    </Button>
                  </div>
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
                  {selectedCase.steps && selectedCase.steps.map((step, index) => {
                    const prevCompleted = index === 0 || selectedCase.steps.slice(0, index).every(s => s.status === 'completed');
                    const isLocked = !prevCompleted && index > 0;
                    const isCompleted = step.status === 'completed';

                    return (
                    <div key={index} className={`border rounded-lg p-4 ${isLocked ? 'opacity-50 bg-slate-50' : ''} ${isCompleted ? 'border-emerald-200 bg-emerald-50/30' : ''}`}>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                            {isLocked && <Lock className="h-4 w-4 text-slate-400" />}
                            {isCompleted && <CheckCircle className="h-4 w-4 text-emerald-500" />}
                            {step.step_order}. {step.step_name}
                          </h4>
                          {isLocked && <p className="text-xs text-red-500 mt-1">Complete previous step first</p>}
                          {step.notes && <p className="text-sm text-slate-600 mt-1">{step.notes}</p>}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {step.required_documents.map((d, di) => {
                                const uploaded = (caseDocuments || []).some(cd => 
                                  cd.document_type?.toLowerCase().includes(d.doc_name?.toLowerCase()) || 
                                  d.doc_name?.toLowerCase().includes(cd.document_type?.toLowerCase())
                                );
                                return (
                                  <span key={di} className={`text-xs px-2 py-0.5 rounded-full border ${uploaded ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
                                    {d.doc_name} {uploaded ? '✓' : '✗'}
                                    {d.is_mandatory && !uploaded && <span className="text-red-500 ml-0.5">*</span>}
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </div>
                        {getStatusBadge(step.status)}
                      </div>
                      {!isLocked && !isCompleted && (
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
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => openCustomDocDialog(step.step_order)}
                            data-testid={`add-doc-step-${index}`}
                          >
                            <Plus className="h-4 w-4 mr-1" />Add Doc
                          </Button>
                        )}
                      </div>
                      )}
                    </div>
                    );
                  })}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Documents</h3>
                <div className="space-y-3" data-testid="case-documents">
                  {caseDocuments.map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg hover:bg-slate-50">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{doc.filename}</p>
                        <div className="flex flex-wrap gap-3 text-sm text-slate-600">
                          {doc.step_name && <span>Step: {doc.step_name}</span>}
                          {doc.document_type && <span className="capitalize">Type: {doc.document_type.replace(/_/g, ' ')}</span>}
                          <span>By: {doc.uploader_name || 'Unknown'}</span>
                          <span>{formatDate(doc.uploaded_at)}</span>
                        </div>
                        {doc.review_comment && (
                          <div className="mt-1 text-sm">
                            <span className="text-slate-500">Review ({doc.reviewer_name || 'CM'}): </span>
                            <span className={doc.status === 'approved' ? 'text-green-600' : doc.status === 'rejected' ? 'text-red-600' : 'text-amber-600'}>{doc.review_comment}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        {getStatusBadge(doc.status)}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => downloadDocument(doc.id, doc.filename)}
                          data-testid={`download-case-doc-${doc.id}`}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        {['pending', 'pending_review', 'uploaded', 'revision_required'].includes(doc.status) && (
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
                              Requested by {req.requested_by_name || 'Unknown'}{req.requested_at ? ` on ${new Date(req.requested_at).toLocaleDateString()}` : ''}
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
            <TicketSection initialTicketId={initialTicketId} initialFilter={ticketFilter} />
          )}

          {/* Expiry Alerts Tab */}
          {activeTab === 'expiry-alerts' && (
            <div className="space-y-6" data-testid="expiry-alerts-section">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {[
                  { label: 'Expired', count: expiringDocs.filter(d => d.urgency === 'expired').length, style: 'bg-red-50 border-red-200 text-red-700' },
                  { label: 'Critical (<30 days)', count: expiringDocs.filter(d => d.urgency === 'critical').length, style: 'bg-orange-50 border-orange-200 text-orange-700' },
                  { label: 'Warning (<60 days)', count: expiringDocs.filter(d => d.urgency === 'warning').length, style: 'bg-amber-50 border-amber-200 text-amber-700' },
                  { label: 'Attention (<90 days)', count: expiringDocs.filter(d => d.urgency === 'attention').length, style: 'bg-yellow-50 border-yellow-200 text-yellow-700' },
                ].map((s, i) => (
                  <Card key={i} className={`p-4 border ${s.style}`}>
                    <p className="text-2xl font-bold">{s.count}</p>
                    <p className="text-sm font-medium">{s.label}</p>
                  </Card>
                ))}
              </div>

              {expiringDocs.length === 0 ? (
                <Card className="p-12 text-center bg-white shadow-md border-0">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                  <h3 className="text-lg font-bold text-slate-800">No Expiry Alerts</h3>
                  <p className="text-sm text-slate-500 mt-1">No documents have expiry dates set. Set expiry dates from the case documents view.</p>
                </Card>
              ) : (
                <Card className="p-6 bg-white shadow-md border-0">
                  <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-[#f7620b]" />
                    All Expiring Documents ({expiringDocs.length})
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-200">
                          <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Document</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Client</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Case</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Expiry Date</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Status</th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {expiringDocs.map((doc) => (
                          <tr key={doc.id} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`expiry-row-${doc.id}`}>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <FileText className="h-4 w-4 text-[#2a777a]" />
                                <div>
                                  <p className="font-medium text-slate-800 text-sm">{doc.filename}</p>
                                  <p className="text-xs text-slate-400 capitalize">{doc.document_type.replace('_', ' ')}</p>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600">{doc.client_name || '-'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600">{doc.case_number || '-'}</td>
                            <td className="py-3 px-4 text-sm">
                              {doc.expiry_date ? new Date(doc.expiry_date).toLocaleDateString() : '-'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge className={`text-xs ${getUrgencyStyle(doc.urgency)}`}>
                                {doc.urgency === 'expired' ? `Expired ${Math.abs(doc.days_remaining)}d ago` :
                                 `${doc.days_remaining} days left`}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Button size="sm" variant="outline" onClick={() => {
                                setExpiryEditModal(doc);
                                setExpiryEditDate(doc.expiry_date ? doc.expiry_date.split('T')[0] : '');
                                setExpiryEditNotes(doc.expiry_notes || '');
                              }} data-testid={`cm-edit-expiry-${doc.id}`}>
                                <Calendar className="h-4 w-4 mr-1" /> Edit
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Pending Review Section — Grouped by Client */}
          {activeTab === 'pending-review' && (
            <div className="space-y-6" data-testid="pending-review-section">
              <Card className="p-6 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-amber-100 rounded-full">
                    <AlertCircle className="h-8 w-8 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-amber-800">{pendingReviewCount} Documents Awaiting Review</h3>
                    <p className="text-sm text-amber-600">Grouped by client for easier review</p>
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
                (() => {
                  // Group pending docs by client
                  const clientGroups = {};
                  pendingReviewDocs.forEach(doc => {
                    const key = doc.client_name || 'Unknown Client';
                    if (!clientGroups[key]) clientGroups[key] = { docs: [], caseId: doc.case_id };
                    clientGroups[key].docs.push(doc);
                  });
                  
                  return (
                    <div className="space-y-4">
                      {Object.entries(clientGroups).map(([clientName, group]) => (
                        <Card key={clientName} className="overflow-hidden border border-slate-200 hover:border-amber-300 transition-colors" data-testid={`pending-client-${clientName}`}>
                          <details className="group" open>
                            <summary className="flex items-center justify-between p-5 cursor-pointer bg-white hover:bg-slate-50 transition-colors list-none">
                              <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#2a777a] to-[#236466] flex items-center justify-center text-white font-bold text-lg shadow-sm">
                                  {clientName[0]?.toUpperCase()}
                                </div>
                                <div>
                                  <h4 className="font-semibold text-slate-800 text-base">{clientName}</h4>
                                  <p className="text-xs text-slate-500">Case: {group.caseId}</p>
                                </div>
                              </div>
                              <div className="flex items-center gap-3">
                                <Badge className="bg-amber-100 text-amber-700 border-amber-200 font-semibold px-3 py-1">
                                  {group.docs.length} pending
                                </Badge>
                                <svg className="h-5 w-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                              </div>
                            </summary>
                            <div className="border-t border-slate-100">
                              {group.docs.map((doc) => (
                                <div key={doc.id} className="flex items-center justify-between p-4 border-b border-slate-50 last:border-b-0 hover:bg-slate-50/50 transition-colors" data-testid={`pending-doc-${doc.id}`}>
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="p-2 bg-amber-50 rounded-lg shrink-0">
                                      <FileText className="h-4 w-4 text-amber-600" />
                                    </div>
                                    <div className="min-w-0">
                                      <p className="font-medium text-slate-800 truncate">{doc.filename || doc.document_type}</p>
                                      <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                                        <span className="capitalize">{doc.document_type?.replace(/_/g, ' ')}</span>
                                        <span>&middot;</span>
                                        <Clock className="h-3 w-3" />
                                        <span>{formatDate(doc.uploaded_at || doc.created_at)}</span>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2 shrink-0">
                                    {doc.file_id && (
                                      <>
                                        <Button size="sm" variant="outline" onClick={() => viewDocument(doc.file_id, doc.filename || `${doc.document_type}.pdf`)} data-testid={`view-doc-${doc.id}`}>
                                          <Eye className="h-4 w-4 mr-1" />View
                                        </Button>
                                        <Button size="sm" variant="outline" onClick={() => downloadDocument(doc.file_id, doc.filename || `${doc.document_type}.pdf`)} data-testid={`download-doc-${doc.id}`}>
                                          <Download className="h-4 w-4" />
                                        </Button>
                                      </>
                                    )}
                                    <Button 
                                      size="sm" 
                                      className="bg-[#2a777a] hover:bg-[#236466] text-white"
                                      onClick={() => {
                                        const caseInfo = cases.find(c => c.case_id === doc.case_id);
                                        if (caseInfo) {
                                          loadCaseDetails(caseInfo.id);
                                          setActiveTab('cases');
                                          setReviewDialog({ open: true, document: doc, status: '', comment: '' });
                                        }
                                      }}
                                      data-testid={`review-btn-${doc.id}`}
                                    >
                                      Review
                                    </Button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </details>
                        </Card>
                      ))}
                    </div>
                  );
                })()
              )}
            </div>
          )}

          {/* All Documents Section — Client-wise with Tabs */}
          {activeTab === 'documents' && (
            <div className="space-y-6" data-testid="documents-section">
              {/* Search & Filter Bar */}
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

              {/* Batch Actions Bar */}
              {selectedDocIds.length > 0 && (
                <Card className="p-3 bg-[#2a777a]/10 border-[#2a777a]/30">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-[#2a777a]">{selectedDocIds.length} document(s) selected</span>
                    <div className="flex gap-2">
                      <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => handleBatchReview('approved')} data-testid="batch-approve-btn">
                        <CheckCircle className="h-4 w-4 mr-1" />Approve All
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleBatchReview('rejected')} data-testid="batch-reject-btn">
                        Reject All
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setSelectedDocIds([])}>Clear</Button>
                    </div>
                  </div>
                </Card>
              )}

              {(() => {
                const filteredDocs = allDocuments.filter(d => {
                  const matchesQuery = !documentSearch.query || 
                    d.filename?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                    d.document_type?.toLowerCase().includes(documentSearch.query.toLowerCase()) ||
                    d.client_name?.toLowerCase().includes(documentSearch.query.toLowerCase());
                  const matchesType = documentSearch.type === 'all' || d.document_type === documentSearch.type;
                  const matchesStatus = documentSearch.status === 'all' || 
                    (documentSearch.status === 'uploaded' ? ['uploaded', 'pending'].includes(d.status) : d.status === documentSearch.status);
                  return matchesQuery && matchesType && matchesStatus;
                });
                
                // Group by client
                const clientDocGroups = {};
                filteredDocs.forEach(doc => {
                  const key = doc.client_name || 'Unknown Client';
                  if (!clientDocGroups[key]) clientDocGroups[key] = { docs: [], caseId: doc.case_id };
                  clientDocGroups[key].docs.push(doc);
                });
                const clientNames = Object.keys(clientDocGroups).sort();
                
                return (
                  <>
                    <div className="text-sm text-slate-500">
                      Showing {filteredDocs.length} of {allDocuments.length} documents across {clientNames.length} clients
                    </div>
                    
                    {clientNames.length === 0 ? (
                      <Card className="p-8 text-center">
                        <p className="text-slate-500">No documents match your filters</p>
                      </Card>
                    ) : (
                      <div className="space-y-4">
                        {clientNames.map(clientName => {
                          const group = clientDocGroups[clientName];
                          const pendingCount = group.docs.filter(d => ['uploaded', 'pending', 'pending_review'].includes(d.status)).length;
                          const approvedCount = group.docs.filter(d => d.status === 'approved').length;
                          
                          return (
                            <Card key={clientName} className="overflow-hidden border border-slate-200" data-testid={`docs-client-${clientName}`}>
                              <details className="group">
                                <summary className="flex items-center justify-between p-5 cursor-pointer bg-white hover:bg-slate-50 transition-colors list-none">
                                  <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#2a777a] to-[#236466] flex items-center justify-center text-white font-bold text-lg shadow-sm">
                                      {clientName[0]?.toUpperCase()}
                                    </div>
                                    <div>
                                      <h4 className="font-semibold text-slate-800">{clientName}</h4>
                                      <p className="text-xs text-slate-500">Case: {group.caseId} &middot; {group.docs.length} documents</p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {pendingCount > 0 && <Badge className="bg-amber-100 text-amber-700 border-amber-200">{pendingCount} pending</Badge>}
                                    {approvedCount > 0 && <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">{approvedCount} approved</Badge>}
                                    <svg className="h-5 w-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                                  </div>
                                </summary>
                                <div className="border-t border-slate-100">
                                  <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                      <thead>
                                        <tr className="bg-slate-50 text-slate-600">
                                          <th className="p-3 w-10">
                                            <input
                                              type="checkbox"
                                              checked={group.docs.filter(d => ['uploaded','pending'].includes(d.status)).every(d => selectedDocIds.includes(d.id))}
                                              onChange={() => {
                                                const reviewable = group.docs.filter(d => ['uploaded','pending'].includes(d.status));
                                                const allSelected = reviewable.every(d => selectedDocIds.includes(d.id));
                                                if (allSelected) setSelectedDocIds(prev => prev.filter(id => !reviewable.map(d=>d.id).includes(id)));
                                                else setSelectedDocIds(prev => [...new Set([...prev, ...reviewable.map(d=>d.id)])]);
                                              }}
                                              className="rounded"
                                            />
                                          </th>
                                          <th className="text-left p-3">Document</th>
                                          <th className="text-left p-3">Type</th>
                                          <th className="text-center p-3">Status</th>
                                          <th className="text-left p-3">Uploaded</th>
                                          <th className="text-center p-3">Actions</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {group.docs.map((doc) => (
                                          <tr key={doc.id} className={`border-b border-slate-50 hover:bg-slate-50/50 ${selectedDocIds.includes(doc.id) ? 'bg-teal-50/50' : ''}`}>
                                            <td className="p-3">
                                              {['uploaded', 'pending'].includes(doc.status) && (
                                                <input type="checkbox" checked={selectedDocIds.includes(doc.id)} onChange={() => toggleDocSelection(doc.id)} className="rounded" />
                                              )}
                                            </td>
                                            <td className="p-3 font-medium text-slate-800">{doc.filename || 'Unknown'}</td>
                                            <td className="p-3 text-slate-600 capitalize">{doc.document_type?.replace(/_/g, ' ')}</td>
                                            <td className="p-3 text-center">{getStatusBadge(doc.status)}</td>
                                            <td className="p-3 text-slate-500 text-xs">{formatDate(doc.uploaded_at || doc.created_at)}</td>
                                            <td className="p-3">
                                              <div className="flex items-center justify-center gap-1">
                                                <Button size="sm" variant="ghost" onClick={() => downloadDocument(doc.id || doc.file_id, doc.filename)} data-testid={`dl-doc-${doc.id}`}>
                                                  <Download className="h-4 w-4" />
                                                </Button>
                                                {['uploaded', 'pending', 'pending_review'].includes(doc.status) && (
                                                  <Button 
                                                    size="sm" 
                                                    className="bg-[#2a777a] hover:bg-[#236466] text-white"
                                                    onClick={() => {
                                                      const caseInfo = cases.find(c => c.case_id === doc.case_id);
                                                      if (caseInfo) { loadCaseDetails(caseInfo.id); setActiveTab('cases'); }
                                                      setReviewDialog({ open: true, document: doc, status: '', comment: '' });
                                                    }}
                                                  >
                                                    Review
                                                  </Button>
                                                )}
                                                <Button 
                                                  size="sm" variant="outline" className="text-purple-600 border-purple-200"
                                                  onClick={async () => {
                                                    try {
                                                      toast.info('Running AI analysis...');
                                                      const res = await axios.post(`${API}/ai/verify-document/${doc.id}`, {}, getAuthHeader());
                                                      toast.success('AI analysis complete!');
                                                      setAiAnalysis({ open: true, doc: doc, result: res.data });
                                                    } catch (e) { toast.error('AI analysis failed'); }
                                                  }}
                                                  data-testid={`ai-verify-${doc.id}`}
                                                >
                                                  AI
                                                </Button>
                                              </div>
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              </details>
                            </Card>
                          );
                        })}
                      </div>
                    )}
                  </>
                );
              })()}
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
              {reviewDialog.document?.uploader_name && (
                <p className="text-sm text-slate-500 mb-3">Uploaded by: {reviewDialog.document.uploader_name} on {formatDate(reviewDialog.document.uploaded_at)}</p>
              )}
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
              <Label>
                Comment
                {(reviewDialog.status === 'rejected' || reviewDialog.status === 'revision_required') && <span className="text-red-500"> * (required)</span>}
              </Label>
              <Textarea
                value={reviewDialog.comment}
                onChange={(e) => setReviewDialog({ ...reviewDialog, comment: e.target.value })}
                placeholder={
                  reviewDialog.status === 'rejected' ? 'Explain why this document is rejected (min 5 chars)...' :
                  reviewDialog.status === 'revision_required' ? 'Explain what revisions are needed (min 5 chars)...' :
                  'Add review comments (optional)...'
                }
                rows={4}
                data-testid="review-comment-textarea"
              />
              {(reviewDialog.status === 'rejected' || reviewDialog.status === 'revision_required') && (
                <p className="text-xs text-slate-400 mt-1">{reviewDialog.comment.length}/5 characters minimum</p>
              )}
            </div>
            <div className="flex gap-3">
              <Button 
                onClick={() => {
                  downloadDocument(reviewDialog.document?.id || reviewDialog.document?.file_id, reviewDialog.document?.filename);
                }}
                variant="outline" 
                className="flex-1"
                data-testid="review-download-btn"
              >
                <Download className="h-4 w-4 mr-1" />View File
              </Button>
              <Button 
                onClick={handleReviewDocument} 
                className={`flex-1 ${reviewDialog.status === 'approved' ? 'bg-emerald-600 hover:bg-emerald-700' : reviewDialog.status === 'rejected' ? 'bg-red-600 hover:bg-red-700' : 'bg-[#2a777a] hover:bg-[#236466]'}`}
                disabled={!reviewDialog.status || ((reviewDialog.status === 'rejected' || reviewDialog.status === 'revision_required') && reviewDialog.comment.trim().length < 5)}
                data-testid="submit-review-button"
              >
                Submit Review
              </Button>
            </div>
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

      {/* Information Sheet Dialog */}
      <Dialog open={infoSheetDialog.open} onOpenChange={(open) => setInfoSheetDialog({ ...infoSheetDialog, open })}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Client Information Sheet</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Personal Information */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Personal Information</h4>
              <div className="grid grid-cols-3 gap-3">
                <div><Label>Full Name</Label><Input value={infoSheetDialog.data.full_name || ''} onChange={(e) => updateInfoField('full_name', e.target.value)} data-testid="info-full-name" /></div>
                <div><Label>Date of Birth</Label><Input type="date" value={infoSheetDialog.data.date_of_birth || ''} onChange={(e) => updateInfoField('date_of_birth', e.target.value)} /></div>
                <div><Label>Gender</Label>
                  <Select value={infoSheetDialog.data.gender || ''} onValueChange={(v) => updateInfoField('gender', v)}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Nationality</Label><Input value={infoSheetDialog.data.nationality || ''} onChange={(e) => updateInfoField('nationality', e.target.value)} /></div>
                <div><Label>Passport Number</Label><Input value={infoSheetDialog.data.passport_number || ''} onChange={(e) => updateInfoField('passport_number', e.target.value)} /></div>
                <div><Label>Passport Expiry</Label><Input type="date" value={infoSheetDialog.data.passport_expiry || ''} onChange={(e) => updateInfoField('passport_expiry', e.target.value)} /></div>
              </div>
            </div>

            {/* Contact */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Contact Information</h4>
              <div className="grid grid-cols-3 gap-3">
                <div><Label>Phone</Label><Input value={infoSheetDialog.data.phone || ''} onChange={(e) => updateInfoField('phone', e.target.value)} /></div>
                <div><Label>Email</Label><Input value={infoSheetDialog.data.email || ''} onChange={(e) => updateInfoField('email', e.target.value)} /></div>
                <div><Label>Postal Code</Label><Input value={infoSheetDialog.data.postal_code || ''} onChange={(e) => updateInfoField('postal_code', e.target.value)} /></div>
                <div className="col-span-3"><Label>Address</Label><Input value={infoSheetDialog.data.address || ''} onChange={(e) => updateInfoField('address', e.target.value)} /></div>
                <div><Label>City</Label><Input value={infoSheetDialog.data.city || ''} onChange={(e) => updateInfoField('city', e.target.value)} /></div>
                <div><Label>State</Label><Input value={infoSheetDialog.data.state || ''} onChange={(e) => updateInfoField('state', e.target.value)} /></div>
                <div><Label>Country</Label><Input value={infoSheetDialog.data.country || ''} onChange={(e) => updateInfoField('country', e.target.value)} /></div>
              </div>
            </div>

            {/* Education */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Education</h4>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Highest Education</Label><Input value={infoSheetDialog.data.highest_education || ''} onChange={(e) => updateInfoField('highest_education', e.target.value)} /></div>
                <div><Label>Field of Study</Label><Input value={infoSheetDialog.data.field_of_study || ''} onChange={(e) => updateInfoField('field_of_study', e.target.value)} /></div>
                <div><Label>Institution</Label><Input value={infoSheetDialog.data.institution_name || ''} onChange={(e) => updateInfoField('institution_name', e.target.value)} /></div>
                <div><Label>Graduation Year</Label><Input type="number" value={infoSheetDialog.data.graduation_year || ''} onChange={(e) => updateInfoField('graduation_year', e.target.value)} /></div>
              </div>
            </div>

            {/* Work */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Work Experience</h4>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Current Occupation</Label><Input value={infoSheetDialog.data.current_occupation || ''} onChange={(e) => updateInfoField('current_occupation', e.target.value)} /></div>
                <div><Label>Employer Name</Label><Input value={infoSheetDialog.data.employer_name || ''} onChange={(e) => updateInfoField('employer_name', e.target.value)} /></div>
                <div><Label>Job Title</Label><Input value={infoSheetDialog.data.job_title || ''} onChange={(e) => updateInfoField('job_title', e.target.value)} /></div>
                <div><Label>Years of Experience</Label><Input type="number" value={infoSheetDialog.data.years_of_experience || ''} onChange={(e) => updateInfoField('years_of_experience', e.target.value)} /></div>
              </div>
            </div>

            {/* Language */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Language Proficiency</h4>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Primary Language</Label><Input value={infoSheetDialog.data.primary_language || ''} onChange={(e) => updateInfoField('primary_language', e.target.value)} /></div>
                <div><Label>English Proficiency</Label>
                  <Select value={infoSheetDialog.data.english_proficiency || ''} onValueChange={(v) => updateInfoField('english_proficiency', v)}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="native">Native</SelectItem>
                      <SelectItem value="fluent">Fluent</SelectItem>
                      <SelectItem value="intermediate">Intermediate</SelectItem>
                      <SelectItem value="basic">Basic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>IELTS Score</Label><Input type="number" step="0.5" value={infoSheetDialog.data.ielts_score || ''} onChange={(e) => updateInfoField('ielts_score', e.target.value)} /></div>
                <div><Label>Other Languages</Label><Input value={infoSheetDialog.data.other_languages || ''} onChange={(e) => updateInfoField('other_languages', e.target.value)} /></div>
              </div>
            </div>

            {/* Family */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Family Details</h4>
              <div className="grid grid-cols-3 gap-3">
                <div><Label>Marital Status</Label>
                  <Select value={infoSheetDialog.data.marital_status || ''} onValueChange={(v) => updateInfoField('marital_status', v)}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="single">Single</SelectItem>
                      <SelectItem value="married">Married</SelectItem>
                      <SelectItem value="divorced">Divorced</SelectItem>
                      <SelectItem value="widowed">Widowed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Spouse Name</Label><Input value={infoSheetDialog.data.spouse_name || ''} onChange={(e) => updateInfoField('spouse_name', e.target.value)} /></div>
                <div><Label>Number of Dependents</Label><Input type="number" value={infoSheetDialog.data.number_of_dependents || ''} onChange={(e) => updateInfoField('number_of_dependents', e.target.value)} /></div>
              </div>
              {/* Dependent Details */}
              <div className="mt-3 bg-slate-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-sm font-medium">Dependent Details (Children, Spouse, etc.)</Label>
                  <Button size="sm" variant="outline" onClick={() => {
                    const deps = infoSheetDialog.data.dependents || [];
                    updateInfoField('dependents', [...deps, { name: '', relationship: '', age: '', passport_number: '' }]);
                  }}>
                    <Plus className="h-3 w-3 mr-1" />Add Dependent
                  </Button>
                </div>
                {(infoSheetDialog.data.dependents || []).map((dep, idx) => (
                  <div key={idx} className="grid grid-cols-5 gap-2 mb-2 items-end">
                    <div><Label className="text-xs">Name</Label><Input className="text-sm h-8" value={dep.name || ''} onChange={(e) => {
                      const deps = [...(infoSheetDialog.data.dependents || [])];
                      deps[idx] = { ...deps[idx], name: e.target.value };
                      updateInfoField('dependents', deps);
                    }} /></div>
                    <div><Label className="text-xs">Relationship</Label><Input className="text-sm h-8" placeholder="Child/Spouse" value={dep.relationship || ''} onChange={(e) => {
                      const deps = [...(infoSheetDialog.data.dependents || [])];
                      deps[idx] = { ...deps[idx], relationship: e.target.value };
                      updateInfoField('dependents', deps);
                    }} /></div>
                    <div><Label className="text-xs">Age</Label><Input type="number" className="text-sm h-8" value={dep.age || ''} onChange={(e) => {
                      const deps = [...(infoSheetDialog.data.dependents || [])];
                      deps[idx] = { ...deps[idx], age: e.target.value };
                      updateInfoField('dependents', deps);
                    }} /></div>
                    <div><Label className="text-xs">Passport #</Label><Input className="text-sm h-8" value={dep.passport_number || ''} onChange={(e) => {
                      const deps = [...(infoSheetDialog.data.dependents || [])];
                      deps[idx] = { ...deps[idx], passport_number: e.target.value };
                      updateInfoField('dependents', deps);
                    }} /></div>
                    <Button size="sm" variant="ghost" className="text-red-500 h-8" onClick={() => {
                      const deps = [...(infoSheetDialog.data.dependents || [])];
                      deps.splice(idx, 1);
                      updateInfoField('dependents', deps);
                    }}>Remove</Button>
                  </div>
                ))}
                {(!infoSheetDialog.data.dependents || infoSheetDialog.data.dependents.length === 0) && (
                  <p className="text-xs text-slate-400 text-center py-2">No dependents added yet</p>
                )}
              </div>
            </div>

            {/* Immigration */}
            <div>
              <h4 className="font-semibold text-slate-800 mb-3 border-b pb-2">Immigration Details</h4>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Intended Destination</Label><Input value={infoSheetDialog.data.intended_destination || ''} onChange={(e) => updateInfoField('intended_destination', e.target.value)} /></div>
                <div><Label>Purpose of Immigration</Label><Input value={infoSheetDialog.data.purpose_of_immigration || ''} onChange={(e) => updateInfoField('purpose_of_immigration', e.target.value)} /></div>
                <div className="col-span-2"><Label>Previous Visa Refusals</Label><Textarea rows={2} value={infoSheetDialog.data.previous_visa_refusals || ''} onChange={(e) => updateInfoField('previous_visa_refusals', e.target.value)} /></div>
                <div className="col-span-2"><Label>Previous Travel History</Label><Textarea rows={2} value={infoSheetDialog.data.previous_travel_history || ''} onChange={(e) => updateInfoField('previous_travel_history', e.target.value)} /></div>
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label>Additional Notes</Label>
              <Textarea rows={3} value={infoSheetDialog.data.additional_notes || ''} onChange={(e) => updateInfoField('additional_notes', e.target.value)} />
            </div>

            {/* Case Manager Notes */}
            <div className="bg-teal-50 rounded-lg p-4 border border-teal-200">
              <h4 className="font-semibold text-[#2a777a] mb-2">Case Manager Notes</h4>
              <p className="text-xs text-slate-500 mb-2">Internal notes visible only to case managers and admins</p>
              <Textarea rows={3} placeholder="Add internal notes about this client's information (status changes, follow-up items, etc.)" value={infoSheetDialog.data.case_manager_notes || ''} onChange={(e) => updateInfoField('case_manager_notes', e.target.value)} />
            </div>

            {/* Change History */}
            {infoSheetDialog.data.change_history && infoSheetDialog.data.change_history.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-4 border">
                <h4 className="font-semibold text-slate-700 mb-2 text-sm">Change History</h4>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {infoSheetDialog.data.change_history.slice().reverse().map((entry, idx) => (
                    <div key={idx} className="text-xs text-slate-500 flex items-center gap-2">
                      <span className="font-medium text-slate-700">{entry.changed_by_name || 'Unknown'}</span>
                      <span>({entry.changed_by_role})</span>
                      <span>&middot;</span>
                      <span>{new Date(entry.changed_at).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button onClick={saveInfoSheet} className="w-full bg-[#2a777a] hover:bg-[#236466]" data-testid="save-info-sheet-btn">
              Save Information Sheet
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* AI Analysis Dialog */}
      <Dialog open={aiAnalysis.open} onOpenChange={(open) => setAiAnalysis({ ...aiAnalysis, open })}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-purple-600">AI Document Analysis</span>
              <span className="text-sm font-normal text-slate-500">— {aiAnalysis.doc?.filename}</span>
            </DialogTitle>
          </DialogHeader>
          {aiAnalysis.result && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>Model: {aiAnalysis.result.model}</span>
                <span>|</span>
                <span>Analyzed: {new Date(aiAnalysis.result.analyzed_at).toLocaleString()}</span>
              </div>
              <div className="bg-slate-50 rounded-lg p-4 prose prose-sm max-w-none whitespace-pre-wrap text-sm">
                {aiAnalysis.result.analysis}
              </div>
              {aiAnalysis.result.status === 'error' && (
                <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">Analysis encountered an error. Try again.</div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Expiry Edit Modal */}
      {expiryEditModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="cm-expiry-modal">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Calendar className="h-5 w-5 text-[#2a777a]" />
                Edit Expiry Date
              </h3>
              <button onClick={() => setExpiryEditModal(null)} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg">
              <p className="text-sm font-semibold text-slate-700">{expiryEditModal.filename}</p>
              <p className="text-xs text-slate-500">Client: {expiryEditModal.client_name || 'N/A'} | Case: {expiryEditModal.case_number || 'N/A'}</p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1">Expiry Date</label>
                <input type="date" value={expiryEditDate} onChange={e => setExpiryEditDate(e.target.value)} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm" data-testid="cm-expiry-date-input" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1">Notes</label>
                <input value={expiryEditNotes} onChange={e => setExpiryEditNotes(e.target.value)} placeholder="e.g. IELTS valid 2 years" className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm" data-testid="cm-expiry-notes-input" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => setExpiryEditModal(null)}>Cancel</Button>
              <Button className="flex-1 bg-[#2a777a] hover:bg-[#236466]" onClick={handleCMSetExpiry} disabled={!expiryEditDate} data-testid="cm-save-expiry-btn">
                Save Expiry
              </Button>
            </div>
          </div>
        </div>
      )}

      </div>
    </div>
  );
};

export default CaseManagerDashboard;
