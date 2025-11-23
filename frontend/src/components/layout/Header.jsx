import { Menu, Settings, Plus } from 'lucide-react';
import { useStore } from '../../store';
import { Button } from '../common';

export function Header({ onAddVideo }) {
  const { toggleSidebar, openSettingsModal } = useStore();

  return (
    <header className="fixed top-0 left-0 right-0 z-40 glass-card rounded-none border-t-0 border-x-0">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        {/* Left side */}
        <div className="flex items-center gap-4">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors lg:hidden"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--rednote-primary)] flex items-center justify-center">
              <span className="text-white font-bold text-sm">R</span>
            </div>
            <h1 className="text-lg font-semibold hidden sm:block">
              RedNote Manager
            </h1>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            icon={Plus}
            onClick={onAddVideo}
          >
            <span className="hidden sm:inline">Add Video</span>
          </Button>

          <button
            onClick={openSettingsModal}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
