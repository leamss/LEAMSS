import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import NotificationBell from '@/components/NotificationBell';
import CreateTicket from '@/components/CreateTicket';
import TicketSection from '@/components/TicketSection';
import QuickActions from '@/components/QuickActions';
import { 
  User, FileText, Upload, LogOut, CheckCircle, Clock, AlertCircle, 
  Lock, Download, FileCheck, ArrowLeft, Calendar, Shield, 
  FolderOpen, AlertTriangle, FileUp, Eye, ChevronRight, MessageSquare,
  CreditCard, Loader2, IndianRupee, ExternalLink, TrendingUp, Brain, FileSearch
} from 'lucide-react';
import AIChatWidget from '@/components/AIChatWidget';

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

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
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
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }

    // Load proposals/payments independently
    try {
      const proposalsRes = await axios.get(`${API}/payments/my-proposals`, getAuthHeader());
      setProposals(proposalsRes.data || []);
    } catch (e) { /* no proposals */ }
  };

  useEffect(() => {
    if (user) {
      loadData();
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <AdminReturnBanner />
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14 md:h-16">
            <div className="flex items-center gap-2 md:gap-3">
              <img src="/leamss-logo.png" alt="LEAMSS" className="w-8 h-8 md:w-10 md:h-10 rounded-xl object-contain shadow-lg" />
              <div>
                <h1 className="text-base md:text-xl font-bold bg-gradient-to-r from-[#2a777a] to-[#236466] bg-clip-text text-transparent">
                  LEAMSS Portal
                </h1>
                <p className="text-xs text-slate-500 hidden sm:block">Client Dashboard</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2 md:gap-4">
              <NotificationBell onNotificationClick={handleNotificationClick} />
              <div className="hidden sm:block">
                <CreateTicket caseId={caseData?.id} onTicketCreated={() => setActiveTab('tickets')} />
              </div>
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full">
                <User className="h-4 w-4 text-[#2a777a]" />
                <span className="text-sm font-medium text-slate-700">{user.name}</span>
              </div>
              <Button variant="ghost" onClick={handleLogout} className="text-slate-600 hover:text-red-600" size="sm">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!caseData ? (
          <Card className="p-12 text-center bg-white shadow-xl rounded-2xl border-0">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-slate-100 to-slate-200 rounded-full flex items-center justify-center">
              <FileText className="h-10 w-10 text-slate-400" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">No Active Case</h2>
            <p className="text-slate-500 max-w-md mx-auto">
              You don&apos;t have any active cases yet. Please contact your case manager or partner for assistance.
            </p>
          </Card>
        ) : (
          <>
            {/* Case Overview Header */}
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

            {/* Main Content Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="bg-white shadow-md rounded-xl p-1 border-0">
                <TabsTrigger value="overview" className="data-[state=active]:bg-[#2a777a] data-[state=active]:text-white rounded-lg px-6">
                  <Eye className="h-4 w-4 mr-2" />
                  Overview
                </TabsTrigger>
                <TabsTrigger value="additional" className="data-[state=active]:bg-[#f7620b] data-[state=active]:text-white rounded-lg px-6 relative">
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Action Required
                  {pendingAdditionalDocs.length > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                      {pendingAdditionalDocs.length}
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="workflow" className="data-[state=active]:bg-[#2a777a] data-[state=active]:text-white rounded-lg px-6">
                  <FileText className="h-4 w-4 mr-2" />
                  Workflow Steps
                </TabsTrigger>
                <TabsTrigger value="uploaded" className="data-[state=active]:bg-[#2a777a] data-[state=active]:text-white rounded-lg px-6">
                  <FileCheck className="h-4 w-4 mr-2" />
                  My Documents
                </TabsTrigger>
                <TabsTrigger value="tickets" className="data-[state=active]:bg-[#2a777a] data-[state=active]:text-white rounded-lg px-6">
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Support
                </TabsTrigger>
                <TabsTrigger value="info-sheet" className="data-[state=active]:bg-[#2a777a] data-[state=active]:text-white rounded-lg px-6">
                  <User className="h-4 w-4 mr-2" />
                  My Info
                </TabsTrigger>
                <TabsTrigger value="payments" className="data-[state=active]:bg-[#f7620b] data-[state=active]:text-white rounded-lg px-6 relative" data-testid="payments-tab">
                  <CreditCard className="h-4 w-4 mr-2" />
                  Payments
                  {proposals.filter(p => p.status === 'approved' && (p.pending_amount || 0) > 0).length > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                      {proposals.filter(p => p.status === 'approved' && (p.pending_amount || 0) > 0).length}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-6">
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
                          onClick={() => setActiveTab('additional')} 
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
              </TabsContent>

              {/* Additional Documents Tab */}
              <TabsContent value="additional" className="space-y-6">
                {/* Pending Additional Document Requests */}
                <Card className="p-6 bg-white shadow-md border-0">
                  <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-[#f7620b]" />
                    Pending Document Requests
                    {pendingAdditionalDocs.length > 0 && (
                      <Badge className="bg-[#f7620b] text-white ml-2">{pendingAdditionalDocs.length}</Badge>
                    )}
                  </h3>
                  
                  {pendingAdditionalDocs.length === 0 ? (
                    <div className="text-center py-12 bg-slate-50 rounded-xl">
                      <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                      <p className="text-slate-600 font-medium">No pending document requests!</p>
                      <p className="text-sm text-slate-500">All requested documents have been uploaded.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {pendingAdditionalDocs.map((request, index) => (
                        <div key={request.id} className="bg-gradient-to-br from-[#f7620b]/5 to-white rounded-xl border border-[#f7620b]/20 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                          <div className="bg-gradient-to-r from-[#f7620b] to-[#e55a09] px-4 py-3">
                            <div className="flex items-center justify-between">
                              <h4 className="font-semibold text-white">{request.doc_name || request.document_name}</h4>
                              <Badge className="bg-white/20 text-white border-0 text-xs">Required</Badge>
                            </div>
                          </div>
                          <div className="p-4">
                            <p className="text-sm text-slate-600 mb-4">{request.description}</p>
                            
                            <div className="flex flex-wrap gap-2 mb-4">
                              {request.step_name && (
                                <Badge variant="outline" className="bg-slate-50 text-slate-600 text-xs">
                                  <FileText className="h-3 w-3 mr-1" />
                                  {request.step_name}
                                </Badge>
                              )}
                              {request.doc_type && (
                                <Badge variant="outline" className="bg-blue-50 text-blue-600 text-xs capitalize">
                                  {request.doc_type}
                                </Badge>
                              )}
                              {request.due_date && (
                                <Badge variant="outline" className="bg-amber-50 text-amber-600 text-xs">
                                  <Calendar className="h-3 w-3 mr-1" />
                                  Due: {new Date(request.due_date).toLocaleDateString()}
                                </Badge>
                              )}
                              {request.expiry_date && (
                                <Badge variant="outline" className="bg-red-50 text-red-600 text-xs">
                                  Expires: {new Date(request.expiry_date).toLocaleDateString()}
                                </Badge>
                              )}
                              {request.validity_months && (
                                <Badge variant="outline" className="bg-purple-50 text-purple-600 text-xs">
                                  Valid: {request.validity_months} months
                                </Badge>
                              )}
                            </div>

                            <p className="text-xs text-slate-500 mb-3">
                              Requested by {request.requested_by_name} on {new Date(request.requested_at).toLocaleDateString()}
                            </p>

                            <div className="flex gap-2">
                              <Input
                                type="file"
                                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                                onChange={(e) => {
                                  setSelectedFile(e.target.files[0]);
                                  setUploadingFor(request.id);
                                }}
                                className="flex-1 text-sm"
                                data-testid={`additional-file-input-${index}`}
                              />
                              <Button
                                onClick={() => handleFileUpload(
                                  request.doc_name || request.document_name, 
                                  true, 
                                  request.id, 
                                  request.step_name
                                )}
                                disabled={!selectedFile || uploadingFor !== request.id}
                                className="bg-[#f7620b] hover:bg-[#e55a09] whitespace-nowrap"
                                data-testid={`additional-upload-btn-${index}`}
                              >
                                <Upload className="h-4 w-4 mr-1" />
                                Upload
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Uploaded Additional Documents */}
                {uploadedAdditionalDocs.length > 0 && (
                  <Card className="p-6 bg-white shadow-md border-0">
                    <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                      <FileCheck className="h-5 w-5 text-green-500" />
                      Submitted Additional Documents
                      <Badge className="bg-green-100 text-green-700 ml-2">{uploadedAdditionalDocs.length}</Badge>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {uploadedAdditionalDocs.map((request) => (
                        <div key={request.id} className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200">
                          <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                            <FileCheck className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{request.doc_name || request.document_name}</p>
                            <p className="text-xs text-slate-500">Uploaded {new Date(request.uploaded_at || request.requested_at).toLocaleDateString()}</p>
                          </div>
                          <Badge className="bg-green-100 text-green-700 flex-shrink-0">Submitted</Badge>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </TabsContent>

              {/* Workflow Steps Tab */}
              <TabsContent value="workflow" className="space-y-6">
                {caseData.steps?.map((step, stepIndex) => (
                  <Card key={stepIndex} className={`p-6 bg-white shadow-md border-0 ${step.is_locked ? 'opacity-60' : ''}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          step.status === 'completed' ? 'bg-gradient-to-br from-green-500 to-green-600' :
                          step.is_locked ? 'bg-gradient-to-br from-slate-300 to-slate-400' :
                          'bg-gradient-to-br from-[#2a777a] to-[#236466]'
                        }`}>
                          {step.status === 'completed' ? <CheckCircle className="h-6 w-6 text-white" /> :
                           step.is_locked ? <Lock className="h-6 w-6 text-white" /> :
                           <span className="text-white font-bold">{step.step_order}</span>}
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-slate-800">{step.step_name}</h3>
                          {step.description && <p className="text-sm text-slate-500">{step.description}</p>}
                        </div>
                      </div>
                      <Badge className={`${
                        step.status === 'completed' ? 'bg-green-100 text-green-700' :
                        step.is_locked ? 'bg-slate-100 text-slate-600' :
                        'bg-[#2a777a]/10 text-[#2a777a]'
                      }`}>
                        {step.status === 'completed' ? 'Completed' : step.is_locked ? 'Locked' : 'In Progress'}
                      </Badge>
                    </div>

                    {step.is_locked ? (
                      <div className="text-center py-8 bg-slate-50 rounded-xl">
                        <Lock className="h-8 w-8 text-slate-400 mx-auto mb-2" />
                        <p className="text-slate-500">Complete previous steps to unlock</p>
                      </div>
                    ) : (
                      <>
                        {/* Required Documents for this step */}
                        {step.required_documents?.length > 0 && (
                          <div className="mb-4">
                            <h4 className="font-medium text-slate-700 mb-3">Required Documents</h4>
                            <div className="space-y-3">
                              {step.required_documents.map((doc, docIndex) => {
                                const uploadedDoc = documents.find(d => 
                                  d.step_name === step.step_name && 
                                  (d.document_type === doc.doc_name || d.document_type === 'workflow')
                                );
                                return (
                                  <div key={docIndex} className={`p-4 rounded-xl border ${
                                    uploadedDoc ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
                                  }`}>
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3">
                                        {uploadedDoc ? 
                                          <FileCheck className="h-5 w-5 text-green-600" /> :
                                          <FileUp className="h-5 w-5 text-amber-600" />
                                        }
                                        <div>
                                          <p className="font-medium text-slate-800">{doc.doc_name}</p>
                                          {doc.description && <p className="text-xs text-slate-500">{doc.description}</p>}
                                        </div>
                                      </div>
                                      {uploadedDoc ? (
                                        <Badge className="bg-green-100 text-green-700">Uploaded</Badge>
                                      ) : (
                                        <Badge className="bg-amber-100 text-amber-700">Pending</Badge>
                                      )}
                                    </div>
                                    {!uploadedDoc && (
                                      <div className="flex gap-2 mt-3">
                                        <Input
                                          type="file"
                                          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                                          onChange={(e) => {
                                            setSelectedFile(e.target.files[0]);
                                            setUploadingFor(`${step.step_name}-${doc.doc_name}`);
                                          }}
                                          className="flex-1 text-sm"
                                        />
                                        <Button
                                          onClick={() => handleFileUpload(step.step_name, false, null, step.step_name)}
                                          disabled={!selectedFile || uploadingFor !== `${step.step_name}-${doc.doc_name}`}
                                          className="bg-[#2a777a] hover:bg-[#236466]"
                                        >
                                          <Upload className="h-4 w-4 mr-1" />
                                          Upload
                                        </Button>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Documents uploaded for this step */}
                        {getDocumentsByStep(step.step_name).length > 0 && (
                          <div>
                            <h4 className="font-medium text-slate-700 mb-3">Uploaded Documents</h4>
                            <div className="space-y-2">
                              {getDocumentsByStep(step.step_name).map((doc) => (
                                <div key={doc.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                  <div className="flex items-center gap-3">
                                    <FileText className="h-4 w-4 text-slate-500" />
                                    <span className="text-sm font-medium text-slate-700">{doc.filename}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Badge className={`text-xs ${
                                      doc.status === 'approved' ? 'bg-green-100 text-green-700' :
                                      doc.status === 'rejected' ? 'bg-red-100 text-red-700' :
                                      'bg-amber-100 text-amber-700'
                                    }`}>
                                      {doc.status === 'pending_review' ? 'Under Review' : doc.status}
                                    </Badge>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => downloadDocument(doc.id, doc.filename)}
                                      data-testid={`download-doc-${doc.id}`}
                                    >
                                      <Download className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </Card>
                ))}
              </TabsContent>

              {/* My Documents Tab */}
              <TabsContent value="uploaded" className="space-y-6">
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
              </TabsContent>

              {/* Support Tickets Tab */}
              <TabsContent value="tickets" className="space-y-6">
                <TicketSection caseId={caseData?.id} initialTicketId={initialTicketId} initialFilter={ticketFilter} />
              </TabsContent>

              {/* Information Sheet Tab */}
              <TabsContent value="info-sheet" className="space-y-6">
                <Card className="p-6 bg-white shadow-md border-0" data-testid="info-sheet-card">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                      <User className="h-5 w-5 text-[#2a777a]" />
                      My Information Sheet
                    </h3>
                    {/* Resume upload & auto-fill */}
                    {caseData && (
                      <div className="flex items-center gap-2">
                        <label className="cursor-pointer">
                          <input type="file" className="hidden" accept=".pdf,.doc,.docx,.txt" onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            setExtractingResume(true);
                            try {
                              // First upload the document
                              const formData = new FormData();
                              formData.append('file', file);
                              formData.append('case_id', caseData.id);
                              formData.append('document_type', 'resume');
                              const uploadRes = await axios.post(`${API}/documents/upload`, formData, {
                                headers: { Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'multipart/form-data' }
                              });
                              const docId = uploadRes.data?.id || uploadRes.data?.document_id;
                              if (docId) {
                                // Then extract and auto-fill
                                const extractRes = await axios.post(
                                  `${API}/ai-intel/extract-resume-to-infosheet/${caseData.id}?document_id=${docId}`,
                                  {}, getAuthHeader()
                                );
                                toast.success(extractRes.data.message || `Extracted ${extractRes.data.fields_filled} fields!`);
                                loadData();
                              } else {
                                toast.success('Document uploaded! Use AI extract to auto-fill.');
                              }
                            } catch (err) {
                              toast.error(err.response?.data?.detail || 'Failed to extract. Try a clearer document.');
                            } finally {
                              setExtractingResume(false);
                              e.target.value = '';
                            }
                          }} />
                          <Button variant="outline" size="sm" className="text-[#2a777a] border-[#2a777a]" disabled={extractingResume} asChild>
                            <span data-testid="upload-resume-btn">
                              {extractingResume ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
                              {extractingResume ? 'Extracting...' : 'Upload Resume & Auto-Fill'}
                            </span>
                          </Button>
                        </label>
                      </div>
                    )}
                  </div>

                  {/* Completion bar */}
                  {infoSheetCompletion.total_fields > 0 && (
                    <div className="mb-4 p-3 rounded-lg bg-slate-50 border">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-600">Information Completion</span>
                        <span className={`font-semibold ${infoSheetCompletion.percentage === 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {infoSheetCompletion.percentage}% ({infoSheetCompletion.filled_count}/{infoSheetCompletion.total_fields} fields)
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2">
                        <div className={`h-2 rounded-full transition-all ${infoSheetCompletion.percentage === 100 ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${infoSheetCompletion.percentage}%` }} />
                      </div>
                      {infoSheetCompletion.missing_fields?.length > 0 && (
                        <p className="text-xs text-red-500 mt-1">Missing: {infoSheetCompletion.missing_fields.map(f => f.replace(/_/g, ' ')).join(', ')}</p>
                      )}
                    </div>
                  )}

                  {infoSheet ? (
                    <div>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {(infoSheetRequiredFields.length > 0 ? infoSheetRequiredFields : Object.keys(infoSheet)).filter(key =>
                          !['id', 'case_id', 'client_id', 'created_at', 'updated_at', '_id', 'required_fields', 'status', 'auto_filled_at', 'auto_filled_by', 'auto_filled_from', 'auto_filled_data'].includes(key)
                        ).map((key) => {
                          const value = infoSheet[key];
                          const isMissing = !value || String(value).trim() === '' || String(value) === 'null';
                          const isRequired = infoSheetRequiredFields.includes(key);
                          return (
                            <div key={key} className={`p-4 rounded-xl border shadow-sm transition-shadow ${
                              isMissing && isRequired ? 'bg-red-50/50 border-red-200 ring-1 ring-red-100' : 'bg-gradient-to-br from-slate-50 to-white border-slate-100 hover:shadow-md'
                            }`}>
                              <p className="text-xs font-semibold uppercase tracking-wide mb-1 flex items-center gap-1">
                                <span className="text-[#2a777a]">{key.replace(/_/g, ' ')}</span>
                                {isRequired && <span className="text-red-500">*</span>}
                              </p>
                              {isMissing ? (
                                <p className="text-sm text-red-400 italic font-medium">Required — please fill</p>
                              ) : (
                                <p className="font-medium text-slate-800 text-sm">{String(value)}</p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      {infoSheet.updated_at && (
                        <p className="text-xs text-slate-400 text-right mt-4">
                          Last updated: {new Date(infoSheet.updated_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-16 bg-gradient-to-br from-slate-50 to-white rounded-xl border border-dashed border-slate-200">
                      <User className="h-14 w-14 text-slate-300 mx-auto mb-4" />
                      <p className="text-slate-600 font-semibold text-lg">No information sheet submitted yet</p>
                      <p className="text-sm text-slate-500 mt-2 max-w-sm mx-auto">Your case manager will request you to fill this out. You can upload a resume to auto-fill.</p>
                    </div>
                  )}
                </Card>
              </TabsContent>

              {/* Payments Tab */}
              <TabsContent value="payments" className="space-y-6">
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
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
      {/* AI Chat Widget - floating */}
      <AIChatWidget />

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
    </div>
  );
};

export default ClientDashboard;
