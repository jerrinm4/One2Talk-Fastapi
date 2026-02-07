from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)

    votes = relationship("Vote", back_populates="user")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    order = Column(Integer, default=0)

    cards = relationship("Card", back_populates="category")
    votes = relationship("Vote", back_populates="category")

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    title = Column(String)
    subtitle = Column(String)  # Supports // for line breaks
    image_url = Column(String)

    category = relationship("Category", back_populates="cards")
    votes = relationship("Vote", back_populates="card")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    card_id = Column(Integer, ForeignKey("cards.id"))

    user = relationship("User", back_populates="votes")
    category = relationship("Category", back_populates="votes")
    card = relationship("Card", back_populates="votes")

    __table_args__ = (
        UniqueConstraint('user_id', 'category_id', name='unique_user_category_vote'),
    )

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
