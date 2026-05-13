import { useState, useEffect, lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DashboardShell from '@/components/DashboardShell';
import {
  LayoutDashboard, Building2, UsersRound, Network, UserPlus, ArrowLeft,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Dynamic imports — keeps babel cross-file AST scanner from recursing through shadcn primitives
const EmployeesDashboard = lazy(() => import('@/components/employees/EmployeesDashboard'));
const DepartmentsPage = lazy(() => import('@/components/employees/DepartmentsPage'));
const EmployeesList = lazy(() => import('@/components/employees/EmployeesList'));
const AddEmployeeForm = lazy(() => import('@/components/employees/AddEmployeeForm'));
const OrgChart = lazy(() => import('@/components/employees/OrgChart'));

const PAGE_TITLES = {
  'emp-dashboard': 'Employees Dashboard',
  'emp-departments': 'Departments',
  'emp-list': 'All Employees',
  'emp-add': 'Add Employee',
  'emp-org-chart': 'Org Chart',
};

const Fallback = () => <div className="p-12 text-center text-slate-400">Loading…</div>;

export default function EmployeesPortal() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('emp-dashboard');
  const [empListFilter, setEmpListFilter] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setUser(r.data))
      .catch(() => navigate('/'));
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const navGroups = [
    {
      groupLabel: 'Employee Portal',
      defaultOpen: true,
      items: [
        { id: 'emp-dashboard', icon: LayoutDashboard, label: 'Dashboard', onClick: () => { setActiveTab('emp-dashboard'); setEmpListFilter(null); } },
        { id: 'emp-departments', icon: Building2, label: 'Departments', onClick: () => { setActiveTab('emp-departments'); setEmpListFilter(null); } },
        { id: 'emp-list', icon: UsersRound, label: 'All Employees', onClick: () => { setActiveTab('emp-list'); setEmpListFilter(null); } },
        { id: 'emp-org-chart', icon: Network, label: 'Org Chart', onClick: () => { setActiveTab('emp-org-chart'); } },
        { id: 'emp-add', icon: UserPlus, label: 'Add Employee', onClick: () => { setActiveTab('emp-add'); } },
      ]
    },
    {
      groupLabel: 'Back to Main',
      defaultOpen: false,
      items: [
        { id: 'back-admin', icon: ArrowLeft, label: 'Admin Dashboard', onClick: () => navigate('/admin') },
      ]
    },
  ];

  const onNavigateInternal = (tab, filter) => {
    if (filter) setEmpListFilter(filter);
    setActiveTab(tab);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'emp-dashboard':
        return <EmployeesDashboard onNavigate={onNavigateInternal} />;
      case 'emp-departments':
        return <DepartmentsPage onNavigate={onNavigateInternal} />;
      case 'emp-list':
        return <EmployeesList initialFilter={empListFilter} onNavigate={(t) => setActiveTab(t)} />;
      case 'emp-add':
        return <AddEmployeeForm onNavigate={(t) => { setEmpListFilter(null); setActiveTab(t); }} />;
      case 'emp-org-chart':
        return <OrgChart onSelect={(id) => { setEmpListFilter({ employeeId: id }); setActiveTab('emp-list'); }} />;
      default:
        return null;
    }
  };

  if (!user) return <div className="flex items-center justify-center h-screen text-slate-500">Loading...</div>;

  return (
    <DashboardShell
      user={user}
      roleLabel="Employee Portal"
      navGroups={navGroups}
      activeTab={activeTab}
      pageTitle={PAGE_TITLES[activeTab] || 'Employees'}
      onLogout={handleLogout}
    >
      <Suspense fallback={<Fallback />}>
        {renderActiveTab()}
      </Suspense>
    </DashboardShell>
  );
}
