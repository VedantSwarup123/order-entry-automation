import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  PlusCircle,
  Inbox,
  Users,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  Search,
  Zap,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/orders', icon: Package, label: 'Orders' },
  { to: '/orders/new', icon: PlusCircle, label: 'New Order' },
  { to: '/inbox', icon: Inbox, label: 'Inbox' },
  { to: '/customers', icon: Users, label: 'Customers' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/orders': 'Orders',
  '/orders/new': 'New Order',
  '/inbox': 'Inbox',
  '/customers': 'Customers',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

export default function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const pageTitle =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/orders/') ? 'Order Detail' :
     location.pathname.startsWith('/customers/') ? 'Customer Detail' : 'Dashboard');

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <aside
        className="flex flex-col h-full border-r border-[var(--border)] bg-[var(--bg-card)] backdrop-blur-xl transition-all duration-300 ease-in-out"
        style={{ width: collapsed ? 72 : 280, minWidth: collapsed ? 72 : 280 }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-[var(--border)]">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-emerald)] shrink-0">
            <Zap size={18} className="text-white" />
          </div>
          {!collapsed && (
            <span className="text-base font-bold tracking-tight text-[var(--text-primary)] whitespace-nowrap">
              OrderFlow
            </span>
          )}
        </div>

        {/* Nav Links */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/' || item.to === '/orders'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  isActive
                    ? 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border border-[var(--accent-blue)]/20'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] border border-transparent'
                }`
              }
            >
              <item.icon size={20} className="shrink-0" />
              {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Collapse Toggle */}
        <div className="px-3 py-3 border-t border-[var(--border)]">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center w-full py-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors duration-200"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            {!collapsed && <span className="ml-2 text-sm">Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex items-center justify-between px-8 h-16 border-b border-[var(--border)] bg-[var(--bg-primary)]">
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">{pageTitle}</h1>
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-secondary)] w-64">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search orders..."
                className="bg-transparent outline-none text-sm w-full text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
              />
              <kbd className="text-xs px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-muted)]">/</kbd>
            </div>
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors duration-200"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
