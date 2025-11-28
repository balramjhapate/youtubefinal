"""
Google Sheets service for tracking video data
"""
import json
import logging
import re

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    service_account = None
    build = None
    HttpError = Exception

from .models import GoogleSheetsSettings
from django.utils import timezone
import re

logger = logging.getLogger(__name__)


def format_hindi_title_for_sheets(title):
    """
    Format title for Google Sheets:
    - Ensure it's in Hindi
    - Make it shorter (max 100 chars)
    - Add #shorts #trending hashtags
    
    Args:
        title: Original title (may be in Hindi or English)
    
    Returns:
        str: Formatted Hindi title with hashtags
    """
    if not title:
        return "#shorts #trending"
    
    # Remove existing hashtags to avoid duplicates
    title = re.sub(r'#\w+\s*', '', title).strip()
    
    # Truncate to max 80 chars (leaving room for hashtags)
    if len(title) > 80:
        title = title[:77] + "..."
    
    # Add hashtags
    formatted_title = f"{title} #shorts #trending"
    
    return formatted_title


def format_hindi_description_for_sheets(description):
    """
    Format description for Google Sheets:
    - Ensure it's in Hindi
    - Add relevant hashtags at the end
    
    Args:
        description: Original description (may be in Hindi or English)
    
    Returns:
        str: Formatted Hindi description with hashtags
    """
    if not description:
        return ""
    
    # Remove existing hashtags to avoid duplicates
    description = re.sub(r'#\w+\s*', '', description).strip()
    
    # Add hashtags at the end
    # Common hashtags for Hindi shorts content
    hashtags = [
        "#shorts",
        "#trending",
        "#viral",
        "#hindi",
        "#india",
        "#youtubeshorts",
        "#funny",
        "#experiment",
        "#science",
        "#amazing"
    ]
    
    # Add hashtags
    formatted_description = f"{description}\n\n{' '.join(hashtags)}"
    
    return formatted_description


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
    if not GOOGLE_SHEETS_AVAILABLE:
        logger.warning("Google Sheets packages not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return None
    
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
        
        # Prepare row data with Hindi formatting
        video_url = cloudinary_url or video.cloudinary_url or video.final_processed_video_url or ''
        
        # Format title: Hindi, shorter, with #shorts #trending hashtags
        raw_title = video.generated_title or video.title or 'Untitled'
        title = format_hindi_title_for_sheets(raw_title)
        
        # Format description: Hindi with hashtags
        raw_description = video.generated_description or video.description or ''
        description = format_hindi_description_for_sheets(raw_description)
        
        tags = video.generated_tags or video.ai_tags or ''
        original_url = video.url or ''
        video_id = video.video_id or str(video.id)  # Use video_id or fallback to database ID
        duration = str(video.duration) if video.duration else ''
        created_at = video.created_at.strftime('%Y-%m-%d %H:%M:%S') if video.created_at else ''
        status = video.review_status or 'pending_review'
        synced_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if video already exists in sheet (by Video ID in column F)
        # Read all rows to find existing video and remove duplicates (keep only latest)
        try:
            all_rows = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A:J'
            ).execute()
            
            existing_row_index = None
            duplicate_row_indices = []
            
            if all_rows.get('values'):
                # Column F (index 5) contains Video ID, Column J (index 9) contains Synced At
                # Find all rows with matching video_id
                matching_rows = []
                for idx, row in enumerate(all_rows['values'], start=1):  # Start at 1 (row 1 is header)
                    if len(row) > 5 and row[5] == video_id:  # Check Video ID column
                        synced_at = row[9] if len(row) > 9 else ''
                        matching_rows.append({
                            'index': idx + 1,  # +1 because sheet rows are 1-indexed
                            'synced_at': synced_at
                        })
                
                if matching_rows:
                    # Sort by synced_at (most recent first) - keep the latest one
                    matching_rows.sort(key=lambda x: x['synced_at'], reverse=True)
                    existing_row_index = matching_rows[0]['index']  # Keep the latest
                    duplicate_row_indices = [r['index'] for r in matching_rows[1:]]  # Mark others for deletion
                    
                    logger.info(f"Found {len(matching_rows)} existing video(s) in Google Sheet. Keeping row {existing_row_index}, removing {len(duplicate_row_indices)} duplicate(s)")
                    
                    # Delete duplicate rows (in reverse order to maintain indices)
                    if duplicate_row_indices:
                        for row_idx in sorted(duplicate_row_indices, reverse=True):
                            try:
                                service.spreadsheets().batchUpdate(
                                    spreadsheetId=spreadsheet_id,
                                    body={
                                        'requests': [{
                                            'deleteDimension': {
                                                'range': {
                                                    'sheetId': 0,  # Assuming first sheet
                                                    'dimension': 'ROWS',
                                                    'startIndex': row_idx - 1,  # Convert to 0-indexed
                                                    'endIndex': row_idx
                                                }
                                            }
                                        }]
                                    }
                                ).execute()
                                logger.info(f"Deleted duplicate row {row_idx} from Google Sheets")
                            except Exception as e:
                                logger.warning(f"Could not delete duplicate row {row_idx}: {e}")
        except Exception as e:
            logger.warning(f"Error checking for existing video in sheet: {str(e)}")
            existing_row_index = None
        
        # Prepare row data
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
        
        if existing_row_index:
            # Update existing row
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A{existing_row_index}:J{existing_row_index}',
                valueInputOption='RAW',
                body=body
            ).execute()
            logger.info(f"Successfully updated video in Google Sheet at row {existing_row_index}: {video.id}")
        else:
            # Append new row
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

