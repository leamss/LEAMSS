import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import NotificationBell from '@/components/NotificationBell';
import CreateTicket from '@/components/CreateTicket';
import { 
  LayoutDashboard, FileText, Users, Briefcase, LogOut, Plus, 
  Download, Edit, Trash2, UserPlus, Eye, ArrowRight, Settings,
  Search, DollarSign, TrendingUp
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [pendingSales, setPendingSales] = useState([]);
  const [cases, setCases] = useState([]);
  const [products, setProducts] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [caseManagers, setCaseManagers] = useState([]);
  const [sales, setSales] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);
  const [selectedSale, setSelectedSale] = useState(null);
  const [saleDocuments, setSaleDocuments] = useState([]);
  const [caseDocuments, setCaseDocuments] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState({ month: '', year: '' });
  
  // Dialogs
  const [productDialog, setProductDialog] = useState({ open: false, mode: 'create', data: null });
  const [userDialog, setUserDialog] = useState({ open: false, mode: 'create', data: null });
  const [workflowDialog, setWorkflowDialog] = useState({ 
    open: false, 
    product_id: null, 
    steps: [],
    currentStep: {
      step_name: '',
      step_order: 1,
      description: '',
      duration_days: null,
      required_documents: []
    },
    currentDoc: { doc_name: '', description: '', is_mandatory: true }
  });
  const [ticketDialog, setTicketDialog] = useState({ 
    open: false, 
    subject: '', 
    description: '', 
    category: 'general',
    priority: 'medium',
    target_user_id: null 
  });
  const [reassignDialog, setReassignDialog] = useState({ open: false, case_id: null });

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData || userData.role !== 'admin') {
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
      const [statsRes, salesRes, casesRes, productsRes, usersRes, allSalesRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, getAuthHeader()),
        axios.get(`${API}/sales/pending`, getAuthHeader()),
        axios.get(`${API}/cases`, getAuthHeader()),
        axios.get(`${API}/products`, getAuthHeader()),
        axios.get(`${API}/users`, getAuthHeader()),
        axios.get(`${API}/sales/pending`, getAuthHeader()).catch(() => ({ data: [] }))
      ]);
      setStats(statsRes.data);
      setPendingSales(salesRes.data);
      setCases(casesRes.data);
      setProducts(productsRes.data);
      setAllUsers(usersRes.data);
      setCaseManagers(usersRes.data.filter(u => u.role === 'case_manager'));
      setSales(allSalesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleImpersonate = async (targetUser) => {
    try {
      const response = await axios.post(`${API}/admin/impersonate/${targetUser.id}`, {}, getAuthHeader());
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      const routes = {
        admin: '/admin',
        partner: '/partner',
        case_manager: '/case-manager',
        client: '/client'
      };
      
      toast.success(`Switched to ${targetUser.name}'s account`);
      window.location.href = routes[response.data.user.role];
    } catch (error) {
      toast.error('Failed to impersonate user');
    }
  };

  const viewSaleDocuments = async (sale) => {
    try {
      const response = await axios.get(`${API}/sales/${sale.id}/documents`, getAuthHeader());
      setSaleDocuments(response.data);
      setSelectedSale(sale);
      setActiveTab('sale-docs');
    } catch (error) {
      toast.error('Failed to load sale documents');
    }
  };

  const viewCaseDetails = async (caseItem) => {
    try {
      const [caseRes, docsRes] = await Promise.all([
        axios.get(`${API}/cases/${caseItem.id}`, getAuthHeader()),
        axios.get(`${API}/documents/case/${caseItem.id}`, getAuthHeader())
      ]);
      setSelectedCase(caseRes.data);
      setCaseDocuments(docsRes.data);
      setActiveTab('case-detail');
    } catch (error) {
      toast.error('Failed to load case details');
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

  const handleApproveSale = async (saleId, status, caseManagerId) => {
    try {
      await axios.post(`${API}/sales/approve`, { 
        sale_id: saleId, 
        status, 
        case_manager_id: caseManagerId 
      }, getAuthHeader());
      toast.success(`Sale ${status}!`);
      loadData();
      setActiveTab('sales');
    } catch (error) {
      toast.error('Failed to update sale');
    }
  };

  const handleSaveProduct = async (productData) => {
    try {
      if (productDialog.mode === 'create') {
        await axios.post(`${API}/products`, productData, getAuthHeader());
        toast.success('Product created!');
      } else {
        await axios.put(`${API}/products/${productDialog.data.id}`, productData, getAuthHeader());
        toast.success('Product updated!');
      }
      setProductDialog({ open: false, mode: 'create', data: null });
      loadData();
    } catch (error) {
      toast.error('Failed to save product');
    }
  };

  const handleDeleteProduct = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    try {
      await axios.delete(`${API}/products/${productId}`, getAuthHeader());
      toast.success('Product deleted!');
      loadData();
    } catch (error) {
      toast.error('Failed to delete product');
    }
  };

  const openWorkflowEditor = (product) => {
    setWorkflowDialog({
      ...workflowDialog,
      open: true,
      product_id: product.id,
      steps: product.workflow_steps || [],
      currentStep: {
        step_name: '',
        step_order: (product.workflow_steps?.length || 0) + 1,
        description: '',
        duration_days: null,
        required_documents: []
      }
    });
  };

  const addDocToCurrentStep = () => {
    const { currentDoc, currentStep } = workflowDialog;
    if (!currentDoc.doc_name) {
      toast.error('Please enter document name');
      return;
    }
    setWorkflowDialog({
      ...workflowDialog,
      currentStep: {
        ...currentStep,
        required_documents: [...currentStep.required_documents, { ...currentDoc }]
      },
      currentDoc: { doc_name: '', description: '', is_mandatory: true }
    });
  };

  const addStepToWorkflow = () => {
    const { currentStep, steps } = workflowDialog;
    if (!currentStep.step_name) {
      toast.error('Please enter step name');
      return;
    }
    setWorkflowDialog({
      ...workflowDialog,
      steps: [...steps, currentStep],
      currentStep: {
        step_name: '',
        step_order: steps.length + 2,
        description: '',
        duration_days: null,
        required_documents: []
      }
    });
  };

  const saveWorkflow = async () => {
    try {
      const { steps, product_id } = workflowDialog;
      for (const step of steps) {
        await axios.post(`${API}/products/workflow-step`, {
          product_id,
          ...step
        }, getAuthHeader());
      }
      toast.success('Workflow saved!');
      setWorkflowDialog({ ...workflowDialog, open: false });
      loadData();
    } catch (error) {
      toast.error('Failed to save workflow');
    }
  };

  const handleSaveUser = async (userData) => {
    try {
      if (userDialog.mode === 'create') {
        await axios.post(`${API}/auth/register`, userData, getAuthHeader());
        toast.success('User created!');
      } else {
        const updateData = { ...userData };
        if (!updateData.password) delete updateData.password;
        await axios.put(`${API}/users/${userDialog.data.id}`, updateData, getAuthHeader());
        toast.success('User updated!');
      }
      setUserDialog({ open: false, mode: 'create', data: null });
      loadData();
    } catch (error) {
      toast.error('Failed to save user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try {
      await axios.delete(`${API}/users/${userId}`, getAuthHeader());
      toast.success('User deleted!');
      loadData();
    } catch (error) {
      toast.error('Failed to delete user');
    }
  };

  const handleCreateTicket = async () => {
    try {
      await axios.post(`${API}/tickets`, {
        subject: ticketDialog.subject,
        description: ticketDialog.description,
        category: ticketDialog.category,
        priority: ticketDialog.priority,
        case_id: null
      }, getAuthHeader());
      
      if (ticketDialog.target_user_id) {
        // Notification will be handled by backend
      }
      
      toast.success('Ticket created!');
      setTicketDialog({ open: false, subject: '', description: '', category: 'general', priority: 'medium', target_user_id: null });
    } catch (error) {
      toast.error('Failed to create ticket');
    }
  };

  const handleReassignCase = async (caseId, newManagerId) => {
    try {
      await axios.put(`${API}/cases/${caseId}/assign-manager?case_manager_id=${newManagerId}`, {}, getAuthHeader());
      toast.success('Case manager reassigned!');
      setReassignDialog({ open: false, case_id: null });
      loadData();
    } catch (error) {
      toast.error('Failed to reassign case');
    }
  };

  const filteredCases = cases.filter(c => 
    c.case_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.client_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredUsers = allUsers.filter(u =>
    u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRevenueData = () => {
    const partnerRevenue = {};
    sales.forEach(sale => {
      if (sale.status === 'approved') {
        if (!partnerRevenue[sale.partner_id]) {
          partnerRevenue[sale.partner_id] = {
            partner_name: sale.partner_name,
            total_sales: 0,
            total_commission: 0,
            sales_count: 0
          };
        }
        partnerRevenue[sale.partner_id].total_sales += sale.fee_amount;
        partnerRevenue[sale.partner_id].total_commission += sale.commission_amount;
        partnerRevenue[sale.partner_id].sales_count += 1;
      }
    });
    return Object.values(partnerRevenue);
  };

  return (
    <div className="flex min-h-screen bg-[#EBEBEB]">
      {/* Sidebar */}
      <aside className="w-64 bg-[#33363B] text-white p-6 flex flex-col">
        <div className="flex items-center gap-2 mb-8">
          <Briefcase className="h-8 w-8 text-[#A8B5A2]" />
          <h1 className="text-xl font-bold">LEAMSS Admin</h1>
        </div>
        
        <nav className="flex-1 space-y-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'dashboard' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <LayoutDashboard className="h-5 w-5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('sales')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'sales' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <FileText className="h-5 w-5" />
            <span>Pending Sales</span>
          </button>
          <button
            onClick={() => setActiveTab('cases')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'cases' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <Briefcase className="h-5 w-5" />
            <span>All Cases</span>
          </button>
          <button
            onClick={() => setActiveTab('products')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'products' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <Settings className="h-5 w-5" />
            <span>Products</span>
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'users' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <Users className="h-5 w-5" />
            <span>Users</span>
          </button>
          <button
            onClick={() => setActiveTab('revenue')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'revenue' ? 'bg-[#A8B5A2] text-white' : 'hover:bg-gray-700'
            }`}
          >
            <DollarSign className="h-5 w-5" />
            <span>Revenue</span>
          </button>
        </nav>
        
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-white hover:bg-gray-700 mt-4"
        >
          <LogOut className="mr-2 h-5 w-5" />
          Logout
        </Button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-[#33363B]">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'sales' && 'Pending Sales Approval'}
              {activeTab === 'cases' && 'All Cases'}
              {activeTab === 'products' && 'Products & Workflows'}
              {activeTab === 'users' && 'User Management'}
              {activeTab === 'revenue' && 'Revenue & Commission Report'}
              {activeTab === 'sale-docs' && `Sale Documents - ${selectedSale?.client_name}`}
              {activeTab === 'case-detail' && `Case Details - ${selectedCase?.case_id}`}
            </h2>
            <div className="flex items-center gap-3">
              <Button
                onClick={() => setTicketDialog({ ...ticketDialog, open: true })}
                variant="outline"
                size="sm"
              >
                <Plus className="mr-2 h-4 w-4" />
                Raise Ticket
              </Button>
              <NotificationBell />
            </div>
          </div>

          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="p-6 border-l-4 border-l-[#D9775D]">
                <p className="text-sm text-gray-600 font-medium">Pending Sales</p>
                <p className="text-3xl font-bold text-[#33363B] mt-2">{stats.pending_sales || 0}</p>
              </Card>
              <Card className="p-6 border-l-4 border-l-[#A8B5A2]">
                <p className="text-sm text-gray-600 font-medium">Active Cases</p>
                <p className="text-3xl font-bold text-[#33363B] mt-2">{stats.active_cases || 0}</p>
              </Card>
              <Card className="p-6 border-l-4 border-l-[#D3A96B]">
                <p className="text-sm text-gray-600 font-medium">Total Revenue</p>
                <p className="text-3xl font-bold text-[#33363B] mt-2">${stats.total_revenue?.toFixed(2) || 0}</p>
              </Card>
            </div>
          )}

          {/* Sales Tab */}
          {activeTab === 'sales' && (
            <div className="space-y-4">
              {pendingSales.map((sale) => (
                <Card key={sale.id} className="p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-[#33363B]">{sale.client_name}</h3>
                      <p className="text-sm text-gray-600">{sale.client_email} | {sale.client_mobile}</p>
                      <p className="text-sm text-gray-600 mt-2">Product: {sale.product_name}</p>
                      <p className="text-sm text-gray-600">Fee: ${sale.fee_amount} | Partner: {sale.partner_name}</p>
                    </div>
                    <div className="flex flex-col gap-2">
                      <Button
                        onClick={() => viewSaleDocuments(sale)}
                        size="sm"
                        className="bg-[#51D0DE] hover:bg-[#51D0DE]/90 text-white"
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View Documents
                      </Button>
                      <Select onValueChange={(managerId) => handleApproveSale(sale.id, 'approved', managerId)}>
                        <SelectTrigger className="w-48">
                          <SelectValue placeholder="Assign & Approve" />
                        </SelectTrigger>
                        <SelectContent>
                          {caseManagers.map((manager) => (
                            <SelectItem key={manager.id} value={manager.id}>
                              {manager.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        onClick={() => handleApproveSale(sale.id, 'rejected', null)}
                        variant="destructive"
                        size="sm"
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
              {pendingSales.length === 0 && (
                <p className="text-center text-gray-500 py-12">No pending sales</p>
              )}
            </div>
          )}

          {/* Sale Documents View */}
          {activeTab === 'sale-docs' && selectedSale && (
            <div className="space-y-6">
              <Button onClick={() => setActiveTab('sales')} variant="outline">
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Back to Sales
              </Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-[#33363B]">Uploaded Documents</h3>
                <div className="space-y-3">
                  {saleDocuments.map((doc, idx) => (
                    <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <p className="font-medium text-[#33363B]">{doc.filename}</p>
                        <p className="text-sm text-gray-600">Type: {doc.type}</p>
                      </div>
                      <Button
                        onClick={() => downloadDocument(doc.file_id, doc.filename)}
                        size="sm"
                        variant="outline"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  {saleDocuments.length === 0 && (
                    <p className="text-center text-gray-500 py-8">No documents uploaded</p>
                  )}
                </div>
              </Card>
              <div className="flex gap-3">
                <Select onValueChange={(managerId) => handleApproveSale(selectedSale.id, 'approved', managerId)} className="flex-1">
                  <SelectTrigger>
                    <SelectValue placeholder="Assign Case Manager & Approve" />
                  </SelectTrigger>
                  <SelectContent>
                    {caseManagers.map((manager) => (
                      <SelectItem key={manager.id} value={manager.id}>
                        {manager.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  onClick={() => handleApproveSale(selectedSale.id, 'rejected', null)}
                  variant="destructive"
                >
                  Reject Sale
                </Button>
              </div>
            </div>
          )}

          {/* Cases Tab */}
          {activeTab === 'cases' && (
            <div className="space-y-4">
              <div className="flex gap-3 mb-6">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search by case ID or client name..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              {filteredCases.map((caseItem) => (
                <Card key={caseItem.id} className="p-6 cursor-pointer hover:shadow-md transition-shadow" onClick={() => viewCaseDetails(caseItem)}>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-[#33363B]">{caseItem.case_id}</h3>
                      <p className="text-sm text-gray-600">Client: {caseItem.client_name}</p>
                      <p className="text-sm text-gray-600">Product: {caseItem.product_name}</p>
                      <p className="text-sm text-gray-600">Case Manager: {caseItem.case_manager_name}</p>
                    </div>
                    <div className="text-right">
                      <Badge className="bg-[#A8B5A2] text-white">{caseItem.current_step}</Badge>
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          setReassignDialog({ open: true, case_id: caseItem.id });
                        }}
                        size="sm"
                        variant="outline"
                        className="mt-2"
                      >
                        <Edit className="h-4 w-4 mr-1" />
                        Change Manager
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Case Detail View - ENHANCED */}
          {activeTab === 'case-detail' && selectedCase && (
            <div className="space-y-6">
              <Button onClick={() => setActiveTab('cases')} variant="outline">
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Back to Cases
              </Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-[#33363B]">Case Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Client</p>
                    <p className="font-medium text-[#33363B]">{selectedCase.client_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Email</p>
                    <p className="font-medium text-[#33363B]">{selectedCase.client_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Product</p>
                    <p className="font-medium text-[#33363B]">{selectedCase.product_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Case Manager</p>
                    <p className="font-medium text-[#33363B]">{selectedCase.case_manager_name}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-[#33363B]">Workflow Steps (All Stages)</h3>
                <div className="space-y-3">
                  {selectedCase.steps && selectedCase.steps.map((step, idx) => (
                    <div key={idx} className={`p-4 rounded-lg border-2 ${
                      step.status === 'completed' ? 'bg-green-50 border-green-200' :
                      step.status === 'in_progress' ? 'bg-blue-50 border-blue-200' :
                      'bg-gray-50 border-gray-200'
                    }`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-semibold text-[#33363B]">{step.step_order}. {step.step_name}</p>
                          {step.notes && <p className="text-sm text-gray-600 mt-1">{step.notes}</p>}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs font-medium text-gray-700">Required Documents:</p>
                              <ul className="text-xs text-gray-600 ml-4 list-disc">
                                {step.required_documents.map((doc, i) => (
                                  <li key={i}>{doc.doc_name}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                        <Badge className={
                          step.status === 'completed' ? 'bg-green-600 text-white' :
                          step.status === 'in_progress' ? 'bg-blue-600 text-white' :
                          'bg-gray-400 text-white'
                        }>
                          {step.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-[#33363B]">Documents</h3>
                <div className="space-y-3">
                  {caseDocuments.map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <p className="font-medium text-[#33363B]">{doc.filename}</p>
                        <p className="text-sm text-gray-600">Step: {doc.step_name}</p>
                        <p className="text-sm text-gray-600">Status: {doc.status}</p>
                      </div>
                      <Button
                        onClick={() => downloadDocument(doc.id, doc.filename)}
                        size="sm"
                        variant="outline"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Products Tab */}
          {activeTab === 'products' && (
            <div className="space-y-6">
              <div className="flex justify-end">
                <Button
                  onClick={() => setProductDialog({ open: true, mode: 'create', data: { name: '', description: '', fee: 0, commission_rate: 0 } })}
                  className="bg-[#D3A96B] hover:bg-[#D3A96B]/90 text-white"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Product
                </Button>
              </div>
              <div className="space-y-4">
                {products.map((product) => (
                  <Card key={product.id} className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-[#33363B]">{product.name}</h3>
                        <p className="text-sm text-gray-600">{product.description}</p>
                        <p className="text-sm text-gray-600 mt-2">Fee: ${product.fee} | Commission: {product.commission_rate}%</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => openWorkflowEditor(product)}
                          size="sm"
                          className="bg-[#51D0DE] hover:bg-[#51D0DE]/90 text-white"
                        >
                          <Settings className="h-4 w-4 mr-1" />
                          Edit Workflow
                        </Button>
                        <Button
                          onClick={() => setProductDialog({ open: true, mode: 'edit', data: product })}
                          size="sm"
                          variant="outline"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          onClick={() => handleDeleteProduct(product.id)}
                          size="sm"
                          variant="destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {product.workflow_steps && product.workflow_steps.length > 0 && (
                      <div>
                        <p className="font-medium mb-2 text-[#33363B]">Workflow Steps:</p>
                        <div className="space-y-2">
                          {product.workflow_steps.map((step, idx) => (
                            <div key={idx} className="text-sm p-2 bg-gray-50 rounded">
                              <span className="font-medium text-[#33363B]">{step.step_order}. {step.step_name}</span>
                              {step.required_documents && step.required_documents.length > 0 && (
                                <span className="text-xs text-gray-500 ml-2">
                                  ({step.required_documents.length} docs required)
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <div className="relative flex-1 mr-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button
                  onClick={() => setUserDialog({ open: true, mode: 'create', data: { email: '', name: '', password: '', role: 'partner', mobile: '' } })}
                  className="bg-[#D3A96B] hover:bg-[#D3A96B]/90 text-white"
                >
                  <UserPlus className="mr-2 h-4 w-4" />
                  Create User
                </Button>
              </div>
              
              {['partner', 'case_manager', 'client'].map(role => (
                <Card key={role} className="p-6">
                  <h3 className="text-lg font-semibold mb-4 capitalize text-[#33363B]">
                    {role === 'case_manager' ? 'Case Managers' : `${role}s`}
                  </h3>
                  <div className="space-y-3">
                    {filteredUsers.filter(u => u.role === role).map((usr) => (
                      <div key={usr.id} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <p className="font-medium text-[#33363B]">{usr.name}</p>
                          <p className="text-sm text-gray-600">{usr.email}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleImpersonate(usr)}
                            size="sm"
                            className="bg-[#51D0DE] hover:bg-[#51D0DE]/90 text-white"
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Switch
                          </Button>
                          <Button
                            onClick={() => setUserDialog({ open: true, mode: 'edit', data: usr })}
                            size="sm"
                            variant="outline"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            onClick={() => handleDeleteUser(usr.id)}
                            size="sm"
                            variant="destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Revenue Tab - NEW */}
          {activeTab === 'revenue' && (
            <div className="space-y-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-[#33363B]">Partner Revenue & Commission Report</h3>
                <div className="space-y-4">
                  {getRevenueData().map((data, idx) => (
                    <div key={idx} className="p-4 border rounded-lg">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-semibold text-[#33363B]">{data.partner_name}</p>
                          <p className="text-sm text-gray-600">Total Sales: {data.sales_count}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-gray-600">Total Revenue</p>
                          <p className="text-lg font-bold text-[#A8B5A2]">${data.total_sales.toFixed(2)}</p>
                          <p className="text-sm text-gray-600 mt-2">Commission Payable</p>
                          <p className="text-lg font-bold text-[#D3A96B]">${data.total_commission.toFixed(2)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </div>
      </main>

      {/* Product Dialog */}
      <Dialog open={productDialog.open} onOpenChange={(open) => setProductDialog({ ...productDialog, open })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{productDialog.mode === 'create' ? 'Create' : 'Edit'} Product</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Product Name</Label>
              <Input
                value={productDialog.data?.name || ''}
                onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, name: e.target.value } })}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={productDialog.data?.description || ''}
                onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, description: e.target.value } })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fee ($)</Label>
                <Input
                  type="number"
                  value={productDialog.data?.fee || 0}
                  onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, fee: parseFloat(e.target.value) } })}
                />
              </div>
              <div>
                <Label>Commission (%)</Label>
                <Input
                  type="number"
                  value={productDialog.data?.commission_rate || 0}
                  onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_rate: parseFloat(e.target.value) } })}
                />
              </div>
            </div>
            <Button onClick={() => handleSaveProduct(productDialog.data)} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90 text-white">
              Save Product
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Workflow Editor Dialog - NEW ENHANCED */}
      <Dialog open={workflowDialog.open} onOpenChange={(open) => setWorkflowDialog({ ...workflowDialog, open })}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Workflow Steps</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Existing Steps */}
            {workflowDialog.steps.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2 text-[#33363B]">Current Steps:</h4>
                <div className="space-y-2">
                  {workflowDialog.steps.map((step, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 rounded border">
                      <p className="font-medium text-[#33363B]">{step.step_order}. {step.step_name}</p>
                      <p className="text-sm text-gray-600">{step.description}</p>
                      {step.required_documents.length > 0 && (
                        <p className="text-xs text-gray-500 mt-1">
                          Documents: {step.required_documents.map(d => d.doc_name).join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Add New Step */}
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3 text-[#33363B]">Add New Step:</h4>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Step Name *</Label>
                    <Input
                      value={workflowDialog.currentStep.step_name}
                      onChange={(e) => setWorkflowDialog({ 
                        ...workflowDialog, 
                        currentStep: { ...workflowDialog.currentStep, step_name: e.target.value }
                      })}
                      placeholder="e.g., Document Verification"
                    />
                  </div>
                  <div>
                    <Label>Step Order</Label>
                    <Input
                      type="number"
                      value={workflowDialog.currentStep.step_order}
                      onChange={(e) => setWorkflowDialog({ 
                        ...workflowDialog, 
                        currentStep: { ...workflowDialog.currentStep, step_order: parseInt(e.target.value) }
                      })}
                    />
                  </div>
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    value={workflowDialog.currentStep.description}
                    onChange={(e) => setWorkflowDialog({ 
                      ...workflowDialog, 
                      currentStep: { ...workflowDialog.currentStep, description: e.target.value }
                    })}
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Duration (days)</Label>
                  <Input
                    type="number"
                    value={workflowDialog.currentStep.duration_days || ''}
                    onChange={(e) => setWorkflowDialog({ 
                      ...workflowDialog, 
                      currentStep: { ...workflowDialog.currentStep, duration_days: parseInt(e.target.value) || null }
                    })}
                  />
                </div>

                {/* Document Requirements */}
                <div className="border-t pt-3">
                  <h5 className="font-medium mb-2 text-[#33363B]">Document Requirements:</h5>
                  {workflowDialog.currentStep.required_documents.length > 0 && (
                    <div className="space-y-1 mb-2">
                      {workflowDialog.currentStep.required_documents.map((doc, i) => (
                        <div key={i} className="text-sm p-2 bg-blue-50 rounded flex justify-between">
                          <span className="text-[#33363B]">{doc.doc_name} {doc.is_mandatory && '*'}</span>
                          <button
                            onClick={() => {
                              const docs = [...workflowDialog.currentStep.required_documents];
                              docs.splice(i, 1);
                              setWorkflowDialog({
                                ...workflowDialog,
                                currentStep: { ...workflowDialog.currentStep, required_documents: docs }
                              });
                            }}
                            className="text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="Document name"
                      value={workflowDialog.currentDoc.doc_name}
                      onChange={(e) => setWorkflowDialog({
                        ...workflowDialog,
                        currentDoc: { ...workflowDialog.currentDoc, doc_name: e.target.value }
                      })}
                    />
                    <Input
                      placeholder="Description"
                      value={workflowDialog.currentDoc.description}
                      onChange={(e) => setWorkflowDialog({
                        ...workflowDialog,
                        currentDoc: { ...workflowDialog.currentDoc, description: e.target.value }
                      })}
                    />
                  </div>
                  <Button
                    onClick={addDocToCurrentStep}
                    size="sm"
                    variant="outline"
                    className="mt-2"
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    Add Document
                  </Button>
                </div>

                <Button
                  onClick={addStepToWorkflow}
                  className="w-full bg-[#51D0DE] hover:bg-[#51D0DE]/90 text-white"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add This Step to Workflow
                </Button>
              </div>
            </div>

            <Button onClick={saveWorkflow} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90 text-white">
              Save Complete Workflow
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* User Dialog */}
      <Dialog open={userDialog.open} onOpenChange={(open) => setUserDialog({ ...userDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{userDialog.mode === 'create' ? 'Create' : 'Edit'} User</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Name</Label>
              <Input
                value={userDialog.data?.name || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, name: e.target.value } })}
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={userDialog.data?.email || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, email: e.target.value } })}
              />
            </div>
            <div>
              <Label>Password</Label>
              <Input
                type="password"
                value={userDialog.data?.password || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, password: e.target.value } })}
                placeholder={userDialog.mode === 'edit' ? 'Leave blank to keep current' : ''}
              />
            </div>
            <div>
              <Label>Mobile</Label>
              <Input
                value={userDialog.data?.mobile || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, mobile: e.target.value } })}
              />
            </div>
            <div>
              <Label>Role</Label>
              <Select
                value={userDialog.data?.role}
                onValueChange={(value) => setUserDialog({ ...userDialog, data: { ...userDialog.data, role: value } })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="partner">Partner</SelectItem>
                  <SelectItem value="case_manager">Case Manager</SelectItem>
                  <SelectItem value="client">Client</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={() => handleSaveUser(userDialog.data)} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90 text-white">
              Save User
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Ticket Dialog - ENHANCED */}
      <Dialog open={ticketDialog.open} onOpenChange={(open) => setTicketDialog({ ...ticketDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Raise Ticket</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Send To (Optional)</Label>
              <Select
                value={ticketDialog.target_user_id || ''}
                onValueChange={(value) => setTicketDialog({ ...ticketDialog, target_user_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select user or leave blank for all" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem>
                  {allUsers.map((usr) => (
                    <SelectItem key={usr.id} value={usr.id}>
                      {usr.name} ({usr.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Subject</Label>
              <Input
                value={ticketDialog.subject}
                onChange={(e) => setTicketDialog({ ...ticketDialog, subject: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Category</Label>
                <Select value={ticketDialog.category} onValueChange={(value) => setTicketDialog({ ...ticketDialog, category: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="document">Document</SelectItem>
                    <SelectItem value="payment">Payment</SelectItem>
                    <SelectItem value="technical">Technical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Priority</Label>
                <Select value={ticketDialog.priority} onValueChange={(value) => setTicketDialog({ ...ticketDialog, priority: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={ticketDialog.description}
                onChange={(e) => setTicketDialog({ ...ticketDialog, description: e.target.value })}
                rows={4}
              />
            </div>
            <Button onClick={handleCreateTicket} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90 text-white">
              Create Ticket
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reassign Dialog */}
      <Dialog open={reassignDialog.open} onOpenChange={(open) => setReassignDialog({ ...reassignDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reassign Case Manager</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Select onValueChange={(value) => handleReassignCase(reassignDialog.case_id, value)}>
              <SelectTrigger>
                <SelectValue placeholder="Select new case manager" />
              </SelectTrigger>
              <SelectContent>
                {caseManagers.map((manager) => (
                  <SelectItem key={manager.id} value={manager.id}>
                    {manager.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
