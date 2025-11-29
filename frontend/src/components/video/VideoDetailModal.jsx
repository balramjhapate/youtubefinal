import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { showSuccess, showError, showWarning, showInfo, showConfirm } from '../../utils/alerts';
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
      showSuccess('Download Started', 'Video download has been started.', { timer: 3000 });
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      showError('Download Failed', error?.response?.data?.error || 'Download failed. Please try again.');
    },
  });

  const transcribeMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'transcribe');
      return videosApi.transcribe(selectedVideoId);
    },
    onSuccess: () => {
      showSuccess('Processing Started', 'Video processing has been started.', { timer: 3000 });
      // Invalidate and refetch to get updated status
      queryClient.invalidateQueries(['video', selectedVideoId]);
      queryClient.invalidateQueries(['videos']);
      // Start polling for updates
      let pollCount = 0;
      const pollInterval = setInterval(() => {
        pollCount++;
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
              showSuccess('Processing Completed', 'Video processing completed successfully!', { timer: 5000 });
            }
          } else if (data) {
            // Show progress updates for long-running processes
            if (pollCount % 30 === 0 && data.transcription_status === 'transcribing') {
              const elapsed = data.elapsed_seconds || 0;
              showInfo('Transcription in Progress', `Transcription in progress... (${Math.floor(elapsed / 60)}m ${elapsed % 60}s)`, { timer: 3000 });
            }
          }
        }).catch((err) => {
          // If refetch fails, don't stop polling immediately - might be temporary network issue
          console.warn('Polling error:', err);
        });
      }, 2000);
      
      // Increased timeout to 30 minutes for large videos
      setTimeout(() => {
        clearInterval(pollInterval);
        // Check final status before showing timeout message
        refetch().then(({ data }) => {
          if (data && data.transcription_status === 'transcribing') {
            showWarning('Processing Taking Longer', 'Processing is taking longer than expected. It may still be running in the background. Please check back later.', { timer: 10000 });
          }
        });
      }, 30 * 60 * 1000); // 30 minutes
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      const errorMsg = error?.response?.data?.error || error?.message || 'Processing failed';
      // Provide more helpful error messages
      if (errorMsg.includes('timeout') || errorMsg.includes('timed out')) {
        showError('Processing Timeout', 'Processing timed out. The video may be too long. Please try again or use a shorter video.');
      } else if (errorMsg.includes('already_processing')) {
        showInfo('Processing in Progress', 'Processing is already in progress. Please wait for it to complete.', { timer: 3000 });
      } else {
        showError('Processing Failed', `Processing failed: ${errorMsg}`);
      }
    },
  });

  const processAIMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'processAI');
      return videosApi.processAI(selectedVideoId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['video', selectedVideoId]);
      showSuccess('AI Processing Started', 'AI processing has been started.', { timer: 3000 });
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      showError('AI Processing Failed', error?.response?.data?.error || 'AI processing failed. Please try again.');
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => {
      startProcessing(selectedVideoId, 'transcribe');
      return videosApi.reprocess(selectedVideoId);
    },
    onSuccess: () => {
      showSuccess('Reprocessing Started', 'Video reprocessing has been started in the background.', { timer: 3000 });
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
              showSuccess('Reprocessing Completed', 'Video reprocessing completed successfully!', { timer: 5000 });
            }
          }
        });
      }, 2000);
      
      // Clear interval after 5 minutes to prevent infinite polling
      setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
    },
    onError: (error) => {
      completeProcessing(selectedVideoId);
      showError('Reprocessing Failed', error?.response?.data?.error || 'Reprocessing failed. Please try again.');
    },
  });



  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showSuccess('Copied', 'Text copied to clipboard.', { timer: 2000 });
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
            </div>
          </div>

          {/* Processing Checklist and TTS Parameters - Below video */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Checklist */}
              <div>
                <h4 className="text-sm font-semibold text-gray-300 mb-3">Processing Status</h4>
                <div className="space-y-2">
                  {video.is_downloaded && (
                    <p className="text-sm text-green-400 flex items-center gap-2">
                      <span>✓</span>
                      <span>Downloaded locally</span>
                    </p>
                  )}
                  {video.script_status === 'generated' && (
                    <p className="text-sm text-indigo-400 flex items-center gap-2">
                      <span>✓</span>
                      <span>Hindi Script Generated</span>
                    </p>
                  )}
                  {video.script_status === 'generating' && (
                    <p className="text-sm text-yellow-400 animate-pulse flex items-center gap-2">
                      <span>⏳</span>
                      <span>Generating Script...</span>
                    </p>
                  )}
                  {video.synthesis_status === 'synthesized' && (
                    <p className="text-sm text-green-400 flex items-center gap-2">
                      <span>✓</span>
                      <span>TTS Audio Generated</span>
                    </p>
                  )}
                  {video.synthesis_status === 'synthesizing' && (
                    <p className="text-sm text-yellow-400 animate-pulse flex items-center gap-2">
                      <span>⏳</span>
                      <span>Generating Voice...</span>
                    </p>
                  )}
                  {video.voice_removed_video_url && (
                    <p className="text-sm text-yellow-400 flex items-center gap-2">
                      <span>✓</span>
                      <span>Voice Removed Video Ready</span>
                    </p>
                  )}
                  {video.final_processed_video_url && (
                    <p className="text-sm text-green-400 flex items-center gap-2">
                      <span>✓</span>
                      <span>Final Video with New Hindi Audio Ready</span>
                    </p>
                  )}
                </div>
              </div>

              {/* TTS Parameters */}
              <div>
                <h4 className="text-sm font-semibold text-gray-300 mb-3">TTS Parameters</h4>
                {video.tts_speed ? (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-300">
                      <span className="text-gray-400">Speed:</span> {video.tts_speed}x
                    </p>
                    {video.tts_temperature !== undefined && video.tts_temperature !== null && (
                      <p className="text-sm text-gray-300">
                        <span className="text-gray-400">Temperature:</span> {video.tts_temperature}
                      </p>
                    )}
                    {video.tts_repetition_penalty !== undefined && video.tts_repetition_penalty !== null && (
                      <p className="text-sm text-gray-300">
                        <span className="text-gray-400">Repetition Penalty:</span> {video.tts_repetition_penalty}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">TTS parameters will be shown after processing</p>
                )}
                {video.tts_speed && (
                  <div className="mt-3 pt-3 border-t border-white/10">
                    <p className="text-xs text-gray-400">
                      TTS Speed: {video.tts_speed}x | Temp: {video.tts_temperature || '0.75'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action buttons and Video Versions - Below video */}
          <div className="space-y-4 pt-4 border-t border-white/10">
            {/* Action buttons */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
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
                >
                  {video.ai_processing_status === 'failed' ? 'Retry AI Summary' : 'Generate AI Summary'}
                </Button>
              )}

              {/* Reprocess Button - Show when video has been transcribed (allows reprocessing at any stage) */}
              {(video.transcription_status === 'transcribed' || 
                video.transcription_status === 'failed' ||
                video.script_status === 'generated' || 
                video.script_status === 'failed' ||
                video.synthesis_status === 'synthesized' ||
                video.synthesis_status === 'failed' ||
                video.final_processed_video_url) && (
                <Button
                  size="sm"
                  variant="secondary"
                  icon={RefreshCw}
                  onClick={async () => {
                    const result = await showConfirm(
                      'Reprocess Video',
                      'Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.',
                      {
                        confirmText: 'Yes, Reprocess',
                        cancelText: 'Cancel',
                      }
                    );
                    if (result.isConfirmed) {
                      reprocessMutation.mutate();
                    }
                  }}
                  loading={!!processingState && processingState.type === 'transcribe'}
                  disabled={!!processingState && processingState.type === 'transcribe'}
                >
                  {processingState?.type === 'transcribe' ? 'Reprocessing...' : 'Reprocess Video'}
                </Button>
              )}
            </div>

            {/* Video Versions */}
            <div className="space-y-2">
              <div className="text-sm font-semibold text-gray-300 mb-3">Video Versions:</div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Downloaded Video (original with audio) */}
                {(video.local_file_url || video.video_url) && (
                  <a
                    href={video.local_file_url || video.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border border-blue-500/30 w-full justify-center transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="text-center">Downloaded Video (Original with Audio)</span>
                  </a>
                )}
                
                {/* 2. Voice Removed Video (no audio) */}
                {video.voice_removed_video_url && (
                  <a
                    href={video.voice_removed_video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30 border border-yellow-500/30 w-full justify-center transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="text-center">Voice Removed Video (No Audio)</span>
                  </a>
                )}
                
                {/* 2b. Synthesized TTS Audio (Hindi) */}
                {video.synthesized_audio_url && (
                  <a
                    href={video.synthesized_audio_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 w-full justify-center transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="text-center">🎵 Synthesized TTS Audio (Hindi)</span>
                  </a>
                )}
                
                {/* 3. Final Processed Video (with new Hindi audio) */}
                {video.final_processed_video_url && (
                  <a
                    href={video.final_processed_video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 w-full justify-center transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="text-center">Final Processed Video (with New Hindi Audio)</span>
                  </a>
                )}
              </div>
              
              {/* Show processing status if videos are not ready yet */}
              {video.synthesis_status === 'synthesized' && !video.voice_removed_video_url && !video.final_processed_video_url && (
                <div className="text-xs text-yellow-400 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
                  ⏳ Processing video files... (This may take a few moments)
                </div>
              )}
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

          {/* Additional Info Section - Between video and tabs */}
          <div className="grid md:grid-cols-3 gap-4 pt-4 border-t border-white/10">
            {/* Processing Statistics */}
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">Processing Status</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Download</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${video.is_downloaded ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20 text-gray-400'}`}>
                    {video.is_downloaded ? '✓ Complete' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Transcription</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    video.transcription_status === 'transcribed' ? 'bg-green-500/20 text-green-300' :
                    video.transcription_status === 'transcribing' ? 'bg-yellow-500/20 text-yellow-300' :
                    video.transcription_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {video.transcription_status === 'transcribed' ? '✓ Complete' :
                     video.transcription_status === 'transcribing' ? '⏳ Processing' :
                     video.transcription_status === 'failed' ? '✗ Failed' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">AI Processing</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    video.ai_processing_status === 'processed' ? 'bg-green-500/20 text-green-300' :
                    video.ai_processing_status === 'processing' ? 'bg-yellow-500/20 text-yellow-300' :
                    video.ai_processing_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {video.ai_processing_status === 'processed' ? '✓ Complete' :
                     video.ai_processing_status === 'processing' ? '⏳ Processing' :
                     video.ai_processing_status === 'failed' ? '✗ Failed' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Script Generation</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    video.script_status === 'generated' ? 'bg-green-500/20 text-green-300' :
                    video.script_status === 'generating' ? 'bg-yellow-500/20 text-yellow-300' :
                    video.script_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {video.script_status === 'generated' ? '✓ Complete' :
                     video.script_status === 'generating' ? '⏳ Processing' :
                     video.script_status === 'failed' ? '✗ Failed' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">TTS Synthesis</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    video.synthesis_status === 'synthesized' ? 'bg-green-500/20 text-green-300' :
                    video.synthesis_status === 'synthesizing' ? 'bg-yellow-500/20 text-yellow-300' :
                    video.synthesis_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {video.synthesis_status === 'synthesized' ? '✓ Complete' :
                     video.synthesis_status === 'synthesizing' ? '⏳ Processing' :
                     video.synthesis_status === 'failed' ? '✗ Failed' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Final Video</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${video.final_processed_video_url ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20 text-gray-400'}`}>
                    {video.final_processed_video_url ? '✓ Ready' : 'Pending'}
                  </span>
                </div>
              </div>
            </div>

            {/* Video Metadata */}
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">Video Information</h4>
              <div className="space-y-2">
                {video.duration && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Duration</span>
                    <span className="text-xs text-gray-300 font-mono">{formatDuration(video.duration)}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Source</span>
                  <span className="text-xs text-gray-300">
                    {video.video_source ? (video.video_source === 'rednote' ? 'RedNote' : 
                     video.video_source === 'youtube' ? 'YouTube' :
                     video.video_source === 'facebook' ? 'Facebook' :
                     video.video_source === 'instagram' ? 'Instagram' :
                     video.video_source === 'vimeo' ? 'Vimeo' :
                     video.video_source === 'local' ? 'Local' :
                     video.video_source) : '-'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Method</span>
                  <span className="text-xs text-gray-300">{video.extraction_method || '-'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Language</span>
                  <span className="text-xs text-gray-300">{video.transcript_language || 'Unknown'}</span>
                </div>
                {video.video_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Video ID</span>
                    <span className="text-xs text-gray-300 font-mono truncate max-w-[120px]" title={video.video_id}>
                      {video.video_id}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Created</span>
                  <span className="text-xs text-gray-300">{formatDate(video.created_at)}</span>
                </div>
              </div>
            </div>

            {/* TTS Parameters & Settings */}
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">TTS Settings</h4>
              <div className="space-y-2">
                {video.tts_speed ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Speed</span>
                    <span className="text-xs text-gray-300 font-mono">{video.tts_speed}x</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Speed</span>
                    <span className="text-xs text-gray-500">Default (1.0x)</span>
                  </div>
                )}
                {video.tts_temperature !== undefined && video.tts_temperature !== null ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Temperature</span>
                    <span className="text-xs text-gray-300 font-mono">{video.tts_temperature}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Temperature</span>
                    <span className="text-xs text-gray-500">Default (0.75)</span>
                  </div>
                )}
                {video.tts_repetition_penalty !== undefined && video.tts_repetition_penalty !== null ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Repetition Penalty</span>
                    <span className="text-xs text-gray-300 font-mono">{video.tts_repetition_penalty}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Repetition Penalty</span>
                    <span className="text-xs text-gray-500">Default (5.0)</span>
                  </div>
                )}
                {video.voice_profile ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Voice Profile</span>
                    <span className="text-xs text-green-300">✓ Assigned</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Voice Profile</span>
                    <span className="text-xs text-gray-500">Default</span>
                  </div>
                )}
                {video.transcript_hindi && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Hindi Translation</span>
                    <span className="text-xs text-purple-300">✓ Available</span>
                  </div>
                )}
                {video.hindi_script && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Hindi Script</span>
                    <span className="text-xs text-indigo-300">✓ Generated</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tab content */}
          <div className="min-h-[300px]">
            {activeTab === 'info' && (
              <div className="space-y-6">
                {/* Description Section */}
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Description
                  </h4>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    {video.description || <span className="text-gray-500 italic">No description available</span>}
                  </p>
                </div>

                {/* Original Description */}
                {video.original_description && (
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Original Description
                    </h4>
                    <p className="text-sm text-gray-400 leading-relaxed">
                      {video.original_description}
                    </p>
                  </div>
                )}

                {/* Processing Timeline */}
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Processing Timeline
                  </h4>
                  <div className="space-y-3">
                    {video.created_at && (
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-gray-300">Video Added</p>
                          <p className="text-xs text-gray-500">{formatDate(video.created_at)}</p>
                        </div>
                      </div>
                    )}
                    {video.transcript_processed_at && (
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-green-400 mt-1.5"></div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-gray-300">Transcription Completed</p>
                          <p className="text-xs text-gray-500">{formatDate(video.transcript_processed_at)}</p>
                        </div>
                      </div>
                    )}
                    {video.script_generated_at && (
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5"></div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-gray-300">Hindi Script Generated</p>
                          <p className="text-xs text-gray-500">{formatDate(video.script_generated_at)}</p>
                        </div>
                      </div>
                    )}
                    {video.synthesized_at && (
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-purple-400 mt-1.5"></div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-gray-300">TTS Audio Synthesized</p>
                          <p className="text-xs text-gray-500">{formatDate(video.synthesized_at)}</p>
                        </div>
                      </div>
                    )}
                    {video.final_processed_video_url && (
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-gray-300">Final Video Ready</p>
                          <p className="text-xs text-gray-500">Processing complete</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Original URL */}
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <ExternalLink className="w-4 h-4" />
                    Original URL
                  </h4>
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

                {/* File Information */}
                {(video.local_file_url || video.voice_removed_video_url || video.final_processed_video_url || video.synthesized_audio_url) && (
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                      <Download className="w-4 h-4" />
                      Generated Files
                    </h4>
                    <div className="grid grid-cols-2 gap-2">
                      {video.local_file_url && (
                        <div className="text-xs">
                          <span className="text-gray-400">Original:</span>
                          <span className="text-green-300 ml-1">✓ Available</span>
                        </div>
                      )}
                      {video.voice_removed_video_url && (
                        <div className="text-xs">
                          <span className="text-gray-400">Voice Removed:</span>
                          <span className="text-yellow-300 ml-1">✓ Available</span>
                        </div>
                      )}
                      {video.synthesized_audio_url && (
                        <div className="text-xs">
                          <span className="text-gray-400">TTS Audio:</span>
                          <span className="text-purple-300 ml-1">✓ Available</span>
                        </div>
                      )}
                      {video.final_processed_video_url && (
                        <div className="text-xs">
                          <span className="text-gray-400">Final Video:</span>
                          <span className="text-green-300 ml-1">✓ Available</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
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
