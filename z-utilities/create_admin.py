from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Admin
import auth
import sys

def create_admin():
    print("Creating Admin User (Direct DB Connection)")
    username = input("Enter Admin Username: ")
    password = input("Enter Admin Password: ")

    db = SessionLocal()
    try:
        # Check if admin exists
        if db.query(Admin).filter(Admin.username == username).first():
            print(f"Error: Admin with username '{username}' already exists.")
            return

        hashed_password = auth.get_password_hash(password)
        admin = Admin(username=username, password_hash=hashed_password)
        db.add(admin)
        db.commit()
        print(f"Admin '{username}' created successfully!")
        
    except Exception as e:
        print(f"Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
