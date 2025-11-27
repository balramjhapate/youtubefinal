import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  Download,
  FileText,
  Brain,
  MessageSquare,
  CheckSquare,
  Square,
  Trash2,
} from 'lucide-react';
import { VideoCard } from './VideoCard';
import { Button, LoadingOverlay } from '../common';
import { videosApi } from '../../api';
import { useStore } from '../../store';

export function VideoList({ videos, isLoading }) {
  const queryClient = useQueryClient();
  const {
    selectedVideos,
    toggleVideoSelection,
    selectAllVideos,
    clearSelection,
    startProcessing,
    completeProcessing,
  } = useStore();
  const [synthesizeModalOpen, setSynthesizeModalOpen] = useState(false);
  const [currentVideoId, setCurrentVideoId] = useState(null);

  // Mutations
  const downloadMutation = useMutation({
    mutationFn: async (videoId) => {
      startProcessing(videoId, 'download');
      return videosApi.download(videoId);
    },
    onSuccess: (data, videoId) => {
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['video', videoId]);
      toast.success('Download started');
    },
    onError: (error, videoId) => {
      completeProcessing(videoId);
      toast.error(error?.response?.data?.error || 'Download failed');
    },
  });

  const transcribeMutation = useMutation({
    mutationFn: async (videoId) => {
      startProcessing(videoId, 'transcribe');
      return videosApi.transcribe(videoId);
    },
    onSuccess: (data, videoId) => {
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['video', videoId]);
      completeProcessing(videoId);
      toast.success('Transcription, AI processing, and script generation completed!');
    },
    onError: (error, videoId) => {
      completeProcessing(videoId);
      const errorMessage = error?.response?.data?.error || error?.message || 'Processing failed';
      toast.error(errorMessage);
    },
  });

  const processAIMutation = useMutation({
    mutationFn: async (videoId) => {
      startProcessing(videoId, 'processAI');
      return videosApi.processAI(videoId);
    },
    onSuccess: (data, videoId) => {
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['video', videoId]);
      toast.success('AI processing started');
    },
    onError: (error, videoId) => {
      completeProcessing(videoId);
      toast.error(error?.response?.data?.error || 'AI processing failed');
    },
  });

  const generatePromptMutation = useMutation({
    mutationFn: videosApi.generateAudioPrompt,
    onSuccess: () => {
      toast.success('Audio prompt generated');
      queryClient.invalidateQueries(['videos']);
    },
    onError: (error) => toast.error(error),
  });

  const deleteMutation = useMutation({
    mutationFn: videosApi.delete,
    onSuccess: () => {
      toast.success('Video deleted successfully');
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['dashboard-stats']);
    },
    onError: (error) => {
      const errorMessage = error?.response?.data?.error || error?.message || error || 'Failed to delete video';
      toast.error(errorMessage);
    },
  });

  // Bulk mutations
  const bulkDownloadMutation = useMutation({
    mutationFn: videosApi.bulkDownload,
    onSuccess: () => {
      toast.success('Bulk download started');
      queryClient.invalidateQueries(['videos']);
      clearSelection();
    },
    onError: (error) => toast.error(error),
  });

  const bulkTranscribeMutation = useMutation({
    mutationFn: videosApi.bulkTranscribe,
    onSuccess: () => {
      toast.success('Bulk transcription started');
      queryClient.invalidateQueries(['videos']);
      clearSelection();
    },
    onError: (error) => toast.error(error),
  });

  const bulkProcessAIMutation = useMutation({
    mutationFn: videosApi.bulkProcessAI,
    onSuccess: () => {
      toast.success('Bulk AI processing started');
      queryClient.invalidateQueries(['videos']);
      clearSelection();
    },
    onError: (error) => toast.error(error),
  });

  const bulkGeneratePromptsMutation = useMutation({
    mutationFn: videosApi.bulkGeneratePrompts,
    onSuccess: () => {
      toast.success('Bulk prompt generation started');
      queryClient.invalidateQueries(['videos']);
      clearSelection();
    },
    onError: (error) => toast.error(error),
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: videosApi.bulkDelete,
    onSuccess: () => {
      toast.success('Videos deleted successfully');
      queryClient.invalidateQueries(['videos']);
      clearSelection();
    },
    onError: (error) => toast.error(error),
  });

  const handleSelectAll = () => {
    if (selectedVideos.length === videos.length) {
      clearSelection();
    } else {
      selectAllVideos(videos.map((v) => v.id));
    }
  };

  const handleSynthesize = (videoId) => {
    setCurrentVideoId(videoId);
    setSynthesizeModalOpen(true);
  };

  if (isLoading) {
    return <LoadingOverlay message="Loading videos..." />;
  }

  if (!videos || videos.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">No videos found</div>
        <p className="text-sm text-gray-500">
          Click "Add Video" to extract your first video from Xiaohongshu
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Bulk actions toolbar */}
      {selectedVideos.length > 0 && (
        <div className="glass-card p-3 mb-4 flex flex-wrap items-center gap-3">
          <span className="text-sm text-gray-400">
            {selectedVideos.length} selected
          </span>

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              icon={Download}
              onClick={() => bulkDownloadMutation.mutate(selectedVideos)}
              loading={bulkDownloadMutation.isPending}
            >
              Download All
            </Button>

            <Button
              size="sm"
              variant="secondary"
              icon={FileText}
              onClick={() => bulkTranscribeMutation.mutate(selectedVideos)}
              loading={bulkTranscribeMutation.isPending}
            >
              Transcribe All
            </Button>

            <Button
              size="sm"
              variant="secondary"
              icon={Brain}
              onClick={() => bulkProcessAIMutation.mutate(selectedVideos)}
              loading={bulkProcessAIMutation.isPending}
            >
              AI Process All
            </Button>

            <Button
              size="sm"
              variant="secondary"
              icon={MessageSquare}
              onClick={() => bulkGeneratePromptsMutation.mutate(selectedVideos)}
              loading={bulkGeneratePromptsMutation.isPending}
            >
              Generate All Prompts
            </Button>
          </div>

          <div className="flex gap-2 ml-auto">
            <Button
              size="sm"
              variant="danger"
              icon={Trash2}
              onClick={() => {
                if (window.confirm(`Delete ${selectedVideos.length} video(s)?`)) {
                  bulkDeleteMutation.mutate(selectedVideos);
                }
              }}
              loading={bulkDeleteMutation.isPending}
            >
              Delete All
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={clearSelection}
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Select all */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={handleSelectAll}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white"
        >
          {selectedVideos.length === videos.length ? (
            <CheckSquare className="w-4 h-4" />
          ) : (
            <Square className="w-4 h-4" />
          )}
          {selectedVideos.length === videos.length ? 'Deselect All' : 'Select All'}
        </button>
        <span className="text-sm text-gray-500">
          ({videos.length} video{videos.length !== 1 ? 's' : ''})
        </span>
      </div>

      {/* Video grid - 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {videos.map((video) => (
          <VideoCard
            key={video.id}
            video={video}
            isSelected={selectedVideos.includes(video.id)}
            onSelect={toggleVideoSelection}
            onDownload={() => downloadMutation.mutate(video.id)}
            onTranscribe={() => transcribeMutation.mutate(video.id)}
            onProcessAI={() => processAIMutation.mutate(video.id)}
            onGeneratePrompt={() => generatePromptMutation.mutate(video.id)}
            onSynthesize={() => handleSynthesize(video.id)}
            onDelete={() => deleteMutation.mutate(video.id)}
          />
        ))}
      </div>
    </div>
  );
}

export default VideoList;
