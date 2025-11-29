#!/usr/bin/env python3
"""
Migration script to update video_url column from VARCHAR(1000) to TEXT
Run this after updating the model to fix the "Data too long" error
"""
import pymysql
from app.config import settings
from sqlalchemy import create_engine, text

def migrate_video_url_column():
    """Update video_url column to TEXT type"""
    try:
        # Connect to MySQL
        connect_kwargs = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'database': settings.DB_NAME,
            'charset': 'utf8mb4'
        }
        if settings.DB_PASSWORD:
            connect_kwargs['password'] = settings.DB_PASSWORD
        
        connection = pymysql.connect(**connect_kwargs)
        
        try:
            with connection.cursor() as cursor:
                # Check current column type
                cursor.execute("""
                    SELECT COLUMN_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'video_download' 
                    AND COLUMN_NAME = 'video_url'
                """, (settings.DB_NAME,))
                
                result = cursor.fetchone()
                if result:
                    current_type = result[0]
                    print(f"Current video_url column type: {current_type}")
                    
                    if 'varchar' in current_type.lower() or 'char' in current_type.lower():
                        print("Updating video_url column to TEXT...")
                        cursor.execute("""
                            ALTER TABLE video_download 
                            MODIFY COLUMN video_url TEXT DEFAULT ''
                        """)
                        connection.commit()
                        print("✅ Successfully updated video_url column to TEXT")
                    else:
                        print(f"✅ Column is already TEXT or compatible type: {current_type}")
                else:
                    print("⚠️  video_url column not found. Table may need to be created.")
        
        finally:
            connection.close()
            
        return True
    except Exception as e:
        print(f"❌ Error migrating video_url column: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔄 Migrating video_url column...")
    print(f"   Database: {settings.DB_NAME}")
    print(f"   Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print()
    
    success = migrate_video_url_column()
    
    if success:
        print()
        print("🎉 Migration complete!")
    else:
        print()
        print("❌ Migration failed. Please check the error messages above.")
        exit(1)

