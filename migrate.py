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
    print(f"Running: {command}")
    if isinstance(command, str):
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
    else:
        result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    print(result.stdout)
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

    if not os.getenv("DATABASE_URL"):
        print("Error: DATABASE_URL environment variable not set!")
        sys.exit(1)

    if command == "init":
        print("Creating initial migration...")
        run_command(["alembic", "revision", "--autogenerate", "-m", "Initial migration"], shell=False)
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Please provide a migration message")
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        run_command(["alembic", "revision", "--autogenerate", "-m", message], shell=False)
        
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_command(["alembic", "upgrade", revision], shell=False)
        
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
