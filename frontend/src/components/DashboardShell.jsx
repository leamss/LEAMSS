import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import NotificationBell from '@/components/NotificationBell';
import { LanguageToggle, useLanguage } from '@/components/LanguageProvider';
import { ThemeToggle } from '@/components/ThemeProvider';
import { LogOut, Menu, ArrowLeft, ChevronDown, ChevronRight, MessageCircle, TicketCheck } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const COMM_API = `${BACKEND_URL}/api`;

// Hindi translations for nav labels
const hiLabels = {
  'Dashboard': 'डैशबोर्ड', 'Pending Sales': 'लंबित बिक्री', 'Sales Report': 'बिक्री रिपोर्ट',
  'Commissions': 'कमीशन', 'Refunds': 'रिफंड', 'Payment Reminders': 'भुगतान अनुस्मारक',
  'Revenue Forecast': 'राजस्व पूर्वानुमान', 'Conversion Funnel': 'रूपांतरण फ़नल',
  'Commission Analytics': 'कमीशन विश्लेषण', 'Country & Product': 'देश और उत्पाद',
  'All Cases': 'सभी केस', 'Pending Assignment': 'लंबित असाइनमेंट', 'Users': 'उपयोगकर्ता',
  'Bulk Operations': 'बल्क ऑपरेशन', 'SLA Tracker': 'SLA ट्रैकर', 'Case Transfer': 'केस ट्रांसफर',
  'CM Performance': 'CM प्रदर्शन', 'Products': 'उत्पाद', 'Tickets': 'टिकट', 'Settings': 'सेटिंग्स',
  'Appointments': 'अपॉइंटमेंट', 'AI Workflow Builder': 'AI वर्कफ़्लो बिल्डर', 'Workflows': 'वर्कफ़्लो',
  'Marketing': 'मार्केटिंग', 'Knowledge Base': 'ज्ञान केंद्र', 'Satisfaction Surveys': 'संतुष्टि सर्वेक्षण',
  'Canned Responses': 'तैयार उत्तर', 'Referral Program': 'रेफरल कार्यक्रम', 'Client Greetings': 'ग्राहक शुभकामनाएं',
  'My Cases': 'मेरे केस', 'Pending Review': 'समीक्षा लंबित', 'All Documents': 'सभी दस्तावेज़',
  'Support': 'सहायता', 'Document Expiry Alerts': 'दस्तावेज़ समाप्ति अलर्ट', 'Client Info Sheets': 'ग्राहक जानकारी',
  'Survey Stats': 'सर्वेक्षण आंकड़े', 'Overview': 'अवलोकन', 'Action Required': 'कार्रवाई आवश्यक',
  'Workflow Steps': 'वर्कफ़्लो चरण', 'My Documents': 'मेरे दस्तावेज़', 'My Info Sheet': 'मेरी जानकारी',
  'Payments': 'भुगतान', 'Document Checklist': 'दस्तावेज़ चेकलिस्ट', 'Help Center': 'सहायता केंद्र',
  'Rate Experience': 'अनुभव रेट करें', 'Refer a Friend': 'दोस्त को रेफर करें', 'Case Timeline': 'केस टाइमलाइन',
  // Phase 10 - Admin Superpowers
  'Approval Center': 'अनुमोदन केंद्र', 'Unified Approval Center': 'एकीकृत अनुमोदन केंद्र',
  'Refund Manager': 'रिफंड प्रबंधक', 'Revenue Dashboard': 'राजस्व डैशबोर्ड',
  'Report Builder': 'रिपोर्ट बिल्डर', 'Custom Report Builder': 'कस्टम रिपोर्ट बिल्डर',
  'Email Digest': 'ईमेल डाइजेस्ट', 'Analytics': 'विश्लेषण', 'Activity Log': 'गतिविधि लॉग',
  'Pre-Assessments': 'प्री-असेसमेंट',
  // Phase 11 - CM Efficiency
  'Smart Workload': 'स्मार्ट वर्कलोड', 'Client Messages': 'ग्राहक संदेश',
  'Batch Operations': 'बैच ऑपरेशन', 'Batch Case Operations': 'बैच केस ऑपरेशन',
  'Support Tickets': 'सहायता टिकट', 'Client Communication Hub': 'ग्राहक संवाद केंद्र',
  'Info Sheets': 'जानकारी शीट', 'Expiry Alerts': 'समाप्ति अलर्ट',
  // Phase 12 - Client Experience
  'Eligibility Check': 'योग्यता जांच', 'Family Members': 'परिवार के सदस्य',
  'EMI Plans': 'EMI योजनाएं', 'EMI Payment Plans': 'EMI भुगतान योजनाएं',
  'Doc Completion': 'दस्तावेज़ पूर्णता', 'Document Completion': 'दस्तावेज़ पूर्णता',
  'My Journey': 'मेरी यात्रा', 'My Case Journey': 'मेरे केस की यात्रा',
  'Messages': 'संदेश', 'My Profile': 'मेरी प्रोफ़ाइल',
  'Refer a Friend': 'दोस्त को रेफर करें',
  // Groups
  'Sales & Finance': 'बिक्री और वित्त', 'Cases & Users': 'केस और उपयोगकर्ता', 'System': 'सिस्टम',
  'Tools': 'उपकरण', 'Case Management': 'केस प्रबंधन', 'Documents': 'दस्तावेज़',
  'My Case': 'मेरा केस', 'Finance': 'वित्त', 'Resources': 'संसाधन',
  'Communication': 'संवाद', 'Reports & Analytics': 'रिपोर्ट और विश्लेषण',
  // Roles
  'Admin Portal': 'एडमिन पोर्टल', 'Case Manager': 'केस मैनेजर', 'Partner Portal': 'पार्टनर पोर्टल',
  'Client Portal': 'क्लाइंट पोर्टल', 'Client': 'क्लाइंट',
};

const AdminReturnBanner = () => {
  const adminToken = localStorage.getItem('admin_token');
  const adminUserData = localStorage.getItem('admin_user');
  if (!adminToken || !adminUserData) return null;
  let adminUser = null;
  try { adminUser = JSON.parse(adminUserData); } catch (e) {}

  // Current (impersonated) user — to show their name in the banner
  let currentUser = null;
  try { currentUser = JSON.parse(localStorage.getItem('user') || 'null'); } catch (e) {}

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
        <span className="text-lg">🔄</span>
        <span className="text-sm font-semibold" data-testid="impersonating-label">
          Impersonating {currentUser?.name || 'user'}
          {currentUser?.role && <span className="ml-1.5 px-1.5 py-0.5 rounded bg-white/20 text-[10px] font-medium uppercase tracking-wide">{currentUser.role.replace('_', ' ')}</span>}
        </span>
        {adminUser && <span className="text-xs opacity-80 ml-2">(Logged in as Admin: {adminUser.name})</span>}
      </div>
      <Button onClick={handleReturn} size="sm" className="bg-white text-orange-600 hover:bg-orange-50 font-medium" data-testid="return-to-admin-btn">
        <ArrowLeft className="h-4 w-4 mr-1" /> Exit Impersonation
      </Button>
    </div>
  );
};

/**
 * Phase 21 Slice 4 Sub-Slice B — Communication header buttons.
 * Chat icon with live unread badge (polls every 15s, pauses on /chat page)
 * and quick Tickets jump. Internal staff only — silently hides if API returns 4xx.
 */
const HeaderCommButtons = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [unread, setUnread] = useState(0);
  const [hidden, setHidden] = useState(false);

  const onChatPage = location.pathname.startsWith('/portal/chat') || location.pathname.startsWith('/admin/chat');
  const isClient = user?.user_type === 'client';

  useEffect(() => {
    if (!user || isClient || hidden) return undefined;
    const token = localStorage.getItem('token');
    if (!token) return undefined;
    const auth = { headers: { Authorization: `Bearer ${token}` } };

    const fetchCount = async () => {
      try {
        const { data } = await axios.get(`${COMM_API}/internal-chat/unread-count`, auth);
        setUnread(onChatPage ? 0 : (data?.total || 0));
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401 || status === 403 || status === 404) setHidden(true);
      }
    };

    fetchCount();
    const tid = setInterval(fetchCount, 15000);
    return () => clearInterval(tid);
  }, [user, isClient, hidden, onChatPage]);

  // On chat page, force-reset visual badge to 0 (real read happens server-side)
  useEffect(() => { if (onChatPage) setUnread(0); }, [onChatPage]);

  if (!user || isClient || hidden) return null;

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="relative h-8 w-8 p-0 hover:bg-leamss-teal-50 dark:hover:bg-leamss-teal-900/20"
        onClick={() => navigate('/portal/chat')}
        data-testid="header-chat-icon"
        title="Chat"
      >
        <MessageCircle className="h-4 w-4 text-leamss-teal-600 dark:text-leamss-teal-400" />
        {unread > 0 && (
          <Badge
            className="absolute -top-1 -right-1 h-4 min-w-[16px] px-1 bg-leamss-red-500 text-white text-[9px] font-bold flex items-center justify-center rounded-full border border-white"
            data-testid="header-chat-unread-badge"
          >
            {unread > 99 ? '99+' : unread}
          </Badge>
        )}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 w-8 p-0 hover:bg-leamss-orange-50 dark:hover:bg-leamss-orange-900/20"
        onClick={() => navigate('/portal/tickets')}
        data-testid="header-tickets-link"
        title="Tickets"
      >
        <TicketCheck className="h-4 w-4 text-leamss-orange-600 dark:text-leamss-orange-400" />
      </Button>
    </>
  );
};

const NavGroup = ({ label, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-[10px] font-bold uppercase tracking-[0.08em] text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
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
        ? 'bg-[#2a777a]/10 text-[#2a777a] dark:bg-[#2a777a]/20 dark:text-[#4db8bb] font-semibold' 
        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-800 dark:hover:text-gray-200'
    }`}
    data-testid={testId}
  >
    {Icon && <Icon className={`h-4 w-4 flex-shrink-0 ${active ? 'text-[#2a777a] dark:text-[#4db8bb]' : 'text-gray-400 dark:text-gray-500'}`} />}
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
  navGroups = [],
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
  const { lang } = useLanguage();
  const tl = (text) => lang === 'hi' ? (hiLabels[text] || text) : text;

  return (
    <div className="min-h-screen bg-[#F5F7FA] dark:bg-[#0f172a] transition-colors duration-300" data-testid={`${roleLabel?.toLowerCase().replace(/\s/g, '-')}-dashboard`}>
      <AdminReturnBanner />
      <div className="flex">
        {/* Mobile overlay */}
        {sidebarOpen && <div className="fixed inset-0 bg-black/30 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}

        {/* Sidebar */}
        <aside className={`w-[260px] bg-white dark:bg-[#1e293b] border-r border-gray-200 dark:border-gray-700 flex flex-col fixed h-screen top-0 left-0 z-40 transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`} data-testid="sidebar">
          {/* Logo */}
          <div className="px-5 py-5 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <img src="/leamss-logo.png" alt="LEAMSS" className="h-9 w-9 rounded-lg object-contain" />
              <div>
                <h1 className="text-base font-bold text-gray-900 dark:text-white tracking-tight">LEAMSS</h1>
                <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">{tl(roleLabel)}</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5">
            {navGroups.map((group, gi) => {
              if (group.groupLabel) {
                return (
                  <NavGroup key={gi} label={tl(group.groupLabel)} defaultOpen={group.defaultOpen !== false}>
                    {group.items.map((item) => (
                      <NavItem
                        key={item.id}
                        icon={item.icon}
                        label={tl(item.label)}
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
                  label={tl(group.label)}
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
          <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="h-8 w-8 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                <span className="text-[#2a777a] dark:text-[#4db8bb] font-bold text-xs">{user?.name?.charAt(0) || '?'}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">{user?.name}</p>
                <p className="text-[11px] text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              onClick={onLogout}
              variant="ghost"
              size="sm"
              className="w-full justify-start text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 h-8 text-xs"
              data-testid="logout-button"
            >
              <LogOut className="mr-2 h-3.5 w-3.5" /> Logout
            </Button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 md:ml-[260px]">
          {/* Header */}
          <header className="sticky top-0 z-10 bg-white/90 dark:bg-[#1e293b]/90 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 px-4 md:px-6 py-3">
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
                <h2 className="text-sm sm:text-lg font-bold text-gray-900 dark:text-white tracking-tight truncate max-w-[120px] sm:max-w-none" data-testid="page-title">{tl(pageTitle)}</h2>
              </div>
              <div className="flex items-center gap-2">
                {headerActions}
                <HeaderCommButtons user={user} />
                <ThemeToggle />
                <LanguageToggle />
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
