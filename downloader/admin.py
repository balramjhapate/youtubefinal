from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from .models import VideoDownload, AIProviderSettings, VoiceProfile
from .utils import (
    perform_extraction, extract_video_id, translate_text, download_file,
    process_video_with_ai, transcribe_video, add_caption_to_video,
    extract_thumbnail_from_video, trim_video_segment, generate_audio_prompt
)
from .voice_cloning import get_voice_cloning_service

# Unregister default auth models
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(AIProviderSettings)
class AIProviderSettingsAdmin(admin.ModelAdmin):
    """Admin interface for AI Provider Settings"""
    list_display = ['id', 'provider', 'api_key_display']
    fields = ['provider', 'api_key']

    def api_key_display(self, obj):
        if obj.api_key:
            return f"{obj.api_key[:10]}..." if len(obj.api_key) > 10 else obj.api_key
        return "-"
    api_key_display.short_description = "API Key"

    def has_add_permission(self, request):
        # Only allow one settings record
        return not AIProviderSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the settings record
        return False

@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    """Admin interface for VoiceProfile model"""
    list_display = ['name', 'created_at']
    search_fields = ['name', 'reference_text']
    readonly_fields = ['created_at']
    fields = ['name', 'reference_audio', 'reference_text', 'embedding_path']

@admin.register(VideoDownload)
class VideoDownloadAdmin(admin.ModelAdmin):
    """Admin interface for VideoDownload model"""

    change_list_template = 'admin/downloader/videodownload/change_list.html'

    def changelist_view(self, request, extra_context=None):
        # Calculate stats
        total_videos = VideoDownload.objects.count()
        downloaded_count = VideoDownload.objects.filter(is_downloaded=True).count()
        cloud_only_count = total_videos - downloaded_count
        success_count = VideoDownload.objects.filter(status='success').count()
        failed_count = VideoDownload.objects.filter(status='failed').count()
        pending_count = VideoDownload.objects.filter(status='pending').count()

        # AI Processing stats
        ai_processed_count = VideoDownload.objects.filter(ai_processing_status='processed').count()
        ai_processing_count = VideoDownload.objects.filter(ai_processing_status='processing').count()
        ai_not_processed_count = VideoDownload.objects.filter(ai_processing_status='not_processed').count()
        ai_failed_count = VideoDownload.objects.filter(ai_processing_status='failed').count()

        extra_context = extra_context or {}
        extra_context['total_videos'] = total_videos
        extra_context['downloaded_count'] = downloaded_count
        extra_context['cloud_only_count'] = cloud_only_count
        extra_context['success_count'] = success_count
        extra_context['failed_count'] = failed_count
        extra_context['pending_count'] = pending_count
        extra_context['ai_processed_count'] = ai_processed_count
        extra_context['ai_processing_count'] = ai_processing_count
        extra_context['ai_not_processed_count'] = ai_not_processed_count
        extra_context['ai_failed_count'] = ai_failed_count

        return super().changelist_view(request, extra_context=extra_context)

    list_display = [
        'thumbnail_display',
        'title_display',
        'status_badge',
        'transcription_status_badge',
        'ai_status_badge',
        'audio_prompt_status_badge',
        'synthesis_status_badge',
        'voice_profile_display',
        'download_status',
        'download_button',
        'created_at'
    ]

    search_fields = [
        'title',
        'original_title',
        'url',
        'video_id'
    ]

    readonly_fields = [
        'video_id',
        'title',
        'description',
        'original_title',
        'original_description',
        'video_url',
        'cover_url',
        'thumbnail_preview',
        'extraction_method',
        'status',
        'error_message',
        'is_downloaded',
        'local_file',
        'ai_processing_status',
        'ai_summary',
        'ai_tags',
        'ai_error_message',
        'ai_processed_at',
        'transcription_status',
        'transcript',
        'transcript_hindi',
        'transcript_language',
        'transcript_started_at',
        'transcript_processed_at',
        'transcript_error_message',
        'audio_prompt_status',
        'audio_generation_prompt',
        'audio_prompt_error',
        'audio_prompt_generated_at',
        'synthesis_status',
        'synthesized_audio',
        'synthesis_error',
        'synthesis_actions',
        'created_at',
        'updated_at'
    ]

    fieldsets = [
        ('Video Information', {
            'fields': ('url', 'video_id', 'thumbnail_preview')
        }),
        ('Content (Translated)', {
            'fields': ('title', 'description')
        }),
        ('Original Content (Chinese)', {
            'fields': ('original_title', 'original_description')
        }),
        ('Media Details', {
            'fields': ('video_url', 'cover_url', 'local_file', 'is_downloaded')
        }),
        ('Extraction Status', {
            'fields': ('extraction_method', 'status', 'error_message')
        }),
        ('AI Processing', {
            'fields': ('ai_processing_status', 'ai_summary', 'ai_tags', 'ai_error_message', 'ai_processed_at')
        }),
        ('Transcription', {
            'fields': ('transcription_status', 'transcript', 'transcript_hindi', 'transcript_language', 'transcript_started_at', 'transcript_processed_at', 'transcript_error_message'),
            'description': 'Full transcript of video speech/audio with Hindi translation'
        }),
        ('Audio Generation', {
            'fields': ('audio_prompt_status', 'audio_generation_prompt', 'audio_prompt_error', 'audio_prompt_generated_at'),
            'description': 'AI-generated prompt for audio generation from transcript'
        }),
        ('Audio Synthesis', {
            'fields': ('voice_profile', 'synthesis_status', 'synthesis_actions', 'synthesized_audio', 'synthesis_error'),
            'description': 'AI-generated audio from transcript using a voice profile'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    ]

    actions = [
        'download_video_action',
        'transcribe_video_action',
        'process_with_ai_action',
        'generate_audio_prompt_action',
        'synthesize_audio_action',
        'add_caption_action'
    ]

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'download-video/<int:pk>/',
                self.admin_site.admin_view(self.download_video_view),
                name='downloader_videodownload_download',
            ),
            path(
                'process-ai/<int:pk>/',
                self.admin_site.admin_view(self.process_ai_view),
                name='downloader_videodownload_process_ai',
            ),
            path(
                'process-ai/',
                self.admin_site.admin_view(self.process_ai_bulk_view),
                name='downloader_videodownload_process_ai_bulk',
            ),
            path(
                'transcribe/<int:pk>/',
                self.admin_site.admin_view(self.transcribe_video_view),
                name='downloader_videodownload_transcribe',
            ),
            path(
                'transcribe/',
                self.admin_site.admin_view(self.transcribe_video_bulk_view),
                name='downloader_videodownload_transcribe_bulk',
            ),
            path(
                'transcription-status/<int:pk>/',
                self.admin_site.admin_view(self.transcription_status_view),
                name='downloader_videodownload_transcription_status',
            ),
            path(
                'synthesize-audio/<int:pk>/',
                self.admin_site.admin_view(self.synthesize_audio_view),
                name='downloader_videodownload_synthesize_audio',
            ),
            path(
                'synthesize-audio/',
                self.admin_site.admin_view(self.synthesize_audio_bulk_view),
                name='downloader_videodownload_synthesize_audio_bulk',
            ),
        ]
        return custom_urls + urls

    def download_video_view(self, request, pk):
        obj = get_object_or_404(VideoDownload, pk=pk)

        if not obj.video_url:
            self.message_user(request, "No video URL available.", level=messages.ERROR)
            return redirect('admin:downloader_videodownload_changelist')

        # Download file
        file_content = download_file(obj.video_url)
        if file_content:
            filename = f"{obj.video_id or 'video'}_{obj.pk}.mp4"
            obj.local_file.save(filename, file_content, save=True)
            obj.is_downloaded = True
            obj.save()
            self.message_user(request, f"Successfully downloaded video: {obj.title}")
        else:
            self.message_user(request, "Failed to download video file.", level=messages.ERROR)

        return redirect('admin:downloader_videodownload_changelist')

    def save_model(self, request, obj, form, change):
        """Override save to auto-fetch and translate data"""
        if not change:  # Only on creation
            # 1. Extract Video ID
            video_id = extract_video_id(obj.url)
            if video_id:
                # Check for duplicates (exclude current object if it exists)
                existing = VideoDownload.objects.filter(video_id=video_id).first()
                if existing:
                    messages.error(request, format_html(
                        "Video with ID '{}' already exists! <a href='/admin/downloader/videodownload/{}/change/'>View existing record</a>",
                        video_id, existing.pk
                    ))
                    # Don't save, return early
                    return
                obj.video_id = video_id
            else:
                # If no video_id extracted, leave it as None (NULL)
                # Multiple NULL values don't violate unique constraints
                obj.video_id = None

            # 2. Fetch Metadata
            video_data = perform_extraction(obj.url)
            if video_data:
                obj.status = 'success'
                obj.extraction_method = video_data.get('method', '')
                obj.video_url = video_data.get('video_url', '')
                obj.cover_url = video_data.get('cover_url', '')

                # 3. Translate Content
                original_title = video_data.get('original_title', '')
                original_desc = video_data.get('original_description', '')

                obj.original_title = original_title
                obj.original_description = original_desc

                # Translate to English
                obj.title = translate_text(original_title, target='en')
                obj.description = translate_text(original_desc, target='en')
            else:
                obj.status = 'failed'
                obj.error_message = "Could not extract video metadata"
                # Ensure required fields have default values even on failure
                obj.original_title = obj.original_title or ''
                obj.original_description = obj.original_description or ''
                obj.title = obj.title or ''
                obj.description = obj.description or ''

        # Ensure all required fields have default values before saving
        obj.original_title = obj.original_title or ''
        obj.original_description = obj.original_description or ''
        obj.title = obj.title or ''
        obj.description = obj.description or ''

        # Try to save, catch IntegrityError in case duplicate check missed something (race condition)
        try:
            super().save_model(request, obj, form, change)
        except IntegrityError as e:
            if 'video_id' in str(e):
                # Find the existing record
                if obj.video_id:
                    existing = VideoDownload.objects.filter(video_id=obj.video_id).first()
                    if existing:
                        messages.error(request, format_html(
                            "Video with ID '{}' already exists! <a href='/admin/downloader/videodownload/{}/change/'>View existing record</a>",
                            obj.video_id, existing.pk
                        ))
                    else:
                        messages.error(request, f"Duplicate video ID detected: '{obj.video_id}'. This may be a race condition.")
                else:
                    messages.error(request, "Could not save video. Please ensure the URL contains a valid video ID.")
            else:
                messages.error(request, f"Database error: {str(e)}")
            # Re-raise to prevent saving
            raise

    def download_video_action(self, request, queryset):
        """Action to download video files to local storage"""
        success_count = 0
        for obj in queryset:
            if obj.is_downloaded:
                continue

            if not obj.video_url:
                continue

            # Download file
            file_content = download_file(obj.video_url)
            if file_content:
                filename = f"{obj.video_id or 'video'}_{obj.pk}.mp4"
                obj.local_file.save(filename, file_content, save=True)
                obj.is_downloaded = True
                obj.save()
                success_count += 1

        self.message_user(request, f"Successfully downloaded {success_count} videos to local storage.")
    download_video_action.short_description = "Download Selected Videos to Storage"

    def transcribe_video_action(self, request, queryset):
        """Action to transcribe videos"""
        # Redirect to bulk transcription page
        selected_ids = ','.join(str(obj.pk) for obj in queryset)
        return redirect(f'/admin/downloader/videodownload/transcribe/?ids={selected_ids}')
    transcribe_video_action.short_description = "Transcribe Selected Videos"

    def process_with_ai_action(self, request, queryset):
        """Action to process videos with AI"""
        # Redirect to bulk processing page
        selected_ids = ','.join(str(obj.pk) for obj in queryset)
        return redirect(f'/admin/downloader/videodownload/process-ai/?ids={selected_ids}')
    process_with_ai_action.short_description = "Process Selected Videos with AI"

    def add_caption_action(self, request, queryset):
        """Action to add captions to videos (requires transcription first)"""
        from django.conf import settings
        if not getattr(settings, 'NCA_API_ENABLED', False):
            messages.error(request, "Captioning requires NCA Toolkit API. Please enable it in settings.")
            return

        success_count = 0
        failed_count = 0

        for obj in queryset:
            if not obj.transcript:
                failed_count += 1
                messages.warning(request, f"Video '{obj.title}' has no transcript. Please transcribe first.")
                continue

            if not obj.video_url:
                failed_count += 1
                messages.warning(request, f"Video '{obj.title}' has no video URL.")
                continue

            try:
                result = add_caption_to_video(obj)
                if result['status'] == 'success':
                    success_count += 1
                    messages.success(request, f"Added captions to: {obj.title}")
                else:
                    failed_count += 1
                    messages.error(request, f"Failed to add captions to '{obj.title}': {result.get('error')}")
            except Exception as e:
                failed_count += 1
                messages.error(request, f"Error adding captions to '{obj.title}': {str(e)}")

        if success_count > 0:
            messages.success(request, f"Successfully added captions to {success_count} video(s).")
        if failed_count > 0:
            messages.error(request, f"Failed to add captions to {failed_count} video(s).")
    add_caption_action.short_description = "Add Captions to Videos (NCA API)"

    def generate_audio_prompt_action(self, request, queryset):
        """Action to generate audio prompts from transcripts"""
        success_count = 0
        failed_count = 0

        for obj in queryset:
            if not obj.transcript:
                failed_count += 1
                messages.warning(request, f"Video '{obj.title}' has no transcript. Please transcribe first.")
                continue

            # Set status to generating
            obj.audio_prompt_status = 'generating'
            obj.save()

            try:
                result = generate_audio_prompt(obj)

                if result['status'] == 'success':
                    obj.audio_prompt_status = 'generated'
                    obj.audio_generation_prompt = result['prompt']
                    obj.audio_prompt_generated_at = timezone.now()
                    obj.audio_prompt_error = ''
                    success_count += 1
                else:
                    obj.audio_prompt_status = 'failed'
                    obj.audio_prompt_error = result.get('error', 'Unknown error')
                    failed_count += 1

                obj.save()

            except Exception as e:
                obj.audio_prompt_status = 'failed'
                obj.audio_prompt_error = str(e)
                obj.save()
                failed_count += 1

        if success_count > 0:
            messages.success(request, f"Successfully generated audio prompts for {success_count} video(s).")
        if failed_count > 0:
            messages.error(request, f"Failed to generate audio prompts for {failed_count} video(s).")
    generate_audio_prompt_action.short_description = "Generate Audio Prompts (AI)"

    def synthesize_audio_action(self, request, queryset):
        """Action to synthesize audio from transcripts using a voice profile"""
        selected_ids = ','.join(str(obj.pk) for obj in queryset)
        return redirect(f'/admin/downloader/videodownload/synthesize-audio/?ids={selected_ids}')
    synthesize_audio_action.short_description = "Synthesize Audio for Selected Videos"

    def process_ai_view(self, request, pk):
        """Process a single video with AI"""
        obj = get_object_or_404(VideoDownload, pk=pk)

        if obj.ai_processing_status == 'processing':
            messages.warning(request, "This video is already being processed.")
            return redirect('admin:downloader_videodownload_changelist')

        # Set status to processing
        obj.ai_processing_status = 'processing'
        obj.save()

        try:
            # Process with AI
            result = process_video_with_ai(obj)

            if result['status'] == 'success':
                obj.ai_processing_status = 'processed'
                obj.ai_summary = result['summary']
                obj.ai_tags = ', '.join(result['tags'])
                obj.ai_processed_at = timezone.now()
                obj.ai_error_message = ''
                messages.success(request, f"Successfully processed video with AI: {obj.title}")
            else:
                obj.ai_processing_status = 'failed'
                obj.ai_error_message = result.get('error', 'Unknown error')
                messages.error(request, f"AI processing failed: {result.get('error', 'Unknown error')}")

            obj.save()

        except Exception as e:
            obj.ai_processing_status = 'failed'
            obj.ai_error_message = str(e)
            obj.save()
            messages.error(request, f"AI processing error: {str(e)}")

        return redirect('admin:downloader_videodownload_changelist')

    def process_ai_bulk_view(self, request):
        """Process multiple videos with AI"""
        ids_param = request.GET.get('ids', '')
        if not ids_param:
            messages.error(request, "No videos selected.")
            return redirect('admin:downloader_videodownload_changelist')

        try:
            video_ids = [int(id) for id in ids_param.split(',') if id.strip()]
            videos = VideoDownload.objects.filter(pk__in=video_ids)

            if request.method == 'POST':
                # Process all videos
                success_count = 0
                failed_count = 0

                for obj in videos:
                    if obj.ai_processing_status == 'processing':
                        continue

                    obj.ai_processing_status = 'processing'
                    obj.save()

                    try:
                        result = process_video_with_ai(obj)

                        if result['status'] == 'success':
                            obj.ai_processing_status = 'processed'
                            obj.ai_summary = result['summary']
                            obj.ai_tags = ', '.join(result['tags'])
                            obj.ai_processed_at = timezone.now()
                            obj.ai_error_message = ''
                            success_count += 1
                        else:
                            obj.ai_processing_status = 'failed'
                            obj.ai_error_message = result.get('error', 'Unknown error')
                            failed_count += 1

                        obj.save()

                    except Exception as e:
                        obj.ai_processing_status = 'failed'
                        obj.ai_error_message = str(e)
                        obj.save()
                        failed_count += 1

                messages.success(
                    request,
                    f"AI processing completed: {success_count} successful, {failed_count} failed."
                )
                return redirect('admin:downloader_videodownload_changelist')

            # Render processing page
            context = {
                'videos': videos,
                'video_count': videos.count(),
                'opts': self.model._meta,
                'has_view_permission': self.has_view_permission(request),
            }
            return render(request, 'admin/downloader/videodownload/process_ai.html', context)

        except ValueError:
            messages.error(request, "Invalid video IDs.")
            return redirect('admin:downloader_videodownload_changelist')

    def transcribe_video_view(self, request, pk):
        """Transcribe a single video"""
        obj = get_object_or_404(VideoDownload, pk=pk)

        if obj.transcription_status == 'transcribing':
            messages.warning(request, "This video is already being transcribed.")
            return redirect('admin:downloader_videodownload_changelist')

        # Set status to transcribing and save start time
        obj.transcription_status = 'transcribing'
        obj.transcript_started_at = timezone.now()
        obj.save()

        try:
            # Transcribe video
            result = transcribe_video(obj)

            if result['status'] == 'success':
                obj.transcription_status = 'transcribed'
                obj.transcript = result['text']
                obj.transcript_hindi = result.get('text_hindi', '')
                obj.transcript_language = result.get('language', '')
                obj.transcript_processed_at = timezone.now()
                obj.transcript_error_message = ''
                messages.success(request, f"Successfully transcribed video: {obj.title}")
            else:
                obj.transcription_status = 'failed'
                obj.transcript_error_message = result.get('error', 'Unknown error')
                messages.error(request, f"Transcription failed: {result.get('error', 'Unknown error')}")

            obj.save()

        except Exception as e:
            obj.transcription_status = 'failed'
            obj.transcript_error_message = str(e)
            obj.save()
            messages.error(request, f"Transcription error: {str(e)}")

        return redirect('admin:downloader_videodownload_changelist')

    def transcribe_video_bulk_view(self, request):
        """Transcribe multiple videos"""
        ids_param = request.GET.get('ids', '')
        if not ids_param:
            messages.error(request, "No videos selected.")
            return redirect('admin:downloader_videodownload_changelist')

        try:
            video_ids = [int(id) for id in ids_param.split(',') if id.strip()]
            videos = VideoDownload.objects.filter(pk__in=video_ids)

            if request.method == 'POST':
                # Process all videos
                success_count = 0
                failed_count = 0

                for obj in videos:
                    if obj.transcription_status == 'transcribing':
                        continue

                    obj.transcription_status = 'transcribing'
                    obj.transcript_started_at = timezone.now()
                    obj.save()

                    try:
                        result = transcribe_video(obj)

                        if result['status'] == 'success':
                            obj.transcription_status = 'transcribed'
                            obj.transcript = result['text']
                            obj.transcript_hindi = result.get('text_hindi', '')
                            obj.transcript_language = result.get('language', '')
                            obj.transcript_processed_at = timezone.now()
                            obj.transcript_error_message = ''
                            success_count += 1
                        else:
                            obj.transcription_status = 'failed'
                            obj.transcript_error_message = result.get('error', 'Unknown error')
                            failed_count += 1

                        obj.save()

                    except Exception as e:
                        obj.transcription_status = 'failed'
                        obj.transcript_error_message = str(e)
                        obj.save()
                        failed_count += 1

                messages.success(
                    request,
                    f"Transcription completed: {success_count} successful, {failed_count} failed."
                )
                return redirect('admin:downloader_videodownload_changelist')

            # Render transcription page
            context = {
                'videos': videos,
                'video_count': videos.count(),
                'opts': self.model._meta,
                'has_view_permission': self.has_view_permission(request),
            }
            return render(request, 'admin/downloader/videodownload/transcribe.html', context)

        except ValueError:
            messages.error(request, "Invalid video IDs.")
            return redirect('admin:downloader_videodownload_changelist')

    def transcription_status_view(self, request, pk):
        """API endpoint to check transcription status"""
        from django.http import JsonResponse
        from django.utils import timezone
        from datetime import timedelta

        # Ensure user has permission
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        try:
            obj = get_object_or_404(VideoDownload, pk=pk)

            elapsed_seconds = 0
            if obj.transcript_started_at:
                elapsed = timezone.now() - obj.transcript_started_at
                elapsed_seconds = int(elapsed.total_seconds())

            # Format elapsed time
            if elapsed_seconds < 60:
                elapsed_display = f"{elapsed_seconds}s"
            elif elapsed_seconds < 3600:
                minutes = elapsed_seconds // 60
                seconds = elapsed_seconds % 60
                elapsed_display = f"{minutes}m {seconds}s"
            else:
                hours = elapsed_seconds // 3600
                minutes = (elapsed_seconds % 3600) // 60
                elapsed_display = f"{hours}h {minutes}m"

            response = JsonResponse({
                'status': obj.transcription_status,
                'elapsed_seconds': elapsed_seconds,
                'elapsed_display': elapsed_display,
                'has_transcript': bool(obj.transcript),
                'error': obj.transcript_error_message if obj.transcription_status == 'failed' else None
            })
            # Ensure proper content type header
            response['Content-Type'] = 'application/json'
            return response
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def synthesize_audio_view(self, request, pk):
        """Synthesize audio for a single video"""
        obj = get_object_or_404(VideoDownload, pk=pk)

        if not obj.transcript:
            messages.error(request, "Cannot synthesize audio: no transcript available.")
            return redirect('admin:downloader_videodownload_changelist')

        if not obj.voice_profile:
            messages.error(request, "Cannot synthesize audio: no voice profile selected for this video.")
            return redirect('admin:downloader_videodownload_changelist')

        if obj.synthesis_status == 'synthesizing':
            messages.warning(request, "Audio is already being synthesized for this video.")
            return redirect('admin:downloader_videodownload_changelist')

        obj.synthesis_status = 'synthesizing'
        obj.synthesis_error = ''
        obj.save()

        try:
            voice_cloning_service = get_voice_cloning_service()
            audio_file = voice_cloning_service.synthesize(obj.transcript, obj.voice_profile)

            if audio_file:
                filename = f"synthesized_audio_{obj.pk}.mp3"
                obj.synthesized_audio.save(filename, audio_file, save=True)
                obj.synthesis_status = 'synthesized'
                messages.success(request, f"Successfully synthesized audio for: {obj.title}")
            else:
                obj.synthesis_status = 'failed'
                obj.synthesis_error = "Failed to get audio file from service."
                messages.error(request, f"Audio synthesis failed for '{obj.title}': Failed to get audio file.")

            obj.save()

        except Exception as e:
            obj.synthesis_status = 'failed'
            obj.synthesis_error = str(e)
            obj.save()
            messages.error(request, f"Audio synthesis error for '{obj.title}': {str(e)}")

        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('admin:downloader_videodownload_changelist')

    def synthesize_audio_bulk_view(self, request):
        """Synthesize audio for multiple videos"""
        ids_param = request.GET.get('ids', '')
        if not ids_param:
            messages.error(request, "No videos selected.")
            return redirect('admin:downloader_videodownload_changelist')

        try:
            video_ids = [int(id) for id in ids_param.split(',') if id.strip()]
            videos = VideoDownload.objects.filter(pk__in=video_ids)

            if request.method == 'POST':
                success_count = 0
                failed_count = 0

                for obj in videos:
                    if not obj.transcript:
                        messages.warning(request, f"Skipping '{obj.title}': no transcript available.")
                        failed_count += 1
                        continue
                    if not obj.voice_profile:
                        messages.warning(request, f"Skipping '{obj.title}': no voice profile selected.")
                        failed_count += 1
                        continue
                    if obj.synthesis_status == 'synthesizing':
                        continue

                    obj.synthesis_status = 'synthesizing'
                    obj.synthesis_error = ''
                    obj.save()

                    try:
                        voice_cloning_service = get_voice_cloning_service()
                        audio_file = voice_cloning_service.synthesize(obj.transcript, obj.voice_profile)

                        if audio_file:
                            filename = f"synthesized_audio_{obj.pk}.mp3"
                            obj.synthesized_audio.save(filename, audio_file, save=True)
                            obj.synthesis_status = 'synthesized'
                            success_count += 1
                        else:
                            obj.synthesis_status = 'failed'
                            obj.synthesis_error = "Failed to get audio file from service."
                            failed_count += 1
                        obj.save()

                    except Exception as e:
                        obj.synthesis_status = 'failed'
                        obj.synthesis_error = str(e)
                        obj.save()
                        failed_count += 1

                messages.success(
                    request,
                    f"Audio synthesis completed: {success_count} successful, {failed_count} failed."
                )
                return redirect('admin:downloader_videodownload_changelist')

            context = {
                'videos': videos,
                'video_count': videos.count(),
                'opts': self.model._meta,
                'has_view_permission': self.has_view_permission(request),
            }
            return render(request, 'admin/downloader/videodownload/synthesize_audio.html', context)

        except ValueError:
            messages.error(request, "Invalid video IDs.")
            return redirect('admin:downloader_videodownload_changelist')

    # --- Display Helpers ---

    def thumbnail_display(self, obj):
        if obj.cover_url:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.cover_url)
        return "-"
    thumbnail_display.short_description = "Thumbnail"

    def thumbnail_preview(self, obj):
        if obj.cover_url:
            return format_html('<img src="{}" width="300" style="border-radius: 8px;" />', obj.cover_url)
        return "-"
    thumbnail_preview.short_description = "Preview"

    def title_display(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_display.short_description = "Title"

    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'failed': 'red',
            'pending': 'orange'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status.upper()
        )
    status_badge.short_description = "Status"

    def transcription_status_badge(self, obj):
        from django.utils import timezone
        colors = {
            'not_transcribed': '#6c757d',  # gray
            'transcribing': '#ffc107',     # yellow
            'transcribed': '#28a745',      # green
            'failed': '#dc3545'            # red
        }
        labels = {
            'not_transcribed': 'Not Transcribed',
            'transcribing': 'Transcribing',
            'transcribed': 'Transcribed',
            'failed': 'Failed'
        }
        status = obj.transcription_status
        icon = ''
        if status == 'transcribed':
            icon = '📝 '
        elif status == 'transcribing':
            icon = '⟳ '
        elif status == 'failed':
            icon = '✗ '

        # Calculate and display elapsed time if transcribing
        elapsed_text = ''
        if status == 'transcribing' and obj.transcript_started_at:
            elapsed = timezone.now() - obj.transcript_started_at
            elapsed_seconds = int(elapsed.total_seconds())
            if elapsed_seconds < 60:
                elapsed_text = f' ({elapsed_seconds}s)'
            elif elapsed_seconds < 3600:
                minutes = elapsed_seconds // 60
                seconds = elapsed_seconds % 60
                elapsed_text = f' ({minutes}m {seconds}s)'
            else:
                hours = elapsed_seconds // 3600
                minutes = (elapsed_seconds % 3600) // 60
                elapsed_text = f' ({hours}h {minutes}m)'

        # Add data attribute for JavaScript polling
        data_attr = ''
        if status == 'transcribing':
            data_attr = f' data-transcribe-id="{obj.pk}"'

        return format_html(
            '<span id="transcribe-status-{}" style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; display: inline-block;"{}>{}{}{}</span>',
            obj.pk,
            colors.get(status, '#6c757d'),
            data_attr,
            icon,
            labels.get(status, status.title()),
            elapsed_text
        )
    transcription_status_badge.short_description = "Transcript"

    def ai_status_badge(self, obj):
        colors = {
            'not_processed': '#6c757d',  # gray
            'processing': '#ffc107',     # yellow
            'processed': '#28a745',      # green
            'failed': '#dc3545'          # red
        }
        labels = {
            'not_processed': 'Not Processed',
            'processing': 'Processing',
            'processed': 'Processed',
            'failed': 'Failed'
        }
        status = obj.ai_processing_status
        icon = ''
        if status == 'processed':
            icon = '✓ '
        elif status == 'processing':
            icon = '⟳ '
        elif status == 'failed':
            icon = '✗ '

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; display: inline-block;">{}{}</span>',
            colors.get(status, '#6c757d'),
            icon,
            labels.get(status, status.title())
        )
    ai_status_badge.short_description = "AI Status"

    def audio_prompt_status_badge(self, obj):
        colors = {
            'not_generated': '#6c757d',  # gray
            'generating': '#ffc107',     # yellow
            'generated': '#28a745',      # green
            'failed': '#dc3545'          # red
        }
        labels = {
            'not_generated': 'Not Generated',
            'generating': 'Generating',
            'generated': 'Generated',
            'failed': 'Failed'
        }
        status = obj.audio_prompt_status
        icon = ''
        if status == 'generated':
            icon = '🎵 '
        elif status == 'generating':
            icon = '⟳ '
        elif status == 'failed':
            icon = '✗ '

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; display: inline-block;">{}{}</span>',
            colors.get(status, '#6c757d'),
            icon,
            labels.get(status, status.title())
        )
    audio_prompt_status_badge.short_description = "Audio Prompt"

    def synthesis_status_badge(self, obj):
        colors = {
            'not_synthesized': '#6c757d',  # gray
            'synthesizing': '#ffc107',     # yellow
            'synthesized': '#28a745',      # green
            'failed': '#dc3545'            # red
        }
        labels = {
            'not_synthesized': 'Not Synthesized',
            'synthesizing': 'Synthesizing',
            'synthesized': 'Synthesized',
            'failed': 'Failed'
        }
        status = obj.synthesis_status
        icon = ''
        if status == 'synthesized':
            icon = '🗣️ '
        elif status == 'synthesizing':
            icon = '⟳ '
        elif status == 'failed':
            icon = '✗ '

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; display: inline-block;">{}{}</span>',
            colors.get(status, '#6c757d'),
            icon,
            labels.get(status, status.title())
        )
    synthesis_status_badge.short_description = "Synthesis"

    def voice_profile_display(self, obj):
        from django.urls import reverse
        if obj.voice_profile:
            return format_html('<a href="{}">{}</a>',
                               reverse('admin:downloader_voiceprofile_change', args=[obj.voice_profile.pk]),
                               obj.voice_profile.name)
        return "-"
    voice_profile_display.short_description = "Voice Profile"

    def download_status(self, obj):
        if obj.is_downloaded:
            return format_html('<span style="color: green;">✔ Saved Locally</span>')
        return format_html('<span style="color: gray;">Cloud Only</span>')
    download_status.short_description = "Storage"

    def download_button(self, obj):
        from django.urls import reverse
        buttons = []

        # 1. Download / View
        if obj.is_downloaded and obj.local_file:
            buttons.append(format_html(
                '<a href="{}" target="_blank" title="View Video" style="text-decoration: none; font-size: 20px; color: #17a2b8;">👁️</a>',
                obj.local_file.url
            ))
        elif obj.status == 'success' and obj.video_url:
            download_url = reverse('admin:downloader_videodownload_download', args=[obj.pk])
            buttons.append(format_html(
                '<a class="button" href="{}" style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Download</a>',
                download_url
            ))

        # 2. Transcription
        if obj.status == 'success':
            transcribe_url = reverse('admin:downloader_videodownload_transcribe', args=[obj.pk])
            if obj.transcription_status == 'transcribed':
                buttons.append(format_html(
                    '<span title="Transcribed" style="font-size: 20px; cursor: help; color: #28a745;">📝</span>'
                ))
            elif obj.transcription_status == 'transcribing':
                buttons.append(format_html(
                    '<span title="Transcribing..." style="font-size: 20px; color: #ffc107;">⟳</span>'
                ))
            elif obj.transcription_status == 'failed':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Retry 📝</a>',
                    transcribe_url
                ))
            elif obj.transcription_status == 'not_transcribed':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Transcribe</a>',
                    transcribe_url
                ))

        # 3. AI Processing
        if obj.status == 'success':
            ai_url = reverse('admin:downloader_videodownload_process_ai', args=[obj.pk])
            if obj.ai_processing_status == 'processed':
                buttons.append(format_html(
                    '<span title="AI Processed" style="font-size: 20px; cursor: help; color: #667eea;">🤖</span>'
                ))
            elif obj.ai_processing_status == 'processing':
                buttons.append(format_html(
                    '<span title="Processing AI..." style="font-size: 20px; color: #ffc107;">⟳</span>'
                ))
            elif obj.ai_processing_status == 'failed':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Retry 🤖</a>',
                    ai_url
                ))
            elif obj.ai_processing_status == 'not_processed':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Process AI</a>',
                    ai_url
                ))

        # 4. Audio Prompt Generation
        if obj.transcription_status == 'transcribed':
            if obj.audio_prompt_status == 'generated':
                buttons.append(format_html(
                    '<span title="Audio Prompt Ready" style="font-size: 20px; cursor: help; color: #f5576c;">🎵</span>'
                ))
            elif obj.audio_prompt_status == 'generating':
                buttons.append(format_html(
                    '<span title="Generating Prompt..." style="font-size: 20px; color: #ffc107;">⟳</span>'
                ))
            elif obj.audio_prompt_status == 'failed':
                buttons.append(format_html(
                    '<button class="button" onclick="generateAudioPrompt({}, this)" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; border: none; cursor: pointer; font-size: 12px;">Retry 🎵</button>',
                    obj.pk
                ))
            elif obj.audio_prompt_status == 'not_generated':
                buttons.append(format_html(
                    '<button class="button" onclick="generateAudioPrompt({}, this)" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 3px 8px; border-radius: 4px; border: none; cursor: pointer; font-size: 12px;">Gen Audio</button>',
                    obj.pk
                ))

        # 5. Audio Synthesis
        if obj.transcription_status == 'transcribed' and obj.voice_profile:
            synthesize_url = reverse('admin:downloader_videodownload_synthesize_audio', args=[obj.pk])
            if obj.synthesis_status == 'synthesized':
                buttons.append(format_html(
                    '<span title="Audio Synthesized" style="font-size: 20px; cursor: help; color: #9b59b6;">🗣️</span>'
                ))
                if obj.synthesized_audio:
                    buttons.append(format_html(
                        '<a href="{}" target="_blank" title="Play Synthesized Audio" style="text-decoration: none; font-size: 20px; color: #9b59b6;">▶️</a>',
                        obj.synthesized_audio.url
                    ))
            elif obj.synthesis_status == 'synthesizing':
                buttons.append(format_html(
                    '<span title="Synthesizing..." style="font-size: 20px; color: #ffc107;">⟳</span>'
                ))
            elif obj.synthesis_status == 'failed':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Retry 🗣️</a>',
                    synthesize_url
                ))
            elif obj.synthesis_status == 'not_synthesized':
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 12px;">Synthesize</a>',
                    synthesize_url
                ))

        return format_html('<div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">{}</div>', format_html(''.join(str(b) for b in buttons)))
    download_button.short_description = "Actions"

    def synthesis_actions(self, obj):
        from django.urls import reverse
        buttons = []
        
        if obj.transcription_status == 'transcribed' and obj.voice_profile:
            synthesize_url = reverse('admin:downloader_videodownload_synthesize_audio', args=[obj.pk])
            
            if obj.synthesis_status == 'synthesized':
                if obj.synthesized_audio:
                    buttons.append(format_html(
                        '<audio controls src="{}" style="vertical-align: middle; margin-right: 10px;"></audio>',
                        obj.synthesized_audio.url
                    ))
                buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #17a2b8; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Re-Synthesize ⟳</a>',
                    synthesize_url
                ))
            elif obj.synthesis_status == 'synthesizing':
                buttons.append(format_html(
                    '<span style="color: #ffc107; font-weight: bold;">Synthesizing... ⟳</span>'
                ))
            elif obj.synthesis_status == 'failed':
                 buttons.append(format_html(
                    '<span style="color: #dc3545; margin-right: 10px;">Failed: {}</span>',
                    obj.synthesis_error
                ))
                 buttons.append(format_html(
                    '<a class="button" href="{}" style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Retry Synthesis 🗣️</a>',
                    synthesize_url
                ))
            else: # not_synthesized
                 buttons.append(format_html(
                    '<a class="button" href="{}" style="background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Synthesize Audio 🗣️</a>',
                    synthesize_url
                ))
        elif not obj.voice_profile:
            return format_html('<span style="color: #6c757d;">Select a Voice Profile and Save to enable synthesis.</span>')
        elif obj.transcription_status != 'transcribed':
            return format_html('<span style="color: #6c757d;">Transcribe video first to enable synthesis.</span>')
            
        return format_html(''.join(buttons))
    
    synthesis_actions.short_description = "Actions"

