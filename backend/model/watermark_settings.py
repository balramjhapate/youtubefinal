from django.db import models


class WatermarkSettings(models.Model):
    """Store watermark configuration for videos."""
    enabled = models.BooleanField(default=False, help_text="Enable watermark on videos")
    watermark_text = models.CharField(max_length=100, blank=True, default='', help_text="Watermark text to display on videos")
    font_size = models.IntegerField(default=24, help_text="Font size for watermark text")
    font_color = models.CharField(max_length=20, default='white', help_text="Font color (e.g., 'white', 'black', '#FFFFFF')")
    position_change_interval = models.FloatField(default=1.0, help_text="Position change interval in seconds (how often watermark moves)")
    opacity = models.FloatField(default=0.7, help_text="Watermark opacity (0.0 to 1.0)")
    
    class Meta:
        app_label = 'downloader'
        verbose_name = "Watermark Setting"
        verbose_name_plural = "Watermark Settings"
    
    def __str__(self):
        return f"Watermark settings ({'enabled' if self.enabled else 'disabled'})"

