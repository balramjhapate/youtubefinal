# Generated manually for Whisper transcription fields
# Run: python3 manage.py migrate downloader

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0028_add_multi_provider_support'),
    ]

    operations = [
        # Update existing transcription field help texts to indicate NCA
        migrations.AlterField(
            model_name='videodownload',
            name='transcription_status',
            field=models.CharField(
                choices=[('not_transcribed', 'Not Transcribed'), ('transcribing', 'Transcribing'), ('transcribed', 'Transcribed'), ('failed', 'Failed')],
                default='not_transcribed',
                help_text='NCA Transcription status',
                max_length=20
            ),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript',
            field=models.TextField(blank=True, help_text='NCA: Full transcript WITH timestamps (00:00:00 format)'),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_without_timestamps',
            field=models.TextField(blank=True, help_text='NCA: Full transcript WITHOUT timestamps (plain text)'),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_hindi',
            field=models.TextField(blank=True, help_text='NCA: Hindi translation of the transcript'),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_language',
            field=models.CharField(blank=True, help_text='NCA: Detected language of transcript', max_length=10),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_started_at',
            field=models.DateTimeField(blank=True, help_text='When NCA transcription started', null=True),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_processed_at',
            field=models.DateTimeField(blank=True, help_text='When NCA transcription was completed', null=True),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='transcript_error_message',
            field=models.TextField(blank=True, help_text='NCA: Transcription error message if failed'),
        ),
        
        # Add new Whisper transcription fields
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcription_status',
            field=models.CharField(
                choices=[('not_transcribed', 'Not Transcribed'), ('transcribing', 'Transcribing'), ('transcribed', 'Transcribed'), ('failed', 'Failed')],
                default='not_transcribed',
                help_text='Whisper Transcription status',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript',
            field=models.TextField(blank=True, help_text='Whisper: Full transcript WITH timestamps (00:00:00 format)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_without_timestamps',
            field=models.TextField(blank=True, help_text='Whisper: Full transcript WITHOUT timestamps (plain text)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_hindi',
            field=models.TextField(blank=True, help_text='Whisper: Hindi translation of the transcript'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_language',
            field=models.CharField(blank=True, help_text='Whisper: Detected language (ISO code)', max_length=10),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_segments',
            field=models.JSONField(blank=True, help_text='Whisper: Raw segments with timestamps and confidence scores', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_started_at',
            field=models.DateTimeField(blank=True, help_text='When Whisper transcription started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_processed_at',
            field=models.DateTimeField(blank=True, help_text='When Whisper transcription was completed', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcript_error_message',
            field=models.TextField(blank=True, help_text='Whisper: Transcription error message if failed'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_model_used',
            field=models.CharField(blank=True, help_text='Whisper model size used (tiny/base/small/medium/large)', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='whisper_confidence_avg',
            field=models.FloatField(blank=True, help_text='Whisper: Average confidence score across all segments', null=True),
        ),
    ]
