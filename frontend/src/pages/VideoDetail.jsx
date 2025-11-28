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
import { ProcessingStatusCard } from '../components/video/ProcessingStatusCard';
import { videosApi } from '../api';
import { formatDate, truncateText, formatDuration } from '../utils/formatters';
import { useStore } from '../store';
import { showError, showWarning, showSuccess, showConfirm, showInfo } from '../utils/alerts';

export function VideoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const {
    startProcessing,
    completeProcessing,
    getProcessingState,
    clearProcessingForVideo,
  } = useStore();

  const [activeTab, setActiveTab] = useState('info');
  // const [progress, setProgress] = useState(0); // Removed simulated progress
  
  // Get processing state early so it can be used in refetchInterval
  const processingState = id ? getProcessingState(id) : null;
  
  // Fetch video details with real-time polling during processing
  const { data: video, isLoading, refetch } = useQuery({
    queryKey: ['video', id],
    queryFn: () => videosApi.getById(id),
    enabled: !!id,
    // Add staleTime to ensure fresh data during processing
    staleTime: 0, // Always consider data stale to force refetch
    // Add cacheTime to keep data in cache but allow refetch
    cacheTime: 0, // Don't cache during processing
    refetchInterval: (query) => {
      const video = query.state.data;
      if (!video) return false;
      
      // Get current processing state dynamically
      const currentProcessingState = id ? getProcessingState(id) : null;
      
      // Check if any processing is active
      const isProcessing = 
        video.transcription_status === 'transcribing' ||
        video.ai_processing_status === 'processing' ||
        video.script_status === 'generating' ||
        video.synthesis_status === 'synthesizing' ||
        (video.synthesis_status === 'synthesized' && !video.final_processed_video_url) ||
        (currentProcessingState && currentProcessingState.type) ||
        // Poll if Cloudinary/Sheets are pending (after final video is ready)
        (video.final_processed_video_url && !video.cloudinary_url) ||
        (video.final_processed_video_url && !video.google_sheets_synced) ||
        // Poll if we are in a transition state (e.g., Transcribed but AI not started yet)
        (video.transcription_status === 'transcribed' && (video.ai_processing_status === 'pending' || video.ai_processing_status === 'not_processed')) ||
        (video.ai_processing_status === 'processed' && video.script_status === 'pending');
      
      if (isProcessing) {
        return 2000; // Poll every 2 seconds during processing
      }
      return false;
    },
  });
  
  // Calculate elapsed time for transcription (after video is loaded)
  const transcriptionElapsedMinutes = video && video.transcript_started_at 
    ? Math.floor((new Date() - new Date(video.transcript_started_at)) / 1000 / 60)
    : 0;
  
  // Check if transcription is stuck (running for more than 2 minutes)
  const isTranscriptionStuck = video?.transcription_status === 'transcribing' && transcriptionElapsedMinutes > 2;

  // Auto-clear stuck processing state on mount and when video status changes
  useEffect(() => {
    if (!video || !processingState) return;
    
    const { type } = processingState;
    let shouldClear = false;
    
    // Check if processing state doesn't match actual video status
    if (type === 'transcribe') {
      // Clear if transcription is not actually transcribing (failed, completed, or stuck)
      if (video.transcription_status !== 'transcribing') {
        shouldClear = true;
      } else if (isTranscriptionStuck) {
        // Clear if transcription is stuck (>2 minutes)
        shouldClear = true;
      }
    } else if (type === 'processAI') {
      // Clear if AI processing is not actually processing
      if (video.ai_processing_status !== 'processing') {
        shouldClear = true;
      }
    } else if (type === 'download') {
      // Clear if video is already downloaded
      if (video.is_downloaded) {
        shouldClear = true;
      }
    }
    
    if (shouldClear) {
      console.log(`Auto-clearing stuck processing state for ${type}`);
      clearProcessingForVideo(id);
      if (isTranscriptionStuck) {
        toast.warning('Processing state cleared. Transcription appears stuck. You can retry now.', { duration: 5000 });
      }
    }
  }, [video, processingState, id, clearProcessingForVideo, isTranscriptionStuck]);

  // Force clear on initial load if transcription is stuck
  useEffect(() => {
    if (video && isTranscriptionStuck && processingState) {
      console.log('Force clearing stuck processing state on initial load');
      clearProcessingForVideo(id);
    }
  }, [video?.id]); // Only run once when video loads

  // Removed simulated progress effect

  // Check completion and clear stuck processing states
  useEffect(() => {
    if (processingState && video) {
      const { type } = processingState;
      let isCompleted = false;
      let isStuck = false;

      if (type === 'download' && video.is_downloaded) {
        isCompleted = true;
      } else if (type === 'transcribe') {
        if (video.transcription_status === 'transcribed') {
          // Don't complete yet if we expect AI processing to follow
          // But if we are just tracking "transcribe" action, maybe we should?
          // For now, let's keep it simple: if transcribed, this step is done.
          isCompleted = true;
        } else if (video.transcription_status === 'failed') {
          isCompleted = true;
        } else if (video.transcription_status === 'transcribing' && isTranscriptionStuck) {
          isStuck = true;
        }
      } else if (type === 'processAI') {
        if (video.ai_processing_status === 'processed') {
          isCompleted = true;
        } else if (video.ai_processing_status === 'failed') {
          isCompleted = true;
        }
      }

      if (isCompleted || isStuck) {
        // setProgress(100); // Removed
        setTimeout(() => {
          completeProcessing(id);
          // setProgress(0); // Removed
          if (isStuck) {
            showWarning('Processing Stuck', 'Processing state cleared. You can now retry the operation.', { timer: 3000, showConfirmButton: false });
          }
        }, 1000);
      }
    }
  }, [video, processingState, id, completeProcessing, isTranscriptionStuck]);

  // Completion Summary
  useEffect(() => {
    if (video?.final_processed_video_url && video?.status === 'success') {
       // Check if we just finished processing (could track previous state, but for now just show if we are viewing it)
       // To avoid showing it every time, we might need a local state "hasShownCompletion".
       // But the user asked for "show the box to know whichone is done".
       // Maybe just relying on the ProcessingStatusCard is enough?
       // The user said: "for the process complites also show the box to know whichone is done and which is pending"
       // The ProcessingStatusCard does exactly this.
    }
  }, [video?.final_processed_video_url]);

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
      // Check if already transcribing and stuck - reset first
      if (video?.transcription_status === 'transcribing' && isTranscriptionStuck) {
        // Reset stuck transcription first
        return videosApi.resetTranscription(id).then(() => {
          // Then start new transcription
          startProcessing(id, 'transcribe');
          return videosApi.transcribe(id);
        });
      }
      startProcessing(id, 'transcribe');
      return videosApi.transcribe(id);
    },
    onSuccess: (response) => {
      // Check for warnings in response (visual/enhanced errors)
      if (response?.data?.warnings && response.data.warnings.length > 0) {
        const warnings = response.data.warnings;
        let warningMessage = warnings.join('\n\n');
        
        showWarning(
          'Transcription Completed with Warnings',
          warningMessage,
          { confirmButtonText: 'OK', width: '600px' }
        );
      } else {
        toast.success('Processing started');
      }
      
      let pollCount = 0;
      const pollInterval = setInterval(() => {
        pollCount++;
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
              showSuccess('Video Processing Completed!', 'All steps completed successfully.');
            } else if (data.transcription_status === 'failed') {
              showError(
                'Transcription Failed',
                data.transcript_error_message || 'Transcription failed. Please check your settings and try again.',
                { confirmButtonText: 'OK' }
              );
            } else if (data.transcription_status === 'transcribed') {
              // Check for visual or enhanced errors
              const hasVisual = data.visual_transcript;
              const hasEnhanced = data.enhanced_transcript;
              
              if (!hasVisual || !hasEnhanced) {
                let missingItems = [];
                if (!hasVisual) missingItems.push('Visual Analysis');
                if (!hasEnhanced) missingItems.push('AI Enhancement');
                
                showWarning(
                  'Transcription Completed',
                  `Transcription completed, but ${missingItems.join(' and ')} ${missingItems.length > 1 ? 'were' : 'was'} not generated. Please check your AI provider settings (Gemini required for Visual Analysis).`,
                  { confirmButtonText: 'OK', width: '600px' }
                );
              } else {
                toast.success('Transcription completed successfully!');
              }
            }
          } else if (data) {
            // Show progress updates for long-running processes
            // Show progress updates for long-running processes
            if (pollCount % 15 === 0) { // Show updates every 30 seconds (15 * 2s)
              if (data.transcription_status === 'transcribing') {
                const elapsed = data.elapsed_seconds || 0;
                showInfo('Transcription in progress...', `Elapsed: ${Math.floor(elapsed / 60)}m ${elapsed % 60}s`, { showConfirmButton: false, timer: 2000, toast: true, position: 'top-end' });
              } else if (data.ai_processing_status === 'processing') {
                showInfo('AI Processing...', 'This may take a few minutes.', { showConfirmButton: false, timer: 2000, toast: true, position: 'top-end' });
              } else if (data.script_status === 'generating') {
                showInfo('Generating Script...', 'Creating Hindi script...', { showConfirmButton: false, timer: 2000, toast: true, position: 'top-end' });
              } else if (data.synthesis_status === 'synthesizing') {
                showInfo('Synthesizing...', 'Generating audio...', { showConfirmButton: false, timer: 2000, toast: true, position: 'top-end' });
              }
            }
            // Auto-clear processing state if stuck
            if (data.transcription_status === 'transcribing') {
              const elapsed = data.elapsed_seconds || 0;
              if (elapsed > 2 * 60) { // 2 minutes
                completeProcessing(id);
                showWarning(
                  'Transcription Appears Stuck',
                  'Transcription has been running for more than 2 minutes. Processing state cleared. You can retry now.',
                  { confirmButtonText: 'OK' }
                );
              }
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
            completeProcessing(id); // Clear processing state
            showWarning(
              'Processing Timeout',
              'Processing is taking longer than expected. Processing state cleared. You can check back later or retry.',
              { confirmButtonText: 'OK', width: '600px' }
            );
          }
        });
      }, 30 * 60 * 1000); // 30 minutes
    },
    onError: (error) => {
      completeProcessing(id);
      const errorMsg = error?.response?.data?.error || error?.message || 'Processing failed';
      const errorDetails = error?.response?.data?.detail || '';
      
      // Provide more helpful error messages with SweetAlert
      if (errorMsg.includes('timeout') || errorMsg.includes('timed out')) {
        showError(
          'Processing Timeout',
          'Processing timed out. The video may be too long. Please try again or use a shorter video.',
          { confirmButtonText: 'OK', width: '600px' }
        );
      } else if (errorMsg.includes('already_processing')) {
        showInfo('Processing in Progress', 'Processing is already in progress. Please wait.', { showConfirmButton: false, timer: 3000 });
      } else {
        showError(
          'Processing Failed',
          errorDetails || errorMsg,
          { confirmButtonText: 'OK', width: '600px' }
        );
      }
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

  const resetTranscriptionMutation = useMutation({
    mutationFn: () => {
      return videosApi.resetTranscription(id);
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Transcription reset successfully');
      queryClient.invalidateQueries(['video', id]);
      queryClient.invalidateQueries(['videos']);
      refetch();
      completeProcessing(id);
    },
    onError: (error) => {
      toast.error(error?.response?.data?.error || 'Failed to reset transcription');
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

  const handleRetry = async (stepId) => {
    switch (stepId) {
      case 'transcription':
        transcribeMutation.mutate();
        break;
      case 'ai_processing':
        processAIMutation.mutate();
        break;
      case 'script':
        // Assuming script generation is part of AI processing or has its own endpoint?
        // If no specific endpoint, try processAI
        processAIMutation.mutate();
        break;
      case 'synthesis':
        // For synthesis, we might need to know the profile ID. 
        // If we don't have it, maybe reprocess is safer, or try synthesize with default?
        // Let's try to use the existing voice profile if available
        if (video.voice_profile) {
           try {
             startProcessing(id, 'synthesis'); // Add this type to store if needed
             await videosApi.synthesize(id, video.voice_profile);
             toast.success('Synthesis retried');
             refetch();
           } catch (error) {
             toast.error('Failed to retry synthesis');
             completeProcessing(id);
           }
        } else {
          toast.error('No voice profile selected. Please configure voice settings.');
        }
        break;
      default:
        toast.error('Unknown step to retry');
    }
  };

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
					onClick={() => navigate("/videos")}>
					Back
				</Button>
				<h1 className="text-2xl font-bold">Video Details</h1>
			</div>

			{/* Main content - Full Width Layout */}
			<div className="grid grid-cols-1 xl:grid-cols-3 gap-6 w-full">
				{/* Left column - Video and main content */}
				<div className="xl:col-span-2 space-y-6 w-full">
					{/* Video player */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						{video.final_processed_video_url ||
						video.local_file_url ||
						video.video_url ? (
							<div className="relative rounded-lg overflow-hidden bg-black aspect-video">
								<video
									src={
										video.final_processed_video_url ||
										video.local_file_url ||
										video.video_url
									}
									poster={video.cover_url}
									controls
									className="w-full h-full"
								/>
								{video.final_processed_video_url && (
									<div className="absolute top-2 right-2 px-2 py-1 bg-green-500/80 text-white text-xs rounded">
										✓ Final Video (with new Hindi audio)
									</div>
								)}
								{!video.final_processed_video_url &&
									video.local_file_url && (
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

					{/* Progress Indicators - Replaced with ProcessingStatusCard */}
					{(processingState || 
            video.transcription_status === 'transcribing' || 
            video.ai_processing_status === 'processing' ||
            video.script_status === 'generating' ||
            video.synthesis_status === 'synthesizing' ||
            video.transcription_status === 'failed' ||
            video.ai_processing_status === 'failed' ||
            video.script_status === 'failed' ||
            video.synthesis_status === 'failed' ||
            (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
          ) && (
            <ProcessingStatusCard 
              video={video} 
              processingState={processingState}
              onRetry={handleRetry} 
            />
					)}

					{/* Actions and Video Versions - Combined in one card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						{/* Actions Section */}
						<div className="mb-6">
							<h4 className="text-sm font-semibold text-gray-300 mb-4">
								Actions
							</h4>
							<div className="grid grid-cols-2 md:grid-cols-4 gap-2">
								{!video.is_downloaded &&
									video.status === "success" && (
										<Button
											size="sm"
											variant="secondary"
											icon={Download}
											onClick={() =>
												downloadMutation.mutate()
											}
											loading={
												downloadMutation.isPending ||
												(!!processingState &&
												processingState.type ===
													"download")
											}
											disabled={
												downloadMutation.isPending ||
												(!!processingState &&
												processingState.type ===
													"download")
											}>
											{downloadMutation.isPending || (processingState?.type ===
											"download")
												? "Downloading..."
												: "Download"}
										</Button>
									)}

								{(video.transcription_status ===
									"not_transcribed" ||
									video.transcription_status === "failed" ||
									isTranscriptionStuck) && (
									<Button
										size="sm"
										variant={
											video.transcription_status ===
												"failed" || isTranscriptionStuck
												? "danger"
												: "secondary"
										}
										icon={FileText}
										onClick={() => {
											// Clear processing state if stuck before starting
											if (
												isTranscriptionStuck ||
												(processingState &&
													processingState.type ===
														"transcribe")
											) {
												clearProcessingForVideo(id);
											}
											transcribeMutation.mutate();
										}}
										loading={
											transcribeMutation.isPending ||
											(!!processingState &&
											processingState.type ===
												"transcribe" &&
											!isTranscriptionStuck)
										}
										disabled={
											transcribeMutation.isPending ||
											(!!processingState &&
											processingState.type ===
												"transcribe" &&
											!isTranscriptionStuck)
										}>
										{isTranscriptionStuck
											? `Retry Process (Stuck ${transcriptionElapsedMinutes}m)`
											: video.transcription_status ===
											  "failed"
											? "Retry Process"
											: "Process Video"}
									</Button>
								)}

								{/* Reset button for stuck transcriptions */}
								{isTranscriptionStuck && (
									<Button
										size="sm"
										variant="danger"
										icon={RefreshCw}
										onClick={async () => {
											const result = await showConfirm(
												'Reset Transcription?',
												`Transcription has been running for ${transcriptionElapsedMinutes} minutes. Do you want to reset it and try again?`,
												{ confirmButtonText: 'Yes, Reset', cancelButtonText: 'Cancel' }
											);
											if (result.isConfirmed) {
												resetTranscriptionMutation.mutate();
												clearProcessingForVideo(id); // Clear processing state
											}
										}}
										loading={
											resetTranscriptionMutation.isPending
										}
										disabled={
											resetTranscriptionMutation.isPending
										}>
										Reset Transcription (
										{transcriptionElapsedMinutes}m)
									</Button>
								)}

								{/* Clear processing state button - shows when processingState exists but video is not actually processing or is stuck */}
								{processingState &&
									video &&
									((processingState.type === "transcribe" &&
										(video.transcription_status !==
											"transcribing" ||
											isTranscriptionStuck)) ||
										(processingState.type === "processAI" &&
											video.ai_processing_status !==
												"processing" &&
											video.ai_processing_status !==
												"processed") ||
										(processingState.type === "download" &&
											video.is_downloaded)) && (
										<Button
											size="sm"
											variant="danger"
											icon={RefreshCw}
											onClick={() => {
												clearProcessingForVideo(id);
												toast.success(
													"Processing state cleared. You can now retry the operation."
												);
											}}>
											{isTranscriptionStuck
												? `Clear Stuck State (${transcriptionElapsedMinutes}m)`
												: "Clear Processing State"}
										</Button>
									)}


								{/* Show reprocess button when transcription is complete OR failed OR stuck OR when other steps are done */}
								{(video.transcription_status ===
									"transcribed" ||
									video.transcription_status === "failed" ||
									isTranscriptionStuck ||
									video.script_status === "generated" ||
									video.script_status === "failed" ||
									video.synthesis_status === "synthesized" ||
									video.synthesis_status === "failed" ||
									video.final_processed_video_url) && (
									<Button
										size="sm"
										variant="secondary"
										icon={RefreshCw}
										onClick={async () => {
											const result = await showConfirm(
												'Reprocess Video?',
												'Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.',
												{ confirmButtonText: 'Yes, Reprocess', cancelButtonText: 'Cancel' }
											);
											if (result.isConfirmed) {
												reprocessMutation.mutate();
											}
										}}
										loading={
											reprocessMutation.isPending ||
											!!processingState ||
											(video &&
												((video.transcription_status ===
													"transcribing" &&
													!isTranscriptionStuck) ||
													video.ai_processing_status ===
														"processing" ||
													video.script_status ===
														"generating" ||
													video.synthesis_status ===
														"synthesizing" ||
													(video.synthesis_status ===
														"synthesized" &&
														!video.final_processed_video_url)))
										}
										disabled={
											reprocessMutation.isPending ||
											!!processingState ||
											(video &&
												((video.transcription_status ===
													"transcribing" &&
													!isTranscriptionStuck) ||
													video.ai_processing_status ===
														"processing" ||
													video.script_status ===
														"generating" ||
													video.synthesis_status ===
														"synthesizing" ||
													(video.synthesis_status ===
														"synthesized" &&
														!video.final_processed_video_url)))
										}>
										{reprocessMutation.isPending ||
										!!processingState ||
										(video &&
											((video.transcription_status ===
												"transcribing" &&
												!isTranscriptionStuck) ||
												video.ai_processing_status ===
													"processing" ||
												video.script_status ===
													"generating" ||
												video.synthesis_status ===
													"synthesizing"))
											? "Reprocessing..."
											: isTranscriptionStuck
											? "Reset & Reprocess"
											: "Reprocess Video"}
									</Button>
								)}
							</div>
						</div>

						{/* Divider */}
						<div className="border-t border-white/10 mb-6"></div>

						{/* Video Versions Section */}
						<div>
							<h4 className="text-sm font-semibold text-gray-300 mb-4">
								Video Versions
							</h4>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
								{(video.local_file_url || video.video_url) && (
									<a
										href={
											video.local_file_url ||
											video.video_url
										}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border border-blue-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Downloaded Video (Original with
											Audio)
										</span>
									</a>
								)}

								{video.voice_removed_video_url && (
									<a
										href={video.voice_removed_video_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30 border border-yellow-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Voice Removed Video (No Audio)
										</span>
									</a>
								)}

								{video.synthesized_audio_url && (
									<a
										href={video.synthesized_audio_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											🎵 Synthesized TTS Audio (Hindi)
										</span>
									</a>
								)}

								{video.final_processed_video_url && (
									<a
										href={video.final_processed_video_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Final Processed Video (with New
											Hindi Audio)
										</span>
									</a>
								)}
							</div>

							{video.synthesis_status === "synthesized" &&
								!video.voice_removed_video_url &&
								!video.final_processed_video_url && (
									<div className="text-xs text-yellow-400 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30 mt-3">
										⏳ Processing video files... (This may
										take a few moments)
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
							{video.title || "Untitled"}
						</h3>

						{video.original_title &&
							video.original_title !== video.title && (
								<p className="text-sm text-gray-400 mb-4">
									{video.original_title}
								</p>
							)}

						{/* Status badges */}
						<div className="flex flex-wrap gap-2 mb-4">
							<StatusBadge status={video.status} />
							{video.transcription_status !==
								"not_transcribed" && (
								<StatusBadge
									status={video.transcription_status}
								/>
							)}
							{video.ai_processing_status !== "not_processed" && (
								<StatusBadge
									status={video.ai_processing_status}
								/>
							)}
							{video.transcript_hindi && (
								<span className="px-2 py-1 text-xs bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/30">
									🇮🇳 Hindi Available
								</span>
							)}
						</div>

						{/* Meta info */}
						<div className="text-sm text-gray-400 space-y-2">
							<p>
								<span className="text-gray-500">Created:</span>{" "}
								{formatDate(video.created_at)}
							</p>
							<p>
								<span className="text-gray-500">Source:</span>{" "}
								{video.video_source
									? video.video_source === "rednote"
										? "RedNote"
										: video.video_source === "youtube"
										? "YouTube"
										: video.video_source === "facebook"
										? "Facebook"
										: video.video_source === "instagram"
										? "Instagram"
										: video.video_source === "vimeo"
										? "Vimeo"
										: video.video_source === "local"
										? "Local"
										: video.video_source
									: "-"}
							</p>
							<p>
								<span className="text-gray-500">Method:</span>{" "}
								{video.extraction_method || "-"}
							</p>
							{video.duration && (
								<p>
									<span className="text-gray-500">
										Duration:
									</span>{" "}
									{formatDuration(video.duration)}
								</p>
							)}
						</div>
					</div>

					{/* Processing Status Card - Sidebar */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<div className="flex items-center justify-between mb-3">
							<h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
								Processing Status
							</h4>
							{(() => {
								// Calculate overall progress percentage
                const isTranscribing = video.transcription_status === 'transcribing' || (processingState?.type === 'transcribe');
                const isProcessingAI = video.ai_processing_status === 'processing' || (processingState?.type === 'processAI');
                const isSynthesizing = video.synthesis_status === 'synthesizing' || (processingState?.type === 'synthesis');
                const isDownloading = processingState?.type === 'download';

								const steps = [
									{ done: video.is_downloaded || isDownloading, weight: 10 },
									{ done: video.transcription_status === 'transcribed', weight: 25 },
									{ done: video.ai_processing_status === 'processed', weight: 15 },
									{ done: video.script_status === 'generated', weight: 15 },
									{ done: video.synthesis_status === 'synthesized', weight: 20 },
									{ done: !!video.final_processed_video_url, weight: 10 },
									{ done: !!video.cloudinary_url, weight: 3 },
									{ done: !!video.google_sheets_synced, weight: 2 },
								];
								const totalWeight = steps.reduce((sum, step) => sum + step.weight, 0);
								const completedWeight = steps.reduce((sum, step) => sum + (step.done ? step.weight : 0), 0);
								const progressPercent = Math.round((completedWeight / totalWeight) * 100);
								
								return (
									<div className="flex items-center gap-2">
										<div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
											<div 
												className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300"
												style={{ width: `${progressPercent}%` }}
											/>
										</div>
										<span className="text-xs font-semibold text-gray-300 min-w-[3rem] text-right">
											{progressPercent}%
										</span>
									</div>
								);
							})()}
						</div>
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Download
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.is_downloaded
											? "bg-green-500/20 text-green-300"
                      : (processingState?.type === 'download')
                      ? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.is_downloaded
										? "✓ Complete"
                    : (processingState?.type === 'download')
                    ? "⏳ Downloading"
										: "Pending"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Transcription
								</span>
                {(() => {
                  const isTranscribing = video.transcription_status === 'transcribing' || (processingState?.type === 'transcribe');
                  const isFailed = video.transcription_status === 'failed';
                  const isComplete = video.transcription_status === 'transcribed';
                  
                  return (
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        isComplete
                          ? "bg-green-500/20 text-green-300"
                          : isTranscribing
                          ? "bg-yellow-500/20 text-yellow-300 animate-pulse"
                          : isFailed
                          ? "bg-red-500/20 text-red-300"
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                      {isComplete
                        ? "✓ Complete"
                        : isTranscribing
                        ? "⏳ Processing"
                        : isFailed
                        ? "✗ Failed"
                        : "Pending"}
                    </span>
                  );
                })()}
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									AI Processing
								</span>
                {(() => {
                  const isProcessing = video.ai_processing_status === 'processing' || (processingState?.type === 'processAI');
                  const isFailed = video.ai_processing_status === 'failed';
                  const isComplete = video.ai_processing_status === 'processed';
                  
                  return (
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        isComplete
                          ? "bg-green-500/20 text-green-300"
                          : isProcessing
                          ? "bg-yellow-500/20 text-yellow-300 animate-pulse"
                          : isFailed
                          ? "bg-red-500/20 text-red-300"
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                      {isComplete
                        ? "✓ Complete"
                        : isProcessing
                        ? "⏳ Processing"
                        : isFailed
                        ? "✗ Failed"
                        : "Pending"}
                    </span>
                  );
                })()}
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Script Generation
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.script_status === "generated"
											? "bg-green-500/20 text-green-300"
											: video.script_status ===
											  "generating"
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: video.script_status === "failed"
											? "bg-red-500/20 text-red-300"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.script_status === "generated"
										? "✓ Complete"
										: video.script_status === "generating"
										? "⏳ Processing"
										: video.script_status === "failed"
										? "✗ Failed"
										: "Pending"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									TTS Synthesis
								</span>
                {(() => {
                  const isSynthesizing = video.synthesis_status === 'synthesizing' || (processingState?.type === 'synthesis');
                  const isFailed = video.synthesis_status === 'failed';
                  const isComplete = video.synthesis_status === 'synthesized';
                  
                  return (
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        isComplete
                          ? "bg-green-500/20 text-green-300"
                          : isSynthesizing
                          ? "bg-yellow-500/20 text-yellow-300 animate-pulse"
                          : isFailed
                          ? "bg-red-500/20 text-red-300"
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                      {isComplete
                        ? "✓ Complete"
                        : isSynthesizing
                        ? "⏳ Processing"
                        : isFailed
                        ? "✗ Failed"
                        : "Pending"}
                    </span>
                  );
                })()}
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Final Video
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.final_processed_video_url
											? "bg-green-500/20 text-green-300"
                      : (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
                      ? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.final_processed_video_url
										? "✓ Ready"
                    : (video.synthesis_status === 'synthesized' && !video.final_processed_video_url)
                    ? "⏳ Assembling"
										: "Pending"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Cloudinary Upload
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.cloudinary_url
											? "bg-green-500/20 text-green-300"
											: video.final_processed_video_url
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.cloudinary_url
										? "✓ Uploaded"
										: video.final_processed_video_url
										? "⏳ Uploading..."
										: "Not Ready"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Google Sheets Sync
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.google_sheets_synced
											? "bg-green-500/20 text-green-300"
											: video.final_processed_video_url
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.google_sheets_synced
										? "✓ Synced"
										: video.final_processed_video_url
										? "⏳ Syncing..."
										: "Not Ready"}
								</span>
							</div>
						</div>
					</div>

					{/* Video Information Card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
							Video Information
						</h4>
						<div className="space-y-2">
							{video.duration && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Duration
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{formatDuration(video.duration)}
									</span>
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Source
								</span>
								<span className="text-xs text-gray-300">
									{video.video_source
										? video.video_source === "rednote"
											? "RedNote"
											: video.video_source === "youtube"
											? "YouTube"
											: video.video_source === "facebook"
											? "Facebook"
											: video.video_source === "instagram"
											? "Instagram"
											: video.video_source === "vimeo"
											? "Vimeo"
											: video.video_source === "local"
											? "Local"
											: video.video_source
										: "-"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Method
								</span>
								<span className="text-xs text-gray-300">
									{video.extraction_method || "-"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Language
								</span>
								<span className="text-xs text-gray-300">
									{video.transcript_language || "Unknown"}
								</span>
							</div>
							{video.video_id && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Video ID
									</span>
									<span
										className="text-xs text-gray-300 font-mono truncate max-w-[120px]"
										title={video.video_id}>
										{video.video_id}
									</span>
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Created
								</span>
								<span className="text-xs text-gray-300">
									{formatDate(video.created_at)}
								</span>
							</div>
						</div>
					</div>

					{/* TTS Settings Card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
							TTS Settings
						</h4>
						<div className="space-y-2">
							{video.tts_speed ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Speed
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_speed}x
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Speed
									</span>
									<span className="text-xs text-gray-500">
										Default (1.0x)
									</span>
								</div>
							)}
							{video.tts_temperature !== undefined &&
							video.tts_temperature !== null ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Temperature
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_temperature}
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Temperature
									</span>
									<span className="text-xs text-gray-500">
										Default (0.75)
									</span>
								</div>
							)}
							{video.tts_repetition_penalty !== undefined &&
							video.tts_repetition_penalty !== null ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Repetition Penalty
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_repetition_penalty}
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Repetition Penalty
									</span>
									<span className="text-xs text-gray-500">
										Default (5.0)
									</span>
								</div>
							)}
							{video.voice_profile ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Voice Profile
									</span>
									<span className="text-xs text-green-300">
										✓ Assigned
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Voice Profile
									</span>
									<span className="text-xs text-gray-500">
										Default
									</span>
								</div>
							)}
							{video.transcript_hindi && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Hindi Translation
									</span>
									<span className="text-xs text-purple-300">
										✓ Available
									</span>
								</div>
							)}
							{video.hindi_script && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Hindi Script
									</span>
									<span className="text-xs text-indigo-300">
										✓ Generated
									</span>
								</div>
							)}
						</div>
						{video.tts_speed && (
							<div className="mt-3 pt-3 border-t border-white/10">
								<p className="text-xs text-gray-400">
									TTS Speed: {video.tts_speed}x | Temp:{" "}
									{video.tts_temperature || "0.75"}
								</p>
							</div>
						)}
					</div>
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
								className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
									activeTab === tab.id
										? "bg-white/10 text-white"
										: "text-gray-400 hover:text-white hover:bg-white/5"
								}`}>
								{tab.label}
							</button>
						))}
					</div>
				</div>

				{/* Tab content - Full Width */}
				<div className="p-6 min-h-[400px] w-full">
					{activeTab === "info" && (
						<div className="space-y-6">
							<div className="bg-white/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
									<FileText className="w-4 h-4" />
									Description
								</h4>
								<p className="text-sm text-gray-300 leading-relaxed">
									{video.description || (
										<span className="text-gray-500 italic">
											No description available
										</span>
									)}
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
												<p className="text-xs font-medium text-gray-300">
													Video Added
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.created_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.transcript_processed_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-green-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Transcription Completed
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.transcript_processed_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.script_generated_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Hindi Script Generated
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.script_generated_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.synthesized_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-purple-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													TTS Audio Synthesized
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.synthesized_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.final_processed_video_url && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Final Video Ready
												</p>
												<p className="text-xs text-gray-500">
													Processing complete
												</p>
											</div>
										</div>
									)}
									{video.cloudinary_uploaded_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Uploaded to Cloudinary
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.cloudinary_uploaded_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.google_sheets_synced_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Synced to Google Sheets
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.google_sheets_synced_at
													)}
												</p>
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
										onClick={() =>
											copyToClipboard(video.url)
										}
										className="opacity-0 group-hover:opacity-100 transition-opacity">
										Copy
									</Button>
									<a
										href={video.url}
										target="_blank"
										rel="noopener noreferrer"
										className="p-2 text-gray-400 hover:text-white transition-colors"
										title="Open in new tab">
										<ExternalLink className="w-4 h-4" />
									</a>
								</div>
							</div>

							{(video.local_file_url ||
								video.voice_removed_video_url ||
								video.final_processed_video_url ||
								video.synthesized_audio_url) && (
								<div className="bg-white/5 rounded-lg p-4 border border-white/10">
									<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
										<Download className="w-4 h-4" />
										Generated Files
									</h4>
									<div className="grid grid-cols-2 gap-2">
										{video.local_file_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Original:
												</span>
												<span className="text-green-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.voice_removed_video_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Voice Removed:
												</span>
												<span className="text-yellow-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.synthesized_audio_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													TTS Audio:
												</span>
												<span className="text-purple-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.final_processed_video_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Final Video:
												</span>
												<span className="text-green-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
									</div>
								</div>
							)}
						</div>
					)}

					{activeTab === "transcript" && (
						<div className="space-y-6">
							{/* Comparison Header */}
							{(video.transcript ||
								video.whisper_transcript ||
								video.visual_transcript ||
								video.enhanced_transcript) && (
								<div className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-green-500/10 to-orange-500/10 rounded-lg p-4 border border-white/10">
									<h3 className="text-lg font-semibold text-white mb-2">
										📊 Triple Transcription Comparison + AI
										Enhancement
									</h3>
									<p className="text-sm text-gray-400">
										Compare NCA Toolkit, Whisper AI, and
										Visual Analysis transcriptions. The
										Enhanced transcript uses AI to merge all
										three sources for perfect accuracy.
									</p>
								</div>
							)}

							{/* Enhanced Transcript (Primary Display) - Show if available (Visual Analysis is optional) */}
							{video.enhanced_transcript && (
							<div className="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 rounded-lg p-4 border border-orange-500/30 mb-6 w-full">
								<div className="flex items-center justify-between mb-3">
									<h4 className="text-base font-semibold text-orange-300 flex items-center gap-2">
										⭐ AI-Enhanced Transcript (Best Quality)
									</h4>
									<span className="px-2 py-1 text-xs rounded bg-orange-500/20 text-orange-300">
										✓ AI-Merged (All 3 Sources)
									</span>
								</div>
								<p className="text-xs text-gray-400 mb-3">
									This transcript combines the best parts from
									Whisper, NCA Toolkit, and Visual Analysis (if available)
									using AI for perfect accuracy. <strong className="text-orange-400">Visual Analysis is optional.</strong>
								</p>

								{/* With Timestamps */}
								<div className="space-y-2 mb-3">
									<div className="flex items-center justify-between">
										<h5 className="text-xs font-medium text-gray-300">
											With Timestamps
										</h5>
										<Button
											size="sm"
											variant="ghost"
											icon={Copy}
											onClick={() =>
												copyToClipboard(
													video.enhanced_transcript
												)
											}
											className="text-xs">
											Copy
										</Button>
									</div>
									<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
										<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
											{video.enhanced_transcript}
										</p>
									</div>
								</div>

								{/* Plain Text */}
								<div className="space-y-2">
									<div className="flex items-center justify-between">
										<h5 className="text-xs font-medium text-gray-300">
											Plain Text
										</h5>
										<Button
											size="sm"
											variant="ghost"
											icon={Copy}
											onClick={() =>
												copyToClipboard(
													video.enhanced_transcript_without_timestamps ||
														video.enhanced_transcript
												)
											}
											className="text-xs">
											Copy
										</Button>
									</div>
									<div className="p-3 bg-orange-500/5 rounded-lg max-h-96 overflow-y-auto border border-orange-500/20">
										<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
											{video.enhanced_transcript_without_timestamps ||
												video.enhanced_transcript}
										</p>
									</div>
								</div>

								{/* Hindi Translation - Show if available */}
								{video.enhanced_transcript_hindi && (
									<div className="space-y-2 mt-3">
										<div className="flex items-center justify-between">
											<h5 className="text-xs font-medium text-purple-300">
												Hindi Translation
											</h5>
											<Button
												size="sm"
												variant="ghost"
												icon={Copy}
												onClick={() =>
													copyToClipboard(
														video.enhanced_transcript_hindi
													)
												}
												className="text-xs">
												Copy
											</Button>
										</div>
										<div className="p-3 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
											<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
												{
													video.enhanced_transcript_hindi
												}
											</p>
										</div>
									</div>
								)}
							</div>
							)}
							
							{/* Show message if Enhanced Transcript is not available */}
							{!video.enhanced_transcript && (video.transcript || video.whisper_transcript) && (
								<div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30 mb-6 w-full">
									<div className="flex items-center gap-2 mb-2">
										<span className="text-yellow-400">⏳</span>
										<h4 className="text-base font-semibold text-yellow-300">
											AI-Enhanced Transcript Processing
										</h4>
									</div>
									<p className="text-xs text-gray-400 mb-2">
										AI-Enhanced transcript is being generated. Status:
									</p>
									<ul className="text-xs text-gray-400 space-y-1 ml-4 list-disc">
										<li className="text-green-400">
											✓ NCA Toolkit / Whisper AI: Complete
										</li>
										<li className={video.visual_transcript ? "text-green-400" : "text-gray-500"}>
											{video.visual_transcript ? "✓" : "○"} Visual Analysis: {video.visual_transcript ? "Complete" : "Optional (Not Available - continuing without it)"}
										</li>
									</ul>
									<p className="text-xs text-yellow-400 mt-3">
										<strong>Note:</strong> AI-Enhanced transcript is being generated using available sources. 
										Visual Analysis is optional and will be included if available for better accuracy.
									</p>
								</div>
							)}
							
							{/* Show message if no transcript sources available */}
							{!video.enhanced_transcript && !video.transcript && !video.whisper_transcript && (
								<div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30 mb-6 w-full">
									<div className="flex items-center gap-2 mb-2">
										<span className="text-yellow-400">⚠️</span>
										<h4 className="text-base font-semibold text-yellow-300">
											AI-Enhanced Transcript Not Available
										</h4>
									</div>
									<p className="text-xs text-gray-400 mb-2">
										AI-Enhanced transcript requires at least NCA/Whisper transcription:
									</p>
									<ul className="text-xs text-gray-400 space-y-1 ml-4 list-disc">
										<li className={video.transcript || video.whisper_transcript ? "text-green-400" : "text-yellow-400"}>
											{video.transcript || video.whisper_transcript ? "✓" : "⏳"} NCA Toolkit / Whisper AI: {video.transcript || video.whisper_transcript ? "Complete" : "Pending (Required)"}
										</li>
										<li className={video.visual_transcript ? "text-green-400" : "text-gray-500"}>
											{video.visual_transcript ? "✓" : "○"} Visual Analysis: {video.visual_transcript ? "Complete" : "Optional (Not Available)"}
										</li>
									</ul>
									<p className="text-xs text-yellow-400 mt-3">
										<strong>Note:</strong> Please start transcription to generate AI-Enhanced transcript. 
										Visual Analysis is optional and will be included if available for better accuracy.
									</p>
								</div>
							)}

							{/* Triple Transcription Comparison - Full Width Layout */}
							{video.transcript ||
							video.whisper_transcript ||
							video.visual_transcript ? (
								<div className="grid grid-cols-1 xl:grid-cols-3 gap-6 w-full">
									{/* NCA TOOLKIT TRANSCRIPTION */}
									<div className="space-y-4">
										<div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30">
											<div className="flex items-center justify-between mb-3">
												<h4 className="text-base font-semibold text-blue-300 flex items-center gap-2">
													🔷 NCA Toolkit
												</h4>
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.transcription_status ===
														"transcribed"
															? "bg-green-500/20 text-green-300"
															: video.transcription_status ===
															  "transcribing"
															? "bg-yellow-500/20 text-yellow-300"
															: video.transcription_status ===
															  "failed"
															? "bg-red-500/20 text-red-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.transcription_status ===
													"transcribed"
														? "✓ Complete"
														: video.transcription_status ===
														  "transcribing"
														? isTranscriptionStuck
															? `⏳ Processing (${transcriptionElapsedMinutes}m - Stuck?)`
															: `⏳ Processing (${transcriptionElapsedMinutes}m)`
														: video.transcription_status ===
														  "failed"
														? "✗ Failed"
														: "Pending"}
												</span>
											</div>

											{video.transcript ? (
												<>
													<div className="grid grid-cols-2 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Language:
															</span>
															<span className="text-white ml-1">
																{video.transcript_language ||
																	"Unknown"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.transcript_without_timestamps
																	?.length ||
																	video
																		.transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.transcript_without_timestamps ||
																			video.transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-blue-500/5 rounded-lg max-h-96 overflow-y-auto border border-blue-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.transcript_without_timestamps ||
																	video.transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm">
														No NCA transcription
														available
													</p>
												</div>
											)}
										</div>
									</div>

									{/* VISUAL ANALYSIS TRANSCRIPTION */}
									<div className="space-y-4">
										<div className="bg-purple-500/10 rounded-lg p-4 border border-purple-500/30">
											<div className="flex items-center justify-between mb-3">
												<h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
													👁️ Visual Analysis
												</h4>
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.visual_transcript
															? "bg-green-500/20 text-green-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.visual_transcript
														? "✓ Complete"
														: "Pending"}
												</span>
											</div>

											{video.visual_transcript ? (
												<>
													<div className="grid grid-cols-1 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Frames Analyzed:
															</span>
															<span className="text-white ml-1">
																Every 3ms
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.visual_transcript_without_timestamps
																	?.length ||
																	video
																		.visual_transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.visual_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.visual_transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.visual_transcript_without_timestamps ||
																			video.visual_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.visual_transcript_without_timestamps ||
																	video.visual_transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm mb-2">
														Visual Analysis in
														Progress
													</p>
													<p className="text-xs text-gray-600">
														Analyzing video frames
														every 3 milliseconds
														using Gemini Vision
														API...
													</p>
													{video.transcription_status ===
														"transcribing" && (
														<p className="text-xs text-yellow-400 mt-2 animate-pulse">
															⏳ Frame extraction
															and analysis
															running...
														</p>
													)}
													{video.transcription_status ===
														"transcribed" &&
														!video.visual_transcript && (
															<p className="text-xs text-yellow-400 mt-2">
																⚠ Visual
																analysis may
																still be
																processing.
																Check back in a
																moment or
																reprocess the
																video.
															</p>
														)}
												</div>
											)}

											{/* Show visual transcript segments if available */}
											{video.visual_transcript_segments &&
												Array.isArray(
													video.visual_transcript_segments
												) &&
												video.visual_transcript_segments
													.length > 0 && (
													<div className="space-y-2 mt-4">
														<h5 className="text-xs font-medium text-purple-300">
															Frame-by-Frame
															Analysis
														</h5>
														<div className="p-3 bg-purple-500/5 rounded-lg max-h-64 overflow-y-auto border border-purple-500/20">
															<div className="space-y-2">
																{video.visual_transcript_segments.map(
																	(
																		segment,
																		idx
																	) => (
																		<div
																			key={
																				idx
																			}
																			className="text-xs border-b border-purple-500/10 pb-2 last:border-0">
																			<span className="text-purple-300 font-mono">
																				{segment.timestamp_str ||
																					`${Math.floor(
																						segment.start /
																							60
																					)}:${String(
																						Math.floor(
																							segment.start %
																								60
																						)
																					).padStart(
																						2,
																						"0"
																					)}`}
																			</span>
																			<span className="text-gray-300 ml-2">
																				{segment.text ||
																					segment.description}
																			</span>
																		</div>
																	)
																)}
															</div>
														</div>
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
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.whisper_transcription_status ===
														"transcribed"
															? "bg-green-500/20 text-green-300"
															: video.whisper_transcription_status ===
															  "transcribing"
															? "bg-yellow-500/20 text-yellow-300"
															: video.whisper_transcription_status ===
															  "failed"
															? "bg-red-500/20 text-red-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.whisper_transcription_status ===
													"transcribed"
														? "✓ Complete"
														: video.whisper_transcription_status ===
														  "transcribing"
														? "⏳ Processing"
														: video.whisper_transcription_status ===
														  "failed"
														? "✗ Failed"
														: "Pending"}
												</span>
											</div>

											{video.whisper_transcript ? (
												<>
													<div className="grid grid-cols-2 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Language:
															</span>
															<span className="text-white ml-1">
																{video.whisper_transcript_language ||
																	"Unknown"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.whisper_transcript_without_timestamps
																	?.length ||
																	video
																		.whisper_transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Model:
															</span>
															<span className="text-white ml-1">
																{video.whisper_model_used ||
																	"base"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Confidence:
															</span>
															<span
																className={`ml-1 ${
																	video.whisper_confidence_avg &&
																	video.whisper_confidence_avg >
																		-1.0
																		? "text-green-300"
																		: video.whisper_confidence_avg &&
																		  video.whisper_confidence_avg >
																				-2.0
																		? "text-yellow-300"
																		: "text-red-300"
																}`}>
																{video.whisper_confidence_avg
																	? video.whisper_confidence_avg >
																	  -1.0
																		? "High"
																		: video.whisper_confidence_avg >
																		  -2.0
																		? "Medium"
																		: "Low"
																	: "N/A"}
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.whisper_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.whisper_transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.whisper_transcript_without_timestamps ||
																			video.whisper_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.whisper_transcript_without_timestamps ||
																	video.whisper_transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm">
														No Whisper transcription
														available
													</p>
													{video.whisper_transcription_status ===
														"not_transcribed" && (
														<p className="text-xs mt-2">
															Run dual
															transcription to
															generate
														</p>
													)}
												</div>
											)}
										</div>
									</div>
								</div>
							) : (
								<div className="text-center py-12 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p className="mb-2">
										No transcriptions available
									</p>
									{video.transcription_status ===
										"not_transcribed" && (
										<Button
											size="sm"
											variant="primary"
											className="mt-4"
											onClick={() =>
												transcribeMutation.mutate()
											}
											loading={
												transcribeMutation.isPending
											}>
											Start Triple Transcription + AI
											Enhancement
										</Button>
									)}
								</div>
							)}

							{/* Hindi Translations Comparison - Full Width */}
							{(video.transcript_hindi ||
								video.whisper_transcript_hindi ||
								video.visual_transcript_hindi ||
								video.enhanced_transcript_hindi) && (
								<div className="space-y-4 w-full">
									<h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
										<Globe className="w-5 h-5" />
										🌍 Hindi Translations Comparison
									</h4>

									<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 w-full">
										{/* NCA Hindi */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-blue-300">
													NCA Hindi Translation
												</h5>
												{video.transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.transcript_hindi ? (
												<div className="p-4 bg-blue-500/5 rounded-lg max-h-96 overflow-y-auto border border-blue-500/20">
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
												<h5 className="text-sm font-medium text-green-300">
													Whisper Hindi Translation
												</h5>
												{video.whisper_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.whisper_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.whisper_transcript_hindi ? (
												<div className="p-4 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.whisper_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													No Whisper Hindi translation
												</div>
											)}
										</div>

										{/* Visual Hindi - Always Show */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-purple-300 flex items-center gap-2">
													👁️ Visual Hindi Translation
												</h5>
												{video.visual_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.visual_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.visual_transcript_hindi ? (
												<div className="p-4 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.visual_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													{video.visual_transcript
														? "Visual analysis in progress, translation will appear soon..."
														: "No Visual Hindi translation available"}
												</div>
											)}
										</div>

										{/* Enhanced Hindi - Always Show */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-orange-300 flex items-center gap-2">
													⭐ Enhanced Hindi
													Translation
												</h5>
												{video.enhanced_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.enhanced_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.enhanced_transcript_hindi ? (
												<div className="p-4 bg-orange-500/5 rounded-lg max-h-96 overflow-y-auto border border-orange-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.enhanced_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													{video.enhanced_transcript
														? "Enhanced transcript in progress, translation will appear soon..."
														: "No Enhanced Hindi translation available"}
												</div>
											)}
										</div>
									</div>
								</div>
							)}

							{/* Additional Information Section */}
							<div className="mt-6 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-green-500/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3">
									📋 Transcription Sources Summary
								</h4>
								<div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
									<div className="bg-blue-500/10 rounded p-3 border border-blue-500/20">
										<div className="font-semibold text-blue-300 mb-1">
											NCA Toolkit
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.transcription_status ===
											"transcribed"
												? "✓ Complete"
												: video.transcription_status ===
												  "transcribing"
												? "⏳ Processing"
												: "Pending"}
										</div>
										{video.transcript_language && (
											<div className="text-gray-400">
												Language:{" "}
												{video.transcript_language}
											</div>
										)}
										{video.transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
									</div>

									<div className="bg-purple-500/10 rounded p-3 border border-purple-500/20">
										<div className="font-semibold text-purple-300 mb-1">
											Visual Analysis
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.visual_transcript
												? "✓ Complete"
												: "⏳ Processing"}
										</div>
										<div className="text-gray-400">
											Method: Frame extraction (every 3ms)
										</div>
										{video.visual_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.visual_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
										{video.visual_transcript_segments &&
											Array.isArray(
												video.visual_transcript_segments
											) && (
												<div className="text-gray-400">
													Frames:{" "}
													{
														video
															.visual_transcript_segments
															.length
													}{" "}
													analyzed
												</div>
											)}
									</div>

									<div className="bg-green-500/10 rounded p-3 border border-green-500/20">
										<div className="font-semibold text-green-300 mb-1">
											Whisper AI
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.whisper_transcription_status ===
											"transcribed"
												? "✓ Complete"
												: video.whisper_transcription_status ===
												  "transcribing"
												? "⏳ Processing"
												: "Pending"}
										</div>
										{video.whisper_transcript_language && (
											<div className="text-gray-400">
												Language:{" "}
												{
													video.whisper_transcript_language
												}
											</div>
										)}
										{video.whisper_model_used && (
											<div className="text-gray-400">
												Model:{" "}
												{video.whisper_model_used}
											</div>
										)}
										{video.whisper_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.whisper_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
									</div>
								</div>

								{video.enhanced_transcript && (
									<div className="mt-4 bg-orange-500/10 rounded p-3 border border-orange-500/20">
										<div className="font-semibold text-orange-300 mb-1">
											⭐ AI-Enhanced Transcript
										</div>
										<div className="text-gray-400">
											Status: ✓ Complete (Merged from all
											three sources)
										</div>
										{video.enhanced_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.enhanced_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
										<div className="text-gray-400 text-xs mt-1">
											This is the final, AI-enhanced
											transcript combining the best parts
											from all sources.
										</div>
									</div>
								)}
							</div>
						</div>
					)}

					{activeTab === "script" && (
						<div className="space-y-4">
							{video.hindi_script ? (
								<>
									<div className="mb-4">
										<h4 className="text-sm font-medium text-gray-400 mb-1">
											Hindi Script for TTS
										</h4>
										{video.script_generated_at && (
											<p className="text-xs text-gray-500">
												Generated:{" "}
												{formatDate(
													video.script_generated_at
												)}
											</p>
										)}
										{video.duration && (
											<p className="text-xs text-gray-500">
												Video Duration:{" "}
												{formatDuration(video.duration)}
											</p>
										)}
										{video.tts_speed && (
											<p className="text-xs text-gray-500">
												TTS Parameters: Speed{" "}
												{video.tts_speed}x | Temperature{" "}
												{video.tts_temperature} |
												Repetition Penalty{" "}
												{video.tts_repetition_penalty}
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
													onClick={() =>
														copyToClipboard(
															video.hindi_script
														)
													}>
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
													onClick={() =>
														copyToClipboard(
															video.clean_script_for_tts ||
																video.hindi_script
														)
													}>
													Copy
												</Button>
											</div>
											<div className="p-4 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
												<p className="text-sm whitespace-pre-wrap leading-relaxed">
													{video.clean_script_for_tts ||
														video.hindi_script}
												</p>
											</div>
										</div>
									</div>
								</>
							) : video.script_status === "generating" ? (
								<div className="text-center py-8 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50 animate-pulse" />
									<p>Generating Hindi script...</p>
									<p className="text-xs mt-2">
										This may take a few moments
									</p>
								</div>
							) : video.script_status === "failed" ? (
								<div className="text-center py-8 text-red-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p>Script generation failed</p>
									{video.script_error_message && (
										<p className="text-xs mt-2 text-gray-400">
											{video.script_error_message}
										</p>
									)}
								</div>
							) : (
								<div className="text-center py-8 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p>No script available</p>
									<p className="text-xs mt-2">
										Script will be automatically generated
										after video download
									</p>
								</div>
							)}
						</div>
					)}

					{activeTab === "ai" && (
						<div className="space-y-4">
							{video.ai_summary ? (
								<>
									<div>
										<h4 className="text-sm font-medium text-gray-400 mb-2">
											Summary
										</h4>
										<div className="p-4 bg-white/5 rounded-lg">
											<p className="text-sm">
												{video.ai_summary}
											</p>
										</div>
									</div>
									{video.ai_tags && (
										<div>
											<h4 className="text-sm font-medium text-gray-400 mb-2">
												Tags
											</h4>
											<div className="flex flex-wrap gap-2">
												{video.ai_tags
													.split(",")
													.map((tag, i) => (
														<span
															key={i}
															className="px-2 py-1 text-xs bg-white/10 rounded">
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
									{video.ai_processing_status ===
										"not_processed" && (
										<Button
											size="sm"
											variant="primary"
											className="mt-4"
											onClick={() =>
												processAIMutation.mutate()
											}
											loading={
												processAIMutation.isPending
											}>
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
  );
}

export default VideoDetail;

