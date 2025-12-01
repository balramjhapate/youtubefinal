"""
Test script for Google Sheets integration
Run this to diagnose Google Sheets connection issues
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from ..model import GoogleSheetsSettings
from google_sheets_service import get_google_sheets_service, extract_spreadsheet_id, ensure_header_row
import json

def test_google_sheets_config():
    """Test Google Sheets configuration"""
    print("=" * 60)
    print("Testing Google Sheets Configuration")
    print("=" * 60)
    
    # Check if settings exist
    sheets_settings = GoogleSheetsSettings.objects.first()
    
    if not sheets_settings:
        print("❌ ERROR: Google Sheets settings not found in database")
        print("   → Go to Settings page and configure Google Sheets")
        return False
    
    print(f"✓ Settings found (ID: {sheets_settings.id})")
    print(f"  Enabled: {sheets_settings.enabled}")
    print(f"  Spreadsheet ID: {sheets_settings.spreadsheet_id or 'NOT SET'}")
    print(f"  Sheet Name: {sheets_settings.sheet_name or 'NOT SET'}")
    print(f"  Credentials JSON: {'SET' if sheets_settings.credentials_json else 'NOT SET'}")
    
    if not sheets_settings.enabled:
        print("\n❌ ERROR: Google Sheets is disabled")
        print("   → Enable it in Settings page")
        return False
    
    if not sheets_settings.spreadsheet_id:
        print("\n❌ ERROR: Spreadsheet ID is missing")
        print("   → Add Spreadsheet ID in Settings page")
        return False
    
    if not sheets_settings.credentials_json:
        print("\n❌ ERROR: Service Account credentials are missing")
        print("   → Add Service Account JSON in Settings page")
        return False
    
    # Test spreadsheet ID extraction
    print("\n" + "-" * 60)
    print("Testing Spreadsheet ID extraction...")
    extracted_id = extract_spreadsheet_id(sheets_settings.spreadsheet_id)
    print(f"  Original: {sheets_settings.spreadsheet_id}")
    print(f"  Extracted ID: {extracted_id}")
    
    if not extracted_id:
        print("❌ ERROR: Could not extract spreadsheet ID")
        print("   → Make sure the Spreadsheet ID or URL is correct")
        return False
    
    # Test credentials JSON parsing
    print("\n" + "-" * 60)
    print("Testing Credentials JSON...")
    try:
        credentials_dict = json.loads(sheets_settings.credentials_json)
        print("✓ JSON is valid")
        
        # Check required fields
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in credentials_dict]
        
        if missing_fields:
            print(f"❌ ERROR: Missing required fields: {', '.join(missing_fields)}")
            return False
        
        print(f"  Project ID: {credentials_dict.get('project_id', 'N/A')}")
        print(f"  Client Email: {credentials_dict.get('client_email', 'N/A')}")
        print(f"  Type: {credentials_dict.get('type', 'N/A')}")
        
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in credentials: {str(e)}")
        print("   → Check the Service Account JSON format")
        return False
    
    # Test service creation
    print("\n" + "-" * 60)
    print("Testing Google Sheets API connection...")
    try:
        sheets_config = get_google_sheets_service()
        
        if not sheets_config:
            print("❌ ERROR: Failed to create Google Sheets service")
            print("   → Check the error messages above")
            return False
        
        print("✓ Google Sheets service created successfully")
        print(f"  Spreadsheet ID: {sheets_config['spreadsheet_id']}")
        print(f"  Sheet Name: {sheets_config['sheet_name']}")
        
        # Test reading from sheet
        print("\n" + "-" * 60)
        print("Testing read access to Google Sheet...")
        service = sheets_config['service']
        spreadsheet_id = sheets_config['spreadsheet_id']
        sheet_name = sheets_config['sheet_name']
        
        try:
            range_name = f'{sheet_name}!A1:J1'
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            print(f"✓ Successfully read from sheet '{sheet_name}'")
            if values:
                print(f"  Header row found: {values[0]}")
            else:
                print("  No header row found (will be created on first sync)")
            
        except Exception as e:
            error_str = str(e)
            if 'PERMISSION_DENIED' in error_str or 'permission' in error_str.lower():
                print(f"❌ ERROR: Permission denied")
                print(f"   → Share the Google Sheet with this email: {credentials_dict.get('client_email', 'N/A')}")
                print(f"   → Give 'Editor' access to the service account")
            elif 'NOT_FOUND' in error_str or 'not found' in error_str.lower():
                print(f"❌ ERROR: Spreadsheet not found")
                print(f"   → Check the Spreadsheet ID: {spreadsheet_id}")
                print(f"   → Make sure the spreadsheet exists and is accessible")
            else:
                print(f"❌ ERROR: {error_str}")
            return False
        
        # Test write access
        print("\n" + "-" * 60)
        print("Testing write access to Google Sheet...")
        try:
            # Try to ensure header row (this will create it if it doesn't exist)
            ensure_header_row(sheets_config)
            print("✓ Write access successful")
            print("  Header row created/verified")
            
        except Exception as e:
            error_str = str(e)
            if 'PERMISSION_DENIED' in error_str or 'permission' in error_str.lower():
                print(f"❌ ERROR: Write permission denied")
                print(f"   → Share the Google Sheet with this email: {credentials_dict.get('client_email', 'N/A')}")
                print(f"   → Give 'Editor' access (not just 'Viewer')")
            else:
                print(f"❌ ERROR: {error_str}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nGoogle Sheets is properly configured and ready to use.")
        print(f"\nService Account Email: {credentials_dict.get('client_email', 'N/A')}")
        print(f"Spreadsheet ID: {spreadsheet_id}")
        print(f"Sheet Name: {sheet_name}")
        print("\nMake sure the Google Sheet is shared with the service account email above.")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_google_sheets_config()
    sys.exit(0 if success else 1)

