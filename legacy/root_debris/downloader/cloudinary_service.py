"""
Cloudinary service for uploading videos
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
from .models import CloudinarySettings
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
        }
        
        if public_id:
            upload_options['public_id'] = public_id
        
        # Upload the file
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


def upload_video_file(video_file, public_id=None):
    """
    Upload a Django FileField to Cloudinary
    
    Args:
        video_file: Django FileField instance
        public_id: Optional public ID for the resource
    
    Returns:
        dict with 'url' and 'public_id' if successful, None otherwise
    """
    if not video_file:
        return None
    
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

