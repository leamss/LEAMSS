import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { User, FileText, Upload, LogOut, CheckCircle, Clock, AlertCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [caseData, setCaseData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [uploadStep, setUploadStep] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

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

  const handleFileUpload = async () => {
    if (!selectedFile || !uploadStep) {
      toast.error('Please select a file and step');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('case_id', caseData.id);
      formData.append('step_name', uploadStep);
      
      await axios.post(`${API}/documents/upload`, formData, getAuthHeader());
      toast.success('Document uploaded successfully!');
      setSelectedFile(null);
      setUploadStep('');
      loadData();
    } catch (error) {
      toast.error('Failed to upload document');
    }
  };

  const getStepIcon = (status) => {
    if (status === 'completed') return <CheckCircle className="h-5 w-5 text-emerald-600" />;
    if (status === 'in_progress') return <Clock className="h-5 w-5 text-blue-600" />;
    return <AlertCircle className="h-5 w-5 text-amber-600" />;
  };

  const getProgressPercentage = () => {
    if (!caseData || !caseData.steps) return 0;
    const completed = caseData.steps.filter(s => s.status === 'completed').length;
    return (completed / caseData.steps.length) * 100;
  };

  const getDocumentStatusBadge = (status) => {
    const classes = {
      pending_review: 'bg-amber-50 text-amber-700 border-amber-200',
      approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      rejected: 'bg-red-50 text-red-700 border-red-200',
      revision_required: 'bg-blue-50 text-blue-700 border-blue-200'
    };
    return classes[status] || 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <User className="h-8 w-8 text-blue-600" />
            <h1 className="text-xl font-bold" style={{ fontFamily: 'Merriweather, serif' }}>Client Portal</h1>
          </div>
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="text-slate-600"
            data-testid="logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 md:p-8">
        {!caseData ? (
          <Card className="p-12 text-center">
            <FileText className="h-16 w-16 text-slate-400 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">No Active Case</h2>
            <p className="text-slate-600">Your case is being set up. You'll receive an email when it's ready.</p>
          </Card>
        ) : (
          <div className="space-y-6">
            <Card className="p-6 bg-gradient-to-r from-blue-600 to-blue-700 text-white" data-testid="case-overview">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-2xl font-bold mb-1" style={{ fontFamily: 'Merriweather, serif' }}>
                    {caseData.case_id}
                  </h2>
                  <p className="text-blue-100">{caseData.product_name}</p>
                </div>
                <span className="bg-white/20 px-4 py-2 rounded-full text-sm font-semibold">
                  {caseData.status}
                </span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span>{getProgressPercentage().toFixed(0)}%</span>
                </div>
                <Progress value={getProgressPercentage()} className="h-2" />
              </div>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 text-center">
                <p className="text-sm text-slate-600 mb-1">Current Step</p>
                <p className="text-lg font-semibold">{caseData.current_step}</p>
              </Card>
              <Card className="p-4 text-center">
                <p className="text-sm text-slate-600 mb-1">Completed Steps</p>
                <p className="text-lg font-semibold text-emerald-600">{stats.completed_steps || 0}</p>
              </Card>
              <Card className="p-4 text-center">
                <p className="text-sm text-slate-600 mb-1">Pending Steps</p>
                <p className="text-lg font-semibold text-amber-600">{stats.pending_steps || 0}</p>
              </Card>
            </div>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Case Manager</h3>
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <User className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium">{caseData.case_manager_name}</p>
                  <p className="text-sm text-slate-600">Your assigned case manager</p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Workflow Checklist</h3>
              <div className="space-y-3" data-testid="workflow-checklist">
                {caseData.steps && caseData.steps.map((step, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-3 p-4 rounded-lg border ${
                      step.status === 'completed' ? 'bg-emerald-50 border-emerald-200' :
                      step.status === 'in_progress' ? 'bg-blue-50 border-blue-200' :
                      'bg-white border-slate-200'
                    }`}
                  >
                    {getStepIcon(step.status)}
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-semibold">{step.step_name}</p>
                          {step.notes && <p className="text-sm text-slate-600 mt-1">{step.notes}</p>}
                        </div>
                        <span className="text-xs font-medium uppercase text-slate-600">
                          {step.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Upload Documents</h3>
              <div className="space-y-4">
                <div>
                  <Label>Select Step</Label>
                  <select
                    className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-md"
                    value={uploadStep}
                    onChange={(e) => setUploadStep(e.target.value)}
                    data-testid="upload-step-select"
                  >
                    <option value="">Choose a step...</option>
                    {caseData.steps && caseData.steps.map((step, index) => (
                      <option key={index} value={step.step_name}>
                        {step.step_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Choose File</Label>
                  <Input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => setSelectedFile(e.target.files[0])}
                    className="mt-1"
                    data-testid="file-input"
                  />
                  <p className="text-xs text-slate-500 mt-1">Accepted: PDF, JPG, PNG (Max 10MB)</p>
                </div>
                <Button
                  onClick={handleFileUpload}
                  disabled={!selectedFile || !uploadStep}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  data-testid="upload-button"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </Button>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">My Documents</h3>
              <div className="space-y-3" data-testid="documents-list">
                {documents.map((doc) => (
                  <div key={doc.id} className="flex justify-between items-start p-4 border rounded-lg">
                    <div>
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-slate-600">Step: {doc.step_name}</p>
                      <p className="text-sm text-slate-500">Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</p>
                      {doc.review_comment && (
                        <p className="text-sm text-slate-700 mt-2 p-2 bg-slate-50 rounded">
                          <strong>Comment:</strong> {doc.review_comment}
                        </p>
                      )}
                    </div>
                    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold whitespace-nowrap ${getDocumentStatusBadge(doc.status)}`}>
                      {doc.status.replace('_', ' ')}
                    </span>
                  </div>
                ))}
                {documents.length === 0 && (
                  <p className="text-center text-slate-500 py-8">No documents uploaded yet</p>
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
