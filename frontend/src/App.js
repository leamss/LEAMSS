import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { LanguageProvider } from '@/components/LanguageProvider';
import { ThemeProvider } from '@/components/ThemeProvider';
import Login from '@/pages/Login';
import AdminDashboard from '@/pages/AdminDashboard';
import PartnerDashboard from '@/pages/PartnerDashboard';
import CaseManagerDashboard from '@/pages/CaseManagerDashboard';
import ClientDashboard from '@/pages/ClientDashboard';
import NotificationHistory from '@/pages/NotificationHistory';
import AnalyticsDashboard from '@/pages/AnalyticsDashboard';
import ActivityLog from '@/pages/ActivityLog';
import PaymentSuccess from '@/pages/PaymentSuccess';
import WorkflowBuilder from '@/pages/WorkflowBuilder';
import AIWorkflowBuilder from '@/pages/AIWorkflowBuilder';
import MarketingDashboard from '@/pages/MarketingDashboard';
import EmployeesPortal from '@/pages/EmployeesPortal';
import PortalWelcome from '@/pages/PortalWelcome';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPasswordWithToken from '@/pages/ResetPasswordWithToken';
import ForceChangePassword from '@/pages/ForceChangePassword';
import RequirePermission from '@/components/RequirePermission';
import MyAttendance from '@/pages/MyAttendance';
import MyLeaves from '@/pages/MyLeaves';
import LeaveApprovals from '@/pages/LeaveApprovals';
import AttendanceSettings from '@/pages/admin/AttendanceSettings';
import HolidayManager from '@/pages/admin/HolidayManager';
import LeaveTypesManager from '@/pages/admin/LeaveTypesManager';
import ApproverConfig from '@/pages/admin/ApproverConfig';
import HRAuditLog from '@/pages/admin/HRAuditLog';
import SalesDashboard from '@/pages/SalesDashboard';
import MyTargets from '@/pages/MyTargets';
import SalesTargetsAdmin from '@/pages/admin/SalesTargetsAdmin';
import TargetTemplatesManager from '@/pages/admin/TargetTemplatesManager';
import ExpressApprovalsAdmin from '@/pages/admin/ExpressApprovalsAdmin';
import ExpressSalesSettings from '@/pages/admin/ExpressSalesSettings';
import EligibilityKnowledgeBase from '@/pages/admin/EligibilityKnowledgeBase';
import EligibilityProfileWizard from '@/pages/eligibility/EligibilityProfileWizard';
import { EligibilityProfilesList, EligibilityProfileDetail } from '@/pages/eligibility/EligibilityProfiles';
import AdminVendors from '@/pages/admin/AdminVendors';
import VendorCategoriesManager from '@/pages/admin/VendorCategoriesManager';
import CostStructuresManager from '@/pages/admin/CostStructuresManager';
import ProductsManager from '@/pages/admin/ProductsManager';
import AdminAllocations from '@/pages/admin/AdminAllocations';
import CommissionSlabsManager from '@/pages/admin/CommissionSlabsManager';
import CommissionDashboard from '@/pages/admin/CommissionDashboard';
import MyCommission from '@/pages/MyCommission';
import VendorAcceptInvite from '@/pages/vendor/VendorAcceptInvite';
import VendorDashboard from '@/pages/vendor/VendorDashboard';
import PayoutQueue from '@/pages/admin/PayoutQueue';
import PeopleManager from '@/pages/admin/PeopleManager';
import FinanceDashboard from '@/pages/admin/FinanceDashboard';
import ComingSoon from '@/pages/ComingSoon';
import ServiceCalculator from '@/pages/ServiceCalculator';
import LeadCapture from '@/pages/LeadCapture';
import SharedEstimate from '@/pages/SharedEstimate';
import PreAssessmentPayment from '@/pages/PreAssessmentPayment';
import MagicLinkLogin from '@/pages/MagicLinkLogin';
import EligibilityCheck from '@/pages/EligibilityCheck';
import VisaCompare from '@/pages/VisaCompare';
import '@/App.css';

function App() {
  return (
    <ThemeProvider>
    <LanguageProvider>
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/analytics" element={<AnalyticsDashboard />} />
          <Route path="/admin/activity" element={<ActivityLog />} />
          <Route path="/admin/workflows" element={<WorkflowBuilder />} />
          <Route path="/admin/ai-workflow" element={<AIWorkflowBuilder />} />
          <Route path="/admin/marketing" element={<MarketingDashboard />} />
          <Route path="/admin/employees" element={
            <RequirePermission anyOf={['employee.view.all', 'user.view.all']} allowRoles={['admin_owner', 'admin']}>
              <EmployeesPortal />
            </RequirePermission>
          } />
          <Route path="/portal/welcome" element={<PortalWelcome />} />
          <Route path="/portal/attendance" element={<MyAttendance />} />
          <Route path="/portal/leaves" element={<MyLeaves />} />
          <Route path="/portal/leave-approvals" element={<LeaveApprovals />} />
          <Route path="/admin/hr/settings" element={
            <RequirePermission anyOf={['system.update.any', 'attendance.update.all']}>
              <AttendanceSettings />
            </RequirePermission>
          } />
          <Route path="/admin/hr/holidays" element={
            <RequirePermission anyOf={['system.update.any', 'attendance.update.all']}>
              <HolidayManager />
            </RequirePermission>
          } />
          <Route path="/admin/hr/leave-types" element={
            <RequirePermission anyOf={['system.update.any', 'leave.approve.final']}>
              <LeaveTypesManager />
            </RequirePermission>
          } />
          <Route path="/admin/hr/approvers" element={
            <RequirePermission anyOf={['system.update.any', 'attendance.update.all']}>
              <ApproverConfig />
            </RequirePermission>
          } />
          <Route path="/admin/hr/audit" element={
            <RequirePermission anyOf={['system.view.all', 'leave.view.all', 'attendance.view.all']}>
              <HRAuditLog />
            </RequirePermission>
          } />
          <Route path="/sales/dashboard" element={
            <RequirePermission anyOf={['pa.create.own', 'pa.view.own']}>
              <SalesDashboard />
            </RequirePermission>
          } />
          <Route path="/sales/my-targets" element={
            <RequirePermission anyOf={['target.view.own']}>
              <MyTargets />
            </RequirePermission>
          } />
          <Route path="/admin/sales/targets" element={
            <RequirePermission anyOf={['target.view.all', 'target.view.team', 'target.view.dept', 'target.create.any']}>
              <SalesTargetsAdmin />
            </RequirePermission>
          } />
          <Route path="/admin/sales/target-templates" element={
            <RequirePermission anyOf={['target_template.view.all', 'target_template.manage.any']}>
              <TargetTemplatesManager />
            </RequirePermission>
          } />
          <Route path="/admin/sales/express-approvals" element={
            <RequirePermission anyOf={['pa.approve.express', 'system.user_manage.any']}>
              <ExpressApprovalsAdmin />
            </RequirePermission>
          } />
          <Route path="/admin/sales/express-settings" element={
            <RequirePermission anyOf={['system.user_manage.any']} allowRoles={['admin_owner', 'admin']}>
              <ExpressSalesSettings />
            </RequirePermission>
          } />
          <Route path="/admin/eligibility/knowledge-base" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <EligibilityKnowledgeBase />
            </RequirePermission>
          } />
          <Route path="/eligibility/profiles" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <EligibilityProfilesList />
            </RequirePermission>
          } />
          <Route path="/eligibility/new-assessment" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <EligibilityProfileWizard />
            </RequirePermission>
          } />
          <Route path="/eligibility/edit/:profileId" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <EligibilityProfileWizard />
            </RequirePermission>
          } />
          <Route path="/eligibility/profile/:profileId" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <EligibilityProfileDetail />
            </RequirePermission>
          } />
          <Route path="/admin/vendors" element={
            <RequirePermission anyOf={['vendor.view.all', 'vendor.create.any', 'system.user_manage.any']}>
              <AdminVendors />
            </RequirePermission>
          } />
          <Route path="/admin/vendors/categories" element={
            <RequirePermission anyOf={['vendor_category.manage.any', 'system.user_manage.any']}>
              <VendorCategoriesManager />
            </RequirePermission>
          } />
          <Route path="/admin/products" element={
            <RequirePermission anyOf={['product_cost.view.all', 'product_cost.manage.any', 'system.user_manage.any']}>
              <ProductsManager />
            </RequirePermission>
          } />
          <Route path="/admin/products/cost-structures" element={
            <RequirePermission anyOf={['product_cost.view.all', 'product_cost.manage.any', 'system.user_manage.any']}>
              <CostStructuresManager />
            </RequirePermission>
          } />
          <Route path="/admin/allocations" element={
            <RequirePermission anyOf={['allocation.view.all', 'vendor.view.all', 'system.user_manage.any']}>
              <AdminAllocations />
            </RequirePermission>
          } />
          <Route path="/admin/sales/commission-slabs" element={
            <RequirePermission anyOf={['commission.view.all', 'commission.update.any', 'system.user_manage.any']}>
              <CommissionSlabsManager />
            </RequirePermission>
          } />
          <Route path="/admin/sales/commissions" element={
            <RequirePermission anyOf={['commission.view.all', 'commission.view.team', 'system.user_manage.any']}>
              <CommissionDashboard />
            </RequirePermission>
          } />
          <Route path="/sales/my-commission" element={
            <RequirePermission anyOf={['commission.view.own', 'pa.create.own', 'pa.view.own']}>
              <MyCommission />
            </RequirePermission>
          } />
          <Route path="/admin/payouts" element={
            <RequirePermission anyOf={['commission.payout.any', 'allocation.mark-paid.any', 'system.user_manage.any']}>
              <PayoutQueue />
            </RequirePermission>
          } />
          <Route path="/admin/people" element={
            <RequirePermission anyOf={['system.user_manage.any', 'hr.user_manage.any']}>
              <PeopleManager />
            </RequirePermission>
          } />
          <Route path="/admin/finance" element={
            <RequirePermission anyOf={['commission.view.all', 'commission.payout.any', 'system.user_manage.any']}>
              <FinanceDashboard />
            </RequirePermission>
          } />
          <Route path="/vendor/accept-invite/:token" element={<VendorAcceptInvite />} />
          <Route path="/vendor/dashboard" element={<VendorDashboard />} />
          <Route path="/sales/coming-soon" element={<ComingSoon />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPasswordWithToken />} />
          <Route path="/force-change-password" element={<ForceChangePassword />} />
          <Route path="/calculator" element={<ServiceCalculator />} />
          <Route path="/inquiry" element={<LeadCapture />} />
          <Route path="/shared-estimate/:token" element={<SharedEstimate />} />
          <Route path="/pre-assess/:token" element={<PreAssessmentPayment />} />
          <Route path="/magic/:token" element={<MagicLinkLogin />} />
          <Route path="/eligibility" element={<EligibilityCheck />} />
          <Route path="/visa-compare" element={<VisaCompare />} />
          <Route path="/partner" element={<PartnerDashboard />} />
          <Route path="/case-manager" element={<CaseManagerDashboard />} />
          <Route path="/client" element={<ClientDashboard />} />
          <Route path="/notifications" element={<NotificationHistory />} />
          <Route path="/payment-success" element={<PaymentSuccess />} />
          <Route path="/payment-cancel" element={<Navigate to="/client" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
    </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
