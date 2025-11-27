import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  Settings,
  X,
  Mic,
  FileText,
} from 'lucide-react';
import { useStore } from '../../store';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/videos', icon: Video, label: 'Videos' },
  { path: '/voice-cloning', icon: Mic, label: 'Voice Cloning' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useStore();

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-16 left-0 bottom-0 z-40 w-64 glass-card rounded-none border-t-0 border-b-0 border-l-0 transform transition-transform duration-300 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } lg:translate-x-0`}
      >
        {/* Close button (mobile) */}
        <button
          onClick={toggleSidebar}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-white/10 lg:hidden"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Navigation */}
        <nav className="p-4 pt-6 lg:pt-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => {
                if (window.innerWidth < 1024) toggleSidebar();
              }}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${isActive
                  ? 'bg-[var(--rednote-primary)]/20 text-[var(--rednote-primary)] border border-[var(--rednote-primary)]/30'
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/10">
          <div className="text-xs text-gray-500 text-center">
            RedNote Manager v1.0
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
