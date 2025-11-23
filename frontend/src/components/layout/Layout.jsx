import { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useStore } from '../../store';
import { VideoExtractModal } from '../video/VideoExtractModal';
import { AISettingsModal } from '../ai/AISettingsModal';

export function Layout({ children }) {
  const [extractModalOpen, setExtractModalOpen] = useState(false);
  const { settingsModalOpen, closeSettingsModal } = useStore();

  return (
    <div className="min-h-screen">
      {/* Animated background */}
      <div className="animated-bg">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      {/* Header */}
      <Header onAddVideo={() => setExtractModalOpen(true)} />

      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <main className="pt-16 lg:pl-64 min-h-screen">
        <div className="p-4 md:p-6 lg:p-8">
          {children}
        </div>
      </main>

      {/* Modals */}
      <VideoExtractModal
        isOpen={extractModalOpen}
        onClose={() => setExtractModalOpen(false)}
      />

      <AISettingsModal
        isOpen={settingsModalOpen}
        onClose={closeSettingsModal}
      />
    </div>
  );
}

export default Layout;
