import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import NotificationBell from '@/components/NotificationBell';
import CreateTicket from '@/components/CreateTicket';
import { LayoutDashboard, FileText, Users, Briefcase, LogOut, Plus, Download } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [pendingSales, setPendingSales] = useState([]);
  const [cases, setCases] = useState([]);
  const [products, setProducts] = useState([]);
  const [caseManagers, setCaseManagers] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseDocuments, setCaseDocuments] = useState([]);
  const [newProduct, setNewProduct] = useState({ name: '', description: '', fee: 0, commission_rate: 0 });
  const [newUser, setNewUser] = useState({ email: '', name: '', password: '', role: 'case_manager', mobile: '' });
  const [newStep, setNewStep] = useState({ product_id: '', step_name: '', step_order: 1, description: '', duration_days: null, required_documents: [] });
  const [newDocRequirement, setNewDocRequirement] = useState({ doc_name: '', description: '', is_mandatory: true });

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
      const [statsRes, salesRes, casesRes, productsRes, managersRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, getAuthHeader()),
        axios.get(`${API}/sales/pending`, getAuthHeader()),
        axios.get(`${API}/cases`, getAuthHeader()),
        axios.get(`${API}/products`, getAuthHeader()),
        axios.get(`${API}/users/case-managers`, getAuthHeader())
      ]);
      setStats(statsRes.data);
      setPendingSales(salesRes.data);
      setCases(casesRes.data);
      setProducts(productsRes.data);
      setCaseManagers(managersRes.data);
    } catch (error) {
      toast.error('Failed to load data');
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

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleApproveSale = async (saleId, status, caseManagerId) => {
    try {
      await axios.post(`${API}/sales/approve`, { sale_id: saleId, status, case_manager_id: caseManagerId }, getAuthHeader());
      toast.success(`Sale ${status}!`);
      loadData();
    } catch (error) {
      toast.error('Failed to update sale');
    }
  };

  const handleCreateProduct = async () => {
    try {
      await axios.post(`${API}/products`, newProduct, getAuthHeader());
      toast.success('Product created!');
      setNewProduct({ name: '', description: '', fee: 0, commission_rate: 0 });
      loadData();
    } catch (error) {
      toast.error('Failed to create product');
    }
  };

  const handleCreateUser = async () => {
    try {
      await axios.post(`${API}/auth/register`, newUser, getAuthHeader());
      toast.success('User created!');
      setNewUser({ email: '', name: '', password: '', role: 'case_manager', mobile: '' });
      loadData();
    } catch (error) {
      toast.error('Failed to create user');
    }
  };

  const handleAddWorkflowStep = async () => {
    try {
      await axios.post(`${API}/products/workflow-step`, {
        ...newStep,
        required_documents: newStep.required_documents || []
      }, getAuthHeader());
      toast.success('Workflow step added!');
      setNewStep({ product_id: '', step_name: '', step_order: 1, description: '', duration_days: null, required_documents: [] });
      loadData();
    } catch (error) {
      toast.error('Failed to add workflow step');
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-64 bg-slate-900 text-white p-6 flex flex-col" data-testid="admin-sidebar">
        <div className="flex items-center gap-2 mb-8">
          <Briefcase className="h-8 w-8 text-emerald-400" />
          <h1 className="text-xl font-bold" style={{ fontFamily: 'Poppins, serif' }}>LEAMSS Admin</h1>
        </div>
        
        <nav className="flex-1 space-y-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'dashboard' ? 'bg-emerald-600' : 'hover:bg-slate-800'
            }`}
            data-testid="nav-dashboard"
          >
            <LayoutDashboard className="h-5 w-5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('sales')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'sales' ? 'bg-blue-600' : 'hover:bg-slate-800'
            }`}
            data-testid="nav-sales"
          >
            <FileText className="h-5 w-5" />
            <span>Pending Sales</span>
          </button>
          <button
            onClick={() => setActiveTab('cases')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'cases' ? 'bg-blue-600' : 'hover:bg-slate-800'
            }`}
            data-testid="nav-cases"
          >
            <Briefcase className="h-5 w-5" />
            <span>All Cases</span>
          </button>
          <button
            onClick={() => setActiveTab('products')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'products' ? 'bg-blue-600' : 'hover:bg-slate-800'
            }`}
            data-testid="nav-products"
          >
            <Plus className="h-5 w-5" />
            <span>Products</span>
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
              activeTab === 'users' ? 'bg-blue-600' : 'hover:bg-slate-800'
            }`}
            data-testid="nav-users"
          >
            <Users className="h-5 w-5" />
            <span>Users</span>
          </button>
        </nav>
        
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-white hover:bg-slate-800 mt-4"
          data-testid="logout-button"
        >
          <LogOut className="mr-2 h-5 w-5" />
          Logout
        </Button>
      </aside>

      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold mb-8" style={{ fontFamily: 'Merriweather, serif' }}>
            {activeTab === 'dashboard' && 'Dashboard'}
            {activeTab === 'sales' && 'Pending Sales Approval'}
            {activeTab === 'cases' && 'All Cases'}
            {activeTab === 'products' && 'Products & Workflows'}
            {activeTab === 'users' && 'User Management'}
          </h2>

          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="dashboard-stats">
              <Card className="p-6 border-l-4 border-l-amber-500">
                <p className="text-sm text-slate-600 font-medium">Pending Sales</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats.pending_sales || 0}</p>
              </Card>
              <Card className="p-6 border-l-4 border-l-blue-600">
                <p className="text-sm text-slate-600 font-medium">Active Cases</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats.active_cases || 0}</p>
              </Card>
              <Card className="p-6 border-l-4 border-l-emerald-600">
                <p className="text-sm text-slate-600 font-medium">Total Revenue</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">${stats.total_revenue?.toFixed(2) || 0}</p>
              </Card>
            </div>
          )}

          {activeTab === 'sales' && (
            <div className="space-y-4" data-testid="pending-sales-list">
              {pendingSales.map((sale) => (
                <Card key={sale.id} className="p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold">{sale.client_name}</h3>
                      <p className="text-sm text-slate-600">{sale.client_email}</p>
                      <p className="text-sm text-slate-600 mt-2">Product: {sale.product_name}</p>
                      <p className="text-sm text-slate-600">Fee: ${sale.fee_amount}</p>
                      <p className="text-sm text-slate-600">Partner: {sale.partner_name}</p>
                    </div>
                    <div className="flex flex-col gap-2">
                      <Select onValueChange={(managerId) => handleApproveSale(sale.id, 'approved', managerId)}>
                        <SelectTrigger className="w-48" data-testid={`approve-sale-${sale.id}`}>
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
              ))}
              {pendingSales.length === 0 && (
                <p className="text-center text-slate-500 py-12">No pending sales</p>
              )}
            </div>
          )}

          {activeTab === 'cases' && (
            <div className="space-y-4" data-testid="all-cases-list">
              {cases.map((caseItem) => (
                <Card key={caseItem.id} className="p-6">
                  <div className="flex justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">{caseItem.case_id}</h3>
                      <p className="text-sm text-slate-600">Client: {caseItem.client_name}</p>
                      <p className="text-sm text-slate-600">Product: {caseItem.product_name}</p>
                      <p className="text-sm text-slate-600">Case Manager: {caseItem.case_manager_name}</p>
                    </div>
                    <div className="text-right">
                      <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                        {caseItem.current_step}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {activeTab === 'products' && (
            <div className="space-y-8">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Create New Product</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Product Name</Label>
                    <Input
                      value={newProduct.name}
                      onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                      placeholder="e.g., Australia PR - Skilled Route"
                      data-testid="product-name-input"
                    />
                  </div>
                  <div>
                    <Label>Fee Amount</Label>
                    <Input
                      type="number"
                      value={newProduct.fee}
                      onChange={(e) => setNewProduct({ ...newProduct, fee: parseFloat(e.target.value) })}
                      data-testid="product-fee-input"
                    />
                  </div>
                  <div>
                    <Label>Commission Rate (%)</Label>
                    <Input
                      type="number"
                      value={newProduct.commission_rate}
                      onChange={(e) => setNewProduct({ ...newProduct, commission_rate: parseFloat(e.target.value) })}
                      data-testid="product-commission-input"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label>Description</Label>
                    <Input
                      value={newProduct.description}
                      onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                      data-testid="product-description-input"
                    />
                  </div>
                </div>
                <Button onClick={handleCreateProduct} className="mt-4 bg-slate-900" data-testid="create-product-button">
                  Create Product
                </Button>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Add Workflow Step</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Select Product</Label>
                    <Select value={newStep.product_id} onValueChange={(value) => setNewStep({ ...newStep, product_id: value })}>
                      <SelectTrigger data-testid="step-product-select">
                        <SelectValue placeholder="Select product" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Step Name</Label>
                    <Input
                      value={newStep.step_name}
                      onChange={(e) => setNewStep({ ...newStep, step_name: e.target.value })}
                      placeholder="e.g., Document Verification"
                      data-testid="step-name-input"
                    />
                  </div>
                  <div>
                    <Label>Step Order</Label>
                    <Input
                      type="number"
                      value={newStep.step_order}
                      onChange={(e) => setNewStep({ ...newStep, step_order: parseInt(e.target.value) })}
                      data-testid="step-order-input"
                    />
                  </div>
                </div>
                <Button onClick={handleAddWorkflowStep} className="mt-4 bg-slate-900" data-testid="add-step-button">
                  Add Workflow Step
                </Button>
              </Card>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Existing Products</h3>
                {products.map((product) => (
                  <Card key={product.id} className="p-6">
                    <h4 className="font-semibold text-lg">{product.name}</h4>
                    <p className="text-sm text-slate-600">{product.description}</p>
                    <p className="text-sm text-slate-600 mt-2">Fee: ${product.fee} | Commission: {product.commission_rate}%</p>
                    {product.workflow_steps && product.workflow_steps.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm font-medium mb-2">Workflow Steps:</p>
                        <div className="space-y-1">
                          {product.workflow_steps.map((step, idx) => (
                            <div key={idx} className="text-sm text-slate-600 pl-4">
                              {step.step_order}. {step.step_name}
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

          {activeTab === 'users' && (
            <div className="space-y-8">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Create New User</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={newUser.name}
                      onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                      data-testid="user-name-input"
                    />
                  </div>
                  <div>
                    <Label>Email</Label>
                    <Input
                      type="email"
                      value={newUser.email}
                      onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                      data-testid="user-email-input"
                    />
                  </div>
                  <div>
                    <Label>Password</Label>
                    <Input
                      type="password"
                      value={newUser.password}
                      onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                      data-testid="user-password-input"
                    />
                  </div>
                  <div>
                    <Label>Mobile</Label>
                    <Input
                      value={newUser.mobile}
                      onChange={(e) => setNewUser({ ...newUser, mobile: e.target.value })}
                      data-testid="user-mobile-input"
                    />
                  </div>
                  <div>
                    <Label>Role</Label>
                    <Select value={newUser.role} onValueChange={(value) => setNewUser({ ...newUser, role: value })}>
                      <SelectTrigger data-testid="user-role-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="case_manager">Case Manager</SelectItem>
                        <SelectItem value="partner">Partner</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button onClick={handleCreateUser} className="mt-4 bg-slate-900" data-testid="create-user-button">
                  Create User
                </Button>
              </Card>

              <div>
                <h3 className="text-lg font-semibold mb-4">Case Managers</h3>
                <div className="space-y-4">
                  {caseManagers.map((manager) => (
                    <Card key={manager.id} className="p-4">
                      <p className="font-semibold">{manager.name}</p>
                      <p className="text-sm text-slate-600">{manager.email}</p>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default AdminDashboard;
