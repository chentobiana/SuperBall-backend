from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import random


def generate_player_name() -> str:
    """Generates a random player name in format Player + 5 digits"""
    random_number = random.randint(10000, 99999)
    return f"Player{random_number}"


class UserBase(BaseModel):
    uniqId: str


class UserCreate(UserBase):
    name: Optional[str] = None


class UserInDB(UserBase):
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    name: str = Field(default_factory=generate_player_name)  # Random name for each player

    # Game data
    level: int = 1
    score: int = 0
    coins: int = 0
    lives: int = 5
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class UserResponse(UserBase):
    """API response model with user data"""
    id: str
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    level: int
    score: int
    coins: int
    lives: int


class UserUpdate(BaseModel):
    """Model for updating user data"""
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    level: Optional[int] = None
    score: Optional[int] = None
    coins: Optional[int] = None
    lives: Optional[int] = None
    last_login: Optional[datetime] = None
