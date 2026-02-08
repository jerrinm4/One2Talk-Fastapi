#!/usr/bin/env python3
"""
Database Backup Utility for One2Talk-Fastapi
Supports PostgreSQL and SQLite databases with image backup and server export.
"""
import sys
import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect
from database import SessionLocal, engine
from models import User, Category, Card, Vote, Admin, Settings
from config import DATABASE_URL

# Constants
BACKUP_DIR = Path(__file__).parent.parent / "backups"
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("=" * 60)
    print("        🗄️  ONE2TALK DATABASE BACKUP UTILITY  🗄️")
    print("=" * 60)
    print()


def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(exist_ok=True)
    return BACKUP_DIR


def export_table_to_json(db, model_class):
    """Export a table to JSON format."""
    rows = db.query(model_class).all()
    data = []
    
    # Get column names from model
    mapper = inspect(model_class)
    columns = [c.key for c in mapper.columns]
    
    for row in rows:
        row_dict = {}
        for col in columns:
            value = getattr(row, col)
            # Handle datetime serialization
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            row_dict[col] = value
        data.append(row_dict)
    
    return data


def backup_database_json(db, backup_path: Path):
    """Backup all tables to JSON files."""
    tables = {
        'users': User,
        'categories': Category,
        'cards': Card,
        'votes': Vote,
        'admins': Admin,
        'settings': Settings
    }
    
    db_backup = {}
    for table_name, model_class in tables.items():
        try:
            data = export_table_to_json(db, model_class)
            db_backup[table_name] = data
            print(f"  ✓ {table_name}: {len(data)} records")
        except Exception as e:
            print(f"  ✗ {table_name}: Error - {e}")
            db_backup[table_name] = []
    
    # Save to JSON file
    json_path = backup_path / "database.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(db_backup, f, indent=2, ensure_ascii=False)
    
    return json_path


def backup_images(backup_path: Path):
    """Copy all uploaded images to backup folder."""
    images_backup_path = backup_path / "uploads"
    
    if not UPLOADS_DIR.exists():
        print("  ⚠ No uploads directory found")
        return None
    
    image_count = 0
    images_backup_path.mkdir(exist_ok=True)
    
    for file in UPLOADS_DIR.iterdir():
        if file.is_file():
            shutil.copy2(file, images_backup_path / file.name)
            image_count += 1
    
    print(f"  ✓ Copied {image_count} images")
    return images_backup_path


def create_backup_zip(backup_path: Path, timestamp: str):
    """Create a compressed ZIP archive of the backup."""
    zip_name = f"backup_{timestamp}.zip"
    zip_path = BACKUP_DIR / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in backup_path.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(backup_path)
                zipf.write(file, arcname)
    
    # Remove uncompressed backup folder
    shutil.rmtree(backup_path)
    
    return zip_path


def full_backup():
    """Perform a full backup of database and images."""
    print("\n📦 Starting Full Backup...")
    print("-" * 40)
    
    timestamp = get_timestamp()
    backup_path = ensure_backup_dir() / f"backup_{timestamp}"
    backup_path.mkdir(exist_ok=True)
    
    db = SessionLocal()
    try:
        # Backup database
        print("\n🗄️  Backing up database...")
        backup_database_json(db, backup_path)
        
        # Backup images
        print("\n🖼️  Backing up images...")
        backup_images(backup_path)
        
        # Create ZIP archive
        print("\n📦 Creating compressed archive...")
        zip_path = create_backup_zip(backup_path, timestamp)
        
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Backup completed successfully!")
        print(f"   📁 File: {zip_path.name}")
        print(f"   📊 Size: {size_mb:.2f} MB")
        print(f"   📍 Location: {zip_path}")
        
    except Exception as e:
        print(f"\n❌ Backup failed: {e}")
    finally:
        db.close()
    
    input("\nPress Enter to continue...")


def database_only_backup():
    """Backup only the database (no images)."""
    print("\n🗄️  Starting Database-Only Backup...")
    print("-" * 40)
    
    timestamp = get_timestamp()
    backup_path = ensure_backup_dir()
    json_path = backup_path / f"database_{timestamp}.json"
    
    db = SessionLocal()
    try:
        tables = {
            'users': User,
            'categories': Category,
            'cards': Card,
            'votes': Vote,
            'admins': Admin,
            'settings': Settings
        }
        
        db_backup = {'_metadata': {
            'timestamp': timestamp,
            'database_url': DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'
        }}
        
        print()
        for table_name, model_class in tables.items():
            try:
                data = export_table_to_json(db, model_class)
                db_backup[table_name] = data
                print(f"  ✓ {table_name}: {len(data)} records")
            except Exception as e:
                print(f"  ✗ {table_name}: Error - {e}")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(db_backup, f, indent=2, ensure_ascii=False)
        
        size_kb = json_path.stat().st_size / 1024
        print(f"\n✅ Database backup completed!")
        print(f"   📁 File: {json_path.name}")
        print(f"   📊 Size: {size_kb:.2f} KB")
        
    except Exception as e:
        print(f"\n❌ Backup failed: {e}")
    finally:
        db.close()
    
    input("\nPress Enter to continue...")


def export_to_server():
    """Export backup to a remote server via SCP/SFTP."""
    print("\n🌐 Export to Server")
    print("-" * 40)
    
    # List available backups
    backups = list(BACKUP_DIR.glob("*.zip")) + list(BACKUP_DIR.glob("*.json"))
    
    if not backups:
        print("\n⚠ No backups found. Please create a backup first.")
        input("\nPress Enter to continue...")
        return
    
    print("\nAvailable backups:")
    for i, backup in enumerate(backups, 1):
        size = backup.stat().st_size / 1024
        unit = "KB"
        if size > 1024:
            size = size / 1024
            unit = "MB"
        print(f"  {i}. {backup.name} ({size:.2f} {unit})")
    
    print(f"\n  0. Cancel")
    
    try:
        choice = int(input("\nSelect backup to export (number): "))
        if choice == 0:
            return
        if choice < 1 or choice > len(backups):
            print("Invalid selection.")
            input("\nPress Enter to continue...")
            return
        
        selected_backup = backups[choice - 1]
        
        print("\n📡 Server Configuration")
        print("-" * 40)
        host = input("Server hostname/IP: ").strip()
        user = input("Username: ").strip()
        remote_path = input("Remote path (default: ~/backups/): ").strip() or "~/backups/"
        
        if not host or not user:
            print("❌ Invalid server configuration.")
            input("\nPress Enter to continue...")
            return
        
        # Use SCP for file transfer
        scp_command = f'scp "{selected_backup}" {user}@{host}:{remote_path}'
        
        print(f"\n🚀 Executing: {scp_command}")
        print("\n(You may be prompted for password)")
        
        result = os.system(scp_command)
        
        if result == 0:
            print(f"\n✅ Successfully exported to {host}:{remote_path}")
        else:
            print(f"\n❌ Export failed with code {result}")
            print("   Make sure SSH/SCP is available and server is reachable.")
        
    except ValueError:
        print("Invalid input.")
    
    input("\nPress Enter to continue...")


def restore_from_backup():
    """Restore database from a JSON backup file."""
    print("\n🔄 Restore from Backup")
    print("-" * 40)
    print("\n⚠️  WARNING: This will OVERWRITE existing data!")
    
    # List available JSON backups
    backups = list(BACKUP_DIR.glob("database_*.json"))
    zip_backups = list(BACKUP_DIR.glob("*.zip"))
    
    all_backups = backups + zip_backups
    
    if not all_backups:
        print("\n⚠ No backups found in backup directory.")
        input("\nPress Enter to continue...")
        return
    
    print("\nAvailable backups:")
    for i, backup in enumerate(all_backups, 1):
        size = backup.stat().st_size / 1024
        unit = "KB"
        if size > 1024:
            size = size / 1024
            unit = "MB"
        print(f"  {i}. {backup.name} ({size:.2f} {unit})")
    
    print(f"\n  0. Cancel")
    
    try:
        choice = int(input("\nSelect backup to restore (number): "))
        if choice == 0:
            return
        if choice < 1 or choice > len(all_backups):
            print("Invalid selection.")
            input("\nPress Enter to continue...")
            return
        
        selected_backup = all_backups[choice - 1]
        
        confirm = input(f"\n⚠️  Restore from '{selected_backup.name}'? This cannot be undone! (yes/no): ")
        if confirm.lower() != 'yes':
            print("Restore cancelled.")
            input("\nPress Enter to continue...")
            return
        
        print("\n🔄 Restoring...")
        
        # Handle ZIP files
        if selected_backup.suffix == '.zip':
            temp_dir = BACKUP_DIR / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(selected_backup, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            json_file = temp_dir / "database.json"
            uploads_dir = temp_dir / "uploads"
        else:
            json_file = selected_backup
            uploads_dir = None
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        db = SessionLocal()
        try:
            # Restore each table
            model_map = {
                'settings': Settings,
                'admins': Admin,
                'users': User,
                'categories': Category,
                'cards': Card,
                'votes': Vote,
            }
            
            for table_name, model_class in model_map.items():
                if table_name in backup_data and table_name != '_metadata':
                    # Clear existing data
                    db.query(model_class).delete()
                    
                    # Insert backup data
                    for row_data in backup_data[table_name]:
                        # Remove datetime fields that will be auto-generated
                        if 'created_at' in row_data:
                            del row_data['created_at']
                        if 'updated_at' in row_data:
                            del row_data['updated_at']
                        
                        obj = model_class(**row_data)
                        db.add(obj)
                    
                    print(f"  ✓ {table_name}: {len(backup_data[table_name])} records restored")
            
            db.commit()
            
            # Restore images if available
            if uploads_dir and uploads_dir.exists():
                print("\n🖼️  Restoring images...")
                for file in uploads_dir.iterdir():
                    if file.is_file():
                        shutil.copy2(file, UPLOADS_DIR / file.name)
                print(f"  ✓ Images restored")
            
            print("\n✅ Restore completed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"\n❌ Restore failed: {e}")
        finally:
            db.close()
            
            # Cleanup temp directory
            if selected_backup.suffix == '.zip':
                shutil.rmtree(temp_dir, ignore_errors=True)
        
    except ValueError:
        print("Invalid input.")
    
    input("\nPress Enter to continue...")


def list_backups():
    """List all available backups."""
    print("\n📋 Available Backups")
    print("-" * 40)
    
    ensure_backup_dir()
    backups = sorted(BACKUP_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not backups:
        print("\nNo backups found.")
    else:
        print(f"\nBackup directory: {BACKUP_DIR}")
        print()
        total_size = 0
        for backup in backups:
            if backup.is_file():
                size = backup.stat().st_size
                total_size += size
                size_str = f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.2f} MB"
                mtime = datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"  📁 {backup.name}")
                print(f"     Size: {size_str} | Modified: {mtime}")
        
        print(f"\n  Total: {len([b for b in backups if b.is_file()])} files, {total_size / (1024*1024):.2f} MB")
    
    input("\nPress Enter to continue...")


def show_db_info():
    """Show current database connection info."""
    print("\n📊 Database Information")
    print("-" * 40)
    
    # Mask password in URL
    masked_url = DATABASE_URL
    if '@' in DATABASE_URL:
        parts = DATABASE_URL.split('@')
        prefix = parts[0].rsplit(':', 1)[0]
        masked_url = f"{prefix}:****@{parts[1]}"
    
    print(f"\n  Database URL: {masked_url}")
    
    db = SessionLocal()
    try:
        print("\n  Table Statistics:")
        tables = {
            'Users': User,
            'Categories': Category,
            'Cards': Card,
            'Votes': Vote,
            'Admins': Admin,
            'Settings': Settings
        }
        
        for name, model in tables.items():
            count = db.query(model).count()
            print(f"    • {name}: {count} records")
            
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
    finally:
        db.close()
    
    input("\nPress Enter to continue...")


def create_remote_session(db_url: str):
    """Create a database session for a remote database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Clean up the URL if needed
    db_url = db_url.strip()
    if db_url.startswith("postgresql://"):
        remote_engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    else:
        raise ValueError("Invalid database URL. Must start with 'postgresql://'")
    
    RemoteSession = sessionmaker(autocommit=False, autoflush=False, bind=remote_engine)
    return RemoteSession(), remote_engine


def export_to_remote_db():
    """Export current database to a remote PostgreSQL database."""
    print("\n🌐 Export to Remote Database")
    print("-" * 40)
    print("\nThis will COPY data from the current database to a remote database.")
    print("⚠️  WARNING: This will OVERWRITE data in the remote database!\n")
    
    remote_url = input("Enter remote database URL:\n> ").strip()
    
    if not remote_url:
        print("❌ No URL provided.")
        input("\nPress Enter to continue...")
        return
    
    # Mask password for display
    if '@' in remote_url:
        parts = remote_url.split('@')
        prefix = parts[0].rsplit(':', 1)[0]
        masked_url = f"{prefix}:****@{parts[1]}"
    else:
        masked_url = remote_url
    
    print(f"\n📡 Target: {masked_url}")
    
    confirm = input("\n⚠️  Proceed with export? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Export cancelled.")
        input("\nPress Enter to continue...")
        return
    
    print("\n🔄 Connecting to remote database...")
    
    try:
        remote_db, remote_engine = create_remote_session(remote_url)
        
        # Create tables on remote if they don't exist
        from models import Base
        Base.metadata.create_all(bind=remote_engine)
        print("  ✓ Connected and tables verified")
        
        # Get data from local database
        local_db = SessionLocal()
        
        tables = {
            'settings': Settings,
            'admins': Admin,
            'users': User,
            'categories': Category,
            'cards': Card,
            'votes': Vote,
        }
        
        print("\n📤 Exporting data...")
        
        for table_name, model_class in tables.items():
            try:
                # Get data from local
                local_data = export_table_to_json(local_db, model_class)
                
                # Clear remote table
                remote_db.query(model_class).delete()
                
                # Insert into remote
                for row_data in local_data:
                    # Remove auto-generated datetime fields
                    row_copy = row_data.copy()
                    if 'created_at' in row_copy:
                        del row_copy['created_at']
                    if 'updated_at' in row_copy:
                        del row_copy['updated_at']
                    
                    obj = model_class(**row_copy)
                    remote_db.add(obj)
                
                remote_db.commit()
                print(f"  ✓ {table_name}: {len(local_data)} records exported")
                
            except Exception as e:
                remote_db.rollback()
                print(f"  ✗ {table_name}: Error - {e}")
        
        print("\n✅ Export to remote database completed!")
        
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
    finally:
        try:
            local_db.close()
            remote_db.close()
        except:
            pass
    
    input("\nPress Enter to continue...")


def import_from_remote_db():
    """Import data from a remote PostgreSQL database to current database."""
    print("\n📥 Import from Remote Database")
    print("-" * 40)
    print("\nThis will COPY data from a remote database to the current database.")
    print("⚠️  WARNING: This will OVERWRITE data in the current database!\n")
    
    remote_url = input("Enter remote database URL:\n> ").strip()
    
    if not remote_url:
        print("❌ No URL provided.")
        input("\nPress Enter to continue...")
        return
    
    # Mask password for display
    if '@' in remote_url:
        parts = remote_url.split('@')
        prefix = parts[0].rsplit(':', 1)[0]
        masked_url = f"{prefix}:****@{parts[1]}"
    else:
        masked_url = remote_url
    
    print(f"\n📡 Source: {masked_url}")
    
    confirm = input("\n⚠️  Proceed with import? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Import cancelled.")
        input("\nPress Enter to continue...")
        return
    
    print("\n🔄 Connecting to remote database...")
    
    try:
        remote_db, remote_engine = create_remote_session(remote_url)
        print("  ✓ Connected to remote database")
        
        # Get local database session
        local_db = SessionLocal()
        
        tables = {
            'settings': Settings,
            'admins': Admin,
            'users': User,
            'categories': Category,
            'cards': Card,
            'votes': Vote,
        }
        
        print("\n📥 Importing data...")
        
        for table_name, model_class in tables.items():
            try:
                # Get data from remote
                remote_data = export_table_to_json(remote_db, model_class)
                
                # Clear local table
                local_db.query(model_class).delete()
                
                # Insert into local
                for row_data in remote_data:
                    # Remove auto-generated datetime fields
                    row_copy = row_data.copy()
                    if 'created_at' in row_copy:
                        del row_copy['created_at']
                    if 'updated_at' in row_copy:
                        del row_copy['updated_at']
                    
                    obj = model_class(**row_copy)
                    local_db.add(obj)
                
                local_db.commit()
                print(f"  ✓ {table_name}: {len(remote_data)} records imported")
                
            except Exception as e:
                local_db.rollback()
                print(f"  ✗ {table_name}: Error - {e}")
        
        print("\n✅ Import from remote database completed!")
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
    finally:
        try:
            local_db.close()
            remote_db.close()
        except:
            pass
    
    input("\nPress Enter to continue...")


def main_menu():
    """Display main menu and handle user input."""
    while True:
        clear_screen()
        print_header()
        
        print("  ┌─ Local Backups ─────────────────────┐")
        print("  │  1. 📦 Full Backup (DB + Images)    │")
        print("  │  2. 🗄️  Database Only Backup        │")
        print("  │  3. 🔄 Restore from Backup          │")
        print("  │  4. 📋 List Backups                 │")
        print("  └─────────────────────────────────────┘")
        print()
        print("  ┌─ Remote Database Transfer ──────────┐")
        print("  │  5. 📤 Export to Remote Database    │")
        print("  │  6. 📥 Import from Remote Database  │")
        print("  │  7. 🌐 Export Backup File (SCP)     │")
        print("  └─────────────────────────────────────┘")
        print()
        print("  ┌─ Info ──────────────────────────────┐")
        print("  │  8. 📊 Database Info                │")
        print("  │  0. 🚪 Exit                         │")
        print("  └─────────────────────────────────────┘")
        print()
        
        try:
            choice = input("Select option: ").strip()
            
            if choice == '1':
                full_backup()
            elif choice == '2':
                database_only_backup()
            elif choice == '3':
                restore_from_backup()
            elif choice == '4':
                list_backups()
            elif choice == '5':
                export_to_remote_db()
            elif choice == '6':
                import_from_remote_db()
            elif choice == '7':
                export_to_server()
            elif choice == '8':
                show_db_info()
            elif choice == '0':
                print("\nGoodbye! 👋")
                break
            else:
                print("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            break


if __name__ == "__main__":
    main_menu()

