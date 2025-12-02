# Generated migration for analysis provider settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0002_add_frame_extraction_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiprovidersettings',
            name='enable_nca_transcription',
            field=models.BooleanField(default=True, help_text='Enable NCA Toolkit transcription (fast API-based transcription)'),
        ),
        migrations.AddField(
            model_name='aiprovidersettings',
            name='enable_whisper_transcription',
            field=models.BooleanField(default=True, help_text='Enable Whisper transcription (local model-based transcription)'),
        ),
        migrations.AddField(
            model_name='aiprovidersettings',
            name='enable_visual_analysis',
            field=models.BooleanField(default=False, help_text='Enable Visual Analysis (frame-by-frame analysis using AI Vision)'),
        ),
    ]

