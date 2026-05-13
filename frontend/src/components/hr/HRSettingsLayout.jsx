import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  ArrowLeft, Settings as SettingsIcon, Calendar, FileText, Users, History,
  Home, ChevronRight,
} from 'lucide-react';

const NAV = [
  { key: 'settings', path: '/admin/hr/settings', label: 'Attendance Settings', icon: SettingsIcon },
  { key: 'holidays', path: '/admin/hr/holidays', label: 'Holiday Calendar', icon: Calendar },
  { key: 'leave-types', path: '/admin/hr/leave-types', label: 'Leave Types & Policies', icon: FileText },
  { key: 'approvers', path: '/admin/hr/approvers', label: 'Approval Configuration', icon: Users },
  { key: 'audit', path: '/admin/hr/audit', label: 'Audit Log', icon: History },
];

export default function HRSettingsLayout({ children, title, subtitle, breadcrumb }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50" data-testid="hr-settings-layout">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin')} data-testid="back-admin-btn">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Admin
            </Button>
            <nav className="flex items-center gap-1 text-xs text-slate-500" data-testid="breadcrumb">
              <Home className="h-3 w-3" />
              <ChevronRight className="h-3 w-3" />
              <span>Admin</span>
              <ChevronRight className="h-3 w-3" />
              <span className="text-slate-700 font-medium">HR Settings</span>
              {breadcrumb && (
                <>
                  <ChevronRight className="h-3 w-3" />
                  <span className="text-slate-900 font-semibold">{breadcrumb}</span>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      <div className="flex max-w-7xl mx-auto">
        {/* Sidebar */}
        <aside className="w-60 border-r border-slate-200 min-h-[calc(100vh-56px)] bg-white" data-testid="hr-sidebar">
          <div className="p-4 border-b border-slate-100">
            <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">HR Settings</p>
          </div>
          <ul className="py-2">
            {NAV.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return (
                <li key={item.key}>
                  <button
                    onClick={() => navigate(item.path)}
                    className={`w-full text-left px-4 py-2 flex items-center gap-2 text-sm transition-colors ${
                      active
                        ? 'bg-indigo-50 text-indigo-700 border-l-2 border-indigo-600 font-semibold'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                    data-testid={`hr-nav-${item.key}`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* Content */}
        <main className="flex-1 p-6">
          <div className="mb-5">
            <h1 className="text-2xl font-bold text-slate-900" data-testid="hr-page-title">{title}</h1>
            {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
