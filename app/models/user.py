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
    name: str  # Player name (required field)

    # Game rewards (persistent data)
    coins: int = 0  # Money for purchases
    trophies: int = 0  # Ranking/league position

    # Wheel system
    wheel_last_spin: Optional[datetime] = None  # Last time user spun the wheel
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class UserResponse(UserBase):
    """API response model with user data"""
    id: str
    created_at: datetime
    last_login: Optional[datetime]
    name: str
    coins: int
    trophies: int
    wheel_last_spin: Optional[datetime] = None


class UserUpdate(BaseModel):
    """Model for updating user data"""
    name: Optional[str] = None
    coins: Optional[int] = None
    trophies: Optional[int] = None
    last_login: Optional[datetime] = None
    wheel_last_spin: Optional[datetime] = None
