"""
Pipeline Manager - Enforces strict processing order and auto-progression

This module manages the video processing pipeline, ensuring steps are executed
in the correct order and automatically triggering the next step when a step completes.
"""

from django.utils import timezone
from model import VideoDownload, AIProviderSettings
from downloader.websocket_utils import broadcast_video_update
import logging

logger = logging.getLogger(__name__)

# Define the strict pipeline order
PIPELINE_STEPS = [
    {
        'id': 'download',
        'name': 'Video Download',
        'check_complete': lambda v: v.is_downloaded,
        'check_processing': lambda v: False,  # Download is handled separately
        'next_step': 'frame_extraction'
    },
    {
        'id': 'frame_extraction',
        'name': 'Frame Extraction',
        'check_complete': lambda v: v.frames_extracted,
        'check_processing': lambda v: False,  # Frame extraction is automatic
        'next_step': 'visual_analysis'
    },
    {
        'id': 'visual_analysis',
        'name': 'Visual Analysis',
        'check_complete': lambda v: bool(v.visual_transcript),
        'check_processing': lambda v: bool(v.visual_transcript_started_at) and not bool(v.visual_transcript_finished_at),
        'next_step': 'transcription'
    },
    {
        'id': 'transcription',
        'name': 'Transcription',
        'check_complete': lambda v: v.transcription_status == 'transcribed' or v.whisper_transcription_status == 'transcribed',
        'check_processing': lambda v: v.transcription_status == 'transcribing' or v.whisper_transcription_status == 'transcribing',
        'next_step': 'ai_processing'
    },
    {
        'id': 'ai_processing',
        'name': 'AI Processing & Enhanced Transcript',
        'check_complete': lambda v: v.ai_processing_status == 'processed' and bool(v.enhanced_transcript),
        'check_processing': lambda v: v.ai_processing_status == 'processing',
        'next_step': 'script_generation'
    },
    {
        'id': 'script_generation',
        'name': 'Hindi Script Generation',
        'check_complete': lambda v: v.script_status == 'generated',
        'check_processing': lambda v: v.script_status == 'generating',
        'next_step': 'synthesis'
    },
    {
        'id': 'synthesis',
        'name': 'Voice Synthesis',
        'check_complete': lambda v: v.synthesis_status == 'synthesized',
        'check_processing': lambda v: v.synthesis_status == 'synthesizing',
        'next_step': 'final_video'
    },
    {
        'id': 'final_video',
        'name': 'Final Video Assembly',
        'check_complete': lambda v: bool(v.final_processed_video_url),
        'check_processing': lambda v: v.final_video_status in ['removing_audio', 'combining_audio'],
        'next_step': 'cloudinary_upload'
    },
    {
        'id': 'cloudinary_upload',
        'name': 'Cloudinary Upload',
        'check_complete': lambda v: bool(v.cloudinary_url),
        'check_processing': lambda v: bool(v.cloudinary_upload_started_at) and not bool(v.cloudinary_uploaded_at),
        'next_step': 'google_sheets_sync'
    },
    {
        'id': 'google_sheets_sync',
        'name': 'Google Sheets Sync',
        'check_complete': lambda v: v.google_sheets_synced,
        'check_processing': lambda v: bool(v.google_sheets_sync_started_at) and not bool(v.google_sheets_synced_at),
        'next_step': None  # Last step
    }
]


def get_current_step(video):
    """
    Get the current step in the pipeline for a video.
    
    Returns:
        dict: Current step info, or None if all steps are complete
    """
    for step in PIPELINE_STEPS:
        if not step['check_complete'](video):
            return step
    return None


def get_next_step(step_id):
    """
    Get the next step after the given step.
    
    Args:
        step_id: ID of the current step
        
    Returns:
        dict: Next step info, or None if this is the last step
    """
    for i, step in enumerate(PIPELINE_STEPS):
        if step['id'] == step_id:
            if i + 1 < len(PIPELINE_STEPS):
                return PIPELINE_STEPS[i + 1]
            return None
    return None


def can_proceed_to_step(video, step_id):
    """
    Check if a video can proceed to a specific step.
    All previous steps must be complete.
    
    Args:
        video: VideoDownload instance
        step_id: ID of the step to check
        
    Returns:
        bool: True if can proceed, False otherwise
    """
    for step in PIPELINE_STEPS:
        if step['id'] == step_id:
            return True  # Found the step, all previous steps are checked
        if not step['check_complete'](video):
            return False  # Previous step not complete
    return False


def get_pipeline_status(video):
    """
    Get comprehensive pipeline status for a video.
    
    Returns:
        dict: {
            'current_step': dict or None,
            'completed_steps': list,
            'pending_steps': list,
            'failed_steps': list,
            'progress_percentage': float
        }
    """
    completed_steps = []
    pending_steps = []
    failed_steps = []
    current_step = None
    
    for step in PIPELINE_STEPS:
        if step['check_complete'](video):
            completed_steps.append(step['id'])
        elif step['check_processing'](video):
            current_step = step
            pending_steps.append(step['id'])
        else:
            # Check if step has failed
            if step['id'] == 'transcription' and video.transcription_status == 'failed':
                failed_steps.append(step['id'])
            elif step['id'] == 'ai_processing' and video.ai_processing_status == 'failed':
                failed_steps.append(step['id'])
            elif step['id'] == 'script_generation' and video.script_status == 'failed':
                failed_steps.append(step['id'])
            elif step['id'] == 'synthesis' and video.synthesis_status == 'failed':
                failed_steps.append(step['id'])
            else:
                pending_steps.append(step['id'])
    
    if not current_step:
        # Find first incomplete step
        for step in PIPELINE_STEPS:
            if not step['check_complete'](video):
                current_step = step
                break
    
    total_steps = len(PIPELINE_STEPS)
    completed_count = len(completed_steps)
    progress_percentage = (completed_count / total_steps) * 100 if total_steps > 0 else 0
    
    return {
        'current_step': current_step,
        'completed_steps': completed_steps,
        'pending_steps': pending_steps,
        'failed_steps': failed_steps,
        'progress_percentage': progress_percentage,
        'total_steps': total_steps,
        'completed_count': completed_count
    }


def auto_trigger_next_step(video_id, completed_step_id):
    """
    Automatically trigger the next step in the pipeline after a step completes.
    
    Args:
        video_id: ID of the video
        completed_step_id: ID of the step that just completed
        
    Returns:
        bool: True if next step was triggered, False otherwise
    """
    try:
        video = VideoDownload.objects.get(pk=video_id)
        next_step = get_next_step(completed_step_id)
        
        if not next_step:
            logger.info(f"Video {video_id}: No next step after {completed_step_id}")
            return False
        
        # Check if next step is already complete
        if next_step['check_complete'](video):
            logger.info(f"Video {video_id}: Next step {next_step['id']} already complete")
            return False
        
        # Check if next step is already processing
        if next_step['check_processing'](video):
            logger.info(f"Video {video_id}: Next step {next_step['id']} already processing")
            return False
        
        logger.info(f"Video {video_id}: Auto-triggering next step: {next_step['id']}")
        
        # Trigger the next step by calling processing functions directly
        # We use threading to avoid blocking and to properly handle the request context
        import threading
        from django.test import RequestFactory
        from controller.api_views import VideoDownloadViewSet
        
        def trigger_next_step():
            """Background thread to trigger next step"""
            try:
                # Create a mock request for the ViewSet
                factory = RequestFactory()
                request = factory.post(f'/api/videos/{video_id}/{next_step["id"]}/')
                
                # Create ViewSet instance and set up context
                viewset = VideoDownloadViewSet()
                viewset.kwargs = {'pk': video_id}
                viewset.request = request
                viewset.format_kwarg = None
                
                # Trigger the next step based on its ID
                if next_step['id'] == 'visual_analysis':
                    # Visual analysis requires manual trigger (button), so skip
                    logger.info(f"Video {video_id}: Visual analysis requires manual trigger, skipping auto-trigger")
                    return False
                elif next_step['id'] == 'transcription':
                    # Check if transcription is enabled
                    settings_obj = AIProviderSettings.objects.first()
                    if settings_obj and (settings_obj.enable_nca_transcription or settings_obj.enable_whisper_transcription):
                        viewset.transcribe(request, pk=video_id)
                        return True
                elif next_step['id'] == 'ai_processing':
                    viewset.process_ai(request, pk=video_id)
                    return True
                elif next_step['id'] == 'script_generation':
                    # Script generation happens automatically during transcription/AI processing
                    # No separate endpoint needed
                    logger.info(f"Video {video_id}: Script generation will happen automatically after AI processing")
                    return False
                elif next_step['id'] == 'synthesis':
                    # Use synthesize_tts endpoint if available, otherwise skip
                    if hasattr(viewset, 'synthesize_tts'):
                        viewset.synthesize_tts(request, pk=video_id)
                        return True
                    else:
                        logger.info(f"Video {video_id}: Synthesis endpoint not available, skipping auto-trigger")
                        return False
                elif next_step['id'] == 'final_video':
                    # Trigger final video generation
                    if hasattr(viewset, 'generate_final_video'):
                        viewset.generate_final_video(request, pk=video_id)
                        return True
                    else:
                        logger.warning(f"Video {video_id}: generate_final_video endpoint not available")
                        return False
                elif next_step['id'] == 'cloudinary_upload':
                    # Cloudinary upload happens automatically during final video generation
                    logger.info(f"Video {video_id}: Cloudinary upload will happen automatically during final video generation")
                    return False
                elif next_step['id'] == 'google_sheets_sync':
                    # Google Sheets sync happens automatically during final video generation
                    logger.info(f"Video {video_id}: Google Sheets sync will happen automatically during final video generation")
                    return False
            except Exception as e:
                logger.error(f"Error in trigger_next_step thread for video {video_id}: {e}")
                import traceback
                traceback.print_exc()
        
        # Start background thread to trigger next step
        thread = threading.Thread(target=trigger_next_step, daemon=True)
        thread.start()
        
        return True
        
        return False
    except VideoDownload.DoesNotExist:
        logger.error(f"Video {video_id} not found for auto-trigger")
        return False
    except Exception as e:
        logger.error(f"Error auto-triggering next step for video {video_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

