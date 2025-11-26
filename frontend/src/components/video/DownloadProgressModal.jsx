import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, X } from 'lucide-react';
import { Modal } from '../common';
import { videosApi } from '../../api';

export function DownloadProgressModal({ videoId, isOpen, onClose, videoTitle }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('downloading'); // downloading, completed, error

  // Poll video status to check if download completed
  const { data: video } = useQuery({
    queryKey: ['video', videoId],
    queryFn: () => videosApi.getById(videoId),
    enabled: isOpen && !!videoId,
    refetchInterval: (query) => {
      const video = query.state.data;
      // Stop polling if download completed or failed
      if (video?.is_downloaded) {
        setProgress(100);
        setStatus('completed');
        setTimeout(() => {
          onClose();
        }, 1500);
        return false;
      }
      // Poll every 500ms while downloading
      return 500;
    },
  });

  // Simulate progress (since backend doesn't provide real-time progress)
  useEffect(() => {
    if (!isOpen || !videoId) {
      setProgress(0);
      setStatus('downloading');
      return;
    }

    // Reset progress when modal opens
    setProgress(0);
    setStatus('downloading');

    // Simulate progress updates
    const interval = setInterval(() => {
      setProgress((prev) => {
        // Increase progress gradually, but cap at 95% until download actually completes
        if (prev < 95) {
          return Math.min(prev + Math.random() * 5, 95);
        }
        return prev;
      });
    }, 300);

    return () => clearInterval(interval);
  }, [isOpen, videoId]);

  // Update status based on video data
  useEffect(() => {
    if (video?.is_downloaded) {
      setProgress(100);
      setStatus('completed');
    }
  }, [video]);

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={status === 'completed' ? onClose : undefined}
      title="Downloading Video"
      showCloseButton={status === 'completed'}
      size="md"
    >
      <div className="space-y-6">
        {/* Video Info */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-1">Video</h3>
          <p className="text-white truncate">{videoTitle || 'Loading...'}</p>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Progress</span>
            <span className="text-white font-medium">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[var(--rednote-primary)] to-[var(--rednote-primary)]/80 transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Status Message */}
        <div className="text-center">
          {status === 'downloading' && (
            <p className="text-sm text-gray-400 flex items-center justify-center gap-2">
              <Download className="w-4 h-4 animate-pulse" />
              Downloading video file...
            </p>
          )}
          {status === 'completed' && (
            <p className="text-sm text-green-400 flex items-center justify-center gap-2">
              <Download className="w-4 h-4" />
              Download completed successfully!
            </p>
          )}
          {status === 'error' && (
            <p className="text-sm text-red-400">Download failed. Please try again.</p>
          )}
        </div>

        {/* Close button (only show when completed) */}
        {status === 'completed' && (
          <div className="flex justify-end pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg btn-secondary"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default DownloadProgressModal;

