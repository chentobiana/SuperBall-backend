from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database.user_repository import UserRepository
import logging
from app.models.user import UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_user_repo():
    return UserRepository()


# Define request and response models for login-or-register
class LoginRequest(BaseModel):
    uniqId: str


class LoginResponse(BaseModel):
    name: str
    coins: int
    trophies: int


@router.post("/login-or-register", response_model=LoginResponse)
async def login_or_register(user_data: LoginRequest, user_repo: UserRepository = Depends(get_user_repo)):
    try:
        existing_user = await user_repo.find_by_unique_id(user_data.uniqId)

        if existing_user:
            await user_repo.update_last_login(user_data.uniqId)
            return {
                "name": existing_user.name,
                "coins": existing_user.coins,
                "trophies": existing_user.lives
            }
        else:
            new_user = await user_repo.create_user(
                UserCreate(uniqId=user_data.uniqId)
            )
            await user_repo.update_last_login(user_data.uniqId)
            return {
                "name": new_user.name,
                "coins": new_user.coins,
                "trophies": new_user.lives
            }

    except Exception as e:
        logger.error(f"Error in login_or_register_unity: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
