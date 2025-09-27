from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database.user_repository import UserRepository
import logging
from app.models.user import UserCreate
from app.models.user import UserUpdate, UserInDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_user_repo():
    return UserRepository()


# Define request and response models for login-or-register
class LoginRequest(BaseModel):
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
    uniqId: str
    name: str


@router.post("/update-name")
async def update_name(payload: UpdateNameRequest, user_repo: UserRepository = Depends(get_user_repo)):
    """Update player's display name.

    If the user does not exist, returns 404. Name is trimmed and limited server-side if needed.
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
