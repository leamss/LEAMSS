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
import { Briefcase, FileText, DollarSign, LogOut, Plus, ArrowLeft, MessageSquare, Filter, Download, Menu, X } from 'lucide-react';
import DashboardShell from '@/components/DashboardShell';
import TicketSection from '@/components/TicketSection';
import QuickActions from '@/components/QuickActions';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PartnerDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({});
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [ticketFilter, setTicketFilter] = useState(null);
  const [showNewSaleDialog, setShowNewSaleDialog] = useState(false);
  const [commissionFilter, setCommissionFilter] = useState({ period: 'all' });
  const [filteredCommissions, setFilteredCommissions] = useState([]);
  const [initialTicketId, setInitialTicketId] = useState(null);
  const [newSale, setNewSale] = useState({
    client_name: '',
    client_email: '',
    client_mobile: '',
    product_id: '',
    fee_amount: 0,
    amount_received: 0,
    payment_method: 'bank_transfer',
    payment_reference: '',
    agreement_signed: true,
    currency: 'INR',
    promo_code: '',
    discount_percentage: 0
  });
  const [promoStatus, setPromoStatus] = useState({ validated: false, message: '', discount: null });
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
        axios.get(`${API}/stats/partner-dashboard`, authHeader),
        axios.get(`${API}/sales/my-sales`, authHeader),
        axios.get(`${API}/products`, authHeader)
      ]);
      setStats(statsRes.data);
      setSales(salesRes.data);
      setProducts(productsRes.data);
      // Initialize filtered commissions
      setFilteredCommissions(salesRes.data.filter(s => s.status === 'approved'));
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
    
    // Check if there's a ticket to open from notification click
    const storedTicketId = sessionStorage.getItem('openTicketId');
    if (storedTicketId) {
      setActiveTab('tickets');
      setInitialTicketId(storedTicketId);
      sessionStorage.removeItem('openTicketId');
    }
    
    // Check if there's a tab to open
    const storedTab = sessionStorage.getItem('activeTab');
    if (storedTab) {
      setActiveTab(storedTab);
      sessionStorage.removeItem('activeTab');
    }
  }, [navigate]);

  useEffect(() => {
    if (user) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Handle notification click - navigate to correct tab/item
  const handleNotificationClick = (notification) => {
    const type = notification.type || '';
    const relatedId = notification.related_id;
    
    if (type.includes('ticket')) {
      setActiveTab('tickets');
      setInitialTicketId(relatedId);
    } else if (type.includes('sale')) {
      setActiveTab('sales');
    } else if (type.includes('commission')) {
      setActiveTab('commission');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleValidatePromo = async () => {
    if (!newSale.promo_code.trim()) { setPromoStatus({ validated: false, message: '', discount: null }); return; }
    try {
      const res = await axios.post(`${API}/marketing/promo/validate`, { code: newSale.promo_code }, getAuthHeader());
      setPromoStatus({ validated: true, message: `Promo applied: ${res.data.discount_type === 'percentage' ? `${res.data.discount_value}% off` : `₹${res.data.discount_value} off`}`, discount: res.data });
      toast.success('Promo code applied!');
    } catch (e) {
      setPromoStatus({ validated: false, message: e.response?.data?.detail || 'Invalid promo code', discount: null });
      toast.error(e.response?.data?.detail || 'Invalid promo code');
    }
  };

  const getDiscountBreakdown = () => {
    const baseFee = newSale.fee_amount || 0;
    let promoDiscount = 0;
    if (promoStatus.validated && promoStatus.discount) {
      promoDiscount = promoStatus.discount.discount_type === 'percentage'
        ? Math.round(baseFee * (promoStatus.discount.discount_value / 100))
        : Math.min(promoStatus.discount.discount_value, baseFee);
    }
    const afterPromo = baseFee - promoDiscount;
    const additionalDiscount = newSale.discount_percentage > 0 ? Math.round(afterPromo * (newSale.discount_percentage / 100)) : 0;
    const finalFee = afterPromo - additionalDiscount;
    const totalDiscount = promoDiscount + additionalDiscount;
    return { baseFee, promoDiscount, afterPromo, additionalDiscount, finalFee, totalDiscount };
  };

  const handleCreateSale = async () => {
    try {
      const formData = new FormData();
      formData.append('client_name', newSale.client_name);
      formData.append('client_email', newSale.client_email);
      formData.append('client_mobile', newSale.client_mobile);
      formData.append('product_id', newSale.product_id);
      formData.append('fee_amount', newSale.fee_amount.toString());
      formData.append('amount_received', newSale.amount_received.toString());
      formData.append('payment_method', newSale.payment_method);
      formData.append('payment_reference', newSale.payment_reference);
      formData.append('agreement_signed', newSale.agreement_signed.toString());
      formData.append('currency', newSale.currency || 'INR');
      if (newSale.collection_deadline) {
        formData.append('collection_deadline', newSale.collection_deadline);
      }
      // Promo & Discount
      if (promoStatus.validated && newSale.promo_code.trim()) {
        formData.append('promo_code', newSale.promo_code.trim());
      }
      if (newSale.discount_percentage > 0) {
        formData.append('discount_percentage', newSale.discount_percentage.toString());
      }
      
      for (const [docType, file] of Object.entries(uploadFiles)) {
        if (file) {
          formData.append('documents', file);
        }
      }
      
      await axios.post(`${API}/sales`, formData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Sale created successfully! Proposal sent to client.');
      setShowNewSaleDialog(false);
      setNewSale({
        client_name: '', client_email: '', client_mobile: '',
        product_id: '', fee_amount: 0, amount_received: 0,
        payment_method: 'bank_transfer', payment_reference: '',
        agreement_signed: true, collection_deadline: '', currency: 'INR',
        promo_code: '', discount_percentage: 0
      });
      setPromoStatus({ validated: false, message: '', discount: null });
      setUploadFiles({ payment_receipt: null, agreement: null, passport: null });
      loadData();
    } catch (error) {
      console.error('Create sale error:', error);
      toast.error(error.response?.data?.detail || 'Failed to create sale');
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

  const partnerNavGroups = [
    { id: 'dashboard', icon: Briefcase, label: 'Dashboard', onClick: () => setActiveTab('dashboard') },
    { id: 'sales', icon: FileText, label: 'My Sales', onClick: () => setActiveTab('sales') },
    { id: 'commission', icon: DollarSign, label: 'Commission', onClick: () => setActiveTab('commission') },
    { id: 'tickets', icon: MessageSquare, label: 'Support', onClick: () => setActiveTab('tickets') },
  ];

  const partnerPageTitle = { dashboard: 'Dashboard', sales: 'My Sales', commission: 'Commission', tickets: 'Support' }[activeTab] || 'Dashboard';

  return (
    <DashboardShell
      user={user}
      roleLabel="Partner"
      navGroups={partnerNavGroups}
      activeTab={activeTab}
      pageTitle={partnerPageTitle}
      headerActions={
        (activeTab === 'sales' || activeTab === 'dashboard') && (
          <Button className="bg-[#f7620b] hover:bg-[#e55a09]" size="sm" onClick={() => setShowNewSaleDialog(true)} data-testid="new-sale-button">
            <Plus className="mr-2 h-4 w-4" /> New Sale
          </Button>
        )
      }
      onNotificationClick={handleNotificationClick}
      onLogout={handleLogout}
    >
      {/* New Sale Dialog */}
      <Dialog open={showNewSaleDialog} onOpenChange={setShowNewSaleDialog}>
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
                          setNewSale({ ...newSale, product_id: value, fee_amount: product?.fee || product?.base_fee || 0 });
                        }}>
                          <SelectTrigger data-testid="product-select">
                            <SelectValue placeholder="Select product" />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((product) => (
                              <SelectItem key={product.id} value={product.id}>
                                {product.name} - {product.base_fee ? `₹${product.base_fee.toLocaleString()}` : `$${product.fee}`}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Currency</Label>
                        <Select value={newSale.currency} onValueChange={(value) => setNewSale({ ...newSale, currency: value })}>
                          <SelectTrigger data-testid="currency-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="INR">INR (₹) - Indian Rupee</SelectItem>
                            <SelectItem value="USD">USD ($) - US Dollar</SelectItem>
                            <SelectItem value="AUD">AUD (A$) - Australian Dollar</SelectItem>
                            <SelectItem value="CAD">CAD (C$) - Canadian Dollar</SelectItem>
                            <SelectItem value="GBP">GBP (£) - British Pound</SelectItem>
                            <SelectItem value="EUR">EUR (€) - Euro</SelectItem>
                          </SelectContent>
                        </Select>
                        {newSale.currency !== 'INR' && (
                          <p className="text-xs text-amber-600 mt-1">Amount will be converted to INR at current exchange rate</p>
                        )}
                      </div>
                      <div>
                        <Label>Fee Amount ({newSale.currency || 'INR'})</Label>
                        <Input
                          type="number"
                          value={newSale.fee_amount}
                          onChange={(e) => setNewSale({ ...newSale, fee_amount: parseFloat(e.target.value) || 0 })}
                          data-testid="fee-amount-input"
                        />
                      </div>
                      <div>
                        <Label>Amount Received ({newSale.currency || 'INR'})</Label>
                        <Input
                          type="number"
                          value={newSale.amount_received}
                          onChange={(e) => setNewSale({ ...newSale, amount_received: parseFloat(e.target.value) || 0 })}
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
                      <div>
                        <Label>Collection Deadline</Label>
                        <Input
                          type="date"
                          value={newSale.collection_deadline || ''}
                          onChange={(e) => setNewSale({ ...newSale, collection_deadline: e.target.value })}
                          data-testid="collection-deadline-input"
                        />
                        <p className="text-xs text-slate-400 mt-1">When is the remaining balance expected?</p>
                      </div>
                    </div>
                    
                    {/* Promo Code & Discount Section */}
                    <div className="border-t pt-4">
                      <h4 className="font-semibold mb-3 text-slate-700">Promo Code & Discount</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Promo Code</Label>
                          <div className="flex gap-2">
                            <Input
                              value={newSale.promo_code}
                              onChange={(e) => { setNewSale({ ...newSale, promo_code: e.target.value.toUpperCase() }); setPromoStatus({ validated: false, message: '', discount: null }); }}
                              placeholder="e.g., SUMMER2026"
                              data-testid="promo-code-input"
                            />
                            <Button type="button" variant="outline" onClick={handleValidatePromo} className="shrink-0" data-testid="apply-promo-btn">Apply</Button>
                          </div>
                          {promoStatus.message && (
                            <p className={`text-xs mt-1 ${promoStatus.validated ? 'text-emerald-600' : 'text-red-500'}`} data-testid="promo-status">
                              {promoStatus.message}
                            </p>
                          )}
                        </div>
                        <div>
                          <Label>Additional Discount (%)</Label>
                          <Input
                            type="number" min="0" max="50" step="0.5"
                            value={newSale.discount_percentage}
                            onChange={(e) => setNewSale({ ...newSale, discount_percentage: parseFloat(e.target.value) || 0 })}
                            placeholder="0"
                            data-testid="discount-percentage-input"
                          />
                          <p className="text-xs text-slate-400 mt-1">Extra discount for this client (needs admin approval)</p>
                        </div>
                      </div>

                      {/* Price Breakdown */}
                      {(promoStatus.validated || newSale.discount_percentage > 0) && newSale.fee_amount > 0 && (() => {
                        const bd = getDiscountBreakdown();
                        return (
                          <div className="mt-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200" data-testid="price-breakdown">
                            <p className="text-sm font-semibold text-slate-700 mb-2">Price Breakdown</p>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between"><span className="text-slate-600">Original Fee</span><span>₹{bd.baseFee.toLocaleString()}</span></div>
                              {bd.promoDiscount > 0 && <div className="flex justify-between text-emerald-700"><span>Promo ({promoStatus.discount?.discount_type === 'percentage' ? `${promoStatus.discount.discount_value}%` : 'Flat'})</span><span>-₹{bd.promoDiscount.toLocaleString()}</span></div>}
                              {bd.additionalDiscount > 0 && <div className="flex justify-between text-emerald-700"><span>Additional Discount ({newSale.discount_percentage}%)</span><span>-₹{bd.additionalDiscount.toLocaleString()}</span></div>}
                              <div className="flex justify-between font-bold border-t pt-1 mt-1"><span>Final Fee</span><span className="text-[#2a777a]">₹{bd.finalFee.toLocaleString()}</span></div>
                              <p className="text-xs text-slate-500 mt-1">Client will receive a proposal with this pricing</p>
                            </div>
                          </div>
                        );
                      })()}
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

          {activeTab === 'dashboard' && (
            <div>
              {/* Quick Actions Widget */}
              <div className="mb-6">
                <QuickActions 
                  userRole="partner" 
                  onNavigate={(tab, filter) => {
                    setActiveTab(tab);
                    if (filter && tab === 'tickets') setTicketFilter(filter);
                  }} 
                />
              </div>

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
                  <p className="text-3xl font-bold text-slate-900 mt-2">₹{stats.total_commission?.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}) || 0}</p>
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
                      <p className="text-sm text-slate-600 mt-2">Product: {sale.product_name} <span className="text-xs text-slate-400 capitalize">({sale.product_category || 'N/A'})</span></p>
                      <div className="flex flex-wrap gap-4 mt-1 text-sm">
                        <span className="text-slate-600">Fee: <span className="font-semibold">₹{(sale.fee_amount || 0).toLocaleString()}</span></span>
                        <span className="text-green-700">Received: <span className="font-semibold">₹{(sale.amount_received || 0).toLocaleString()}</span></span>
                        {(sale.pending_amount || 0) > 0 && (
                          <span className="text-amber-700">Pending: <span className="font-semibold">₹{(sale.pending_amount || 0).toLocaleString()}</span></span>
                        )}
                        {sale.original_currency && sale.original_currency !== 'INR' && (
                          <span className="text-blue-600 text-xs">(Original: {sale.original_currency} {(sale.original_fee_amount || 0).toLocaleString()} @ {sale.exchange_rate_used})</span>
                        )}
                      </div>
                      {(sale.total_discount_amount || 0) > 0 && (
                        <div className="flex flex-wrap gap-3 mt-1 text-xs">
                          {sale.promo_code && <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200">Promo: {sale.promo_code} (-₹{(sale.promo_discount_amount || 0).toLocaleString()})</span>}
                          {(sale.additional_discount_percentage || 0) > 0 && <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">Additional: {sale.additional_discount_percentage}% (-₹{(sale.additional_discount_amount || 0).toLocaleString()})</span>}
                          <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full border border-amber-200">Total Savings: ₹{(sale.total_discount_amount || 0).toLocaleString()}</span>
                        </div>
                      )}
                      <p className="text-sm text-slate-600">Payment: {sale.payment_method} {sale.payment_reference ? `- ${sale.payment_reference}` : ''}</p>
                      {sale.rejection_reason && (
                        <p className="text-sm text-red-600 mt-1 bg-red-50 p-2 rounded">Rejection Reason: {sale.rejection_reason}</p>
                      )}
                      <p className="text-sm text-slate-500 mt-1">Created: {new Date(sale.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${getStatusBadgeClass(sale.status)}`}>
                        {sale.status}
                      </span>
                      {sale.status === 'approved' && (
                        <p className="text-sm text-emerald-600 font-semibold mt-2">
                          Commission ({sale.commission_rate}% of received): ₹{(sale.commission_amount || 0).toLocaleString()}
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
                    <Button onClick={async () => {
                      try {
                        const res = await axios.get(`${API}/reports/export/partner-sales`, { ...getAuthHeader(), responseType: 'blob' });
                        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
                        const a = document.createElement('a'); a.href = url; a.download = 'My_Sales_Report.pdf'; a.click();
                        window.URL.revokeObjectURL(url);
                      } catch (e) { toast.error('Failed to export PDF'); }
                    }} variant="outline" className="gap-2 text-red-600 border-red-200" data-testid="export-partner-pdf">
                      <FileText className="h-4 w-4" />
                      PDF Report
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-6 bg-gradient-to-br from-[#2a777a] to-[#236466] text-white">
                  <p className="text-sm opacity-80">Total Commission</p>
                  <p className="text-3xl font-bold mt-2">₹{filteredCommissions.reduce((sum, s) => sum + (s.commission_amount || 0), 0).toLocaleString()}</p>
                </Card>
                <Card className="p-6 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
                  <p className="text-sm opacity-80">Approved Sales</p>
                  <p className="text-3xl font-bold mt-2">{filteredCommissions.length}</p>
                </Card>
                <Card className="p-6 bg-gradient-to-br from-amber-500 to-amber-600 text-white">
                  <p className="text-sm opacity-80">Total Revenue Generated</p>
                  <p className="text-3xl font-bold mt-2">₹{filteredCommissions.reduce((sum, s) => sum + (s.fee_amount || 0), 0).toLocaleString()}</p>
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
                          <th className="text-right p-3">Amt Received</th>
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
                            <td className="p-3 text-right">₹{(sale.fee_amount || 0).toLocaleString()}</td>
                            <td className="p-3 text-right text-green-700">₹{(sale.amount_received || 0).toLocaleString()}</td>
                            <td className="p-3 text-right">{sale.commission_rate}%</td>
                            <td className="p-3 text-right font-bold text-emerald-600">₹{(sale.commission_amount || 0).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-slate-100 font-bold">
                          <td colSpan={6} className="p-3 text-right">Total:</td>
                          <td className="p-3 text-right text-emerald-600">₹{filteredCommissions.reduce((sum, s) => sum + (s.commission_amount || 0), 0).toLocaleString()}</td>
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
            <TicketSection initialTicketId={initialTicketId} initialFilter={ticketFilter} />
          )}
    </DashboardShell>
  );
};

export default PartnerDashboard;
