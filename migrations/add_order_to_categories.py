from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path to import models if needed, though we use raw SQL here for migration simplicity
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SQLALCHEMY_DATABASE_URL

def add_order_column():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        try:
            print("Attempting to add 'order' column to 'categories' table...")
            connection.execute(text("ALTER TABLE categories ADD COLUMN 'order' INTEGER DEFAULT 0"))
            connection.commit()
            print("Column 'order' added successfully.")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("Column 'order' already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_order_column()
