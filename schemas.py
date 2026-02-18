from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

# Base Schemas
class CardBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    image_url: str

class CategoryBase(BaseModel):
    name: str
    order: int = 0

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Basic validation: Remove spaces/dashes, check length and digits
        import re
        clean_phone = re.sub(r'[\s\-]', '', v)
        if not clean_phone.isdigit():
            raise ValueError('Phone number must contain only digits')
        if not (10 <= len(clean_phone) <= 15):
             raise ValueError('Phone number must be between 10 and 15 digits')
        return clean_phone

# Creation Schemas
class CardCreate(CardBase):
    pass

class CardUpdate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: str

class CategoryDelete(BaseModel):
    password: Optional[str] = None

class CardDelete(BaseModel):
    password: Optional[str] = None

class UserDelete(BaseModel):
    password: str

class VoteItem(BaseModel):
    category_id: int
    card_id: int

class VoteCreate(BaseModel):
    user: UserBase
    votes: List[VoteItem]
    turnstile_token: str  # Cloudflare Turnstile verification token

class AdminCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"  # 'admin' or 'view_admin'

class AdminUpdate(BaseModel):
    role: Optional[str] = None
    new_password: Optional[str] = None

class AdminDelete(BaseModel):
    password: str

class CategoryReorderRequest(BaseModel):
    items: List[int]

class AdCreate(BaseModel):
    image_url: str
    link: str = "https://myg.in/"

class AdUpdate(BaseModel):
    image_url: Optional[str] = None
    link: Optional[str] = None
    enabled: Optional[bool] = None

class AdReorderRequest(BaseModel):
    items: List[int]

# Response Schemas
class Card(CardBase):
    id: int
    category_id: int

    model_config = ConfigDict(from_attributes=True)

class Category(CategoryBase):
    id: int
    cards: List[Card] = []

    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class AdminResponse(BaseModel):
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class AdResponse(BaseModel):
    id: int
    image_url: str
    link: str
    order: int
    enabled: bool

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None

class DashboardStats(BaseModel):
    total_votes: int
    total_users: int
    total_categories: int
    category_stats: List[dict]

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class AppSettings(BaseModel):
    voting_enabled: bool = True
    show_poll_count: bool = False
    password: str



