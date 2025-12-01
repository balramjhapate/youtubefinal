#!/usr/bin/env python
"""
Fix migration ordering issues in the Django project.
This script will:
1. Remove incorrectly numbered migrations from django_migrations table
2. Rename migration files to correct numbers
3. Update dependencies in migration files
4. Mark the renamed migrations as applied
5. Apply remaining migrations
"""

import os
import sys
import re
import django
from pathlib import Path

# Add the project path
project_root = Path(__file__).parent / "legacy" / "root_debris"
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')

django.setup()

from django.db import connection
from django.core.management import call_command

def fix_migrations():
    """Fix the migration ordering issues"""
    
    migrations_dir = project_root / "downloader" / "migrations"
    
    print("=" * 60)
    print("Fixing Migration Issues")
    print("=" * 60)
    
    # Step 1: Remove incorrectly numbered migrations from database
    print("\n[1/5] Removing incorrectly numbered migrations from database...")
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM django_migrations 
            WHERE app = 'downloader' 
            AND name IN ('0002_add_whisper_transcription_fields', '0003_add_visual_transcript_fields')
        """)
        deleted = cursor.rowcount
        print(f"   ✓ Removed {deleted} migration records from database")
    
    # Step 2: Rename migration files
    print("\n[2/5] Renaming migration files...")
    
    old_file_1 = migrations_dir / "0002_add_whisper_transcription_fields.py"
    new_file_1 = migrations_dir / "0029_add_whisper_transcription_fields.py"
    
    old_file_2 = migrations_dir / "0003_add_visual_transcript_fields.py"
    new_file_2 = migrations_dir / "0030_add_visual_transcript_fields.py"
    
    if old_file_1.exists():
        # Read and update the file
        content = old_file_1.read_text()
        # Update dependencies to point to 0028 (the latest before this)
        content = re.sub(
            r"('downloader', '0022_add_cloudinary_google_sheets')",
            "('downloader', '0028_add_multi_provider_support')",
            content
        )
        # Update the class name
        content = content.replace(
            "class Migration(migrations.Migration):",
            "class Migration(migrations.Migration):"
        )
        new_file_1.write_text(content)
        print(f"   ✓ Renamed {old_file_1.name} -> {new_file_1.name}")
        old_file_1.unlink()
    else:
        print(f"   ⚠ File {old_file_1.name} not found")
    
    if old_file_2.exists():
        # Read and update the file
        content = old_file_2.read_text()
        # Update dependencies to point to 0029 (the renamed whisper migration)
        content = re.sub(
            r"('downloader', '0002_add_whisper_transcription_fields')",
            "('downloader', '0029_add_whisper_transcription_fields')",
            content
        )
        new_file_2.write_text(content)
        print(f"   ✓ Renamed {old_file_2.name} -> {new_file_2.name}")
        old_file_2.unlink()
    else:
        print(f"   ⚠ File {old_file_2.name} not found")
    
    # Step 3: Mark the renamed migrations as applied (fake apply)
    print("\n[3/5] Marking renamed migrations as applied...")
    try:
        call_command('migrate', 'downloader', '0029', '--fake', verbosity=0)
        print("   ✓ Marked 0029_add_whisper_transcription_fields as applied")
    except Exception as e:
        print(f"   ⚠ Error faking 0029: {e}")
    
    try:
        call_command('migrate', 'downloader', '0030', '--fake', verbosity=0)
        print("   ✓ Marked 0030_add_visual_transcript_fields as applied")
    except Exception as e:
        print(f"   ⚠ Error faking 0030: {e}")
    
    # Step 4: Show migration status
    print("\n[4/5] Current migration status:")
    call_command('showmigrations', 'downloader', verbosity=1)
    
    # Step 5: Apply remaining migrations
    print("\n[5/5] Applying remaining migrations...")
    try:
        call_command('migrate', 'downloader', verbosity=1)
        print("\n✓ All migrations applied successfully!")
    except Exception as e:
        print(f"\n⚠ Error applying migrations: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = fix_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

