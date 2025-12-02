"""
Cloudinary service for uploading videos
"""
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    cloudinary = None

from django.conf import settings
from model import CloudinarySettings
import logging

logger = logging.getLogger(__name__)


def get_cloudinary_config():
    """Get Cloudinary configuration from settings model"""
    cloudinary_settings = CloudinarySettings.objects.first()
    if not cloudinary_settings or not cloudinary_settings.enabled:
        return None
    
    if not cloudinary_settings.cloud_name or not cloudinary_settings.api_key or not cloudinary_settings.api_secret:
        logger.warning("Cloudinary is enabled but credentials are missing")
        return None
    
    return {
        'cloud_name': cloudinary_settings.cloud_name,
        'api_key': cloudinary_settings.api_key,
        'api_secret': cloudinary_settings.api_secret,
    }


def upload_video_to_cloudinary(video_file_path, public_id=None, resource_type='video'):
    """
    Upload a video file to Cloudinary
    
    Args:
        video_file_path: Path to the video file
        public_id: Optional public ID for the resource
        resource_type: Resource type ('video' or 'image')
    
    Returns:
        dict with 'url' and 'public_id' if successful, None otherwise
    """
    if not CLOUDINARY_AVAILABLE:
        logger.warning("Cloudinary package not installed. Install with: pip install cloudinary")
        return None
    
    config = get_cloudinary_config()
    if not config:
        logger.warning("Cloudinary not configured or disabled")
        return None
    
    try:
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=config['cloud_name'],
            api_key=config['api_key'],
            api_secret=config['api_secret']
        )
        
        # Upload options
        upload_options = {
            'resource_type': resource_type,
            'folder': 'videos/final',  # Organize in a folder
            'overwrite': True,  # Replace existing video if public_id matches
            'invalidate': True,  # Invalidate CDN cache for replaced video
        }
        
        if public_id:
            upload_options['public_id'] = public_id
        
        # Upload the file (will replace existing if public_id matches)
        result = cloudinary.uploader.upload(
            video_file_path,
            **upload_options
        )
        
        logger.info(f"Successfully uploaded video to Cloudinary: {result.get('url')}")
        return {
            'url': result.get('url'),
            'secure_url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'format': result.get('format'),
            'bytes': result.get('bytes'),
        }
    except Exception as e:
        logger.error(f"Error uploading video to Cloudinary: {str(e)}")
        return None


def upload_video_file(video_file, public_id=None, video_id=None):
    """
    Upload a Django FileField to Cloudinary
    
    Args:
        video_file: Django FileField instance
        public_id: Optional public ID for the resource (if not provided, uses video_id)
        video_id: Optional video ID to use as public_id (replaces existing video if same ID)
    
    Returns:
        dict with 'url' and 'public_id' if successful, None otherwise
    """
    if not video_file:
        return None
    
    # Use video_id as public_id if provided (this will replace existing video with same ID)
    # The overwrite=True option ensures only the latest version is kept
    if not public_id and video_id:
        public_id = f"videos/final/{video_id}"
    
    try:
        # Get the file path
        file_path = video_file.path if hasattr(video_file, 'path') else None
        if not file_path:
            # If file is in memory or doesn't have a path, we need to save it temporarily
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                for chunk in video_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name
            
            try:
                result = upload_video_to_cloudinary(tmp_file_path, public_id)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            return result
        else:
            return upload_video_to_cloudinary(file_path, public_id)
    except Exception as e:
        logger.error(f"Error uploading video file to Cloudinary: {str(e)}")
        return None


def cleanup_duplicate_cloudinary_videos():
    """
    Clean up duplicate videos in Cloudinary by keeping only the latest version for each video_id.
    This function can be called periodically to clean up old duplicates.
    
    Note: With overwrite=True in upload_video_to_cloudinary, duplicates shouldn't occur,
    but this function can clean up any that exist from before the fix.
    
    Returns:
        dict with cleanup results
    """
    if not CLOUDINARY_AVAILABLE:
        return {'success': False, 'error': 'Cloudinary package not installed'}
    
    config = get_cloudinary_config()
    if not config:
        return {'success': False, 'error': 'Cloudinary not configured'}
    
    try:
        cloudinary.config(
            cloud_name=config['cloud_name'],
            api_key=config['api_key'],
            api_secret=config['api_secret']
        )
        
        # List all videos in the videos/final folder
        resources = cloudinary.api.resources(
            type='upload',
            resource_type='video',
            prefix='videos/final/',
            max_results=500
        )
        
        # Group by video_id (extract from public_id)
        videos_by_id = {}
        for resource in resources.get('resources', []):
            public_id = resource.get('public_id', '')
            # Extract video_id from public_id (format: videos/final/{video_id})
            if '/final/' in public_id:
                video_id = public_id.split('/final/')[-1]
                if video_id not in videos_by_id:
                    videos_by_id[video_id] = []
                videos_by_id[video_id].append({
                    'public_id': public_id,
                    'created_at': resource.get('created_at', ''),
                    'bytes': resource.get('bytes', 0)
                })
        
        # For each video_id with multiple versions, keep only the latest
        deleted_count = 0
        for video_id, versions in videos_by_id.items():
            if len(versions) > 1:
                # Sort by created_at (most recent first)
                versions.sort(key=lambda x: x['created_at'], reverse=True)
                # Keep the first (latest), delete the rest
                for version in versions[1:]:
                    try:
                        cloudinary.uploader.destroy(version['public_id'], resource_type='video')
                        deleted_count += 1
                        logger.info(f"Deleted duplicate Cloudinary video: {version['public_id']}")
                    except Exception as e:
                        logger.warning(f"Could not delete duplicate {version['public_id']}: {e}")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleaned up {deleted_count} duplicate video(s) from Cloudinary'
        }
    except Exception as e:
        logger.error(f"Error cleaning up Cloudinary duplicates: {str(e)}")
        return {'success': False, 'error': str(e)}

