"""
Google Sheets service for tracking video data
"""
import json
import logging
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .models import GoogleSheetsSettings
from django.utils import timezone

logger = logging.getLogger(__name__)


def extract_spreadsheet_id(spreadsheet_id_or_url):
    """Extract spreadsheet ID from URL or return as-is if already an ID"""
    if not spreadsheet_id_or_url:
        return None
    
    # Check if it's a URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_id_or_url)
    if match:
        return match.group(1)
    
    # If it doesn't match URL pattern, assume it's already an ID
    return spreadsheet_id_or_url


def get_google_sheets_service():
    """Get Google Sheets API service instance"""
    sheets_settings = GoogleSheetsSettings.objects.first()
    if not sheets_settings or not sheets_settings.enabled:
        return None
    
    if not sheets_settings.spreadsheet_id or not sheets_settings.credentials_json:
        logger.warning("Google Sheets is enabled but credentials are missing")
        return None
    
    # Extract spreadsheet ID from URL if needed
    spreadsheet_id = extract_spreadsheet_id(sheets_settings.spreadsheet_id)
    if not spreadsheet_id:
        logger.warning("Could not extract spreadsheet ID")
        return None
    
    try:
        # Parse credentials JSON
        credentials_dict = json.loads(sheets_settings.credentials_json)
        
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build the service
        service = build('sheets', 'v4', credentials=credentials)
        return {
            'service': service,
            'spreadsheet_id': spreadsheet_id,
            'sheet_name': sheets_settings.sheet_name or 'Sheet1',
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Google Sheets credentials: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error creating Google Sheets service: {str(e)}")
        return None


def ensure_header_row(sheets_config):
    """Ensure the header row exists in the Google Sheet"""
    try:
        service = sheets_config['service']
        spreadsheet_id = sheets_config['spreadsheet_id']
        sheet_name = sheets_config['sheet_name']
        
        # Check if header row exists
        range_name = f'{sheet_name}!A1:J1'
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # If no header row exists, create it
        if not values or len(values) == 0:
            headers = [
                'Title',
                'Description',
                'Tags',
                'Video Link (Cloudinary)',
                'Original URL',
                'Video ID',
                'Duration (seconds)',
                'Created At',
                'Status',
                'Synced At'
            ]
            
            body = {
                'values': [headers]
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A1:J1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info("Created header row in Google Sheet")
    except HttpError as e:
        logger.error(f"Error ensuring header row: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error ensuring header row: {str(e)}")


def add_video_to_sheet(video, cloudinary_url=None):
    """
    Add video data to Google Sheet
    
    Args:
        video: VideoDownload instance
        cloudinary_url: Optional Cloudinary URL (if not provided, uses video.cloudinary_url)
    
    Returns:
        dict: {
            'success': bool,
            'error': str (if failed)
        }
    """
    sheets_config = get_google_sheets_service()
    if not sheets_config:
        sheets_settings = GoogleSheetsSettings.objects.first()
        if not sheets_settings:
            error_msg = "Google Sheets settings not found. Please configure in Settings."
        elif not sheets_settings.enabled:
            error_msg = "Google Sheets is disabled. Enable it in Settings."
        elif not sheets_settings.spreadsheet_id:
            error_msg = "Spreadsheet ID is missing. Add it in Settings."
        elif not sheets_settings.credentials_json:
            error_msg = "Service Account credentials are missing. Add them in Settings."
        else:
            error_msg = "Google Sheets configuration error. Check Settings."
        
        logger.warning(f"Google Sheets sync failed: {error_msg}")
        return {'success': False, 'error': error_msg}
    
    try:
        service = sheets_config['service']
        spreadsheet_id = sheets_config['spreadsheet_id']
        sheet_name = sheets_config['sheet_name']
        
        # Ensure header row exists
        ensure_header_row(sheets_config)
        
        # Prepare row data
        video_url = cloudinary_url or video.cloudinary_url or video.final_processed_video_url or ''
        title = video.generated_title or video.title or 'Untitled'
        description = video.generated_description or video.description or ''
        tags = video.generated_tags or video.ai_tags or ''
        original_url = video.url or ''
        video_id = video.video_id or ''
        duration = str(video.duration) if video.duration else ''
        created_at = video.created_at.strftime('%Y-%m-%d %H:%M:%S') if video.created_at else ''
        status = video.review_status or 'pending_review'
        synced_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Append row
        values = [[
            title,
            description,
            tags,
            video_url,
            original_url,
            video_id,
            duration,
            created_at,
            status,
            synced_at
        ]]
        
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:J',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        logger.info(f"Successfully added video to Google Sheet: {video.id}")
        
        # Update video model
        video.google_sheets_synced = True
        video.google_sheets_synced_at = timezone.now()
        video.save(update_fields=['google_sheets_synced', 'google_sheets_synced_at'])
        
        return {'success': True, 'error': None}
    except HttpError as e:
        error_details = str(e)
        # Extract more specific error information
        if hasattr(e, 'content'):
            try:
                import json
                error_content = json.loads(e.content.decode('utf-8'))
                if 'error' in error_content:
                    error_details = error_content['error'].get('message', error_details)
            except:
                pass
        
        # Common error messages
        if 'PERMISSION_DENIED' in error_details or 'permission' in error_details.lower():
            error_msg = f"Permission denied. Make sure the service account email has edit access to the Google Sheet. Error: {error_details}"
        elif 'NOT_FOUND' in error_details or 'not found' in error_details.lower():
            error_msg = f"Spreadsheet not found. Check the Spreadsheet ID in Settings. Error: {error_details}"
        elif 'UNAUTHENTICATED' in error_details or 'invalid' in error_details.lower():
            error_msg = f"Authentication failed. Check your Service Account JSON credentials in Settings. Error: {error_details}"
        else:
            error_msg = f"Google Sheets API error: {error_details}"
        
        logger.error(f"Error adding video to Google Sheet: {error_msg}")
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Unexpected error adding video to Google Sheet: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': error_msg}

