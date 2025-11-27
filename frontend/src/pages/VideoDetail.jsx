import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  ArrowLeft,
} from 'lucide-react';
import { Button, StatusBadge, AudioPlayer, LoadingSpinner } from '../components/common';
import { VideoProgressIndicator } from '../components/video/VideoProgressIndicator';
import { videosApi } from '../api';
import { formatDate, truncateText, formatDuration } from '../utils/formatters';
import { useStore } from '../store';

export function VideoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const {
    startProcessing,
    completeProcessing,
    getProcessingState,
  } = useStore();

  const [activeTab, setActiveTab] = useState('info');
  const [progress, setProgress] = useState(0);
  
  // Fetch video details with real-time polling during processing
  const { data: video, isLoading, refetch } = useQuery({
    queryKey: ['video', id],
    queryFn: () => videosApi.getById(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const video = query.state.data;
      if (video && (
        video.transcription_status === 'transcribing' ||
        video.ai_processing_status === 'processing' ||
        video.script_status === 'generating' ||
        video.synthesis_status === 'synthesizing' ||
        (video.synthesis_status === 'synthesized' && !video.final_processed_video_url) ||
        // Also poll if we have a processing state (reprocessing)
        (processingState && processingState.type)
      )) {
        return 2000; // Poll every 2 seconds during processing
      }
      return false;
    },
  });
  
  const processingState = id ? getProcessingState(id) : null;

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
          completeProcessing(id);
          setProgress(0);
        }, 1000);
      }
    }
  }, [video, processingState, id, completeProcessing]);

  // Mutations
  const downloadMutation = useMutation({
    mutationFn: async () => {
      startProcessing(id, 'download');
      return videosApi.download(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['video', id]);
      queryClient.invalidateQueries(['videos']);
      toast.success('Download started');
    },
    onError: (error) => {
      completeProcessing(id);
      toast.error(error?.response?.data?.error || 'Download failed');
    },
  });

  const transcribeMutation = useMutation({
    mutationFn: () => {
      startProcessing(id, 'transcribe');
      return videosApi.transcribe(id);
    },
    onSuccess: () => {
      toast.success('Processing started');
      const pollInterval = setInterval(() => {
        refetch().then(({ data }) => {
          if (data && 
              data.transcription_status !== 'transcribing' &&
              data.ai_processing_status !== 'processing' &&
              data.script_status !== 'generating' &&
              data.synthesis_status !== 'synthesizing' &&
              (data.synthesis_status !== 'synthesized' || data.final_processed_video_url)) {
            clearInterval(pollInterval);
            completeProcessing(id);
            if (data.final_processed_video_url) {
              toast.success('Video processing completed!');
            }
          }
        });
      }, 2000);
      setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
    },
    onError: (error) => {
      completeProcessing(id);
      toast.error(error?.response?.data?.error || 'Processing failed');
    },
  });

  const processAIMutation = useMutation({
    mutationFn: () => {
      startProcessing(id, 'processAI');
      return videosApi.processAI(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['video', id]);
      toast.success('AI processing started');
    },
    onError: (error) => {
      completeProcessing(id);
      toast.error(error?.response?.data?.error || 'AI processing failed');
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => {
      startProcessing(id, 'reprocess');
      return videosApi.reprocess(id);
    },
    onSuccess: () => {
      toast.success('Video reprocessing started');
      queryClient.invalidateQueries(['video', id]);
      queryClient.invalidateQueries(['videos']);
      // Start immediate refetch to get updated status
      refetch();
      
      // Set up polling to check for completion
      const pollInterval = setInterval(() => {
        refetch().then(({ data }) => {
          if (data) {
            // Check if all processing is complete
            const isProcessing = 
              data.transcription_status === 'transcribing' ||
              data.ai_processing_status === 'processing' ||
              data.script_status === 'generating' ||
              data.synthesis_status === 'synthesizing' ||
              (data.synthesis_status === 'synthesized' && !data.final_processed_video_url);
            
            if (!isProcessing) {
              clearInterval(pollInterval);
              completeProcessing(id);
              if (data.final_processed_video_url) {
                toast.success('Video reprocessing completed!');
              } else if (data.synthesis_status === 'failed') {
                toast.error('Reprocessing completed but TTS synthesis failed. Check video details.');
              }
            }
          }
        });
      }, 2000);
      
      // Clean up polling after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        completeProcessing(id);
      }, 5 * 60 * 1000);
    },
    onError: (error) => {
      completeProcessing(id);
      toast.error(error?.response?.data?.error || 'Reprocessing failed');
    },
  });

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'script', label: 'Hindi Script' },
    { id: 'ai', label: 'AI Summary' },
  ];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p>Video not found</p>
        <Button
          variant="secondary"
          icon={ArrowLeft}
          onClick={() => navigate('/videos')}
          className="mt-4"
        >
          Back to Videos
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate('/videos')}
        >
          Back
        </Button>
        <h1 className="text-2xl font-bold">Video Details</h1>
      </div>

      {/* Main content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left column - Video and main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video player */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
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

          {/* Progress Indicators */}
          {processingState && (
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
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

          {/* Actions and Video Versions - Combined in one card */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            {/* Actions Section */}
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-300 mb-4">Actions</h4>
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
                    onClick={() => {
                      if (window.confirm('Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.')) {
                        reprocessMutation.mutate();
                      }
                    }}
                    loading={
                      reprocessMutation.isPending ||
                      !!processingState ||
                      (video && (
                        video.transcription_status === 'transcribing' ||
                        video.ai_processing_status === 'processing' ||
                        video.script_status === 'generating' ||
                        video.synthesis_status === 'synthesizing' ||
                        (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
                      ))
                    }
                    disabled={
                      reprocessMutation.isPending ||
                      !!processingState ||
                      (video && (
                        video.transcription_status === 'transcribing' ||
                        video.ai_processing_status === 'processing' ||
                        video.script_status === 'generating' ||
                        video.synthesis_status === 'synthesizing' ||
                        (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
                      ))
                    }
                  >
                    {reprocessMutation.isPending || 
                     !!processingState || 
                     (video && (
                       video.transcription_status === 'transcribing' ||
                       video.ai_processing_status === 'processing' ||
                       video.script_status === 'generating' ||
                       video.synthesis_status === 'synthesizing'
                     )) 
                     ? 'Reprocessing...' 
                     : 'Reprocess Video'}
                  </Button>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-white/10 mb-6"></div>

            {/* Video Versions Section */}
            <div>
              <h4 className="text-sm font-semibold text-gray-300 mb-4">Video Versions</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
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
              
              {video.synthesis_status === 'synthesized' && !video.voice_removed_video_url && !video.final_processed_video_url && (
                <div className="text-xs text-yellow-400 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30 mt-3">
                  ⏳ Processing video files... (This may take a few moments)
                </div>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-white/5 rounded-lg border border-white/10 overflow-hidden">
            <div className="border-b border-white/10">
              <div className="flex gap-1 p-2">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${activeTab === tab.id
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
            <div className="p-6 min-h-[400px]">
              {activeTab === 'info' && (
                <div className="space-y-6">
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Description
                    </h4>
                    <p className="text-sm text-gray-300 leading-relaxed">
                      {video.description || <span className="text-gray-500 italic">No description available</span>}
                    </p>
                  </div>

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
                      {video.cloudinary_uploaded_at && (
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5"></div>
                          <div className="flex-1">
                            <p className="text-xs font-medium text-gray-300">Uploaded to Cloudinary</p>
                            <p className="text-xs text-gray-500">{formatDate(video.cloudinary_uploaded_at)}</p>
                          </div>
                        </div>
                      )}
                      {video.google_sheets_synced_at && (
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5"></div>
                          <div className="flex-1">
                            <p className="text-xs font-medium text-gray-300">Synced to Google Sheets</p>
                            <p className="text-xs text-gray-500">{formatDate(video.google_sheets_synced_at)}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

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
                <div className="space-y-6">
                  {/* Comparison Header */}
                  {(video.transcript || video.whisper_transcript) && (
                    <div className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-green-500/10 rounded-lg p-4 border border-white/10">
                      <h3 className="text-lg font-semibold text-white mb-2">📊 Transcription Comparison</h3>
                      <p className="text-sm text-gray-400">
                        Compare NCA Toolkit and Whisper AI transcriptions side-by-side to evaluate accuracy and quality.
                      </p>
                    </div>
                  )}

                  {/* Dual Transcription Comparison */}
                  {(video.transcript || video.whisper_transcript) ? (
                    <div className="grid lg:grid-cols-2 gap-6">
                      {/* NCA TOOLKIT TRANSCRIPTION */}
                      <div className="space-y-4">
                        <div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-base font-semibold text-blue-300 flex items-center gap-2">
                              🔷 NCA Toolkit
                            </h4>
                            <span className={`px-2 py-1 text-xs rounded ${
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
                          
                          {video.transcript ? (
                            <>
                              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Language:</span>
                                  <span className="text-white ml-1">{video.transcript_language || 'Unknown'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Length:</span>
                                  <span className="text-white ml-1">{video.transcript_without_timestamps?.length || video.transcript?.length || 0} chars</span>
                                </div>
                              </div>

                              {/* With Timestamps */}
                              <div className="space-y-2 mb-3">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">With Timestamps</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-white/5 rounded-lg max-h-64 overflow-y-auto border border-white/10">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
                                    {video.transcript}
                                  </p>
                                </div>
                              </div>

                              {/* Plain Text */}
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">Plain Text</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.transcript_without_timestamps || video.transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-blue-500/5 rounded-lg max-h-64 overflow-y-auto border border-blue-500/20">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
                                    {video.transcript_without_timestamps || video.transcript}
                                  </p>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="text-center py-8 text-gray-500">
                              <p className="text-sm">No NCA transcription available</p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* WHISPER AI TRANSCRIPTION */}
                      <div className="space-y-4">
                        <div className="bg-green-500/10 rounded-lg p-4 border border-green-500/30">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-base font-semibold text-green-300 flex items-center gap-2">
                              🎯 Whisper AI
                            </h4>
                            <span className={`px-2 py-1 text-xs rounded ${
                              video.whisper_transcription_status === 'transcribed' ? 'bg-green-500/20 text-green-300' :
                              video.whisper_transcription_status === 'transcribing' ? 'bg-yellow-500/20 text-yellow-300' :
                              video.whisper_transcription_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                              'bg-gray-500/20 text-gray-400'
                            }`}>
                              {video.whisper_transcription_status === 'transcribed' ? '✓ Complete' :
                               video.whisper_transcription_status === 'transcribing' ? '⏳ Processing' :
                               video.whisper_transcription_status === 'failed' ? '✗ Failed' : 'Pending'}
                            </span>
                          </div>
                          
                          {video.whisper_transcript ? (
                            <>
                              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Language:</span>
                                  <span className="text-white ml-1">{video.whisper_transcript_language || 'Unknown'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Length:</span>
                                  <span className="text-white ml-1">{video.whisper_transcript_without_timestamps?.length || video.whisper_transcript?.length || 0} chars</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Model:</span>
                                  <span className="text-white ml-1">{video.whisper_model_used || 'base'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Confidence:</span>
                                  <span className={`ml-1 ${
                                    video.whisper_confidence_avg && video.whisper_confidence_avg > -1.0 ? 'text-green-300' :
                                    video.whisper_confidence_avg && video.whisper_confidence_avg > -2.0 ? 'text-yellow-300' :
                                    'text-red-300'
                                  }`}>
                                    {video.whisper_confidence_avg ? 
                                      (video.whisper_confidence_avg > -1.0 ? 'High' :
                                       video.whisper_confidence_avg > -2.0 ? 'Medium' : 'Low') : 
                                      'N/A'}
                                  </span>
                                </div>
                              </div>

                              {/* With Timestamps */}
                              <div className="space-y-2 mb-3">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">With Timestamps</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.whisper_transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-white/5 rounded-lg max-h-64 overflow-y-auto border border-white/10">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
                                    {video.whisper_transcript}
                                  </p>
                                </div>
                              </div>

                              {/* Plain Text */}
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">Plain Text</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.whisper_transcript_without_timestamps || video.whisper_transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-green-500/5 rounded-lg max-h-64 overflow-y-auto border border-green-500/20">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
                                    {video.whisper_transcript_without_timestamps || video.whisper_transcript}
                                  </p>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="text-center py-8 text-gray-500">
                              <p className="text-sm">No Whisper transcription available</p>
                              {video.whisper_transcription_status === 'not_transcribed' && (
                                <p className="text-xs mt-2">Run dual transcription to generate</p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-400">
                      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="mb-2">No transcriptions available</p>
                      {video.transcription_status === 'not_transcribed' && (
                        <Button
                          size="sm"
                          variant="primary"
                          className="mt-4"
                          onClick={() => transcribeMutation.mutate()}
                          loading={transcribeMutation.isPending}
                        >
                          Start Dual Transcription
                        </Button>
                      )}
                    </div>
                  )}

                  {/* Hindi Translations Comparison */}
                  {(video.transcript_hindi || video.whisper_transcript_hindi) && (
                    <div className="space-y-4">
                      <h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
                        <Globe className="w-5 h-5" />
                        🌍 Hindi Translations Comparison
                      </h4>
                      
                      <div className="grid lg:grid-cols-2 gap-6">
                        {/* NCA Hindi */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-medium text-blue-300">NCA Hindi Translation</h5>
                            {video.transcript_hindi && (
                              <Button
                                size="sm"
                                variant="ghost"
                                icon={Copy}
                                onClick={() => copyToClipboard(video.transcript_hindi)}
                                className="text-xs"
                              >
                                Copy
                              </Button>
                            )}
                          </div>
                          {video.transcript_hindi ? (
                            <div className="p-4 bg-blue-500/5 rounded-lg max-h-64 overflow-y-auto border border-blue-500/20">
                              <p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
                                {video.transcript_hindi}
                              </p>
                            </div>
                          ) : (
                            <div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
                              No NCA Hindi translation
                            </div>
                          )}
                        </div>

                        {/* Whisper Hindi */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-medium text-green-300">Whisper Hindi Translation</h5>
                            {video.whisper_transcript_hindi && (
                              <Button
                                size="sm"
                                variant="ghost"
                                icon={Copy}
                                onClick={() => copyToClipboard(video.whisper_transcript_hindi)}
                                className="text-xs"
                              >
                                Copy
                              </Button>
                            )}
                          </div>
                          {video.whisper_transcript_hindi ? (
                            <div className="p-4 bg-green-500/5 rounded-lg max-h-64 overflow-y-auto border border-green-500/20">
                              <p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
                                {video.whisper_transcript_hindi}
                              </p>
                            </div>
                          ) : (
                            <div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
                              No Whisper Hindi translation
                            </div>
                          )}
                        </div>
                      </div>
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
                      
                      <div className="grid md:grid-cols-2 gap-4">
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
        </div>

        {/* Right column - Sidebar info */}
        <div className="space-y-6">
          {/* Video Info Card */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <h3 className="text-lg font-semibold mb-2">
              {video.title || 'Untitled'}
            </h3>

            {video.original_title && video.original_title !== video.title && (
              <p className="text-sm text-gray-400 mb-4">
                {video.original_title}
              </p>
            )}

            {/* Status badges */}
            <div className="flex flex-wrap gap-2 mb-4">
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
            <div className="text-sm text-gray-400 space-y-2">
              <p><span className="text-gray-500">Created:</span> {formatDate(video.created_at)}</p>
              <p><span className="text-gray-500">Source:</span> {video.video_source ? (video.video_source === 'rednote' ? 'RedNote' : 
                 video.video_source === 'youtube' ? 'YouTube' :
                 video.video_source === 'facebook' ? 'Facebook' :
                 video.video_source === 'instagram' ? 'Instagram' :
                 video.video_source === 'vimeo' ? 'Vimeo' :
                 video.video_source === 'local' ? 'Local' :
                 video.video_source) : '-'}</p>
              <p><span className="text-gray-500">Method:</span> {video.extraction_method || '-'}</p>
              {video.duration && (
                <p><span className="text-gray-500">Duration:</span> {formatDuration(video.duration)}</p>
              )}
            </div>
          </div>

          {/* Processing Status Card */}
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
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Cloudinary Upload</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  video.cloudinary_url ? 'bg-green-500/20 text-green-300' :
                  video.final_processed_video_url ? 'bg-yellow-500/20 text-yellow-300' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {video.cloudinary_url ? '✓ Uploaded' :
                   video.final_processed_video_url ? '⏳ Pending' : 'Not Ready'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Google Sheets Sync</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  video.google_sheets_synced ? 'bg-green-500/20 text-green-300' :
                  video.final_processed_video_url ? 'bg-yellow-500/20 text-yellow-300' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {video.google_sheets_synced ? '✓ Synced' :
                   video.final_processed_video_url ? '⏳ Pending' : 'Not Ready'}
                </span>
              </div>
            </div>
          </div>

          {/* Video Information Card */}
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

          {/* TTS Settings Card */}
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
            {video.tts_speed && (
              <div className="mt-3 pt-3 border-t border-white/10">
                <p className="text-xs text-gray-400">
                  TTS Speed: {video.tts_speed}x | Temp: {video.tts_temperature || '0.75'}
                </p>
              </div>
            )}
          </div>

          {/* Processing Checklist */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <h4 className="text-sm font-semibold text-gray-300 mb-3">Processing Checklist</h4>
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
        </div>
      </div>
    </div>
  );
}

export default VideoDetail;

