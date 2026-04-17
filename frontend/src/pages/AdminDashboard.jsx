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
import DashboardShell from '@/components/DashboardShell';
import QuickActions from '@/components/QuickActions';
import { 
  LayoutDashboard, FileText, Users, Briefcase, LogOut, Plus, User, 
  Download, Edit, Trash2, UserPlus, Eye, ArrowRight, Settings,
  Search, DollarSign, TrendingUp, CheckCircle, XCircle, Clock,
  MessageSquare, Filter, Calendar, RefreshCw, AlertTriangle, Copy, Mail, Gift,
  Menu, X, Bell, Loader2, CreditCard, BarChart3, Activity, Megaphone,
  ArrowRightLeft, Zap, BookOpen, Star, UserCheck, ClipboardList, Sparkles, Calculator
} from 'lucide-react';
import BulkOperations from '@/pages/BulkOperations';
import SLATracker from '@/pages/SLATracker';
import CaseTransfer from '@/pages/CaseTransfer';
import SatisfactionSurvey from '@/pages/SatisfactionSurvey';
import KnowledgeBase from '@/pages/KnowledgeBase';
import RevenueForecasting from '@/pages/RevenueForecasting';
import CMPerformance from '@/pages/CMPerformance';
import Appointments from '@/pages/Appointments';
import CaseTimeline from '@/pages/CaseTimeline';
import CaseNotesAndTags from '@/pages/CaseNotesAndTags';
import CannedResponses from '@/pages/CannedResponses';
import ReferralProgram from '@/pages/ReferralProgram';
import ClientGreetings from '@/pages/ClientGreetings';
import ConversionFunnel from '@/pages/ConversionFunnel';
import CountryProductAnalytics from '@/pages/CountryProductAnalytics';
import CommissionAnalytics from '@/pages/CommissionAnalytics';
import PreAssessmentQueue from '@/components/PreAssessmentQueue';
import HappinessScoreWidget from '@/components/HappinessScoreWidget';
import ApprovalCenter from '@/components/ApprovalCenter';
import FeeCalculator from '@/components/FeeCalculator';
import RefundManager from '@/components/RefundManager';
import RevenueDashboard from '@/components/RevenueDashboard';
import { DeadlineOverviewWidget } from '@/components/DeadlineTracker';
import IntakeFormBuilder from '@/components/IntakeFormBuilder';
import ReportBuilder from '@/components/ReportBuilder';
import EmailDigest from '@/components/EmailDigest';
import PaymentReminders from '@/components/PaymentReminders';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ClientInfoSheetSection = ({ caseId }) => {
  const [infoSheet, setInfoSheet] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!caseId) return;
    const fetchInfoSheet = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API}/cases/${caseId}/information-sheet`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.data?.exists) setInfoSheet(res.data.data);
      } catch (e) { /* no info sheet */ }
      setLoading(false);
    };
    fetchInfoSheet();
  }, [caseId, token]);

  if (loading) return <Card className="p-6"><p className="text-slate-500 text-sm">Loading info sheet...</p></Card>;

  return (
    <Card className="p-6" data-testid="admin-info-sheet-section">
      <h3 className="text-lg font-semibold mb-4 text-slate-800 flex items-center gap-2">
        <User className="h-5 w-5 text-[#2a777a]" />
        Client Information Sheet
      </h3>
      {infoSheet ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(infoSheet).filter(([key]) =>
            !['id', 'case_id', 'client_id', 'created_at', 'updated_at', '_id'].includes(key)
          ).map(([key, value]) => (
            <div key={key} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-xs text-slate-500 capitalize font-medium">{key.replace(/_/g, ' ')}</p>
              <p className="text-sm font-medium text-slate-800 mt-1">{value || 'N/A'}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-6 bg-slate-50 rounded-lg">
          <User className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">No information sheet submitted for this case</p>
        </div>
      )}
    </Card>
  );
};

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
  const [salesStatusFilter, setSalesStatusFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);
  const [selectedSale, setSelectedSale] = useState(null);
  const [saleDocuments, setSaleDocuments] = useState([]);
  const [caseDocuments, setCaseDocuments] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [userSearchTerm, setUserSearchTerm] = useState('');
  const [caseFilter, setCaseFilter] = useState({ search: '', case_manager_id: '', status: '' });
  
  // New state for sales reports
  const [salesReport, setSalesReport] = useState([]);
  const [partnerCommissions, setPartnerCommissions] = useState([]);
  const [salesFilter, setSalesFilter] = useState({ partner_id: '', period: 'lifetime', date_from: '', date_to: '' });
  const [commissionFilter, setCommissionFilter] = useState({ period: 'lifetime', date_from: '', date_to: '' });
  const [selectedPartnerReport, setSelectedPartnerReport] = useState(null);
  
  // New state for tickets
  const [allTickets, setAllTickets] = useState([]);
  const [ticketStats, setTicketStats] = useState({});
  const [ticketFilter, setTicketFilter] = useState({ status: '', priority: '', created_by_role: '' });
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketReplyText, setTicketReplyText] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  
  // Expiring documents state
  const [expiringDocuments, setExpiringDocuments] = useState([]);
  
  // System Settings
  const [systemSettings, setSystemSettings] = useState({ allow_case_manager_workflow_customization: false });
  
  // Payment Tracker
  const [paymentTracker, setPaymentTracker] = useState({ summary: {}, items: [] });
  
  // Currency settings
  const [exchangeRate, setExchangeRate] = useState(83.50);
  const [showINR, setShowINR] = useState(false);
  
  // Refunds
  const [refundDialog, setRefundDialog] = useState({ open: false, sale_id: null, amount: 0, reason: '', refund_method: 'original_payment', notes: '' });
  const [refunds, setRefunds] = useState([]);

  // Custom per-partner product commissions
  const [customCommissions, setCustomCommissions] = useState([]);
  const [newCustomCommission, setNewCustomCommission] = useState({ partner_id: '', product_id: '', commission_rate: 0 });
  
  // Dialogs
  const [productDialog, setProductDialog] = useState({ open: false, mode: 'create', data: null });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [workflowDialog, setWorkflowDialog] = useState({ open: false, product: null, editingStepIndex: null });
  const [stepEditorDialog, setStepEditorDialog] = useState({
    open: false,
    mode: 'create',
    stepData: { step_name: '', step_order: 1, description: '', duration_days: '', required_documents: [] },
    newDoc: { doc_name: '', description: '', is_mandatory: true, has_expiry: false, expiry_date: '', validity_months: '', doc_type: '' }
  });
  const [userDialog, setUserDialog] = useState({ open: false, mode: 'create', data: null });
  const [ticketDialog, setTicketDialog] = useState({ open: false, subject: '', description: '', category: 'general', priority: 'medium', target_user_ids: [], target_role: '' });
  const [reassignDialog, setReassignDialog] = useState({ open: false, case_id: null });
  const [clientCredentialsDialog, setClientCredentialsDialog] = useState({ open: false, credentials: null });
  const [unassignedCases, setUnassignedCases] = useState([]);
  const [pendingPayments, setPendingPayments] = useState([]);
  const [sendingReminder, setSendingReminder] = useState(null);
  const [expirySummary, setExpirySummary] = useState({ expired: 0, critical: 0, warning: 0, attention: 0, ok: 0, total: 0 });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadData = async () => {
    try {
      const authHeader = getAuthHeader();
      const [statsRes, pendingSalesRes, casesRes, productsRes, usersRes, allSalesRes, commissionsRes, ticketsRes, ticketStatsRes, settingsRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`, authHeader),
        axios.get(`${API}/sales/pending`, authHeader),
        axios.get(`${API}/cases`, authHeader),
        axios.get(`${API}/products`, authHeader),
        axios.get(`${API}/users`, authHeader),
        axios.get(`${API}/sales`, authHeader).catch(() => ({ data: [] })),
        axios.get(`${API}/reports/partner-commissions`, authHeader).catch(() => ({ data: [] })),
        axios.get(`${API}/tickets/all`, authHeader).catch(() => ({ data: [] })),
        axios.get(`${API}/tickets/stats`, authHeader).catch(() => ({ data: {} })),
        axios.get(`${API}/settings`, authHeader).catch(() => ({ data: { allow_case_manager_workflow_customization: false } }))
      ]);
      setStats(statsRes.data);
      setPendingSales(pendingSalesRes.data);
      setCases(casesRes.data);
      setProducts(productsRes.data);
      setAllUsers(usersRes.data);
      setCaseManagers(usersRes.data.filter(u => u.role === 'case_manager'));
      setAllSales(allSalesRes.data);
      setPartnerCommissions(commissionsRes.data?.commissions || commissionsRes.data || []);
      setAllTickets(ticketsRes.data);
      setTicketStats(ticketStatsRes.data);
      setSystemSettings(settingsRes.data);
      
      // Load expiring documents
      try {
        const expiringRes = await axios.get(`${API}/scheduler/expiring-documents`, getAuthHeader());
        setExpiringDocuments(expiringRes.data.documents || []);
      } catch (e) {
        console.error('Failed to load expiring documents:', e);
      }
      
      // Load payment tracker
      try {
        const trackerRes = await axios.get(`${API}/sales/tracker/payment-deadlines`, authHeader);
        setPaymentTracker(trackerRes.data);
      } catch (e) {
        console.error('Failed to load payment tracker:', e);
      }
      
      // Load exchange rate
      try {
        const rateRes = await axios.get(`${API}/settings/exchange-rate`, authHeader);
        setExchangeRate(rateRes.data.rate || 83.50);
        setShowINR(rateRes.data.show_dual_currency || false);
      } catch (e) { /* use default */ }
      
      // Load refunds
      try {
        const refundsRes = await axios.get(`${API}/refunds`, authHeader);
        setRefunds(refundsRes.data || []);
      } catch (e) { /* no refunds yet */ }

      // Load unassigned cases
      try {
        const unassignedRes = await axios.get(`${API}/cases/unassigned`, authHeader);
        setUnassignedCases(unassignedRes.data || []);
      } catch (e) { console.error('Failed to load unassigned cases:', e); }

      // Load pending payments for reminders
      try {
        const remindersRes = await axios.get(`${API}/reminders/pending-payments`, authHeader);
        setPendingPayments(remindersRes.data || []);
      } catch (e) { /* no reminders */ }

      // Load expiry summary
      try {
        const expSummaryRes = await axios.get(`${API}/documents/expiry-summary`, authHeader);
        setExpirySummary(expSummaryRes.data || { expired: 0, critical: 0, warning: 0, attention: 0, ok: 0, total: 0 });
      } catch (e) { /* no expiry data */ }
      // Auto-trigger expiry reminders
      axios.post(`${API}/documents/check-expiry-reminders`, {}, authHeader).catch(() => {});
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const updateSystemSettings = async (newSettings) => {
    try {
      await axios.put(`${API}/settings`, newSettings, getAuthHeader());
      setSystemSettings(newSettings);
      toast.success('Settings updated!');
    } catch (error) {
      toast.error('Failed to update settings');
    }
  };

  // Currency formatting
  const formatCurrency = (amount, sale = null) => {
    const val = amount || 0;
    const inr = `₹${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    // If sale has original currency different from INR, show original too
    if (sale && sale.original_currency && sale.original_currency !== 'INR') {
      const symbols = { USD: '$', AUD: 'A$', CAD: 'C$', GBP: '£', EUR: '€' };
      const sym = symbols[sale.original_currency] || sale.original_currency;
      return inr;
    }
    return inr;
  };

  // Handle refund
  const handleRefund = async () => {
    if (!refundDialog.reason || refundDialog.reason.trim().length < 5) {
      toast.error('Refund reason is required (minimum 5 characters)');
      return;
    }
    if (!refundDialog.amount || refundDialog.amount <= 0) {
      toast.error('Refund amount must be positive');
      return;
    }
    try {
      await axios.post(`${API}/refunds`, {
        sale_id: refundDialog.sale_id,
        amount: refundDialog.amount,
        reason: refundDialog.reason.trim(),
        refund_method: refundDialog.refund_method,
        notes: refundDialog.notes
      }, getAuthHeader());
      toast.success('Refund processed successfully');
      setRefundDialog({ open: false, sale_id: null, amount: 0, reason: '', refund_method: 'original_payment', notes: '' });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process refund');
    }
  };

  // Handle notification navigation - open specific ticket or case
  const handleNotificationNavigation = async () => {
    const openTicketId = sessionStorage.getItem('openTicketId');
    const openCaseId = sessionStorage.getItem('openCaseId');
    
    if (openTicketId) {
      sessionStorage.removeItem('openTicketId');
      setActiveTab('tickets');
      try {
        const response = await axios.get(`${API}/tickets/${openTicketId}`, getAuthHeader());
        setSelectedTicket(response.data);
      } catch (error) {
        console.error('Failed to load ticket', error);
      }
    }
    
    if (openCaseId) {
      sessionStorage.removeItem('openCaseId');
      setActiveTab('cases');
      const caseItem = cases.find(c => c.id === openCaseId);
      if (caseItem) {
        setSelectedCase(caseItem);
      }
    }
  };

  // Custom notification click handler for admin
  const handleNotificationClick = async (notification) => {
    const type = notification.type || '';
    const relatedId = notification.related_id;
    
    if (type.includes('ticket')) {
      setActiveTab('tickets');
      if (relatedId) {
        try {
          const response = await axios.get(`${API}/tickets/${relatedId}`, getAuthHeader());
          setSelectedTicket(response.data);
        } catch (error) {
          toast.error('Failed to load ticket');
        }
      }
    } else if (type.includes('doc') || type.includes('case') || type.includes('step')) {
      setActiveTab('cases');
      if (relatedId) {
        const caseItem = cases.find(c => c.id === relatedId);
        if (caseItem) {
          setSelectedCase(caseItem);
        }
      }
    } else if (type.includes('sale')) {
      setActiveTab('sales');
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
      loadCustomCommissions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  const handleImpersonate = async (targetUser) => {
    try {
      // Store admin's original token and user info before switching
      const currentToken = localStorage.getItem('token');
      const currentUser = localStorage.getItem('user');
      localStorage.setItem('admin_token', currentToken);
      localStorage.setItem('admin_user', currentUser);
      
      const response = await axios.post(`${API}/auth/impersonate/${targetUser.id}`, {}, getAuthHeader());
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      const routes = { admin: '/admin', partner: '/partner', case_manager: '/case-manager', client: '/client' };
      toast.success(`Switched to ${targetUser.name}'s account`);
      setTimeout(() => { window.location.assign(routes[response.data.user.role]); }, 100);
    } catch (error) {
      toast.error('Failed to impersonate user');
    }
  };

  const downloadSalesReport = () => {
    if (salesReport.length === 0) {
      toast.error('No data to export');
      return;
    }
    
    // Create CSV content with enhanced fields
    const headers = ['Date of Sale', 'Client Name', 'Client Email', 'Service Type', 'Product', 'Partner', 'Fee Amount', 'Amount Received', 'Pending Amount', 'Commission Rate', 'Commission', 'Payment Status', 'Status', 'Rejection Reason', 'Approval Date'];
    const rows = salesReport.map(sale => [
      new Date(sale.created_at).toLocaleDateString(),
      sale.client_name,
      sale.client_email,
      sale.product_category || 'N/A',
      sale.product_name || 'N/A',
      sale.partner_name || 'N/A',
      sale.fee_amount,
      sale.amount_received || 0,
      sale.pending_amount || 0,
      (sale.commission_rate || 0) + '%',
      sale.commission_amount || 0,
      sale.payment_status || 'pending',
      sale.status,
      sale.rejection_reason || '',
      sale.approved_at ? new Date(sale.approved_at).toLocaleDateString() : 'N/A'
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `sales_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Sales report downloaded!');
  };

  // Load expiring documents
  const loadExpiringDocuments = async () => {
    try {
      const response = await axios.get(`${API}/scheduler/expiring-documents`, getAuthHeader());
      setExpiringDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Failed to load expiring documents:', error);
    }
  };

  // Trigger expiry check manually
  const triggerExpiryCheck = async () => {
    try {
      await axios.post(`${API}/scheduler/run-expiry-check-now`, {}, getAuthHeader());
      toast.success('Expiry check completed! Notifications sent to affected users.');
      loadExpiringDocuments();
    } catch (error) {
      toast.error('Failed to run expiry check');
    }
  };

  // Sales report functions
  const loadSalesReport = async () => {
    try {
      let url = `${API}/reports/sales?`;
      if (salesFilter.partner_id && salesFilter.partner_id !== 'all') url += `partner_id=${salesFilter.partner_id}&`;
      if (salesFilter.period && salesFilter.period !== 'custom') {
        url += `period=${salesFilter.period}&`;
      }
      if (salesFilter.period === 'custom') {
        if (salesFilter.date_from) url += `start_date=${salesFilter.date_from}&`;
        if (salesFilter.date_to) url += `end_date=${salesFilter.date_to}&`;
      }
      const response = await axios.get(url, getAuthHeader());
      setSalesReport(response.data.sales || response.data);
    } catch (error) {
      toast.error('Failed to load sales report');
    }
  };

  const loadPartnerReport = async (partnerId) => {
    try {
      let url = `${API}/sales/partner-report?`;
      if (partnerId && partnerId !== 'all') url += `partner_id=${partnerId}&`;
      if (salesFilter.period && salesFilter.period !== 'custom') url += `period=${salesFilter.period}&`;
      if (salesFilter.period === 'custom') {
        if (salesFilter.date_from) url += `date_from=${salesFilter.date_from}&`;
        if (salesFilter.date_to) url += `date_to=${salesFilter.date_to}&`;
      }
      const response = await axios.get(url, getAuthHeader());
      setSelectedPartnerReport(response.data);
    } catch (error) {
      toast.error('Failed to load partner report');
    }
  };

  const downloadReport = (data, filename) => {
    if (!data || data.length === 0) {
      toast.error('No data to export');
      return;
    }
    
    // Get headers from first object
    const headers = Object.keys(data[0]);
    
    // Build CSV rows with proper escaping
    const csvRows = data.map(row => {
      return headers.map(header => {
        let cell = row[header];
        if (cell === null || cell === undefined) cell = '';
        // Convert to string and escape quotes
        cell = String(cell).replace(/"/g, '""');
        // Wrap in quotes if contains comma, newline, or quotes
        if (cell.includes(',') || cell.includes('\n') || cell.includes('"')) {
          cell = `"${cell}"`;
        }
        return cell;
      }).join(',');
    });
    
    const csvContent = [headers.join(','), ...csvRows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    toast.success('Report downloaded');
  };

  // Load commissions with filters
  const loadCommissions = async () => {
    try {
      let url = `${API}/reports/partner-commissions?`;
      if (commissionFilter.period && commissionFilter.period !== 'custom') {
        url += `period=${commissionFilter.period}&`;
      }
      if (commissionFilter.period === 'custom') {
        if (commissionFilter.date_from) url += `start_date=${commissionFilter.date_from}&`;
        if (commissionFilter.date_to) url += `end_date=${commissionFilter.date_to}&`;
      }
      const response = await axios.get(url, getAuthHeader());
      setPartnerCommissions(response.data?.commissions || response.data || []);
    } catch (error) {
      toast.error('Failed to load commissions');
    }
  };

  const loadCustomCommissions = async () => {
    try {
      const res = await axios.get(`${API}/partner-commissions`, getAuthHeader());
      setCustomCommissions(res.data || []);
    } catch (error) {
      console.error('Failed to load custom commissions');
    }
  };

  const saveCustomCommission = async () => {
    if (!newCustomCommission.partner_id || !newCustomCommission.product_id) {
      toast.error('Select a partner and product');
      return;
    }
    try {
      await axios.post(`${API}/partner-commissions`, newCustomCommission, getAuthHeader());
      toast.success('Custom commission saved');
      loadCustomCommissions();
      setNewCustomCommission({ partner_id: '', product_id: '', commission_rate: 0 });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    }
  };

  const deleteCustomCommission = async (partnerId, productId) => {
    try {
      await axios.delete(`${API}/partner-commissions`, {
        ...getAuthHeader(),
        data: { partner_id: partnerId, product_id: productId }
      });
      toast.success('Custom commission removed');
      loadCustomCommissions();
    } catch (error) {
      toast.error('Failed to remove');
    }
  };

  // Download as PDF (simple HTML to print approach)
  const downloadPDF = (data, title, columns) => {
    if (!data || data.length === 0) {
      toast.error('No data to export');
      return;
    }

    // Create printable HTML
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          h1 { color: #2a777a; margin-bottom: 20px; }
          .summary { margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; }
          .summary-item { display: inline-block; margin-right: 30px; }
          .summary-label { font-size: 12px; color: #666; }
          .summary-value { font-size: 24px; font-weight: bold; color: #2a777a; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th { background: #2a777a; color: white; padding: 12px 8px; text-align: left; }
          td { padding: 10px 8px; border-bottom: 1px solid #ddd; }
          tr:hover { background: #f9f9f9; }
          .total-row { font-weight: bold; background: #e8f5f5; }
          .footer { margin-top: 20px; text-align: center; font-size: 12px; color: #666; }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        <p>Generated on: ${new Date().toLocaleString()}</p>
        <table>
          <thead>
            <tr>${columns.map(c => `<th>${c.header}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${data.map(row => `<tr>${columns.map(c => `<td>${c.format ? c.format(row[c.key]) : (row[c.key] ?? '')}</td>`).join('')}</tr>`).join('')}
          </tbody>
        </table>
        <div class="footer">Ladhani Education & Migration Services Pvt. Ltd</div>
      </body>
      </html>
    `;

    // Open print dialog
    const printWindow = window.open('', '_blank');
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 500);
    toast.success('PDF ready for printing');
  };

  // Ticket functions
  const loadTickets = async () => {
    try {
      let url = `${API}/tickets/all?`;
      if (ticketFilter.status) url += `status=${ticketFilter.status}&`;
      if (ticketFilter.priority) url += `priority=${ticketFilter.priority}&`;
      if (ticketFilter.created_by_role) url += `created_by_role=${ticketFilter.created_by_role}&`;
      const response = await axios.get(url, getAuthHeader());
      setAllTickets(response.data);
    } catch (error) {
      toast.error('Failed to load tickets');
    }
  };

  const updateTicketStatus = async (ticketId, status) => {
    try {
      // Validate resolution note for resolve/close actions
      if ((status === 'resolved' || status === 'closed') && (!resolutionNote || resolutionNote.trim().length < 10)) {
        toast.error('Resolution note is required (minimum 10 characters) to resolve or close a ticket');
        return;
      }
      await axios.put(`${API}/tickets/${ticketId}/status`, { status, resolution_note: resolutionNote || null }, getAuthHeader());
      toast.success(`Ticket ${status}`);
      setResolutionNote('');
      loadTickets();
      if (selectedTicket?.id === ticketId) {
        const res = await axios.get(`${API}/tickets/${ticketId}`, getAuthHeader());
        setSelectedTicket(res.data);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update ticket');
    }
  };

  const uploadTicketAttachment = async (ticketId, file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      await axios.post(`${API}/tickets/${ticketId}/attachment`, formData, {
        ...getAuthHeader(),
        headers: { ...getAuthHeader().headers, 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Attachment uploaded');
      const res = await axios.get(`${API}/tickets/${ticketId}`, getAuthHeader());
      setSelectedTicket(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload attachment');
    }
  };

  const downloadTicketAttachment = async (ticketId, fileId, filename) => {
    try {
      const response = await axios.get(`${API}/tickets/${ticketId}/attachment/${fileId}`, {
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
      toast.success('Attachment downloaded');
    } catch (error) {
      toast.error('Failed to download attachment');
    }
  };

  const addTicketReply = async (ticketId) => {
    if (!ticketReplyText.trim()) return;
    try {
      await axios.post(`${API}/tickets/${ticketId}/message`, { message: ticketReplyText }, getAuthHeader());
      toast.success('Reply added');
      setTicketReplyText('');
      const res = await axios.get(`${API}/tickets/${ticketId}`, getAuthHeader());
      setSelectedTicket(res.data);
    } catch (error) {
      toast.error('Failed to add reply');
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

  const downloadDocument = async (docId, filename, isSaleDoc = false) => {
    try {
      const endpoint = isSaleDoc 
        ? `${API}/sales/document/download/${docId}` 
        : `${API}/documents/download/${docId}`;
      const response = await axios.get(endpoint, { ...getAuthHeader(), responseType: 'blob' });
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

  // State for rejection dialog
  const [rejectionDialog, setRejectionDialog] = useState({ open: false, sale_id: null, reason: '' });

  const handleApproveSale = async (saleId, status, caseManagerId) => {
    // If rejecting, require a reason via dialog
    if (status === 'rejected') {
      setRejectionDialog({ open: true, sale_id: saleId, reason: '' });
      return;
    }
    try {
      const response = await axios.post(`${API}/sales/approve`, { sale_id: saleId, status, case_manager_id: caseManagerId || null }, getAuthHeader());
      toast.success(response.data.assignment_pending ? 'Sale approved! Assign a case manager from Pending Assignment tab.' : `Sale ${status}!`);
      
      // Show client credentials if new client was created
      if (response.data.client_credentials) {
        const creds = response.data.client_credentials;
        setClientCredentialsDialog({
          open: true,
          credentials: creds
        });
      }
      
      loadData();
      setActiveTab('sales');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update sale');
    }
  };

  const handleConfirmRejection = async () => {
    if (!rejectionDialog.reason || rejectionDialog.reason.trim().length < 5) {
      toast.error('Rejection reason is required (minimum 5 characters)');
      return;
    }
    try {
      await axios.post(`${API}/sales/approve`, {
        sale_id: rejectionDialog.sale_id,
        status: 'rejected',
        rejection_reason: rejectionDialog.reason.trim()
      }, getAuthHeader());
      toast.success('Sale rejected');
      setRejectionDialog({ open: false, sale_id: null, reason: '' });
      loadData();
      setActiveTab('sales');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject sale');
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
    setWorkflowDialog({ open: true, product: product, editingStepIndex: null });
  };

  const openStepEditor = (mode, stepIndex = null) => {
    if (mode === 'create') {
      const nextOrder = (workflowDialog.product?.workflow_steps?.length || 0) + 1;
      setStepEditorDialog({
        open: true, mode: 'create',
        stepData: { step_name: '', step_order: nextOrder, description: '', duration_days: '', required_documents: [] },
        newDoc: { doc_name: '', description: '', is_mandatory: true, has_expiry: false, expiry_date: '', validity_months: '', doc_type: '' }
      });
    } else {
      const step = workflowDialog.product.workflow_steps[stepIndex];
      setStepEditorDialog({
        open: true, mode: 'edit',
        stepData: { ...step, duration_days: step.duration_days || '' },
        newDoc: { doc_name: '', description: '', is_mandatory: true, has_expiry: false, expiry_date: '', validity_months: '', doc_type: '' }
      });
      setWorkflowDialog({ ...workflowDialog, editingStepIndex: stepIndex });
    }
  };

  const addDocToStep = () => {
    const { newDoc, stepData } = stepEditorDialog;
    if (!newDoc.doc_name.trim()) { toast.error('Please enter document name'); return; }
    setStepEditorDialog({
      ...stepEditorDialog,
      stepData: { ...stepData, required_documents: [...stepData.required_documents, { ...newDoc }] },
      newDoc: { doc_name: '', description: '', is_mandatory: true, has_expiry: false, expiry_date: '', validity_months: '', doc_type: '' }
    });
  };

  const [aiSuggesting, setAiSuggesting] = useState(false);

  const aiSuggestDocs = async () => {
    const { stepData } = stepEditorDialog;
    if (!stepData.step_name.trim()) { toast.error('Enter step name first'); return; }
    setAiSuggesting(true);
    try {
      const existingNames = stepData.required_documents.map(d => d.doc_name || d.name || '');
      const res = await axios.post(`${API}/step-documents/ai-suggest-step-docs`, {
        product_name: workflowDialog.product?.name || '',
        step_name: stepData.step_name,
        step_description: stepData.description || '',
        existing_docs: existingNames.filter(Boolean),
      }, getAuthHeader());
      const suggestions = res.data.suggestions || [];
      if (suggestions.length === 0) { toast.info('No suggestions available'); setAiSuggesting(false); return; }
      const newDocs = suggestions.map(s => ({
        doc_name: s.doc_name, description: s.description || '',
        is_mandatory: s.is_mandatory !== false, doc_type: s.doc_type || '',
        has_expiry: false, expiry_date: '', validity_months: ''
      }));
      setStepEditorDialog({
        ...stepEditorDialog,
        stepData: { ...stepData, required_documents: [...stepData.required_documents, ...newDocs] }
      });
      const sourceLabel = res.data.source === 'template' ? 'Official Template' : 'AI + Web Search';
      const feesMsg = res.data.fees_info ? `\nFees: ${res.data.fees_info.substring(0, 100)}...` : '';
      toast.success(`${sourceLabel}: ${suggestions.length} documents added!${feesMsg}`, { duration: 5000 });
    } catch (e) {
      toast.error(e.response?.data?.detail || 'AI suggestion failed');
    }
    setAiSuggesting(false);
  };

  const aiBulkSuggest = async () => {
    if (!workflowDialog.product?.workflow_steps?.length) { toast.error('Add steps first'); return; }
    setAiSuggesting(true);
    try {
      const res = await axios.post(`${API}/step-documents/ai-suggest-bulk`, {
        product_name: workflowDialog.product.name,
        product_description: workflowDialog.product.description || '',
        steps: workflowDialog.product.workflow_steps.map(s => ({
          step_name: s.step_name, description: s.description || ''
        })),
      }, getAuthHeader());
      const suggestions = res.data.suggestions || {};
      let totalAdded = 0;
      for (const step of workflowDialog.product.workflow_steps) {
        // Match step name flexibly - AI may return "Step Name - Description"
        const stepSuggs = suggestions[step.step_name] || 
          Object.entries(suggestions).find(([k]) => k.startsWith(step.step_name) || step.step_name.startsWith(k))?.[1] || [];
        if (stepSuggs.length > 0) {
          const existingNames = (step.required_documents || []).map(d => (d.doc_name || d.name || '').toLowerCase());
          const newDocs = stepSuggs.filter(s => !existingNames.includes((s.doc_name || '').toLowerCase()));
          if (newDocs.length > 0) {
            await axios.put(`${API}/products/${workflowDialog.product.id}/workflow-step/${step.step_order}`, {
              ...step, required_documents: [...(step.required_documents || []), ...newDocs.map(s => ({
                doc_name: s.doc_name, description: s.description || '',
                is_mandatory: s.is_mandatory !== false, doc_type: s.doc_type || ''
              }))]
            }, getAuthHeader());
            totalAdded += newDocs.length;
          }
        }
      }
      // Refresh product data
      const productsRes = await axios.get(`${API}/products`, getAuthHeader());
      setProducts(productsRes.data);
      const updatedProduct = productsRes.data.find(p => p.id === workflowDialog.product.id);
      setWorkflowDialog({ ...workflowDialog, product: updatedProduct });
      toast.success(`${res.data.source === 'template' ? 'Official Template' : 'AI'}: ${totalAdded} documents added across all steps!`, { duration: 5000 });
    } catch (e) {
      toast.error(e.response?.data?.detail || 'AI bulk suggestion failed');
    }
    setAiSuggesting(false);
  };

  const removeDocFromStep = (docIndex) => {
    const updatedDocs = stepEditorDialog.stepData.required_documents.filter((_, i) => i !== docIndex);
    setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, required_documents: updatedDocs } });
  };

  const saveWorkflowStep = async () => {
    const { stepData, mode } = stepEditorDialog;
    if (!stepData.step_name.trim()) { toast.error('Please enter step name'); return; }
    try {
      const productId = workflowDialog.product.id;
      const durationDays = stepData.duration_days ? parseInt(stepData.duration_days) : null;
      const stepOrder = stepData.step_order ? parseInt(stepData.step_order) : 1;
      const payload = {
        product_id: productId,
        step_name: stepData.step_name.trim(),
        step_order: isNaN(stepOrder) ? 1 : stepOrder,
        description: stepData.description || '',
        duration_days: isNaN(durationDays) ? null : durationDays,
        required_documents: (stepData.required_documents || []).map(d => ({
          doc_name: d.doc_name || d.name || '',
          description: d.description || '',
          is_mandatory: d.is_mandatory !== false,
          doc_type: d.doc_type || '',
          has_expiry: d.has_expiry || false,
          expiry_date: d.expiry_date || '',
          validity_months: d.validity_months || '',
        })).filter(d => d.doc_name)
      };

      if (mode === 'create') {
        await axios.post(`${API}/products/${productId}/workflow-step`, payload, getAuthHeader());
        toast.success('Workflow step added!');
      } else {
        const origStepOrder = workflowDialog.product.workflow_steps[workflowDialog.editingStepIndex].step_order;
        await axios.put(`${API}/products/${productId}/workflow-step/${origStepOrder}`, payload, getAuthHeader());
        toast.success('Workflow step updated!');
      }
      setStepEditorDialog({ ...stepEditorDialog, open: false });
      const productsRes = await axios.get(`${API}/products`, getAuthHeader());
      setProducts(productsRes.data);
      const updatedProduct = productsRes.data.find(p => p.id === productId);
      setWorkflowDialog({ ...workflowDialog, product: updatedProduct, editingStepIndex: null });
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || 'Failed to save workflow step';
      toast.error(detail);
      console.error('Save workflow step error:', error.response?.data || error);
    }
  };

  const deleteWorkflowStep = async (stepOrder) => {
    if (!window.confirm('Are you sure you want to delete this step?')) return;
    try {
      const productId = workflowDialog.product.id;
      await axios.delete(`${API}/products/${productId}/workflow-step/${stepOrder}`, getAuthHeader());
      toast.success('Workflow step deleted!');
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
        const newPassword = updateData.password;
        delete updateData.password;
        await axios.put(`${API}/users/${userDialog.data.id}`, updateData, getAuthHeader());
        
        // If password was provided, reset it separately
        if (newPassword && newPassword.length >= 6) {
          await axios.put(`${API}/users/${userDialog.data.id}/reset-password`, 
            { new_password: newPassword }, getAuthHeader());
          toast.success('User updated & password reset!');
        } else {
          toast.success('User updated!');
        }
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
    if (!ticketDialog.subject || !ticketDialog.description) { toast.error('Please fill subject and description'); return; }
    try {
      await axios.post(`${API}/tickets`, {
        subject: ticketDialog.subject, 
        description: ticketDialog.description,
        category: ticketDialog.category, 
        priority: ticketDialog.priority, 
        case_id: null,
        target_user_ids: ticketDialog.target_user_ids.length > 0 ? ticketDialog.target_user_ids : null,
        target_role: ticketDialog.target_role || null
      }, getAuthHeader());
      toast.success('Ticket created!');
      setTicketDialog({ open: false, subject: '', description: '', category: 'general', priority: 'medium', target_user_ids: [], target_role: '' });
      loadData();
    } catch (error) {
      toast.error('Failed to create ticket');
    }
  };

  const openTicketForUser = (targetUser) => {
    setTicketDialog({
      open: true,
      subject: '',
      description: '',
      category: 'general',
      priority: 'medium',
      target_user_ids: [targetUser.id],
      target_role: ''
    });
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
  const filteredCases = cases.filter(c => {
    const searchMatch = !caseFilter.search || 
      c.case_id?.toLowerCase().includes(caseFilter.search.toLowerCase()) || 
      c.client_name?.toLowerCase().includes(caseFilter.search.toLowerCase()) ||
      c.case_manager_name?.toLowerCase().includes(caseFilter.search.toLowerCase()) ||
      c.id?.toLowerCase().includes(caseFilter.search.toLowerCase());
    const managerMatch = !caseFilter.case_manager_id || c.case_manager_id === caseFilter.case_manager_id;
    const statusMatch = !caseFilter.status || c.status === caseFilter.status;
    return searchMatch && managerMatch && statusMatch;
  });
  const filteredUsers = allUsers.filter(u => u.name?.toLowerCase().includes(userSearchTerm.toLowerCase()) || u.email?.toLowerCase().includes(userSearchTerm.toLowerCase()));
  const partners = allUsers.filter(u => u.role === 'partner');

  const getStatusBadge = (status) => {
    const badges = {
      pending: <Badge className="bg-amber-100 text-amber-700 border-amber-300">Pending</Badge>,
      approved: <Badge className="bg-green-100 text-green-700 border-green-300">Approved</Badge>,
      rejected: <Badge className="bg-red-100 text-red-700 border-red-300">Rejected</Badge>,
      active: <Badge className="bg-blue-100 text-blue-700 border-blue-300">Active</Badge>,
      completed: <Badge className="bg-green-100 text-green-700 border-green-300">Completed</Badge>,
      in_progress: <Badge className="bg-blue-100 text-blue-700 border-blue-300">In Progress</Badge>,
      open: <Badge className="bg-blue-100 text-blue-700 border-blue-300">Open</Badge>,
      resolved: <Badge className="bg-green-100 text-green-700 border-green-300">Resolved</Badge>,
      closed: <Badge className="bg-slate-100 text-slate-600 border-slate-300">Closed</Badge>
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  const getPriorityBadge = (priority) => {
    const badges = {
      urgent: <Badge className="bg-red-500 text-white">Urgent</Badge>,
      high: <Badge className="bg-orange-500 text-white">High</Badge>,
      medium: <Badge className="bg-yellow-500 text-white">Medium</Badge>,
      low: <Badge className="bg-slate-400 text-white">Low</Badge>
    };
    return badges[priority] || <Badge>{priority}</Badge>;
  };

  const resetSelections = () => {
    setSelectedCase(null); setSelectedSale(null); setSelectedPartnerReport(null); setSelectedTicket(null);
  };

  const adminNavGroups = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard', onClick: () => { setActiveTab('dashboard'); resetSelections(); } },
    { id: 'approval-center', icon: CheckCircle, label: 'Approval Center', badge: (stats.pending_sales || 0) + (unassignedCases?.length || 0), badgeColor: 'bg-red-500', onClick: () => { setActiveTab('approval-center'); resetSelections(); } },
    {
      groupLabel: 'Sales & Finance',
      defaultOpen: true,
      items: [
        { id: 'revenue-dashboard', icon: BarChart3, label: 'Revenue Dashboard', onClick: () => { setActiveTab('revenue-dashboard'); resetSelections(); } },
        { id: 'refund-manager', icon: XCircle, label: 'Refund Manager', onClick: () => { setActiveTab('refund-manager'); resetSelections(); } },
        { id: 'reminders', icon: Bell, label: 'Payment Reminders', onClick: () => { setActiveTab('reminders'); resetSelections(); } },
        { id: 'total-sales', icon: TrendingUp, label: 'Sales Report', onClick: () => { setActiveTab('total-sales'); resetSelections(); } },
        { id: 'commissions', icon: DollarSign, label: 'Commissions', onClick: () => { setActiveTab('commissions'); resetSelections(); } },
        { id: 'revenue-forecast', icon: TrendingUp, label: 'Revenue Forecast', onClick: () => { setActiveTab('revenue-forecast'); resetSelections(); } },
        { id: 'commission-analytics', icon: DollarSign, label: 'Commission Analytics', onClick: () => { setActiveTab('commission-analytics'); resetSelections(); } },
      ]
    },
    {
      groupLabel: 'Cases & Users',
      defaultOpen: true,
      items: [
        { id: 'cases', icon: Briefcase, label: 'All Cases', onClick: () => { setActiveTab('cases'); resetSelections(); } },
        { id: 'users', icon: User, label: 'Users', onClick: () => { setActiveTab('users'); resetSelections(); } },
        { id: 'bulk-ops', icon: Zap, label: 'Bulk Operations', onClick: () => { setActiveTab('bulk-ops'); resetSelections(); } },
        { id: 'sla-tracker', icon: Clock, label: 'SLA Tracker', onClick: () => { setActiveTab('sla-tracker'); resetSelections(); } },
        { id: 'case-transfer', icon: ArrowRightLeft, label: 'Case Transfer', onClick: () => { setActiveTab('case-transfer'); resetSelections(); } },
        { id: 'cm-performance', icon: UserCheck, label: 'CM Performance', onClick: () => { setActiveTab('cm-performance'); resetSelections(); } },
      ]
    },
    {
      groupLabel: 'Reports & Analytics',
      items: [
        { id: 'report-builder', icon: FileText, label: 'Report Builder', onClick: () => { setActiveTab('report-builder'); resetSelections(); } },
        { id: 'country-product', icon: BarChart3, label: 'Country & Product', onClick: () => { setActiveTab('country-product'); resetSelections(); } },
        { id: 'conversion-funnel', icon: TrendingUp, label: 'Conversion Funnel', onClick: () => { setActiveTab('conversion-funnel'); resetSelections(); } },
        { id: 'email-digest', icon: Mail, label: 'Email Digest', onClick: () => { setActiveTab('email-digest'); resetSelections(); } },
        { id: 'activity', icon: Activity, label: 'Activity Log', onClick: () => navigate('/admin/activity') },
      ]
    },
    {
      groupLabel: 'System',
      items: [
        { id: 'products', icon: Settings, label: 'Products', onClick: () => { setActiveTab('products'); resetSelections(); } },
        { id: 'intake-builder', icon: ClipboardList, label: 'Intake Form Builder', onClick: () => { setActiveTab('intake-builder'); resetSelections(); } },
        { id: 'tickets', icon: MessageSquare, label: 'Tickets', badge: ticketStats.open, onClick: () => { setActiveTab('tickets'); resetSelections(); } },
        { id: 'settings', icon: Settings, label: 'Settings', onClick: () => { setActiveTab('settings'); resetSelections(); } },
        { id: 'appointments', icon: Calendar, label: 'Appointments', onClick: () => { setActiveTab('appointments'); resetSelections(); } },
      ]
    },
    {
      groupLabel: 'Planning Tools',
      defaultOpen: true,
      items: [
        { id: 'fee-calculator', icon: Calculator, label: 'Fee Calculator', onClick: () => { setActiveTab('fee-calculator'); resetSelections(); } },
        { id: 'ai-workflow', icon: Sparkles, label: 'AI Workflow Builder', onClick: () => navigate('/admin/ai-workflow') },
        { id: 'workflows', icon: FileText, label: 'Workflows', onClick: () => navigate('/admin/workflows') },
      ]
    },
    {
      groupLabel: 'Tools',
      defaultOpen: false,
      items: [
        { id: 'marketing', icon: Megaphone, label: 'Marketing', onClick: () => navigate('/admin/marketing') },
        { id: 'knowledge-base', icon: BookOpen, label: 'Knowledge Base', onClick: () => { setActiveTab('knowledge-base'); resetSelections(); } },
        { id: 'surveys', icon: Star, label: 'Satisfaction Surveys', onClick: () => { setActiveTab('surveys'); resetSelections(); } },
        { id: 'canned-responses', icon: MessageSquare, label: 'Canned Responses', onClick: () => { setActiveTab('canned-responses'); resetSelections(); } },
        { id: 'referrals', icon: Users, label: 'Referral Program', onClick: () => { setActiveTab('referrals'); resetSelections(); } },
        { id: 'greetings', icon: Bell, label: 'Client Greetings', onClick: () => { setActiveTab('greetings'); resetSelections(); } },
      ]
    },
  ];

  const getAdminPageTitle = () => {
    if (selectedTicket) return `Ticket: ${selectedTicket.subject}`;
    if (activeTab === 'sale-docs' && selectedSale) return `Sale: ${selectedSale.client_name}`;
    if (activeTab === 'case-detail' && selectedCase) return `Case: ${selectedCase.case_id}`;
    const titles = {
      dashboard: 'Dashboard', sales: 'Pending Sales', 'total-sales': 'Sales Report',
      commissions: 'Commissions', cases: 'All Cases', 'pending-assignment': 'Pending Assignment',
      reminders: 'Payment Reminders', products: 'Products', users: 'Users',
      tickets: 'Tickets', settings: 'Settings', refunds: 'Refunds',
      'bulk-ops': 'Bulk Operations', 'sla-tracker': 'SLA Tracker',
      'case-transfer': 'Case Transfer', 'cm-performance': 'CM Performance',
      'revenue-forecast': 'Revenue Forecast', 'knowledge-base': 'Knowledge Base',
      surveys: 'Satisfaction Surveys', appointments: 'Appointments',
      'conversion-funnel': 'Conversion Funnel', 'commission-analytics': 'Commission Analytics',
      'country-product': 'Country & Product Analytics', 'canned-responses': 'Canned Responses',
      referrals: 'Referral Program', greetings: 'Client Greetings',
      'approval-center': 'Unified Approval Center',
      'refund-manager': 'Refund Manager',
      'revenue-dashboard': 'Revenue Dashboard',
      'report-builder': 'Custom Report Builder',
      'email-digest': 'Email Digest',
    };
    return titles[activeTab] || 'Dashboard';
  };

  return (
    <DashboardShell
      user={user}
      roleLabel="Admin Portal"
      navGroups={adminNavGroups}
      activeTab={activeTab}
      pageTitle={getAdminPageTitle()}
      showBackButton={!!selectedCase || !!selectedSale || !!selectedTicket}
      onBack={() => {
        if (selectedTicket) { setSelectedTicket(null); setActiveTab('tickets'); }
        else if (selectedSale) { setSelectedSale(null); setActiveTab('sales'); }
        else if (selectedCase) { setSelectedCase(null); setActiveTab('cases'); }
      }}
      headerActions={
        <Button onClick={() => setTicketDialog({ ...ticketDialog, open: true })} variant="outline" size="sm" data-testid="raise-ticket-btn" className="hidden sm:flex">
          <Plus className="mr-2 h-4 w-4" />Raise Ticket
        </Button>
      }
      onNotificationClick={handleNotificationClick}
      onLogout={handleLogout}
    >
          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6" data-testid="dashboard-content">
              {/* Quick Actions Widget */}
              <QuickActions 
                userRole="admin" 
                onNavigate={(tab, filter) => {
                  setActiveTab(tab);
                  if (filter && tab === 'tickets') {
                    setTicketFilter({ ...ticketFilter, status: filter.status || '', priority: filter.priority || '' });
                  }
                }} 
              />

              <HappinessScoreWidget token={localStorage.getItem('token')} />

              <DeadlineOverviewWidget token={localStorage.getItem('token')} role="admin" />

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Pending Sales</p>
                  <p className="text-3xl font-bold text-[#f7620b] mt-2">{stats.pending_sales || 0}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Active Cases</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.active_cases || 0}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Total Revenue</p>
                  <p className="text-3xl font-bold text-emerald-600 mt-2">₹{(stats.total_revenue || 0).toLocaleString()}</p>
                  <div className="flex justify-between text-xs mt-2 text-slate-500">
                    <span className="text-green-600">Received: ₹{(stats.total_received || 0).toLocaleString()}</span>
                    <span className="text-amber-600">Pending: ₹{(stats.total_pending_amount || 0).toLocaleString()}</span>
                  </div>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Open Tickets</p>
                  <p className="text-3xl font-bold text-[#2a777a] mt-2">{ticketStats.open || 0}</p>
                </Card>
              </div>

              {/* Document Expiry Summary */}
              {(expirySummary.expired > 0 || expirySummary.critical > 0 || expirySummary.warning > 0 || expirySummary.attention > 0) && (
                <Card className="p-6 bg-white shadow-sm border-0" data-testid="admin-expiry-summary">
                  <h3 className="text-lg font-semibold mb-4 text-slate-800 flex items-center gap-2">
                    <svg className="h-5 w-5 text-[#f7620b]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                    Document Expiry Tracker
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {expirySummary.expired > 0 && (
                      <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                        <p className="text-2xl font-bold text-red-700">{expirySummary.expired}</p>
                        <p className="text-xs font-medium text-red-600">Expired</p>
                      </div>
                    )}
                    {expirySummary.critical > 0 && (
                      <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                        <p className="text-2xl font-bold text-orange-700">{expirySummary.critical}</p>
                        <p className="text-xs font-medium text-orange-600">Critical (&lt;30d)</p>
                      </div>
                    )}
                    {expirySummary.warning > 0 && (
                      <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                        <p className="text-2xl font-bold text-amber-700">{expirySummary.warning}</p>
                        <p className="text-xs font-medium text-amber-600">Warning (&lt;60d)</p>
                      </div>
                    )}
                    {expirySummary.attention > 0 && (
                      <div className="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
                        <p className="text-2xl font-bold text-yellow-700">{expirySummary.attention}</p>
                        <p className="text-xs font-medium text-yellow-600">Attention (&lt;90d)</p>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-3">Total tracked: {expirySummary.total} documents | Auto-reminders active</p>
                </Card>
              )}

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
                        <Button size="sm" onClick={() => viewSaleDocuments(sale)} className="bg-[#2a777a] hover:bg-[#236466]">Review</Button>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {allTickets.filter(t => t.status === 'open' || t.priority === 'urgent').length > 0 && (
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 text-slate-800">Urgent/Open Tickets</h3>
                  <div className="space-y-3">
                    {allTickets.filter(t => t.status === 'open' || t.priority === 'urgent').slice(0, 5).map(ticket => (
                      <div key={ticket.id} className="flex justify-between items-center p-3 bg-red-50 rounded-lg border border-red-200">
                        <div>
                          <p className="font-medium text-slate-800">{ticket.subject}</p>
                          <p className="text-sm text-slate-600">By: {ticket.created_by_name} ({ticket.created_by_role})</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {getPriorityBadge(ticket.priority)}
                          <Button size="sm" onClick={() => { setSelectedTicket(ticket); setActiveTab('tickets'); }} className="bg-[#2a777a] hover:bg-[#236466]">View</Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Expiring Documents Alert */}
              {expiringDocuments.length > 0 && (
                <Card className="p-6 border-l-4 border-l-amber-500">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-amber-500" />
                      Documents Expiring Soon ({expiringDocuments.length})
                    </h3>
                    <Button size="sm" variant="outline" onClick={triggerExpiryCheck} className="text-amber-600 border-amber-300 hover:bg-amber-50">
                      Send Reminders Now
                    </Button>
                  </div>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {expiringDocuments.slice(0, 5).map((doc, idx) => (
                      <div key={idx} className="flex justify-between items-center p-3 bg-amber-50 rounded-lg border border-amber-200">
                        <div>
                          <p className="font-medium text-slate-800">{doc.document_name}</p>
                          <p className="text-sm text-slate-600">{doc.client_name} • Case: {doc.case_id}</p>
                        </div>
                        <div className="text-right">
                          <Badge className={`${doc.days_remaining <= 3 ? 'bg-red-500' : doc.days_remaining <= 7 ? 'bg-amber-500' : 'bg-yellow-500'} text-white`}>
                            {doc.days_remaining} day{doc.days_remaining !== 1 ? 's' : ''}
                          </Badge>
                          <p className="text-xs text-slate-500 mt-1">Expires: {doc.expiry_date?.slice(0, 10)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {expiringDocuments.length > 5 && (
                    <p className="text-sm text-slate-500 mt-3 text-center">
                      +{expiringDocuments.length - 5} more documents expiring soon
                    </p>
                  )}
                </Card>
              )}

              {/* Currency Info */}
              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-slate-600" />
                    <span className="text-sm font-medium text-slate-700">Base Currency: INR (₹)</span>
                  </div>
                  <span className="text-xs text-slate-500">Exchange rates: USD ₹83.50 | AUD ₹55 | CAD ₹62 | GBP ₹106 | EUR ₹91</span>
                </div>
              </Card>

              {/* Payment Collection Tracker Widget */}
              <Card className="p-6" data-testid="payment-tracker-widget">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-[#2a777a]" />
                    Payment Collection Tracker
                  </h3>
                  <Badge className="bg-slate-100 text-slate-700 border-slate-300">{paymentTracker.items?.length || 0} pending</Badge>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                    <p className="text-xs text-red-600 font-medium">Overdue</p>
                    <p className="text-lg font-bold text-red-700">{paymentTracker.summary?.overdue_count || 0}</p>
                    <p className="text-xs text-red-500">{formatCurrency(paymentTracker.summary?.overdue_amount)}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                    <p className="text-xs text-amber-600 font-medium">Due This Week</p>
                    <p className="text-lg font-bold text-amber-700">{paymentTracker.summary?.due_soon_count || 0}</p>
                    <p className="text-xs text-amber-500">{formatCurrency(paymentTracker.summary?.due_soon_amount)}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                    <p className="text-xs text-green-600 font-medium">Upcoming</p>
                    <p className="text-lg font-bold text-green-700">{paymentTracker.summary?.upcoming_count || 0}</p>
                    <p className="text-xs text-green-500">{formatCurrency(paymentTracker.summary?.upcoming_amount)}</p>
                  </div>
                </div>

                {/* Payment Items List */}
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {(paymentTracker.items || []).slice(0, 10).map((item, idx) => (
                    <div key={idx} className={`flex justify-between items-center p-3 rounded-lg border ${
                      item.urgency === 'overdue' ? 'bg-red-50 border-red-200' :
                      item.urgency === 'due_soon' ? 'bg-amber-50 border-amber-200' :
                      'bg-green-50 border-green-200'
                    }`} data-testid={`tracker-item-${idx}`}>
                      <div>
                        <p className="font-medium text-slate-800">{item.client_name}</p>
                        <p className="text-xs text-slate-600">{item.partner_name} | Created: {new Date(item.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className="text-right">
                        <p className={`font-bold ${
                          item.urgency === 'overdue' ? 'text-red-700' :
                          item.urgency === 'due_soon' ? 'text-amber-700' :
                          'text-green-700'
                        }`}>{formatCurrency(item.pending_amount)}</p>
                        {item.collection_deadline && (
                          <p className="text-xs text-slate-500">
                            {item.days_until_deadline !== null ? (
                              item.days_until_deadline < 0 ? `${Math.abs(item.days_until_deadline)} days overdue` :
                              item.days_until_deadline === 0 ? 'Due today' :
                              `${item.days_until_deadline} days left`
                            ) : 'No deadline set'}
                          </p>
                        )}
                        {!item.collection_deadline && <p className="text-xs text-slate-400">No deadline</p>}
                      </div>
                    </div>
                  ))}
                  {(!paymentTracker.items || paymentTracker.items.length === 0) && (
                    <div className="text-center py-8 text-slate-500">
                      <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-400" />
                      <p>All payments collected!</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          )}

          {/* Total Sales Tab */}
          {activeTab === 'total-sales' && !selectedPartnerReport && (
            <div className="space-y-6" data-testid="total-sales-content">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800 flex items-center gap-2">
                  <Filter className="h-5 w-5" /> Filters
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <div>
                    <Label>Partner</Label>
                    <Select value={salesFilter.partner_id} onValueChange={(v) => setSalesFilter({ ...salesFilter, partner_id: v })}>
                      <SelectTrigger><SelectValue placeholder="All Partners" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Partners</SelectItem>
                        {partners.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Period</Label>
                    <Select value={salesFilter.period} onValueChange={(v) => setSalesFilter({ ...salesFilter, period: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="lifetime">Lifetime</SelectItem>
                        <SelectItem value="weekly">This Week</SelectItem>
                        <SelectItem value="monthly">This Month</SelectItem>
                        <SelectItem value="quarterly">This Quarter</SelectItem>
                        <SelectItem value="yearly">This Year</SelectItem>
                        <SelectItem value="custom">Custom Range</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {salesFilter.period === 'custom' && (
                    <>
                      <div>
                        <Label>From Date</Label>
                        <Input type="date" value={salesFilter.date_from} onChange={(e) => setSalesFilter({ ...salesFilter, date_from: e.target.value })} />
                      </div>
                      <div>
                        <Label>To Date</Label>
                        <Input type="date" value={salesFilter.date_to} onChange={(e) => setSalesFilter({ ...salesFilter, date_to: e.target.value })} />
                      </div>
                    </>
                  )}
                  <div className="flex items-end gap-2">
                    <Button onClick={loadSalesReport} className="bg-[#2a777a] hover:bg-[#236466]"><Search className="mr-2 h-4 w-4" />Search</Button>
                    <Button onClick={() => downloadReport(salesReport, 'sales_report')} variant="outline"><Download className="mr-2 h-4 w-4" />CSV</Button>
                    <Button onClick={async () => {
                      try {
                        const res = await axios.get(`${API}/reports/export/sales-report?status=${salesFilter.status || ''}`, { ...getAuthHeader(), responseType: 'blob' });
                        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
                        const a = document.createElement('a'); a.href = url; a.download = `LEAMSS_Sales_Report.pdf`; a.click();
                        window.URL.revokeObjectURL(url);
                      } catch (e) { toast.error('Failed to export PDF'); }
                    }} variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" data-testid="export-sales-pdf"><FileText className="mr-2 h-4 w-4" />PDF</Button>
                  </div>
                </div>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-blue-50 border-blue-200">
                  <p className="text-sm text-slate-600">Total Sales</p>
                  <p className="text-2xl font-bold text-blue-700">{salesReport.length}</p>
                </Card>
                <Card className="p-4 bg-green-50 border-green-200">
                  <p className="text-sm text-slate-600">Approved</p>
                  <p className="text-2xl font-bold text-green-700">{salesReport.filter(s => s.status === 'approved').length}</p>
                </Card>
                <Card className="p-4 bg-amber-50 border-amber-200">
                  <p className="text-sm text-slate-600">Total Revenue</p>
                  <p className="text-2xl font-bold text-amber-700">₹{salesReport.filter(s => s.status === 'approved').reduce((sum, s) => sum + (s.fee_amount || 0), 0).toLocaleString()}</p>
                </Card>
                <Card className="p-4 bg-purple-50 border-purple-200">
                  <p className="text-sm text-slate-600">Total Commission</p>
                  <p className="text-2xl font-bold text-purple-700">₹{salesReport.filter(s => s.status === 'approved').reduce((sum, s) => sum + (s.commission_amount || 0), 0).toLocaleString()}</p>
                </Card>
              </div>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Sales Records</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3">Date</th>
                        <th className="text-left p-3">Client</th>
                        <th className="text-left p-3">Partner</th>
                        <th className="text-left p-3">Service Type</th>
                        <th className="text-right p-3">Fee</th>
                        <th className="text-right p-3">Received</th>
                        <th className="text-right p-3">Pending</th>
                        <th className="text-right p-3">Commission</th>
                        <th className="text-center p-3">Status</th>
                        <th className="text-left p-3">Rejection Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesReport.slice(0, 50).map(sale => (
                        <tr key={sale.id} className="border-b hover:bg-slate-50">
                          <td className="p-3">{new Date(sale.created_at).toLocaleDateString()}</td>
                          <td className="p-3">{sale.client_name}</td>
                          <td className="p-3">{sale.partner_name}</td>
                          <td className="p-3">
                            <Badge variant="outline" className="capitalize">{sale.product_category || 'N/A'}</Badge>
                          </td>
                          <td className="p-3 text-right">₹{sale.fee_amount?.toLocaleString()}</td>
                          <td className="p-3 text-right text-green-700">₹{(sale.amount_received || 0).toLocaleString()}</td>
                          <td className="p-3 text-right text-amber-700">₹{(sale.pending_amount || 0).toLocaleString()}</td>
                          <td className="p-3 text-right">₹{sale.commission_amount?.toLocaleString()}</td>
                          <td className="p-3 text-center">{getStatusBadge(sale.status)}</td>
                          <td className="p-3 text-sm text-red-600">{sale.rejection_reason || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* Partner Report Detail */}
          {activeTab === 'total-sales' && selectedPartnerReport && (
            <div className="space-y-6" data-testid="partner-report-content">
              <Button onClick={() => setSelectedPartnerReport(null)} variant="outline"><ArrowRight className="mr-2 h-4 w-4 rotate-180" />Back to Sales</Button>
              
              <Card className="p-6">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-xl font-semibold text-slate-800">{selectedPartnerReport.partner?.name}</h3>
                    <p className="text-slate-600">{selectedPartnerReport.partner?.email}</p>
                  </div>
                  <Button onClick={() => downloadReport(selectedPartnerReport.sales, `partner_${selectedPartnerReport.partner?.name}_report`)} variant="outline">
                    <Download className="mr-2 h-4 w-4" />Download Report
                  </Button>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-slate-600">Total Sales</p>
                    <p className="text-2xl font-bold text-blue-700">{selectedPartnerReport.summary?.total_sales}</p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-sm text-slate-600">Approved</p>
                    <p className="text-2xl font-bold text-green-700">{selectedPartnerReport.summary?.approved_sales}</p>
                  </div>
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <p className="text-sm text-slate-600">Pending</p>
                    <p className="text-2xl font-bold text-amber-700">{selectedPartnerReport.summary?.pending_sales}</p>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <p className="text-sm text-slate-600">Total Revenue</p>
                    <p className="text-2xl font-bold text-purple-700">₹{selectedPartnerReport.summary?.total_revenue?.toLocaleString()}</p>
                  </div>
                  <div className="p-4 bg-[#2a777a]/10 rounded-lg">
                    <p className="text-sm text-slate-600">Commission Payable</p>
                    <p className="text-2xl font-bold text-[#2a777a]">₹{selectedPartnerReport.summary?.total_commission_payable?.toLocaleString()}</p>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* Commissions Tab */}
          {activeTab === 'commissions' && (
            <div className="space-y-6" data-testid="commissions-content">
              {/* Filters Card */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800 flex items-center gap-2">
                  <Filter className="h-5 w-5" /> Filters
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <div>
                    <Label>Period</Label>
                    <Select value={commissionFilter.period} onValueChange={(v) => setCommissionFilter({ ...commissionFilter, period: v })}>
                      <SelectTrigger data-testid="commission-period-filter"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="lifetime">Lifetime</SelectItem>
                        <SelectItem value="weekly">This Week</SelectItem>
                        <SelectItem value="monthly">This Month</SelectItem>
                        <SelectItem value="quarterly">This Quarter</SelectItem>
                        <SelectItem value="yearly">This Year</SelectItem>
                        <SelectItem value="custom">Custom Range</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {commissionFilter.period === 'custom' && (
                    <>
                      <div>
                        <Label>From Date</Label>
                        <Input type="date" value={commissionFilter.date_from} onChange={(e) => setCommissionFilter({ ...commissionFilter, date_from: e.target.value })} data-testid="commission-date-from" />
                      </div>
                      <div>
                        <Label>To Date</Label>
                        <Input type="date" value={commissionFilter.date_to} onChange={(e) => setCommissionFilter({ ...commissionFilter, date_to: e.target.value })} data-testid="commission-date-to" />
                      </div>
                    </>
                  )}
                  <div className="flex items-end gap-2">
                    <Button onClick={loadCommissions} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="commission-search-btn">
                      <Search className="mr-2 h-4 w-4" />Search
                    </Button>
                  </div>
                  <div className="flex items-end gap-2">
                    <Button onClick={() => downloadReport(partnerCommissions, 'partner_commissions')} variant="outline" data-testid="commission-export-csv">
                      <Download className="mr-2 h-4 w-4" />CSV
                    </Button>
                    <Button 
                      onClick={() => downloadPDF(
                        partnerCommissions, 
                        'Partner Commission Report',
                        [
                          { key: 'partner_name', header: 'Partner' },
                          { key: 'total_sales', header: 'Sales' },
                          { key: 'total_fee', header: 'Revenue', format: (v) => `₹${(v || 0).toLocaleString()}` },
                          { key: 'total_commission', header: 'Commission', format: (v) => `₹${(v || 0).toLocaleString()}` }
                        ]
                      )} 
                      variant="outline"
                      data-testid="commission-export-pdf"
                    >
                      <FileText className="mr-2 h-4 w-4" />PDF
                    </Button>
                  </div>
                </div>
              </Card>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-4 bg-gradient-to-br from-[#2a777a] to-[#236466] text-white">
                  <p className="text-sm opacity-80">Total Commission</p>
                  <p className="text-3xl font-bold mt-2">₹{partnerCommissions.reduce((sum, p) => sum + (p.total_commission || 0), 0).toLocaleString()}</p>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-[#f7620b] to-[#e55a09] text-white">
                  <p className="text-sm opacity-80">Total Revenue</p>
                  <p className="text-3xl font-bold mt-2">₹{partnerCommissions.reduce((sum, p) => sum + (p.total_fee || 0), 0).toLocaleString()}</p>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-purple-500 to-purple-600 text-white">
                  <p className="text-sm opacity-80">Total Partners</p>
                  <p className="text-3xl font-bold mt-2">{partnerCommissions.length}</p>
                </Card>
              </div>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Partner Commission Details</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-slate-50">
                        <th className="text-left p-3">Partner</th>
                        <th className="text-center p-3">Total Sales</th>
                        <th className="text-right p-3">Total Fee</th>
                        <th className="text-right p-3">Commission</th>
                        <th className="text-center p-3">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {partnerCommissions.map(partner => (
                        <tr key={partner._id} className="border-b hover:bg-slate-50">
                          <td className="p-3 font-medium">{partner.partner_name}</td>
                          <td className="p-3 text-center">{partner.total_sales}</td>
                          <td className="p-3 text-right">₹{partner.total_fee?.toLocaleString()}</td>
                          <td className="p-3 text-right font-bold text-[#2a777a]">₹{partner.total_commission?.toLocaleString()}</td>
                          <td className="p-3 text-center">
                            <Button size="sm" variant="outline" onClick={() => { setSalesFilter({ ...salesFilter, partner_id: partner._id }); setActiveTab('total-sales'); }}>
                              <Eye className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Custom Per-Partner Product Commissions */}
              <Card className="p-6" data-testid="custom-commissions-card">
                <h3 className="text-lg font-semibold mb-4 text-slate-800 flex items-center gap-2">
                  <Settings className="h-5 w-5 text-[#f7620b]" />
                  Custom Product Commissions Per Partner
                </h3>
                <p className="text-sm text-slate-500 mb-4">
                  Set custom commission rates for specific partners on specific products. These override the partner's default rate.
                </p>

                {/* Add New Custom Commission */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6 p-4 bg-slate-50 rounded-lg">
                  <div>
                    <Label>Partner</Label>
                    <Select value={newCustomCommission.partner_id} onValueChange={(v) => setNewCustomCommission({ ...newCustomCommission, partner_id: v })}>
                      <SelectTrigger data-testid="custom-comm-partner-select"><SelectValue placeholder="Select Partner" /></SelectTrigger>
                      <SelectContent>
                        {allUsers.filter(u => u.role === 'partner').map(u => (
                          <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Product</Label>
                    <Select value={newCustomCommission.product_id} onValueChange={(v) => setNewCustomCommission({ ...newCustomCommission, product_id: v })}>
                      <SelectTrigger data-testid="custom-comm-product-select"><SelectValue placeholder="Select Product" /></SelectTrigger>
                      <SelectContent>
                        {products.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Commission Rate (%)</Label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      value={newCustomCommission.commission_rate}
                      onChange={(e) => setNewCustomCommission({ ...newCustomCommission, commission_rate: parseFloat(e.target.value) || 0 })}
                      data-testid="custom-comm-rate-input"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button onClick={saveCustomCommission} className="bg-[#2a777a] hover:bg-[#236466] w-full" data-testid="save-custom-comm-btn">
                      <Plus className="h-4 w-4 mr-2" /> Save
                    </Button>
                  </div>
                </div>

                {/* Existing Custom Commissions Table */}
                {customCommissions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-slate-50">
                          <th className="text-left p-3">Partner</th>
                          <th className="text-left p-3">Product</th>
                          <th className="text-center p-3">Custom Rate</th>
                          <th className="text-center p-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {customCommissions.map((cc, idx) => (
                          <tr key={idx} className="border-b hover:bg-slate-50">
                            <td className="p-3 font-medium">{cc.partner_name}</td>
                            <td className="p-3">{cc.product_name}</td>
                            <td className="p-3 text-center">
                              {cc._editing ? (
                                <Input
                                  type="number"
                                  min="0"
                                  max="100"
                                  step="0.5"
                                  className="w-24 mx-auto"
                                  value={cc._editRate}
                                  onChange={(e) => {
                                    const updated = [...customCommissions];
                                    updated[idx] = { ...cc, _editRate: parseFloat(e.target.value) || 0 };
                                    setCustomCommissions(updated);
                                  }}
                                  data-testid={`edit-rate-input-${idx}`}
                                />
                              ) : (
                                <span className="bg-[#2a777a] text-white px-3 py-1 rounded-full text-xs font-bold">{cc.commission_rate}%</span>
                              )}
                            </td>
                            <td className="p-3 text-center">
                              <div className="flex gap-1 justify-center">
                                {cc._editing ? (
                                  <>
                                    <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white" onClick={async () => {
                                      try {
                                        await axios.post(`${API}/partner-commissions`, { partner_id: cc.partner_id, product_id: cc.product_id, commission_rate: cc._editRate }, getAuthHeader());
                                        toast.success('Rate updated');
                                        loadCustomCommissions();
                                      } catch (error) { toast.error('Failed to update'); }
                                    }} data-testid={`save-edit-${idx}`}>
                                      <CheckCircle className="h-4 w-4" />
                                    </Button>
                                    <Button size="sm" variant="outline" onClick={() => {
                                      const updated = [...customCommissions];
                                      updated[idx] = { ...cc, _editing: false };
                                      setCustomCommissions(updated);
                                    }} data-testid={`cancel-edit-${idx}`}>
                                      <XCircle className="h-4 w-4" />
                                    </Button>
                                  </>
                                ) : (
                                  <>
                                    <Button size="sm" variant="outline" onClick={() => {
                                      const updated = [...customCommissions];
                                      updated[idx] = { ...cc, _editing: true, _editRate: cc.commission_rate };
                                      setCustomCommissions(updated);
                                    }} data-testid={`edit-custom-comm-${idx}`}>
                                      <Edit className="h-4 w-4" />
                                    </Button>
                                    <Button size="sm" variant="destructive" onClick={() => deleteCustomCommission(cc.partner_id, cc.product_id)} data-testid={`delete-custom-comm-${idx}`}>
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <p>No custom product commissions configured yet.</p>
                    <p className="text-xs mt-1">All partners are using their default commission rates.</p>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Pending Sales Tab */}
          {activeTab === 'sales' && (
            <div className="space-y-4" data-testid="sales-content">
              {/* Sales filter tabs */}
              <div className="flex gap-2 mb-4">
                {['all', 'pending', 'approved', 'rejected'].map(filter => (
                  <Button key={filter} size="sm" variant={salesStatusFilter === filter ? 'default' : 'outline'}
                    className={salesStatusFilter === filter ? 'bg-[#2a777a] text-white' : ''}
                    onClick={() => setSalesStatusFilter(filter)} data-testid={`sales-filter-${filter}`}>
                    {filter.charAt(0).toUpperCase() + filter.slice(1)} ({filter === 'all' ? allSales.length : allSales.filter(s => s.status === filter).length})
                  </Button>
                ))}
              </div>
              
              {(salesStatusFilter === 'all' ? allSales : allSales.filter(s => s.status === salesStatusFilter)).length === 0 ? (
                <Card className="p-12 text-center">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <p className="text-slate-600">No {salesStatusFilter !== 'all' ? salesStatusFilter : ''} sales found</p>
                </Card>
              ) : (
                (salesStatusFilter === 'all' ? allSales : allSales.filter(s => s.status === salesStatusFilter)).map((sale) => (
                  <Card key={sale.id} className="p-6" data-testid={`sale-card-${sale.id}`}>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-slate-800">{sale.client_name}</h3>
                          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                            sale.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                            sale.status === 'rejected' ? 'bg-red-50 text-red-700 border-red-200' :
                            'bg-amber-50 text-amber-700 border-amber-200'
                          }`}>{sale.status}</span>
                          {sale.payment_status && sale.payment_status !== 'pending' && (
                            <Badge className={sale.payment_status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>{sale.payment_status}</Badge>
                          )}
                        </div>
                        <p className="text-sm text-slate-600">{sale.client_email} | {sale.client_mobile}</p>
                        <p className="text-sm text-slate-600 mt-1">
                          Product: <span className="font-medium">{sale.product_name}</span>
                          <Badge variant="outline" className="ml-2 capitalize text-xs">{sale.product_category || 'N/A'}</Badge>
                          {' | '}Partner: {sale.partner_name}
                        </p>
                        <div className="flex flex-wrap gap-4 mt-1 text-sm">
                          <span className="text-slate-600">Fee: <span className="font-semibold">₹{(sale.fee_amount || 0).toLocaleString()}</span></span>
                          <span className="text-green-700">Received: <span className="font-semibold">₹{(sale.amount_received || 0).toLocaleString()}</span></span>
                          {(sale.pending_amount || 0) > 0 && (
                            <span className="text-amber-700">Pending: <span className="font-semibold">₹{(sale.pending_amount || 0).toLocaleString()}</span></span>
                          )}
                          <span className="text-slate-600">Payment: {sale.payment_method} {sale.payment_reference ? `(${sale.payment_reference})` : ''}</span>
                        </div>
                        {sale.commission_rate > 0 && (
                          <p className="text-sm text-slate-600 mt-1">
                            Commission: {sale.commission_rate}% of received = <span className="font-semibold text-[#2a777a]">₹{(sale.commission_amount || 0).toLocaleString()}</span>
                          </p>
                        )}
                        {(sale.total_discount_amount || 0) > 0 && (
                          <div className="flex flex-wrap gap-2 mt-1">
                            {sale.promo_code && <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200">Promo: {sale.promo_code} (-₹{(sale.promo_discount_amount || 0).toLocaleString()})</span>}
                            {(sale.additional_discount_percentage || 0) > 0 && <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">Additional: {sale.additional_discount_percentage}% (-₹{(sale.additional_discount_amount || 0).toLocaleString()})</span>}
                            <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full border border-amber-200">Original: ₹{(sale.fee_before_discount || sale.fee_amount).toLocaleString()} | Discount: ₹{(sale.total_discount_amount).toLocaleString()}</span>
                          </div>
                        )}
                        {sale.rejection_reason && (
                          <p className="text-sm text-red-600 mt-1 bg-red-50 p-2 rounded">Rejection Reason: {sale.rejection_reason}</p>
                        )}
                        <p className="text-xs text-slate-400 mt-1">Created: {new Date(sale.created_at).toLocaleString()}</p>
                      </div>
                      <div className="flex flex-col gap-2">
                        {sale.status === 'pending' && (
                          <>
                            <Button onClick={() => viewSaleDocuments(sale)} size="sm" className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid={`view-docs-${sale.id}`}>
                              <Eye className="mr-2 h-4 w-4" />View Docs
                            </Button>
                            <Button onClick={() => handleApproveSale(sale.id, 'approved', null)} size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid={`approve-sale-${sale.id}`}>
                              <CheckCircle className="mr-2 h-4 w-4" />Approve
                            </Button>
                            <Button onClick={() => handleApproveSale(sale.id, 'rejected', null)} variant="destructive" size="sm" data-testid={`reject-sale-${sale.id}`}>Reject</Button>
                          </>
                        )}
                        {sale.status === 'approved' && (
                          <>
                          <Button onClick={() => viewSaleDocuments(sale)} size="sm" variant="outline" data-testid={`view-docs-${sale.id}`}>
                            <Eye className="mr-2 h-4 w-4" />View Docs
                          </Button>
                          {(sale.amount_received || 0) > 0 && (
                            <Button onClick={async () => {
                              try {
                                const token = localStorage.getItem('token');
                                const res = await axios.get(`${API}/reports/export/sale-receipt/${sale.id}`, {
                                  headers: { Authorization: `Bearer ${token}` }, responseType: 'blob'
                                });
                                const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
                                const link = document.createElement('a');
                                link.href = url;
                                link.setAttribute('download', `Receipt_${sale.client_name.replace(/\s/g,'_')}.pdf`);
                                document.body.appendChild(link);
                                link.click();
                                link.remove();
                                toast.success('Receipt downloaded!');
                              } catch (e) { toast.error('Failed to download receipt'); }
                            }} size="sm" variant="outline" className="text-[#2a777a] border-[#2a777a]" data-testid={`receipt-${sale.id}`}>
                              <Download className="mr-2 h-4 w-4" />Receipt
                            </Button>
                          )}
                          </>
                        )}
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
              <Button onClick={() => setActiveTab('sales')} variant="outline"><ArrowRight className="mr-2 h-4 w-4 rotate-180" />Back to Sales</Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Sale Information</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div><p className="text-sm text-slate-500">Client</p><p className="font-medium text-slate-800">{selectedSale.client_name}</p></div>
                  <div><p className="text-sm text-slate-500">Email</p><p className="font-medium text-slate-800">{selectedSale.client_email}</p></div>
                  <div><p className="text-sm text-slate-500">Product</p><p className="font-medium text-slate-800">{selectedSale.product_name}</p></div>
                  <div><p className="text-sm text-slate-500">Service Type</p><Badge variant="outline" className="capitalize">{selectedSale.product_category || 'N/A'}</Badge></div>
                  <div><p className="text-sm text-slate-500">Fee Amount</p><p className="font-medium text-slate-800">{formatCurrency(selectedSale.fee_amount)}</p></div>
                  <div><p className="text-sm text-slate-500">Amount Received</p><p className="font-medium text-green-700">{formatCurrency(selectedSale.amount_received)}</p></div>
                  <div><p className="text-sm text-slate-500">Pending Amount</p><p className="font-medium text-amber-700">{formatCurrency(selectedSale.pending_amount || (selectedSale.fee_amount - (selectedSale.amount_received || 0)))}</p></div>
                  <div><p className="text-sm text-slate-500">Commission ({selectedSale.commission_rate || 0}%)</p><p className="font-medium text-[#2a777a]">{formatCurrency(selectedSale.commission_amount)}</p></div>
                </div>
                {selectedSale.original_currency && selectedSale.original_currency !== 'INR' && (
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 mb-4">
                    <p className="text-sm text-blue-700">
                      Original: {selectedSale.original_currency} {(selectedSale.original_fee_amount || 0).toLocaleString()} 
                      {' '}(Rate: 1 {selectedSale.original_currency} = ₹{selectedSale.exchange_rate_used})
                    </p>
                  </div>
                )}
                {selectedSale.total_refunded > 0 && (
                  <div className="p-3 bg-red-50 rounded-lg border border-red-200 mb-4">
                    <p className="text-sm text-red-700">Total Refunded: <span className="font-bold">{formatCurrency(selectedSale.total_refunded)}</span></p>
                  </div>
                )}
                <h4 className="font-semibold mb-3 text-slate-800">Uploaded Documents</h4>
                <div className="space-y-3">
                  {saleDocuments.length === 0 ? (
                    <p className="text-center text-slate-500 py-4">No documents uploaded</p>
                  ) : (
                    saleDocuments.map((doc, idx) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                        <div><p className="font-medium text-slate-800">{doc.filename}</p><p className="text-sm text-slate-600">Type: {doc.type}</p></div>
                        <Button onClick={() => downloadDocument(doc.id || doc.file_id, doc.filename, true)} size="sm" variant="outline"><Download className="h-4 w-4" /></Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
              <div className="flex gap-3">
                {selectedSale.status === 'pending' && (
                  <>
                    <Button onClick={() => handleApproveSale(selectedSale.id, 'approved', null)} className="bg-emerald-600 hover:bg-emerald-700 text-white flex-1" data-testid="approve-sale-btn">
                      <CheckCircle className="mr-2 h-4 w-4" />Approve Sale
                    </Button>
                    <Button onClick={() => handleApproveSale(selectedSale.id, 'rejected', null)} variant="destructive">Reject Sale</Button>
                  </>
                )}
                {selectedSale.status === 'approved' && (selectedSale.amount_received || 0) > 0 && (
                  <Button
                    onClick={() => setRefundDialog({ open: true, sale_id: selectedSale.id, amount: 0, reason: '', refund_method: 'original_payment', notes: '', max_refundable: (selectedSale.amount_received || 0) - (selectedSale.total_refunded || 0) })}
                    variant="outline"
                    className="text-red-600 border-red-300 hover:bg-red-50"
                    data-testid="refund-sale-btn"
                  >
                    <XCircle className="mr-2 h-4 w-4" />Process Refund
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Cases Tab */}
          {activeTab === 'cases' && !selectedCase && (
            <div className="space-y-4" data-testid="cases-content">
              <div className="flex flex-wrap gap-3 mb-6">
                <div className="relative flex-1 min-w-[250px]">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input 
                    placeholder="Search by Case ID, Client Name, or Manager..." 
                    value={caseFilter.search} 
                    onChange={(e) => setCaseFilter({ ...caseFilter, search: e.target.value })} 
                    className="pl-10" 
                    data-testid="case-search" 
                  />
                </div>
                <Select value={caseFilter.case_manager_id} onValueChange={(value) => setCaseFilter({ ...caseFilter, case_manager_id: value === 'all' ? '' : value })}>
                  <SelectTrigger className="w-[200px]" data-testid="case-manager-filter">
                    <SelectValue placeholder="Filter by Manager" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Managers</SelectItem>
                    {caseManagers.map(cm => (
                      <SelectItem key={cm.id} value={cm.id}>{cm.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={caseFilter.status} onValueChange={(value) => setCaseFilter({ ...caseFilter, status: value === 'all' ? '' : value })}>
                  <SelectTrigger className="w-[150px]" data-testid="case-status-filter">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="on_hold">On Hold</SelectItem>
                  </SelectContent>
                </Select>
                {(caseFilter.search || caseFilter.case_manager_id || caseFilter.status) && (
                  <Button variant="outline" onClick={() => setCaseFilter({ search: '', case_manager_id: '', status: '' })} data-testid="clear-case-filters">
                    <XCircle className="h-4 w-4 mr-1" />Clear
                  </Button>
                )}
              </div>
              <div className="text-sm text-slate-500 mb-2">
                Showing {filteredCases.length} of {cases.length} cases
              </div>
              {filteredCases.length === 0 ? (
                <Card className="p-12 text-center"><Briefcase className="h-12 w-12 text-slate-400 mx-auto mb-4" /><p className="text-slate-600">No cases found</p></Card>
              ) : (
                filteredCases.map((caseItem) => (
                  <Card key={caseItem.id} className="p-6 cursor-pointer hover:shadow-md transition-shadow" onClick={() => viewCaseDetails(caseItem)} data-testid={`case-card-${caseItem.id}`}>
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
                        <Button onClick={(e) => { e.stopPropagation(); setReassignDialog({ open: true, case_id: caseItem.id }); }} size="sm" variant="outline" className="mt-2" data-testid={`reassign-${caseItem.id}`}>
                          <Edit className="h-4 w-4 mr-1" />Change Manager
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Pending Assignment Tab */}
          {activeTab === 'pending-assignment' && (
            <div className="space-y-6" data-testid="pending-assignment-content">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm text-slate-500">{unassignedCases.length} case{unassignedCases.length !== 1 ? 's' : ''} awaiting case manager assignment</p>
                </div>
                <Button variant="outline" size="sm" onClick={loadData}>Refresh</Button>
              </div>

              {unassignedCases.length === 0 ? (
                <Card className="p-12 text-center">
                  <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
                  <p className="text-lg font-semibold text-slate-700">All Clear!</p>
                  <p className="text-slate-500 mt-1">All approved cases have been assigned to case managers.</p>
                </Card>
              ) : (
                unassignedCases.map((caseItem) => (
                  <Card key={caseItem.id} className="p-6 border-l-4 border-l-amber-400" data-testid={`unassigned-case-${caseItem.id}`}>
                    <div className="flex flex-col md:flex-row justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-slate-800">{caseItem.case_id}</h3>
                          <Badge className="bg-amber-100 text-amber-700 border-amber-300">Pending Assignment</Badge>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          <div><span className="text-slate-500">Client:</span> <span className="font-medium">{caseItem.client_name}</span></div>
                          <div><span className="text-slate-500">Product:</span> <span className="font-medium">{caseItem.product_name}</span></div>
                          <div><span className="text-slate-500">Partner:</span> <span className="font-medium">{caseItem.partner_name}</span></div>
                          <div><span className="text-slate-500">Step:</span> <span className="font-medium">{caseItem.current_step}</span></div>
                        </div>
                        {/* Sale info */}
                        {(caseItem.sale_fee || caseItem.sale_discount > 0) && (
                          <div className="flex flex-wrap gap-3 mt-2 text-xs">
                            <span className="bg-slate-50 text-slate-600 px-2 py-1 rounded border">Fee: ₹{(caseItem.sale_fee || 0).toLocaleString()}</span>
                            {caseItem.sale_discount > 0 && <span className="bg-emerald-50 text-emerald-700 px-2 py-1 rounded border border-emerald-200">Discount: ₹{caseItem.sale_discount.toLocaleString()}</span>}
                            {caseItem.sale_promo && <span className="bg-purple-50 text-purple-700 px-2 py-1 rounded border border-purple-200">Promo: {caseItem.sale_promo}</span>}
                            <span className={`px-2 py-1 rounded border ${caseItem.sale_payment_status === 'paid' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : caseItem.sale_payment_status === 'partial' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                              Payment: {caseItem.sale_payment_status || 'pending'}
                            </span>
                          </div>
                        )}
                        <p className="text-xs text-slate-400 mt-2">Created: {caseItem.created_at ? new Date(caseItem.created_at).toLocaleString() : 'N/A'}</p>
                      </div>
                      <div className="flex flex-col gap-2 min-w-[220px]">
                        <Label className="text-sm font-medium text-slate-700">Assign Case Manager</Label>
                        <Select onValueChange={(managerId) => {
                          if (managerId) {
                            handleReassignCase(caseItem.id, managerId);
                          }
                        }}>
                          <SelectTrigger data-testid={`assign-manager-${caseItem.id}`}>
                            <SelectValue placeholder="Select Manager" />
                          </SelectTrigger>
                          <SelectContent>
                            {caseManagers.map(cm => (
                              <SelectItem key={cm.id} value={cm.id}>{cm.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
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
              <Button onClick={() => { setActiveTab('cases'); setSelectedCase(null); }} variant="outline"><ArrowRight className="mr-2 h-4 w-4 rotate-180" />Back to Cases</Button>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Case Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div><p className="text-sm text-slate-500">Client</p><p className="font-medium text-slate-800">{selectedCase.client_name}</p></div>
                  <div><p className="text-sm text-slate-500">Email</p><p className="font-medium text-slate-800">{selectedCase.client_email}</p></div>
                  <div><p className="text-sm text-slate-500">Product</p><p className="font-medium text-slate-800">{selectedCase.product_name}</p></div>
                  <div><p className="text-sm text-slate-500">Case Manager</p><p className="font-medium text-slate-800">{selectedCase.case_manager_name}</p></div>
                </div>
              </Card>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Workflow Progress</h3>
                <div className="space-y-3">
                  {selectedCase.steps && selectedCase.steps.map((step, idx) => (
                    <div key={idx} className={`p-4 rounded-lg border-2 ${step.status === 'completed' ? 'bg-green-50 border-green-200' : step.status === 'in_progress' ? 'bg-blue-50 border-blue-300' : 'bg-slate-50 border-slate-200'}`}>
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-semibold text-slate-800">{step.step_order}. {step.step_name}</p>
                          {step.notes && <p className="text-sm text-slate-600 mt-1">{step.notes}</p>}
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
                        <div><p className="font-medium text-slate-800">{doc.filename}</p><p className="text-sm text-slate-600">Step: {doc.step_name}</p><p className="text-sm text-slate-500">Status: {doc.status}</p></div>
                        <Button onClick={() => downloadDocument(doc.id, doc.filename)} size="sm" variant="outline"><Download className="h-4 w-4" /></Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
              {/* Client Information Sheet */}
              <ClientInfoSheetSection caseId={selectedCase?.id} />
            </div>
          )}

          {/* Products Tab */}
          {activeTab === 'intake-builder' && (
            <IntakeFormBuilder token={localStorage.getItem('token')} products={products} />
          )}

          {activeTab === 'products' && (
            <div className="space-y-6" data-testid="products-content">
              <div className="flex justify-end">
                <Button onClick={() => setProductDialog({ open: true, mode: 'create', data: { name: '', description: '', fee: 0, commission_rate: 0, commission_type: 'fixed', commission_tiers: [] } })} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="create-product-btn">
                  <Plus className="mr-2 h-4 w-4" />Create Product
                </Button>
              </div>
              <div className="space-y-4">
                {products.length === 0 ? (
                  <Card className="p-12 text-center"><Settings className="h-12 w-12 text-slate-400 mx-auto mb-4" /><p className="text-slate-600">No products created yet</p></Card>
                ) : (
                  products.map((product) => (
                    <Card key={product.id} className="p-6" data-testid={`product-card-${product.id}`}>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-semibold text-slate-800">{product.name}</h3>
                          <p className="text-sm text-slate-600">{product.description}</p>
                          <div className="flex items-center gap-4 mt-2">
                            <p className="text-sm text-slate-600">Fee: <span className="font-medium">₹{product.fee?.toLocaleString() || product.base_fee?.toLocaleString()}</span></p>
                            <p className="text-sm text-slate-600">Commission: <span className="font-medium">{product.commission_rate}%</span></p>
                            <Badge variant="outline" className="text-xs">{product.commission_type === 'fixed' ? 'Fixed %' : product.commission_type === 'tiered' ? 'Tiered' : 'Custom'}</Badge>
                          </div>
                          {product.commission_type === 'tiered' && product.commission_tiers?.length > 0 && (
                            <div className="mt-2 text-xs text-slate-500">
                              Tiers: {product.commission_tiers.map((t, i) => `${t.min_sales}-${t.max_sales}: ${t.rate}%`).join(' | ')}
                            </div>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <Button onClick={() => openWorkflowEditor(product)} size="sm" className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid={`edit-workflow-${product.id}`}>
                            <Settings className="h-4 w-4 mr-1" />Edit Workflow
                          </Button>
                          <Button onClick={() => setProductDialog({ open: true, mode: 'edit', data: product })} size="sm" variant="outline" data-testid={`edit-product-${product.id}`}><Edit className="h-4 w-4" /></Button>
                          <Button onClick={() => handleDeleteProduct(product.id)} size="sm" variant="destructive" data-testid={`delete-product-${product.id}`}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </div>
                      {product.workflow_steps && product.workflow_steps.length > 0 && (
                        <div className="border-t pt-4">
                          <p className="font-medium mb-3 text-slate-800">Workflow Steps ({product.workflow_steps.length}):</p>
                          <div className="space-y-2">
                            {product.workflow_steps.sort((a, b) => a.step_order - b.step_order).map((step, idx) => (
                              <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                                <span className="w-8 h-8 rounded-full bg-[#2a777a] text-white flex items-center justify-center text-sm font-medium">{step.step_order}</span>
                                <div className="flex-1">
                                  <p className="font-medium text-slate-800">{step.step_name}</p>
                                  {step.required_documents && step.required_documents.length > 0 && <p className="text-xs text-slate-500">{step.required_documents.length} document(s) required</p>}
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
                  <Input placeholder="Search users..." value={userSearchTerm} onChange={(e) => setUserSearchTerm(e.target.value)} className="pl-10" data-testid="user-search" />
                </div>
                <Button onClick={() => setUserDialog({ open: true, mode: 'create', data: { email: '', name: '', password: '', role: 'partner', mobile: '' } })} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="create-user-btn">
                  <UserPlus className="mr-2 h-4 w-4" />Create User
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
                          <div><p className="font-medium text-slate-800">{usr.name}</p><p className="text-sm text-slate-600">{usr.email}</p></div>
                          <div className="flex gap-2">
                            {usr.role !== 'admin' && <Button onClick={() => openTicketForUser(usr)} size="sm" variant="outline" className="text-[#f7620b] border-[#f7620b] hover:bg-[#f7620b]/10" data-testid={`ticket-for-${usr.id}`}><MessageSquare className="h-4 w-4 mr-1" />Ticket</Button>}
                            {usr.role !== 'admin' && <Button onClick={() => handleImpersonate(usr)} size="sm" className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid={`impersonate-${usr.id}`}><Eye className="h-4 w-4 mr-1" />Switch</Button>}
                            <Button onClick={() => setUserDialog({ open: true, mode: 'edit', data: usr })} size="sm" variant="outline" data-testid={`edit-user-${usr.id}`}><Edit className="h-4 w-4" /></Button>
                            {usr.role !== 'admin' && <Button onClick={() => handleDeleteUser(usr.id)} size="sm" variant="destructive" data-testid={`delete-user-${usr.id}`}><Trash2 className="h-4 w-4" /></Button>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Tickets Tab */}
          {activeTab === 'tickets' && !selectedTicket && (
            <div className="space-y-6" data-testid="tickets-content">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="p-4 bg-blue-50 border-blue-200"><p className="text-sm text-slate-600">Total</p><p className="text-2xl font-bold text-blue-700">{ticketStats.total || 0}</p></Card>
                <Card className="p-4 bg-amber-50 border-amber-200"><p className="text-sm text-slate-600">Open</p><p className="text-2xl font-bold text-amber-700">{ticketStats.open || 0}</p></Card>
                <Card className="p-4 bg-purple-50 border-purple-200"><p className="text-sm text-slate-600">In Progress</p><p className="text-2xl font-bold text-purple-700">{ticketStats.in_progress || 0}</p></Card>
                <Card className="p-4 bg-green-50 border-green-200"><p className="text-sm text-slate-600">Resolved</p><p className="text-2xl font-bold text-green-700">{ticketStats.resolved || 0}</p></Card>
                <Card className="p-4 bg-slate-50 border-slate-200"><p className="text-sm text-slate-600">Closed</p><p className="text-2xl font-bold text-slate-700">{ticketStats.closed || 0}</p></Card>
              </div>

              <Card className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2"><Filter className="h-5 w-5" />Filters</h3>
                  <Select value={ticketFilter.status} onValueChange={(v) => setTicketFilter({ ...ticketFilter, status: v })}>
                    <SelectTrigger className="w-36"><SelectValue placeholder="Status" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={ticketFilter.priority} onValueChange={(v) => setTicketFilter({ ...ticketFilter, priority: v })}>
                    <SelectTrigger className="w-36"><SelectValue placeholder="Priority" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Priority</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={ticketFilter.created_by_role} onValueChange={(v) => setTicketFilter({ ...ticketFilter, created_by_role: v })}>
                    <SelectTrigger className="w-36"><SelectValue placeholder="Role" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Roles</SelectItem>
                      <SelectItem value="client">Client</SelectItem>
                      <SelectItem value="partner">Partner</SelectItem>
                      <SelectItem value="case_manager">Case Manager</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={loadTickets} size="sm" variant="outline"><RefreshCw className="h-4 w-4 mr-1" />Refresh</Button>
                </div>
              </Card>

              <div className="space-y-3">
                {allTickets.length === 0 ? (
                  <Card className="p-12 text-center"><MessageSquare className="h-12 w-12 text-slate-400 mx-auto mb-4" /><p className="text-slate-600">No tickets found</p></Card>
                ) : (
                  allTickets
                    .filter(t => !ticketFilter.status || ticketFilter.status === 'all' || t.status === ticketFilter.status)
                    .filter(t => !ticketFilter.priority || ticketFilter.priority === 'all' || t.priority === ticketFilter.priority)
                    .filter(t => !ticketFilter.created_by_role || ticketFilter.created_by_role === 'all' || t.created_by_role === ticketFilter.created_by_role)
                    .map(ticket => (
                    <Card key={ticket.id} className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setSelectedTicket(ticket)}>
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-semibold text-slate-800">{ticket.subject}</h4>
                            {getPriorityBadge(ticket.priority)}
                            {getStatusBadge(ticket.status)}
                          </div>
                          <p className="text-sm text-slate-600 line-clamp-1">{ticket.description}</p>
                          <p className="text-xs text-slate-500 mt-1">By: {ticket.created_by_name} ({ticket.created_by_role}) | {new Date(ticket.created_at).toLocaleString()}</p>
                        </div>
                        <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setSelectedTicket(ticket); }}><Eye className="h-4 w-4" /></Button>
                      </div>
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Ticket Detail View */}
          {activeTab === 'tickets' && selectedTicket && (
            <div className="space-y-6" data-testid="ticket-detail-content">
              <Button onClick={() => setSelectedTicket(null)} variant="outline"><ArrowRight className="mr-2 h-4 w-4 rotate-180" />Back to Tickets</Button>
              
              <Card className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-xl font-semibold text-slate-800">{selectedTicket.subject}</h3>
                      {getPriorityBadge(selectedTicket.priority)}
                      {getStatusBadge(selectedTicket.status)}
                    </div>
                    <p className="text-sm text-slate-600">Category: {selectedTicket.category}</p>
                    <p className="text-sm text-slate-600">Created by: {selectedTicket.created_by_name} ({selectedTicket.created_by_role})</p>
                    <p className="text-sm text-slate-600">Created: {new Date(selectedTicket.created_at).toLocaleString()}</p>
                    {selectedTicket.target_user_ids?.length > 0 && (
                      <p className="text-sm text-slate-600">Assigned to: {selectedTicket.target_user_ids.length} user(s)</p>
                    )}
                    {selectedTicket.target_role && (
                      <p className="text-sm text-slate-600">Target Role: <Badge variant="outline" className="capitalize">{selectedTicket.target_role.replace('_', ' ')}</Badge></p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {selectedTicket.status === 'open' && <Button onClick={() => updateTicketStatus(selectedTicket.id, 'in_progress')} size="sm" className="bg-purple-500 hover:bg-purple-600"><Clock className="mr-1 h-4 w-4" />Start</Button>}
                    {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'closed' && (
                      <Button onClick={() => updateTicketStatus(selectedTicket.id, 'resolved')} size="sm" className="bg-green-500 hover:bg-green-600"><CheckCircle className="mr-1 h-4 w-4" />Resolve</Button>
                    )}
                    {selectedTicket.status !== 'closed' && <Button onClick={() => updateTicketStatus(selectedTicket.id, 'closed')} size="sm" variant="outline"><XCircle className="mr-1 h-4 w-4" />Close</Button>}
                  </div>
                </div>
                
                <div className="p-4 bg-slate-50 rounded-lg mb-4">
                  <p className="text-slate-800">{selectedTicket.description}</p>
                </div>

                {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'closed' && (
                  <div className="mb-4">
                    <Label>Resolution Note (required for resolve/close - min 10 chars)</Label>
                    <Textarea value={resolutionNote} onChange={(e) => setResolutionNote(e.target.value)} placeholder="Add a resolution note when resolving or closing this ticket..." rows={2} data-testid="resolution-note-input" />
                  </div>
                )}

                {selectedTicket.resolution_note && (
                  <div className="p-4 bg-green-50 rounded-lg mb-4 border border-green-200">
                    <p className="text-sm font-medium text-green-800">Resolution Note:</p>
                    <p className="text-green-700">{selectedTicket.resolution_note}</p>
                    {selectedTicket.resolved_by_name && <p className="text-xs text-green-600 mt-1">Resolved by {selectedTicket.resolved_by_name} on {new Date(selectedTicket.resolved_at).toLocaleString()}</p>}
                  </div>
                )}
              </Card>

              {/* Attachments Card */}
              <Card className="p-6">
                <h4 className="font-semibold mb-4 text-slate-800 flex items-center gap-2">
                  <FileText className="h-5 w-5" /> Attachments ({selectedTicket.attachments?.length || 0})
                </h4>
                <div className="space-y-2 mb-4">
                  {selectedTicket.attachments?.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No attachments</p>
                  ) : (
                    selectedTicket.attachments?.map((att, idx) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg hover:bg-slate-50">
                        <div>
                          <p className="font-medium text-slate-800">{att.filename}</p>
                          <p className="text-xs text-slate-500">
                            Uploaded by {att.uploaded_by_name} on {new Date(att.uploaded_at).toLocaleString()}
                            {att.file_size && ` • ${(att.file_size / 1024).toFixed(1)} KB`}
                          </p>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => downloadTicketAttachment(selectedTicket.id, att.id, att.filename)} data-testid={`download-attachment-${idx}`}>
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
                {selectedTicket.status !== 'closed' && (
                  <div className="pt-3 border-t">
                    <Label className="text-sm mb-2 block">Upload Attachment (max 10MB)</Label>
                    <Input
                      type="file"
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          uploadTicketAttachment(selectedTicket.id, e.target.files[0]);
                          e.target.value = '';
                        }
                      }}
                      className="cursor-pointer"
                      data-testid="ticket-attachment-input"
                    />
                  </div>
                )}
              </Card>

              {/* Messages Card */}
              <Card className="p-6">
                <h4 className="font-semibold mb-4 text-slate-800">Messages ({selectedTicket.messages?.length || 0})</h4>
                <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
                  {selectedTicket.messages?.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No messages yet</p>
                  ) : (
                    selectedTicket.messages?.map((msg, idx) => (
                      <div key={idx} className={`p-3 rounded-lg ${msg.user_role === 'admin' ? 'bg-blue-50 ml-8' : 'bg-slate-50 mr-8'}`}>
                        <div className="flex justify-between items-center mb-1">
                          <p className="text-sm font-medium text-slate-800">{msg.user_name} <span className="text-slate-500">({msg.user_role})</span></p>
                          <p className="text-xs text-slate-500">{new Date(msg.created_at).toLocaleString()}</p>
                        </div>
                        <p className="text-slate-700">{msg.message}</p>
                      </div>
                    ))
                  )}
                </div>
                {selectedTicket.status !== 'closed' && (
                  <div className="flex gap-2">
                    <Textarea value={ticketReplyText} onChange={(e) => setTicketReplyText(e.target.value)} placeholder="Type your reply..." rows={2} className="flex-1" data-testid="ticket-reply-input" />
                    <Button onClick={() => addTicketReply(selectedTicket.id)} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="send-reply-btn">Send</Button>
                  </div>
                )}
              </Card>

              {/* Activity Log Card */}
              <Card className="p-6">
                <h4 className="font-semibold mb-4 text-slate-800 flex items-center gap-2">
                  <RefreshCw className="h-5 w-5" /> Activity Log ({selectedTicket.activity_log?.length || 0})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedTicket.activity_log?.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No activity logged</p>
                  ) : (
                    [...(selectedTicket.activity_log || [])].reverse().map((activity, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-2 border-l-2 border-slate-300 pl-4">
                        <div className="flex-1">
                          <p className="text-sm text-slate-800">{typeof activity.details === 'object' ? Object.entries(activity.details).map(([k,v]) => `${k}: ${v}`).join(', ') : activity.details}</p>
                          <p className="text-xs text-slate-500">{new Date(activity.timestamp).toLocaleString()}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          )}

          {/* Refunds Tab */}
          {activeTab === 'refunds' && (
            <div className="space-y-6" data-testid="refunds-content">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-slate-800">Refund History</h3>
                <Badge className="bg-slate-100 text-slate-700">{refunds.length} total</Badge>
              </div>

              {refunds.length === 0 ? (
                <Card className="p-12 text-center">
                  <CheckCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <p className="text-slate-600">No refunds processed yet</p>
                  <p className="text-sm text-slate-400 mt-1">Refunds can be processed from the Sale Detail view</p>
                </Card>
              ) : (
                <Card className="p-6">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-3">Date</th>
                          <th className="text-left p-3">Client</th>
                          <th className="text-right p-3">Original Fee</th>
                          <th className="text-right p-3">Refund Amount</th>
                          <th className="text-left p-3">Reason</th>
                          <th className="text-left p-3">Method</th>
                          <th className="text-center p-3">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {refunds.map(refund => (
                          <tr key={refund.id} className="border-b hover:bg-slate-50">
                            <td className="p-3">{new Date(refund.created_at).toLocaleDateString()}</td>
                            <td className="p-3 font-medium">{refund.client_name}</td>
                            <td className="p-3 text-right">{formatCurrency(refund.original_fee)}</td>
                            <td className="p-3 text-right text-red-600 font-bold">{formatCurrency(refund.amount)}</td>
                            <td className="p-3 max-w-[200px] truncate">{refund.reason}</td>
                            <td className="p-3 capitalize">{refund.refund_method?.replace('_', ' ')}</td>
                            <td className="p-3 text-center">
                              <Badge className={refund.status === 'processed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>{refund.status}</Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6" data-testid="settings-content">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-6 text-slate-800 flex items-center gap-2">
                  <Settings className="h-5 w-5" /> Case Manager Permissions
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-800">Allow Workflow Customization</p>
                      <p className="text-sm text-slate-600">When enabled, Case Managers can request additional documents for individual client cases on specific workflow steps.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={systemSettings.allow_case_manager_workflow_customization}
                        onChange={(e) => updateSystemSettings({ ...systemSettings, allow_case_manager_workflow_customization: e.target.checked })}
                        className="sr-only peer"
                        data-testid="cm-workflow-toggle"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#2a777a]/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#2a777a]"></div>
                    </label>
                  </div>
                  {systemSettings.allow_case_manager_workflow_customization && (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                      <p className="text-sm text-green-800">
                        <CheckCircle className="h-4 w-4 inline mr-1" />
                        Case Managers can now request additional documents for their cases. They can add documents with custom names, descriptions, due dates, and validity requirements.
                      </p>
                    </div>
                  )}
                  {!systemSettings.allow_case_manager_workflow_customization && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-sm text-amber-800">
                        <XCircle className="h-4 w-4 inline mr-1" />
                        Workflow customization is currently disabled. Only Admins can modify workflow documents.
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              {/* Currency Settings */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-6 text-slate-800 flex items-center gap-2">
                  <DollarSign className="h-5 w-5" /> Currency & Exchange Rate
                </h3>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Base Currency</Label>
                      <Input value="USD" disabled className="bg-slate-50" />
                    </div>
                    <div>
                      <Label>USD to INR Exchange Rate</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={systemSettings.exchange_rate_usd_to_inr || 83.50}
                        onChange={(e) => setSystemSettings({ ...systemSettings, exchange_rate_usd_to_inr: parseFloat(e.target.value) || 83.50 })}
                        data-testid="exchange-rate-input"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-800">Show Dual Currency (USD + INR)</p>
                      <p className="text-sm text-slate-600">Display amounts in both USD and INR across dashboards and reports.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={systemSettings.show_dual_currency || false}
                        onChange={(e) => {
                          const updated = { ...systemSettings, show_dual_currency: e.target.checked };
                          setSystemSettings(updated);
                          updateSystemSettings(updated);
                          setShowINR(e.target.checked);
                        }}
                        className="sr-only peer"
                        data-testid="dual-currency-toggle"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#2a777a]/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#2a777a]"></div>
                    </label>
                  </div>
                  <Button onClick={() => updateSystemSettings(systemSettings)} className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-exchange-rate-btn">
                    Save Exchange Rate
                  </Button>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Last Updated</h3>
                <div className="text-sm text-slate-600">
                  {systemSettings.updated_at ? (
                    <p>Settings last modified on {new Date(systemSettings.updated_at).toLocaleString()} by {systemSettings.updated_by_name || 'System'}</p>
                  ) : (
                    <p>Using default settings</p>
                  )}
                </div>
              </Card>
            </div>
          )}

          {/* Payment Reminders Tab */}
          {activeTab === 'reminders' && <PaymentReminders token={localStorage.getItem('token')} />}

          {activeTab === 'bulk-ops' && <BulkOperations token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'sla-tracker' && <SLATracker token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'case-transfer' && <CaseTransfer token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'cm-performance' && <CMPerformance token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'revenue-forecast' && <RevenueForecasting token={localStorage.getItem('token')} />}
          {activeTab === 'knowledge-base' && <KnowledgeBase token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'surveys' && <SatisfactionSurvey token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'appointments' && <Appointments token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'canned-responses' && <CannedResponses token={localStorage.getItem('token')} />}
          {activeTab === 'referrals' && <ReferralProgram token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'greetings' && <ClientGreetings token={localStorage.getItem('token')} />}
          {activeTab === 'conversion-funnel' && <ConversionFunnel token={localStorage.getItem('token')} />}
          {activeTab === 'country-product' && <CountryProductAnalytics token={localStorage.getItem('token')} />}
          {activeTab === 'commission-analytics' && <CommissionAnalytics token={localStorage.getItem('token')} role="admin" />}
          {activeTab === 'pre-assessments' && <PreAssessmentQueue />}
          {activeTab === 'approval-center' && <ApprovalCenter token={localStorage.getItem('token')} onNavigate={(tab) => setActiveTab(tab)} />}
          {activeTab === 'refund-manager' && <RefundManager token={localStorage.getItem('token')} />}
          {activeTab === 'revenue-dashboard' && <RevenueDashboard token={localStorage.getItem('token')} />}
          {activeTab === 'report-builder' && <ReportBuilder token={localStorage.getItem('token')} />}
          {activeTab === 'email-digest' && <EmailDigest token={localStorage.getItem('token')} />}
          {activeTab === 'fee-calculator' && <FeeCalculator token={localStorage.getItem('token')} role="admin" />}

      {/* Product Dialog */}
      <Dialog open={productDialog.open} onOpenChange={(open) => setProductDialog({ ...productDialog, open })}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{productDialog.mode === 'create' ? 'Create' : 'Edit'} Product</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><Label>Product Name</Label><Input value={productDialog.data?.name || ''} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, name: e.target.value } })} data-testid="product-name-input" /></div>
            <div><Label>Description</Label><Textarea value={productDialog.data?.description || ''} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, description: e.target.value } })} data-testid="product-description-input" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Fee (₹)</Label><Input type="number" value={productDialog.data?.base_fee || productDialog.data?.fee || 0} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, base_fee: parseFloat(e.target.value) || 0, fee: parseFloat(e.target.value) || 0 } })} data-testid="product-fee-input" /></div>
              <div>
                <Label>Commission Type</Label>
                <Select value={productDialog.data?.commission_type || 'fixed'} onValueChange={(value) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_type: value } })}>
                  <SelectTrigger data-testid="commission-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed">Fixed Percentage</SelectItem>
                    <SelectItem value="tiered">Tiered (Volume-based)</SelectItem>
                    <SelectItem value="custom">Custom (Per Partner)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {productDialog.data?.commission_type === 'fixed' && (
              <div><Label>Commission Rate (%)</Label><Input type="number" value={productDialog.data?.commission_rate || 0} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_rate: parseFloat(e.target.value) || 0 } })} data-testid="product-commission-input" /></div>
            )}
            {productDialog.data?.commission_type === 'tiered' && (
              <div className="p-4 bg-slate-50 rounded-lg">
                <Label className="mb-2 block">Commission Tiers</Label>
                <p className="text-xs text-slate-500 mb-3">Define tiers based on total sales count</p>
                <div className="space-y-2 mb-3">
                  {(productDialog.data?.commission_tiers || []).map((tier, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm p-2 bg-white rounded border">
                      <span className="text-slate-600">{tier.min_sales}-{tier.max_sales} sales:</span>
                      <span className="font-medium text-[#2a777a]">{tier.rate}%</span>
                      <Button size="sm" variant="ghost" onClick={() => { const tiers = (productDialog.data?.commission_tiers || []).filter((_, i) => i !== idx); setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_tiers: tiers } }); }} className="h-6 w-6 p-0 ml-auto"><Trash2 className="h-3 w-3 text-red-500" /></Button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="Min" type="number" className="w-20" id="tier-min" />
                  <Input placeholder="Max" type="number" className="w-20" id="tier-max" />
                  <Input placeholder="%" type="number" className="w-16" id="tier-rate" />
                  <Button size="sm" variant="outline" onClick={() => {
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
                  }}>Add</Button>
                </div>
              </div>
            )}
            {productDialog.data?.commission_type === 'custom' && (
              <div className="p-4 bg-slate-50 rounded-lg">
                <Label className="mb-2 block">Custom Commission</Label>
                <p className="text-xs text-slate-500 mb-2">Commission will be set individually for each partner</p>
                <div><Label>Default Rate (%)</Label><Input type="number" value={productDialog.data?.commission_rate || 0} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_rate: parseFloat(e.target.value) || 0 } })} /></div>
              </div>
            )}
            {productDialog.mode === 'edit' && (
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <Label className="mb-2 block text-amber-800"><Calendar className="inline h-4 w-4 mr-1" />Commission Effective Date</Label>
                <p className="text-xs text-amber-700 mb-2">When should the new commission structure take effect? Leave blank for immediate effect.</p>
                <Input type="date" value={productDialog.data?.commission_effective_from?.split('T')[0] || ''} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, commission_effective_from: e.target.value ? new Date(e.target.value).toISOString() : '' } })} />
              </div>
            )}
            {productDialog.mode === 'edit' && productDialog.data?.commission_history?.length > 0 && (
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <Label className="mb-2 block text-slate-800"><RefreshCw className="inline h-4 w-4 mr-1" />Commission History</Label>
                <div className="max-h-32 overflow-y-auto space-y-2">
                  {productDialog.data.commission_history.slice().reverse().map((entry, idx) => (
                    <div key={idx} className="text-xs p-2 bg-white rounded border border-slate-200">
                      <div className="flex justify-between">
                        <span className="font-medium">{entry.new_type}: {entry.new_rate}%</span>
                        <span className="text-slate-500">Effective: {new Date(entry.effective_from).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-500">Changed on {new Date(entry.changed_at).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <Button onClick={() => handleSaveProduct(productDialog.data)} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-product-btn">Save Product</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Workflow Editor Dialog */}
      <Dialog open={workflowDialog.open} onOpenChange={(open) => setWorkflowDialog({ ...workflowDialog, open })}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Edit Workflow - {workflowDialog.product?.name}</DialogTitle></DialogHeader>
          <div className="space-y-6 py-4">
            <div className="flex justify-between items-center gap-2">
              <p className="text-sm text-slate-600">Define the steps for this product workflow.</p>
              <div className="flex gap-2">
                {workflowDialog.product?.workflow_steps?.length > 0 && (
                  <Button onClick={aiBulkSuggest} disabled={aiSuggesting} variant="outline" className="border-purple-300 text-purple-700 hover:bg-purple-50" data-testid="ai-bulk-suggest-btn">
                    {aiSuggesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}AI Auto-Fill Docs
                  </Button>
                )}
                <Button onClick={() => openStepEditor('create')} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="add-step-btn"><Plus className="mr-2 h-4 w-4" />Add Step</Button>
              </div>
            </div>
            {workflowDialog.product?.workflow_steps?.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed rounded-lg"><Settings className="h-12 w-12 text-slate-400 mx-auto mb-4" /><p className="text-slate-600">No workflow steps defined</p></div>
            ) : (
              <div className="space-y-3">
                {workflowDialog.product?.workflow_steps?.sort((a, b) => a.step_order - b.step_order).map((step, idx) => (
                  <div key={idx} className="p-4 border rounded-lg bg-white shadow-sm" data-testid={`workflow-step-${idx}`}>
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-3 flex-1">
                        <span className="w-10 h-10 rounded-full bg-[#2a777a] text-white flex items-center justify-center font-bold">{step.step_order}</span>
                        <div className="flex-1">
                          <h4 className="font-semibold text-slate-800">{step.step_name}</h4>
                          {step.description && <p className="text-sm text-slate-600 mt-1">{step.description}</p>}
                          {step.duration_days && <p className="text-xs text-slate-500 mt-1">Duration: {step.duration_days} days</p>}
                          {step.required_documents && step.required_documents.length > 0 && (
                            <div className="mt-2"><p className="text-xs font-medium text-slate-700">Required Documents:</p><div className="flex flex-wrap gap-1 mt-1">{step.required_documents.map((doc, docIdx) => <Badge key={docIdx} variant="outline" className="text-xs">{doc.doc_name || doc.name || 'Unnamed'} {doc.is_mandatory && '*'}</Badge>)}</div></div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => openStepEditor('edit', idx)} data-testid={`edit-step-${idx}`}><Edit className="h-4 w-4" /></Button>
                        <Button size="sm" variant="destructive" onClick={() => deleteWorkflowStep(step.step_order)} data-testid={`delete-step-${idx}`}><Trash2 className="h-4 w-4" /></Button>
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
          <DialogHeader><DialogTitle>{stepEditorDialog.mode === 'create' ? 'Add New' : 'Edit'} Workflow Step</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Step Name *</Label><Input value={stepEditorDialog.stepData.step_name} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, step_name: e.target.value } })} placeholder="e.g., Document Verification" data-testid="step-name-input" /></div>
              <div><Label>Step Order</Label><Input type="number" value={stepEditorDialog.stepData.step_order} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, step_order: parseInt(e.target.value) || 1 } })} data-testid="step-order-input" /></div>
            </div>
            <div><Label>Description</Label><Textarea value={stepEditorDialog.stepData.description} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, description: e.target.value } })} placeholder="Describe what happens in this step..." rows={2} data-testid="step-description-input" /></div>
            <div><Label>Duration (days)</Label><Input type="number" value={stepEditorDialog.stepData.duration_days} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, duration_days: e.target.value } })} placeholder="Estimated days to complete" data-testid="step-duration-input" /></div>
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3 text-slate-800">Document Requirements</h4>
              {stepEditorDialog.stepData.required_documents.length > 0 && (
                <div className="space-y-2 mb-4">
                  {stepEditorDialog.stepData.required_documents.map((doc, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-blue-50 rounded-lg">
                      <div>
                        <p className="font-medium text-slate-800">{doc.doc_name}</p>
                        <p className="text-xs text-slate-600">{doc.description}</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {doc.is_mandatory && <Badge className="text-xs bg-red-100 text-red-700">Mandatory</Badge>}
                          {doc.doc_type && <Badge variant="outline" className="text-xs">{doc.doc_type}</Badge>}
                          {doc.has_expiry && doc.expiry_date && <Badge className="text-xs bg-amber-100 text-amber-700">Expires: {doc.expiry_date}</Badge>}
                          {doc.has_expiry && doc.validity_months && <Badge className="text-xs bg-blue-100 text-blue-700">Valid: {doc.validity_months} months</Badge>}
                        </div>
                      </div>
                      <Button size="sm" variant="ghost" onClick={() => removeDocFromStep(idx)}><XCircle className="h-4 w-4 text-red-500" /></Button>
                    </div>
                  ))}
                </div>
              )}
              <div className="p-4 bg-slate-50 rounded-lg space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="text-sm">Document Name *</Label><Input value={stepEditorDialog.newDoc.doc_name} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, doc_name: e.target.value } })} placeholder="e.g., Passport Copy" data-testid="doc-name-input" /></div>
                  <div>
                    <Label className="text-sm">Document Type</Label>
                    <Select value={stepEditorDialog.newDoc.doc_type || ''} onValueChange={(value) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, doc_type: value === 'none' ? '' : value } })}>
                      <SelectTrigger data-testid="doc-type-select"><SelectValue placeholder="Select type" /></SelectTrigger>
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
                <div><Label className="text-sm">Description</Label><Input value={stepEditorDialog.newDoc.description} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, description: e.target.value } })} placeholder="Additional info..." data-testid="doc-description-input" /></div>
                
                {/* Expiry/Validity Section */}
                <div className="border-t pt-3 mt-2">
                  <label className="flex items-center gap-2 text-sm mb-2">
                    <input type="checkbox" checked={stepEditorDialog.newDoc.has_expiry} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, has_expiry: e.target.checked, expiry_date: '', validity_months: '' } })} className="rounded" data-testid="doc-expiry-checkbox" />
                    <span className="font-medium">Set Expiry/Validity</span>
                  </label>
                  {stepEditorDialog.newDoc.has_expiry && (
                    <div className="grid grid-cols-2 gap-3 mt-2">
                      <div>
                        <Label className="text-sm">Specific Expiry Date</Label>
                        <Input type="date" value={stepEditorDialog.newDoc.expiry_date} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, expiry_date: e.target.value, validity_months: '' } })} data-testid="doc-expiry-date-input" />
                      </div>
                      <div>
                        <Label className="text-sm">OR Validity (months)</Label>
                        <Input type="number" placeholder="e.g., 6" value={stepEditorDialog.newDoc.validity_months} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, validity_months: e.target.value, expiry_date: '' } })} data-testid="doc-validity-months-input" />
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2">
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={stepEditorDialog.newDoc.is_mandatory} onChange={(e) => setStepEditorDialog({ ...stepEditorDialog, newDoc: { ...stepEditorDialog.newDoc, is_mandatory: e.target.checked } })} className="rounded" data-testid="doc-mandatory-checkbox" />Mandatory Document</label>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={aiSuggestDocs} disabled={aiSuggesting} variant="outline" className="border-purple-300 text-purple-700 hover:bg-purple-50" data-testid="ai-suggest-docs-btn">
                      {aiSuggesting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Sparkles className="h-4 w-4 mr-1" />}AI Suggest
                    </Button>
                    <Button size="sm" onClick={addDocToStep} variant="outline" data-testid="add-doc-btn"><Plus className="h-4 w-4 mr-1" />Add Document</Button>
                  </div>
                </div>
              </div>
            </div>
            <Button onClick={saveWorkflowStep} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-step-btn">{stepEditorDialog.mode === 'create' ? 'Add Step' : 'Update Step'}</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* User Dialog */}
      <Dialog open={userDialog.open} onOpenChange={(open) => setUserDialog({ ...userDialog, open })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{userDialog.mode === 'create' ? 'Create New User' : 'Edit User Profile'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {userDialog.mode === 'edit' && (
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#2a777a] rounded-full flex items-center justify-center text-white font-bold text-lg">
                    {(userDialog.data?.name || '?')[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{userDialog.data?.name}</p>
                    <p className="text-sm text-slate-500">{userDialog.data?.role?.replace('_', ' ')} &middot; {userDialog.data?.status || 'active'}</p>
                  </div>
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Name *</Label><Input value={userDialog.data?.name || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, name: e.target.value } })} data-testid="user-name-input" /></div>
              <div><Label>Mobile</Label><Input value={userDialog.data?.mobile || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, mobile: e.target.value } })} data-testid="user-mobile-input" /></div>
            </div>
            <div><Label>Email *</Label><Input type="email" value={userDialog.data?.email || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, email: e.target.value } })} data-testid="user-email-input" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Role</Label>
                <Select value={userDialog.data?.role || 'partner'} onValueChange={(value) => setUserDialog({ ...userDialog, data: { ...userDialog.data, role: value } })}>
                  <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="admin">Admin</SelectItem><SelectItem value="case_manager">Case Manager</SelectItem><SelectItem value="partner">Partner</SelectItem><SelectItem value="client">Client</SelectItem></SelectContent>
                </Select>
              </div>
              {(userDialog.data?.role === 'partner' || userDialog.data?.role === 'case_manager') && (
                <div>
                  <Label>Commission Rate (%)</Label>
                  <Input type="number" step="0.1" min="0" max="100" value={userDialog.data?.commission_rate || 0} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, commission_rate: parseFloat(e.target.value) || 0 } })} data-testid="user-commission-input" />
                </div>
              )}
            </div>
            {userDialog.mode === 'edit' && (
              <div>
                <Label>Status</Label>
                <Select value={userDialog.data?.status || 'active'} onValueChange={(value) => setUserDialog({ ...userDialog, data: { ...userDialog.data, status: value } })}>
                  <SelectTrigger data-testid="user-status-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="active">Active</SelectItem><SelectItem value="inactive">Inactive</SelectItem><SelectItem value="suspended">Suspended</SelectItem></SelectContent>
                </Select>
              </div>
            )}
            <div className="border-t pt-4">
              <Label className="text-slate-700 font-medium">{userDialog.mode === 'edit' ? 'Reset Password' : 'Password *'}</Label>
              <p className="text-xs text-slate-500 mb-2">{userDialog.mode === 'edit' ? 'Leave blank to keep current password. Min 6 characters.' : 'Minimum 6 characters.'}</p>
              <Input type="password" placeholder={userDialog.mode === 'edit' ? 'Enter new password...' : 'Password'} value={userDialog.data?.password || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, password: e.target.value } })} data-testid="user-password-input" />
            </div>
            <Button onClick={() => handleSaveUser(userDialog.data)} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-user-btn">{userDialog.mode === 'create' ? 'Create User' : 'Update User'}</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Ticket Dialog */}
      <Dialog open={ticketDialog.open} onOpenChange={(open) => setTicketDialog({ ...ticketDialog, open })}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Create Support Ticket</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><Label>Subject</Label><Input value={ticketDialog.subject} onChange={(e) => setTicketDialog({ ...ticketDialog, subject: e.target.value })} data-testid="ticket-subject-input" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Category</Label>
                <Select value={ticketDialog.category} onValueChange={(value) => setTicketDialog({ ...ticketDialog, category: value })}>
                  <SelectTrigger data-testid="ticket-category-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="general">General</SelectItem><SelectItem value="document">Document</SelectItem><SelectItem value="payment">Payment</SelectItem><SelectItem value="technical">Technical</SelectItem></SelectContent>
                </Select>
              </div>
              <div>
                <Label>Priority</Label>
                <Select value={ticketDialog.priority} onValueChange={(value) => setTicketDialog({ ...ticketDialog, priority: value })}>
                  <SelectTrigger data-testid="ticket-priority-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="low">Low</SelectItem><SelectItem value="medium">Medium</SelectItem><SelectItem value="high">High</SelectItem><SelectItem value="urgent">Urgent</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>Description</Label><Textarea value={ticketDialog.description} onChange={(e) => setTicketDialog({ ...ticketDialog, description: e.target.value })} rows={4} data-testid="ticket-description-input" /></div>
            
            {/* Assignment Section */}
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3 text-slate-800">Assignment (Optional)</h4>
              <p className="text-xs text-slate-500 mb-3">Assign to specific users or a role. If left empty, admins will be notified.</p>
              
              <div className="space-y-3">
                <div>
                  <Label>Target Role</Label>
                  <Select value={ticketDialog.target_role} onValueChange={(value) => setTicketDialog({ ...ticketDialog, target_role: value === 'none' ? '' : value })}>
                    <SelectTrigger data-testid="ticket-target-role-select"><SelectValue placeholder="Select target role" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None (Admins)</SelectItem>
                      <SelectItem value="case_manager">Case Managers</SelectItem>
                      <SelectItem value="partner">Partners</SelectItem>
                      <SelectItem value="client">Clients</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label>Assign to Specific Users</Label>
                  <div className="max-h-32 overflow-y-auto border rounded-lg p-2 mt-1 space-y-1">
                    {allUsers.filter(u => u.role !== 'admin').map(usr => (
                      <label key={usr.id} className="flex items-center gap-2 p-1 hover:bg-slate-50 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={ticketDialog.target_user_ids.includes(usr.id)}
                          onChange={(e) => {
                            const newIds = e.target.checked
                              ? [...ticketDialog.target_user_ids, usr.id]
                              : ticketDialog.target_user_ids.filter(id => id !== usr.id);
                            setTicketDialog({ ...ticketDialog, target_user_ids: newIds });
                          }}
                          className="rounded"
                        />
                        <span className="text-sm">{usr.name}</span>
                        <Badge variant="outline" className="text-xs capitalize ml-auto">{usr.role.replace('_', ' ')}</Badge>
                      </label>
                    ))}
                  </div>
                  {ticketDialog.target_user_ids.length > 0 && (
                    <p className="text-xs text-slate-500 mt-1">{ticketDialog.target_user_ids.length} user(s) selected</p>
                  )}
                </div>
              </div>
            </div>
            
            <Button onClick={handleCreateTicket} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="create-ticket-btn">Create Ticket</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reassign Dialog */}
      <Dialog open={reassignDialog.open} onOpenChange={(open) => setReassignDialog({ ...reassignDialog, open })}>
        <DialogContent>
          <DialogHeader><DialogTitle>Reassign Case Manager</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <Select onValueChange={(value) => handleReassignCase(reassignDialog.case_id, value)}>
              <SelectTrigger data-testid="reassign-manager-select"><SelectValue placeholder="Select new case manager" /></SelectTrigger>
              <SelectContent>{caseManagers.map((manager) => <SelectItem key={manager.id} value={manager.id}>{manager.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </DialogContent>
      </Dialog>

      {/* Client Credentials Dialog */}
      <Dialog open={clientCredentialsDialog.open} onOpenChange={(open) => setClientCredentialsDialog({ ...clientCredentialsDialog, open })}>
        <DialogContent>
          <DialogHeader><DialogTitle>Client Login Credentials Created</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            {clientCredentialsDialog.credentials && (
              <>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm font-medium text-green-800 mb-3">{clientCredentialsDialog.credentials.message}</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600 w-20">Name:</span>
                    <span className="font-medium text-slate-800">{clientCredentialsDialog.credentials.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600 w-20">Email:</span>
                    <code className="bg-white px-2 py-1 rounded text-sm font-mono border">{clientCredentialsDialog.credentials.email}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600 w-20">Password:</span>
                    <code className="bg-white px-2 py-1 rounded text-sm font-mono border">{clientCredentialsDialog.credentials.password}</code>
                  </div>
                </div>
              </div>
              <div className="border-t pt-3">
                <p className="text-sm font-medium text-slate-700 mb-2">Share credentials via:</p>
                <div className="grid grid-cols-3 gap-2">
                  <Button variant="outline" size="sm" data-testid="copy-credentials-btn" onClick={() => {
                    const text = `LEAMSS Portal Credentials\nName: ${clientCredentialsDialog.credentials.name}\nEmail: ${clientCredentialsDialog.credentials.email}\nPassword: ${clientCredentialsDialog.credentials.password}\nLogin: ${window.location.origin}`;
                    navigator.clipboard.writeText(text);
                    toast.success('Credentials copied to clipboard!');
                  }}>
                    <Copy className="h-4 w-4 mr-1" />Copy
                  </Button>
                  <Button variant="outline" size="sm" data-testid="email-credentials-btn" onClick={() => {
                    const subject = encodeURIComponent('Your LEAMSS Portal Login Credentials');
                    const body = encodeURIComponent(`Dear ${clientCredentialsDialog.credentials.name},\n\nYour LEAMSS Portal login credentials:\n\nEmail: ${clientCredentialsDialog.credentials.email}\nPassword: ${clientCredentialsDialog.credentials.password}\n\nLogin URL: ${window.location.origin}\n\nPlease change your password after first login.\n\nRegards,\nLEAMSS Team`);
                    window.open(`mailto:${clientCredentialsDialog.credentials.email}?subject=${subject}&body=${body}`);
                  }}>
                    <Mail className="h-4 w-4 mr-1" />Email
                  </Button>
                  <Button variant="outline" size="sm" data-testid="whatsapp-credentials-btn" onClick={() => {
                    const text = encodeURIComponent(`*LEAMSS Portal Credentials*\nName: ${clientCredentialsDialog.credentials.name}\nEmail: ${clientCredentialsDialog.credentials.email}\nPassword: ${clientCredentialsDialog.credentials.password}\nLogin: ${window.location.origin}`);
                    window.open(`https://wa.me/?text=${text}`, '_blank');
                  }}>
                    <MessageSquare className="h-4 w-4 mr-1" />WhatsApp
                  </Button>
                </div>
              </div>
              </>
            )}
            <Button onClick={() => setClientCredentialsDialog({ open: false, credentials: null })} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white">Done</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Rejection Reason Dialog */}
      <Dialog open={rejectionDialog.open} onOpenChange={(open) => setRejectionDialog({ ...rejectionDialog, open })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>Reject Sale</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-slate-600">Please provide a reason for rejecting this sale. This will be visible in reports.</p>
            <div>
              <Label>Rejection Reason <span className="text-red-500">*</span></Label>
              <Textarea
                value={rejectionDialog.reason}
                onChange={(e) => setRejectionDialog({ ...rejectionDialog, reason: e.target.value })}
                rows={3}
                placeholder="Enter the reason for rejection (minimum 5 characters)..."
                data-testid="rejection-reason-input"
              />
              <p className="text-xs text-slate-400 mt-1">{rejectionDialog.reason.length}/5 characters minimum</p>
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setRejectionDialog({ open: false, sale_id: null, reason: '' })} variant="outline" className="flex-1">Cancel</Button>
              <Button
                onClick={handleConfirmRejection}
                variant="destructive"
                className="flex-1"
                disabled={rejectionDialog.reason.trim().length < 5}
                data-testid="confirm-rejection-btn"
              >
                <XCircle className="mr-2 h-4 w-4" />Confirm Rejection
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Refund Dialog */}
      <Dialog open={refundDialog.open} onOpenChange={(open) => setRefundDialog({ ...refundDialog, open })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-red-700"><XCircle className="h-5 w-5" />Process Refund</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-700">Refunds will automatically reduce the amount received and recalculate partner commission.</p>
              {refundDialog.max_refundable > 0 && (
                <p className="text-xs text-red-600 mt-1">Max refundable: ${refundDialog.max_refundable?.toFixed(2)}</p>
              )}
            </div>
            <div>
              <Label>Refund Amount ($) <span className="text-red-500">*</span></Label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                max={refundDialog.max_refundable || undefined}
                value={refundDialog.amount || ''}
                onChange={(e) => setRefundDialog({ ...refundDialog, amount: parseFloat(e.target.value) || 0 })}
                placeholder="Enter refund amount"
                data-testid="refund-amount-input"
              />
            </div>
            <div>
              <Label>Reason <span className="text-red-500">*</span></Label>
              <Textarea
                value={refundDialog.reason}
                onChange={(e) => setRefundDialog({ ...refundDialog, reason: e.target.value })}
                rows={3}
                placeholder="Reason for refund (min 5 characters)..."
                data-testid="refund-reason-input"
              />
            </div>
            <div>
              <Label>Refund Method</Label>
              <Select value={refundDialog.refund_method} onValueChange={(v) => setRefundDialog({ ...refundDialog, refund_method: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="original_payment">Original Payment Method</SelectItem>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="credit">Account Credit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes (optional)</Label>
              <Input
                value={refundDialog.notes}
                onChange={(e) => setRefundDialog({ ...refundDialog, notes: e.target.value })}
                placeholder="Additional notes..."
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setRefundDialog({ open: false, sale_id: null, amount: 0, reason: '', refund_method: 'original_payment', notes: '' })} variant="outline" className="flex-1">Cancel</Button>
              <Button
                onClick={handleRefund}
                variant="destructive"
                className="flex-1"
                disabled={!refundDialog.amount || refundDialog.amount <= 0 || refundDialog.reason.trim().length < 5}
                data-testid="confirm-refund-btn"
              >
                Confirm Refund
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
};

export default AdminDashboard;
