#!/usr/bin/env python3
"""
Initialize MySQL database for the project
Creates the database if it doesn't exist, then creates all tables
"""
import pymysql
from sqlalchemy import create_engine, text
from app.config import settings
from app.models import Base, engine, init_db

def create_database_if_not_exists():
    """Create MySQL database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        # Handle empty password for localhost
        connect_kwargs = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'charset': 'utf8mb4'
        }
        # Only add password if it's not empty
        if settings.DB_PASSWORD:
            connect_kwargs['password'] = settings.DB_PASSWORD
        
        connection = pymysql.connect(**connect_kwargs)
        
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
        if "XAMPP" in str(settings.DB_HOST) or settings.DB_HOST == "localhost":
            print(f"     - For XAMPP: Start MySQL from XAMPP Control Panel")
            print(f"     - Check if MySQL is running: lsof -i :3306")
        print(f"  2. User '{settings.DB_USER}' has CREATE DATABASE privileges")
        print(f"  3. Connection details in .env are correct")
        print(f"     - Host: {settings.DB_HOST}")
        print(f"     - Port: {settings.DB_PORT}")
        print(f"     - User: {settings.DB_USER}")
        print(f"     - Password: {'(set)' if settings.DB_PASSWORD else '(empty - OK for XAMPP)'}")
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
    print(f"   Password: {'(set)' if settings.DB_PASSWORD else '(empty - OK for XAMPP)'}")
    print(f"   Database: {settings.DB_NAME}")
    print()
    
    # Check if MySQL is running
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((settings.DB_HOST, settings.DB_PORT))
        sock.close()
        if result != 0:
            print(f"⚠️  Warning: Cannot connect to MySQL on {settings.DB_HOST}:{settings.DB_PORT}")
            print(f"   Please ensure MySQL is running")
            if settings.DB_HOST == "localhost":
                print(f"   For XAMPP: Start MySQL from XAMPP Control Panel")
            return False
    except Exception as e:
        print(f"⚠️  Warning: Could not check MySQL connection: {e}")
    
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

