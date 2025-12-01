from django.db import models


class GoogleSheetsSettings(models.Model):
    """Store Google Sheets configuration for tracking."""
    spreadsheet_id = models.CharField(max_length=255, blank=True, help_text="Google Sheets spreadsheet ID")
    sheet_name = models.CharField(max_length=255, default='Sheet1', help_text="Sheet name to write data to")
    credentials_json = models.TextField(blank=True, help_text="Google Service Account JSON credentials")
    enabled = models.BooleanField(default=False, help_text="Enable Google Sheets tracking")

    class Meta:
        verbose_name = "Google Sheets Setting"
        verbose_name_plural = "Google Sheets Settings"

    def __str__(self):
        return f"Google Sheets settings ({'enabled' if self.enabled else 'disabled'})"

