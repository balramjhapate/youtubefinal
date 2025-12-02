from django.db import models


class CloudinarySettings(models.Model):
    """Store Cloudinary configuration for video uploads."""
    cloud_name = models.CharField(max_length=255, blank=True, help_text="Cloudinary cloud name")
    api_key = models.CharField(max_length=255, blank=True, help_text="Cloudinary API key")
    api_secret = models.CharField(max_length=255, blank=True, help_text="Cloudinary API secret")
    enabled = models.BooleanField(default=False, help_text="Enable Cloudinary uploads")

    class Meta:
        app_label = 'downloader'
        verbose_name = "Cloudinary Setting"
        verbose_name_plural = "Cloudinary Settings"

    def __str__(self):
        return f"Cloudinary settings ({'enabled' if self.enabled else 'disabled'})"

