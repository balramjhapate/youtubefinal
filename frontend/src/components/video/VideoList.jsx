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
} from 'lucide-react';
import { VideoCard } from './VideoCard';
import { Button, LoadingOverlay } from '../common';
import { videosApi } from '../../api';
import { useStore } from '../../store';

export function VideoList({ videos, isLoading }) {
  const queryClient = useQueryClient();
  const { selectedVideos, toggleVideoSelection, selectAllVideos, clearSelection } = useStore();
  const [synthesizeModalOpen, setSynthesizeModalOpen] = useState(false);
  const [currentVideoId, setCurrentVideoId] = useState(null);

  // Mutations
  const downloadMutation = useMutation({
    mutationFn: videosApi.download,
    onSuccess: () => {
      toast.success('Video downloaded successfully');
      queryClient.invalidateQueries(['videos']);
    },
    onError: (error) => toast.error(error),
  });

  const transcribeMutation = useMutation({
    mutationFn: videosApi.transcribe,
    onSuccess: () => {
      toast.success('Transcription started');
      queryClient.invalidateQueries(['videos']);
    },
    onError: (error) => toast.error(error),
  });

  const processAIMutation = useMutation({
    mutationFn: videosApi.processAI,
    onSuccess: () => {
      toast.success('AI processing completed');
      queryClient.invalidateQueries(['videos']);
    },
    onError: (error) => toast.error(error),
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
      toast.success('Video deleted');
      queryClient.invalidateQueries(['videos']);
    },
    onError: (error) => toast.error(error),
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

          <Button
            size="sm"
            variant="ghost"
            onClick={clearSelection}
          >
            Clear
          </Button>
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

      {/* Video grid */}
      <div className="space-y-4">
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
