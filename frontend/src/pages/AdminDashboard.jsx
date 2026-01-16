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
import { 
  LayoutDashboard, FileText, Users, Briefcase, LogOut, Plus, 
  Download, Edit, Trash2, UserPlus, Eye, ArrowRight, Settings,
  Search, DollarSign, TrendingUp, ChevronDown, ChevronUp, GripVertical,
  CheckCircle, XCircle, Clock
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
  const [allSales, setAllSales] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);
  const [selectedSale, setSelectedSale] = useState(null);
  const [saleDocuments, setSaleDocuments] = useState([]);
  const [caseDocuments, setCaseDocuments] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [userSearchTerm, setUserSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState({ month: '', year: '' });
  
  // Dialogs
  const [productDialog, setProductDialog] = useState({ open: false, mode: 'create', data: null });
  const [workflowDialog, setWorkflowDialog] = useState({ 
    open: false, 
    product: null,
    editingStepIndex: null
  });
  const [stepEditorDialog, setStepEditorDialog] = useState({
    open: false,
    mode: 'create',
    stepData: {
      step_name: '',
      step_order: 1,
      description: '',
      duration_days: '',
      required_documents: []
    },
    newDoc: { doc_name: '', description: '', is_mandatory: true }
  });
  const [userDialog, setUserDialog] = useState({ open: false, mode: 'create', data: null });
  const [ticketDialog, setTicketDialog] = useState({ 
    open: false, 
    subject: '', 
    description: '', 
    category: 'general',
    priority: 'medium',
    target_user_id: '' 
  });
  const [reassignDialog, setReassignDialog] = useState({ open: false, case_id: null });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadData = async () => {
    try {
      const authHeader = getAuthHeader();
      const [statsRes, pendingSalesRes, casesRes, productsRes, usersRes, allSalesRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, authHeader),
        axios.get(`${API}/sales/pending`, authHeader),
        axios.get(`${API}/cases`, authHeader),
        axios.get(`${API}/products`, authHeader),
        axios.get(`${API}/users`, authHeader),
        axios.get(`${API}/sales/pending`, authHeader).catch(() => ({ data: [] }))
      ]);
      setStats(statsRes.data);
      setPendingSales(pendingSalesRes.data);
      setCases(casesRes.data);
      setProducts(productsRes.data);
      setAllUsers(usersRes.data);
      setCaseManagers(usersRes.data.filter(u => u.role === 'case_manager'));
      setAllSales(allSalesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData || userData.role !== 'admin') {
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
      const targetRoute = routes[response.data.user.role];
      setTimeout(() => { window.location.assign(targetRoute); }, 100);
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

  // Workflow Management Functions
  const openWorkflowEditor = (product) => {
    setWorkflowDialog({
      open: true,
      product: product,
      editingStepIndex: null
    });
  };

  const openStepEditor = (mode, stepIndex = null) => {
    if (mode === 'create') {
      const nextOrder = (workflowDialog.product?.workflow_steps?.length || 0) + 1;
      setStepEditorDialog({
        open: true,
        mode: 'create',
        stepData: {
          step_name: '',
          step_order: nextOrder,
          description: '',
          duration_days: '',
          required_documents: []
        },
        newDoc: { doc_name: '', description: '', is_mandatory: true }
      });
    } else {
      const step = workflowDialog.product.workflow_steps[stepIndex];
      setStepEditorDialog({
        open: true,
        mode: 'edit',
        stepData: { ...step, duration_days: step.duration_days || '' },
        newDoc: { doc_name: '', description: '', is_mandatory: true }
      });
      setWorkflowDialog({ ...workflowDialog, editingStepIndex: stepIndex });
    }
  };

  const addDocToStep = () => {
    const { newDoc, stepData } = stepEditorDialog;
    if (!newDoc.doc_name.trim()) {
      toast.error('Please enter document name');
      return;
    }
    setStepEditorDialog({
      ...stepEditorDialog,
      stepData: {
        ...stepData,
        required_documents: [...stepData.required_documents, { ...newDoc }]
      },
      newDoc: { doc_name: '', description: '', is_mandatory: true }
    });
  };

  const removeDocFromStep = (docIndex) => {
    const updatedDocs = stepEditorDialog.stepData.required_documents.filter((_, i) => i !== docIndex);
    setStepEditorDialog({
      ...stepEditorDialog,
      stepData: { ...stepEditorDialog.stepData, required_documents: updatedDocs }
    });
  };

  const saveWorkflowStep = async () => {
    const { stepData, mode } = stepEditorDialog;
    if (!stepData.step_name.trim()) {
      toast.error('Please enter step name');
      return;
    }

    try {
      const productId = workflowDialog.product.id;
      
      if (mode === 'create') {
        await axios.post(`${API}/products/workflow-step`, {
          product_id: productId,
          step_name: stepData.step_name,
          step_order: stepData.step_order,
          description: stepData.description,
          duration_days: stepData.duration_days ? parseInt(stepData.duration_days) : null,
          required_documents: stepData.required_documents
        }, getAuthHeader());
        toast.success('Workflow step added!');
      } else {
        const stepOrder = workflowDialog.product.workflow_steps[workflowDialog.editingStepIndex].step_order;
        await axios.put(`${API}/products/${productId}/workflow-step/${stepOrder}`, {
          product_id: productId,
          step_name: stepData.step_name,
          step_order: stepData.step_order,
          description: stepData.description,
          duration_days: stepData.duration_days ? parseInt(stepData.duration_days) : null,
          required_documents: stepData.required_documents
        }, getAuthHeader());
        toast.success('Workflow step updated!');
      }
      
      setStepEditorDialog({ ...stepEditorDialog, open: false });
      
      // Reload products and update workflow dialog
      const productsRes = await axios.get(`${API}/products`, getAuthHeader());
      setProducts(productsRes.data);
      const updatedProduct = productsRes.data.find(p => p.id === productId);
      setWorkflowDialog({ ...workflowDialog, product: updatedProduct, editingStepIndex: null });
    } catch (error) {
      toast.error('Failed to save workflow step');
    }
  };

  const deleteWorkflowStep = async (stepOrder) => {
    if (!window.confirm('Are you sure you want to delete this step?')) return;
    
    try {
      const productId = workflowDialog.product.id;
      await axios.delete(`${API}/products/${productId}/workflow-step/${stepOrder}`, getAuthHeader());
      toast.success('Workflow step deleted!');
      
      // Reload products and update workflow dialog
      const productsRes = await axios.get(`${API}/products`, getAuthHeader());
      setProducts(productsRes.data);
      const updatedProduct = productsRes.data.find(p => p.id === productId);
      setWorkflowDialog({ ...workflowDialog, product: updatedProduct });
    } catch (error) {
      toast.error('Failed to delete workflow step');
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
      toast.error(error.response?.data?.detail || 'Failed to save user');
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
    if (!ticketDialog.subject || !ticketDialog.description) {
      toast.error('Please fill subject and description');
      return;
    }
    try {
      await axios.post(`${API}/tickets`, {
        subject: ticketDialog.subject,
        description: ticketDialog.description,
        category: ticketDialog.category,
        priority: ticketDialog.priority,
        case_id: null
      }, getAuthHeader());
      toast.success('Ticket created!');
      setTicketDialog({ open: false, subject: '', description: '', category: 'general', priority: 'medium', target_user_id: '' });
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

  // Filtered data
  const filteredCases = cases.filter(c => 
    c.case_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.client_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredUsers = allUsers.filter(u =>
    u.name?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
    u.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
  );

  // Revenue calculations
  const getRevenueData = () => {
    const partnerRevenue = {};
    allSales.forEach(sale => {
      if (sale.status === 'approved') {
        if (!partnerRevenue[sale.partner_id]) {
          partnerRevenue[sale.partner_id] = {
            partner_name: sale.partner_name,
            total_sales: 0,
            total_commission: 0,
            sales_count: 0
          };
        }
        partnerRevenue[sale.partner_id].total_sales += sale.fee_amount || 0;
        partnerRevenue[sale.partner_id].total_commission += sale.commission_amount || 0;
        partnerRevenue[sale.partner_id].sales_count += 1;
      }
    });
    return Object.values(partnerRevenue);
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: <Badge className="bg-amber-100 text-amber-700 border-amber-300">Pending</Badge>,
      approved: <Badge className="bg-green-100 text-green-700 border-green-300">Approved</Badge>,
      rejected: <Badge className="bg-red-100 text-red-700 border-red-300">Rejected</Badge>,
      active: <Badge className="bg-blue-100 text-blue-700 border-blue-300">Active</Badge>,
      completed: <Badge className="bg-green-100 text-green-700 border-green-300">Completed</Badge>,
      in_progress: <Badge className="bg-blue-100 text-blue-700 border-blue-300">In Progress</Badge>,
      locked: <Badge className="bg-slate-100 text-slate-600 border-slate-300">Locked</Badge>
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  return (
    <div className="flex min-h-screen bg-[#F5F7FA]" data-testid="admin-dashboard">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-800 text-white p-6 flex flex-col" data-testid="admin-sidebar">
        <div className="flex items-center gap-2 mb-8">
          <Briefcase className="h-8 w-8 text-[#f7620b]" />
          <h1 className="text-xl font-bold">LEAMSS Admin</h1>
        </div>
        
        <nav className="flex-1 space-y-2">
          {[
            { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
            { id: 'sales', icon: FileText, label: 'Pending Sales' },
            { id: 'cases', icon: Briefcase, label: 'All Cases' },
            { id: 'products', icon: Settings, label: 'Products' },
            { id: 'users', icon: Users, label: 'Users' },
            { id: 'revenue', icon: DollarSign, label: 'Revenue' }
          ].map(item => (
            <button
              key={item.id}
              onClick={() => { setActiveTab(item.id); setSelectedCase(null); setSelectedSale(null); }}
              data-testid={`nav-${item.id}`}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeTab === item.id ? 'bg-[#2a777a] text-white' : 'hover:bg-slate-700 text-slate-300'
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
            </button>
          ))}
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

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-slate-800" data-testid="page-title">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'sales' && 'Pending Sales Approval'}
              {activeTab === 'cases' && !selectedCase && 'All Cases'}
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
                data-testid="raise-ticket-btn"
              >
                <Plus className="mr-2 h-4 w-4" />
                Raise Ticket
              </Button>
              <NotificationBell />
            </div>
          </div>

          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6" data-testid="dashboard-content">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="p-6 border-l-4 border-l-[#f7620b]">
                  <p className="text-sm text-slate-600 font-medium">Pending Sales</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.pending_sales || 0}</p>
                </Card>
                <Card className="p-6 border-l-4 border-l-[#2a777a]">
                  <p className="text-sm text-slate-600 font-medium">Active Cases</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.active_cases || 0}</p>
                </Card>
                <Card className="p-6 border-l-4 border-l-green-500">
                  <p className="text-sm text-slate-600 font-medium">Total Revenue</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">${(stats.total_revenue || 0).toFixed(2)}</p>
                </Card>
              </div>

              {pendingSales.length > 0 && (
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 text-slate-800">Recent Pending Sales</h3>
                  <div className="space-y-3">
                    {pendingSales.slice(0, 3).map(sale => (
                      <div key={sale.id} className="flex justify-between items-center p-3 bg-amber-50 rounded-lg border border-amber-200">
                        <div>
                          <p className="font-medium text-slate-800">{sale.client_name}</p>
                          <p className="text-sm text-slate-600">{sale.product_name}</p>
                        </div>
                        <Button size="sm" onClick={() => viewSaleDocuments(sale)} className="bg-[#2a777a] hover:bg-[#236466]">
                          Review
                        </Button>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Sales Tab */}
          {activeTab === 'sales' && (
            <div className="space-y-4" data-testid="sales-content">
              {pendingSales.length === 0 ? (
                <Card className="p-12 text-center">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <p className="text-slate-600">No pending sales to approve</p>
                </Card>
              ) : (
                pendingSales.map((sale) => (
                  <Card key={sale.id} className="p-6" data-testid={`sale-card-${sale.id}`}>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-slate-800">{sale.client_name}</h3>
                        <p className="text-sm text-slate-600">{sale.client_email} | {sale.client_mobile}</p>
                        <p className="text-sm text-slate-600 mt-2">Product: <span className="font-medium">{sale.product_name}</span></p>
                        <p className="text-sm text-slate-600">Fee: ${sale.fee_amount} | Partner: {sale.partner_name}</p>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Button
                          onClick={() => viewSaleDocuments(sale)}
                          size="sm"
                          className="bg-[#2a777a] hover:bg-[#236466] text-white"
                          data-testid={`view-docs-${sale.id}`}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View Documents
                        </Button>
                        <Select onValueChange={(managerId) => handleApproveSale(sale.id, 'approved', managerId)}>
                          <SelectTrigger className="w-48" data-testid={`assign-manager-${sale.id}`}>
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
                          data-testid={`reject-sale-${sale.id}`}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Sale Documents View */}
          {activeTab === 'sale-docs' && selectedSale && (
            <div className="space-y-6" data-testid="sale-docs-content">
              <Button onClick={() => setActiveTab('sales')} variant="outline">
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Back to Sales
              </Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Sale Information</h3>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <p className="text-sm text-slate-500">Client</p>
                    <p className="font-medium text-slate-800">{selectedSale.client_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Email</p>
                    <p className="font-medium text-slate-800">{selectedSale.client_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Product</p>
                    <p className="font-medium text-slate-800">{selectedSale.product_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Fee Amount</p>
                    <p className="font-medium text-slate-800">${selectedSale.fee_amount}</p>
                  </div>
                </div>
                
                <h4 className="font-semibold mb-3 text-slate-800">Uploaded Documents</h4>
                <div className="space-y-3">
                  {saleDocuments.length === 0 ? (
                    <p className="text-center text-slate-500 py-4">No documents uploaded</p>
                  ) : (
                    saleDocuments.map((doc, idx) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <p className="font-medium text-slate-800">{doc.filename}</p>
                          <p className="text-sm text-slate-600">Type: {doc.type}</p>
                        </div>
                        <Button onClick={() => downloadDocument(doc.file_id, doc.filename)} size="sm" variant="outline">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
              <div className="flex gap-3">
                <Select onValueChange={(managerId) => handleApproveSale(selectedSale.id, 'approved', managerId)} className="flex-1">
                  <SelectTrigger data-testid="assign-case-manager">
                    <SelectValue placeholder="Assign Case Manager & Approve" />
                  </SelectTrigger>
                  <SelectContent>
                    {caseManagers.map((manager) => (
                      <SelectItem key={manager.id} value={manager.id}>{manager.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button onClick={() => handleApproveSale(selectedSale.id, 'rejected', null)} variant="destructive">
                  Reject Sale
                </Button>
              </div>
            </div>
          )}

          {/* Cases Tab */}
          {activeTab === 'cases' && !selectedCase && (
            <div className="space-y-4" data-testid="cases-content">
              <div className="flex gap-3 mb-6">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search by case ID or client name..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                    data-testid="case-search"
                  />
                </div>
              </div>
              {filteredCases.length === 0 ? (
                <Card className="p-12 text-center">
                  <Briefcase className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <p className="text-slate-600">No cases found</p>
                </Card>
              ) : (
                filteredCases.map((caseItem) => (
                  <Card 
                    key={caseItem.id} 
                    className="p-6 cursor-pointer hover:shadow-md transition-shadow" 
                    onClick={() => viewCaseDetails(caseItem)}
                    data-testid={`case-card-${caseItem.id}`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-800">{caseItem.case_id}</h3>
                        <p className="text-sm text-slate-600">Client: {caseItem.client_name}</p>
                        <p className="text-sm text-slate-600">Product: {caseItem.product_name}</p>
                        <p className="text-sm text-slate-600">Case Manager: {caseItem.case_manager_name}</p>
                      </div>
                      <div className="text-right">
                        {getStatusBadge(caseItem.status || 'active')}
                        <p className="text-sm text-slate-600 mt-2">Step: {caseItem.current_step}</p>
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            setReassignDialog({ open: true, case_id: caseItem.id });
                          }}
                          size="sm"
                          variant="outline"
                          className="mt-2"
                          data-testid={`reassign-${caseItem.id}`}
                        >
                          <Edit className="h-4 w-4 mr-1" />
                          Change Manager
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Case Detail View */}
          {activeTab === 'case-detail' && selectedCase && (
            <div className="space-y-6" data-testid="case-detail-content">
              <Button onClick={() => { setActiveTab('cases'); setSelectedCase(null); }} variant="outline">
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Back to Cases
              </Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Case Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Client</p>
                    <p className="font-medium text-slate-800">{selectedCase.client_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Email</p>
                    <p className="font-medium text-slate-800">{selectedCase.client_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Product</p>
                    <p className="font-medium text-slate-800">{selectedCase.product_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Case Manager</p>
                    <p className="font-medium text-slate-800">{selectedCase.case_manager_name}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Workflow Progress</h3>
                <div className="space-y-3">
                  {selectedCase.steps && selectedCase.steps.map((step, idx) => (
                    <div key={idx} className={`p-4 rounded-lg border-2 ${
                      step.status === 'completed' ? 'bg-green-50 border-green-200' :
                      step.status === 'in_progress' ? 'bg-blue-50 border-blue-300' :
                      'bg-slate-50 border-slate-200'
                    }`}>
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-semibold text-slate-800">{step.step_order}. {step.step_name}</p>
                          {step.notes && <p className="text-sm text-slate-600 mt-1">{step.notes}</p>}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs font-medium text-slate-700">Required Documents:</p>
                              <ul className="text-xs text-slate-600 ml-4 list-disc">
                                {step.required_documents.map((doc, i) => (
                                  <li key={i}>{doc.doc_name}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                        {getStatusBadge(step.status)}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Documents</h3>
                <div className="space-y-3">
                  {caseDocuments.length === 0 ? (
                    <p className="text-center text-slate-500 py-4">No documents uploaded</p>
                  ) : (
                    caseDocuments.map((doc) => (
                      <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <p className="font-medium text-slate-800">{doc.filename}</p>
                          <p className="text-sm text-slate-600">Step: {doc.step_name}</p>
                          <p className="text-sm text-slate-500">Status: {doc.status}</p>
                        </div>
                        <Button onClick={() => downloadDocument(doc.id, doc.filename)} size="sm" variant="outline">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          )}

          {/* Products Tab */}
          {activeTab === 'products' && (
            <div className="space-y-6" data-testid="products-content">
              <div className="flex justify-end">
                <Button
                  onClick={() => setProductDialog({ open: true, mode: 'create', data: { name: '', description: '', fee: 0, commission_rate: 0 } })}
                  className="bg-[#f7620b] hover:bg-[#e55a09] text-white"
                  data-testid="create-product-btn"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Product
                </Button>
              </div>
              <div className="space-y-4">
                {products.length === 0 ? (
                  <Card className="p-12 text-center">
                    <Settings className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-600">No products created yet</p>
                  </Card>
                ) : (
                  products.map((product) => (
                    <Card key={product.id} className="p-6" data-testid={`product-card-${product.id}`}>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-semibold text-slate-800">{product.name}</h3>
                          <p className="text-sm text-slate-600">{product.description}</p>
                          <p className="text-sm text-slate-600 mt-2">
                            Fee: <span className="font-medium">${product.fee}</span> | 
                            Commission: <span className="font-medium">{product.commission_rate}%</span>
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => openWorkflowEditor(product)}
                            size="sm"
                            className="bg-[#2a777a] hover:bg-[#236466] text-white"
                            data-testid={`edit-workflow-${product.id}`}
                          >
                            <Settings className="h-4 w-4 mr-1" />
                            Edit Workflow
                          </Button>
                          <Button
                            onClick={() => setProductDialog({ open: true, mode: 'edit', data: product })}
                            size="sm"
                            variant="outline"
                            data-testid={`edit-product-${product.id}`}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            onClick={() => handleDeleteProduct(product.id)}
                            size="sm"
                            variant="destructive"
                            data-testid={`delete-product-${product.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      {product.workflow_steps && product.workflow_steps.length > 0 && (
                        <div className="border-t pt-4">
                          <p className="font-medium mb-3 text-slate-800">Workflow Steps ({product.workflow_steps.length}):</p>
                          <div className="space-y-2">
                            {product.workflow_steps.sort((a, b) => a.step_order - b.step_order).map((step, idx) => (
                              <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                                <span className="w-8 h-8 rounded-full bg-[#2a777a] text-white flex items-center justify-center text-sm font-medium">
                                  {step.step_order}
                                </span>
                                <div className="flex-1">
                                  <p className="font-medium text-slate-800">{step.step_name}</p>
                                  {step.required_documents && step.required_documents.length > 0 && (
                                    <p className="text-xs text-slate-500">
                                      {step.required_documents.length} document(s) required
                                    </p>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-6" data-testid="users-content">
              <div className="flex justify-between items-center">
                <div className="relative flex-1 mr-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search users..."
                    value={userSearchTerm}
                    onChange={(e) => setUserSearchTerm(e.target.value)}
                    className="pl-10"
                    data-testid="user-search"
                  />
                </div>
                <Button
                  onClick={() => setUserDialog({ open: true, mode: 'create', data: { email: '', name: '', password: '', role: 'partner', mobile: '' } })}
                  className="bg-[#f7620b] hover:bg-[#e55a09] text-white"
                  data-testid="create-user-btn"
                >
                  <UserPlus className="mr-2 h-4 w-4" />
                  Create User
                </Button>
              </div>
              
              {['admin', 'case_manager', 'partner', 'client'].map(role => {
                const roleUsers = filteredUsers.filter(u => u.role === role);
                if (roleUsers.length === 0) return null;
                
                return (
                  <Card key={role} className="p-6" data-testid={`users-${role}`}>
                    <h3 className="text-lg font-semibold mb-4 capitalize text-slate-800">
                      {role === 'case_manager' ? 'Case Managers' : role === 'admin' ? 'Administrators' : `${role}s`}
                      <Badge className="ml-2 bg-slate-100 text-slate-600">{roleUsers.length}</Badge>
                    </h3>
                    <div className="space-y-3">
                      {roleUsers.map((usr) => (
                        <div key={usr.id} className="flex justify-between items-center p-3 border rounded-lg hover:bg-slate-50">
                          <div>
                            <p className="font-medium text-slate-800">{usr.name}</p>
                            <p className="text-sm text-slate-600">{usr.email}</p>
                          </div>
                          <div className="flex gap-2">
                            {usr.role !== 'admin' && (
                              <Button
                                onClick={() => handleImpersonate(usr)}
                                size="sm"
                                className="bg-[#2a777a] hover:bg-[#236466] text-white"
                                data-testid={`impersonate-${usr.id}`}
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                Switch
                              </Button>
                            )}
                            <Button
                              onClick={() => setUserDialog({ open: true, mode: 'edit', data: usr })}
                              size="sm"
                              variant="outline"
                              data-testid={`edit-user-${usr.id}`}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            {usr.role !== 'admin' && (
                              <Button
                                onClick={() => handleDeleteUser(usr.id)}
                                size="sm"
                                variant="destructive"
                                data-testid={`delete-user-${usr.id}`}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Revenue Tab */}
          {activeTab === 'revenue' && (
            <div className="space-y-6" data-testid="revenue-content">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="p-6 bg-gradient-to-br from-[#2a777a] to-[#236466] text-white">
                  <p className="text-sm opacity-80">Total Revenue</p>
                  <p className="text-4xl font-bold mt-2">${(stats.total_revenue || 0).toFixed(2)}</p>
                </Card>
                <Card className="p-6 bg-gradient-to-br from-[#f7620b] to-[#e55a09] text-white">
                  <p className="text-sm opacity-80">Approved Sales</p>
                  <p className="text-4xl font-bold mt-2">{allSales.filter(s => s.status === 'approved').length}</p>
                </Card>
              </div>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Partner Revenue & Commission Report</h3>
                {getRevenueData().length === 0 ? (
                  <p className="text-center text-slate-500 py-8">No approved sales yet</p>
                ) : (
                  <div className="space-y-4">
                    {getRevenueData().map((data, idx) => (
                      <div key={idx} className="p-4 border rounded-lg">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-semibold text-slate-800">{data.partner_name}</p>
                            <p className="text-sm text-slate-600">Total Sales: {data.sales_count}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-slate-500">Total Revenue</p>
                            <p className="text-lg font-bold text-[#2a777a]">${data.total_sales.toFixed(2)}</p>
                            <p className="text-sm text-slate-500 mt-2">Commission Payable</p>
                            <p className="text-lg font-bold text-[#f7620b]">${data.total_commission.toFixed(2)}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
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
                data-testid="product-name-input"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={productDialog.data?.description || ''}
                onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, description: e.target.value } })}
                data-testid="product-description-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fee ($)</Label>
                <Input
                  type="number"
                  value={productDialog.data?.fee || 0}
                  onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, fee: parseFloat(e.target.value) || 0 } })}
                  data-testid="product-fee-input"
                />
              </div>
              <div>
                <Label>Commission Type</Label>
                <Select 
                  value={productDialog.data?.commission_type || 'fixed'} 
                  onValueChange={(value) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_type: value } })}
                >
                  <SelectTrigger data-testid="commission-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed">Fixed Percentage</SelectItem>
                    <SelectItem value="tiered">Tiered (Volume-based)</SelectItem>
                    <SelectItem value="custom">Custom (Per Partner)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {productDialog.data?.commission_type === 'fixed' && (
              <div>
                <Label>Commission Rate (%)</Label>
                <Input
                  type="number"
                  value={productDialog.data?.commission_rate || 0}
                  onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_rate: parseFloat(e.target.value) || 0 } })}
                  data-testid="product-commission-input"
                />
              </div>
            )}
            {productDialog.data?.commission_type === 'tiered' && (
              <div className="p-4 bg-slate-50 rounded-lg">
                <Label className="mb-2 block">Commission Tiers</Label>
                <p className="text-xs text-slate-500 mb-3">Define tiers based on total sales count. Example: 0-10 sales = 5%, 11-50 = 7%</p>
                <div className="space-y-2">
                  {(productDialog.data?.commission_tiers || []).map((tier, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <span className="text-slate-600">{tier.min_sales}-{tier.max_sales} sales:</span>
                      <span className="font-medium text-[#2a777a]">{tier.rate}%</span>
                      <Button 
                        size="sm" 
                        variant="ghost" 
                        onClick={() => {
                          const tiers = (productDialog.data?.commission_tiers || []).filter((_, i) => i !== idx);
                          setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_tiers: tiers } });
                        }}
                        className="h-6 w-6 p-0"
                      >
                        <Trash2 className="h-3 w-3 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-3">
                  <Input placeholder="Min" type="number" className="w-20" id="tier-min" />
                  <Input placeholder="Max" type="number" className="w-20" id="tier-max" />
                  <Input placeholder="Rate %" type="number" className="w-20" id="tier-rate" />
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => {
                      const min = document.getElementById('tier-min').value;
                      const max = document.getElementById('tier-max').value;
                      const rate = document.getElementById('tier-rate').value;
                      if (min && max && rate) {
                        const tiers = [...(productDialog.data?.commission_tiers || []), { min_sales: parseInt(min), max_sales: parseInt(max), rate: parseFloat(rate) }];
                        setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_tiers: tiers } });
                        document.getElementById('tier-min').value = '';
                        document.getElementById('tier-max').value = '';
                        document.getElementById('tier-rate').value = '';
                      }
                    }}
                  >
                    Add Tier
                  </Button>
                </div>
              </div>
            )}
            {productDialog.data?.commission_type === 'custom' && (
              <div className="p-4 bg-slate-50 rounded-lg">
                <Label className="mb-2 block">Custom Commission</Label>
                <p className="text-xs text-slate-500">Commission will be set individually for each partner in their profile settings.</p>
                <div className="mt-2">
                  <Label>Default Rate (%)</Label>
                  <Input
                    type="number"
                    value={productDialog.data?.commission_rate || 0}
                    onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_rate: parseFloat(e.target.value) || 0 } })}
                    data-testid="product-commission-default-input"
                  />
                </div>
              </div>
            )}
            <Button onClick={() => handleSaveProduct(productDialog.data)} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-product-btn">
              Save Product
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Workflow Editor Dialog */}
      <Dialog open={workflowDialog.open} onOpenChange={(open) => setWorkflowDialog({ ...workflowDialog, open })}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Workflow - {workflowDialog.product?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-slate-600">
                Define the steps for this product workflow. Each step can have required documents.
              </p>
              <Button onClick={() => openStepEditor('create')} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="add-step-btn">
                <Plus className="mr-2 h-4 w-4" />
                Add Step
              </Button>
            </div>

            {workflowDialog.product?.workflow_steps?.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed rounded-lg">
                <Settings className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-600">No workflow steps defined</p>
                <p className="text-sm text-slate-500">Click &quot;Add Step&quot; to create your first workflow step</p>
              </div>
            ) : (
              <div className="space-y-3">
                {workflowDialog.product?.workflow_steps?.sort((a, b) => a.step_order - b.step_order).map((step, idx) => (
                  <div key={idx} className="p-4 border rounded-lg bg-white shadow-sm" data-testid={`workflow-step-${idx}`}>
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-3 flex-1">
                        <span className="w-10 h-10 rounded-full bg-[#2a777a] text-white flex items-center justify-center font-bold">
                          {step.step_order}
                        </span>
                        <div className="flex-1">
                          <h4 className="font-semibold text-slate-800">{step.step_name}</h4>
                          {step.description && <p className="text-sm text-slate-600 mt-1">{step.description}</p>}
                          {step.duration_days && (
                            <p className="text-xs text-slate-500 mt-1">Duration: {step.duration_days} days</p>
                          )}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs font-medium text-slate-700">Required Documents:</p>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.required_documents.map((doc, docIdx) => (
                                  <Badge key={docIdx} variant="outline" className="text-xs">
                                    {doc.doc_name} {doc.is_mandatory && '*'}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => openStepEditor('edit', idx)} data-testid={`edit-step-${idx}`}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => deleteWorkflowStep(step.step_order)} data-testid={`delete-step-${idx}`}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Step Editor Dialog */}
      <Dialog open={stepEditorDialog.open} onOpenChange={(open) => setStepEditorDialog({ ...stepEditorDialog, open })}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{stepEditorDialog.mode === 'create' ? 'Add New' : 'Edit'} Workflow Step</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Step Name *</Label>
                <Input
                  value={stepEditorDialog.stepData.step_name}
                  onChange={(e) => setStepEditorDialog({
                    ...stepEditorDialog,
                    stepData: { ...stepEditorDialog.stepData, step_name: e.target.value }
                  })}
                  placeholder="e.g., Document Verification"
                  data-testid="step-name-input"
                />
              </div>
              <div>
                <Label>Step Order</Label>
                <Input
                  type="number"
                  value={stepEditorDialog.stepData.step_order}
                  onChange={(e) => setStepEditorDialog({
                    ...stepEditorDialog,
                    stepData: { ...stepEditorDialog.stepData, step_order: parseInt(e.target.value) || 1 }
                  })}
                  data-testid="step-order-input"
                />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={stepEditorDialog.stepData.description}
                onChange={(e) => setStepEditorDialog({
                  ...stepEditorDialog,
                  stepData: { ...stepEditorDialog.stepData, description: e.target.value }
                })}
                placeholder="Describe what happens in this step..."
                rows={2}
                data-testid="step-description-input"
              />
            </div>
            <div>
              <Label>Duration (days)</Label>
              <Input
                type="number"
                value={stepEditorDialog.stepData.duration_days}
                onChange={(e) => setStepEditorDialog({
                  ...stepEditorDialog,
                  stepData: { ...stepEditorDialog.stepData, duration_days: e.target.value }
                })}
                placeholder="Estimated days to complete"
                data-testid="step-duration-input"
              />
            </div>

            {/* Document Requirements Section */}
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3 text-slate-800">Document Requirements</h4>
              
              {stepEditorDialog.stepData.required_documents.length > 0 && (
                <div className="space-y-2 mb-4">
                  {stepEditorDialog.stepData.required_documents.map((doc, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-blue-50 rounded-lg">
                      <div>
                        <p className="font-medium text-slate-800">{doc.doc_name}</p>
                        <p className="text-xs text-slate-600">{doc.description}</p>
                        {doc.is_mandatory && <Badge className="mt-1 text-xs bg-red-100 text-red-700">Mandatory</Badge>}
                      </div>
                      <Button size="sm" variant="ghost" onClick={() => removeDocFromStep(idx)}>
                        <XCircle className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-sm">Document Name</Label>
                    <Input
                      value={stepEditorDialog.newDoc.doc_name}
                      onChange={(e) => setStepEditorDialog({
                        ...stepEditorDialog,
                        newDoc: { ...stepEditorDialog.newDoc, doc_name: e.target.value }
                      })}
                      placeholder="e.g., Passport Copy"
                      data-testid="doc-name-input"
                    />
                  </div>
                  <div>
                    <Label className="text-sm">Description</Label>
                    <Input
                      value={stepEditorDialog.newDoc.description}
                      onChange={(e) => setStepEditorDialog({
                        ...stepEditorDialog,
                        newDoc: { ...stepEditorDialog.newDoc, description: e.target.value }
                      })}
                      placeholder="Additional info..."
                      data-testid="doc-description-input"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={stepEditorDialog.newDoc.is_mandatory}
                      onChange={(e) => setStepEditorDialog({
                        ...stepEditorDialog,
                        newDoc: { ...stepEditorDialog.newDoc, is_mandatory: e.target.checked }
                      })}
                      className="rounded"
                      data-testid="doc-mandatory-checkbox"
                    />
                    Mandatory Document
                  </label>
                  <Button size="sm" onClick={addDocToStep} variant="outline" data-testid="add-doc-btn">
                    <Plus className="h-4 w-4 mr-1" />
                    Add Document
                  </Button>
                </div>
              </div>
            </div>

            <Button onClick={saveWorkflowStep} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-step-btn">
              {stepEditorDialog.mode === 'create' ? 'Add Step' : 'Update Step'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* User Dialog */}
      <Dialog open={userDialog.open} onOpenChange={(open) => setUserDialog({ ...userDialog, open })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{userDialog.mode === 'create' ? 'Create' : 'Edit'} User</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Name</Label>
              <Input
                value={userDialog.data?.name || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, name: e.target.value } })}
                data-testid="user-name-input"
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={userDialog.data?.email || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, email: e.target.value } })}
                data-testid="user-email-input"
              />
            </div>
            <div>
              <Label>Mobile</Label>
              <Input
                value={userDialog.data?.mobile || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, mobile: e.target.value } })}
                data-testid="user-mobile-input"
              />
            </div>
            <div>
              <Label>Role</Label>
              <Select 
                value={userDialog.data?.role || 'partner'} 
                onValueChange={(value) => setUserDialog({ ...userDialog, data: { ...userDialog.data, role: value } })}
              >
                <SelectTrigger data-testid="user-role-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="case_manager">Case Manager</SelectItem>
                  <SelectItem value="partner">Partner</SelectItem>
                  <SelectItem value="client">Client</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{userDialog.mode === 'edit' ? 'New Password (leave blank to keep)' : 'Password'}</Label>
              <Input
                type="password"
                value={userDialog.data?.password || ''}
                onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, password: e.target.value } })}
                data-testid="user-password-input"
              />
            </div>
            <Button onClick={() => handleSaveUser(userDialog.data)} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-user-btn">
              {userDialog.mode === 'create' ? 'Create User' : 'Update User'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Ticket Dialog */}
      <Dialog open={ticketDialog.open} onOpenChange={(open) => setTicketDialog({ ...ticketDialog, open })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Support Ticket</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Target User (Optional)</Label>
              <Select
                value={ticketDialog.target_user_id}
                onValueChange={(value) => setTicketDialog({ ...ticketDialog, target_user_id: value })}
              >
                <SelectTrigger data-testid="ticket-target-select">
                  <SelectValue placeholder="Select user or leave for all" />
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
                data-testid="ticket-subject-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Category</Label>
                <Select value={ticketDialog.category} onValueChange={(value) => setTicketDialog({ ...ticketDialog, category: value })}>
                  <SelectTrigger data-testid="ticket-category-select">
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
                  <SelectTrigger data-testid="ticket-priority-select">
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
                data-testid="ticket-description-input"
              />
            </div>
            <Button onClick={handleCreateTicket} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="create-ticket-btn">
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
              <SelectTrigger data-testid="reassign-manager-select">
                <SelectValue placeholder="Select new case manager" />
              </SelectTrigger>
              <SelectContent>
                {caseManagers.map((manager) => (
                  <SelectItem key={manager.id} value={manager.id}>{manager.name}</SelectItem>
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
