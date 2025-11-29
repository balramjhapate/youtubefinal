#!/bin/bash
# Script to remove Django-related files and directories

echo "🧹 Cleaning up Django-related files..."

# Remove Django directories
echo "Removing Django directories..."
rm -rf downloader/
rm -rf rednote_project/
rm -rf __pycache__/
rm -rf *.pyc

# Remove Django files
echo "Removing Django files..."
rm -f manage.py
rm -f requirements.txt  # Django requirements
rm -f db.sqlite3  # SQLite database (we're using MySQL now)

# Remove old HTML/JS files (not needed for FastAPI)
echo "Removing old frontend files..."
rm -f index.html
rm -f download_form.js
rm -f rednote_js.js
rm -f script.js
rm -f seekin_js.js
rm -f style.css
rm -f xhs_page.html
rm -f xhs_page_2.html
rm -f seekin_source.html

# Remove old server files
rm -f server_old.py
rm -f get-pip.py

# Remove test files (can be recreated if needed)
rm -f test_nca_integration.py
rm -f test_xhs.py
rm -f reproduce_download_error.py

echo "✅ Django cleanup complete!"
echo ""
echo "Remaining FastAPI files:"
echo "  - app/ (FastAPI application)"
echo "  - requirements_fastapi.txt"
echo "  - run_fastapi.py"
echo "  - init_database.py"
echo "  - migrate_from_sqlite.py"
echo "  - Documentation files (*.md)"

