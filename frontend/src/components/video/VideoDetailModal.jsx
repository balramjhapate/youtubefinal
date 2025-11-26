import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  Download,
  FileText,
  Brain,
  MessageSquare,

  Play,
  Globe,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { Modal, Button, StatusBadge, AudioPlayer, LoadingSpinner, Select } from '../common';
import { VideoProgressIndicator } from './VideoProgressIndicator';
import { videosApi } from '../../api';
import { formatDate, truncateText } from '../../utils/formatters';
import { useStore } from '../../store';

export function VideoDetailModal() {
  const {
    videoDetailModalOpen,
    selectedVideoId,
    closeVideoDetail,
    startProcessing,
    completeProcessing,
    getProcessingState,
  } = useStore();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState('info');
  const [progress, setProgress] = useState(0);
  
  // Fetch video details - must be before useEffect hooks that use it
  const { data: video, isLoading } = useQuery({
    queryKey: ['video', selectedVideoId],
    queryFn: () => videosApi.getById(selectedVideoId),
    enabled: !!selectedVideoId,
  });
  
  const processingState = selectedVideoId ? getProcessingState(selectedVideoId) : null;

  // Simulate progress
  useEffect(() => {
    if (!processingState) {
      setProgress(0);
      return;
    }

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev < 95) {
          return Math.min(prev + Math.random() * 3, 95);
        }
        return prev;
      });
    }, 300);

    return () => clearInterval(interval);
  }, [processingState]);

  // Check completion
  useEffect(() => {
    if (processingState && video) {
      const { type } = processingState;
      let isCompleted = false;

      if (type === 'download' && video.is_downloaded) {
        isCompleted = true;
      } else if (type === 'transcribe' && video.transcription_status === 'transcribed') {
        isCompleted = true;
      } else if (type === 'processAI' && video.ai_processing_status === 'processed') {
        isCompleted = true;
      }

      if (isCompleted) {
        setProgress(100);
        setTimeout(() => {
          completeProcessing(selectedVideoId);
          setProgress(0);
        }, 1000);
      }
    }
  }, [video, processingState, selectedVideoId, completeProcessing]);



  // Mutations
  const downloadMutation = useMutation({
    mutationFn: async () => {
      startProcessing(selectedVideoId, 'download');
      return videosApi.download(selectedVideoId);
    },
    onSuccess: () => {
      const checkInterval = setInterval(() => {
        queryClient.invalidateQueries(['video', selectedVideoId]);
        queryClient.invalidateQueries(['videos']);
        const updatedVideo = queryClient.getQueryData(['video', selectedVideoId]);
        if (updatedVideo?.is_downloaded) {
          clearInterval(checkInterval);
          completeProcessing(selectedVideoId);
          toast.success('Video downloaded successfully');
        }
      }, 1000);

      setTimeout(() => {
        clearInterval(checkInterval);
        completeProcessing(selectedVideoId);
      }, 60000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'Download failed');
    },
  });

  const transcribeMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'transcribe');
      return videosApi.transcribe(selectedVideoId);
    },
    onSuccess: () => {
      toast.success('Transcription started');
      queryClient.invalidateQueries(['video', selectedVideoId]);
      
      const checkInterval = setInterval(() => {
        queryClient.invalidateQueries(['video', selectedVideoId]);
        const updatedVideo = queryClient.getQueryData(['video', selectedVideoId]);
        if (updatedVideo?.transcription_status === 'transcribed' || updatedVideo?.transcription_status === 'failed') {
          clearInterval(checkInterval);
          completeProcessing(selectedVideoId);
          if (updatedVideo.transcription_status === 'transcribed') {
            toast.success('Transcription completed');
          }
        }
      }, 2000);

      setTimeout(() => {
        clearInterval(checkInterval);
        completeProcessing(selectedVideoId);
      }, 300000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'Transcription failed');
    },
  });

  const processAIMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'processAI');
      return videosApi.processAI(selectedVideoId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['video', selectedVideoId]);
      
      const checkInterval = setInterval(() => {
        queryClient.invalidateQueries(['video', selectedVideoId]);
        const updatedVideo = queryClient.getQueryData(['video', selectedVideoId]);
        if (updatedVideo?.ai_processing_status === 'processed' || updatedVideo?.ai_processing_status === 'failed') {
          clearInterval(checkInterval);
          completeProcessing(selectedVideoId);
          if (updatedVideo.ai_processing_status === 'processed') {
            toast.success('AI processing completed');
          }
        }
      }, 2000);

      setTimeout(() => {
        clearInterval(checkInterval);
        completeProcessing(selectedVideoId);
      }, 120000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'AI processing failed');
    },
  });



  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (!videoDetailModalOpen) return null;

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'ai', label: 'AI Summary' },
  ];

  return (
    <Modal
      isOpen={videoDetailModalOpen}
      onClose={closeVideoDetail}
      title="Video Details"
      size="xl"
    >
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : video ? (
        <div className="space-y-6">
          {/* Video preview */}
          <div className="flex flex-col md:flex-row gap-6">
            {/* Video player or thumbnail */}
            <div className="w-full md:w-1/2">
              {video.video_url ? (
                <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                  <video
                    src={video.video_url}
                    poster={video.cover_url}
                    controls
                    className="w-full h-full"
                  />
                </div>
              ) : video.cover_url ? (
                <img
                  src={video.cover_url}
                  alt={video.title}
                  className="w-full rounded-lg"
                />
              ) : (
                <div className="w-full aspect-video bg-white/5 rounded-lg flex items-center justify-center">
                  <Play className="w-12 h-12 text-gray-500" />
                </div>
              )}
            </div>

            {/* Info panel */}
            <div className="w-full md:w-1/2 space-y-4">
              <h3 className="text-lg font-semibold">
                {video.title || 'Untitled'}
              </h3>

              {video.original_title && video.original_title !== video.title && (
                <p className="text-sm text-gray-400">
                  {video.original_title}
                </p>
              )}

              {/* Status badges */}
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={video.status} />
                {video.transcription_status !== 'not_transcribed' && (
                  <StatusBadge status={video.transcription_status} />
                )}
                {video.ai_processing_status !== 'not_processed' && (
                  <StatusBadge status={video.ai_processing_status} />
                )}
                {video.transcript_hindi && (
                  <span className="px-2 py-1 text-xs bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/30">
                    🇮🇳 Hindi Available
                  </span>
                )}
              </div>

              {/* Meta info */}
              <div className="text-sm text-gray-400 space-y-1">
                <p>Created: {formatDate(video.created_at)}</p>
                <p>Method: {video.extraction_method || '-'}</p>
                {video.is_downloaded && (
                  <p className="text-green-400">✓ Downloaded locally</p>
                )}
              </div>

              {/* Progress Indicators */}
              {processingState && (
                <div className="mb-3">
                  {processingState.type === 'download' && (
                    <VideoProgressIndicator label="Downloading video..." progress={progress} />
                  )}
                  {processingState.type === 'transcribe' && (
                    <VideoProgressIndicator label="Transcribing audio..." progress={progress} />
                  )}
                  {processingState.type === 'processAI' && (
                    <VideoProgressIndicator label="Processing with AI..." progress={progress} />
                  )}
                </div>
              )}

              {/* Action buttons - Organized */}
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  {!video.is_downloaded && video.status === 'success' && (
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={Download}
                      onClick={() => downloadMutation.mutate()}
                      loading={!!processingState && processingState.type === 'download'}
                      disabled={!!processingState && processingState.type === 'download'}
                    >
                      {processingState?.type === 'download' ? 'Downloading...' : 'Download'}
                    </Button>
                  )}

                  {(video.transcription_status === 'not_transcribed' || video.transcription_status === 'failed') && (
                    <Button
                      size="sm"
                      variant={video.transcription_status === 'failed' ? 'danger' : 'secondary'}
                      icon={FileText}
                      onClick={() => transcribeMutation.mutate()}
                      loading={!!processingState && processingState.type === 'transcribe'}
                      disabled={!!processingState && processingState.type === 'transcribe'}
                    >
                      {video.transcription_status === 'failed' ? 'Retry Transcribe' : 'Transcribe'}
                    </Button>
                  )}

                  {(video.ai_processing_status === 'not_processed' || video.ai_processing_status === 'failed') && (
                    <Button
                      size="sm"
                      variant={video.ai_processing_status === 'failed' ? 'danger' : 'primary'}
                      icon={Brain}
                      onClick={() => processAIMutation.mutate()}
                      loading={!!processingState && processingState.type === 'processAI'}
                      disabled={!!processingState && processingState.type === 'processAI'}
                      className="col-span-2"
                    >
                      {video.ai_processing_status === 'failed' ? 'Retry AI Summary' : 'Generate AI Summary'}
                    </Button>
                  )}
                </div>

                <a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg btn-secondary w-full justify-center"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Original
                </a>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-white/10">
            <div className="flex gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === tab.id
                    ? 'bg-white/10 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab content */}
          <div className="min-h-[200px]">
            {activeTab === 'info' && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Description</h4>
                  <p className="text-sm">
                    {video.description || 'No description available'}
                  </p>
                </div>
                {video.original_description && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Original Description</h4>
                    <p className="text-sm text-gray-400">
                      {video.original_description}
                    </p>
                  </div>
                )}
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Original URL</h4>
                  <div className="flex items-center gap-2 p-3 bg-white/5 rounded-lg group">
                    <p className="text-sm text-gray-300 truncate flex-1 font-mono">
                      {video.url}
                    </p>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={Copy}
                      onClick={() => copyToClipboard(video.url)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      Copy
                    </Button>
                    <a
                      href={video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-400 hover:text-white transition-colors"
                      title="Open in new tab"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'transcript' && (
              <div className="space-y-4">
                {video.transcript ? (
                  <>
                    {/* Transcript and Hindi Translation Grid */}
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Original Transcript */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-gray-300">
                            Original Transcript
                          </h4>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">
                              {video.transcript_language || 'Unknown'}
                            </span>
                            <Button
                              size="sm"
                              variant="ghost"
                              icon={Copy}
                              onClick={() => copyToClipboard(video.transcript)}
                            >
                              Copy
                            </Button>
                          </div>
                        </div>
                        <div className="p-4 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">{video.transcript}</p>
                        </div>
                      </div>

                      {/* Hindi Translation */}
                      {video.transcript_hindi ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium text-purple-300 flex items-center gap-2">
                              <Globe className="w-4 h-4" />
                              Hindi Translation
                            </h4>
                            <Button
                              size="sm"
                              variant="ghost"
                              icon={Copy}
                              onClick={() => copyToClipboard(video.transcript_hindi)}
                            >
                              Copy
                            </Button>
                          </div>
                          <div className="p-4 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
                            <p className="text-sm whitespace-pre-wrap leading-relaxed">{video.transcript_hindi}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center p-8 bg-white/5 rounded-lg border border-white/10">
                          <div className="text-center text-gray-400">
                            <Globe className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">Hindi translation not available</p>
                            <p className="text-xs mt-1">Translation happens automatically after transcription</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No transcript available</p>
                    {video.transcription_status === 'not_transcribed' && (
                      <Button
                        size="sm"
                        variant="primary"
                        className="mt-4"
                        onClick={() => transcribeMutation.mutate()}
                        loading={transcribeMutation.isPending}
                      >
                        Start Transcription
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'ai' && (
              <div className="space-y-4">
                {video.ai_summary ? (
                  <>
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-2">Summary</h4>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-sm">{video.ai_summary}</p>
                      </div>
                    </div>
                    {video.ai_tags && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-400 mb-2">Tags</h4>
                        <div className="flex flex-wrap gap-2">
                          {video.ai_tags.split(',').map((tag, i) => (
                            <span
                              key={i}
                              className="px-2 py-1 text-xs bg-white/10 rounded"
                            >
                              {tag.trim()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No AI summary available</p>
                    {video.ai_processing_status === 'not_processed' && (
                      <Button
                        size="sm"
                        variant="primary"
                        className="mt-4"
                        onClick={() => processAIMutation.mutate()}
                        loading={processAIMutation.isPending}
                      >
                        Process with AI
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}


          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          Video not found
        </div>
      )}
    </Modal>
  );
}

export default VideoDetailModal;
