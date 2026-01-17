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
import { Briefcase, FileText, CheckCircle, AlertCircle, LogOut, Download, Plus, Send, ArrowLeft } from 'lucide-react';

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
    <div className="flex flex-col min-h-screen bg-slate-50">
      <AdminReturnBanner />
      <div className="flex flex-1">
      <aside className="w-64 bg-slate-800 text-white p-6 flex flex-col" data-testid="case-manager-sidebar">
        <div className="flex items-center gap-2 mb-8">
          <Briefcase className="h-8 w-8 text-[#f7620b]" />
          <h1 className="text-xl font-bold">Case Manager</h1>
        </div>
        
        <nav className="flex-1 space-y-2">
          <button
            onClick={() => { setActiveTab('dashboard'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'dashboard' ? 'bg-[#2a777a]' : 'hover:bg-slate-700'
            }`}
            data-testid="nav-dashboard"
          >
            <Briefcase className="h-5 w-5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => { setActiveTab('cases'); setSelectedCase(null); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'cases' ? 'bg-[#2a777a]' : 'hover:bg-slate-700'
            }`}
            data-testid="nav-cases"
          >
            <FileText className="h-5 w-5" />
            <span>My Cases</span>
          </button>
        </nav>
        
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-white hover:bg-slate-700 mt-4"
          data-testid="logout-button"
        >
          <LogOut className="mr-2 h-5 w-5" />
          Logout
        </Button>
      </aside>

      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'cases' && !selectedCase && 'My Cases'}
              {selectedCase && `Case: ${selectedCase.case_id}`}
            </h2>
            <div className="flex items-center gap-3">
              {selectedCase && <CreateTicket caseId={selectedCase.id} />}
              <NotificationBell />
            </div>
          </div>

          {activeTab === 'dashboard' && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8" data-testid="case-manager-stats">
                <Card className="p-6 border-l-4 border-l-[#2a777a]">
                  <p className="text-sm text-slate-600 font-medium">My Cases</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stats.my_cases || 0}</p>
                </Card>
                <Card className="p-6 border-l-4 border-l-[#f7620b]">
                  <p className="text-sm text-slate-600 font-medium">Pending Documents</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stats.pending_documents || 0}</p>
                </Card>
              </div>
              
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Recent Cases</h3>
                <div className="space-y-3">
                  {cases.slice(0, 5).map((caseItem) => (
                    <div
                      key={caseItem.id}
                      className="flex justify-between items-center p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors"
                      onClick={() => {
                        setActiveTab('cases');
                        loadCaseDetails(caseItem.id);
                      }}
                    >
                      <div>
                        <p className="font-medium text-gray-900">{caseItem.client_name}</p>
                        <p className="text-sm text-slate-600">{caseItem.product_name}</p>
                      </div>
                      {getStatusBadge('in_progress')}
                    </div>
                  ))}
                </div>
              </Card>
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
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Workflow Steps</h3>
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
                          <div>
                            <p className="font-medium text-gray-900">{req.document_name}</p>
                            <p className="text-sm text-slate-600">{req.description}</p>
                            <p className="text-xs text-slate-500 mt-1">Requested: {new Date(req.requested_at).toLocaleDateString()}</p>
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
    </div>
  );
};

export default CaseManagerDashboard;
