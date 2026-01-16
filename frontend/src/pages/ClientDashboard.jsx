import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import NotificationBell from '@/components/NotificationBell';
import CreateTicket from '@/components/CreateTicket';
import { User, FileText, Upload, LogOut, CheckCircle, Clock, AlertCircle, Lock, Download, FileCheck } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [caseData, setCaseData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [additionalDocRequests, setAdditionalDocRequests] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData || userData.role !== 'client') {
      navigate('/');
      return;
    }
    setUser(userData);
    loadData();
  }, [navigate]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadData = async () => {
    try {
      const [statsRes, casesRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, getAuthHeader()),
        axios.get(`${API}/cases/my-cases`, getAuthHeader())
      ]);
      setStats(statsRes.data);
      
      if (casesRes.data.length > 0) {
        const myCase = casesRes.data[0];
        setCaseData(myCase);
        setAdditionalDocRequests(myCase.additional_doc_requests || []);
        const docsRes = await axios.get(`${API}/documents/case/${myCase.id}`, getAuthHeader());
        setDocuments(docsRes.data);
      }
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleFileUpload = async (stepName, isAdditional = false, requestId = null) => {
    if (!selectedFile) {
      toast.error('Please select a file');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('case_id', caseData.id);
      formData.append('step_name', stepName);
      formData.append('document_type', isAdditional ? 'additional' : 'workflow');
      
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

  const getStepIcon = (step) => {
    if (step.status === 'completed') return <CheckCircle className="h-5 w-5 text-emerald-600" />;
    if (step.status === 'in_progress' && !step.is_locked) return <Clock className="h-5 w-5 text-blue-600" />;
    if (step.is_locked) return <Lock className="h-5 w-5 text-slate-400" />;
    return <AlertCircle className="h-5 w-5 text-amber-600" />;
  };

  const getProgressPercentage = () => {
    if (!caseData || !caseData.steps) return 0;
    const completed = caseData.steps.filter(s => s.status === 'completed').length;
    return (completed / caseData.steps.length) * 100;
  };

  const getDocumentStatusBadge = (status) => {
    const badges = {
      pending_review: <Badge variant=\"outline\" className=\"bg-amber-50 text-amber-700 border-amber-200\">Pending Review</Badge>,
      approved: <Badge variant=\"outline\" className=\"bg-emerald-50 text-emerald-700 border-emerald-200\">Approved</Badge>,
      rejected: <Badge variant=\"outline\" className=\"bg-red-50 text-red-700 border-red-200\">Rejected</Badge>,
      revision_required: <Badge variant=\"outline\" className=\"bg-blue-50 text-blue-700 border-blue-200\">Revision Required</Badge>
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  const getCurrentStep = () => {
    if (!caseData || !caseData.steps) return null;
    return caseData.steps.find(s => s.status === 'in_progress' && !s.is_locked);
  };

  const currentStep = getCurrentStep();

  return (
    <div className=\"min-h-screen bg-slate-50\">
      <header className=\"bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm\">
        <div className=\"max-w-7xl mx-auto px-6 py-4 flex justify-between items-center\">
          <div className=\"flex items-center gap-3\">
            <div className=\"h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center\">
              <User className=\"h-5 w-5 text-emerald-600\" />
            </div>
            <div>
              <h1 className=\"text-lg font-semibold text-gray-900\">Client Portal</h1>
              <p className=\"text-xs text-gray-500\">{user?.name}</p>
            </div>
          </div>
          <div className=\"flex items-center gap-3\">
            <CreateTicket caseId={caseData?.id} />
            <NotificationBell />
            <Button
              onClick={handleLogout}
              variant=\"ghost\"
              size=\"sm\"
              className=\"text-gray-600\"
              data-testid=\"logout-button\"
            >
              <LogOut className=\"mr-2 h-4 w-4\" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className=\"max-w-6xl mx-auto p-6 md:p-8\">
        {!caseData ? (
          <Card className=\"p-12 text-center\">
            <FileText className=\"h-16 w-16 text-slate-400 mx-auto mb-4\" />
            <h2 className=\"text-2xl font-semibold mb-2\">No Active Case</h2>
            <p className=\"text-slate-600\">Your case is being set up. You'll receive an email when it's ready.</p>
          </Card>
        ) : (
          <div className=\"space-y-6\">
            {/* Case Overview Card */}
            <Card className=\"p-6 bg-gradient-to-r from-emerald-500 to-teal-600 text-white\" data-testid=\"case-overview\">
              <div className=\"flex justify-between items-start mb-4\">
                <div>
                  <h2 className=\"text-2xl font-bold mb-1\">{caseData.case_id}</h2>
                  <p className=\"text-emerald-100\">{caseData.product_name}</p>
                </div>
                <Badge className=\"bg-white/20 text-white border-white/30\">
                  {caseData.status}
                </Badge>
              </div>
              <div className=\"space-y-2\">
                <div className=\"flex justify-between text-sm\">
                  <span>Overall Progress</span>
                  <span className=\"font-semibold\">{getProgressPercentage().toFixed(0)}%</span>
                </div>
                <Progress value={getProgressPercentage()} className=\"h-2 bg-white/20\" />
              </div>
            </Card>

            {/* Stats Cards */}
            <div className=\"grid grid-cols-1 md:grid-cols-3 gap-4\">
              <Card className=\"p-4 border-l-4 border-l-emerald-500\">
                <p className=\"text-sm text-slate-600 mb-1\">Current Step</p>
                <p className=\"text-lg font-semibold text-gray-900\">{caseData.current_step}</p>
              </Card>
              <Card className=\"p-4 border-l-4 border-l-blue-500\">
                <p className=\"text-sm text-slate-600 mb-1\">Completed Steps</p>
                <p className=\"text-lg font-semibold text-blue-600\">{stats.completed_steps || 0}</p>
              </Card>
              <Card className=\"p-4 border-l-4 border-l-amber-500\">
                <p className=\"text-sm text-slate-600 mb-1\">Pending Actions</p>
                <p className=\"text-lg font-semibold text-amber-600\">{stats.pending_doc_requests || 0}</p>
              </Card>
            </div>

            {/* Case Manager Info */}
            <Card className=\"p-6\">
              <h3 className=\"text-lg font-semibold mb-4 text-gray-900\">Your Case Manager</h3>
              <div className=\"flex items-center gap-3\">
                <div className=\"h-12 w-12 bg-emerald-100 rounded-full flex items-center justify-center\">
                  <User className=\"h-6 w-6 text-emerald-600\" />
                </div>
                <div>
                  <p className=\"font-medium text-gray-900\">{caseData.case_manager_name}</p>
                  <p className=\"text-sm text-slate-600\">Managing your application process</p>
                </div>
              </div>
            </Card>

            {/* Current Active Step Upload */}
            {currentStep && (
              <Card className=\"p-6 border-2 border-emerald-500\">
                <div className=\"flex items-center gap-3 mb-4\">
                  <div className=\"h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center\">
                    <Upload className=\"h-5 w-5 text-emerald-600\" />
                  </div>
                  <div>
                    <h3 className=\"text-lg font-semibold text-gray-900\">Current Step: {currentStep.step_name}</h3>
                    <p className=\"text-sm text-slate-600\">Upload required documents to proceed</p>
                  </div>
                </div>

                {currentStep.required_documents && currentStep.required_documents.length > 0 && (
                  <div className=\"mb-4 p-4 bg-blue-50 rounded-lg\">
                    <h4 className=\"font-medium text-sm mb-2 text-gray-900\">Required Documents:</h4>
                    <ul className=\"space-y-2\">
                      {currentStep.required_documents.map((doc, idx) => (
                        <li key={idx} className=\"flex items-start gap-2 text-sm\">
                          <FileCheck className=\"h-4 w-4 text-blue-600 mt-0.5\" />
                          <div>
                            <p className=\"font-medium text-gray-900\">{doc.doc_name} {doc.is_mandatory && <span className=\"text-red-500\">*</span>}</p>
                            <p className=\"text-xs text-slate-600\">{doc.description}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className=\"space-y-3\">
                  <Input
                    type=\"file\"
                    accept=\".pdf,.jpg,.jpeg,.png\"
                    onChange={(e) => setSelectedFile(e.target.files[0])}
                    data-testid=\"file-input\"
                  />
                  <Button
                    onClick={() => handleFileUpload(currentStep.step_name)}
                    disabled={!selectedFile}
                    className=\"w-full bg-emerald-600 hover:bg-emerald-700\"
                    data-testid=\"upload-button\"
                  >
                    <Upload className=\"mr-2 h-4 w-4\" />
                    Upload Document
                  </Button>
                </div>
              </Card>
            )}

            {/* Additional Document Requests */}
            {additionalDocRequests.length > 0 && additionalDocRequests.some(r => r.status === 'pending') && (
              <Card className=\"p-6 border-2 border-amber-500\">
                <h3 className=\"text-lg font-semibold mb-4 text-gray-900\">Additional Documents Requested</h3>
                <div className=\"space-y-4\">
                  {additionalDocRequests.filter(r => r.status === 'pending').map((request) => (
                    <div key={request.id} className=\"p-4 bg-amber-50 rounded-lg\">
                      <div className=\"flex justify-between items-start mb-2\">
                        <div>
                          <p className=\"font-medium text-gray-900\">{request.document_name}</p>
                          <p className=\"text-sm text-slate-600\">{request.description}</p>
                          <p className=\"text-xs text-slate-500 mt-1\">Requested by: {request.requested_by_name}</p>
                        </div>
                        <Badge variant=\"outline\" className=\"bg-amber-100 text-amber-700 border-amber-300\">
                          Required
                        </Badge>
                      </div>
                      <div className=\"flex gap-2 mt-3\">
                        <Input
                          type=\"file\"
                          accept=\".pdf,.jpg,.jpeg,.png\"
                          onChange={(e) => setSelectedFile(e.target.files[0])}
                          className=\"flex-1\"
                        />
                        <Button
                          onClick={() => handleFileUpload(request.document_name, true, request.id)}
                          disabled={!selectedFile}
                          size=\"sm\"
                          className=\"bg-amber-600 hover:bg-amber-700\"
                        >
                          Upload
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Workflow Checklist */}
            <Card className=\"p-6\">
              <h3 className=\"text-lg font-semibold mb-4 text-gray-900\">Workflow Progress</h3>
              <div className=\"space-y-3\" data-testid=\"workflow-checklist\">
                {caseData.steps && caseData.steps.map((step, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-3 p-4 rounded-lg border-2 transition-all ${
                      step.status === 'completed' ? 'bg-emerald-50 border-emerald-200' :
                      step.status === 'in_progress' && !step.is_locked ? 'bg-blue-50 border-blue-300 shadow-sm' :
                      step.is_locked ? 'bg-slate-50 border-slate-200 opacity-60' :
                      'bg-white border-slate-200'
                    }`}
                  >
                    {getStepIcon(step)}
                    <div className=\"flex-1\">
                      <div className=\"flex justify-between items-start mb-1\">
                        <div>
                          <div className=\"flex items-center gap-2\">
                            <p className=\"font-semibold text-gray-900\">{step.step_order}. {step.step_name}</p>
                            {step.is_locked && <Lock className=\"h-4 w-4 text-slate-400\" />}
                          </div>
                          {step.notes && <p className=\"text-sm text-slate-600 mt-1\">{step.notes}</p>}
                        </div>
                        <Badge variant={step.status === 'completed' ? 'default' : 'outline'}>
                          {step.status === 'in_progress' && !step.is_locked ? 'Active' : step.status}
                        </Badge>
                      </div>
                      {step.is_locked && step.status !== 'completed' && (
                        <p className=\"text-xs text-slate-500 italic\">Complete previous steps to unlock</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* My Documents */}
            <Card className=\"p-6\">
              <h3 className=\"text-lg font-semibold mb-4 text-gray-900\">My Documents</h3>
              <div className=\"space-y-3\" data-testid=\"documents-list\">
                {documents.map((doc) => (
                  <div key={doc.id} className=\"flex justify-between items-start p-4 border rounded-lg hover:bg-slate-50\">
                    <div className=\"flex-1\">
                      <div className=\"flex items-center gap-2 mb-1\">
                        <FileText className=\"h-4 w-4 text-slate-400\" />
                        <p className=\"font-medium text-gray-900\">{doc.filename}</p>
                      </div>
                      <p className=\"text-sm text-slate-600\">Step: {doc.step_name}</p>
                      <p className=\"text-sm text-slate-500\">Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</p>
                      {doc.review_comment && (
                        <div className=\"mt-2 p-2 bg-blue-50 rounded text-sm\">
                          <p className=\"font-medium text-gray-900\">Case Manager's Comment:</p>
                          <p className=\"text-slate-700\">{doc.review_comment}</p>
                        </div>
                      )}
                    </div>
                    <div className=\"flex flex-col items-end gap-2\">
                      {getDocumentStatusBadge(doc.status)}
                      <Button
                        onClick={() => downloadDocument(doc.id, doc.filename)}
                        size=\"sm\"
                        variant=\"outline\"
                      >
                        <Download className=\"h-4 w-4\" />
                      </Button>
                    </div>
                  </div>
                ))}
                {documents.length === 0 && (
                  <p className=\"text-center text-slate-500 py-8\">No documents uploaded yet</p>
                )}
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
};

export default ClientDashboard;
