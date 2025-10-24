"""Reward system routes for game results and player rewards.

Handles game result retrieval, reward calculations, and reward simulations.
"""

from fastapi import APIRouter, HTTPException, Depends
from app.services.reward_service import RewardService
from app.models.game_result import GameResultResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rewards", tags=["rewards"])


def get_reward_service() -> RewardService:
    """Get reward service instance for dependency injection."""
    return RewardService()


@router.get("/game/{game_id}/result/{player_id}", response_model=GameResultResponse)
async def get_game_result(
    game_id: str,
    player_id: str,
    reward_service: RewardService = Depends(get_reward_service)
):
    """Get game result with rewards for a specific player.

    Args:
        game_id: ID of the game to get results for
        player_id: ID of the player to get results for
        reward_service: Reward service for calculations

    Returns:
        Game result with calculated rewards

    Raises:
        HTTPException: If game result not found or error occurs
    """
    try:
        result = await reward_service.get_game_result_for_player(game_id, player_id)
        if not result:
            raise HTTPException(status_code=404, detail="Game result not found")
        return result
    except Exception as e:
        logger.error(f"Error getting game result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{player_id}/rewards")
async def get_player_rewards(
    player_id: str,
    reward_service: RewardService = Depends(get_reward_service)
):
    """Get current player rewards.

    Args:
        player_id: ID of the player to get rewards for
        reward_service: Reward service for database access

    Returns:
        Dictionary containing trophies, money, and stars

    Raises:
        HTTPException: If player not found or error occurs
    """
    try:
        rewards = await reward_service.get_player_rewards(player_id)
        if not rewards:
            raise HTTPException(status_code=404, detail="Player not found")
        return rewards
    except Exception as e:
        logger.error(f"Error getting player rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate")
async def simulate_game_rewards(
    player_score: int,
    opponent_score: int,
    current_trophies: int = 0,
    current_money: int = 0,
    current_stars: int = 0,
    reward_service: RewardService = Depends(get_reward_service)
):
    """Simulate game rewards without updating database.

    Used for testing and previewing reward calculations.

    Args:
        player_score: Player's final score
        opponent_score: Opponent's final score
        current_trophies: Player's current trophy count
        current_money: Player's current money count
        current_stars: Player's current star count
        reward_service: Reward service for calculations

    Returns:
        Simulated game result with reward calculations

    Raises:
        HTTPException: If simulation fails
    """
    try:
        result = await reward_service.simulate_game_rewards(
            player_score=player_score,
            opponent_score=opponent_score,
            current_trophies=current_trophies,
            current_money=current_money,
            current_stars=current_stars
        )
        return result
    except Exception as e:
        logger.error(f"Error simulating game rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))
