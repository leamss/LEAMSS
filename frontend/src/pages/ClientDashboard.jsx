import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import DashboardShell from '@/components/DashboardShell';
import CreateTicket from '@/components/CreateTicket';
import TicketSection from '@/components/TicketSection';
import QuickActions from '@/components/QuickActions';
import ChatWidget from '@/components/ChatWidget';
import OnboardingWizard from '@/components/OnboardingWizard';
import UnifiedDocumentView from '@/components/UnifiedDocumentView';
import DeadlineTracker from '@/components/DeadlineTracker';
import IntakeFormFiller from '@/components/IntakeFormFiller';
import FeeCalculator from '@/components/FeeCalculator';
import DocumentExtractor from '@/components/DocumentExtractor';
import { 
  User, FileText, Upload, LogOut, CheckCircle, Clock, AlertCircle, 
  Lock, Download, FileCheck, ArrowLeft, Calendar, Shield, 
  FolderOpen, AlertTriangle, FileUp, Eye, ChevronRight, MessageSquare,
  CreditCard, Loader2, IndianRupee, ExternalLink, TrendingUp, Brain, FileSearch, LayoutDashboard, ClipboardList, Workflow,
  BookOpen, Star, Users, Gift, CalendarClock, Calculator, Scan
} from 'lucide-react';
import SatisfactionSurvey from '@/pages/SatisfactionSurvey';
import KnowledgeBase from '@/pages/KnowledgeBase';
import Appointments from '@/pages/Appointments';
import ReferralProgram from '@/pages/ReferralProgram';
import CaseTimeline from '@/pages/CaseTimeline';
import AIChatWidget from '@/components/AIChatWidget';
import InfoSheetEditor from '@/components/InfoSheetEditor';
import ClientProfile from '@/components/ClientProfile';
import CaseJourney from '@/components/CaseJourney';
import PaymentHistoryTimeline from '@/components/PaymentHistoryTimeline';
import MilestonesManager from '@/components/MilestonesManager';
import MessageCenter from '@/components/MessageCenter';
import EligibilityChecker from '@/components/EligibilityChecker';
import EMITracker from '@/components/EMITracker';
import FamilyManager from '@/components/FamilyManager';
import WhatsAppButton from '@/components/WhatsAppButton';
import PreAssessmentMiniPortal from '@/components/PreAssessmentMiniPortal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [initialTicketId, setInitialTicketId] = useState(null);
  const [ticketFilter, setTicketFilter] = useState(null);
  const [highlightedDocId, setHighlightedDocId] = useState(null);
  const [infoSheet, setInfoSheet] = useState(null);
  const [infoSheetCompletion, setInfoSheetCompletion] = useState({});
  const [infoSheetRequiredFields, setInfoSheetRequiredFields] = useState([]);
  const [extractingResume, setExtractingResume] = useState(false);
  const [proposals, setProposals] = useState([]);
  const [payingForSale, setPayingForSale] = useState(null);
  const [predictions, setPredictions] = useState({});
  const [bulkFiles, setBulkFiles] = useState([]);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [loadingPrediction, setLoadingPrediction] = useState(null);
  const [docChecks, setDocChecks] = useState({});
  const [expiryDocs, setExpiryDocs] = useState([]);
  const [expiryModal, setExpiryModal] = useState(null);
  const [expiryDate, setExpiryDate] = useState('');
  const [expiryNotes, setExpiryNotes] = useState('');
  const [preAssessments, setPreAssessments] = useState([]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/');
      return;
    }
    setUser(JSON.parse(userData));
  }, [navigate]);

  const loadData = async () => {
    try {
      const [casesRes, docsRes] = await Promise.all([
        axios.get(`${API}/cases/my-cases`, getAuthHeader()),
        axios.get(`${API}/documents/case/${caseData?.id || 'none'}`, getAuthHeader()).catch(() => ({ data: [] }))
      ]);
      
      if (casesRes.data.length > 0) {
        const theCase = casesRes.data[0];
        setCaseData(theCase);
        const [docsResponse, infoSheetRes] = await Promise.all([
          axios.get(`${API}/documents/case/${theCase.id}`, getAuthHeader()),
          axios.get(`${API}/cases/${theCase.id}/information-sheet`, getAuthHeader()).catch(() => ({ data: { exists: false, data: {} } }))
        ]);
        setDocuments(docsResponse.data);
        if (infoSheetRes.data?.exists) {
          setInfoSheet(infoSheetRes.data.data);
          setInfoSheetCompletion(infoSheetRes.data.completion || {});
          setInfoSheetRequiredFields(infoSheetRes.data.required_fields || []);
        }
        // Load expiry tracking data
        try {
          const expiryRes = await axios.get(`${API}/documents/expiring/case/${theCase.id}`, getAuthHeader());
          setExpiryDocs(expiryRes.data || []);
        } catch (e) { /* no expiry data */ }
        // Auto-trigger expiry reminder check (fire-and-forget)
        axios.post(`${API}/documents/check-expiry-reminders`, {}, getAuthHeader()).catch(() => {});
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }

    // Load pre-assessments early (for mini-portal view when no active case)
    try {
      const paRes = await axios.get(`${API}/pre-assess-portal/client/my-assessments`, getAuthHeader());
      setPreAssessments(paRes.data?.assessments || []);
    } catch (e) { /* no pre-assessments */ }

    // Load proposals/payments independently
    try {
      const proposalsRes = await axios.get(`${API}/payments/my-proposals`, getAuthHeader());
      setProposals(proposalsRes.data || []);
    } catch (e) { /* no proposals */ }
  };

  useEffect(() => {
    if (user) {
      loadData();
      // Check if onboarding should be shown
      const onboardingDone = localStorage.getItem(`onboarding_done_${user.id}`);
      if (!onboardingDone) setShowOnboarding(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Handle notification navigation from sessionStorage
  useEffect(() => {
    const handleNotificationNavigation = () => {
      const openTicketId = sessionStorage.getItem('openTicketId');
      const activeTabFromStorage = sessionStorage.getItem('activeTab');
      const openCaseId = sessionStorage.getItem('openCaseId');
      
      if (openTicketId) {
        sessionStorage.removeItem('openTicketId');
        setActiveTab('tickets');
        setInitialTicketId(openTicketId);
      } else if (activeTabFromStorage === 'documents' || openCaseId) {
        sessionStorage.removeItem('activeTab');
        sessionStorage.removeItem('openCaseId');
        // Switch to action tab to show documents requiring action
        setActiveTab('action');
        // If there's a specific case/doc ID, we could highlight it
        if (openCaseId) {
          setHighlightedDocId(openCaseId);
          // Clear highlight after 5 seconds
          setTimeout(() => setHighlightedDocId(null), 5000);
        }
      }
    };

    // Run after a small delay to ensure component is mounted
    const timer = setTimeout(handleNotificationNavigation, 100);
    return () => clearTimeout(timer);
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handlePayNow = async (saleId) => {
    setPayingForSale(saleId);
    try {
      const originUrl = window.location.origin;
      const res = await axios.post(`${API}/payments/create-checkout`, {
        sale_id: saleId,
        origin_url: originUrl
      }, getAuthHeader());
      if (res.data.url) {
        window.location.href = res.data.url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate payment');
      setPayingForSale(null);
    }
  };

  const handleDownloadReceipt = async (saleId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/payments/receipt-by-sale/${saleId}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `LEAMSS_Receipt_${saleId.substring(0, 8).toUpperCase()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Receipt downloaded!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to download receipt');
    }
  };

  const handleGetPrediction = async (caseId) => {
    setLoadingPrediction(caseId);
    try {
      const res = await axios.get(`${API}/ai-intel/predict-approval/${caseId}`, getAuthHeader());
      setPredictions(prev => ({ ...prev, [caseId]: res.data }));
    } catch (e) {
      toast.error('Could not generate prediction');
    } finally {
      setLoadingPrediction(null);
    }
  };

  const handleDocCheck = async (caseId) => {
    try {
      const res = await axios.get(`${API}/ai-intel/case-document-check/${caseId}`, getAuthHeader());
      setDocChecks(prev => ({ ...prev, [caseId]: res.data }));
    } catch (e) {
      toast.error('Could not check documents');
    }
  };

  const handleFileUpload = async (docName, isAdditional = false, requestId = null, stepName = null) => {
    if (!selectedFile) {
      toast.error('Please select a file');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('case_id', caseData.id);
      formData.append('step_name', stepName || docName);
      formData.append('document_type', isAdditional ? docName : 'workflow');
      if (requestId) {
        formData.append('additional_doc_id', requestId);
      }
      
      await axios.post(`${API}/documents/upload`, formData, getAuthHeader());
      toast.success('Document uploaded successfully!');
      setSelectedFile(null);
      setUploadingFor(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    }
  };

  const handleBulkUpload = async (e) => {
    const files = Array.from(e?.target?.files || []);
    if (!files.length) return;
    // Stage files for type tagging before upload
    const staged = files.map(f => ({ file: f, document_type: 'general', step_name: '' }));
    setBulkFiles(prev => [...prev, ...staged]);
    if (e?.target) e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (!files.length || !caseData) return;
    const staged = files.map(f => ({ file: f, document_type: 'general', step_name: '' }));
    setBulkFiles(prev => [...prev, ...staged]);
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };

  const updateBulkFileType = (index, field, value) => {
    setBulkFiles(prev => prev.map((f, i) => i === index ? { ...f, [field]: value } : f));
  };

  const removeBulkFile = (index) => {
    setBulkFiles(prev => prev.filter((_, i) => i !== index));
  };

  const submitBulkUpload = async () => {
    if (!bulkFiles.length || !caseData) return;
    setBulkUploading(true);
    const formData = new FormData();
    bulkFiles.forEach(f => formData.append('files', f.file));
    formData.append('case_id', caseData.id);
    formData.append('document_types', JSON.stringify(bulkFiles.map(f => f.document_type)));
    formData.append('step_names', JSON.stringify(bulkFiles.map(f => f.step_name)));
    try {
      const res = await axios.post(`${API}/documents/bulk-upload`, formData, getAuthHeader());
      toast.success(res.data.message);
      setBulkFiles([]);
      loadData();
    } catch (error) {
      toast.error('Bulk upload failed');
    }
    setBulkUploading(false);
  };

  const handleSetExpiry = async () => {
    if (!expiryModal || !expiryDate) return;
    try {
      await axios.post(`${API}/documents/${expiryModal.id}/set-expiry`, {
        expiry_date: expiryDate,
        notes: expiryNotes
      }, getAuthHeader());
      toast.success('Expiry date set successfully');
      setExpiryModal(null);
      setExpiryDate('');
      setExpiryNotes('');
      loadData();
    } catch (error) {
      toast.error('Failed to set expiry date');
    }
  };

  const getUrgencyStyle = (urgency) => {
    const styles = {
      expired: 'bg-red-100 text-red-700 border-red-200',
      critical: 'bg-orange-100 text-orange-700 border-orange-200',
      warning: 'bg-amber-100 text-amber-700 border-amber-200',
      attention: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      ok: 'bg-green-100 text-green-700 border-green-200',
      no_expiry: 'bg-slate-100 text-slate-500 border-slate-200',
    };
    return styles[urgency] || styles.no_expiry;
  };

  const getUrgencyLabel = (urgency, days) => {
    if (urgency === 'expired') return `Expired ${Math.abs(days)} days ago`;
    if (urgency === 'critical') return `Expires in ${days} days!`;
    if (urgency === 'warning') return `Expires in ${days} days`;
    if (urgency === 'attention') return `Expires in ${days} days`;
    if (urgency === 'ok') return `Valid for ${days} days`;
    return 'No expiry set';
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

  const getProgressPercentage = () => {
    if (!caseData || !caseData.steps) return 0;
    const completed = caseData.steps.filter(s => s.status === 'completed').length;
    return (completed / caseData.steps.length) * 100;
  };

  // Get additional document requests
  const additionalDocRequests = caseData?.additional_doc_requests || [];
  const pendingAdditionalDocs = additionalDocRequests.filter(r => r.status === 'pending');
  const uploadedAdditionalDocs = additionalDocRequests.filter(r => r.status === 'uploaded');

  // Get documents by step
  const getDocumentsByStep = (stepName) => {
    return documents.filter(d => d.step_name === stepName);
  };

  // Get pending workflow documents
  const getPendingWorkflowDocs = () => {
    if (!caseData?.steps) return [];
    const pending = [];
    caseData.steps.forEach(step => {
      if (!step.is_locked) {
        step.required_documents?.forEach(doc => {
          const uploaded = documents.find(d => 
            d.step_name === step.step_name && 
            (d.document_type === doc.doc_name || d.document_type === 'workflow')
          );
          if (!uploaded) {
            pending.push({ ...doc, step_name: step.step_name, step_order: step.step_order });
          }
        });
      }
    });
    return pending;
  };

  if (!user) return null;

  // Handle notification click - navigate to correct tab/item
  const handleNotificationClick = (notification) => {
    const type = notification.type || '';
    const relatedId = notification.related_id;
    
    if (type.includes('ticket')) {
      setActiveTab('tickets');
      setInitialTicketId(relatedId);
    } else if (type.includes('expiry') || type.includes('doc') || type.includes('step') || type.includes('case')) {
      // Switch to action tab for document-related notifications
      setActiveTab('action');
      if (relatedId) {
        setHighlightedDocId(relatedId);
        setTimeout(() => setHighlightedDocId(null), 5000);
      }
    }
  };

  // Determine active pre-assessment (most-recent not-expired)
  const activePA = preAssessments.find(p => ['payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'rejected', 'refund_initiated', 'refunded'].includes(p.stage));
  const isMiniMode = !caseData && !!activePA;
  const isExpandedMode = isMiniMode && ['approved', 'proposal_sent', 'proposal_paid'].includes(activePA?.stage);

  const clientNavGroups = isMiniMode ? [
    { id: 'overview', icon: LayoutDashboard, label: 'My Pre-Assessment', onClick: () => setActiveTab('overview') },
    {
      groupLabel: 'Tools',
      defaultOpen: true,
      items: [
        { id: 'doc-scanner', icon: Scan, label: 'AI Document Scanner', onClick: () => setActiveTab('doc-scanner') },
        ...(isExpandedMode ? [
          { id: 'cost-estimate', icon: Calculator, label: 'Cost Estimator', onClick: () => setActiveTab('cost-estimate') },
          { id: 'eligibility', icon: Brain, label: 'Eligibility Check', onClick: () => setActiveTab('eligibility') },
        ] : []),
      ]
    },
    {
      groupLabel: 'Communication',
      items: [
        { id: 'messages', icon: MessageSquare, label: 'Messages', onClick: () => setActiveTab('messages') },
        { id: 'tickets', icon: MessageSquare, label: 'Support Tickets', onClick: () => setActiveTab('tickets') },
      ]
    },
    { id: 'profile', icon: User, label: 'My Profile', onClick: () => setActiveTab('profile') },
  ] : [
    { id: 'overview', icon: LayoutDashboard, label: 'Overview', onClick: () => setActiveTab('overview') },
    {
      groupLabel: 'My Case',
      defaultOpen: true,
      items: [
        { id: 'journey', icon: Workflow, label: 'My Journey', onClick: () => setActiveTab('journey') },
        { id: 'documents', icon: FileCheck, label: 'Documents & Steps', badge: pendingAdditionalDocs.length, badgeColor: 'bg-red-500', onClick: () => setActiveTab('documents') },
        { id: 'deadlines', icon: CalendarClock, label: 'Deadlines', onClick: () => setActiveTab('deadlines') },
        { id: 'uploaded', icon: Upload, label: 'My Uploads', onClick: () => setActiveTab('uploaded') },
        { id: 'info-sheet', icon: ClipboardList, label: 'Case Intake Form', onClick: () => setActiveTab('info-sheet') },
      ]
    },
    {
      groupLabel: 'Finance',
      items: [
        { id: 'payments', icon: CreditCard, label: 'Payments', badge: proposals.filter(p => p.status === 'approved' && (p.pending_amount || 0) > 0).length, badgeColor: 'bg-[#f7620b]', onClick: () => setActiveTab('payments') },
        { id: 'emi-plans', icon: CreditCard, label: 'EMI Plans', onClick: () => setActiveTab('emi-plans') },
      ]
    },
    {
      groupLabel: 'Communication',
      items: [
        { id: 'messages', icon: MessageSquare, label: 'Messages', onClick: () => setActiveTab('messages') },
        { id: 'tickets', icon: MessageSquare, label: 'Support Tickets', onClick: () => setActiveTab('tickets') },
      ]
    },
    {
      groupLabel: 'Tools',
      items: [
        { id: 'cost-estimate', icon: Calculator, label: 'Cost Estimator', onClick: () => setActiveTab('cost-estimate') },
        { id: 'doc-scanner', icon: Scan, label: 'AI Document Scanner', onClick: () => setActiveTab('doc-scanner') },
        { id: 'eligibility', icon: Brain, label: 'Eligibility Check', onClick: () => setActiveTab('eligibility') },
        { id: 'family', icon: Users, label: 'Family Members', onClick: () => setActiveTab('family') },
      ]
    },
    {
      groupLabel: 'Resources',
      items: [
        { id: 'knowledge-base', icon: BookOpen, label: 'Help Center', onClick: () => setActiveTab('knowledge-base') },
        { id: 'survey', icon: Star, label: 'Rate Experience', onClick: () => setActiveTab('survey') },
        { id: 'appointments', icon: Calendar, label: 'Appointments', onClick: () => setActiveTab('appointments') },
        { id: 'referrals', icon: Users, label: 'Refer a Friend', onClick: () => setActiveTab('referrals') },
        { id: 'timeline', icon: Clock, label: 'Case Timeline', onClick: () => setActiveTab('timeline') },
      ]
    },
    { id: 'profile', icon: User, label: 'My Profile', onClick: () => setActiveTab('profile') },
  ];

  const clientPageTitle = {
    overview: 'Overview', documents: 'Documents & Workflow', 
    uploaded: 'My Uploads', tickets: 'Support Tickets', 'info-sheet': 'Case Intake Form',
    payments: 'Payments',
    'knowledge-base': 'Help Center', survey: 'Rate Experience', appointments: 'Appointments',
    referrals: 'Refer a Friend', timeline: 'Case Timeline',
    journey: 'My Case Journey', messages: 'Messages', profile: 'My Profile',
    eligibility: 'Eligibility Check', 'emi-plans': 'EMI Payment Plans',
    family: 'Family Members',
  }[activeTab] || 'Overview';

  return (
    <DashboardShell
      user={user}
      roleLabel="Client"
      navGroups={clientNavGroups}
      activeTab={activeTab}
      pageTitle={clientPageTitle}
      headerActions={
        <CreateTicket caseId={caseData?.id} onTicketCreated={() => setActiveTab('tickets')} />
      }
      onNotificationClick={handleNotificationClick}
      onLogout={handleLogout}
    >
      <main>
        {!caseData ? (
          isMiniMode ? (
            <>
              {activeTab === 'overview' && (
                <PreAssessmentMiniPortal
                  pa={activePA}
                  onRefresh={loadData}
                  onOpenScanner={() => setActiveTab('doc-scanner')}
                />
              )}
              {activeTab === 'doc-scanner' && (
                <DocumentExtractor />
              )}
              {activeTab === 'cost-estimate' && isExpandedMode && (
                <FeeCalculator />
              )}
              {activeTab === 'eligibility' && isExpandedMode && (
                <EligibilityChecker token={localStorage.getItem('token')} />
              )}
              {activeTab === 'messages' && (
                <MessageCenter />
              )}
              {activeTab === 'tickets' && (
                <TicketSection caseId={null} initialTicketId={initialTicketId} filter={ticketFilter} onClearFilter={() => setTicketFilter(null)} />
              )}
              {activeTab === 'profile' && (
                <ClientProfile user={user} onUpdate={setUser} />
              )}
            </>
          ) : (
            <Card className="p-12 text-center bg-white shadow-xl rounded-2xl border-0">
              <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-slate-100 to-slate-200 rounded-full flex items-center justify-center">
                <FileText className="h-10 w-10 text-slate-400" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">No Active Case</h2>
              <p className="text-slate-500 max-w-md mx-auto">
                You don&apos;t have any active cases yet. Please contact your case manager or partner for assistance.
              </p>
            </Card>
          )
        ) : (
          <>
            {/* Case Overview Header - Only show on dashboard-like tabs */}
            {!['messages', 'profile', 'journey', 'timeline', 'eligibility', 'emi-plans', 'family', 'documents', 'deadlines', 'cost-estimate', 'doc-scanner'].includes(activeTab) && (
            <>
            <div className="mb-8">
              <div className="bg-gradient-to-r from-[#2a777a] via-[#2a777a] to-[#236466] rounded-2xl p-6 text-white shadow-xl">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className="bg-white/20 text-white border-0">{caseData.case_id}</Badge>
                      <Badge className={`border-0 ${caseData.status === 'active' ? 'bg-green-500' : 'bg-amber-500'}`}>
                        {caseData.status?.toUpperCase()}
                      </Badge>
                    </div>
                    <h2 className="text-2xl font-bold mb-1">{caseData.product_name}</h2>
                    <p className="text-white/80 text-sm">Case Manager: {caseData.case_manager_name}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 min-w-[200px]">
                    <p className="text-white/80 text-sm mb-2">Current Step</p>
                    <p className="font-semibold text-lg">{caseData.current_step}</p>
                    <div className="mt-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Progress</span>
                        <span>{Math.round(getProgressPercentage())}%</span>
                      </div>
                      <Progress value={getProgressPercentage()} className="h-2 bg-white/20" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions Widget */}
            <div className="mb-6">
              <QuickActions 
                userRole="client" 
                caseId={caseData?.id}
                onNavigate={(tab, filter) => {
                  setActiveTab(tab);
                  if (filter && tab === 'tickets') setTicketFilter(filter);
                }} 
              />
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <Card className="p-4 bg-white border-0 shadow-md hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-[#f7620b] to-[#e55a09] rounded-xl flex items-center justify-center shadow-lg">
                    <AlertTriangle className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{pendingAdditionalDocs.length}</p>
                    <p className="text-xs text-slate-500">Pending Requests</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 bg-white border-0 shadow-md hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-xl flex items-center justify-center shadow-lg">
                    <FileCheck className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{documents.filter(d => d.status === 'approved').length}</p>
                    <p className="text-xs text-slate-500">Approved Docs</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 bg-white border-0 shadow-md hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center shadow-lg">
                    <Clock className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{documents.filter(d => d.status === 'pending_review').length}</p>
                    <p className="text-xs text-slate-500">Under Review</p>
                  </div>
                </div>
              </Card>
              <Card className="p-4 bg-white border-0 shadow-md hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                    <FolderOpen className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{caseData.steps?.filter(s => s.status === 'completed').length || 0}</p>
                    <p className="text-xs text-slate-500">Steps Completed</p>
                  </div>
                </div>
              </Card>
            </div>

            {/* AI Insights Panel */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              {/* Approval Prediction */}
              <Card className="p-5 bg-white border-0 shadow-md" data-testid="approval-prediction-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-[#2a777a]" />
                    Approval Prediction
                  </h3>
                  <Button
                    onClick={() => handleGetPrediction(caseData.id)}
                    disabled={loadingPrediction === caseData.id}
                    variant="outline" size="sm"
                    className="text-[#2a777a] border-[#2a777a]"
                    data-testid="get-prediction-btn"
                  >
                    {loadingPrediction === caseData.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4 mr-1" />}
                    {loadingPrediction === caseData.id ? 'Analyzing...' : predictions[caseData.id] ? 'Refresh' : 'Analyze'}
                  </Button>
                </div>
                {predictions[caseData.id] ? (
                  <div>
                    <div className="flex items-center gap-4 mb-3">
                      <div className={`text-4xl font-bold ${
                        predictions[caseData.id].approval_probability >= 70 ? 'text-emerald-600' :
                        predictions[caseData.id].approval_probability >= 40 ? 'text-amber-600' : 'text-red-500'
                      }`}>
                        {predictions[caseData.id].approval_probability}%
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Approval Probability</p>
                        <p className={`text-xs font-semibold ${
                          predictions[caseData.id].risk_level === 'low' ? 'text-emerald-600' :
                          predictions[caseData.id].risk_level === 'medium' ? 'text-amber-600' : 'text-red-500'
                        }`}>Risk: {predictions[caseData.id].risk_level?.toUpperCase()}</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-2">{predictions[caseData.id].prediction_summary}</p>
                    {predictions[caseData.id].missing_actions?.length > 0 && (
                      <div className="mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                        <p className="text-xs font-semibold text-amber-700 mb-1">Recommended Actions:</p>
                        {predictions[caseData.id].missing_actions.slice(0, 3).map((a, i) => (
                          <p key={i} className="text-xs text-amber-600">- {a}</p>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">Click "Analyze" to get AI-powered approval probability for your case.</p>
                )}
              </Card>

              {/* Document Completeness */}
              <Card className="p-5 bg-white border-0 shadow-md" data-testid="doc-check-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <FileSearch className="h-5 w-5 text-[#f7620b]" />
                    Document Check
                  </h3>
                  <Button
                    onClick={() => handleDocCheck(caseData.id)}
                    variant="outline" size="sm"
                    className="text-[#f7620b] border-[#f7620b]"
                    data-testid="check-docs-btn"
                  >
                    <FileSearch className="h-4 w-4 mr-1" /> Check
                  </Button>
                </div>
                {docChecks[caseData.id] ? (
                  <div>
                    <div className="flex items-center gap-4 mb-3">
                      <div className={`text-4xl font-bold ${
                        docChecks[caseData.id].completeness_percentage === 100 ? 'text-emerald-600' :
                        docChecks[caseData.id].completeness_percentage >= 50 ? 'text-amber-600' : 'text-red-500'
                      }`}>
                        {docChecks[caseData.id].completeness_percentage}%
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Document Completeness</p>
                        <p className="text-xs text-slate-400">{docChecks[caseData.id].uploaded_count}/{docChecks[caseData.id].total_required} uploaded</p>
                      </div>
                    </div>
                    {/* Step-wise missing docs */}
                    {docChecks[caseData.id].missing_documents?.length > 0 && (
                      <div className="p-2 bg-red-50 rounded-lg border border-red-200 space-y-1">
                        <p className="text-xs font-semibold text-red-700 mb-1">Missing Documents:</p>
                        {docChecks[caseData.id].missing_documents.map((d, i) => (
                          <div key={i} className="flex justify-between items-center text-xs">
                            <span className="text-red-600">- {d.doc_name} <span className="text-red-400">(Step: {d.step_name})</span></span>
                            <Button variant="ghost" size="sm" className="text-[#f7620b] h-6 text-xs px-2"
                              onClick={() => setActiveTab('documents')} data-testid={`upload-missing-${i}`}>
                              <Upload className="h-3 w-3 mr-1" /> Upload
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                    {docChecks[caseData.id].completeness_percentage === 100 && (
                      <div className="p-2 bg-emerald-50 rounded-lg border border-emerald-200">
                        <p className="text-sm text-emerald-700 font-semibold flex items-center gap-1">
                          <CheckCircle className="h-4 w-4" /> All documents uploaded!
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">Click "Check" to verify all required documents are uploaded per workflow step.</p>
                )}
              </Card>
            </div>
            </>
            )}

            {/* Main Content */}
            <div className="space-y-6">

              {/* Overview Tab */}
              {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Alert for Pending Actions */}
                {pendingAdditionalDocs.length > 0 && (
                  <Card className="p-6 bg-gradient-to-r from-[#f7620b]/10 to-[#f7620b]/5 border-l-4 border-[#f7620b] shadow-md">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-[#f7620b] rounded-full flex items-center justify-center flex-shrink-0">
                        <AlertTriangle className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-lg text-slate-800 mb-1">Action Required</h3>
                        <p className="text-slate-600 mb-3">
                          Your Case Manager has requested {pendingAdditionalDocs.length} additional document(s). 
                          Please upload them as soon as possible.
                        </p>
                        <Button 
                          onClick={() => setActiveTab('documents')} 
                          className="bg-[#f7620b] hover:bg-[#e55a09]"
                        >
                          View Requests <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Document Expiry Tracker */}
                {expiryDocs.filter(d => d.urgency !== 'no_expiry' && d.urgency !== 'ok').length > 0 && (
                  <Card className="p-6 bg-white shadow-md border-0" data-testid="expiry-tracker-card">
                    <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                      <Calendar className="h-5 w-5 text-[#f7620b]" />
                      Document Expiry Alerts
                      <Badge className="bg-red-100 text-red-700 ml-2">
                        {expiryDocs.filter(d => d.urgency === 'expired' || d.urgency === 'critical').length} urgent
                      </Badge>
                    </h3>
                    <div className="space-y-3">
                      {expiryDocs.filter(d => d.urgency !== 'no_expiry' && d.urgency !== 'ok').map((doc) => (
                        <div key={doc.id} className={`flex items-center gap-3 p-3 rounded-lg border ${getUrgencyStyle(doc.urgency)}`} data-testid={`expiry-alert-${doc.id}`}>
                          <div className="flex-shrink-0">
                            {doc.urgency === 'expired' ? <AlertCircle className="h-5 w-5" /> :
                             doc.urgency === 'critical' ? <AlertTriangle className="h-5 w-5" /> :
                             <Clock className="h-5 w-5" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-sm truncate">{doc.filename}</p>
                            <p className="text-xs capitalize">{doc.document_type.replace('_', ' ')}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="text-sm font-bold">{getUrgencyLabel(doc.urgency, doc.days_remaining)}</p>
                            <p className="text-xs">{doc.expiry_date ? new Date(doc.expiry_date).toLocaleDateString() : ''}</p>
                          </div>
                          <Button size="sm" variant="outline" className="flex-shrink-0" onClick={() => {
                            setExpiryModal(doc);
                            setExpiryDate(doc.expiry_date ? doc.expiry_date.split('T')[0] : '');
                            setExpiryNotes(doc.expiry_notes || '');
                          }} data-testid={`edit-expiry-${doc.id}`}>
                            <Calendar className="h-3 w-3 mr-1" /> Update
                          </Button>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Workflow Progress */}
                <Card className="p-6 bg-white shadow-md border-0">
                  <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-[#2a777a]" />
                    Case Progress
                  </h3>
                  <div className="space-y-4">
                    {caseData.steps?.map((step, index) => (
                      <div key={index} className={`flex items-center gap-4 p-4 rounded-xl transition-all ${
                        step.status === 'completed' ? 'bg-green-50 border border-green-200' :
                        step.status === 'in_progress' ? 'bg-blue-50 border border-blue-200' :
                        step.is_locked ? 'bg-slate-50 border border-slate-200' : 'bg-amber-50 border border-amber-200'
                      }`}>
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                          step.status === 'completed' ? 'bg-green-500' :
                          step.status === 'in_progress' ? 'bg-blue-500' :
                          step.is_locked ? 'bg-slate-300' : 'bg-amber-500'
                        }`}>
                          {step.status === 'completed' ? <CheckCircle className="h-5 w-5 text-white" /> :
                           step.is_locked ? <Lock className="h-5 w-5 text-white" /> :
                           <Clock className="h-5 w-5 text-white" />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-slate-800">Step {step.step_order}: {step.step_name}</h4>
                            <Badge className={`text-xs ${
                              step.status === 'completed' ? 'bg-green-100 text-green-700' :
                              step.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                              step.is_locked ? 'bg-slate-100 text-slate-600' : 'bg-amber-100 text-amber-700'
                            }`}>
                              {step.status === 'completed' ? 'Completed' : step.is_locked ? 'Locked' : 'In Progress'}
                            </Badge>
                          </div>
                          {step.description && <p className="text-sm text-slate-500 mt-1">{step.description}</p>}
                        </div>
                        <div className="text-sm text-slate-500">
                          {getDocumentsByStep(step.step_name).length} docs
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
              )}

              {/* Unified Documents & Steps View */}
              {activeTab === 'documents' && (
                <UnifiedDocumentView 
                  token={localStorage.getItem('token')} 
                  caseId={caseData?.id}
                  caseData={caseData}
                  onDocumentUploaded={() => {
                    // Refresh documents
                    axios.get(`${API}/documents/case/${caseData.id}`, getAuthHeader()).then(r => setDocuments(r.data)).catch(() => {});
                  }}
                />
              )}

              {/* Deadline Tracker Tab */}
              {activeTab === 'deadlines' && (
                <DeadlineTracker token={localStorage.getItem('token')} caseId={caseData?.id} role="client" caseName={caseData?.case_id} />
              )}

              {/* Cost Estimator Tab */}
              {activeTab === 'cost-estimate' && (
                <FeeCalculator token={localStorage.getItem('token')} role="client" caseId={caseData?.id} />
              )}

              {/* AI Document Scanner Tab */}
              {activeTab === 'doc-scanner' && (
                <DocumentExtractor token={localStorage.getItem('token')} role="client" caseId={caseData?.id} />
              )}

              {/* My Documents Tab */}
              {activeTab === 'uploaded' && (
              <div className="space-y-6">
                {/* Drag & Drop Bulk Upload Zone */}
                <Card className="p-6 bg-white shadow-md border-0">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                      <Upload className="h-5 w-5 text-[#2a777a]" />
                      Upload Documents
                    </h3>
                    <label className="cursor-pointer">
                      <input type="file" multiple className="hidden" onChange={handleBulkUpload} data-testid="bulk-upload-input" />
                      <span className="inline-flex items-center gap-2 px-4 py-2 bg-[#2a777a] text-white rounded-lg text-sm font-medium hover:bg-[#236466] transition-colors">
                        <Upload className="h-4 w-4" /> Browse Files
                      </span>
                    </label>
                  </div>

                  {/* Drag and Drop Zone */}
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    data-testid="drag-drop-zone"
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                      isDragging ? 'border-[#2a777a] bg-[#2a777a]/5 scale-[1.01]' : 'border-slate-300 bg-slate-50 hover:border-[#2a777a]/50'
                    }`}
                  >
                    <FileUp className={`h-10 w-10 mx-auto mb-3 ${isDragging ? 'text-[#2a777a]' : 'text-slate-400'}`} />
                    <p className="text-slate-600 font-medium">
                      {isDragging ? 'Drop files here...' : 'Drag & drop files here'}
                    </p>
                    <p className="text-sm text-slate-400 mt-1">or click "Browse Files" above</p>
                  </div>

                  {/* Staged Files for Upload */}
                  {bulkFiles.length > 0 && (
                    <div className="mt-4 space-y-3" data-testid="bulk-staging-area">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-slate-700">{bulkFiles.length} file(s) ready to upload</h4>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => setBulkFiles([])} data-testid="clear-bulk-files">
                            Clear All
                          </Button>
                          <Button
                            size="sm"
                            className="bg-[#2a777a] hover:bg-[#236466]"
                            onClick={submitBulkUpload}
                            disabled={bulkUploading}
                            data-testid="submit-bulk-upload"
                          >
                            {bulkUploading ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Uploading...</> : <><Upload className="h-4 w-4 mr-1" /> Upload All</>}
                          </Button>
                        </div>
                      </div>
                      {bulkFiles.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-3 bg-slate-50 rounded-lg p-3 border border-slate-200" data-testid={`staged-file-${idx}`}>
                          <FileText className="h-5 w-5 text-[#2a777a] flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-800 truncate">{item.file.name}</p>
                            <p className="text-xs text-slate-400">{(item.file.size / 1024).toFixed(1)} KB</p>
                          </div>
                          <select
                            value={item.document_type}
                            onChange={e => updateBulkFileType(idx, 'document_type', e.target.value)}
                            className="text-sm border border-slate-200 rounded-md px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-[#2a777a]"
                            data-testid={`bulk-doc-type-${idx}`}
                          >
                            <option value="general">General</option>
                            <option value="passport">Passport</option>
                            <option value="photo">Photo</option>
                            <option value="education">Education Certificate</option>
                            <option value="work_experience">Work Experience</option>
                            <option value="ielts">IELTS/Language Score</option>
                            <option value="bank_statement">Bank Statement</option>
                            <option value="medical">Medical Report</option>
                            <option value="police_clearance">Police Clearance</option>
                            <option value="birth_certificate">Birth Certificate</option>
                            <option value="resume">Resume/CV</option>
                            <option value="offer_letter">Offer Letter</option>
                            <option value="sop">SOP</option>
                            <option value="other">Other</option>
                          </select>
                          {caseData?.steps && (
                            <select
                              value={item.step_name}
                              onChange={e => updateBulkFileType(idx, 'step_name', e.target.value)}
                              className="text-sm border border-slate-200 rounded-md px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-[#2a777a]"
                              data-testid={`bulk-step-${idx}`}
                            >
                              <option value="">Select Step</option>
                              {caseData.steps.map(s => (
                                <option key={s.step_name} value={s.step_name}>{s.step_name}</option>
                              ))}
                            </select>
                          )}
                          <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700 hover:bg-red-50 px-2" onClick={() => removeBulkFile(idx)} data-testid={`remove-file-${idx}`}>
                            &times;
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Document List */}
                <Card className="p-6 bg-white shadow-md border-0">
                  <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-4">
                    <FolderOpen className="h-5 w-5 text-[#2a777a]" />
                    All Uploaded Documents
                    <Badge className="bg-[#2a777a]/10 text-[#2a777a] ml-2">{documents.length}</Badge>
                  </h3>

                  {documents.length === 0 ? (
                    <div className="text-center py-12 bg-slate-50 rounded-xl">
                      <FolderOpen className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                      <p className="text-slate-600 font-medium">No documents uploaded yet</p>
                      <p className="text-sm text-slate-500">Drag & drop files above or upload from Workflow Steps tab</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200">
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Document</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Type</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Expiry</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Status</th>
                            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documents.map((doc) => {
                            const expiryInfo = expiryDocs.find(e => e.id === doc.id);
                            return (
                            <tr key={doc.id} className="border-b border-slate-100 hover:bg-slate-50">
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  <FileText className="h-4 w-4 text-[#2a777a]" />
                                  <div>
                                    <span className="font-medium text-slate-800">{doc.filename}</span>
                                    <p className="text-xs text-slate-400">{doc.step_name || doc.document_type}</p>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600 capitalize">{doc.document_type.replace('_', ' ')}</td>
                              <td className="py-3 px-4">
                                {expiryInfo?.expiry_date ? (
                                  <Badge className={`text-xs cursor-pointer ${getUrgencyStyle(expiryInfo.urgency)}`}
                                    onClick={() => {
                                      setExpiryModal(expiryInfo);
                                      setExpiryDate(expiryInfo.expiry_date.split('T')[0]);
                                      setExpiryNotes(expiryInfo.expiry_notes || '');
                                    }}
                                    data-testid={`expiry-badge-${doc.id}`}
                                  >
                                    {expiryInfo.urgency === 'expired' ? `Expired` :
                                     expiryInfo.urgency === 'critical' ? `${expiryInfo.days_remaining}d left!` :
                                     new Date(expiryInfo.expiry_date).toLocaleDateString()}
                                  </Badge>
                                ) : (
                                  <button
                                    className="text-xs text-[#2a777a] hover:underline flex items-center gap-1"
                                    onClick={() => { setExpiryModal(doc); setExpiryDate(''); setExpiryNotes(''); }}
                                    data-testid={`set-expiry-btn-${doc.id}`}
                                  >
                                    <Calendar className="h-3 w-3" /> Set Expiry
                                  </button>
                                )}
                              </td>
                              <td className="py-3 px-4">
                                <Badge className={`text-xs ${
                                  doc.status === 'approved' ? 'bg-green-100 text-green-700' :
                                  doc.status === 'rejected' ? 'bg-red-100 text-red-700' :
                                  'bg-amber-100 text-amber-700'
                                }`}>
                                  {doc.status === 'pending_review' ? 'Under Review' : doc.status}
                                </Badge>
                              </td>
                              <td className="py-3 px-4 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <Button size="sm" variant="outline" onClick={() => downloadDocument(doc.id, doc.filename)} data-testid={`download-doc-table-${doc.id}`}>
                                    <Download className="h-4 w-4" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </div>
              )}

              {/* Support Tickets Tab */}
              {activeTab === 'tickets' && (
              <div className="space-y-6">
                <TicketSection caseId={caseData?.id} initialTicketId={initialTicketId} initialFilter={ticketFilter} />
              </div>
              )}

              {/* Information Sheet Tab */}
              {activeTab === 'info-sheet' && (
              <div className="space-y-6">
                <IntakeFormFiller token={localStorage.getItem('token')} caseId={caseData?.id} role="client" caseName={caseData?.case_id} />
                <InfoSheetEditor
                  caseData={caseData}
                  API={API}
                  getAuthHeader={getAuthHeader}
                  onRefresh={loadData}
                  extractingResume={extractingResume}
                  setExtractingResume={setExtractingResume}
                />
              </div>
              )}

              {/* Payments Tab */}
              {activeTab === 'payments' && (
              <div className="space-y-6">
                <Card className="p-6 bg-white shadow-md border-0" data-testid="payments-section">
                  <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <CreditCard className="h-5 w-5 text-[#f7620b]" />
                    My Proposals & Payments
                  </h3>

                  {proposals.length === 0 ? (
                    <div className="text-center py-16 bg-gradient-to-br from-slate-50 to-white rounded-xl border border-dashed border-slate-200">
                      <IndianRupee className="h-14 w-14 text-slate-300 mx-auto mb-4" />
                      <p className="text-slate-600 font-semibold text-lg">No proposals yet</p>
                      <p className="text-sm text-slate-500 mt-2">Your proposals will appear here once created.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {proposals.map((proposal) => {
                        const isPending = proposal.status === 'pending';
                        const isApproved = proposal.status === 'approved';
                        const hasPendingAmount = (proposal.pending_amount || 0) > 0;
                        const isPaid = proposal.payment_status === 'paid';
                        const hasDiscount = (proposal.total_discount_amount || 0) > 0;

                        return (
                          <Card key={proposal.id} className={`p-5 border-l-4 ${isPaid ? 'border-l-emerald-500 bg-emerald-50/30' : hasPendingAmount && isApproved ? 'border-l-[#f7620b] bg-orange-50/30' : 'border-l-slate-300'}`} data-testid={`proposal-${proposal.id}`}>
                            <div className="flex flex-col md:flex-row justify-between gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                  <h4 className="font-semibold text-slate-800">{proposal.product_name || 'Service'}</h4>
                                  <Badge className={`text-xs capitalize ${proposal.status === 'approved' ? 'bg-emerald-100 text-emerald-700' : proposal.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                    {proposal.status}
                                  </Badge>
                                  {isPaid && <Badge className="bg-emerald-100 text-emerald-700 text-xs">Fully Paid</Badge>}
                                </div>

                                <p className="text-sm text-slate-500 mb-3">
                                  Partner: {proposal.partner_name || 'N/A'} | Created: {proposal.created_at ? new Date(proposal.created_at).toLocaleDateString() : 'N/A'}
                                </p>

                                {/* Price Breakdown */}
                                <div className="bg-white rounded-lg border p-4 space-y-2">
                                  {hasDiscount && (
                                    <div className="flex justify-between text-sm text-slate-500">
                                      <span>Original Fee</span>
                                      <span className="line-through">₹{(proposal.fee_before_discount || proposal.fee_amount || 0).toLocaleString()}</span>
                                    </div>
                                  )}
                                  {(proposal.promo_discount_amount || 0) > 0 && (
                                    <div className="flex justify-between text-sm text-emerald-600">
                                      <span>Promo ({proposal.promo_code})</span>
                                      <span>-₹{(proposal.promo_discount_amount).toLocaleString()}</span>
                                    </div>
                                  )}
                                  {(proposal.additional_discount_percentage || 0) > 0 && (
                                    <div className="flex justify-between text-sm text-emerald-600">
                                      <span>Special Discount ({proposal.additional_discount_percentage}%)</span>
                                      <span>-₹{(proposal.additional_discount_amount || 0).toLocaleString()}</span>
                                    </div>
                                  )}
                                  <div className="flex justify-between font-semibold text-slate-800 border-t pt-2">
                                    <span>Total Fee</span>
                                    <span>₹{(proposal.fee_amount || 0).toLocaleString()}</span>
                                  </div>
                                  <div className="flex justify-between text-sm">
                                    <span className="text-emerald-600">Paid</span>
                                    <span className="text-emerald-600 font-medium">₹{(proposal.amount_received || 0).toLocaleString()}</span>
                                  </div>
                                  {hasPendingAmount && (
                                    <div className="flex justify-between text-sm font-semibold">
                                      <span className="text-[#f7620b]">Pending Amount</span>
                                      <span className="text-[#f7620b]">₹{(proposal.pending_amount || 0).toLocaleString()}</span>
                                    </div>
                                  )}
                                </div>

                                {/* Payment History */}
                                {(proposal.payment_history || []).length > 0 && (
                                  <div className="mt-3">
                                    <p className="text-xs font-semibold text-slate-500 mb-1">Payment History</p>
                                    <div className="space-y-1">
                                      {proposal.payment_history.map((ph, idx) => (
                                        <div key={idx} className="flex justify-between text-xs bg-slate-50 p-2 rounded">
                                          <span className="text-slate-600">{ph.method === 'stripe_online' ? 'Online Payment' : ph.method} — {new Date(ph.date).toLocaleDateString()}</span>
                                          <span className="font-medium text-slate-800">₹{(ph.amount || 0).toLocaleString()}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Pay Now / Receipt Button */}
                              <div className="flex flex-col items-end justify-center min-w-[180px] gap-2">
                                {isApproved && hasPendingAmount && !isPaid ? (
                                  <Button
                                    onClick={() => handlePayNow(proposal.id)}
                                    disabled={payingForSale === proposal.id}
                                    className="bg-[#f7620b] hover:bg-[#e0580a] text-white w-full md:w-auto px-6 py-3 text-base font-semibold shadow-lg"
                                    data-testid={`pay-now-${proposal.id}`}
                                  >
                                    {payingForSale === proposal.id ? (
                                      <><Loader2 className="h-5 w-5 mr-2 animate-spin" /> Processing...</>
                                    ) : (
                                      <><CreditCard className="h-5 w-5 mr-2" /> Pay ₹{(proposal.pending_amount || 0).toLocaleString()}</>
                                    )}
                                  </Button>
                                ) : isPaid ? (
                                  <div className="text-center">
                                    <CheckCircle className="h-10 w-10 text-emerald-500 mx-auto mb-1" />
                                    <p className="text-sm font-semibold text-emerald-600">Fully Paid</p>
                                  </div>
                                ) : isPending ? (
                                  <div className="text-center">
                                    <Clock className="h-8 w-8 text-amber-400 mx-auto mb-1" />
                                    <p className="text-xs text-slate-500">Awaiting Approval</p>
                                  </div>
                                ) : null}
                                {/* Download Receipt — show for any sale with received amount */}
                                {isApproved && (proposal.amount_received || 0) > 0 && (
                                  <Button
                                    onClick={() => handleDownloadReceipt(proposal.id)}
                                    variant="outline"
                                    size="sm"
                                    className="border-[#2a777a] text-[#2a777a] hover:bg-[#2a777a]/10 w-full md:w-auto"
                                    data-testid={`download-receipt-${proposal.id}`}
                                  >
                                    <Download className="h-4 w-4 mr-2" /> Receipt PDF
                                  </Button>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </Card>
              </div>
              )}

              {activeTab === 'knowledge-base' && (
                <KnowledgeBase token={localStorage.getItem('token')} role="client" />
              )}

              {activeTab === 'survey' && (
                <SatisfactionSurvey token={localStorage.getItem('token')} role="client" caseId={caseData?.id} />
              )}

              {activeTab === 'appointments' && (
                <Appointments token={localStorage.getItem('token')} role="client" />
              )}

              {activeTab === 'referrals' && (
                <ReferralProgram token={localStorage.getItem('token')} role="client" />
              )}

              {activeTab === 'timeline' && caseData?.id && (
                <CaseTimeline caseId={caseData.id} token={localStorage.getItem('token')} />
              )}

              {/* My Journey Tab */}
              {activeTab === 'journey' && (
                <>
                  <CaseJourney caseData={caseData} documents={documents} />
                  {caseData?.id && (
                    <div className="mt-6 grid md:grid-cols-2 gap-4">
                      <div className="bg-white rounded-xl border border-slate-200 p-5">
                        <h3 className="text-sm font-semibold text-slate-800 mb-3">Payment Timeline</h3>
                        <PaymentHistoryTimeline scope="case" id={caseData.id} />
                      </div>
                      <div className="bg-white rounded-xl border border-slate-200 p-5">
                        <MilestonesManager caseId={caseData.id} role="client" />
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Messages Tab */}
              {activeTab === 'messages' && (
                <MessageCenter caseId={caseData?.id} currentUser={user} />
              )}

              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <ClientProfile user={user} onProfileUpdate={(updatedUser) => {
                  setUser(updatedUser);
                  localStorage.setItem('user', JSON.stringify(updatedUser));
                }} />
              )}

              {/* Phase 12 Tabs */}
              {activeTab === 'eligibility' && <EligibilityChecker token={localStorage.getItem('token')} />}
              {activeTab === 'emi-plans' && <EMITracker token={localStorage.getItem('token')} />}
              {activeTab === 'family' && <FamilyManager token={localStorage.getItem('token')} />}
            </div>
          </>
        )}
      </main>
      {/* AI Chat Widget - floating */}
      <AIChatWidget />
      {/* WhatsApp Button */}
      <WhatsAppButton clientName={user?.name} />

      {/* Set Expiry Modal */}
      {expiryModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="expiry-modal">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Calendar className="h-5 w-5 text-[#2a777a]" />
                Set Expiry Date
              </h3>
              <button onClick={() => setExpiryModal(null)} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg">
              <p className="text-sm font-semibold text-slate-700">{expiryModal.filename}</p>
              <p className="text-xs text-slate-500 capitalize">{expiryModal.document_type?.replace('_', ' ')}</p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1">Expiry Date</label>
                <Input
                  type="date"
                  value={expiryDate}
                  onChange={e => setExpiryDate(e.target.value)}
                  data-testid="expiry-date-input"
                />
                {expiryModal.suggested_validity_days && !expiryDate && (
                  <button
                    className="text-xs text-[#2a777a] hover:underline mt-1"
                    onClick={() => {
                      const d = new Date();
                      d.setDate(d.getDate() + expiryModal.suggested_validity_days);
                      setExpiryDate(d.toISOString().split('T')[0]);
                    }}
                    data-testid="auto-suggest-expiry"
                  >
                    Auto-set: {expiryModal.suggested_validity_days >= 365 
                      ? `${Math.floor(expiryModal.suggested_validity_days/365)} year(s) from today`
                      : `${expiryModal.suggested_validity_days} days from today`}
                  </button>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1">Notes (optional)</label>
                <Input
                  value={expiryNotes}
                  onChange={e => setExpiryNotes(e.target.value)}
                  placeholder="e.g. IELTS score valid till..."
                  data-testid="expiry-notes-input"
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => setExpiryModal(null)}>Cancel</Button>
              <Button className="flex-1 bg-[#2a777a] hover:bg-[#236466]" onClick={handleSetExpiry} disabled={!expiryDate} data-testid="save-expiry-btn">
                Save Expiry Date
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Onboarding Wizard */}
      {showOnboarding && caseData && (
        <OnboardingWizard
          user={user}
          caseData={caseData}
          onComplete={() => setShowOnboarding(false)}
          onNavigate={(tab) => { setShowOnboarding(false); setActiveTab(tab); }}
        />
      )}

      {/* Chat Widget */}
      <ChatWidget currentUser={user} />
    </DashboardShell>
  );
};

export default ClientDashboard;
