#!/usr/bin/env python3
"""
PostgreSQL Backup Utility with Telegram Integration

This script creates database backups from the PostgreSQL database
(excluding admin table), includes the uploads folder, creates a ZIP archive,
and sends it to a configured Telegram channel.

Runs as a background worker using BACKUP_INTERVAL from environment.

Usage:
    python backup_telegram.py              # Run backup once
    python backup_telegram.py --worker     # Run as background worker
"""

import os
import sys
import subprocess
import requests
import argparse
import time
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

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
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'one2talk')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'one2talk_secure_password')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'one2talk_db')
DATABASE_URL = os.getenv('DATABASE_URL', '')
BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', 3600))

# Determine if running inside Docker
RUNNING_IN_DOCKER = os.path.exists('/.dockerenv') or os.getenv('DATABASE_URL', '').startswith('postgresql://')

# Paths
if RUNNING_IN_DOCKER:
    PROJECT_ROOT = Path('/app')
else:
    PROJECT_ROOT = Path(__file__).parent.parent
    
BACKUP_DIR = PROJECT_ROOT / 'backups'
UPLOADS_DIR = PROJECT_ROOT / 'uploads'

# Database host - 'db' when in Docker, 'localhost' otherwise
DB_HOST = 'db' if RUNNING_IN_DOCKER else 'localhost'

# Tables to backup (exclude admins)
BACKUP_TABLES = ['users', 'categories', 'cards', 'votes', 'settings']


def ensure_backup_dir():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(exist_ok=True)


def get_timestamp():
    """Get formatted timestamp for backup filename"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def run_pg_command(cmd_args: list, capture_output=True):
    """
    Run a PostgreSQL command with proper environment.
    
    Args:
        cmd_args: Command arguments list
        capture_output: Whether to capture output
    
    Returns:
        subprocess.CompletedProcess
    """
    env = os.environ.copy()
    env['PGPASSWORD'] = POSTGRES_PASSWORD
    
    return subprocess.run(
        cmd_args,
        capture_output=capture_output,
        text=True,
        timeout=300,
        env=env
    )


def create_postgres_backup(backup_sql_path: Path):
    """
    Create a PostgreSQL backup using pg_dump.
    Excludes the admins table.
    
    Args:
        backup_sql_path: Path to save the SQL file
    
    Returns:
        bool: Success status
    """
    logger.info("Creating database backup (excluding admin table)...")
    
    try:
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', DB_HOST,
            '-U', POSTGRES_USER,
            '-d', POSTGRES_DB,
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            '--exclude-table=admins'  # Exclude admin table
        ]
        
        result = run_pg_command(cmd)
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return False
        
        # Write backup to file
        with open(backup_sql_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        backup_size = backup_sql_path.stat().st_size
        logger.info(f"SQL backup created: {backup_sql_path.name} ({backup_size / 1024:.2f} KB)")
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Backup timed out after 5 minutes")
        return False
    except FileNotFoundError:
        logger.error("pg_dump not found. Make sure PostgreSQL client tools are installed.")
        return False
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False


def create_zip_backup():
    """
    Create a ZIP backup containing the SQL dump and uploads folder.
    
    Returns:
        tuple: (zip_path, success)
    """
    timestamp = get_timestamp()
    backup_name = f"backup_{POSTGRES_DB}_{timestamp}"
    
    # Temp SQL file
    sql_filename = f"{backup_name}.sql"
    sql_path = BACKUP_DIR / sql_filename
    
    # Final ZIP file
    zip_filename = f"{backup_name}.zip"
    zip_path = BACKUP_DIR / zip_filename
    
    try:
        # Step 1: Create SQL backup
        if not create_postgres_backup(sql_path):
            return None, False
        
        # Step 2: Create ZIP archive
        logger.info(f"Creating ZIP archive: {zip_filename}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add SQL file
            zipf.write(sql_path, sql_filename)
            logger.info(f"  Added: {sql_filename}")
            
            # Add uploads folder contents
            if UPLOADS_DIR.exists():
                upload_files_count = 0
                for file_path in UPLOADS_DIR.rglob('*'):
                    if file_path.is_file():
                        arcname = f"uploads/{file_path.relative_to(UPLOADS_DIR)}"
                        zipf.write(file_path, arcname)
                        upload_files_count += 1
                logger.info(f"  Added: {upload_files_count} files from uploads/")
            else:
                logger.warning("Uploads folder not found, skipping...")
        
        # Clean up temp SQL file
        sql_path.unlink()
        
        zip_size = zip_path.stat().st_size
        logger.info(f"ZIP backup created: {zip_path} ({zip_size / 1024:.2f} KB)")
        
        return zip_path, True
        
    except Exception as e:
        logger.error(f"ZIP creation failed: {str(e)}")
        # Clean up on failure
        if sql_path.exists():
            sql_path.unlink()
        if zip_path.exists():
            zip_path.unlink()
        return None, False


def get_database_stats():
    """
    Get database table statistics (excluding admin table).
    
    Returns:
        dict: Table name -> row count mapping
    """
    stats = {}
    
    try:
        for table in BACKUP_TABLES:
            cmd = [
                'psql',
                '-h', DB_HOST,
                '-U', POSTGRES_USER,
                '-d', POSTGRES_DB,
                '-t', '-c', f"SELECT COUNT(*) FROM {table};"
            ]
            
            result = run_pg_command(cmd)
            
            if result.returncode == 0:
                count = result.stdout.strip()
                stats[table] = int(count) if count.isdigit() else 0
            else:
                stats[table] = 'N/A'
                
    except Exception as e:
        logger.warning(f"Could not get database stats: {e}")
    
    return stats


def count_upload_files():
    """Count files in uploads folder"""
    if not UPLOADS_DIR.exists():
        return 0
    return sum(1 for f in UPLOADS_DIR.rglob('*') if f.is_file())


def send_to_telegram(zip_path: Path, stats: dict = None):
    """
    Send backup ZIP file to Telegram channel.
    
    Args:
        zip_path: Path to the ZIP file
        stats: Database statistics dict
    
    Returns:
        bool: Success status
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured")
        return False
    
    logger.info(f"Sending backup to Telegram channel: {TELEGRAM_CHAT_ID}")
    
    try:
        # Prepare message caption
        zip_size = zip_path.stat().st_size
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        upload_count = count_upload_files()
        
        caption = f"🗄️ *Database Backup*\n\n"
        caption += f"📅 *Date:* `{timestamp}`\n"
        caption += f"📦 *File:* `{zip_path.name}`\n"
        caption += f"💾 *Size:* `{zip_size / 1024:.2f} KB`\n"
        caption += f"🖼️ *Uploads:* `{upload_count} files`\n"
        
        if stats:
            caption += f"\n📊 *Table Statistics:*\n"
            for table, count in stats.items():
                caption += f"  • {table}: `{count}` rows\n"
            
        # Telegram API endpoint
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        
        # Send file
        with open(zip_path, 'rb') as f:
            files = {'document': (zip_path.name, f)}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info("✅ Backup sent to Telegram successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False
        else:
            logger.error(f"HTTP error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Telegram request timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to send to Telegram: {str(e)}")
        return False


def run_backup():
    """
    Execute a single backup operation.
    
    Returns:
        bool: Success status
    """
    logger.info("=" * 50)
    logger.info("Starting database backup...")
    logger.info(f"Running in Docker: {RUNNING_IN_DOCKER}")
    logger.info(f"Database host: {DB_HOST}")
    
    ensure_backup_dir()
    
    # Create ZIP backup (SQL + uploads)
    zip_path, success = create_zip_backup()
    
    if not success or not zip_path:
        logger.error("❌ Backup creation failed")
        return False
    
    # Get database stats
    stats = get_database_stats()
    
    # Send to Telegram
    telegram_success = send_to_telegram(zip_path, stats)
    
    if telegram_success:
        logger.info("✅ Backup completed successfully")
    else:
        logger.warning("⚠️ Backup created but Telegram delivery failed")
    
    return telegram_success


def run_worker():
    """Run as a background worker with BACKUP_INTERVAL from environment"""
    logger.info("=" * 50)
    logger.info("🚀 Starting backup worker...")
    logger.info(f"   Running in Docker: {RUNNING_IN_DOCKER}")
    logger.info(f"   Database host: {DB_HOST}")
    logger.info(f"   Interval: {BACKUP_INTERVAL} seconds ({BACKUP_INTERVAL // 60} minutes)")
    logger.info(f"   Telegram Channel: {TELEGRAM_CHAT_ID}")
    logger.info("=" * 50)
    
    # Initial delay to allow database to fully start
    logger.info("Waiting 30 seconds for database to be ready...")
    time.sleep(30)
    
    while True:
        try:
            run_backup()
        except Exception as e:
            logger.error(f"Backup worker error: {e}")
        
        next_time = datetime.now()
        logger.info(f"💤 Sleeping for {BACKUP_INTERVAL}s... Next backup around {next_time.strftime('%H:%M:%S')}")
        time.sleep(BACKUP_INTERVAL)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='PostgreSQL Backup Utility with Telegram Integration'
    )
    parser.add_argument(
        '--worker', '-w',
        action='store_true',
        help='Run as background worker (uses BACKUP_INTERVAL from environment)'
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set")
        sys.exit(1)
    
    if args.worker:
        run_worker()
    else:
        success = run_backup()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
