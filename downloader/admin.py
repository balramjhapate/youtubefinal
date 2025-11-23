from django.contrib import admin
from .models import VideoDownload


@admin.register(VideoDownload)
class VideoDownloadAdmin(admin.ModelAdmin):
    """Admin interface for VideoDownload model"""
    
    list_display = [
        'title_short', 
        'url_short', 
        'status', 
        'extraction_method', 
        'created_at'
    ]
    
    list_filter = [
        'status', 
        'extraction_method', 
        'created_at'
    ]
    
    search_fields = [
        'title', 
        'url', 
        'video_url'
    ]
    
    readonly_fields = [
        'url', 
        'title', 
        'video_url', 
        'cover_url', 
        'extraction_method', 
        'status', 
        'error_message', 
        'created_at', 
        'updated_at'
    ]
    
    fieldsets = [
        ('Video Information', {
            'fields': ('title', 'url', 'video_url', 'cover_url')
        }),
        ('Extraction Details', {
            'fields': ('extraction_method', 'status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    ]
    
    date_hierarchy = 'created_at'
    
    def title_short(self, obj):
        """Display shortened title"""
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'
    
    def url_short(self, obj):
        """Display shortened URL"""
        return obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
    url_short.short_description = 'URL'
    
    # Make all records read-only to preserve data integrity
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True
