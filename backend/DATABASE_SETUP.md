# MySQL Database Setup Guide

## Prerequisites

1. **MySQL Server** must be installed and running
2. **MySQL User** with CREATE DATABASE privileges
3. **Python packages** installed (see requirements_fastapi.txt)

## Quick Setup

### 1. Configure Database Connection

Create a `.env` file in the `backend` directory:

```env
# Database - MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=youtubefinal
```

### 2. Initialize Database

Run the initialization script:

```bash
cd backend
python init_database.py
```

This will:
- Create the `youtubefinal` database if it doesn't exist
- Create all required tables
- Set up the database schema

### 3. (Optional) Migrate from SQLite

If you have an existing SQLite database with data:

```bash
python migrate_from_sqlite.py
```

This will migrate all data from `db.sqlite3` to MySQL.

### 4. Start the Application

```bash
python run_fastapi.py
```

## Manual Setup

If you prefer to set up the database manually:

### 1. Create Database

```sql
CREATE DATABASE youtubefinal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Create User (Optional)

```sql
CREATE USER 'youtubefinal_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON youtubefinal.* TO 'youtubefinal_user'@'localhost';
FLUSH PRIVILEGES;
```

Then update `.env`:
```env
DB_USER=youtubefinal_user
DB_PASSWORD=your_password
```

### 3. Run Initialization

```bash
python init_database.py
```

## Database Schema

The following tables are created:

- **ai_provider_settings** - AI provider configuration
- **video_download** - Video records and processing status
- **saved_voice** - Saved voice profiles for XTTS

## Troubleshooting

### Connection Refused

```
Error: Can't connect to MySQL server
```

**Solutions:**
- Check if MySQL server is running: `sudo systemctl status mysql` (Linux) or check MySQL service (Windows/Mac)
- Verify host and port in `.env`
- Check firewall settings

### Access Denied

```
Error: Access denied for user
```

**Solutions:**
- Verify username and password in `.env`
- Check if user has CREATE DATABASE privileges
- Try connecting with MySQL client: `mysql -u root -p`

### Database Already Exists

```
Error: Database 'youtubefinal' already exists
```

**Solutions:**
- This is fine - the script will use the existing database
- If you want to start fresh, drop and recreate:
  ```sql
  DROP DATABASE youtubefinal;
  ```
  Then run `python init_database.py` again

### Character Set Issues

If you see encoding errors, ensure the database uses utf8mb4:

```sql
ALTER DATABASE youtubefinal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Verification

After setup, verify the database:

```bash
mysql -u root -p -e "USE youtubefinal; SHOW TABLES;"
```

You should see:
- ai_provider_settings
- video_download
- saved_voice

## Production Considerations

For production environments:

1. **Use a dedicated database user** (not root)
2. **Set strong passwords**
3. **Enable SSL connections** if possible
4. **Configure connection pooling** (already set in database.py)
5. **Set up backups**
6. **Monitor database performance**

## Connection String Format

The application uses SQLAlchemy with PyMySQL. The connection string format is:

```
mysql+pymysql://user:password@host:port/database?charset=utf8mb4
```

This is automatically constructed from `.env` variables.

## Migration from SQLite

If migrating from SQLite:

1. **Backup SQLite database** (optional but recommended)
2. **Set up MySQL** as described above
3. **Run migration script**: `python migrate_from_sqlite.py`
4. **Verify data** in MySQL
5. **Remove SQLite database** (optional): `rm db.sqlite3`

The migration script will:
- Copy all videos
- Copy AI settings
- Copy saved voices
- Preserve all relationships and data

## Next Steps

After database setup:

1. **Start the FastAPI server**: `python run_fastapi.py`
2. **Test the API** using Swagger UI: http://localhost:8000/docs
3. **Create your first video** via the API

