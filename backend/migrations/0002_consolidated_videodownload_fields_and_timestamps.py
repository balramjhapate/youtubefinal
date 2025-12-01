# Generated manually - Consolidated VideoDownload migration
# This migration consolidates all VideoDownload field additions and adds timestamp fields
# for all processing steps (started_at and finished_at)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0001_initial'),
    ]

    operations = [
        # Core Content Fields (from 0002)
        migrations.AddField(
            model_name='videodownload',
            name='description',
            field=models.TextField(blank=True, help_text='English Description (Translated)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='is_downloaded',
            field=models.BooleanField(default=False, help_text='Is video saved locally?'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='local_file',
            field=models.FileField(blank=True, help_text='Locally downloaded video file', null=True, upload_to='videos/'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='original_description',
            field=models.TextField(blank=True, help_text='Original Chinese Description'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='original_title',
            field=models.CharField(blank=True, help_text='Original Chinese Title', max_length=500),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='status',
            field=models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('pending', 'Pending')], default='pending', help_text='Extraction status', max_length=20),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='title',
            field=models.CharField(blank=True, help_text='English Title (Translated)', max_length=500),
        ),
        
        # Video ID alteration (from 0003)
        migrations.AlterField(
            model_name='videodownload',
            name='video_id',
            field=models.CharField(blank=True, help_text='Unique Video ID from XHS', max_length=100, null=True, unique=True),
        ),
        
        # AI Processing Fields (from 0004)
        migrations.AddField(
            model_name='videodownload',
            name='ai_error_message',
            field=models.TextField(blank=True, help_text='AI processing error message if failed'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='ai_processed_at',
            field=models.DateTimeField(blank=True, help_text='When AI processing was completed', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='ai_processing_status',
            field=models.CharField(choices=[('not_processed', 'Not Processed'), ('processing', 'Processing'), ('processed', 'Processed'), ('failed', 'Failed')], default='not_processed', help_text='AI processing status', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='ai_summary',
            field=models.TextField(blank=True, help_text='AI-generated summary or analysis'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='ai_tags',
            field=models.CharField(blank=True, help_text='AI-generated tags (comma-separated)', max_length=500),
        ),
        
        # Transcription Fields (from 0005, 0006, 0007, 0008, 0019)
        migrations.AddField(
            model_name='videodownload',
            name='transcription_status',
            field=models.CharField(choices=[('not_transcribed', 'Not Transcribed'), ('transcribing', 'Transcribing'), ('transcribed', 'Transcribed'), ('failed', 'Failed')], default='not_transcribed', help_text='NCA Transcription status', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript',
            field=models.TextField(blank=True, help_text='NCA: Full transcript WITH timestamps (00:00:00 format)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_without_timestamps',
            field=models.TextField(blank=True, help_text='NCA: Full transcript WITHOUT timestamps (plain text)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_hindi',
            field=models.TextField(blank=True, help_text='NCA: Hindi translation of the transcript'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_language',
            field=models.CharField(blank=True, help_text='NCA: Detected language of transcript', max_length=10),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_started_at',
            field=models.DateTimeField(blank=True, help_text='When NCA transcription started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_processed_at',
            field=models.DateTimeField(blank=True, help_text='When NCA transcription was completed', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='transcript_error_message',
            field=models.TextField(blank=True, help_text='NCA: Transcription error message if failed'),
        ),
        
        # Audio Synthesis Fields (from 0013)
        migrations.AddField(
            model_name='videodownload',
            name='synthesis_error',
            field=models.TextField(blank=True, help_text='Synthesis error message if failed'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='synthesis_status',
            field=models.CharField(choices=[('not_synthesized', 'Not Synthesized'), ('synthesizing', 'Synthesizing'), ('synthesized', 'Synthesized'), ('failed', 'Failed')], default='not_synthesized', help_text='Audio synthesis status', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='synthesized_audio',
            field=models.FileField(blank=True, help_text='Synthesized audio file', null=True, upload_to='synthesized_audio/'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='synthesized_at',
            field=models.DateTimeField(blank=True, help_text='When audio synthesis finished', null=True),
        ),
        
        # Duration and Script Fields (from 0014)
        migrations.AddField(
            model_name='videodownload',
            name='duration',
            field=models.FloatField(blank=True, help_text='Video duration in seconds', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='hindi_script',
            field=models.TextField(blank=True, help_text='AI-generated Hindi script for TTS'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='script_error_message',
            field=models.TextField(blank=True, help_text='Script generation error message if failed'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='script_generated_at',
            field=models.DateTimeField(blank=True, help_text='When script generation finished', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='script_status',
            field=models.CharField(choices=[('not_generated', 'Not Generated'), ('generating', 'Generating'), ('generated', 'Generated'), ('failed', 'Failed')], default='not_generated', help_text='Hindi script generation status', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='tts_repetition_penalty',
            field=models.FloatField(default=5.0, help_text='TTS repetition penalty'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='tts_speed',
            field=models.FloatField(default=1.0, help_text='TTS speed multiplier (calculated from duration)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='tts_temperature',
            field=models.FloatField(default=0.75, help_text='TTS temperature parameter'),
        ),
        
        # Video Source Fields (from 0015)
        migrations.AddField(
            model_name='videodownload',
            name='video_source',
            field=models.CharField(choices=[('rednote', 'RedNote/Xiaohongshu'), ('youtube', 'YouTube'), ('facebook', 'Facebook'), ('instagram', 'Instagram'), ('vimeo', 'Vimeo'), ('local', 'Local Upload'), ('other', 'Other')], default='rednote', help_text='Video source/platform', max_length=20),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='extraction_method',
            field=models.CharField(blank=True, choices=[('seekin', 'Seekin API'), ('yt-dlp', 'yt-dlp'), ('requests', 'Direct Requests'), ('local', 'Local Upload')], help_text='Which extraction method succeeded', max_length=20),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='url',
            field=models.URLField(blank=True, help_text='Original video URL (optional for local uploads)', max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='videodownload',
            name='video_id',
            field=models.CharField(blank=True, help_text='Unique Video ID', max_length=100, null=True, unique=True),
        ),
        
        # Final Processed Video Fields (from 0016, 0017, 0018)
        migrations.AddField(
            model_name='videodownload',
            name='final_processed_video',
            field=models.FileField(blank=True, help_text='3. Final video file after TTS audio replacement (with new Hindi audio)', null=True, upload_to='videos/final/'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='final_processed_video_url',
            field=models.URLField(blank=True, help_text='3. Final video URL after TTS audio replacement (with new Hindi audio)', max_length=1000),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='voice_removed_video',
            field=models.FileField(blank=True, help_text='2. Video file after removing original audio (no audio)', null=True, upload_to='videos/voice_removed/'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='voice_removed_video_url',
            field=models.URLField(blank=True, help_text='2. Video URL after removing original audio (no audio)', max_length=1000),
        ),
        
        # Review Status Fields (from 0020)
        migrations.AddField(
            model_name='videodownload',
            name='review_status',
            field=models.CharField(choices=[('pending_review', 'Pending Review'), ('approved', 'Approved'), ('needs_revision', 'Needs Revision'), ('rejected', 'Rejected')], default='pending_review', help_text='Review status of final processed video', max_length=20),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='review_notes',
            field=models.TextField(blank=True, help_text='Review notes or feedback'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, help_text='When video was reviewed', null=True),
        ),
        
        # Enhanced Transcript Fields (from 0023)
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript',
            field=models.TextField(blank=True, help_text='Enhanced: AI-merged transcript WITH timestamps (HH:MM:SS format) - combines Whisper, NCA, and Visual'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript_hindi',
            field=models.TextField(blank=True, help_text='Enhanced: Hindi translation of enhanced transcript'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript_segments',
            field=models.JSONField(blank=True, help_text='Enhanced: Raw segments with timestamps from AI enhancement', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript_without_timestamps',
            field=models.TextField(blank=True, help_text='Enhanced: AI-merged transcript WITHOUT timestamps (plain text)'),
        ),
        
        # Final Video Status Fields (from 0026)
        migrations.AddField(
            model_name='videodownload',
            name='final_video_error',
            field=models.TextField(blank=True, help_text='Final video assembly error message if failed'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='final_video_status',
            field=models.CharField(choices=[('not_started', 'Not Started'), ('removing_audio', 'Removing Audio'), ('combining_audio', 'Combining Audio'), ('completed', 'Completed'), ('failed', 'Failed')], default='not_started', help_text='Final video assembly status', max_length=20),
        ),
        
        # Script Edited Fields (from 0027)
        migrations.AddField(
            model_name='videodownload',
            name='script_edited',
            field=models.BooleanField(default=False, help_text='Whether script was manually edited by user'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='script_edited_at',
            field=models.DateTimeField(blank=True, help_text='When script was last edited', null=True),
        ),
        
        # Whisper Transcription Fields (from 0029)
        migrations.AddField(
            model_name='videodownload',
            name='whisper_transcription_status',
            field=models.CharField(choices=[('not_transcribed', 'Not Transcribed'), ('transcribing', 'Transcribing'), ('transcribed', 'Transcribed'), ('failed', 'Failed')], default='not_transcribed', help_text='Whisper Transcription status', max_length=20),
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
        
        # Visual Transcription Fields (from 0030)
        migrations.AddField(
            model_name='videodownload',
            name='has_audio',
            field=models.BooleanField(default=True, help_text='Whether video contains audio track'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript',
            field=models.TextField(blank=True, help_text='Visual: Frame-by-frame description WITH timestamps (HH:MM:SS format)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript_without_timestamps',
            field=models.TextField(blank=True, help_text='Visual: Frame-by-frame description WITHOUT timestamps (plain text)'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript_hindi',
            field=models.TextField(blank=True, help_text='Visual: Hindi translation of visual description'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript_segments',
            field=models.JSONField(blank=True, help_text='Visual: Raw segments with timestamps and descriptions', null=True),
        ),
        
        # Cloudinary and Google Sheets Fields (from 0022)
        migrations.AddField(
            model_name='videodownload',
            name='cloudinary_url',
            field=models.URLField(blank=True, help_text='Cloudinary URL for final processed video', max_length=1000),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='cloudinary_uploaded_at',
            field=models.DateTimeField(blank=True, help_text='When Cloudinary upload finished', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='generated_description',
            field=models.TextField(blank=True, help_text='AI-generated description for video'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='generated_tags',
            field=models.CharField(blank=True, help_text='AI-generated tags (comma-separated)', max_length=1000),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='generated_title',
            field=models.CharField(blank=True, help_text='AI-generated title for video', max_length=500),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='google_sheets_synced',
            field=models.BooleanField(default=False, help_text='Whether data has been synced to Google Sheets'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='google_sheets_synced_at',
            field=models.DateTimeField(blank=True, help_text='When Google Sheets sync finished', null=True),
        ),
        
        # Voice Profile Foreign Key (from 0013)
        migrations.AddField(
            model_name='videodownload',
            name='voice_profile',
            field=models.ForeignKey(blank=True, help_text='Voice profile used for synthesis', null=True, on_delete=django.db.models.deletion.SET_NULL, to='downloader.clonedvoice'),
        ),
        
        # NEW: Timestamp fields for all processing steps
        migrations.AddField(
            model_name='videodownload',
            name='extraction_started_at',
            field=models.DateTimeField(blank=True, help_text='When video extraction/download started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='extraction_finished_at',
            field=models.DateTimeField(blank=True, help_text='When video extraction/download finished', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='ai_processing_started_at',
            field=models.DateTimeField(blank=True, help_text='When AI processing started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='script_started_at',
            field=models.DateTimeField(blank=True, help_text='When script generation started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='synthesis_started_at',
            field=models.DateTimeField(blank=True, help_text='When audio synthesis started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='final_video_started_at',
            field=models.DateTimeField(blank=True, help_text='When final video assembly started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='final_video_finished_at',
            field=models.DateTimeField(blank=True, help_text='When final video assembly finished', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='cloudinary_upload_started_at',
            field=models.DateTimeField(blank=True, help_text='When Cloudinary upload started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='google_sheets_sync_started_at',
            field=models.DateTimeField(blank=True, help_text='When Google Sheets sync started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript_started_at',
            field=models.DateTimeField(blank=True, help_text='When visual transcription started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='visual_transcript_finished_at',
            field=models.DateTimeField(blank=True, help_text='When visual transcription finished', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript_started_at',
            field=models.DateTimeField(blank=True, help_text='When enhanced transcript generation started', null=True),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='enhanced_transcript_finished_at',
            field=models.DateTimeField(blank=True, help_text='When enhanced transcript generation finished', null=True),
        ),
    ]

