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
import DashboardShell from '@/components/DashboardShell';
import InfoSheetEditor from '@/components/InfoSheetEditor';
import ChatWidget from '@/components/ChatWidget';
import WorkloadDashboard from '@/components/WorkloadDashboard';
import DocumentChecklist from '@/components/DocumentChecklist';
import CreateTicket from '@/components/CreateTicket';
import TicketSection from '@/components/TicketSection';
import QuickActions from '@/components/QuickActions';
import { Briefcase, FileText, CheckCircle, AlertCircle, LogOut, Download, Plus, Send, ArrowLeft, MessageSquare, Search, Filter, Clock, Eye, Menu, X, Lock, Calendar, AlertTriangle, User, ClipboardList, Zap, BookOpen, Star, ArrowRightLeft, Sparkles, Loader2 } from 'lucide-react';
import BulkOperations from '@/pages/BulkOperations';
import SLATracker from '@/pages/SLATracker';
import CaseTransfer from '@/pages/CaseTransfer';
import KnowledgeBase from '@/pages/KnowledgeBase';
import SatisfactionSurvey from '@/pages/SatisfactionSurvey';
import Appointments from '@/pages/Appointments';
import CannedResponses from '@/pages/CannedResponses';
import CaseTimeline from '@/pages/CaseTimeline';
import CaseNotesAndTags from '@/pages/CaseNotesAndTags';
import SmartWorkload from '@/components/SmartWorkload';
import CommunicationHub from '@/components/CommunicationHub';
import BatchCaseOps from '@/components/BatchCaseOps';
import CMDocManager from '@/components/CMDocManager';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
    step_order: null,
    step_name: ''
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
  const [infoSheetCaseId, setInfoSheetCaseId] = useState(null);
  const [extractingResume, setExtractingResume] = useState(false);

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
      // Trigger step-documents sync first (merges admin defaults into case_steps)
      await axios.get(`${API}/step-documents/case/${caseId}`, getAuthHeader()).catch(() => {});
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
    if (!additionalDocDialog.document_name) {
      toast.error('Please enter document name');
      return;
    }

    try {
      const isStepDoc = additionalDocDialog.step_order !== null && additionalDocDialog.step_name;

      if (isStepDoc) {
        // Route to step-documents API (adds to case_steps.required_documents)
        await axios.post(`${API}/step-documents/request-step-doc`, {
          case_id: selectedCase.id,
          step_name: additionalDocDialog.step_name,
          doc_name: additionalDocDialog.document_name,
          is_mandatory: true,
          tag: 'mandatory',
          notes: additionalDocDialog.description || '',
        }, getAuthHeader());
      } else {
        // Route to step-documents additional API (separate section)
        await axios.post(`${API}/step-documents/request-additional`, {
          case_id: selectedCase.id,
          doc_name: additionalDocDialog.document_name,
          is_mandatory: true,
          tag: 'mandatory',
          notes: additionalDocDialog.description || '',
        }, getAuthHeader());
      }

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

      toast.success(isStepDoc ? `Document added to step "${additionalDocDialog.step_name}"!` : 'Additional document requested!');
      setAdditionalDocDialog({ 
        open: false, document_name: '', description: '', due_date: '',
        expiry_date: '', validity_months: '', doc_type: '', step_order: null, step_name: ''
      });
      loadCaseDetails(selectedCase.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to request document');
    }
  };

  const openCustomDocDialog = (stepOrder, stepName) => {
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
      step_order: stepOrder,
      step_name: stepName
    });
  };

  const [aiSuggesting, setAiSuggesting] = useState(null); // step_name or null

  const cmAiSuggestDocs = async (stepName, stepDescription = '') => {
    if (!selectedCase) return;
    setAiSuggesting(stepName);
    try {
      const existingDocs = (selectedCase.steps?.find(s => s.step_name === stepName)?.required_documents || []).map(d => d.doc_name || d.name || '').filter(Boolean);
      const res = await axios.post(`${API}/step-documents/ai-suggest-step-docs`, {
        product_name: selectedCase.product_name || '',
        step_name: stepName,
        step_description: stepDescription,
        existing_docs: existingDocs,
      }, getAuthHeader());
      const suggestions = res.data.suggestions || [];
      if (suggestions.length === 0) { toast.info('No new suggestions'); setAiSuggesting(null); return; }
      // Add each suggestion as a step doc
      let added = 0;
      for (const s of suggestions) {
        try {
          await axios.post(`${API}/step-documents/request-step-doc`, {
            case_id: selectedCase.id,
            step_name: stepName,
            doc_name: s.doc_name,
            is_mandatory: s.is_mandatory !== false,
            tag: s.is_mandatory !== false ? 'mandatory' : 'optional',
            notes: s.description || '',
          }, getAuthHeader());
          added++;
        } catch (e) {
          // Duplicate doc - skip silently
        }
      }
      toast.success(`AI added ${added} documents to "${stepName}"!`);
      loadCaseDetails(selectedCase.id);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'AI suggestion failed');
    }
    setAiSuggesting(null);
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

  const navGroups = [
    { id: 'dashboard', icon: Briefcase, label: 'Dashboard', onClick: () => { setActiveTab('dashboard'); setSelectedCase(null); setInfoSheetCaseId(null); } },
    {
      groupLabel: 'Case Management',
      defaultOpen: true,
      items: [
        { id: 'cases', icon: FileText, label: 'My Cases', onClick: () => { setActiveTab('cases'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'smart-workload', icon: AlertCircle, label: 'Smart Workload', onClick: () => { setActiveTab('smart-workload'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'pending-review', icon: AlertCircle, label: 'Pending Review', badge: pendingReviewCount, onClick: () => { setActiveTab('pending-review'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'batch-ops', icon: Zap, label: 'Batch Operations', onClick: () => { setActiveTab('batch-ops'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'info-sheets', icon: ClipboardList, label: 'Info Sheets', onClick: () => { setActiveTab('info-sheets'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'sla-tracker', icon: Clock, label: 'SLA Tracker', onClick: () => { setActiveTab('sla-tracker'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'case-transfer', icon: ArrowRightLeft, label: 'Case Transfer', onClick: () => { setActiveTab('case-transfer'); setSelectedCase(null); setInfoSheetCaseId(null); } },
      ]
    },
    {
      groupLabel: 'Communication',
      defaultOpen: true,
      items: [
        { id: 'communication-hub', icon: Send, label: 'Client Messages', onClick: () => { setActiveTab('communication-hub'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'tickets', icon: MessageSquare, label: 'Support Tickets', onClick: () => { setActiveTab('tickets'); setSelectedCase(null); setInfoSheetCaseId(null); } },
      ]
    },
    {
      groupLabel: 'Documents',
      defaultOpen: true,
      items: [
        { id: 'documents', icon: Download, label: 'All Documents', onClick: () => { setActiveTab('documents'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'step-docs', icon: FileText, label: 'Step Documents', onClick: () => { setActiveTab('step-docs'); setInfoSheetCaseId(null); } },
        { id: 'expiry-alerts', icon: Calendar, label: 'Expiry Alerts', badge: expiringDocs.filter(d => d.urgency === 'expired' || d.urgency === 'critical').length, badgeColor: 'bg-red-500', onClick: () => { setActiveTab('expiry-alerts'); setSelectedCase(null); setInfoSheetCaseId(null); } },
      ]
    },
    {
      groupLabel: 'Tools',
      items: [
        { id: 'knowledge-base', icon: BookOpen, label: 'Knowledge Base', onClick: () => { setActiveTab('knowledge-base'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'surveys', icon: Star, label: 'Survey Stats', onClick: () => { setActiveTab('surveys'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'appointments', icon: Calendar, label: 'Appointments', onClick: () => { setActiveTab('appointments'); setSelectedCase(null); setInfoSheetCaseId(null); } },
        { id: 'canned-responses', icon: Zap, label: 'Canned Responses', onClick: () => { setActiveTab('canned-responses'); setSelectedCase(null); setInfoSheetCaseId(null); } },
      ]
    },
  ];

  const getPageTitle = () => {
    if (selectedCase) return `Case: ${selectedCase.case_id}`;
    if (activeTab === 'info-sheets' && infoSheetCaseId) {
      const c = cases.find(x => x.id === infoSheetCaseId);
      return `Info Sheet: ${c?.client_name || ''}`;
    }
    const titles = {
      dashboard: 'Dashboard', cases: 'My Cases', 'pending-review': 'Pending Review',
      documents: 'All Documents', tickets: 'Support', 'expiry-alerts': 'Document Expiry Alerts',
      'info-sheets': 'Client Info Sheets', 'bulk-ops': 'Bulk Operations',
      'sla-tracker': 'SLA Tracker', 'case-transfer': 'Case Transfer',
      'knowledge-base': 'Knowledge Base', surveys: 'Survey Stats', appointments: 'Appointments',
      'canned-responses': 'Canned Responses',
      'smart-workload': 'Smart Workload',
      'communication-hub': 'Client Communication Hub',
      'batch-ops': 'Batch Case Operations',
      'step-docs': 'Step Documents',
    };
    return titles[activeTab] || 'Dashboard';
  };

  return (
    <DashboardShell
      user={user}
      roleLabel="Case Manager"
      navGroups={navGroups}
      activeTab={activeTab}
      pageTitle={getPageTitle()}
      showBackButton={!!selectedCase || (activeTab === 'info-sheets' && !!infoSheetCaseId)}
      onBack={() => {
        if (selectedCase) { setSelectedCase(null); setActiveTab('cases'); }
        else if (infoSheetCaseId) { setInfoSheetCaseId(null); }
      }}
      headerActions={selectedCase && (
        <CreateTicket caseId={selectedCase.id} clientId={selectedCase.client_id} clientName={selectedCase.client_name} restrictToClient={true} />
      )}
      onNotificationClick={handleNotificationClick}
      onLogout={handleLogout}
    >
          {activeTab === 'dashboard' && (
            <div>
              {/* Smart Workload Dashboard */}
              <WorkloadDashboard
                onNavigateToCase={(caseId) => { loadCaseDetails(caseId); setActiveTab('cases'); }}
                onNavigateToTab={(tab) => setActiveTab(tab)}
              />
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
                      onClick={() => { setInfoSheetCaseId(selectedCase.id); setActiveTab('info-sheets'); }}
                      size="sm"
                      variant="outline"
                      data-testid="info-sheet-btn"
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      View/Edit Info Sheet
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
                      onClick={() => setAdditionalDocDialog({ ...additionalDocDialog, open: true, step_order: null, step_name: '' })}
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
                                const docName = d.doc_name || d.name || '';
                                if (!docName) return null;
                                const uploaded = (caseDocuments || []).some(cd => 
                                  cd.document_type?.toLowerCase().includes(docName.toLowerCase()) || 
                                  docName.toLowerCase().includes(cd.document_type?.toLowerCase())
                                );
                                return (
                                  <span key={di} className={`text-xs px-2 py-0.5 rounded-full border ${uploaded ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
                                    {docName} {uploaded ? '\u2713' : '\u2717'}
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
                          <>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => openCustomDocDialog(step.step_order, step.step_name)}
                            data-testid={`add-doc-step-${index}`}
                          >
                            <Plus className="h-4 w-4 mr-1" />Add Doc
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-purple-300 text-purple-700 hover:bg-purple-50"
                            disabled={aiSuggesting === step.step_name}
                            onClick={() => cmAiSuggestDocs(step.step_name, step.description)}
                            data-testid={`ai-suggest-step-${index}`}
                          >
                            {aiSuggesting === step.step_name ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Sparkles className="h-4 w-4 mr-1" />}AI Suggest
                          </Button>
                          </>
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
              {/* Case Notes & Tags */}
              <CaseNotesAndTags caseId={selectedCase.id} token={localStorage.getItem('token')} />

              {/* Case Timeline */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Case Timeline</h3>
                <CaseTimeline caseId={selectedCase.id} token={localStorage.getItem('token')} />
              </Card>
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

          {/* Info Sheets Tab - Case Manager can view/edit client info sheets */}
          {activeTab === 'info-sheets' && !infoSheetCaseId && (
            <div className="space-y-4" data-testid="info-sheets-list">
              <Card className="p-5 bg-[#2a777a]/5 border border-[#2a777a]/20">
                <div className="flex items-center gap-3">
                  <ClipboardList className="h-6 w-6 text-[#2a777a]" />
                  <div>
                    <h3 className="font-semibold text-gray-900">Client Information Sheets</h3>
                    <p className="text-sm text-gray-500">Select a case to view or edit the client's information sheet</p>
                  </div>
                </div>
              </Card>
              {cases.length === 0 ? (
                <Card className="p-12 text-center">
                  <ClipboardList className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-gray-500">No cases assigned yet</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {cases.map((c) => (
                    <Card
                      key={c.id}
                      className="p-5 cursor-pointer hover:border-[#2a777a]/40 hover:shadow-md transition-all border border-gray-200"
                      onClick={() => setInfoSheetCaseId(c.id)}
                      data-testid={`info-sheet-case-${c.id}`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="h-10 w-10 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                          <User className="h-5 w-5 text-[#2a777a]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-gray-900">{c.client_name}</h4>
                          <p className="text-xs text-gray-500 mt-0.5">{c.client_email}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge variant="outline" className="text-xs">{c.case_id}</Badge>
                            <Badge variant="outline" className="text-xs text-[#2a777a] border-[#2a777a]/30">{c.product_name}</Badge>
                          </div>
                        </div>
                        <FileText className="h-5 w-5 text-gray-300 flex-shrink-0" />
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'info-sheets' && infoSheetCaseId && (
            <div data-testid="info-sheet-editor-wrapper">
              <InfoSheetEditor
                caseData={{ id: infoSheetCaseId, case_id: cases.find(c => c.id === infoSheetCaseId)?.case_id }}
                API={API}
                getAuthHeader={() => getAuthHeader()}
                onRefresh={() => loadData()}
                extractingResume={extractingResume}
                setExtractingResume={setExtractingResume}
              />
            </div>
          )}

          {activeTab === 'bulk-ops' && <BulkOperations token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'sla-tracker' && <SLATracker token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'case-transfer' && <CaseTransfer token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'knowledge-base' && <KnowledgeBase token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'surveys' && <SatisfactionSurvey token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'appointments' && <Appointments token={localStorage.getItem('token')} role="case_manager" />}
          {activeTab === 'canned-responses' && <CannedResponses token={localStorage.getItem('token')} />}
          {activeTab === 'smart-workload' && <SmartWorkload token={localStorage.getItem('token')} onSelectCase={(caseId) => { loadCaseDetails(caseId); setActiveTab('cases'); }} />}
          {activeTab === 'communication-hub' && <CommunicationHub token={localStorage.getItem('token')} cases={cases} />}
          {activeTab === 'batch-ops' && <BatchCaseOps token={localStorage.getItem('token')} />}
          {activeTab === 'step-docs' && <CMDocManager token={localStorage.getItem('token')} caseId={selectedCase?.id} caseName={selectedCase?.case_id} />}

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
              {additionalDocDialog.step_name 
                ? `Add Document to Step: ${additionalDocDialog.step_name}` 
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

      {/* Chat Widget */}
      <ChatWidget currentUser={user} />
    </DashboardShell>
  );
};

export default CaseManagerDashboard;
