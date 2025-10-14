from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import random
import logging

from app.database.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wheel", tags=["wheel"])

# רשימת הפרסים בגלגל (8 פרסים)
WHEEL_REWARDS = [100, 200, 300, 500, 1000, 2000, 5000, 10000]

# זמן המתנה בין סיבובים (24 שעות)
SPIN_COOLDOWN_HOURS = 24


class WheelRewardsResponse(BaseModel):
    rewards: List[int]


class SpinRequest(BaseModel):
    uniqId: str


class SpinResponse(BaseModel):
    winning_id: int
    reward: int
    next_spin_time: datetime
    new_balance: int


@router.get("/rewards", response_model=WheelRewardsResponse)
async def get_wheel_rewards():
    logger.info("Getting wheel rewards")
    return WheelRewardsResponse(rewards=WHEEL_REWARDS)


def get_user_repo():
    return UserRepository()


@router.post("/spin", response_model=SpinResponse)
async def spin_wheel(request: SpinRequest, user_repo: UserRepository = Depends(get_user_repo)):
    logger.info(f"Spin wheel request for user: {request.uniqId}")

    # חיפוש המשתמש במסד הנתונים
    user = await user_repo.find_by_unique_id(request.uniqId)
    if not user:
        logger.error(f"User not found: {request.uniqId}")
        raise HTTPException(status_code=404, detail="User not found")
    current_time = datetime.utcnow()

    # בדיקה אם המשתמש יכול לסובב את הגלגל
    if user.wheel_last_spin:
        time_since_last_spin = current_time - user.wheel_last_spin
        if time_since_last_spin < timedelta(hours=SPIN_COOLDOWN_HOURS):
            # חישוב מתי יוכל לסובב שוב
            next_spin_time = user.wheel_last_spin + timedelta(hours=SPIN_COOLDOWN_HOURS)
            remaining_time = next_spin_time - current_time

            logger.warning(f"User {request.uniqId} tried to spin too early. Remaining time: {remaining_time}")
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "You must wait 24 hours between spins",
                    "next_spin_time": next_spin_time.isoformat(),
                    "remaining_hours": remaining_time.total_seconds() / 3600
                }
            )

    # בחירת פרס אקראי
    winning_id = random.randint(0, len(WHEEL_REWARDS) - 1)
    reward = WHEEL_REWARDS[winning_id]

    # עדכון נתוני המשתמש
    new_balance = user.coins + reward
    next_spin_time = current_time + timedelta(hours=SPIN_COOLDOWN_HOURS)

    # שמירה במסד הנתונים
    from app.models.user import UserUpdate
    update_data = UserUpdate(
        coins=new_balance,
        wheel_last_spin=current_time
    )

    updated_user = await user_repo.update_user(request.uniqId, update_data)

    if not updated_user:
        logger.error(f"Failed to update user {request.uniqId} after wheel spin")
        raise HTTPException(status_code=500, detail="Failed to update user data")

    logger.info(f"User {request.uniqId} won {reward} coins (ID: {winning_id}). New balance: {new_balance}")

    return SpinResponse(
        winning_id=winning_id,
        reward=reward,
        next_spin_time=next_spin_time,
        new_balance=new_balance
    )
