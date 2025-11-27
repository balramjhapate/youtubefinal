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
  RefreshCw,
} from 'lucide-react';
import { Modal, Button, StatusBadge, AudioPlayer, LoadingSpinner, Select } from '../common';
import { VideoProgressIndicator } from './VideoProgressIndicator';
import { videosApi } from '../../api';
import { formatDate, truncateText, formatDuration } from '../../utils/formatters';
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
  const { data: video, isLoading, refetch } = useQuery({
    queryKey: ['video', selectedVideoId],
    queryFn: () => videosApi.getById(selectedVideoId),
    enabled: !!selectedVideoId,
    refetchInterval: (query) => {
      // Auto-refetch if video is being processed
      const video = query.state.data;
      if (video && (
        video.transcription_status === 'transcribing' ||
        video.ai_processing_status === 'processing' ||
        video.script_status === 'generating' ||
        video.synthesis_status === 'synthesizing' ||
        (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
      )) {
        return 2000; // Refetch every 2 seconds during processing
      }
      return false; // Don't auto-refetch when not processing
    },
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
      queryClient.invalidateQueries(['video', selectedVideoId]);
      queryClient.invalidateQueries(['videos']);
      toast.success('Download started');
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
      toast.success('Processing started');
      // Invalidate and refetch to get updated status
      queryClient.invalidateQueries(['video', selectedVideoId]);
      queryClient.invalidateQueries(['videos']);
      // Start polling for updates
      const pollInterval = setInterval(() => {
        refetch().then(({ data }) => {
          // Stop polling when processing is complete
          if (data && 
              data.transcription_status !== 'transcribing' &&
              data.ai_processing_status !== 'processing' &&
              data.script_status !== 'generating' &&
              data.synthesis_status !== 'synthesizing' &&
              (data.synthesis_status !== 'synthesized' || data.final_processed_video_url)) {
            clearInterval(pollInterval);
            completeProcessing(selectedVideoId);
            if (data.final_processed_video_url) {
              toast.success('Video processing completed!');
            }
          }
        });
      }, 2000);
      
      // Clear interval after 5 minutes to prevent infinite polling
      setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'Processing failed');
    },
  });

  const processAIMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'processAI');
      return videosApi.processAI(selectedVideoId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['video', selectedVideoId]);
      toast.success('AI processing started');
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'AI processing failed');
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'transcribe');
      return videosApi.reprocess(selectedVideoId);
    },
    onSuccess: () => {
      toast.success('Video reprocessing started');
      queryClient.invalidateQueries(['video', selectedVideoId]);
      queryClient.invalidateQueries(['videos']);
      // Start polling for updates
      const pollInterval = setInterval(() => {
        refetch().then(({ data }) => {
          // Stop polling when processing is complete
          if (data && 
              data.transcription_status !== 'transcribing' &&
              data.ai_processing_status !== 'processing' &&
              data.script_status !== 'generating' &&
              data.synthesis_status !== 'synthesizing' &&
              (data.synthesis_status !== 'synthesized' || data.final_processed_video_url)) {
            clearInterval(pollInterval);
            completeProcessing(selectedVideoId);
            if (data.final_processed_video_url) {
              toast.success('Video reprocessing completed!');
            }
          }
        });
      }, 2000);
      
      // Clear interval after 5 minutes to prevent infinite polling
      setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      toast.error(error?.response?.data?.error || 'Reprocessing failed');
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
    { id: 'script', label: 'Hindi Script' },
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
              {/* Show final processed video if available, otherwise show downloaded video, otherwise show original */}
              {(video.final_processed_video_url || video.local_file_url || video.video_url) ? (
                <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                  <video
                    src={video.final_processed_video_url || video.local_file_url || video.video_url}
                    poster={video.cover_url}
                    controls
                    className="w-full h-full"
                  />
                  {video.final_processed_video_url && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-green-500/80 text-white text-xs rounded">
                      ✓ Final Video (with new Hindi audio)
                    </div>
                  )}
                  {!video.final_processed_video_url && video.local_file_url && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-blue-500/80 text-white text-xs rounded">
                      ✓ Downloaded Video (original audio)
                    </div>
                  )}
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
                <p>Source: {video.video_source ? (video.video_source === 'rednote' ? 'RedNote' : 
                   video.video_source === 'youtube' ? 'YouTube' :
                   video.video_source === 'facebook' ? 'Facebook' :
                   video.video_source === 'instagram' ? 'Instagram' :
                   video.video_source === 'vimeo' ? 'Vimeo' :
                   video.video_source === 'local' ? 'Local' :
                   video.video_source) : '-'}</p>
                <p>Method: {video.extraction_method || '-'}</p>
                {video.duration && (
                  <p>Duration: {formatDuration(video.duration)}</p>
                )}
                {video.is_downloaded && (
                  <p className="text-green-400">✓ Downloaded locally</p>
                )}
                {video.script_status === 'generated' && (
                  <p className="text-indigo-400">✓ Hindi Script Generated</p>
                )}
                {video.script_status === 'generating' && (
                  <p className="text-yellow-400 animate-pulse">⏳ Generating Script...</p>
                )}
                {video.synthesis_status === 'synthesized' && (
                  <p className="text-green-400">✓ TTS Audio Generated</p>
                )}
                {video.synthesis_status === 'synthesizing' && (
                  <p className="text-yellow-400 animate-pulse">⏳ Generating Voice...</p>
                )}
                {video.voice_removed_video_url && (
                  <p className="text-yellow-400">✓ Voice Removed Video Ready</p>
                )}
                {video.final_processed_video_url && (
                  <p className="text-green-400">✓ Final Video with New Hindi Audio Ready</p>
                )}
                {video.tts_speed && (
                  <p className="text-xs">TTS Speed: {video.tts_speed}x | Temp: {video.tts_temperature}</p>
                )}
              </div>

              {/* Progress Indicators */}
              {processingState && (
                <div className="mb-3">
                  {processingState.type === 'download' && (
                    <VideoProgressIndicator label="Downloading video..." progress={progress} />
                  )}
                  {processingState.type === 'transcribe' && (
                    <>
                      <VideoProgressIndicator 
                        label={video.transcription_status === 'transcribing' ? "Transcribing..." : "Transcribed ✓"} 
                        progress={video.transcription_status === 'transcribing' ? progress : 100} 
                      />
                      {video.transcription_status === 'transcribed' && video.ai_processing_status === 'processing' && (
                        <VideoProgressIndicator label="AI Processing..." progress={progress} />
                      )}
                      {video.ai_processing_status === 'processed' && video.script_status === 'generating' && (
                        <VideoProgressIndicator label="Scripting..." progress={progress} />
                      )}
                      {video.script_status === 'generated' && video.synthesis_status === 'synthesizing' && (
                        <VideoProgressIndicator label="Generating Voice..." progress={progress} />
                      )}
                      {video.synthesis_status === 'synthesized' && !video.final_processed_video_url && (
                        <VideoProgressIndicator label="Removing Audio & Combining..." progress={progress} />
                      )}
                    </>
                  )}
                  {processingState.type === 'processAI' && (
                    <VideoProgressIndicator label="Processing with AI..." progress={progress} />
                  )}
                  {video.script_status === 'generating' && !processingState && (
                    <VideoProgressIndicator label="Generating Hindi script..." progress={progress} />
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
                      {video.transcription_status === 'failed' ? 'Retry Process' : 'Process Video'}
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

                  {/* Reprocess Button - Show when final video is ready */}
                  {video.final_processed_video_url && (
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={RefreshCw}
                      onClick={() => {
                        if (window.confirm('Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.')) {
                          reprocessMutation.mutate();
                        }
                      }}
                      loading={!!processingState && processingState.type === 'transcribe'}
                      disabled={!!processingState && processingState.type === 'transcribe'}
                      className="col-span-2"
                    >
                      {processingState?.type === 'transcribe' ? 'Reprocessing...' : 'Reprocess Video'}
                    </Button>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="text-xs text-gray-400 mb-2 font-semibold">Video Versions:</div>
                  
                  {/* 1. Downloaded Video (original with audio) */}
                  {(video.local_file_url || video.video_url) && (
                    <a
                      href={video.local_file_url || video.video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border border-blue-500/30 w-full justify-center"
                    >
                      <ExternalLink className="w-4 h-4" />
                      1. Downloaded Video (Original with Audio)
                    </a>
                  )}
                  
                  {/* 2. Voice Removed Video (no audio) */}
                  {video.voice_removed_video_url && (
                    <a
                      href={video.voice_removed_video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30 border border-yellow-500/30 w-full justify-center"
                    >
                      <ExternalLink className="w-4 h-4" />
                      2. Voice Removed Video (No Audio)
                    </a>
                  )}
                  
                  {/* 3. Final Processed Video (with new Hindi audio) */}
                  {video.final_processed_video_url && (
                    <>
                      <a
                        href={video.final_processed_video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 w-full justify-center"
                      >
                        <ExternalLink className="w-4 h-4" />
                        3. Final Processed Video (with New Hindi Audio)
                      </a>
                      
                      {/* Reprocess Button - Show immediately after final video is ready */}
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={RefreshCw}
                        onClick={() => {
                          if (window.confirm('Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.')) {
                            reprocessMutation.mutate();
                          }
                        }}
                        loading={!!processingState && processingState.type === 'transcribe'}
                        disabled={!!processingState && processingState.type === 'transcribe'}
                        className="w-full"
                      >
                        {processingState?.type === 'transcribe' ? 'Reprocessing...' : 'Reprocess Video'}
                      </Button>
                    </>
                  )}
                  
                  {/* Show processing status if videos are not ready yet */}
                  {video.synthesis_status === 'synthesized' && !video.voice_removed_video_url && !video.final_processed_video_url && (
                    <div className="text-xs text-yellow-400 p-2 bg-yellow-500/10 rounded border border-yellow-500/30">
                      ⏳ Processing video files... (This may take a few moments)
                    </div>
                  )}
                </div>
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
                    {/* Transcript with and without timestamps */}
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Original Transcript WITH timestamps */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-gray-300">
                            Original Transcript with Timestamps ({video.transcript_language || 'Unknown'})
                          </h4>
                          <Button
                            size="sm"
                            variant="ghost"
                            icon={Copy}
                            onClick={() => copyToClipboard(video.transcript)}
                          >
                            Copy
                          </Button>
                        </div>
                        <div className="p-4 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
                          <p className="text-sm whitespace-pre-wrap leading-relaxed font-mono">{video.transcript}</p>
                        </div>
                      </div>

                      {/* Original Transcript WITHOUT timestamps */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-blue-300">
                            Original Transcript (Plain Text)
                          </h4>
                          <Button
                            size="sm"
                            variant="ghost"
                            icon={Copy}
                            onClick={() => copyToClipboard(video.transcript_without_timestamps || video.transcript)}
                          >
                            Copy
                          </Button>
                        </div>
                        <div className="p-4 bg-blue-500/5 rounded-lg max-h-96 overflow-y-auto border border-blue-500/20">
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">
                            {video.transcript_without_timestamps || video.transcript}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Hindi Translation */}
                    {video.transcript_hindi && (
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
                    )}
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

            {activeTab === 'script' && (
              <div className="space-y-4">
                {video.hindi_script ? (
                  <>
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-400 mb-1">Hindi Script for TTS</h4>
                      {video.script_generated_at && (
                        <p className="text-xs text-gray-500">
                          Generated: {formatDate(video.script_generated_at)}
                        </p>
                      )}
                      {video.duration && (
                        <p className="text-xs text-gray-500">
                          Video Duration: {formatDuration(video.duration)}
                        </p>
                      )}
                      {video.tts_speed && (
                        <p className="text-xs text-gray-500">
                          TTS Parameters: Speed {video.tts_speed}x | Temperature {video.tts_temperature} | Repetition Penalty {video.tts_repetition_penalty}
                        </p>
                      )}
                    </div>
                    
                    {/* Script with timestamps and without timestamps */}
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Script WITH timestamps */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-gray-300">
                            Script with Timestamps
                          </h4>
                          <Button
                            size="sm"
                            variant="ghost"
                            icon={Copy}
                            onClick={() => copyToClipboard(video.hindi_script)}
                          >
                            Copy
                          </Button>
                        </div>
                        <div className="p-4 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
                          <p className="text-sm whitespace-pre-wrap leading-relaxed font-mono">
                            {video.hindi_script}
                          </p>
                        </div>
                      </div>

                      {/* Script WITHOUT timestamps (clean for TTS) */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-green-300">
                            Clean Script (for TTS)
                          </h4>
                          <Button
                            size="sm"
                            variant="ghost"
                            icon={Copy}
                            onClick={() => copyToClipboard(video.clean_script_for_tts || video.hindi_script)}
                          >
                            Copy
                          </Button>
                        </div>
                        <div className="p-4 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">
                            {video.clean_script_for_tts || video.hindi_script}
                          </p>
                        </div>
                      </div>
                    </div>
                  </>
                ) : video.script_status === 'generating' ? (
                  <div className="text-center py-8 text-gray-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50 animate-pulse" />
                    <p>Generating Hindi script...</p>
                    <p className="text-xs mt-2">This may take a few moments</p>
                  </div>
                ) : video.script_status === 'failed' ? (
                  <div className="text-center py-8 text-red-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Script generation failed</p>
                    {video.script_error_message && (
                      <p className="text-xs mt-2 text-gray-400">{video.script_error_message}</p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No script available</p>
                    <p className="text-xs mt-2">Script will be automatically generated after video download</p>
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
