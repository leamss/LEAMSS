import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import NotificationBell from '@/components/NotificationBell';
import { LogOut, Menu, ArrowLeft, ChevronDown, ChevronRight } from 'lucide-react';

const AdminReturnBanner = () => {
  const adminToken = localStorage.getItem('admin_token');
  const adminUserData = localStorage.getItem('admin_user');
  if (!adminToken || !adminUserData) return null;
  let adminUser = null;
  try { adminUser = JSON.parse(adminUserData); } catch (e) {}

  const handleReturn = () => {
    localStorage.setItem('token', adminToken);
    localStorage.setItem('user', adminUserData);
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    toast.success('Returned to Admin account');
    window.location.assign('/admin');
  };

  return (
    <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-4 py-2 flex items-center justify-between" data-testid="admin-return-banner">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Viewing as impersonated user</span>
        {adminUser && <span className="text-xs opacity-80">(Admin: {adminUser.name})</span>}
      </div>
      <Button onClick={handleReturn} size="sm" className="bg-white text-orange-600 hover:bg-orange-50 font-medium" data-testid="return-to-admin-btn">
        <ArrowLeft className="h-4 w-4 mr-1" /> Return to Admin
      </Button>
    </div>
  );
};

const NavGroup = ({ label, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-[10px] font-bold uppercase tracking-[0.08em] text-gray-400 hover:text-gray-600 transition-colors"
      >
        <span>{label}</span>
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>
      {open && <div className="space-y-0.5">{children}</div>}
    </div>
  );
};

const NavItem = ({ icon: Icon, label, active, badge, badgeColor = 'bg-[#f7620b]', onClick, testId }) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
      active 
        ? 'bg-[#2a777a]/10 text-[#2a777a] font-semibold' 
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
    }`}
    data-testid={testId}
  >
    {Icon && <Icon className={`h-4 w-4 flex-shrink-0 ${active ? 'text-[#2a777a]' : 'text-gray-400'}`} />}
    <span className="truncate">{label}</span>
    {badge !== undefined && badge > 0 && (
      <Badge className={`ml-auto ${badgeColor} text-white text-[10px] px-1.5 py-0 h-5 min-w-[20px] flex items-center justify-center`}>
        {badge}
      </Badge>
    )}
  </button>
);

const DashboardShell = ({
  user,
  roleLabel,
  navGroups,
  activeTab,
  pageTitle,
  headerActions,
  onNotificationClick,
  onLogout,
  children,
  showBackButton,
  onBack
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#F5F7FA]" data-testid={`${roleLabel?.toLowerCase().replace(/\s/g, '-')}-dashboard`}>
      <AdminReturnBanner />
      <div className="flex">
        {/* Mobile overlay */}
        {sidebarOpen && <div className="fixed inset-0 bg-black/30 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}

        {/* Sidebar */}
        <aside className={`w-[260px] bg-white border-r border-gray-200 flex flex-col fixed h-screen top-0 left-0 z-40 transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`} data-testid="sidebar">
          {/* Logo */}
          <div className="px-5 py-5 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <img src="/leamss-logo.png" alt="LEAMSS" className="h-9 w-9 rounded-lg object-contain" />
              <div>
                <h1 className="text-base font-bold text-gray-900 tracking-tight">LEAMSS</h1>
                <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">{roleLabel}</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5">
            {navGroups.map((group, gi) => {
              if (group.groupLabel) {
                return (
                  <NavGroup key={gi} label={group.groupLabel} defaultOpen={group.defaultOpen !== false}>
                    {group.items.map((item) => (
                      <NavItem
                        key={item.id}
                        icon={item.icon}
                        label={item.label}
                        active={activeTab === item.id}
                        badge={item.badge}
                        badgeColor={item.badgeColor}
                        onClick={() => { item.onClick?.(); setSidebarOpen(false); }}
                        testId={`nav-${item.id}`}
                      />
                    ))}
                  </NavGroup>
                );
              }
              // Flat items (no group)
              return (
                <NavItem
                  key={group.id}
                  icon={group.icon}
                  label={group.label}
                  active={activeTab === group.id}
                  badge={group.badge}
                  badgeColor={group.badgeColor}
                  onClick={() => { group.onClick?.(); setSidebarOpen(false); }}
                  testId={`nav-${group.id}`}
                />
              );
            })}
          </nav>

          {/* User info */}
          <div className="px-4 py-3 border-t border-gray-100">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="h-8 w-8 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                <span className="text-[#2a777a] font-bold text-xs">{user?.name?.charAt(0) || '?'}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800 truncate">{user?.name}</p>
                <p className="text-[11px] text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              onClick={onLogout}
              variant="ghost"
              size="sm"
              className="w-full justify-start text-gray-500 hover:text-gray-700 hover:bg-gray-50 h-8 text-xs"
              data-testid="logout-button"
            >
              <LogOut className="mr-2 h-3.5 w-3.5" /> Logout
            </Button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 md:ml-[260px]">
          {/* Header */}
          <header className="sticky top-0 z-10 bg-white/90 backdrop-blur-md border-b border-gray-200 px-4 md:px-6 py-3">
            <div className="flex justify-between items-center max-w-[1400px] mx-auto">
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="md:hidden h-8 w-8 p-0" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="mobile-menu-btn">
                  <Menu className="h-5 w-5" />
                </Button>
                {showBackButton && (
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onBack}>
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                )}
                <h2 className="text-lg font-bold text-gray-900 tracking-tight" data-testid="page-title">{pageTitle}</h2>
              </div>
              <div className="flex items-center gap-2">
                {headerActions}
                <NotificationBell onNotificationClick={onNotificationClick} />
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="p-4 md:p-6">
            <div className="max-w-[1400px] mx-auto">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export { DashboardShell, NavGroup, NavItem, AdminReturnBanner };
export default DashboardShell;
