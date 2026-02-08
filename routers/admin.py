from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
import shutil
import os
import uuid
import time
import hashlib

from database import get_db
from models import User, Category, Card, Vote, Admin, Settings
import schemas
import auth

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)

# Simple cache for dashboard stats (30 second TTL)
_dashboard_cache = {"data": None, "timestamp": 0}
DASHBOARD_CACHE_TTL = 30  # seconds

def invalidate_dashboard_cache():
    global _dashboard_cache
    _dashboard_cache = {"data": None, "timestamp": 0}

# Login
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Admin).filter(Admin.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role or "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role or "admin"}

# Protected Dependency (any admin)
def get_current_admin_user(current_user: Admin = Depends(auth.get_current_admin)):
    return current_user

# Protected Dependency (full admin only)
def require_full_admin(current_user: Admin = Depends(auth.require_full_admin)):
    return current_user

# Dashboard Stats
@router.get("/dashboard-stats")
def get_dashboard_stats(current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    global _dashboard_cache
    
    # Return cached data if still valid
    if _dashboard_cache["data"] and (time.time() - _dashboard_cache["timestamp"]) < DASHBOARD_CACHE_TTL:
        return _dashboard_cache["data"]
    
    total_votes = db.query(Vote).count()
    total_users = db.query(User).count()
    total_categories = db.query(Category).count()
    
    categories = db.query(Category).all()
    
    category_stats = []
    for cat in categories:
        cat_total_votes = db.query(Vote).filter(Vote.category_id == cat.id).count()
        card_stats = []
        for card in cat.cards:
            card_votes = db.query(Vote).filter(Vote.card_id == card.id).count()
            card_stats.append({
                "id": card.id,
                "title": card.title,
                "image_url": card.image_url,
                "votes": card_votes,
                "percentage": round((card_votes / cat_total_votes * 100), 1) if cat_total_votes > 0 else 0 
            })
        
        # Sort cards by votes desc for "who wins"
        card_stats.sort(key=lambda x: x["votes"], reverse=True)
        
        category_stats.append({
            "id": cat.id,
            "name": cat.name,
            "total_votes": cat_total_votes,
            "cards": card_stats
        })

    result = {
        "total_votes": total_votes,
        "total_users": total_users,
        "total_categories": total_categories,
        "category_stats": category_stats
    }
    
    # Update cache
    _dashboard_cache["data"] = result
    _dashboard_cache["timestamp"] = time.time()

    return result

# Category Management (Full Admin Only)
@router.post("/categories", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    existing_category = db.query(Category).filter(Category.name == category.name).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    invalidate_dashboard_cache()
    return db_category

@router.get("/categories", response_model=List[schemas.Category])
def get_categories(current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.order.asc()).all()

@router.put("/categories/reorder")
def reorder_categories(payload: schemas.CategoryReorderRequest, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    # payload.items is a list of category IDs in the new order
    for index, cat_id in enumerate(payload.items):
        db.query(Category).filter(Category.id == cat_id).update({"order": index})
    db.commit()
    invalidate_dashboard_cache()
    return {"message": "Categories reordered successfully"}

@router.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(category_id: int, category_update: schemas.CategoryUpdate, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_category.name = category_update.name
    db.commit()
    db.refresh(db_category)
    invalidate_dashboard_cache()
    return db_category

@router.get("/categories/{category_id}/dependencies")
def get_category_dependencies(category_id: int, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    card_count = db.query(Card).filter(Card.category_id == category_id).count()
    vote_count = db.query(Vote).filter(Vote.category_id == category_id).count()
    return {"card_count": card_count, "vote_count": vote_count}

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, delete_data: schemas.CategoryDelete, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for connections
    cards = db.query(Card).filter(Card.category_id == category_id).all()
    votes = db.query(Vote).filter(Vote.category_id == category_id).all()
    
    is_dirty = len(cards) > 0 or len(votes) > 0

    if is_dirty:
        # Require Password for Dirty Deletes
        if not delete_data.password or not auth.verify_password(delete_data.password, current_user.password_hash):
            raise HTTPException(status_code=403, detail="Password required to delete category with existing data.")
        
        # Manual Cascade Delete
        # Delete Votes
        for vote in votes:
            db.delete(vote)
        
        # Delete Cards
        for card in cards:
            db.delete(card)
            
    # If clean, we allow deletion without extra password (user already authenticated via JWT)

    db.delete(db_category)
    db.commit()
    invalidate_dashboard_cache()
    return {"message": "Category deleted successfully"}

# Card Management (Full Admin Only)
@router.post("/cards", response_model=schemas.Card)
def create_card(card: schemas.CardCreate, category_id: int, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    db_card = Card(**card.dict(), category_id=category_id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    invalidate_dashboard_cache()
    return db_card

@router.put("/cards/{card_id}", response_model=schemas.Card)
def update_card(card_id: int, card_update: schemas.CardUpdate, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    db_card = db.query(Card).filter(Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db_card.title = card_update.title
    if card_update.subtitle is not None:
        db_card.subtitle = card_update.subtitle
    if card_update.image_url is not None:
        db_card.image_url = card_update.image_url
        
    db.commit()
    db.refresh(db_card)
    invalidate_dashboard_cache()
    return db_card

@router.get("/cards/{card_id}/dependencies")
def get_card_dependencies(card_id: int, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    vote_count = db.query(Vote).filter(Vote.card_id == card_id).count()
    return {"vote_count": vote_count}

@router.delete("/cards/{card_id}")
def delete_card(card_id: int, delete_data: schemas.CardDelete, current_user: Admin = Depends(require_full_admin), db: Session = Depends(get_db)):
    db_card = db.query(Card).filter(Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")

    votes = db.query(Vote).filter(Vote.card_id == card_id).all()
    is_dirty = len(votes) > 0

    if is_dirty:
        if not delete_data.password or not auth.verify_password(delete_data.password, current_user.password_hash):
            raise HTTPException(status_code=403, detail="Password required to delete card with existing votes.")
        
        for vote in votes:
            db.delete(vote)
    
    db.delete(db_card)
    db.commit()
    invalidate_dashboard_cache()
    return {"message": "Card deleted successfully"}

# File Upload (Full Admin Only)
@router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user: Admin = Depends(require_full_admin)):
    UPLOAD_DIR = "uploads"
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    # Calculate SHA256 hash
    sha256_hash = hashlib.sha256()
    for byte_block in iter(lambda: file.file.read(4096), b""):
        sha256_hash.update(byte_block)
    
    # Reset file cursor
    file.file.seek(0)
    
    file_extension = file.filename.split(".")[-1]
    filename = f"{sha256_hash.hexdigest()}.{file_extension}"
    file_location = f"{UPLOAD_DIR}/{filename}"
    
    # Check if file exists
    if os.path.exists(file_location):
        return {"url": f"/uploads/{filename}"}
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    return {"url": f"/uploads/{filename}"}

# User Management (Full Admin Only)
@router.get("/users")
def get_users(
    page: int = 1, 
    limit: int = 10, 
    search: str = "", 
    current_user: Admin = Depends(require_full_admin), 
    db: Session = Depends(get_db)
):
    query = db.query(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.phone.ilike(search_term))
        )
    
    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit).all()
    
    user_data = [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone
    } for u in users]
        
    return {
        "users": user_data,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, 
    delete_data: schemas.UserDelete, 
    current_user: Admin = Depends(require_full_admin), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Verify Password
    if not auth.verify_password(delete_data.password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Invalid admin password")
        
    # Cascade Delete Votes
    db.query(Vote).filter(Vote.user_id == user_id).delete()
    
    # Delete User
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

# Password Change
@router.put("/password")
def change_password(
    password_data: schemas.PasswordChange,
    current_user: Admin = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Verify current password
    if not auth.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")
    
    # Validate new password
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Update password
    current_user.password_hash = auth.get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

# App Settings
@router.get("/settings")
def get_settings(
    current_user: Admin = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    voting_setting = db.query(Settings).filter(Settings.key == "voting_enabled").first()
    voting_enabled = voting_setting.value == "true" if voting_setting else True
    
    poll_count_setting = db.query(Settings).filter(Settings.key == "show_poll_count").first()
    show_poll_count = poll_count_setting.value == "true" if poll_count_setting else False
    
    return {"voting_enabled": voting_enabled, "show_poll_count": show_poll_count}

@router.put("/settings")
def update_settings(
    settings_data: schemas.AppSettings,
    current_user: Admin = Depends(require_full_admin),
    db: Session = Depends(get_db)
):
    # Verify admin password
    if not auth.verify_password(settings_data.password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    # Update voting_enabled
    voting_setting = db.query(Settings).filter(Settings.key == "voting_enabled").first()
    if not voting_setting:
        voting_setting = Settings(key="voting_enabled", value="true")
        db.add(voting_setting)
    voting_setting.value = "true" if settings_data.voting_enabled else "false"
    
    # Update show_poll_count
    poll_count_setting = db.query(Settings).filter(Settings.key == "show_poll_count").first()
    if not poll_count_setting:
        poll_count_setting = Settings(key="show_poll_count", value="false")
        db.add(poll_count_setting)
    poll_count_setting.value = "true" if settings_data.show_poll_count else "false"
    
    db.commit()
    
    return {
        "message": "Settings updated successfully", 
        "voting_enabled": settings_data.voting_enabled,
        "show_poll_count": settings_data.show_poll_count
    }

# Admin User Management (Full Admin Only)
@router.get("/admins", response_model=List[schemas.AdminResponse])
def get_admins(
    current_user: Admin = Depends(require_full_admin),
    db: Session = Depends(get_db)
):
    """List all view_admin users (full admins are not shown)."""
    admins = db.query(Admin).filter(Admin.role == "view_admin").all()
    return [{"id": a.id, "username": a.username, "role": a.role or "view_admin"} for a in admins]

@router.post("/admins", response_model=schemas.AdminResponse)
def create_admin(
    admin_data: schemas.AdminCreate,
    current_user: Admin = Depends(require_full_admin),
    db: Session = Depends(get_db)
):
    """Create a new view_admin user. Only view_admin role can be created via this API."""
    # Check if username already exists
    existing = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Force role to view_admin only - full admins cannot be created via API
    role = "view_admin"
    
    # Validate password
    if len(admin_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    new_admin = Admin(
        username=admin_data.username,
        password_hash=auth.get_password_hash(admin_data.password),
        role=role
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return {"id": new_admin.id, "username": new_admin.username, "role": new_admin.role}

@router.put("/admins/{admin_id}", response_model=schemas.AdminResponse)
def update_admin(
    admin_id: int,
    admin_data: schemas.AdminUpdate,
    current_user: Admin = Depends(require_full_admin),
    db: Session = Depends(get_db)
):
    """Update an admin user (role or password reset)."""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Update role if provided
    if admin_data.role is not None:
        if admin_data.role not in ["admin", "view_admin"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'view_admin'")
        admin.role = admin_data.role
    
    # Reset password if provided
    if admin_data.new_password is not None:
        if len(admin_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        admin.password_hash = auth.get_password_hash(admin_data.new_password)
    
    db.commit()
    db.refresh(admin)
    
    return {"id": admin.id, "username": admin.username, "role": admin.role or "admin"}

@router.delete("/admins/{admin_id}")
def delete_admin(
    admin_id: int,
    delete_data: schemas.AdminDelete,
    current_user: Admin = Depends(require_full_admin),
    db: Session = Depends(get_db)
):
    """Delete an admin user."""
    # Cannot delete self
    if admin_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Verify current admin's password
    if not auth.verify_password(delete_data.password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    db.delete(admin)
    db.commit()
    
    return {"message": f"Admin '{admin.username}' deleted successfully"}
