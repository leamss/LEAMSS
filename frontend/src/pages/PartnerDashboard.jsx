import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Briefcase, FileText, DollarSign, LogOut, Plus, ArrowLeft, MessageSquare } from 'lucide-react';
import NotificationBell from '@/components/NotificationBell';
import TicketSection from '@/components/TicketSection';

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

const PartnerDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showNewSaleDialog, setShowNewSaleDialog] = useState(false);
  const [commissionFilter, setCommissionFilter] = useState({ period: 'all' });
  const [filteredCommissions, setFilteredCommissions] = useState([]);
  const [newSale, setNewSale] = useState({
    client_name: '',
    client_email: '',
    client_mobile: '',
    product_id: '',
    fee_amount: 0,
    amount_received: 0,
    payment_method: 'bank_transfer',
    payment_reference: '',
    agreement_signed: true
  });
  const [uploadFiles, setUploadFiles] = useState({
    payment_receipt: null,
    agreement: null,
    passport: null
  });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  // Apply commission filter
  const applyCommissionFilter = () => {
    let filtered = sales.filter(s => s.status === 'approved');
    
    if (commissionFilter.period !== 'all') {
      const now = new Date();
      let startDate;
      
      switch (commissionFilter.period) {
        case 'weekly':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'monthly':
          startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
        case 'quarterly':
          startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
          break;
        case 'yearly':
          startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
          break;
        default:
          startDate = null;
      }
      
      if (startDate) {
        filtered = filtered.filter(s => new Date(s.created_at) >= startDate);
      }
    }
    
    setFilteredCommissions(filtered);
  };

  // Download commission CSV
  const downloadMyCommissions = () => {
    if (filteredCommissions.length === 0) {
      toast.error('No commissions to download');
      return;
    }
    
    const headers = ['Date', 'Client', 'Product', 'Fee Amount', 'Commission Rate', 'Commission'];
    const rows = filteredCommissions.map(s => [
      new Date(s.created_at).toLocaleDateString(),
      s.client_name,
      s.product_name,
      s.fee_amount,
      s.commission_rate + '%',
      s.commission_amount
    ]);
    
    // Add total row
    rows.push(['', '', '', '', 'TOTAL:', filteredCommissions.reduce((sum, s) => sum + (s.commission_amount || 0), 0).toFixed(2)]);
    
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `my_commissions_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Commission report downloaded!');
  };

  const loadData = async () => {
    try {
      const authHeader = getAuthHeader();
      const [statsRes, salesRes, productsRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, authHeader),
        axios.get(`${API}/sales`, authHeader),
        axios.get(`${API}/products`, authHeader)
      ]);
      setStats(statsRes.data);
      setSales(salesRes.data);
      setProducts(productsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData || userData.role !== 'partner') {
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

  const handleCreateSale = async () => {
    try {
      const response = await axios.post(`${API}/sales`, newSale, getAuthHeader());
      const saleId = response.data.id;
      
      for (const [docType, file] of Object.entries(uploadFiles)) {
        if (file) {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('document_type', docType);
          await axios.post(`${API}/sales/${saleId}/upload-document`, formData, getAuthHeader());
        }
      }
      
      toast.success('Sale created successfully!');
      setShowNewSaleDialog(false);
      setNewSale({
        client_name: '',
        client_email: '',
        client_mobile: '',
        product_id: '',
        fee_amount: 0,
        amount_received: 0,
        payment_method: 'bank_transfer',
        payment_reference: '',
        agreement_signed: true
      });
      setUploadFiles({ payment_receipt: null, agreement: null, passport: null });
      loadData();
    } catch (error) {
      toast.error('Failed to create sale');
    }
  };

  const getStatusBadgeClass = (status) => {
    const classes = {
      pending: 'bg-amber-50 text-amber-700 border-amber-200',
      approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      rejected: 'bg-red-50 text-red-700 border-red-200'
    };
    return classes[status] || 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="flex min-h-screen bg-[#F5F7FA]" data-testid="partner-dashboard">
      <AdminReturnBanner />
      
      {/* Modern White Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col fixed h-screen" data-testid="sidebar">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-[#2a777a] flex items-center justify-center">
              <span className="text-white font-bold text-lg">L</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-800">LEAMSS</h1>
              <p className="text-xs text-slate-500">Partner Portal</p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'dashboard' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-dashboard"
          >
            <Briefcase className="h-5 w-5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('sales')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'sales' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-sales"
          >
            <FileText className="h-5 w-5" />
            <span>My Sales</span>
          </button>
          <button
            onClick={() => setActiveTab('commission')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'commission' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-commission"
          >
            <DollarSign className="h-5 w-5" />
            <span>Commission</span>
          </button>
          <button
            onClick={() => setActiveTab('tickets')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
              activeTab === 'tickets' 
                ? 'bg-teal-50 text-[#2a777a]' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            data-testid="nav-tickets"
          >
            <MessageSquare className="h-5 w-5" />
            <span>Support</span>
          </button>
        </nav>
        
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2 mb-3">
            <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center">
              <span className="text-slate-600 font-medium text-sm">{user?.name?.charAt(0) || 'P'}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="w-full justify-start text-slate-600 hover:text-slate-800 hover:bg-slate-50"
            data-testid="logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>

      <main className="flex-1 ml-64">
        {/* Header */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 py-4">
          <div className="flex justify-between items-center max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold text-slate-800">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'sales' && 'My Sales'}
              {activeTab === 'commission' && 'Commission'}
              {activeTab === 'tickets' && 'Support'}
            </h2>
            
            <div className="flex items-center gap-3">
              <NotificationBell />
            {(activeTab === 'sales' || activeTab === 'dashboard') && (
              <Dialog open={showNewSaleDialog} onOpenChange={setShowNewSaleDialog}>
                <DialogTrigger asChild>
                  <Button className="bg-[#f7620b] hover:bg-[#e55a09]" data-testid="new-sale-button">
                    <Plus className="mr-2 h-4 w-4" />
                    New Sale
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Create New Sale</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Client Name</Label>
                        <Input
                          value={newSale.client_name}
                          onChange={(e) => setNewSale({ ...newSale, client_name: e.target.value })}
                          data-testid="client-name-input"
                        />
                      </div>
                      <div>
                        <Label>Client Email</Label>
                        <Input
                          type="email"
                          value={newSale.client_email}
                          onChange={(e) => setNewSale({ ...newSale, client_email: e.target.value })}
                          data-testid="client-email-input"
                        />
                      </div>
                      <div>
                        <Label>Client Mobile</Label>
                        <Input
                          value={newSale.client_mobile}
                          onChange={(e) => setNewSale({ ...newSale, client_mobile: e.target.value })}
                          data-testid="client-mobile-input"
                        />
                      </div>
                      <div>
                        <Label>Product</Label>
                        <Select value={newSale.product_id} onValueChange={(value) => {
                          const product = products.find(p => p.id === value);
                          setNewSale({ ...newSale, product_id: value, fee_amount: product?.fee || 0 });
                        }}>
                          <SelectTrigger data-testid="product-select">
                            <SelectValue placeholder="Select product" />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((product) => (
                              <SelectItem key={product.id} value={product.id}>
                                {product.name} - ${product.fee}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Fee Amount</Label>
                        <Input
                          type="number"
                          value={newSale.fee_amount}
                          onChange={(e) => setNewSale({ ...newSale, fee_amount: parseFloat(e.target.value) })}
                          data-testid="fee-amount-input"
                        />
                      </div>
                      <div>
                        <Label>Amount Received</Label>
                        <Input
                          type="number"
                          value={newSale.amount_received}
                          onChange={(e) => setNewSale({ ...newSale, amount_received: parseFloat(e.target.value) })}
                          data-testid="amount-received-input"
                        />
                      </div>
                      <div>
                        <Label>Payment Method</Label>
                        <Select value={newSale.payment_method} onValueChange={(value) => setNewSale({ ...newSale, payment_method: value })}>
                          <SelectTrigger data-testid="payment-method-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                            <SelectItem value="cash">Cash</SelectItem>
                            <SelectItem value="check">Check</SelectItem>
                            <SelectItem value="online">Online Payment</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Payment Reference</Label>
                        <Input
                          value={newSale.payment_reference}
                          onChange={(e) => setNewSale({ ...newSale, payment_reference: e.target.value })}
                          data-testid="payment-reference-input"
                        />
                      </div>
                    </div>
                    
                    <div className="border-t pt-4">
                      <h4 className="font-semibold mb-4">Required Documents</h4>
                      <div className="space-y-3">
                        <div>
                          <Label>Payment Receipt</Label>
                          <Input
                            type="file"
                            accept=".pdf,.jpg,.png"
                            onChange={(e) => setUploadFiles({ ...uploadFiles, payment_receipt: e.target.files[0] })}
                            data-testid="payment-receipt-input"
                          />
                        </div>
                        <div>
                          <Label>Signed Agreement</Label>
                          <Input
                            type="file"
                            accept=".pdf,.jpg,.png"
                            onChange={(e) => setUploadFiles({ ...uploadFiles, agreement: e.target.files[0] })}
                            data-testid="agreement-input"
                          />
                        </div>
                        <div>
                          <Label>Client Passport</Label>
                          <Input
                            type="file"
                            accept=".pdf,.jpg,.png"
                            onChange={(e) => setUploadFiles({ ...uploadFiles, passport: e.target.files[0] })}
                            data-testid="passport-input"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <Button onClick={handleCreateSale} className="w-full bg-slate-900" data-testid="submit-sale-button">
                    Create Sale
                  </Button>
                </DialogContent>
              </Dialog>
            )}
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-8">
          <div className="max-w-7xl mx-auto">
          {activeTab === 'dashboard' && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" data-testid="partner-stats">
                <Card className="p-6 border-l-4 border-l-[#2a777a]">
                  <p className="text-sm text-slate-600 font-medium">Total Sales</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{stats.total_sales || 0}</p>
                </Card>
                <Card className="p-6 border-l-4 border-l-[#2a777a]">
                  <p className="text-sm text-slate-600 font-medium">Approved Sales</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{stats.approved_sales || 0}</p>
                </Card>
                <Card className="p-6 border-l-4 border-l-[#f7620b]">
                  <p className="text-sm text-slate-600 font-medium">Total Commission</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">${stats.total_commission?.toFixed(2) || 0}</p>
                </Card>
              </div>
              
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Recent Sales</h3>
                <div className="space-y-3">
                  {sales.slice(0, 5).map((sale) => (
                    <div key={sale.id} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{sale.client_name}</p>
                        <p className="text-sm text-slate-600">{sale.product_name}</p>
                      </div>
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${getStatusBadgeClass(sale.status)}`}>
                        {sale.status}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'sales' && (
            <div className="space-y-4" data-testid="sales-list">
              {sales.map((sale) => (
                <Card key={sale.id} className="p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold">{sale.client_name}</h3>
                      <p className="text-sm text-slate-600">{sale.client_email} | {sale.client_mobile}</p>
                      <p className="text-sm text-slate-600 mt-2">Product: {sale.product_name}</p>
                      <p className="text-sm text-slate-600">Fee: ${sale.fee_amount} | Received: ${sale.amount_received}</p>
                      <p className="text-sm text-slate-600">Payment: {sale.payment_method} - {sale.payment_reference}</p>
                      <p className="text-sm text-slate-500 mt-1">Created: {new Date(sale.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${getStatusBadgeClass(sale.status)}`}>
                        {sale.status}
                      </span>
                      {sale.status === 'approved' && (
                        <p className="text-sm text-emerald-600 font-semibold mt-2">
                          Commission: ${sale.commission_amount.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
              {sales.length === 0 && (
                <p className="text-center text-slate-500 py-12">No sales yet. Create your first sale!</p>
              )}
            </div>
          )}

          {activeTab === 'commission' && (
            <div className="space-y-6" data-testid="commission-list">
              {/* Filters */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Filter className="h-4 w-4 text-slate-500" />
                  <span className="text-sm font-medium text-slate-700">Filter Commissions</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Select value={commissionFilter.period} onValueChange={(v) => setCommissionFilter({ ...commissionFilter, period: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Period" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Time</SelectItem>
                      <SelectItem value="weekly">This Week</SelectItem>
                      <SelectItem value="monthly">This Month</SelectItem>
                      <SelectItem value="quarterly">This Quarter</SelectItem>
                      <SelectItem value="yearly">This Year</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="flex items-end gap-2 md:col-span-2">
                    <Button onClick={applyCommissionFilter} variant="outline" className="text-[#2a777a] border-[#2a777a]">
                      Apply Filter
                    </Button>
                    <Button onClick={downloadMyCommissions} variant="outline" className="gap-2">
                      <Download className="h-4 w-4" />
                      Download CSV
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-6 bg-gradient-to-br from-[#2a777a] to-[#236466] text-white">
                  <p className="text-sm opacity-80">Total Commission</p>
                  <p className="text-3xl font-bold mt-2">${filteredCommissions.reduce((sum, s) => sum + (s.commission_amount || 0), 0).toFixed(2)}</p>
                </Card>
                <Card className="p-6 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
                  <p className="text-sm opacity-80">Approved Sales</p>
                  <p className="text-3xl font-bold mt-2">{filteredCommissions.length}</p>
                </Card>
                <Card className="p-6 bg-gradient-to-br from-amber-500 to-amber-600 text-white">
                  <p className="text-sm opacity-80">Total Revenue Generated</p>
                  <p className="text-3xl font-bold mt-2">${filteredCommissions.reduce((sum, s) => sum + (s.fee_amount || 0), 0).toFixed(2)}</p>
                </Card>
              </div>
              
              {/* Commission List */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Commission Details</h3>
                {filteredCommissions.length === 0 ? (
                  <p className="text-center text-slate-500 py-8">No commissions found for the selected period.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 border-b">
                          <th className="text-left p-3">Date</th>
                          <th className="text-left p-3">Client</th>
                          <th className="text-left p-3">Product</th>
                          <th className="text-right p-3">Fee Amount</th>
                          <th className="text-right p-3">Rate</th>
                          <th className="text-right p-3">Commission</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredCommissions.map((sale) => (
                          <tr key={sale.id} className="border-b hover:bg-slate-50">
                            <td className="p-3">{new Date(sale.created_at).toLocaleDateString()}</td>
                            <td className="p-3 font-medium">{sale.client_name}</td>
                            <td className="p-3">{sale.product_name}</td>
                            <td className="p-3 text-right">${sale.fee_amount?.toFixed(2)}</td>
                            <td className="p-3 text-right">{sale.commission_rate}%</td>
                            <td className="p-3 text-right font-bold text-emerald-600">${sale.commission_amount?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-slate-100 font-bold">
                          <td colSpan={5} className="p-3 text-right">Total:</td>
                          <td className="p-3 text-right text-emerald-600">${filteredCommissions.reduce((sum, s) => sum + (s.commission_amount || 0), 0).toFixed(2)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Tickets Section */}
          {activeTab === 'tickets' && (
            <TicketSection />
          )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default PartnerDashboard;
