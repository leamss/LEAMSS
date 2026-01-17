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
import QuickActions from '@/components/QuickActions';
import { 
  LayoutDashboard, FileText, Users, Briefcase, LogOut, Plus, 
  Download, Edit, Trash2, UserPlus, Eye, ArrowRight, Settings,
  Search, DollarSign, TrendingUp, CheckCircle, XCircle, Clock,
  MessageSquare, Filter, Calendar, RefreshCw, AlertTriangle
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
  
  // Dialogs
  const [productDialog, setProductDialog] = useState({ open: false, mode: 'create', data: null });
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
      
      const response = await axios.post(`${API}/admin/impersonate/${targetUser.id}`, {}, getAuthHeader());
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
    
    // Create CSV content
    const headers = ['Client Name', 'Client Email', 'Product', 'Partner', 'Fee Amount', 'Commission', 'Status', 'Created Date', 'Approval Date'];
    const rows = salesReport.map(sale => [
      sale.client_name,
      sale.client_email,
      sale.product_name || 'N/A',
      sale.partner_name || 'N/A',
      sale.fee_amount,
      sale.commission_amount || 0,
      sale.status,
      new Date(sale.created_at).toLocaleDateString(),
      sale.approval_date ? new Date(sale.approval_date).toLocaleDateString() : 'N/A'
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
      let url = `${API}/sales/partner-report/${partnerId}?`;
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
        <div class="footer">LEAMSS Portal - Commission Report</div>
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

  const downloadDocument = async (docId, filename) => {
    try {
      const response = await axios.get(`${API}/documents/download/${docId}`, { ...getAuthHeader(), responseType: 'blob' });
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
      await axios.post(`${API}/sales/approve`, { sale_id: saleId, status, case_manager_id: caseManagerId }, getAuthHeader());
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

  const removeDocFromStep = (docIndex) => {
    const updatedDocs = stepEditorDialog.stepData.required_documents.filter((_, i) => i !== docIndex);
    setStepEditorDialog({ ...stepEditorDialog, stepData: { ...stepEditorDialog.stepData, required_documents: updatedDocs } });
  };

  const saveWorkflowStep = async () => {
    const { stepData, mode } = stepEditorDialog;
    if (!stepData.step_name.trim()) { toast.error('Please enter step name'); return; }
    try {
      const productId = workflowDialog.product.id;
      if (mode === 'create') {
        await axios.post(`${API}/products/workflow-step`, {
          product_id: productId, step_name: stepData.step_name, step_order: stepData.step_order,
          description: stepData.description, duration_days: stepData.duration_days ? parseInt(stepData.duration_days) : null,
          required_documents: stepData.required_documents
        }, getAuthHeader());
        toast.success('Workflow step added!');
      } else {
        const stepOrder = workflowDialog.product.workflow_steps[workflowDialog.editingStepIndex].step_order;
        await axios.put(`${API}/products/${productId}/workflow-step/${stepOrder}`, {
          product_id: productId, step_name: stepData.step_name, step_order: stepData.step_order,
          description: stepData.description, duration_days: stepData.duration_days ? parseInt(stepData.duration_days) : null,
          required_documents: stepData.required_documents
        }, getAuthHeader());
        toast.success('Workflow step updated!');
      }
      setStepEditorDialog({ ...stepEditorDialog, open: false });
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

  return (
    <div className="flex min-h-screen bg-[#F5F7FA]" data-testid="admin-dashboard">
      {/* Modern White Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col fixed h-screen" data-testid="admin-sidebar">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-[#2a777a] flex items-center justify-center">
              <span className="text-white font-bold text-lg">L</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-800">LEAMSS</h1>
              <p className="text-xs text-slate-500">Admin Portal</p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {[
            { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
            { id: 'sales', icon: FileText, label: 'Pending Sales' },
            { id: 'total-sales', icon: TrendingUp, label: 'Sales Report' },
            { id: 'commissions', icon: DollarSign, label: 'Commissions' },
            { id: 'cases', icon: Briefcase, label: 'All Cases' },
            { id: 'products', icon: Settings, label: 'Products' },
            { id: 'users', icon: Users, label: 'Users' },
            { id: 'tickets', icon: MessageSquare, label: 'Tickets' },
            { id: 'settings', icon: Settings, label: 'Settings' }
          ].map(item => (
            <button
              key={item.id}
              onClick={() => { setActiveTab(item.id); setSelectedCase(null); setSelectedSale(null); setSelectedPartnerReport(null); setSelectedTicket(null); }}
              data-testid={`nav-${item.id}`}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium ${
                activeTab === item.id 
                  ? 'bg-teal-50 text-[#2a777a]' 
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
              {item.id === 'tickets' && ticketStats.open > 0 && (
                <span className="ml-auto bg-[#f7620b] text-white text-xs px-2 py-0.5 rounded-full">{ticketStats.open}</span>
              )}
              {item.id === 'sales' && pendingSales.length > 0 && (
                <span className="ml-auto bg-[#f7620b] text-white text-xs px-2 py-0.5 rounded-full">{pendingSales.length}</span>
              )}
            </button>
          ))}
        </nav>
        
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2 mb-3">
            <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center">
              <span className="text-slate-600 font-medium text-sm">{user?.name?.charAt(0) || 'A'}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <Button onClick={handleLogout} variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-800 hover:bg-slate-50" data-testid="logout-button">
            <LogOut className="mr-2 h-4 w-4" />Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        {/* Header */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 py-4">
          <div className="flex justify-between items-center max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold text-slate-800" data-testid="page-title">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'sales' && 'Pending Sales'}
              {activeTab === 'total-sales' && 'Sales Report'}
              {activeTab === 'commissions' && 'Commissions'}
              {activeTab === 'cases' && !selectedCase && 'All Cases'}
              {activeTab === 'products' && 'Products'}
              {activeTab === 'users' && 'Users'}
              {activeTab === 'tickets' && !selectedTicket && 'Tickets'}
              {activeTab === 'settings' && 'Settings'}
              {activeTab === 'sale-docs' && `Sale: ${selectedSale?.client_name}`}
              {activeTab === 'case-detail' && `Case: ${selectedCase?.case_id}`}
              {selectedTicket && `Ticket: ${selectedTicket?.subject}`}
            </h2>
            <div className="flex items-center gap-3">
              <Button onClick={() => setTicketDialog({ ...ticketDialog, open: true })} variant="outline" size="sm" data-testid="raise-ticket-btn">
                <Plus className="mr-2 h-4 w-4" />Raise Ticket
              </Button>
              <NotificationBell onNotificationClick={handleNotificationClick} />
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-8">
          <div className="max-w-7xl mx-auto">
          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6" data-testid="dashboard-content">
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
                  <p className="text-3xl font-bold text-emerald-600 mt-2">${(stats.total_revenue || 0).toFixed(2)}</p>
                </Card>
                <Card className="p-6 bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                  <p className="text-sm text-slate-500 font-medium">Open Tickets</p>
                  <p className="text-3xl font-bold text-[#2a777a] mt-2">{ticketStats.open || 0}</p>
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
                    <Button onClick={() => downloadReport(salesReport, 'sales_report')} variant="outline"><Download className="mr-2 h-4 w-4" />Export</Button>
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
                  <p className="text-2xl font-bold text-amber-700">${salesReport.filter(s => s.status === 'approved').reduce((sum, s) => sum + (s.fee_amount || 0), 0).toFixed(2)}</p>
                </Card>
                <Card className="p-4 bg-purple-50 border-purple-200">
                  <p className="text-sm text-slate-600">Total Commission</p>
                  <p className="text-2xl font-bold text-purple-700">${salesReport.filter(s => s.status === 'approved').reduce((sum, s) => sum + (s.commission_amount || 0), 0).toFixed(2)}</p>
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
                        <th className="text-left p-3">Product</th>
                        <th className="text-right p-3">Amount</th>
                        <th className="text-right p-3">Commission</th>
                        <th className="text-center p-3">Status</th>
                        <th className="text-center p-3">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesReport.slice(0, 50).map(sale => (
                        <tr key={sale.id} className="border-b hover:bg-slate-50">
                          <td className="p-3">{new Date(sale.created_at).toLocaleDateString()}</td>
                          <td className="p-3">{sale.client_name}</td>
                          <td className="p-3">{sale.partner_name}</td>
                          <td className="p-3">{sale.product_name}</td>
                          <td className="p-3 text-right">${sale.fee_amount}</td>
                          <td className="p-3 text-right">${sale.commission_amount?.toFixed(2)}</td>
                          <td className="p-3 text-center">{getStatusBadge(sale.status)}</td>
                          <td className="p-3 text-center">
                            <Button size="sm" variant="outline" onClick={() => loadPartnerReport(sale.partner_id)}>
                              <Eye className="h-4 w-4" />
                            </Button>
                          </td>
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
                    <p className="text-2xl font-bold text-purple-700">${selectedPartnerReport.summary?.total_revenue?.toFixed(2)}</p>
                  </div>
                  <div className="p-4 bg-[#2a777a]/10 rounded-lg">
                    <p className="text-sm text-slate-600">Commission Payable</p>
                    <p className="text-2xl font-bold text-[#2a777a]">${selectedPartnerReport.summary?.total_commission_payable?.toFixed(2)}</p>
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
                          { key: 'total_fee', header: 'Revenue', format: (v) => `$${(v || 0).toFixed(2)}` },
                          { key: 'total_commission', header: 'Commission', format: (v) => `$${(v || 0).toFixed(2)}` }
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
                  <p className="text-3xl font-bold mt-2">${partnerCommissions.reduce((sum, p) => sum + (p.total_commission || 0), 0).toFixed(2)}</p>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-[#f7620b] to-[#e55a09] text-white">
                  <p className="text-sm opacity-80">Total Revenue</p>
                  <p className="text-3xl font-bold mt-2">${partnerCommissions.reduce((sum, p) => sum + (p.total_fee || 0), 0).toFixed(2)}</p>
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
                          <td className="p-3 text-right">${partner.total_fee?.toFixed(2)}</td>
                          <td className="p-3 text-right font-bold text-[#2a777a]">${partner.total_commission?.toFixed(2)}</td>
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
            </div>
          )}

          {/* Pending Sales Tab */}
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
                        <Button onClick={() => viewSaleDocuments(sale)} size="sm" className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid={`view-docs-${sale.id}`}>
                          <Eye className="mr-2 h-4 w-4" />View Documents
                        </Button>
                        <Select onValueChange={(managerId) => handleApproveSale(sale.id, 'approved', managerId)}>
                          <SelectTrigger className="w-48" data-testid={`assign-manager-${sale.id}`}><SelectValue placeholder="Assign & Approve" /></SelectTrigger>
                          <SelectContent>
                            {caseManagers.map((manager) => <SelectItem key={manager.id} value={manager.id}>{manager.name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <Button onClick={() => handleApproveSale(sale.id, 'rejected', null)} variant="destructive" size="sm" data-testid={`reject-sale-${sale.id}`}>Reject</Button>
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
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div><p className="text-sm text-slate-500">Client</p><p className="font-medium text-slate-800">{selectedSale.client_name}</p></div>
                  <div><p className="text-sm text-slate-500">Email</p><p className="font-medium text-slate-800">{selectedSale.client_email}</p></div>
                  <div><p className="text-sm text-slate-500">Product</p><p className="font-medium text-slate-800">{selectedSale.product_name}</p></div>
                  <div><p className="text-sm text-slate-500">Fee Amount</p><p className="font-medium text-slate-800">${selectedSale.fee_amount}</p></div>
                </div>
                <h4 className="font-semibold mb-3 text-slate-800">Uploaded Documents</h4>
                <div className="space-y-3">
                  {saleDocuments.length === 0 ? (
                    <p className="text-center text-slate-500 py-4">No documents uploaded</p>
                  ) : (
                    saleDocuments.map((doc, idx) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                        <div><p className="font-medium text-slate-800">{doc.filename}</p><p className="text-sm text-slate-600">Type: {doc.type}</p></div>
                        <Button onClick={() => downloadDocument(doc.file_id, doc.filename)} size="sm" variant="outline"><Download className="h-4 w-4" /></Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
              <div className="flex gap-3">
                <Select onValueChange={(managerId) => handleApproveSale(selectedSale.id, 'approved', managerId)} className="flex-1">
                  <SelectTrigger data-testid="assign-case-manager"><SelectValue placeholder="Assign Case Manager & Approve" /></SelectTrigger>
                  <SelectContent>{caseManagers.map((manager) => <SelectItem key={manager.id} value={manager.id}>{manager.name}</SelectItem>)}</SelectContent>
                </Select>
                <Button onClick={() => handleApproveSale(selectedSale.id, 'rejected', null)} variant="destructive">Reject Sale</Button>
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
            </div>
          )}

          {/* Products Tab */}
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
                            <p className="text-sm text-slate-600">Fee: <span className="font-medium">${product.fee}</span></p>
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
                  allTickets.map(ticket => (
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
                          <p className="text-sm text-slate-800">{activity.details}</p>
                          <p className="text-xs text-slate-500">{new Date(activity.timestamp).toLocaleString()}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
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
          </div>
        </div>
      </main>

      {/* Product Dialog */}
      <Dialog open={productDialog.open} onOpenChange={(open) => setProductDialog({ ...productDialog, open })}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{productDialog.mode === 'create' ? 'Create' : 'Edit'} Product</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><Label>Product Name</Label><Input value={productDialog.data?.name || ''} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, name: e.target.value } })} data-testid="product-name-input" /></div>
            <div><Label>Description</Label><Textarea value={productDialog.data?.description || ''} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, description: e.target.value } })} data-testid="product-description-input" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Fee ($)</Label><Input type="number" value={productDialog.data?.fee || 0} onChange={(e) => setProductDialog({ ...productDialog, data: { ...productDialog.data, fee: parseFloat(e.target.value) || 0 } })} data-testid="product-fee-input" /></div>
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
            <div className="flex justify-between items-center">
              <p className="text-sm text-slate-600">Define the steps for this product workflow.</p>
              <Button onClick={() => openStepEditor('create')} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="add-step-btn"><Plus className="mr-2 h-4 w-4" />Add Step</Button>
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
                            <div className="mt-2"><p className="text-xs font-medium text-slate-700">Required Documents:</p><div className="flex flex-wrap gap-1 mt-1">{step.required_documents.map((doc, docIdx) => <Badge key={docIdx} variant="outline" className="text-xs">{doc.doc_name} {doc.is_mandatory && '*'}</Badge>)}</div></div>
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
                  <Button size="sm" onClick={addDocToStep} variant="outline" data-testid="add-doc-btn"><Plus className="h-4 w-4 mr-1" />Add Document</Button>
                </div>
              </div>
            </div>
            <Button onClick={saveWorkflowStep} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="save-step-btn">{stepEditorDialog.mode === 'create' ? 'Add Step' : 'Update Step'}</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* User Dialog */}
      <Dialog open={userDialog.open} onOpenChange={(open) => setUserDialog({ ...userDialog, open })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{userDialog.mode === 'create' ? 'Create' : 'Edit'} User</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><Label>Name</Label><Input value={userDialog.data?.name || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, name: e.target.value } })} data-testid="user-name-input" /></div>
            <div><Label>Email</Label><Input type="email" value={userDialog.data?.email || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, email: e.target.value } })} data-testid="user-email-input" /></div>
            <div><Label>Mobile</Label><Input value={userDialog.data?.mobile || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, mobile: e.target.value } })} data-testid="user-mobile-input" /></div>
            <div>
              <Label>Role</Label>
              <Select value={userDialog.data?.role || 'partner'} onValueChange={(value) => setUserDialog({ ...userDialog, data: { ...userDialog.data, role: value } })}>
                <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="admin">Admin</SelectItem><SelectItem value="case_manager">Case Manager</SelectItem><SelectItem value="partner">Partner</SelectItem><SelectItem value="client">Client</SelectItem></SelectContent>
              </Select>
            </div>
            <div><Label>{userDialog.mode === 'edit' ? 'New Password (leave blank to keep)' : 'Password'}</Label><Input type="password" value={userDialog.data?.password || ''} onChange={(e) => setUserDialog({ ...userDialog, data: { ...userDialog.data, password: e.target.value } })} data-testid="user-password-input" /></div>
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
    </div>
  );
};

export default AdminDashboard;
