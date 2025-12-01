#!/usr/bin/env python3
"""
Quick verification script to check that all migrations are properly configured
and the Django project can start successfully.
"""

import os
import sys
import django
from pathlib import Path

# Add the project path
project_root = Path(__file__).parent / "legacy" / "root_debris"
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Failed to setup Django: {e}")
    sys.exit(1)

from django.core.management import call_command
from django.db import connection

def check_migrations():
    """Check that all migrations are applied"""
    print("\n" + "="*60)
    print("Checking Migration Status")
    print("="*60)
    
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        
        # Get migration status
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            print(f"❌ {len(plan)} unapplied migration(s) found:")
            for migration, _ in plan:
                print(f"   - {migration}")
            return False
        else:
            print("✅ All migrations are applied")
            return True
    except Exception as e:
        print(f"❌ Error checking migrations: {e}")
        return False

def check_system():
    """Run Django system check"""
    print("\n" + "="*60)
    print("Running Django System Check")
    print("="*60)
    
    try:
        call_command('check', verbosity=0)
        print("✅ System check passed - no issues found")
        return True
    except Exception as e:
        print(f"❌ System check failed: {e}")
        return False

def check_database():
    """Check database connectivity"""
    print("\n" + "="*60)
    print("Checking Database Connection")
    print("="*60)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    print("="*60)
    print("Django Project Setup Verification")
    print("="*60)
    
    results = []
    
    # Run checks
    results.append(("Database Connection", check_database()))
    results.append(("Migrations", check_migrations()))
    results.append(("System Check", check_system()))
    
    # Summary
    print("\n" + "="*60)
    print("Verification Summary")
    print("="*60)
    
    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All checks passed! Project is ready to run.")
        print("\nYou can now:")
        print("  - Run the project: ./run_project.sh")
        print("  - Run tests: python manage.py test")
        print("  - Start Django server: python manage.py runserver")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

