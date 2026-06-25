import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { LanguageProvider } from '@/components/LanguageProvider';
import { ThemeProvider } from '@/components/ThemeProvider';
import Login from '@/pages/Login';
import AdminDashboard from '@/pages/AdminDashboard';
import AuditInsights from '@/pages/admin/AuditInsights';
import OrphanedPAsCleanup from '@/pages/admin/OrphanedPAsCleanup';
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
// Phase 21.A-fix — PortalHub merged into EmployeesPortal; keep alias route for backward-compat
import MyProfile from '@/pages/portal/MyProfile';
import Tasks from '@/pages/portal/Tasks';
import AnnouncementsPolicies from '@/pages/portal/AnnouncementsPolicies';
import MyWorkspace from '@/pages/portal/MyWorkspace';
import MarketingContentStudio from '@/pages/admin/MarketingContentStudio';
import HRAnalyticsDashboard from '@/pages/admin/HRAnalyticsDashboard';
import SEOToolsHub from '@/pages/admin/SEOToolsHub';
import AEOToolsHub from '@/pages/admin/AEOToolsHub';
import GEOToolsHub from '@/pages/admin/GEOToolsHub';
import Reimbursements from '@/pages/portal/Reimbursements';
import SiteAuditHub from '@/pages/it/SiteAuditHub';
import DevTrackerHub from '@/pages/it/DevTrackerHub';
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
import OccupationMasterAdmin from '@/pages/admin/OccupationMasterAdmin';
import AuthoritiesAdmin from '@/pages/admin/AuthoritiesAdmin';
import CountryGuidesAdmin from '@/pages/admin/CountryGuidesAdmin';
import VerificationHub from '@/pages/admin/VerificationHub';
import ScraperHub from '@/pages/admin/ScraperHub';
import DataImportHub from '@/pages/admin/DataImportHub';
import ProtectionPoliciesAdmin from '@/pages/admin/ProtectionPoliciesAdmin';
import CockpitMockup from '@/pages/admin/CockpitMockup';
import Cockpit from '@/pages/admin/Cockpit';
import AnzIntelAudit from '@/pages/admin/AnzIntelAudit';
import CalculatorRulesEditor from '@/pages/admin/CalculatorRulesEditor';
import AtlasSearch from '@/pages/admin/AtlasSearch';
import PublicCountryGuide from '@/pages/PublicCountryGuide';
import PublicCountryIndex from '@/pages/PublicCountryIndex';
import EligibilityProfileWizard from '@/pages/eligibility/EligibilityProfileWizard';
import { EligibilityProfilesList, EligibilityProfileDetail } from '@/pages/eligibility/EligibilityProfiles';
import OccupationSearch from '@/pages/sales/OccupationSearch';
import OccupationDetail from '@/pages/sales/OccupationDetail';
import OccupationCompare from '@/pages/sales/OccupationCompare';
import EligibilityCalculator from '@/pages/sales/EligibilityCalculator';
import ClientAssessment from '@/pages/sales/ClientAssessment';
import MyAssessments from '@/pages/sales/MyAssessments';
import PublicAssessmentReport from '@/pages/sales/PublicAssessmentReport';
import PublicReportView from '@/pages/PublicReportView';
import PublicInfoSheet from '@/pages/eligibility/PublicInfoSheet';
import AdminVendors from '@/pages/admin/AdminVendors';
import VendorCategoriesManager from '@/pages/admin/VendorCategoriesManager';
import CostStructuresManager from '@/pages/admin/CostStructuresManager';
import ProductsManager from '@/pages/admin/ProductsManager';
import BrandGuide from '@/pages/admin/BrandGuide';
import PreAssessmentFeePolicies from '@/pages/admin/PreAssessmentFeePolicies';
import InfoSheetPage from '@/pages/admin/InfoSheetPage';
import PAReviewsQueue from '@/pages/admin/PAReviewsQueue';
import MiniPortalsAdmin from '@/pages/admin/MiniPortalsAdmin';
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
import { MegaLanding, SharedScorecard } from '@/pages/LeamssPublic';
import PublicPagesManager from '@/pages/admin/PublicPagesManager';
import EligibilityScoringRules from '@/pages/admin/EligibilityScoringRules';
import VisaPathwaysEditor from '@/pages/admin/VisaPathwaysEditor';
import ComparePage from '@/pages/sales/ComparePage';
import CompareBar from '@/components/CompareBar';
import AppErrorBoundary from '@/components/AppErrorBoundary';
import ClientErrorsDashboard from '@/pages/admin/ClientErrorsDashboard';
import CouponsAdmin from '@/pages/admin/CouponsAdmin';
import FunnelDashboard from '@/pages/admin/FunnelDashboard';
import ProposalBuilder from '@/pages/sales/ProposalBuilder';
import ClientPortalLogin from '@/pages/client-portal/ClientPortalLogin';
import ClientPortalDashboard from '@/pages/client-portal/ClientPortalDashboard';
import AdminClientPortalPreview from '@/pages/admin/AdminClientPortalPreview';
import PublicProposalView from '@/pages/PublicProposalView';
import { useLocation } from 'react-router-dom';
import '@/App.css';

/**
 * Phase 18.6 — Scoped error boundary that wraps the Routes tree.
 * Reads the pathname to label the scope, and uses a `key` on the boundary
 * so a crash on one scope doesn't leak into another (boundary remounts
 * when we navigate between scopes).
 */
function ScopedRouteBoundary({ children }) {
  const location = useLocation();
  const path = location?.pathname || '';
  let scope = 'public';
  if (path.startsWith('/sales')) scope = 'sales';
  else if (path.startsWith('/admin')) scope = 'admin';
  else if (path.startsWith('/portal')) scope = 'portal';
  else if (path.startsWith('/partner')) scope = 'partner';
  else if (path.startsWith('/case-manager') || path.startsWith('/client') || path.startsWith('/cm')) scope = 'workspace';
  return (
    <AppErrorBoundary key={scope} scope={scope}>
      {children}
    </AppErrorBoundary>
  );
}

function App() {
  return (
    <ThemeProvider>
    <LanguageProvider>
    <div className="App">
      <BrowserRouter>
        <ScopedRouteBoundary>
        <Routes>
          <Route path="/" element={<Login />} />
          {/* ─── Phase 14: LEAMSS Public Brand Experience (no auth) ─── */}
          <Route path="/start" element={<MegaLanding />} />
          {/* Phase 19: /atlas/* paths are served by setupProxy.js as static SSR HTML files.
              We intentionally do NOT mount React routes for them so that ANY navigation
              (direct, refresh, or click from inside the SPA) triggers a full page reload
              and the bot/user receives the pre-rendered, SEO-optimised HTML from
              frontend/public/atlas/... See Phase 19 CHANGELOG. */}
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/analytics" element={<AnalyticsDashboard />} />
          <Route path="/admin/activity" element={<ActivityLog />} />
          <Route path="/admin/audit-insights" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <AuditInsights />
            </RequirePermission>
          } />
          <Route path="/admin/orphaned-pas" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <div className="min-h-screen bg-slate-50 p-5">
                <div className="max-w-6xl mx-auto"><OrphanedPAsCleanup /></div>
              </div>
            </RequirePermission>
          } />
          <Route path="/admin/workflows" element={<WorkflowBuilder />} />
          <Route path="/admin/ai-workflow" element={<AIWorkflowBuilder />} />
          <Route path="/admin/marketing" element={<MarketingDashboard />} />
          <Route path="/admin/employees" element={
            <RequirePermission anyOf={['employee.view.all', 'user.view.all']} allowRoles={['admin_owner', 'admin']}>
              <EmployeesPortal />
            </RequirePermission>
          } />
          {/* Phase 21.A — Unified Portal Hub merged INTO EmployeesPortal; this alias redirects */}
          <Route path="/admin/portal-hub" element={<Navigate to="/admin/employees" replace />} />
          {/* Phase 21.B — Employee self-service profile */}
          <Route path="/portal/my-profile" element={<MyProfile />} />
          {/* Phase 21.E — Tasks (Kanban) */}
          <Route path="/portal/my-tasks" element={<Tasks mode="me" />} />
          <Route path="/admin/employee-tasks" element={<Tasks mode="all" />} />
          {/* Phase 21.F — Announcements + Internal Policies */}
          <Route path="/portal/announcements" element={<AnnouncementsPolicies defaultTab="announcements" />} />
          <Route path="/portal/policies" element={<AnnouncementsPolicies defaultTab="policies" />} />
          <Route path="/admin/announcements" element={<AnnouncementsPolicies defaultTab="announcements" />} />
          <Route path="/admin/policies" element={<AnnouncementsPolicies defaultTab="policies" />} />
          {/* Phase 21 Slice 2 — Employee Workspace (Payslips/Documents/Assets/Onboarding) */}
          <Route path="/portal/my-workspace" element={<MyWorkspace />} />
          <Route path="/portal/my-payslips" element={<MyWorkspace />} />
          <Route path="/portal/my-documents" element={<MyWorkspace />} />
          <Route path="/portal/my-assets" element={<MyWorkspace />} />
          <Route path="/portal/my-onboarding" element={<MyWorkspace />} />
          {/* Phase 21 Slice 3 — Marketing Content Studio (Claude Sonnet 4.5) */}
          <Route path="/admin/marketing/content-studio" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <MarketingContentStudio />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 3 — SEO/AEO/GEO hubs */}
          <Route path="/admin/marketing/seo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <SEOToolsHub />
            </RequirePermission>
          } />
          <Route path="/admin/marketing/aeo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <AEOToolsHub />
            </RequirePermission>
          } />
          <Route path="/admin/marketing/geo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <GEOToolsHub />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 3 Sub-Slice B — /portal/marketing/* canonical aliases */}
          <Route path="/portal/marketing/content-studio" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <MarketingContentStudio />
            </RequirePermission>
          } />
          <Route path="/portal/marketing/seo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <SEOToolsHub />
            </RequirePermission>
          } />
          <Route path="/portal/marketing/aeo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <AEOToolsHub />
            </RequirePermission>
          } />
          <Route path="/portal/marketing/geo" element={
            <RequirePermission anyOf={['marketing.view.all', 'content.view.all', 'campaign.view.all']} allowRoles={['admin_owner', 'admin']}>
              <GEOToolsHub />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 3 — HR Analytics Dashboard */}
          <Route path="/admin/hr/analytics" element={
            <RequirePermission anyOf={['system.view.all', 'hr.user_manage.any', 'leave.view.all']} allowRoles={['admin_owner', 'admin']}>
              <HRAnalyticsDashboard />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 3 Sub-Slice A — /portal/hr-analytics alias */}
          <Route path="/portal/hr-analytics" element={
            <RequirePermission anyOf={['system.view.all', 'hr.user_manage.any', 'leave.view.all']} allowRoles={['admin_owner', 'admin']}>
              <HRAnalyticsDashboard />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 4 Sub-Slice A — IT Site Audit + Dev Tracker */}
          <Route path="/portal/it/site-audit" element={
            <RequirePermission anyOf={['it.view.all', 'system.view.all']} allowRoles={['admin_owner', 'admin', 'it']}>
              <SiteAuditHub />
            </RequirePermission>
          } />
          <Route path="/admin/it/site-audit" element={
            <RequirePermission anyOf={['it.view.all', 'system.view.all']} allowRoles={['admin_owner', 'admin', 'it']}>
              <SiteAuditHub />
            </RequirePermission>
          } />
          <Route path="/portal/it/dev-tracker" element={
            <RequirePermission anyOf={['it.view.all', 'system.view.all']} allowRoles={['admin_owner', 'admin', 'it', 'staff', 'employee', 'case_manager', 'partner']}>
              <DevTrackerHub />
            </RequirePermission>
          } />
          <Route path="/admin/it/dev-tracker" element={
            <RequirePermission anyOf={['it.view.all', 'system.view.all']} allowRoles={['admin_owner', 'admin', 'it', 'staff', 'employee', 'case_manager', 'partner']}>
              <DevTrackerHub />
            </RequirePermission>
          } />
          {/* Phase 21 Slice 3 — Reimbursements */}
          <Route path="/portal/my-reimbursements" element={<Reimbursements view="me" />} />
          <Route path="/admin/reimbursements/pending" element={<Reimbursements view="team" />} />
          <Route path="/admin/reimbursements/all" element={<Reimbursements view="all" />} />
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
          <Route path="/admin/kb/occupation-master" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <OccupationMasterAdmin />
            </RequirePermission>
          } />
          {/* Phase 19.9 — Authority Admin */}
          <Route path="/admin/authorities" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <AuthoritiesAdmin />
            </RequirePermission>
          } />
          {/* Phase 18.7 — Client Errors Admin Dashboard */}
          <Route path="/admin/client-errors" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <ClientErrorsDashboard />
            </RequirePermission>
          } />
          <Route path="/admin/country-guides" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <CountryGuidesAdmin />
            </RequirePermission>
          } />
          <Route path="/admin/verify-hub" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <VerificationHub />
            </RequirePermission>
          } />
          <Route path="/admin/scrapers" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <ScraperHub />
            </RequirePermission>
          } />
          <Route path="/admin/data-import" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <DataImportHub />
            </RequirePermission>
          } />
          <Route path="/admin/protection-policies" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <ProtectionPoliciesAdmin />
            </RequirePermission>
          } />
          <Route path="/admin/cockpit-mockup" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <CockpitMockup />
            </RequirePermission>
          } />
          <Route path="/admin/cockpit" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'case_manager', 'partner']}>
              <Cockpit />
            </RequirePermission>
          } />
          <Route path="/admin/anz-intel/audit" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <AnzIntelAudit />
            </RequirePermission>
          } />
          <Route path="/admin/calculator-rules" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <CalculatorRulesEditor />
            </RequirePermission>
          } />
          <Route path="/admin/public-pages" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <PublicPagesManager />
            </RequirePermission>
          } />
          <Route path="/admin/eligibility-scoring" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <EligibilityScoringRules />
            </RequirePermission>
          } />
          <Route path="/admin/visa-pathways" element={
            <RequirePermission allowRoles={['admin_owner', 'admin']}>
              <VisaPathwaysEditor />
            </RequirePermission>
          } />
          <Route path="/admin/atlas/search" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'case_manager', 'partner']}>
              <AtlasSearch />
            </RequirePermission>
          } />
          <Route path="/countries" element={<PublicCountryIndex />} />
          <Route path="/countries/:code" element={<PublicCountryGuide />} />
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
          {/* Smart Sales Helper — Phase 6 v2 */}
          <Route path="/sales/occupations" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <OccupationSearch />
            </RequirePermission>
          } />
          <Route path="/sales/occupations/compare" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <OccupationCompare />
            </RequirePermission>
          } />
          {/* Phase 18.5 — New unified Compare Mode (sessionStorage-backed) */}
          <Route path="/sales/compare" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <ComparePage />
            </RequirePermission>
          } />
          <Route path="/sales/occupations/:countryCode/:code" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <OccupationDetail />
            </RequirePermission>
          } />
          <Route path="/sales/calculator" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <EligibilityCalculator />
            </RequirePermission>
          } />
          <Route path="/sales/client-assessment" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <ClientAssessment />
            </RequirePermission>
          } />
          <Route path="/sales/my-assessments" element={
            <RequirePermission allowRoles={['admin_owner', 'admin', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'partner', 'case_manager']}>
              <MyAssessments />
            </RequirePermission>
          } />
          {/* Public Sales Report — Phase 6.5 Save & Share (NO LOGIN) */}
          <Route path="/sales/report/:token" element={<PublicAssessmentReport />} />
          <Route path="/reports/view/:token" element={<PublicReportView />} />
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
          <Route path="/admin/brand-guide" element={
            <RequirePermission anyOf={['system.user_manage.any']}>
              <BrandGuide />
            </RequirePermission>
          } />
          <Route path="/admin/fee-policies" element={
            <RequirePermission anyOf={['system.user_manage.any']}>
              <PreAssessmentFeePolicies />
            </RequirePermission>
          } />
          <Route path="/admin/info-sheets/:entityType/:entityId" element={
            <RequirePermission anyOf={['system.user_manage.any', 'sale.create.any', 'case.update.any', 'partner.create.any']}>
              <InfoSheetPage />
            </RequirePermission>
          } />
          <Route path="/admin/pa-reviews" element={
            <RequirePermission anyOf={['system.user_manage.any', 'case.update.any']}>
              <PAReviewsQueue />
            </RequirePermission>
          } />
          <Route path="/admin/coupons" element={
            <RequirePermission anyOf={['system.user_manage.any', 'sale.create.any']}>
              <CouponsAdmin />
            </RequirePermission>
          } />
          <Route path="/admin/funnel-dashboard" element={
            <RequirePermission anyOf={['system.user_manage.any', 'case.update.any']}>
              <FunnelDashboard />
            </RequirePermission>
          } />
          <Route path="/sales/proposal-builder" element={
            <RequirePermission anyOf={['system.user_manage.any', 'sale.create.any', 'case.update.any']}>
              <ProposalBuilder />
            </RequirePermission>
          } />
          {/* Step 2 — Client Portal (separate JWT session, NOT staff RBAC) */}
          <Route path="/client-portal/login" element={<ClientPortalLogin />} />
          <Route path="/client-portal/dashboard" element={<ClientPortalDashboard />} />
          {/* Option 2 — Public Proposal View (token-auth via ?t=) */}
          <Route path="/proposal/view" element={<PublicProposalView />} />
          {/* Option D / X5 — Admin Read-Only Client View */}
          <Route path="/admin/client-preview/:clientId" element={
            <RequirePermission anyOf={['system.user_manage.any', 'case.view.any', 'case.update.any', 'sale.create.any']}>
              <AdminClientPortalPreview />
            </RequirePermission>
          } />
          <Route path="/admin/mini-portals" element={
            <RequirePermission anyOf={['system.user_manage.any', 'case.update.any']}>
              <MiniPortalsAdmin />
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
          <Route path="/eligibility" element={<Navigate to="/start#quiz" replace />} />
          <Route path="/info-sheet/:token" element={<PublicInfoSheet />} />
          <Route path="/visa-compare" element={<Navigate to="/start#compare" replace />} />
          <Route path="/scorecard/:id" element={<SharedScorecard />} />
          <Route path="/partner" element={<PartnerDashboard />} />
          <Route path="/case-manager" element={<CaseManagerDashboard />} />
          <Route path="/client" element={<ClientDashboard />} />
          <Route path="/notifications" element={<NotificationHistory />} />
          <Route path="/payment-success" element={<PaymentSuccess />} />
          <Route path="/payment-cancel" element={<Navigate to="/client" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </ScopedRouteBoundary>
        {/* Phase 18.5 — Floating CompareBar (auto-hides on /sales/compare + when empty) */}
        <CompareBar />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
    </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
