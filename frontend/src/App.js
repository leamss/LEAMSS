import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
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
import MarketingDashboard from '@/pages/MarketingDashboard';
import ServiceCalculator from '@/pages/ServiceCalculator';
import LeadCapture from '@/pages/LeadCapture';
import '@/App.css';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/analytics" element={<AnalyticsDashboard />} />
          <Route path="/admin/activity" element={<ActivityLog />} />
          <Route path="/admin/workflows" element={<WorkflowBuilder />} />
          <Route path="/admin/marketing" element={<MarketingDashboard />} />
          <Route path="/calculator" element={<ServiceCalculator />} />
          <Route path="/inquiry" element={<LeadCapture />} />
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
  );
}

export default App;
