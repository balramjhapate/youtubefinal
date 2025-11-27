from django import template
from downloader.models import VideoDownload

register = template.Library()

@register.simple_tag
def video_stats():
    total = VideoDownload.objects.count()
    downloaded = VideoDownload.objects.filter(is_downloaded=True).count()
    cloud = total - downloaded
    success = VideoDownload.objects.filter(status='success').count()
    failed = VideoDownload.objects.filter(status='failed').count()
    pending = VideoDownload.objects.filter(status='pending').count()
    return {
        'total': total,
        'downloaded': downloaded,
        'cloud': cloud,
        'success': success,
        'failed': failed,
        'pending': pending,
    }
