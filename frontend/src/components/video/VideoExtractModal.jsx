import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { showSuccess, showError } from '../../utils/alerts';
import { Link2, Upload, Video as VideoIcon, FileVideo } from 'lucide-react';
import { Modal, Button, Input } from '../common';
import { videosApi } from '../../api';

const VIDEO_SOURCES = [
  {
    id: 'rednote',
    name: 'RedNote/Xiaohongshu',
    icon: VideoIcon,
    color: 'bg-red-500/20 text-red-400 border-red-500/30',
    placeholder: 'https://www.xiaohongshu.com/explore/...',
    description: 'Paste a RedNote/Xiaohongshu video URL',
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: VideoIcon,
    color: 'bg-red-600/20 text-red-500 border-red-600/30',
    placeholder: 'https://www.youtube.com/watch?v=... or youtube.com/shorts/...',
    description: 'Paste a YouTube video or Shorts URL',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    icon: VideoIcon,
    color: 'bg-blue-600/20 text-blue-400 border-blue-600/30',
    placeholder: 'https://www.facebook.com/watch?v=...',
    description: 'Paste a Facebook video URL',
  },
  {
    id: 'instagram',
    name: 'Instagram',
    icon: VideoIcon,
    color: 'bg-pink-600/20 text-pink-400 border-pink-600/30',
    placeholder: 'https://www.instagram.com/p/...',
    description: 'Paste an Instagram video URL',
  },
  {
    id: 'vimeo',
    name: 'Vimeo',
    icon: VideoIcon,
    color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    placeholder: 'https://vimeo.com/...',
    description: 'Paste a Vimeo video URL',
  },
  {
    id: 'local',
    name: 'Local Upload',
    icon: Upload,
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    placeholder: 'Select video file...',
    description: 'Upload a video file from your computer',
  },
];

export function VideoExtractModal({ isOpen, onClose }) {
  const [selectedSource, setSelectedSource] = useState(null);
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const extractMutation = useMutation({
    mutationFn: async (data) => {
      if (data.source === 'local' && data.file) {
        // Handle file upload using FormData
        const formData = new FormData();
        formData.append('file', data.file);
        if (data.title) {
          formData.append('title', data.title);
        }
        
        // Use axios for file upload
        const response = await videosApi.uploadFile(formData);
        return response;
      } else {
        // Handle URL extraction
        return await videosApi.extract(data.url);
      }
    },
    onSuccess: (data) => {
      if (data.auto_processing) {
        showSuccess('Video Extracted', 'Video extracted successfully. Auto-processing has started in the background!', { timer: 5000 });
      } else {
        showSuccess(
          data.cached ? 'Video Found in Cache' : 'Video Added',
          data.cached ? 'Video was found in cache and added successfully!' : 'Video added successfully!',
          { timer: 3000 }
        );
      }
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['dashboard-stats']);
      // Start polling to show processing status
      const pollInterval = setInterval(() => {
        queryClient.invalidateQueries(['videos']);
      }, 3000);
      // Stop polling after 10 minutes
      setTimeout(() => clearInterval(pollInterval), 10 * 60 * 1000);
      handleClose();
    },
    onError: (error) => {
      const errorMessage = error?.response?.data?.error || error?.message || error || 'Failed to add video';
      setError(errorMessage);
      showError('Extraction Failed', errorMessage);
    },
  });

  const handleClose = () => {
    setSelectedSource(null);
    setUrl('');
    setFile(null);
    setTitle('');
    setError('');
    onClose();
  };

  const validateUrl = (url, source) => {
    if (!url.trim()) return false;
    
    const urlLower = url.toLowerCase();
    switch (source) {
      case 'rednote':
        return /xiaohongshu\.com|xhslink\.com|xhs\.cn|redbook\.com/.test(urlLower);
      case 'youtube':
        return /youtube\.com|youtu\.be/.test(urlLower) && (
          /\/watch\?v=|youtu\.be\/|\/shorts\//.test(urlLower)
        );
      case 'facebook':
        return /facebook\.com|fb\.com/.test(urlLower);
      case 'instagram':
        return /instagram\.com|instagr\.am/.test(urlLower);
      case 'vimeo':
        return /vimeo\.com/.test(urlLower);
      default:
        return url.startsWith('http://') || url.startsWith('https://');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!selectedSource) {
      setError('Please select a video source');
      return;
    }

    if (selectedSource === 'local') {
      if (!file) {
        setError('Please select a video file');
        return;
      }
      extractMutation.mutate({ source: 'local', file, title });
    } else {
      if (!url.trim()) {
        setError('Please enter a URL');
        return;
      }

      if (!validateUrl(url, selectedSource)) {
        const sourceName = VIDEO_SOURCES.find(s => s.id === selectedSource)?.name || 'selected source';
        setError(`Please enter a valid ${sourceName} URL`);
        return;
      }

      extractMutation.mutate({ source: selectedSource, url });
    }
  };

  const selectedSourceData = VIDEO_SOURCES.find(s => s.id === selectedSource);

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add New Video"
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Source Selection Cards */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-3">
            Select Video Source
          </label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {VIDEO_SOURCES.map((source) => {
              const Icon = source.icon;
              const isSelected = selectedSource === source.id;
              return (
                <button
                  key={source.id}
                  type="button"
                  onClick={() => {
                    setSelectedSource(source.id);
                    setUrl('');
                    setFile(null);
                    setError('');
                  }}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    isSelected
                      ? `${source.color} border-opacity-100 scale-105`
                      : 'bg-white/5 border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${isSelected ? '' : 'text-gray-400'}`} />
                    <span className={`text-sm font-medium ${isSelected ? '' : 'text-gray-300'}`}>
                      {source.name}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Input Section */}
        {selectedSource && (
          <div className="space-y-4">
            {selectedSource === 'local' ? (
              <>
                <div>
                  <Input
                    type="file"
                    accept="video/*"
                    label="Select Video File"
                    onChange={(e) => {
                      const selectedFile = e.target.files?.[0];
                      setFile(selectedFile);
                      if (selectedFile && !title) {
                        setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
                      }
                    }}
                    className="file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[var(--rednote-primary)]/20 file:text-[var(--rednote-primary)] hover:file:bg-[var(--rednote-primary)]/30"
                  />
                  {file && (
                    <p className="mt-2 text-xs text-gray-400">
                      Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </p>
                  )}
                </div>
                <Input
                  label="Video Title (Optional)"
                  placeholder="Enter a title for the video"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </>
            ) : (
              <div>
                <Input
                  label={`${selectedSourceData?.name} URL`}
                  placeholder={selectedSourceData?.placeholder}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  error={error}
                  autoFocus
                />
                <p className="mt-2 text-xs text-gray-500">
                  {selectedSourceData?.description}
                </p>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            icon={selectedSource === 'local' ? Upload : Link2}
            loading={extractMutation.isPending}
            disabled={!selectedSource || (selectedSource === 'local' ? !file : !url.trim())}
          >
            {selectedSource === 'local' ? 'Upload Video' : 'Extract Video'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default VideoExtractModal;
