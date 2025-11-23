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
    
    # Core fields
    url = models.URLField(max_length=500, help_text="Original Xiaohongshu URL")
    video_id = models.CharField(max_length=100, blank=True, unique=True, help_text="Unique Video ID from XHS")
    
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
