from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
import shutil
import os
import uuid

from database import get_db
from models import User, Category, Card, Vote, Admin, Settings
import schemas
import auth

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)

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
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Protected Dependency
def get_current_admin_user(current_user: Admin = Depends(auth.get_current_admin)):
    return current_user

# Dashboard Stats
@router.get("/dashboard-stats")
def get_dashboard_stats(current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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

    return {
        "total_votes": total_votes,
        "total_users": total_users,
        "total_categories": total_categories,
        "category_stats": category_stats
    }

# Category Management
@router.post("/categories", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories", response_model=List[schemas.Category])
def get_categories(current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.order.asc()).all()

@router.put("/categories/reorder")
def reorder_categories(payload: schemas.CategoryReorderRequest, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    # payload.items is a list of category IDs in the new order
    for index, cat_id in enumerate(payload.items):
        db.query(Category).filter(Category.id == cat_id).update({"order": index})
    db.commit()
    return {"message": "Categories reordered successfully"}

@router.put("/categories/reorder")
def reorder_categories(payload: schemas.CategoryReorderRequest, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    # payload.items is a list of category IDs in the new order
    for index, cat_id in enumerate(payload.items):
        db.query(Category).filter(Category.id == cat_id).update({"order": index})
    db.commit()
    return {"message": "Categories reordered successfully"}

@router.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(category_id: int, category_update: schemas.CategoryUpdate, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_category.name = category_update.name
    db.commit()
    db.refresh(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category





@router.get("/categories/{category_id}/dependencies")
def get_category_dependencies(category_id: int, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    card_count = db.query(Card).filter(Card.category_id == category_id).count()
    vote_count = db.query(Vote).filter(Vote.category_id == category_id).count()
    return {"card_count": card_count, "vote_count": vote_count}

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, delete_data: schemas.CategoryDelete, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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
    return {"message": "Category deleted successfully"}

# Card Management
@router.post("/cards", response_model=schemas.Card)
def create_card(card: schemas.CardCreate, category_id: int, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    db_card = Card(**card.dict(), category_id=category_id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

@router.put("/cards/{card_id}", response_model=schemas.Card)
def update_card(card_id: int, card_update: schemas.CardUpdate, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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
    return db_card

@router.get("/cards/{card_id}/dependencies")
def get_card_dependencies(card_id: int, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    vote_count = db.query(Vote).filter(Vote.card_id == card_id).count()
    return {"vote_count": vote_count}

@router.delete("/cards/{card_id}")
def delete_card(card_id: int, delete_data: schemas.CardDelete, current_user: Admin = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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
    return {"message": "Card deleted successfully"}

# File Upload
@router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user: Admin = Depends(get_current_admin_user)):
    UPLOAD_DIR = "uploads"
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_location = f"{UPLOAD_DIR}/{filename}"
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    return {"url": f"/uploads/{filename}"}

# User Management
@router.get("/users")
def get_users(
    page: int = 1, 
    limit: int = 10, 
    search: str = "", 
    current_user: Admin = Depends(get_current_admin_user), 
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
    
    # Enrich with vote count
    user_data = []
    for u in users:
        vote_count = db.query(Vote).filter(Vote.user_id == u.id).count()
        user_data.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "vote_count": vote_count
        })
        
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
    current_user: Admin = Depends(get_current_admin_user), 
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
    
    return {"voting_enabled": voting_enabled}

@router.put("/settings")
def update_settings(
    settings_data: schemas.AppSettings,
    current_user: Admin = Depends(get_current_admin_user),
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
    db.commit()
    
    return {"message": "Settings updated successfully", "voting_enabled": settings_data.voting_enabled}
