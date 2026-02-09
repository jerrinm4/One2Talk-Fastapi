#!/usr/bin/env python3
"""
Restore Utility for Database and Uploads from ZIP Backup

Usage:
    python zutilities/restore_backup.py -f <path_to_backup_zip>

This script:
1. Extracts the backup ZIP file to a temporary location.
2. Restores the PostgreSQL database from the SQL dump within the ZIP.
3. Restores the 'uploads' directory content.
4. Cleans up temporary files.
"""

import os
import sys
import shutil
import zipfile
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (for local development)
def load_env():
    """Load environment variables from .env file if running locally"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

# Configuration from environment
POSTGRES_USER = os.getenv('POSTGRES_USER', 'one2talk')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'one2talk_secure_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'one2talk_db')
DATABASE_URL = os.getenv('DATABASE_URL', '')

# Determine if running inside Docker
RUNNING_IN_DOCKER = os.path.exists('/.dockerenv') or os.getenv('DATABASE_URL', '').startswith('postgresql://')

# Paths
if RUNNING_IN_DOCKER:
    PROJECT_ROOT = Path('/app')
else:
    PROJECT_ROOT = Path(__file__).parent.parent
    
UPLOADS_DIR = PROJECT_ROOT / 'uploads'
TEMP_DIR = PROJECT_ROOT / 'temp_restore'

# Database host
DB_HOST = 'db' if RUNNING_IN_DOCKER else 'localhost'


def is_docker_available():
    """Check if docker command is available."""
    return shutil.which('docker') is not None


def is_container_running(container_name):
    """Check if a specific docker container is running."""
    if not is_docker_available():
        return False
    try:
        result = subprocess.run(
            ['docker', 'ps', '-q', '-f', f'name={container_name}'],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False



def extract_backup(zip_path: Path):
    """Extracts the backup ZIP to a temporary directory."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()

    logger.info(f"Extracting {zip_path} to {TEMP_DIR}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_DIR)
        return True
    except Exception as e:
        logger.error(f"Failed to extract backup: {e}")
        return False


def restore_database():
    """Restores the database from the extracted SQL file."""
    # Find the SQL file
    sql_files = list(TEMP_DIR.glob('*.sql'))
    if not sql_files:
        logger.error("No SQL file found in the backup.")
        return False
    
    sql_file = sql_files[0]
    logger.info(f"Restoring database from {sql_file.name}...")

    # Check for Docker container
    db_container = "one2talk_db"
    use_docker = is_container_running(db_container)
    
    if use_docker:
        logger.info(f"Targeting Docker container: {db_container}")
        cmd = [
            'docker', 'exec', '-i', 
            db_container, 
            'psql',
            '-U', POSTGRES_USER,
            '-d', POSTGRES_DB
        ]
        # Environment variables for the container command are set inside the container,
        # usually via the existing env vars or passed explicitly if needed.
        # Here we rely on the user/db existing. PGPASSWORD might be needed if not trusted.
        # But commonly inside the container, we can run psql without password if we are root or matched user,
        # or we assume .pgpass or env vars are set. 
        # Actually, best to pass PGPASSWORD env var to the exec command just in case?
        # docker exec -e PGPASSWORD=... 
        
        # But wait, PGPASSWORD env var passed to subprocess works for 'docker exec' command itself? 
        # No, it needs to be -e inside.
        cmd.insert(3, '-e')
        cmd.insert(4, f'PGPASSWORD={POSTGRES_PASSWORD}')
        
    else:
        logger.info("Targeting local PostgreSQL service (Host)...")
        cmd = [
            'psql',
            '-h', DB_HOST,
            '-U', POSTGRES_USER,
            '-d', POSTGRES_DB
        ]

    try:
        if use_docker:
            # For docker exec -i, we act as the pipe
            # Open as binary to avoid decoding issues, let docker/psql handle it
            with open(sql_file, 'rb') as f:
                result = subprocess.run(
                    cmd,
                    input=f.read(),
                    capture_output=True,
                    text=False, # Return bytes
                    timeout=300
                )
                # Decode stderr for logging (safely)
                stderr_output = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
        else:
            # For local psql, -f is preferred if we didn't use stdin
            cmd.append('-f')
            cmd.append(str(sql_file))
            
            env = os.environ.copy()
            env['PGPASSWORD'] = POSTGRES_PASSWORD
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                encoding='utf-8', # Force UTF-8 for local psql output
                errors='replace'
            )
            stderr_output = result.stderr

        if result.returncode != 0:
            logger.error(f"Database restore failed:\n{stderr_output}")
            if use_docker and "psql: error:" not in stderr_output:
                 logger.info("Tip: Ensure the database container is running and healthy.")
            return False
        
        logger.info("Database restore completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error during database restore: {e}")
        return False


def restore_uploads():
    """Restores the uploads directory."""
    logger.info("Restoring uploads directory...")
    
    extracted_uploads = TEMP_DIR / 'uploads'
    
    if not extracted_uploads.exists():
        logger.warning("'uploads' folder not found in backup. Skipping uploads restore.")
        return True # Not necessarily an error if backup had no uploads

    try:
        # Remove current uploads directory
        if UPLOADS_DIR.exists():
            logger.info("Removing current uploads directory...")
            shutil.rmtree(UPLOADS_DIR)
        
        # Move extracted uploads to target
        shutil.move(str(extracted_uploads), str(UPLOADS_DIR))
        logger.info("Uploads restored successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to restore uploads: {e}")
        return False


def cleanup():
    """Removes temporary files."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        logger.info("Temporary files cleaned up.")


def main():
    parser = argparse.ArgumentParser(description='Restore Database and Uploads from ZIP Backup')
    parser.add_argument('-f', '--file', required=True, help='Path to the backup ZIP file')
    
    args = parser.parse_args()
    zip_path = Path(args.file)

    if not zip_path.exists():
        logger.error(f"Backup file not found: {zip_path}")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info(f"Starting restore process from: {zip_path}")
    logger.info(f"Running in Docker: {RUNNING_IN_DOCKER}")
    logger.info(f"Database Host: {DB_HOST}")
    
    try:
        if not extract_backup(zip_path):
            sys.exit(1)
            
        if not restore_database():
            logger.error("Restore aborted due to database error.")
            sys.exit(1)
            
        if not restore_uploads():
            logger.error("Restore aborted due to uploads error.")
            sys.exit(1)
            
        logger.info("✅ Restore process completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\nRestore process interrupted.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        cleanup()

if __name__ == '__main__':
    main()
