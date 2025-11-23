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
    url = models.URLField(max_length=500, help_text="Original Xiaohongshu URL")
    video_id = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Unique Video ID from XHS")
    
    # Content
    title = models.CharField(max_length=500, blank=True, help_text="English Title (Translated)")
    original_title = models.CharField(max_length=500, blank=True, help_text="Original Chinese Title")
    
    description = models.TextField(blank=True, help_text="English Description (Translated)")
    original_description = models.TextField(blank=True, help_text="Original Chinese Description")
    
    # Media
    video_url = models.URLField(max_length=1000, blank=True, help_text="Extracted video URL")
    cover_url = models.URLField(max_length=1000, blank=True, help_text="Cover/thumbnail URL")
    local_file = models.FileField(upload_to='videos/', blank=True, null=True, help_text="Locally downloaded video file")
    is_downloaded = models.BooleanField(default=False, help_text="Is video saved locally?")
    
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
    
    # AI Processing
    ai_processing_status = models.CharField(
        max_length=20,
        choices=AI_PROCESSING_STATUS_CHOICES,
        default='not_processed',
        help_text="AI processing status"
    )
    ai_processed_at = models.DateTimeField(blank=True, null=True, help_text="When AI processing was completed")
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary or analysis")
    ai_tags = models.CharField(max_length=500, blank=True, help_text="AI-generated tags (comma-separated)")
    ai_error_message = models.TextField(blank=True, help_text="AI processing error message if failed")
    
    # Transcription
    transcription_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPTION_STATUS_CHOICES,
        default='not_transcribed',
        help_text="Transcription status"
    )
    transcript = models.TextField(blank=True, help_text="Full transcript of video speech/audio")
    transcript_language = models.CharField(max_length=10, blank=True, help_text="Detected language of transcript")
    transcript_started_at = models.DateTimeField(blank=True, null=True, help_text="When transcription started")
    transcript_processed_at = models.DateTimeField(blank=True, null=True, help_text="When transcription was completed")
    transcript_error_message = models.TextField(blank=True, help_text="Transcription error message if failed")
    
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
