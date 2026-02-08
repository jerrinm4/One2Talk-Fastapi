"""
Migration script to add 'role' column to the admins table.
Run this script once to update existing database.
"""

import sqlite3
import os

def migrate():
    db_path = "votes.db"
    
    if not os.path.exists(db_path):
        print("Database not found. Skipping migration.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if role column exists
    cursor.execute("PRAGMA table_info(admins)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'role' not in columns:
        print("Adding 'role' column to admins table...")
        cursor.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'admin'")
        
        # Set default role for existing admins
        cursor.execute("UPDATE admins SET role = 'admin' WHERE role IS NULL")
        
        conn.commit()
        print("Migration complete: 'role' column added with default value 'admin'")
    else:
        print("Migration already applied: 'role' column exists")
    
    conn.close()

if __name__ == "__main__":
    migrate()
