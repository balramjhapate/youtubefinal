import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Clock, 
  RefreshCw, 
  AlertCircle 
} from 'lucide-react';
import { Button } from '../common';

export function ProcessingStatusCard({ video, processingState, onRetry }) {
  // Helper to check if a specific step is currently processing locally
  const isLocallyProcessing = (stepId) => {
    if (!processingState) return false;
    const { type } = processingState;
    if (stepId === 'transcription' && type === 'transcribe') return true;
    if (stepId === 'ai_processing' && type === 'processAI') return true;
    if (stepId === 'synthesis' && type === 'synthesis') return true; 
    if (stepId === 'download' && type === 'download') return true;
    if (stepId === 'cloudinary' && type === 'cloudinary') return true;
    if (stepId === 'sheets' && type === 'sheets') return true;
    if (stepId === 'script' && type === 'script') return true;
    if (stepId === 'final_video' && type === 'final_video') return true;
    return false;
  };

  // Local progress simulation for active steps
  const [localProgress, setLocalProgress] = useState(0);

  useEffect(() => {
    // Check if any step is processing
    const isAnyProcessing = 
      video.transcription_status === 'transcribing' ||
      video.ai_processing_status === 'processing' ||
      video.script_status === 'generating' ||
      video.synthesis_status === 'synthesizing' ||
      (video.synthesis_status === 'synthesized' && !video.final_processed_video_url) ||
      processingState;

    if (isAnyProcessing) {
      const interval = setInterval(() => {
        setLocalProgress((prev) => {
          if (prev >= 95) return 95;
          return prev + Math.random() * 2;
        });
      }, 500);
      return () => clearInterval(interval);
    } else {
      setLocalProgress(0);
    }
  }, [video, processingState]);

  const steps = [
    {
      id: 'download',
      label: 'Video Download',
      status: video.is_downloaded ? 'downloaded' : 'pending',
      isProcessing: isLocallyProcessing('download') || (video.status === 'downloading'),
      isCompleted: video.is_downloaded,
      isFailed: false,
      error: null,
    },
    {
      id: 'transcription',
      label: 'Transcription',
      status: video.transcription_status,
      isProcessing: video.transcription_status === 'transcribing' || isLocallyProcessing('transcription'),
      isCompleted: video.transcription_status === 'transcribed',
      isFailed: video.transcription_status === 'failed',
      error: video.transcript_error_message,
    },
    {
      id: 'ai_processing',
      label: 'AI Processing',
      status: video.ai_processing_status,
      isProcessing: video.ai_processing_status === 'processing' || isLocallyProcessing('ai_processing'),
      isCompleted: video.ai_processing_status === 'processed',
      isFailed: video.ai_processing_status === 'failed',
      error: video.ai_error_message,
    },
    {
      id: 'script',
      label: 'Hindi Script Generation',
      status: video.script_status,
      isProcessing: video.script_status === 'generating' || isLocallyProcessing('script'),
      isCompleted: video.script_status === 'generated',
      isFailed: video.script_status === 'failed',
      error: null,
    },
    {
      id: 'synthesis',
      label: 'Voice Synthesis',
      status: video.synthesis_status,
      isProcessing: video.synthesis_status === 'synthesizing' || isLocallyProcessing('synthesis'),
      isCompleted: video.synthesis_status === 'synthesized',
      isFailed: video.synthesis_status === 'failed',
      error: null,
    },
    {
      id: 'final_video',
      label: 'Final Video Assembly',
      status: video.final_processed_video_url ? 'completed' : 'pending',
      isProcessing: (video.synthesis_status === 'synthesized' && !video.final_processed_video_url) || 
                    video.final_video_status === 'removing_audio' || 
                    video.final_video_status === 'combining_audio' || 
                    isLocallyProcessing('final_video'),
      isCompleted: !!video.final_processed_video_url,
      isFailed: false,
      error: null,
    },
    {
      id: 'cloudinary',
      label: 'Cloudinary Upload',
      status: video.cloudinary_url ? 'uploaded' : 'pending',
      isProcessing: isLocallyProcessing('cloudinary'),
      isCompleted: !!video.cloudinary_url,
      isFailed: false,
      error: null,
    },
    {
      id: 'sheets',
      label: 'Google Sheets Sync',
      status: video.google_sheets_synced ? 'synced' : 'pending',
      isProcessing: isLocallyProcessing('sheets'),
      isCompleted: video.google_sheets_synced,
      isFailed: false,
      error: null,
    }
  ];

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10 space-y-4">
      <h3 className="text-lg font-semibold text-white mb-2">Processing Status</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {steps.map((step, index) => {
          // Determine card styling based on state
          let cardClasses = "flex flex-col justify-between p-3 rounded-md border transition-all duration-300 relative overflow-hidden";
          
          if (step.isProcessing) {
            cardClasses += " bg-blue-500/10 border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.2)]";
          } else if (step.isFailed) {
            cardClasses += " bg-red-500/5 border-red-500/30";
          } else if (step.isCompleted) {
            cardClasses += " bg-green-500/5 border-green-500/20";
          } else {
            cardClasses += " bg-white/5 border-white/5 opacity-60";
          }

          return (
            <div key={step.id} className={cardClasses}>
              <div className="flex items-start gap-3 mb-3 relative z-10">
                {/* Status Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {step.isProcessing ? (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  ) : step.isCompleted ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : step.isFailed ? (
                    <XCircle className="w-5 h-5 text-red-400" />
                  ) : (
                    <Clock className="w-5 h-5 text-gray-500" />
                  )}
                </div>
                
                {/* Label & Status Text */}
                <div className="flex flex-col min-w-0">
                  <span className={`text-sm font-medium truncate ${
                    step.isCompleted ? 'text-white' : 
                    step.isProcessing ? 'text-blue-300' : 
                    step.isFailed ? 'text-red-300' : 'text-gray-400'
                  }`}>
                    {step.label}
                  </span>
                  <span className="text-xs text-gray-500 truncate">
                    {step.isProcessing ? 'Processing...' : 
                     step.isCompleted ? 'Completed' : 
                     step.isFailed ? 'Failed' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* Progress Bar for Processing State */}
              {step.isProcessing && (
                <div className="w-full h-1.5 bg-blue-900/30 rounded-full overflow-hidden mt-2 mb-1">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${localProgress}%` }}
                  />
                </div>
              )}

              {/* Action Buttons - Full width at bottom if failed */}
              {step.isFailed && (
                <div className="mt-auto pt-2 relative z-10">
                  <Button
                    size="sm"
                    variant="danger"
                    icon={RefreshCw}
                    onClick={() => onRetry(step.id)}
                    className="w-full justify-center"
                  >
                    Retry {step.label}
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
