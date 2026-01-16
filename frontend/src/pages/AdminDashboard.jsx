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
  Download, Edit, Trash2, UserPlus, Eye, ArrowRight, Settings 
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
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);
  const [selectedSale, setSelectedSale] = useState(null);
  const [saleDocuments, setSaleDocuments] = useState([]);
  const [caseDocuments, setCaseDocuments] = useState([]);
  
  // Dialogs
  const [productDialog, setProductDialog] = useState({ open: false, mode: 'create', data: null });
  const [userDialog, setUserDialog] = useState({ open: false, mode: 'create', data: null });
  const [workflowDialog, setWorkflowDialog] = useState({ open: false, product_id: null, data: null });
  const [impersonateDialog, setImpersonateDialog] = useState({ open: false, user: null });
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
      const [statsRes, salesRes, casesRes, productsRes, usersRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, getAuthHeader()),
        axios.get(`${API}/sales/pending`, getAuthHeader()),
        axios.get(`${API}/cases`, getAuthHeader()),
        axios.get(`${API}/products`, getAuthHeader()),
        axios.get(`${API}/users`, getAuthHeader())
      ]);
      setStats(statsRes.data);
      setPendingSales(salesRes.data);
      setCases(casesRes.data);
      setProducts(productsRes.data);
      setAllUsers(usersRes.data);
      setCaseManagers(usersRes.data.filter(u => u.role === 'case_manager'));
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
      localStorage.setItem('impersonating', 'true');
      localStorage.setItem('admin_token', localStorage.getItem('token'));
      
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

  const handleSaveUser = async (userData) => {
    try {
      if (userDialog.mode === 'create') {
        await axios.post(`${API}/auth/register`, userData, getAuthHeader());
        toast.success('User created!');
      } else {
        await axios.put(`${API}/users/${userDialog.data.id}`, userData, getAuthHeader());
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

  const handleReassignCase = async (caseId, newManagerId) => {
    try {
      await axios.put(`${API}/cases/${caseId}/assign-manager`, null, {
        ...getAuthHeader(),
        params: { case_manager_id: newManagerId }
      });
      toast.success('Case manager reassigned!');
      setReassignDialog({ open: false, case_id: null });
      loadData();
    } catch (error) {
      toast.error('Failed to reassign case');
    }
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
              {activeTab === 'sale-docs' && `Sale Documents - ${selectedSale?.client_name}`}
              {activeTab === 'case-detail' && `Case Details - ${selectedCase?.case_id}`}
            </h2>
            <div className="flex items-center gap-3">
              <CreateTicket />
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
                        className="bg-[#51D0DE] hover:bg-[#51D0DE]/90"
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
                <h3 className="text-lg font-semibold mb-4">Uploaded Documents</h3>
                <div className="space-y-3">
                  {saleDocuments.map((doc, idx) => (
                    <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{doc.filename}</p>
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
                <Select onValueChange={(managerId) => handleApproveSale(selectedSale.id, 'approved', managerId)}>
                  <SelectTrigger className="flex-1">
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
              {cases.map((caseItem) => (
                <Card key={caseItem.id} className="p-6 cursor-pointer hover:shadow-md transition-shadow" onClick={() => viewCaseDetails(caseItem)}>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-[#33363B]">{caseItem.case_id}</h3>
                      <p className="text-sm text-gray-600">Client: {caseItem.client_name}</p>
                      <p className="text-sm text-gray-600">Product: {caseItem.product_name}</p>
                      <p className="text-sm text-gray-600">Case Manager: {caseItem.case_manager_name}</p>
                    </div>
                    <div className="text-right">
                      <Badge className="bg-[#A8B5A2]">{caseItem.current_step}</Badge>
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

          {/* Case Detail View */}
          {activeTab === 'case-detail' && selectedCase && (
            <div className="space-y-6">
              <Button onClick={() => setActiveTab('cases')} variant="outline">
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Back to Cases
              </Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Case Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Client</p>
                    <p className="font-medium">{selectedCase.client_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Email</p>
                    <p className="font-medium">{selectedCase.client_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Product</p>
                    <p className="font-medium">{selectedCase.product_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Case Manager</p>
                    <p className="font-medium">{selectedCase.case_manager_name}</p>
                  </div>
                </div>
              </Card>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Documents</h3>
                <div className="space-y-3">
                  {caseDocuments.map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{doc.filename}</p>
                        <p className="text-sm text-gray-600">Step: {doc.step_name}</p>
                      </div>
                      <div className="flex gap-2">
                        <Badge>{doc.status}</Badge>
                        <Button
                          onClick={() => downloadDocument(doc.id, doc.filename)}
                          size="sm"
                          variant="outline"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
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
                  className="bg-[#D3A96B] hover:bg-[#D3A96B]/90"
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
                        <p className="font-medium mb-2">Workflow Steps:</p>
                        <div className="space-y-2">
                          {product.workflow_steps.map((step, idx) => (
                            <div key={idx} className="text-sm p-2 bg-gray-50 rounded">
                              {step.step_order}. {step.step_name}
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
              <div className="flex justify-end">
                <Button
                  onClick={() => setUserDialog({ open: true, mode: 'create', data: { email: '', name: '', password: '', role: 'partner', mobile: '' } })}
                  className="bg-[#D3A96B] hover:bg-[#D3A96B]/90"
                >
                  <UserPlus className="mr-2 h-4 w-4" />
                  Create User
                </Button>
              </div>
              
              {['partner', 'case_manager', 'client'].map(role => (
                <Card key={role} className="p-6">
                  <h3 className="text-lg font-semibold mb-4 capitalize">
                    {role === 'case_manager' ? 'Case Managers' : `${role}s`}
                  </h3>
                  <div className="space-y-3">
                    {allUsers.filter(u => u.role === role).map((usr) => (
                      <div key={usr.id} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <p className="font-medium">{usr.name}</p>
                          <p className="text-sm text-gray-600">{usr.email}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleImpersonate(usr)}
                            size="sm"
                            className="bg-[#51D0DE] hover:bg-[#51D0DE]/90"
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
        </div>
      </main>

      {/* Product Dialog */}
      <Dialog open={productDialog.open} onOpenChange={(open) => setProductDialog({ ...productDialog, open })}>
        <DialogContent>
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
            <Button onClick={() => handleSaveProduct(productDialog.data)} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90">
              Save Product
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
            <Button onClick={() => handleSaveUser(userDialog.data)} className="w-full bg-[#A8B5A2] hover:bg-[#A8B5A2]/90">
              Save User
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
