from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Category, Card, User, Vote, Settings
import schemas

router = APIRouter(
    prefix="/api",
    tags=["user"]
)

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.order.asc()).all()
    # Explicitly convert to Pydantic models to ensure successful serialization
    # since we are returning a dict, not a List[Model] directly.
    return {"categories": [schemas.Category.model_validate(c) for c in categories]}

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
