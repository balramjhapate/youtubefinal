from django.db import models
from django.utils import timezone


class VideoDownload(models.Model):
    """Model to track video downloads from Xiaohongshu/RedNote"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    EXTRACTION_METHOD_CHOICES = [
        ('seekin', 'Seekin API'),
        ('yt-dlp', 'yt-dlp'),
        ('requests', 'Direct Requests'),
        ('local', 'Local Upload'),
    ]
    
    VIDEO_SOURCE_CHOICES = [
        ('rednote', 'RedNote/Xiaohongshu'),
        ('youtube', 'YouTube'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('vimeo', 'Vimeo'),
        ('local', 'Local Upload'),
        ('other', 'Other'),
    ]
    
    AI_PROCESSING_STATUS_CHOICES = [
        ('not_processed', 'Not Processed'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    TRANSCRIPTION_STATUS_CHOICES = [
        ('not_transcribed', 'Not Transcribed'),
        ('transcribing', 'Transcribing'),
        ('transcribed', 'Transcribed'),
        ('failed', 'Failed'),
    ]
    
    # Core fields
    url = models.URLField(max_length=500, blank=True, null=True, help_text="Original video URL (optional for local uploads)")
    video_id = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Unique Video ID")
    video_source = models.CharField(
        max_length=20,
        choices=VIDEO_SOURCE_CHOICES,
        default='rednote',
        help_text="Video source/platform"
    )
    
    # Content
    title = models.CharField(max_length=500, blank=True, help_text="English Title (Translated)")
    original_title = models.CharField(max_length=500, blank=True, help_text="Original Chinese Title")
    
    description = models.TextField(blank=True, help_text="English Description (Translated)")
    original_description = models.TextField(blank=True, help_text="Original Chinese Description")
    
    # Media
    video_url = models.URLField(max_length=1000, blank=True, help_text="Extracted video URL")
    cover_url = models.URLField(max_length=1000, blank=True, help_text="Cover/thumbnail URL")
    local_file = models.FileField(upload_to='videos/', blank=True, null=True, help_text="1. Downloaded video file (original with audio)")
    is_downloaded = models.BooleanField(default=False, help_text="Is video saved locally?")
    duration = models.FloatField(blank=True, null=True, help_text="Video duration in seconds")
    voice_removed_video = models.FileField(upload_to='videos/voice_removed/', blank=True, null=True, help_text="2. Video file after removing original audio (no audio)")
    voice_removed_video_url = models.URLField(max_length=1000, blank=True, help_text="2. Video URL after removing original audio (no audio)")
    final_processed_video = models.FileField(upload_to='videos/final/', blank=True, null=True, help_text="3. Final video file after TTS audio replacement (with new Hindi audio)")
    final_processed_video_url = models.URLField(max_length=1000, blank=True, help_text="3. Final video URL after TTS audio replacement (with new Hindi audio)")
    
    # Metadata
    extraction_method = models.CharField(
        max_length=20, 
        choices=EXTRACTION_METHOD_CHOICES, 
        blank=True,
        help_text="Which extraction method succeeded"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Extraction status"
    )
    error_message = models.TextField(blank=True, help_text="Error message if failed")
    
    # Video Extraction Timestamps
    extraction_started_at = models.DateTimeField(blank=True, null=True, help_text="When video extraction/download started")
    extraction_finished_at = models.DateTimeField(blank=True, null=True, help_text="When video extraction/download finished")
    
    # AI Processing
    ai_processing_status = models.CharField(
        max_length=20,
        choices=AI_PROCESSING_STATUS_CHOICES,
        default='not_processed',
        help_text="AI processing status"
    )
    ai_processing_started_at = models.DateTimeField(blank=True, null=True, help_text="When AI processing started")
    ai_processed_at = models.DateTimeField(blank=True, null=True, help_text="When AI processing was completed")
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary or analysis")
    ai_tags = models.CharField(max_length=500, blank=True, help_text="AI-generated tags (comma-separated)")
    ai_error_message = models.TextField(blank=True, help_text="AI processing error message if failed")
    
    # Transcription (NCA-based - legacy)
    transcription_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPTION_STATUS_CHOICES,
        default='not_transcribed',
        help_text="NCA Transcription status"
    )
    transcript = models.TextField(blank=True, help_text="NCA: Full transcript WITH timestamps (00:00:00 format)")
    transcript_without_timestamps = models.TextField(blank=True, help_text="NCA: Full transcript WITHOUT timestamps (plain text)")
    transcript_hindi = models.TextField(blank=True, help_text="NCA: Hindi translation of the transcript")
    transcript_language = models.CharField(max_length=10, blank=True, help_text="NCA: Detected language of transcript")
    transcript_started_at = models.DateTimeField(blank=True, null=True, help_text="When NCA transcription started")
    transcript_processed_at = models.DateTimeField(blank=True, null=True, help_text="When NCA transcription was completed")
    transcript_error_message = models.TextField(blank=True, help_text="NCA: Transcription error message if failed")
    
    # Whisper Transcription (new - for comparison)
    whisper_transcription_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPTION_STATUS_CHOICES,
        default='not_transcribed',
        help_text="Whisper Transcription status"
    )
    whisper_transcript = models.TextField(blank=True, help_text="Whisper: Full transcript WITH timestamps (00:00:00 format)")
    whisper_transcript_without_timestamps = models.TextField(blank=True, help_text="Whisper: Full transcript WITHOUT timestamps (plain text)")
    whisper_transcript_hindi = models.TextField(blank=True, help_text="Whisper: Hindi translation of the transcript")
    whisper_transcript_language = models.CharField(max_length=10, blank=True, help_text="Whisper: Detected language (ISO code)")
    whisper_transcript_segments = models.JSONField(blank=True, null=True, help_text="Whisper: Raw segments with timestamps and confidence scores")
    whisper_transcript_started_at = models.DateTimeField(blank=True, null=True, help_text="When Whisper transcription started")
    whisper_transcript_processed_at = models.DateTimeField(blank=True, null=True, help_text="When Whisper transcription was completed")
    whisper_transcript_error_message = models.TextField(blank=True, help_text="Whisper: Transcription error message if failed")
    whisper_model_used = models.CharField(max_length=20, blank=True, help_text="Whisper model size used (tiny/base/small/medium/large)")
    whisper_confidence_avg = models.FloatField(blank=True, null=True, help_text="Whisper: Average confidence score across all segments")
    
    # Visual Transcription (for videos without audio - uses Gemini Vision API)
    has_audio = models.BooleanField(default=True, help_text="Whether video contains audio track")
    visual_transcript = models.TextField(blank=True, help_text="Visual: Frame-by-frame description WITH timestamps (HH:MM:SS format)")
    visual_transcript_without_timestamps = models.TextField(blank=True, help_text="Visual: Frame-by-frame description WITHOUT timestamps (plain text)")
    visual_transcript_hindi = models.TextField(blank=True, help_text="Visual: Hindi translation of visual description")
    visual_transcript_segments = models.JSONField(blank=True, null=True, help_text="Visual: Raw segments with timestamps and descriptions")
    visual_transcript_started_at = models.DateTimeField(blank=True, null=True, help_text="When visual transcription started")
    visual_transcript_finished_at = models.DateTimeField(blank=True, null=True, help_text="When visual transcription finished")
    
    # AI-Enhanced Transcription (merges Whisper + NCA + Visual using AI)
    enhanced_transcript = models.TextField(blank=True, help_text="Enhanced: AI-merged transcript WITH timestamps (HH:MM:SS format) - combines Whisper, NCA, and Visual")
    enhanced_transcript_without_timestamps = models.TextField(blank=True, help_text="Enhanced: AI-merged transcript WITHOUT timestamps (plain text)")
    enhanced_transcript_hindi = models.TextField(blank=True, help_text="Enhanced: Hindi translation of enhanced transcript")
    enhanced_transcript_segments = models.JSONField(blank=True, null=True, help_text="Enhanced: Raw segments with timestamps from AI enhancement")
    enhanced_transcript_started_at = models.DateTimeField(blank=True, null=True, help_text="When enhanced transcript generation started")
    enhanced_transcript_finished_at = models.DateTimeField(blank=True, null=True, help_text="When enhanced transcript generation finished")
    
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, help_text="When the download was requested")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update time")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Video Download"
        verbose_name_plural = "Video Downloads"
    
    def __str__(self):
        return f"{self.title[:50] if self.title else 'Untitled'} - {self.status}"
    
    @property
    def is_successful(self):
        """Check if extraction was successful"""
        return self.status == 'success'
    
    @property
    def is_ai_processed(self):
        """Check if AI processing is completed"""
        return self.ai_processing_status == 'processed'

    # Audio Synthesis
    SYNTHESIS_STATUS_CHOICES = [
        ('not_synthesized', 'Not Synthesized'),
        ('synthesizing', 'Synthesizing'),
        ('synthesized', 'Synthesized'),
        ('failed', 'Failed'),
    ]

    synthesis_status = models.CharField(
        max_length=20,
        choices=SYNTHESIS_STATUS_CHOICES,
        default='not_synthesized',
        help_text="Audio synthesis status"
    )
    synthesis_error = models.TextField(blank=True, help_text="Synthesis error message if failed")
    synthesized_audio = models.FileField(upload_to='synthesized_audio/', blank=True, null=True, help_text="Synthesized audio file")
    synthesis_started_at = models.DateTimeField(blank=True, null=True, help_text="When audio synthesis started")
    synthesized_at = models.DateTimeField(blank=True, null=True, help_text="When audio synthesis finished")
    voice_profile = models.ForeignKey('ClonedVoice', on_delete=models.SET_NULL, null=True, blank=True, help_text="Voice profile used for synthesis")
    
    # Final Video Assembly (audio removal + combining with TTS)
    FINAL_VIDEO_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('removing_audio', 'Removing Audio'),
        ('combining_audio', 'Combining Audio'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    final_video_status = models.CharField(
        max_length=20,
        choices=FINAL_VIDEO_STATUS_CHOICES,
        default='not_started',
        help_text="Final video assembly status"
    )
    final_video_error = models.TextField(blank=True, help_text="Final video assembly error message if failed")
    final_video_started_at = models.DateTimeField(blank=True, null=True, help_text="When final video assembly started")
    final_video_finished_at = models.DateTimeField(blank=True, null=True, help_text="When final video assembly finished")
    
    # Hindi Script Generation
    SCRIPT_STATUS_CHOICES = [
        ('not_generated', 'Not Generated'),
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
    ]
    
    script_status = models.CharField(
        max_length=20,
        choices=SCRIPT_STATUS_CHOICES,
        default='not_generated',
        help_text="Hindi script generation status"
    )
    hindi_script = models.TextField(blank=True, help_text="AI-generated Hindi script for TTS")
    script_error_message = models.TextField(blank=True, help_text="Script generation error message if failed")
    script_started_at = models.DateTimeField(blank=True, null=True, help_text="When script generation started")
    script_generated_at = models.DateTimeField(blank=True, null=True, help_text="When script generation finished")
    script_edited = models.BooleanField(default=False, help_text="Whether script was manually edited by user")
    script_edited_at = models.DateTimeField(blank=True, null=True, help_text="When script was last edited")
    
    # TTS Parameters (calculated based on duration)
    tts_speed = models.FloatField(default=1.0, help_text="TTS speed multiplier (calculated from duration)")
    tts_temperature = models.FloatField(default=0.75, help_text="TTS temperature parameter")
    tts_repetition_penalty = models.FloatField(default=5.0, help_text="TTS repetition penalty")
    
    # Video Review Status
    REVIEW_STATUS_CHOICES = [
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('needs_revision', 'Needs Revision'),
        ('rejected', 'Rejected'),
    ]
    
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending_review',
        help_text="Review status of final processed video"
    )
    review_notes = models.TextField(blank=True, help_text="Review notes or feedback")
    reviewed_at = models.DateTimeField(blank=True, null=True, help_text="When video was reviewed")
    
    # Cloudinary Upload
    cloudinary_url = models.URLField(max_length=1000, blank=True, help_text="Cloudinary URL for final processed video")
    cloudinary_upload_started_at = models.DateTimeField(blank=True, null=True, help_text="When Cloudinary upload started")
    cloudinary_uploaded_at = models.DateTimeField(blank=True, null=True, help_text="When Cloudinary upload finished")
    
    # Generated Metadata (for Google Sheets)
    generated_title = models.CharField(max_length=500, blank=True, help_text="AI-generated title for video")
    generated_description = models.TextField(blank=True, help_text="AI-generated description for video")
    generated_tags = models.CharField(max_length=1000, blank=True, help_text="AI-generated tags (comma-separated)")
    google_sheets_synced = models.BooleanField(default=False, help_text="Whether data has been synced to Google Sheets")
    google_sheets_sync_started_at = models.DateTimeField(blank=True, null=True, help_text="When Google Sheets sync started")
    google_sheets_synced_at = models.DateTimeField(blank=True, null=True, help_text="When Google Sheets sync finished")

