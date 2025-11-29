#!/usr/bin/env python3
"""
Initialize MySQL database for the project
Creates the database if it doesn't exist, then creates all tables
"""
import pymysql
from sqlalchemy import create_engine, text
from app.config import settings
from app.database import Base, engine, init_db

def create_database_if_not_exists():
    """Create MySQL database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Database '{settings.DB_NAME}' is ready")
        
        connection.close()
        return True
    except pymysql.Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        print(f"\nPlease ensure:")
        print(f"  1. MySQL server is running")
        print(f"  2. User '{settings.DB_USER}' has CREATE DATABASE privileges")
        print(f"  3. Connection details in .env are correct")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def create_tables():
    """Create all tables in the database"""
    try:
        print(f"📦 Creating tables in database '{settings.DB_NAME}'...")
        init_db()
        print("✅ All tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to initialize database"""
    print("🚀 Initializing MySQL database...")
    print(f"   Host: {settings.DB_HOST}")
    print(f"   Port: {settings.DB_PORT}")
    print(f"   User: {settings.DB_USER}")
    print(f"   Database: {settings.DB_NAME}")
    print()
    
    # Step 1: Create database
    if not create_database_if_not_exists():
        return False
    
    # Step 2: Create tables
    if not create_tables():
        return False
    
    print()
    print("🎉 Database initialization complete!")
    print(f"   You can now run the FastAPI server: python run_fastapi.py")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

