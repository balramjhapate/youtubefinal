from django.db import models


class AIProviderSettings(models.Model):
    """Store AI provider API keys for all supported providers."""
    
    # Separate API key for each provider
    gemini_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Google Gemini API Key (for TTS, enhancement, etc.)"
    )
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="OpenAI API Key (GPT models)"
    )
    anthropic_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Anthropic API Key (Claude models)"
    )
    
    # Provider selection
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic (Claude)'),
    ]
    
    # Dual default providers for different tasks
    script_generation_provider = models.CharField(
        max_length=50, 
        choices=PROVIDER_CHOICES, 
        default='gemini',
        help_text="AI provider for Hindi script generation"
    )
    default_provider = models.CharField(
        max_length=50, 
        choices=PROVIDER_CHOICES, 
        default='gemini',
        help_text="Default AI provider for general tasks (enhancement, TTS markup, etc.)"
    )
    
    # Analysis Provider Enable/Disable Settings
    enable_nca_transcription = models.BooleanField(
        default=True,
        help_text="Enable NCA Toolkit transcription (fast API-based transcription)"
    )
    enable_whisper_transcription = models.BooleanField(
        default=True,
        help_text="Enable Whisper transcription (local model-based transcription)"
    )
    enable_visual_analysis = models.BooleanField(
        default=False,
        help_text="Enable Visual Analysis (frame-by-frame analysis using AI Vision)"
    )
    
    # Visual Analysis Provider Selection
    visual_analysis_provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='openai',
        help_text="AI provider for visual analysis (OpenAI GPT-4o-mini or Gemini Vision)"
    )
    
    # Legacy fields for backward compatibility (deprecated)
    provider = models.CharField(
        max_length=50, 
        choices=PROVIDER_CHOICES, 
        default='gemini',
        help_text="[DEPRECATED] Use script_generation_provider or default_provider instead"
    )
    api_key = models.CharField(
        max_length=255, 
        blank=True,
        help_text="[DEPRECATED] Use provider-specific API keys instead"
    )

    class Meta:
        app_label = 'downloader'
        verbose_name = "AI Provider Setting"
        verbose_name_plural = "AI Provider Settings"

    def __str__(self):
        return f"AI Provider Settings (Script: {self.script_generation_provider}, General: {self.default_provider})"
    
    def get_api_key(self, provider=None):
        """Get API key for specified provider, or use default provider."""
        if provider is None:
            provider = self.default_provider
        return getattr(self, f'{provider}_api_key', '') or self.api_key  # Fallback to legacy

