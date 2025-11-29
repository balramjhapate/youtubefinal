#!/usr/bin/env python3
"""
Migration script to migrate data from SQLite to MySQL
Run this after initializing the MySQL database
"""
import os
import sqlite3
import pymysql
from app.config import settings
from app.models import SessionLocal, VideoDownload, AIProviderSettings, SavedVoice
from datetime import datetime

def parse_datetime(dt_str):
    """Parse datetime string from SQLite"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return None

def migrate_from_sqlite(sqlite_path="db.sqlite3"):
    """Migrate data from SQLite to MySQL"""
    print("🔄 Starting migration from SQLite to MySQL...")
    
    # Connect to SQLite
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found: {sqlite_path}")
        print("   Skipping migration. Starting with empty MySQL database.")
        return True
    
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to MySQL
        db = SessionLocal()
        
        # Migrate AIProviderSettings
        print("📦 Migrating AI Provider Settings...")
        sqlite_cursor.execute("SELECT * FROM ai_provider_settings WHERE id = 1")
        row = sqlite_cursor.fetchone()
        if row:
            existing = db.query(AIProviderSettings).filter(AIProviderSettings.id == 1).first()
            if not existing:
                settings_obj = AIProviderSettings(
                    id=1,
                    provider=row['provider'],
                    api_key=row['api_key']
                )
                db.add(settings_obj)
                db.commit()
                print("   ✅ AI Provider Settings migrated")
            else:
                print("   ⏭️  AI Provider Settings already exists")
        
        # Migrate VideoDownload
        print("📦 Migrating Videos...")
        sqlite_cursor.execute("SELECT * FROM video_download ORDER BY id")
        videos = sqlite_cursor.fetchall()
        
        migrated_count = 0
        for row in videos:
            # Check if video already exists
            existing = db.query(VideoDownload).filter(VideoDownload.id == row['id']).first()
            if existing:
                continue
            
            video = VideoDownload(
                id=row['id'],
                url=row['url'],
                video_id=row.get('video_id'),
                title=row.get('title', ''),
                original_title=row.get('original_title', ''),
                description=row.get('description', ''),
                original_description=row.get('original_description', ''),
                video_url=row.get('video_url', ''),
                cover_url=row.get('cover_url', ''),
                local_file=row.get('local_file'),
                is_downloaded=bool(row.get('is_downloaded', False)),
                duration=int(row.get('duration', 0)),
                extraction_method=row.get('extraction_method', ''),
                status=row.get('status', 'pending'),
                error_message=row.get('error_message', ''),
                ai_processing_status=row.get('ai_processing_status', 'not_processed'),
                ai_processed_at=parse_datetime(row.get('ai_processed_at')),
                ai_summary=row.get('ai_summary', ''),
                ai_tags=row.get('ai_tags', ''),
                ai_error_message=row.get('ai_error_message', ''),
                transcription_status=row.get('transcription_status', 'not_transcribed'),
                transcript=row.get('transcript', ''),
                transcript_hindi=row.get('transcript_hindi', ''),
                transcript_language=row.get('transcript_language', ''),
                transcript_started_at=parse_datetime(row.get('transcript_started_at')),
                transcript_processed_at=parse_datetime(row.get('transcript_processed_at')),
                transcript_error_message=row.get('transcript_error_message', ''),
                audio_prompt_status=row.get('audio_prompt_status', 'not_generated'),
                audio_generation_prompt=row.get('audio_generation_prompt', ''),
                audio_prompt_generated_at=parse_datetime(row.get('audio_prompt_generated_at')),
                audio_prompt_error=row.get('audio_prompt_error', ''),
                created_at=parse_datetime(row.get('created_at')) or datetime.utcnow(),
                updated_at=parse_datetime(row.get('updated_at')) or datetime.utcnow()
            )
            db.add(video)
            migrated_count += 1
        
        db.commit()
        print(f"   ✅ Migrated {migrated_count} videos")
        
        # Migrate SavedVoice
        print("📦 Migrating Saved Voices...")
        sqlite_cursor.execute("SELECT * FROM saved_voice")
        voices = sqlite_cursor.fetchall()
        
        voice_count = 0
        for row in voices:
            existing = db.query(SavedVoice).filter(SavedVoice.id == row['id']).first()
            if existing:
                continue
            
            voice = SavedVoice(
                id=row['id'],
                name=row['name'],
                file=row.get('file'),
                created_at=parse_datetime(row.get('created_at')) or datetime.utcnow()
            )
            db.add(voice)
            voice_count += 1
        
        db.commit()
        print(f"   ✅ Migrated {voice_count} voices")
        
        sqlite_conn.close()
        db.close()
        
        print()
        print("🎉 Migration complete!")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_from_sqlite()
    exit(0 if success else 1)

