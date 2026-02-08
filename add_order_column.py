
import sqlite3

def add_column():
    print("Checking if 'order' column exists in 'cards' table...")
    conn = sqlite3.connect('votes.db')
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(cards)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'order' in columns:
            print("'order' column already exists.")
        else:
            print("Adding 'order' column...")
            cursor.execute("ALTER TABLE cards ADD COLUMN 'order' INTEGER DEFAULT 0")
            conn.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
