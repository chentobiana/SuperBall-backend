"""Authentication routes for user management.

Handles user registration, login, and profile updates.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database.user_repository import UserRepository
import logging
from app.models.user import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_user_repo() -> UserRepository:
    """Get user repository instance for dependency injection."""
    return UserRepository()


class LoginRequest(BaseModel):
    """Request model for login or registration.

    Supports both login and registration with optional display name.
    """
    uniqId: str
    name: str | None = None


class LoginResponse(BaseModel):
    """Minimal login response aligned with Unity flow.

    Returns only uniqId and name to keep the contract simple.
    """
    uniqId: str
    name: str


@router.post("/login-or-register", response_model=LoginResponse)
async def login_or_register(user_data: LoginRequest, user_repo: UserRepository = Depends(get_user_repo)):
    """Handle user login or registration.

    If the user exists, updates last login time.
    If not, creates a new user with the provided or generated name.

    Args:
        user_data: Login request with uniqId and optional name
        user_repo: User repository for database operations

    Returns:
        User's uniqId and display name

    Raises:
        HTTPException: If database operations fail
    """
    try:
        existing_user = await user_repo.find_by_unique_id(user_data.uniqId)
        if existing_user:
            await user_repo.update_last_login(user_data.uniqId)
            return {
                "uniqId": user_data.uniqId,
                "name": existing_user.name,
            }
        else:
            new_user = await user_repo.create_user(
                UserCreate(uniqId=user_data.uniqId, name=user_data.name)
            )
            await user_repo.update_last_login(user_data.uniqId)
            return {
                "uniqId": user_data.uniqId,
                "name": new_user.name,
            }
    except Exception as e:
        logger.error(f"Error in login_or_register_unity: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


class UpdateNameRequest(BaseModel):
    """Request model for updating player's display name."""
    uniqId: str
    name: str


@router.post("/update-name")
async def update_name(payload: UpdateNameRequest, user_repo: UserRepository = Depends(get_user_repo)):
    """Update player's display name.

    Args:
        payload: Request containing uniqId and new name
        user_repo: User repository for database operations

    Returns:
        Updated uniqId and name

    Raises:
        HTTPException: If user not found or name is invalid
    """
    try:
        if not payload.name or not payload.name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")

        existing = await user_repo.find_by_unique_id(payload.uniqId)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        updated = await user_repo.update_user(payload.uniqId, UserUpdate(name=payload.name.strip()))
        if not updated:
            # Even if nothing changed, respond with current
            updated = await user_repo.find_by_unique_id(payload.uniqId)

        assert updated is not None
        return {"uniqId": payload.uniqId, "name": updated.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating name: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/user/{uniqId}", response_model=UserResponse)
async def get_user_data(uniqId: str, user_repo: UserRepository = Depends(get_user_repo)):
    """Get full user data including rewards and stats.

    Args:
        uniqId: The unique ID of the user to fetch
        user_repo: User repository for database operations

    Returns:
        Complete user profile with all stats and rewards

    Raises:
        HTTPException: If user not found or database error occurs
    """
    try:
        user = await user_repo.find_by_unique_id(uniqId)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            uniqId=user.uniqId,
            name=user.name,
            created_at=user.created_at,
            last_login=user.last_login,
            coins=user.coins,
            trophies=user.trophies,
            wheel_last_spin=user.wheel_last_spin
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
