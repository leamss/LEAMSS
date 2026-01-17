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
import { 
  User, FileText, Upload, LogOut, CheckCircle, Clock, AlertCircle, 
  Lock, Download, FileCheck, ArrowLeft, Calendar, Shield, 
  FolderOpen, AlertTriangle, FileUp, Eye, ChevronRight, MessageSquare
} from 'lucide-react';

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
  const [highlightedDocId, setHighlightedDocId] = useState(null);

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
        setCaseData(casesRes.data[0]);
        const docsResponse = await axios.get(`${API}/documents/case/${casesRes.data[0].id}`, getAuthHeader());
        setDocuments(docsResponse.data);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
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
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-lg">L</span>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-[#2a777a] to-[#236466] bg-clip-text text-transparent">
                  LEAMSS Portal
                </h1>
                <p className="text-xs text-slate-500">Client Dashboard</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <NotificationBell onNotificationClick={handleNotificationClick} />
              <CreateTicket caseId={caseData?.id} />
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full">
                <User className="h-4 w-4 text-[#2a777a]" />
                <span className="text-sm font-medium text-slate-700">{user.name}</span>
              </div>
              <Button variant="ghost" onClick={handleLogout} className="text-slate-600 hover:text-red-600">
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
                                      onClick={() => downloadDocument(doc.file_id, doc.filename)}
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
                <Card className="p-6 bg-white shadow-md border-0">
                  <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <FolderOpen className="h-5 w-5 text-[#2a777a]" />
                    All Uploaded Documents
                    <Badge className="bg-[#2a777a]/10 text-[#2a777a] ml-2">{documents.length}</Badge>
                  </h3>

                  {documents.length === 0 ? (
                    <div className="text-center py-12 bg-slate-50 rounded-xl">
                      <FolderOpen className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                      <p className="text-slate-600 font-medium">No documents uploaded yet</p>
                      <p className="text-sm text-slate-500">Upload documents from the Workflow Steps tab</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200">
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Document</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Step</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Type</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Uploaded</th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Status</th>
                            <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documents.map((doc) => (
                            <tr key={doc.id} className="border-b border-slate-100 hover:bg-slate-50">
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  <FileText className="h-4 w-4 text-[#2a777a]" />
                                  <span className="font-medium text-slate-800">{doc.filename}</span>
                                </div>
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600">{doc.step_name}</td>
                              <td className="py-3 px-4 text-sm text-slate-600 capitalize">{doc.document_type}</td>
                              <td className="py-3 px-4 text-sm text-slate-600">
                                {new Date(doc.upload_date).toLocaleDateString()}
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
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => downloadDocument(doc.file_id, doc.filename)}
                                >
                                  <Download className="h-4 w-4 mr-1" />
                                  Download
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </TabsContent>

              {/* Support Tickets Tab */}
              <TabsContent value="tickets" className="space-y-6">
                <TicketSection caseId={caseData?.id} initialTicketId={initialTicketId} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
    </div>
  );
};

export default ClientDashboard;
