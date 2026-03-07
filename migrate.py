#!/usr/bin/env python3
"""
Database migration management script for Brisk Automations

This script provides convenient commands for managing database migrations
using Alembic.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(command, shell=True):
    """Run a command and return the result"""
    print(f"Running: {command}", flush=True)
    if isinstance(command, str):
        result = subprocess.run(command, shell=shell, capture_output=False, text=True)
    else:
        result = subprocess.run(command, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"Command failed with exit code: {result.returncode}", flush=True)
        sys.exit(1)
    return result

def main():
    if len(sys.argv) < 2:
        print("""
Database Migration Management

Usage:
    python migrate.py <command> [options]

Commands:
    init                    Initialize migration environment (first time setup)
    create <message>        Create a new migration with the given message
    upgrade [revision]      Upgrade to latest or specific revision (default: head)
    downgrade [revision]    Downgrade to previous or specific revision
    current                 Show current revision
    history                 Show migration history
    status                  Show migration status
    reset                   Reset database (⚠️  DANGER: Deletes all data!)

Examples:
    python migrate.py init
    python migrate.py create "Add user table"
    python migrate.py upgrade
    python migrate.py downgrade -1
    python migrate.py current
    python migrate.py history
        """)
        return

    command = sys.argv[1].lower()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable not set!", flush=True)
        sys.exit(1)
    
    # Log database info (mask password)
    if "@" in db_url:
        masked_url = db_url.split("@")[0].rsplit(":", 1)[0] + ":****@" + db_url.split("@")[1]
    else:
        masked_url = db_url
    print(f"Using database: {masked_url}", flush=True)

    if command == "init":
        print("Creating initial migration...", flush=True)
        run_command(["alembic", "revision", "--autogenerate", "-m", "Initial migration"], shell=False)
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Please provide a migration message", flush=True)
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        run_command(["alembic", "revision", "--autogenerate", "-m", message], shell=False)
        
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        
        # Check current state in database directly
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            with engine.connect() as conn:
                try:
                    result = conn.execute(text("SELECT version_num FROM alembic_version"))
                    versions = [row[0] for row in result]
                    if versions:
                        print(f"Current DB version(s): {versions}", flush=True)
                    else:
                        print("No migrations applied yet (alembic_version is empty)", flush=True)
                except Exception as e:
                    print(f"alembic_version table doesn't exist yet: {e}", flush=True)
                
                # Check if tables exist
                result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                print(f"Existing tables: {tables}", flush=True)
        except Exception as e:
            print(f"Could not check DB state: {e}", flush=True)
        
        print(f"Running migrations to {revision}...", flush=True)
        # Run upgrade - use os.system for guaranteed stdout
        exit_code = os.system(f"alembic upgrade {revision}")
        if exit_code != 0:
            print(f"Migration failed with exit code: {exit_code}", flush=True)
            sys.exit(1)
        print("Migrations completed successfully!", flush=True)
        
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        run_command(["alembic", "downgrade", revision], shell=False)
        
    elif command == "current":
        run_command(["alembic", "current"], shell=False)
        
    elif command == "history":
        run_command(["alembic", "history", "--verbose"], shell=False)
        
    elif command == "status":
        print("=== Current Migration Status ===")
        run_command(["alembic", "current"], shell=False)
        print("\n=== Migration History ===")
        run_command(["alembic", "history", "--verbose"], shell=False)
        
    elif command == "reset":
        confirm = input("⚠️  WARNING: This will delete ALL data! Type 'RESET' to confirm: ")
        if confirm == "RESET":
            print("Downgrading to base...")
            run_command(["alembic", "downgrade", "base"], shell=False)
            print("Upgrading to head...")
            run_command(["alembic", "upgrade", "head"], shell=False)
            print("Database reset complete!")
        else:
            print("Reset cancelled.")
            
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
