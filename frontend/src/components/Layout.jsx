import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useTheme } from '../hooks/useTheme';
import {
  LayoutDashboard,
  Users,
  CalendarCheck,
  Monitor,
  FileBarChart,
  Settings,
  LogOut,
  Menu,
  Fingerprint,
  ScanFace,
  Sun,
  Moon
} from 'lucide-react';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/employees', icon: Users, label: 'Employees' },
  { path: '/attendance', icon: CalendarCheck, label: 'Attendance' },
  { path: '/kiosk', icon: ScanFace, label: 'Kiosk', external: true },
  { path: '/devices', icon: Monitor, label: 'Devices' },
  { path: '/reports', icon: FileBarChart, label: 'Reports' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    // dark class is now on <html> via useTheme hook, not here
    <div className="min-h-screen flex">

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 flex flex-col
          bg-slate-800 dark:bg-[#0f172a] text-white
          transform transition-transform duration-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-700 dark:border-slate-700/60">
          <Fingerprint className="w-8 h-8 text-primary-400" />
          <span className="text-xl font-bold">BioAttend</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map(({ path, icon: Icon, label, external }) => (
            <NavLink
              key={path}
              to={path}
              target={external ? '_blank' : undefined}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive && !external
                    ? 'bg-primary-600 dark:bg-primary-700 text-white'
                    : 'text-gray-300 hover:bg-slate-700 dark:hover:bg-slate-700/60 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5 shrink-0" />
              <span>{label}</span>
              {external && (
                <svg
                  className="w-3 h-3 ml-auto text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              )}
            </NavLink>
          ))}
        </nav>

        {/* ── Profile card — bottom of sidebar ── */}
        <div className="border-t border-slate-700 dark:border-slate-700/60 p-4">
          {/* Avatar + name + role stacked vertically */}
          <div className="flex flex-col items-center gap-2 py-3 px-2">
            <div className="w-11 h-11 bg-primary-600 rounded-full flex items-center justify-center font-bold text-lg text-white shrink-0 ring-2 ring-primary-500/40">
              {user?.username?.[0]?.toUpperCase() || 'A'}
            </div>
            <p className="text-sm font-semibold text-white truncate max-w-full">
              {user?.username || 'Admin'}
            </p>
            <span className="inline-block px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-primary-600/30 text-primary-300 border border-primary-500/40">
              {user?.role || 'admin'}
            </span>
          </div>

          {/* Divider */}
          <div className="my-2 border-t border-slate-700/60 dark:border-slate-700/40" />

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-slate-700 dark:hover:bg-slate-700/60 hover:text-white rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-[#1e293b] text-gray-900 dark:text-white">

        {/* Top header */}
        <header className="h-16 bg-white dark:bg-[#0f172a] border-b border-gray-200 dark:border-slate-700/60 flex items-center px-4 lg:px-6 gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 -ml-2 text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
          >
            <Menu className="w-6 h-6" />
          </button>

          <div className="flex-1" />

          {/* Date */}
          <div className="hidden sm:block text-sm text-gray-500 dark:text-slate-400">
            {new Date().toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </div>

          {/* Theme Toggle */}
          <button
            id="theme-toggle-btn"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className={`
              flex items-center justify-center w-9 h-9 rounded-lg
              transition-colors duration-200
              ${isDark
                ? 'bg-slate-700 text-amber-400 hover:bg-slate-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            `}
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;