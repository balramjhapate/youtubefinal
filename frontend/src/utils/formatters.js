// Format duration in seconds to MM:SS format
export const formatDuration = (seconds) => {
  if (!seconds || seconds <= 0) return '0:00';
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

// Format date to readable string
export const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Format relative time
export const formatRelativeTime = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'Just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHour < 24) return `${diffHour} hr ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;

  return formatDate(dateString);
};

// Format elapsed seconds
export const formatElapsedTime = (seconds) => {
  if (!seconds || seconds < 0) return '0s';

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;

  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
};

// Truncate text
export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// Validate Xiaohongshu URL
export const isValidXhsUrl = (url) => {
  if (!url) return false;
  const patterns = [
    /xiaohongshu\.com/,
    /xhslink\.com/,
    /xhs\.cn/,
    /redbook\.com/,
  ];
  return patterns.some((pattern) => pattern.test(url));
};

// Extract video ID from URL
export const extractVideoId = (url) => {
  if (!url) return null;
  const match = url.match(/\/item\/([a-zA-Z0-9]+)/);
  return match ? match[1] : null;
};

// Format file size
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

// Check if a video is currently processing
export const isVideoProcessing = (video) => {
  if (!video) return false;
  return (
    video.transcription_status === 'transcribing' ||
    video.ai_processing_status === 'processing' ||
    video.script_status === 'generating' ||
    video.synthesis_status === 'synthesizing'
  );
};
