from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Category, Card, User, Vote, Settings
import schemas
import time

router = APIRouter(
    prefix="/api",
    tags=["user"]
)

# Simple cache for categories (1 minute TTL)
_categories_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 60  # seconds

# Cache for poll count (3 minutes TTL)
_poll_count_cache = {"data": None, "timestamp": 0}
POLL_COUNT_CACHE_TTL = 180  # 3 minutes

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    global _categories_cache
    current_time = time.time()
    
    # Return cached data if still valid
    if _categories_cache["data"] and (current_time - _categories_cache["timestamp"]) < CACHE_TTL:
        return _categories_cache["data"]
    
    # Fetch from DB and update cache
    categories = db.query(Category).order_by(Category.order.asc()).all()
    result = {"categories": [schemas.Category.model_validate(c) for c in categories]}
    
    _categories_cache["data"] = result
    _categories_cache["timestamp"] = current_time
    
    return result

@router.get("/poll-count")
def get_poll_count(db: Session = Depends(get_db)):
    """Get total poll count with 3-minute cache. Returns count only if enabled in settings."""
    global _poll_count_cache
    current_time = time.time()
    
    # Check if poll count display is enabled
    show_setting = db.query(Settings).filter(Settings.key == "show_poll_count").first()
    if not show_setting or show_setting.value != "true":
        return {"enabled": False, "total_votes": 0, "total_users": 0}
    
    # Return cached data if still valid
    if _poll_count_cache["data"] and (current_time - _poll_count_cache["timestamp"]) < POLL_COUNT_CACHE_TTL:
        return {**_poll_count_cache["data"], "enabled": True}
    
    # Fetch from DB
    total_votes = db.query(Vote).count()
    total_users = db.query(User).count()
    
    result = {
        "total_votes": total_votes,
        "total_users": total_users
    }
    
    _poll_count_cache["data"] = result
    _poll_count_cache["timestamp"] = current_time
    
    return {**result, "enabled": True}

@router.post("/vote")
def submit_vote(vote_data: schemas.VoteCreate, db: Session = Depends(get_db)):
    # 0. Check if voting is enabled
    voting_setting = db.query(Settings).filter(Settings.key == "voting_enabled").first()
    if voting_setting and voting_setting.value == "false":
        raise HTTPException(status_code=403, detail="Voting is currently closed. Please try again later.")

    # 1. Validate that all categories have been voted on
    all_categories = db.query(Category).all()
    all_cat_ids = {c.id for c in all_categories}
    voted_cat_ids = {v.category_id for v in vote_data.votes}
    
    missing_cats = all_cat_ids - voted_cat_ids
    if missing_cats:
        raise HTTPException(status_code=400, detail="Please vote in all categories before submitting.")

    # 2. Check if user already exists (Strict One-Time Vote)
    existing_user = db.query(User).filter(
        (User.email == vote_data.user.email) | 
        (User.phone == vote_data.user.phone)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="You have already submitted your votes. Duplicate entries are not allowed.")

    # 3. Create User
    user = User(
        name=vote_data.user.name,
        email=vote_data.user.email,
        phone=vote_data.user.phone
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. Process Votes
    for v in vote_data.votes:
        # Validate category_id exists (implicitly handled by all_cat_ids check above, but good for sanity)
        if v.category_id not in all_cat_ids:
             continue # or raise error for invalid category

        new_vote = Vote(
            user_id=user.id,
            category_id=v.category_id,
            card_id=v.card_id
        )
        db.add(new_vote)
    
    db.commit()
    return {"message": "Vote submitted successfully"}

