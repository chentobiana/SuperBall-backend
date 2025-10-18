from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import random
import logging

from app.database.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wheel", tags=["wheel"])

WHEEL_REWARDS = [100, 200, 300, 500, 1000, 2000, 5000, 10000]

SPIN_COOLDOWN_HOURS = 24


class WheelRewardsResponse(BaseModel):
    rewards: List[int]
    can_spin: bool
    next_spin_time: datetime = None
    current_time: datetime
    remaining_hours: float = None


class SpinRequest(BaseModel):
    uniqId: str


class RewardsRequest(BaseModel):
    uniqId: str


class ResetSpinRequest(BaseModel):
    uniqId: str


class SpinResponse(BaseModel):
    winning_id: int
    reward: int
    next_spin_time: datetime
    new_balance: int


def get_user_repo():
    return UserRepository()


@router.post("/rewards", response_model=WheelRewardsResponse)
async def get_wheel_rewards(request: RewardsRequest, user_repo: UserRepository = Depends(get_user_repo)):
    logger.info(f"Getting wheel rewards for user: {request.uniqId}")

    user = await user_repo.find_by_unique_id(request.uniqId)
    if not user:
        logger.error(f"User not found: {request.uniqId}")
        raise HTTPException(status_code=404, detail="User not found")

    current_time = datetime.utcnow()
    can_spin = True
    next_spin_time = None
    remaining_hours = None

    if getattr(user, "wheel_last_spin", None):
        time_since_last_spin = current_time - user.wheel_last_spin
        if time_since_last_spin < timedelta(hours=SPIN_COOLDOWN_HOURS):
            can_spin = False
            next_spin_time = user.wheel_last_spin + timedelta(hours=SPIN_COOLDOWN_HOURS)
            remaining_time = next_spin_time - current_time
            remaining_hours = remaining_time.total_seconds() / 3600

    return WheelRewardsResponse(
        rewards=WHEEL_REWARDS,
        can_spin=can_spin,
        next_spin_time=next_spin_time,
        current_time=current_time,
        remaining_hours=remaining_hours
    )


@router.post("/spin", response_model=SpinResponse)
async def spin_wheel(request: SpinRequest, user_repo: UserRepository = Depends(get_user_repo)):
    logger.info(f"Spin wheel request for user: {request.uniqId}")

    user = await user_repo.find_by_unique_id(request.uniqId)
    if not user:
        logger.error(f"User not found: {request.uniqId}")
        raise HTTPException(status_code=404, detail="User not found")
    current_time = datetime.utcnow()

    if user.wheel_last_spin:
        time_since_last_spin = current_time - user.wheel_last_spin
        if time_since_last_spin < timedelta(hours=SPIN_COOLDOWN_HOURS):
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

    winning_id = random.randint(0, len(WHEEL_REWARDS) - 1)
    reward = WHEEL_REWARDS[winning_id]

    new_balance = user.coins + reward
    next_spin_time = current_time + timedelta(hours=SPIN_COOLDOWN_HOURS)

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


@router.post("/reset")
async def reset_spin_timer(request: ResetSpinRequest, user_repo: UserRepository = Depends(get_user_repo)):
    """Reset the wheel spin timer for testing purposes"""
    logger.info(f"Resetting spin timer for user: {request.uniqId}")

    user = await user_repo.find_by_unique_id(request.uniqId)
    if not user:
        logger.error(f"User not found: {request.uniqId}")
        raise HTTPException(status_code=404, detail="User not found")

    from app.models.user import UserUpdate
    update_data = UserUpdate(wheel_last_spin=None)

    updated_user = await user_repo.update_user(request.uniqId, update_data)

    if not updated_user:
        logger.error(f"Failed to reset spin timer for user {request.uniqId}")
        raise HTTPException(status_code=500, detail="Failed to reset spin timer")

    logger.info(f"Successfully reset spin timer for user {request.uniqId}")

    return {"message": "Spin timer reset successfully", "uniqId": request.uniqId}
