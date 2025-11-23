from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.contrib import messages
from .models import VideoDownload
from .utils import perform_extraction, extract_video_id, translate_text, download_file

# Unregister default auth models
admin.site.unregister(User)
admin.site.unregister(Group)

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
        
        extra_context = extra_context or {}
        extra_context['total_videos'] = total_videos
        extra_context['downloaded_count'] = downloaded_count
        extra_context['cloud_only_count'] = cloud_only_count
        extra_context['success_count'] = success_count
        extra_context['failed_count'] = failed_count
        extra_context['pending_count'] = pending_count
        
        return super().changelist_view(request, extra_context=extra_context)

    list_display = [
        'thumbnail_display',
        'title_display', 
        'status_badge', 
        'download_status',
        'download_button',
        'created_at'
    ]
    
    list_filter = [
        'status', 
        'is_downloaded',
        'extraction_method', 
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
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    ]
    
    actions = ['download_video_action']
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'download-video/<int:pk>/',
                self.admin_site.admin_view(self.download_video_view),
                name='downloader_videodownload_download',
            ),
        ]
        return custom_urls + urls

    def download_video_view(self, request, pk):
        from django.shortcuts import redirect, get_object_or_404
        
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
                # Check for duplicates
                if VideoDownload.objects.filter(video_id=video_id).exists():
                    messages.error(request, f"Video {video_id} already exists!")
                    return # Stop saving
                obj.video_id = video_id
            
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
                
        super().save_model(request, obj, form, change)

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
    
    def download_status(self, obj):
        if obj.is_downloaded:
            return format_html('<span style="color: green;">✔ Saved Locally</span>')
        return format_html('<span style="color: gray;">Cloud Only</span>')
    download_status.short_description = "Storage"

    def download_button(self, obj):
        if obj.is_downloaded and obj.local_file:
            return format_html(
                '<a class="button" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; pointer-events: none; opacity: 0.7; margin-right: 5px;">Downloaded</a>'
                '<a class="button" href="{}" target="_blank" style="background-color: #17a2b8; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">View</a>',
                obj.local_file.url
            )
        if obj.status == 'success' and obj.video_url:
            from django.urls import reverse
            url = reverse('admin:downloader_videodownload_download', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background-color: #007bff; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Download</a>',
                url
            )
        return "-"
    download_button.short_description = "Action"
