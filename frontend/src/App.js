import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Login from '@/pages/Login';
import AdminDashboard from '@/pages/AdminDashboard';
import PartnerDashboard from '@/pages/PartnerDashboard';
import CaseManagerDashboard from '@/pages/CaseManagerDashboard';
import ClientDashboard from '@/pages/ClientDashboard';
import '@/App.css';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/partner" element={<PartnerDashboard />} />
          <Route path="/case-manager" element={<CaseManagerDashboard />} />
          <Route path="/client" element={<ClientDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
